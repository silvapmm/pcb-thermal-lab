#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file femmesh.py
@brief Structured hexahedral mesh of a Problem for the finite-element comparison model (`femcore`): plan mesh, via patches, extrusion through the stack, partial slabs.
@details Builds, from any `Problem`, either the `femcore.Model` of a conforming brick mesh or a refusal with the reason in plain text (`ValueError`).
         * **Plan mesh**: a tensor grid whose break lines are the axis-aligned edges of the outline, blocks, heaters, heatsinks and zones (lines closer than a quarter of
           the cell are merged, the feature of higher rank wins), graded from `cell / refine` near the heaters to the cell elsewhere; the elements outside a rectilinear outline
           are removed. A via with room (no break line, no polygon edge and no drill of another via in its window, `PATCH_NSIDE` elements across it) is a conforming hollow cylinder (an O-grid patch: the
           circles at the inner radius, two rings across the plating, the drill); the others are a rod of the barrel area spread over the elements under the drill.
         * **Through the thickness**: a copper layer is one slab up to 105 um and `ceil(t / 70 um)` (at most 8) above; a dielectric gap is `gap_elements` slabs graded
           towards the copper (ratio 1.4); a metal block is a pad slab and `clip(ceil(t / 1 mm), 2, 8)` block slabs, extruded only over the block (partial slabs).
         * **Exact, averaged, refused**: a rectilinear outline, an axis-aligned block, a polygon edge on a break line and a hollow barrel are exact. A zone, a heater or a
           heatsink edge that is not on a break line (a slanted edge) is the exact share of each element under the polygon (the element fill); imported masks are the mean of the
           raster over the element. A slanted or curved outline, a block that is not rectilinear, touching blocks of different thickness and a mesh above the cap are refused.
         * `unknowns` counts the unknowns of the same mesh without building the 3D arrays (the plan and the slab layout only), so the memory guard sees the exact count.
         SI units throughout; z grows downwards from the top face of the top copper layer (blocks on the top face have negative z). No GUI imports.
@see docs/theory.md 4a
"""

import bisect
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from . import blocks, copper, femcore, geometry

log = logging.getLogger(__name__)

## Most break lines per axis after the merge of near-coincident ones (a refusal above it).
FEM_MAX_LINES = 10000
## Most nodes along one axis of the plan grid (a refusal above it: the cell is too fine for this board).
FEM_MAX_AXIS = 20000
## Most via patches (conforming barrels); the other vias are rods.
FEM_MAX_PATCHES = 200
## Structural cap of the unknowns of one mesh (a refusal; the memory guard acts long before it on an ordinary machine).
FEM_MAX_UNKNOWNS = 6_000_000
## Most vertices of a rectilinear outline (the point-in-polygon test is one pass per edge over every plan element).
FEM_MAX_OUTLINE_VERTICES = 2000
## Smallest cell in mm (an element finer than this is refused: the break-line keys and the O-grid circles need micrometres).
FEM_MIN_CELL_MM = 0.02
## Elements across one side of a via window (the O-grid patch), count.
PATCH_NSIDE = 4
## Copper slabs: one up to this thickness (m), otherwise ceil(t / CU_SLAB) up to CU_SLABS_MAX.
CU_ONE_MAX = 105e-6
CU_SLAB = 70e-6
CU_SLABS_MAX = 8
## Ratio of the sizes of neighbouring elements of a graded gap.
GAP_RATIO = 1.4
## Growth of the plan element size per unit of distance from a refined zone (as `research/independent-fem-edge/lib/mesh2d.grid1d`).
GROWTH = 1.3
## Lines closer than this fraction of the cell are one line (the higher rank wins).
MERGE_FRACTION = 0.25
## Lines of the outline, blocks and box closer than this (m) are one line.
HARD_MERGE = 1e-6
## Interface pad slab of a block: conductivity (W/mK); its thickness is the interface resistance times this (as `solid3d.K_PAD`).
K_PAD = 1.0
## Block slabs per face: one per millimetre of the thickest block, at least BLOCK_SLABS[0] and at most BLOCK_SLABS[1].
BLOCK_SLAB = 1e-3
BLOCK_SLABS = (2, 8)
## Via rod fallback: samples of the drill disc (centre plus rings of 24 at the mid-radii of equal-area annuli).
ROD_RINGS = 6
ROD_PER_RING = 24
## Rank of the break lines: the lower rank wins when two lines are near each other.
RANK = {"box": 0, "outline": 0, "block": 0, "heater": 1, "heatsink": 1, "zone": 2}


@dataclass
class Plan:
    """!
    @brief The plan (2D) mesh: nodes, quads, and what each quad is.
    """
    xy: np.ndarray                    # Node coordinates (Np, 2) in m
    quads: np.ndarray                 # (Q, 4) node ids, counter-clockwise
    x0: np.ndarray                    # Bounding box of every quad (Q,) in m (the quad itself for a tensor quad)
    x1: np.ndarray
    y0: np.ndarray
    y1: np.ndarray
    area: np.ndarray                  # Area of every quad (Q,) in m2
    rect: np.ndarray                  # True for a tensor (rectangular) quad (Q,)
    tag: np.ndarray                   # 0 board material, 1 via core, 2 via barrel (plating) (Q,)
    via: np.ndarray                   # Index of the via a patch quad belongs to, -1 otherwise (Q,)
    active: np.ndarray                # True for a quad on the board (inside the outline) (Q,)
    qid: np.ndarray                   # (ny, nx) quad id of every tensor cell, -1 inside a via window
    xn: np.ndarray                    # Node lines of the tensor grid in m
    yn: np.ndarray

    @property
    def cx(self):
        """!
        @brief Centroid x of every quad.
        @return numpy.ndarray (Q,) in m.
        """
        return self.xy[self.quads, 0].mean(axis=1)

    @property
    def cy(self):
        """!
        @brief Centroid y of every quad.
        @return numpy.ndarray (Q,) in m.
        """
        return self.xy[self.quads, 1].mean(axis=1)


@dataclass
class FemMesh:
    """!
    @brief A built mesh: the `femcore.Model` plus what the read-outs and the checks need.
    """
    model: "femcore.Model"
    n_unknowns: int
    n_elements: int
    plan: Plan
    slabs: List[dict]                 # The z slabs from the top (kind, layer, region, dz, element range)
    planes: int                       # Node planes through the stack
    elem_slab: np.ndarray             # Slab index of every element (E,)
    elem_quad: np.ndarray             # Plan quad of every element (E,)
    copper_slabs: List[List[int]]     # Slab indices of every copper layer
    heater_elems: List[np.ndarray]    # Element ids that carry every heater's source
    warnings: List[str] = field(default_factory=list)
    n_patches: int = 0
    n_rods: int = 0
    volume_board: float = 0.0         # Volume of the board slabs (elements of copper and gaps), m3


# ----------------------------------------------------------------------------------------------------------------------------------------
# Small geometry helpers


def _rectilinear(poly, tol=1e-9):
    """!
    @brief Whether every edge of a polygon is parallel to an axis.
    @param poly Polygon vertices (n, 2) in m.
    @param tol Relative tolerance on the extent of the polygon.
    @return bool.
    """
    p = np.asarray(poly, dtype=float)
    d = np.roll(p, -1, axis=0) - p
    scale = max(float(np.ptp(p, axis=0).max()), 1e-12)
    return bool(np.all((np.abs(d[:, 0]) <= tol * scale) | (np.abs(d[:, 1]) <= tol * scale)))


def _edge_lines(poly, tol=1e-9):
    """!
    @brief The coordinates of the axis-parallel edges of a polygon: x of the vertical edges and y of the horizontal ones.
    @param poly Polygon vertices (n, 2) in m.
    @param tol Relative tolerance on the extent of the polygon.
    @return Tuple (xs, ys) of arrays in m.
    """
    p = np.asarray(poly, dtype=float)
    d = np.roll(p, -1, axis=0) - p
    scale = max(float(np.ptp(p, axis=0).max()), 1e-12)
    vert = (np.abs(d[:, 0]) <= tol * scale) & (np.abs(d[:, 1]) > tol * scale)
    hor = (np.abs(d[:, 1]) <= tol * scale) & (np.abs(d[:, 0]) > tol * scale)
    return p[vert, 0], p[hor, 1]


def _merge_lines(cands, length, h_plan):
    """!
    @brief Merge near-coincident break lines of one axis.
    @details Lines are taken in order of rank (the box, outline and block lines first, then heaters and heatsinks, then zones) and then by value; a line is dropped when a line that
             is already kept is nearer than a quarter of the cell (HARD_MERGE for the hard ranks). The two ends of the box are always lines.
    @param cands List of (value in m, rank).
    @param length Length of the axis in m.
    @param h_plan Cell size in m.
    @return Sorted list of the interior break lines in m.
    @throws ValueError If more than FEM_MAX_LINES lines remain.
    """
    items = sorted(((r, float(v)) for v, r in cands if 0.0 < v < length), key=lambda t: (t[0], t[1]))
    kept = [0.0, float(length)]                                   # Sorted; the ends count as kept lines
    for r, v in items:
        tol = HARD_MERGE if r == 0 else MERGE_FRACTION * h_plan
        k = bisect.bisect_left(kept, v)
        if (k > 0 and v - kept[k - 1] < tol) or (k < len(kept) and kept[k] - v < tol):
            continue
        kept.insert(k, v)
    if len(kept) - 2 > FEM_MAX_LINES:
        raise ValueError(f"the FEM needs {len(kept) - 2} break lines along one axis (the edges of the drawn elements), more than the {FEM_MAX_LINES} it accepts; "
                         "simplify the drawing or use another model")
    return kept[1:-1]


def _grid1d(length, breaks, zones, h_fine, h_max, growth=GROWTH):
    """!
    @brief Graded node list of one axis that contains every break line: size h_fine inside the zones, growing with the distance from them up to h_max.
    @param length End coordinate in m.
    @param breaks Coordinates that must be nodes, in m.
    @param zones List of (a, b) intervals in m where the size is h_fine.
    @param h_fine Fine element size in m.
    @param h_max Largest element size in m.
    @param growth Size growth per unit of distance from a zone.
    @return numpy.ndarray of increasing node coordinates in m.
    @throws ValueError If the axis would have more than FEM_MAX_AXIS nodes.
    """
    pts = sorted(set([0.0, float(length)] + [float(b) for b in breaks if 0.0 < b < length]))
    if length / h_fine + len(pts) > FEM_MAX_AXIS:
        raise ValueError(f"the cell of {h_max * 1e3:g} mm gives more than {FEM_MAX_AXIS} elements along {length * 1e3:g} mm of the board: use a coarser cell")
    zs = np.asarray(zones, float).reshape(-1, 2)

    def size(x):
        """!
        @brief Target element size at x.
        @param x Coordinate in m.
        @return float.
        """
        if zs.size == 0:
            return h_max
        d = np.maximum(np.maximum(zs[:, 0] - x, x - zs[:, 1]), 0.0).min()
        return min(h_max, h_fine + (growth - 1.0) * d)

    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        steps, x = [], a
        while x < b - 1e-15:
            s = size(x)
            steps.append(s)
            x += s
        # The march overshoots b: drop the last step when it overshoots by more than half of it, then rescale so that the interval is filled exactly
        if len(steps) > 1 and (x - b) > 0.5 * steps[-1]:
            steps.pop()
        steps = np.asarray(steps) * (b - a) / sum(steps)
        out.extend((a + np.cumsum(steps)).tolist())
        out[-1] = b
    return np.asarray(out)


def _uniform_window(xn, x0, x1, n):
    """!
    @brief Replace the nodes of an axis inside [x0, x1] by n uniform intervals (x0 and x1 are nodes).
    @param xn Node coordinates in m.
    @param x0 Window start in m.
    @param x1 Window end in m.
    @param n Intervals inside the window.
    @return numpy.ndarray of sorted node coordinates.
    """
    keep = xn[(xn < x0 - 1e-12) | (xn > x1 + 1e-12)]
    return np.asarray(sorted(set(keep.tolist() + np.linspace(x0, x1, n + 1).tolist())))


def graded_gap(thickness, n, ratio=GAP_RATIO):
    """!
    @brief Element thicknesses of a gap cut in n elements, finest next to both faces (the copper), growing towards the middle.
    @param thickness Gap thickness in m.
    @param n Number of elements.
    @param ratio Size ratio between neighbouring elements (1: uniform).
    @return numpy.ndarray of n thicknesses summing to `thickness`.
    """
    if n == 1:
        return np.array([float(thickness)])
    i = np.arange(n)
    w = ratio ** np.minimum(i, n - 1 - i)
    return thickness * w / w.sum()


def copper_slab_count(t):
    """!
    @brief Elements through a copper layer: one up to 105 um, otherwise ceil(t / 70 um), at most 8.
    @param t Copper thickness in m.
    @return int.
    """
    if t <= CU_ONE_MAX:
        return 1
    return int(min(CU_SLABS_MAX, math.ceil(t / CU_SLAB - 1e-9)))


# ----------------------------------------------------------------------------------------------------------------------------------------
# The O-grid patch of a via


def _ogrid(cx, cy, s0, radii, n, half, n_blend, n_inner):
    """!
    @brief O-grid (butterfly) patch: an inner square, rings bounded by circles and a square window outside (port of `research/independent-fem-edge/lib/mesh2d.ogrid`).
    @param cx Centre x in m.
    @param cy Centre y in m.
    @param s0 Half side of the inner square in m (below radii[0] / sqrt 2).
    @param radii Increasing circle radii in m.
    @param n Intervals per side of the inner square and of the window.
    @param half Half side of the window in m.
    @param n_blend Blended levels between the last circle and the window.
    @param n_inner Blended levels between the inner square and the first circle.
    @return Tuple (xy (N, 2), quads (M, 4) counter-clockwise, ring (M,) ring index of every quad (0 the inner square), outer (4 n,) node ids of the window loop).
    """
    t = np.linspace(-s0, s0, n + 1)
    X, Y = np.meshgrid(t + cx, t + cy)
    inner_xy = np.column_stack([X.ravel(), Y.ravel()])
    nid = np.arange((n + 1) ** 2).reshape(n + 1, n + 1)
    iq = np.stack([nid[:-1, :-1], nid[:-1, 1:], nid[1:, 1:], nid[1:, :-1]], axis=2).reshape(-1, 4)
    loop = np.concatenate([nid[0, :-1], nid[:-1, n], nid[n, :0:-1], nid[::-1, 0][:-1]])
    p = inner_xy[loop] - np.array([cx, cy])
    theta = np.arctan2(p[:, 1], p[:, 0])
    u = np.column_stack([np.cos(theta), np.sin(theta)])
    c0 = np.array([cx, cy])
    levels = [inner_xy[loop]]
    first = c0 + radii[0] * u
    for b in range(1, n_inner + 1):
        f = b / (n_inner + 1)
        levels.append((1 - f) * levels[0] + f * first)
    for r in radii:
        levels.append(c0 + r * u)
    sq = c0 + p * (half / s0)
    last = levels[-1]
    for b in range(1, n_blend + 1):
        f = b / (n_blend + 1)
        levels.append((1 - f) * last + f * sq)
    levels.append(sq)
    xy = [inner_xy]
    ids = [loop]
    base = inner_xy.shape[0]
    for lv in levels[1:]:
        xy.append(lv)
        ids.append(np.arange(base, base + lv.shape[0]))
        base += lv.shape[0]
    quads = [iq]
    ring = [np.zeros(iq.shape[0], np.int64)]
    m = loop.size
    nxt = np.roll(np.arange(m), -1)
    for j in range(1, len(levels)):
        lo, hi = ids[j - 1], ids[j]
        quads.append(np.column_stack([lo, hi, hi[nxt], lo[nxt]]))
        ring.append(np.full(m, j, np.int64))
    return np.vstack(xy), np.vstack(quads), np.concatenate(ring), ids[-1]


def _area_fix(n):
    """!
    @brief Radius factor that gives the polygon of the circle levels of an O-grid the area of the circle.
    @details The nodes of a circle level lie on the rays of the uniform parametrisation of the inner square (4 n rays at unequal angles), so the polygon has the area
             0.5 r^2 sum(sin(dtheta)), a little under pi r^2; scaled by this factor the plating ring has exactly the area of the annulus (the conduction along the barrel is exact).
    @param n Intervals per side of the inner square.
    @return float, a little above 1.
    """
    t = np.linspace(-1.0, 1.0, n + 1)
    nid = np.arange((n + 1) ** 2).reshape(n + 1, n + 1)
    X, Y = np.meshgrid(t, t)
    xy = np.column_stack([X.ravel(), Y.ravel()])
    loop = np.concatenate([nid[0, :-1], nid[:-1, n], nid[n, :0:-1], nid[::-1, 0][:-1]])
    th = np.arctan2(xy[loop, 1], xy[loop, 0])
    dth = np.diff(np.concatenate([th, [th[0] + 2.0 * math.pi]]))
    dth = np.mod(dth, 2.0 * math.pi)
    return math.sqrt(math.pi / (0.5 * np.sin(dth).sum()))


## The circles of a via patch are polygons of 4 PATCH_NSIDE nodes; their radius is scaled by this so that the polygon has the area of the circle (a ring then has the exact area of the plating).
AREA_FIX = _area_fix(PATCH_NSIDE)


# ----------------------------------------------------------------------------------------------------------------------------------------
# The layout: axes, windows, plan, slabs. Everything that does not need the 3D arrays.


@dataclass
class _Layout:
    """!
    @brief The geometry-only part of a mesh: enough to count the unknowns and to build the arrays.
    """
    plan: Plan
    windows: List[dict]               # The patched vias: via index, centre, half, n_core_rings, n_barrel_rings, radii
    rods: List[int]                   # Via indices that are rods
    zs: List[dict]                    # The z slabs from the top
    sets: Dict[object, np.ndarray]    # Quad ids of every region key ('board', ('blk', block index))
    blocks: List[dict]                # The blocks of both faces: index into problem.heatsinks, face, quads, dz pad and block
    b0: int                           # Index of the first board slab
    b1: int                           # Index after the last board slab
    n_planes: int
    nid: Optional[np.ndarray]         # (n_planes, Np) node ids, -1 where unused
    z: Optional[np.ndarray]           # (n_planes, Np) z of the nodes, nan where unused
    n_unknowns: int
    open_core: np.ndarray             # Quads of an open via core (no element)
    warnings: List[str]


def _check_supported(problem):
    """!
    @brief Refuse what the structured mesh cannot hold, with the reason.
    @param problem A Problem (validated).
    @return None.
    @throws ValueError With the reason.
    """
    b = problem.board
    if b.has_outline():
        o = np.asarray(b.outline, float)
        if not np.isfinite(o).all():
            raise ValueError("the board outline has a non-finite coordinate")
        if not _rectilinear(o):
            raise ValueError("the FEM needs a rectangular or axis-aligned outline in this version: the outline has a slanted or curved side (use the FVM, which cuts the cells)")
        if len(o) > FEM_MAX_OUTLINE_VERTICES:
            raise ValueError(f"the board outline has {len(o)} vertices, more than the {FEM_MAX_OUTLINE_VERTICES} the FEM accepts")
    for s in problem.heatsinks:
        if s.is_block() and len(s.polygon) >= 3 and not _rectilinear(s.polygon):
            raise ValueError("the FEM needs every metal block to have axis-aligned sides in this version (a slanted block side would be a staircase)")


def _polygons(problem):
    """!
    @brief Every polygon that gives break lines, with its rank.
    @param problem A Problem.
    @return List of (polygon (n, 2), rank).
    """
    out = []
    b = problem.board
    if b.has_outline():
        out.append((np.asarray(b.outline, float), RANK["outline"]))
    for s in problem.heatsinks:
        if len(s.polygon) >= 3:
            out.append((np.asarray(s.polygon, float), RANK["block"] if s.is_block() else RANK["heatsink"]))
    for h in problem.heaters:
        if len(h.polygon) >= 3:
            out.append((np.asarray(h.polygon, float), RANK["heater"]))
    for z in problem.zones:
        if len(z.polygon) >= 3:
            out.append((np.asarray(z.polygon, float), RANK["zone"]))
    return out


def _ring_radii(via, plating):
    """!
    @brief The circles of the O-grid of a via and what lies inside them.
    @param via A Via.
    @param plating Plating thickness in m.
    @return Tuple (radii list in m, n_barrel_rings, core_kind) with core_kind 'solid' (a copper rod), 'open' or 'fill'.
    """
    r = 0.5 * via.diameter
    r_in = r - plating
    if via.filled or r_in <= 0.25 * r:
        return [r], 0, "solid"
    return [r_in, r_in + 0.5 * (r - r_in), r], 2, ("fill" if via.fill_k > 0 else "open")


def _window_half(via, h_fine):
    """!
    @brief Half side of the via window.
    @param via A Via.
    @param h_fine Fine element size in m.
    @return float in m.
    """
    return max(2.0 * h_fine, 1.25 * via.diameter)


def _select_windows(problem, bx, by, h_fine, shares):
    """!
    @brief Choose the vias that get a conforming patch (greedy, in the order of the vias).
    @details A via needs its window on the board, free of break lines, of polygon edges, of the drills of the other vias, of the windows already chosen and of any window interval
             that overlaps its own along an axis without being the same (the window lines run across the whole tensor grid). The others are rods.
    @param problem A Problem.
    @param bx Interior break lines along x in m (all ranks).
    @param by Interior break lines along y in m.
    @param h_fine Fine element size in m.
    @param shares Board share of every via (0 for a via with no board under it).
    @return Tuple (windows, rods): windows list of dict(via, cx, cy, half), rods list of via indices (vias with no board are in neither).
    """
    b = problem.board
    plating = b.via_plating
    win, rods = [], []
    bxs, bys = np.asarray(sorted(bx)), np.asarray(sorted(by))

    def has_line(lines, a, c):
        """!
        @brief Whether a break line lies strictly inside (a, c).
        @param lines Sorted array of lines in m.
        @param a Interval start in m.
        @param c Interval end in m.
        @return bool.
        """
        k = np.searchsorted(lines, a + 1e-9, side="left")
        return bool(k < lines.size and lines[k] < c - 1e-9)

    def compatible(i0, i1, j0, j1):
        """!
        @brief Whether two intervals are disjoint or the same one.
        @param i0 Start of the first in m.
        @param i1 End of the first in m.
        @param j0 Start of the second in m.
        @param j1 End of the second in m.
        @return bool.
        """
        if abs(i0 - j0) < 1e-9 and abs(i1 - j1) < 1e-9:
            return True
        return i1 <= j0 + 1e-9 or j1 <= i0 + 1e-9

    outline = np.asarray(b.outline, float) if b.has_outline() else None
    # The vias on the board, sorted along x: a window must hold no drill of another via (a rod whose drill falls in a patch would find no tensor element there and its
    # barrel would be lost; the review measured half the barrel copper of a 4 x 4 array at 2 mm gone before this test)
    on = [k for k, v in enumerate(problem.vias) if shares[k] > 0.0]
    vx = np.array([problem.vias[k].x for k in on], float)
    vy = np.array([problem.vias[k].y for k in on], float)
    vr = np.array([0.5 * problem.vias[k].diameter for k in on], float)
    order = np.argsort(vx, kind="stable")
    sx, sy, sr, sk = vx[order], vy[order], vr[order], np.asarray(on, np.int64)[order]
    r_max = float(vr.max()) if vr.size else 0.0

    def crowded(k, x0, x1, y0, y1):
        """!
        @brief Whether the drill of a via other than k reaches into the window [x0, x1] x [y0, y1].
        @param k Index of the via of the window.
        @param x0 Window start along x in m.
        @param x1 Window end along x in m.
        @param y0 Window start along y in m.
        @param y1 Window end along y in m.
        @return bool.
        """
        a = int(np.searchsorted(sx, x0 - r_max, side="left"))
        c = int(np.searchsorted(sx, x1 + r_max, side="right"))
        if c - a <= 1:
            return False
        sel = slice(a, c)
        hit = (sx[sel] + sr[sel] > x0) & (sx[sel] - sr[sel] < x1) & (sy[sel] + sr[sel] > y0) & (sy[sel] - sr[sel] < y1) & (sk[sel] != k)
        return bool(hit.any())

    # Every polygon edge (outline, blocks, heatsinks, heaters, zones): a window that one of them crosses is refused, so that every quad of a patch is wholly inside or
    # outside each polygon and its centroid gives the exact share (a zone edge merged into a near break line, or a slanted one, could otherwise cross the patch, whose
    # quads read the polygon by their centroid: the review measured 1.2 mm2 of copper lost on a zone edge 0.4 mm from a part edge)
    segs = []
    for poly, _ in _polygons(problem):
        q = np.asarray(poly, float)
        segs.append(np.hstack([q, np.roll(q, -1, axis=0)]))
    segs = np.vstack(segs) if segs else np.zeros((0, 4))

    def crossed(x0, x1, y0, y1):
        """!
        @brief Whether a polygon edge crosses the open interior of the window [x0, x1] x [y0, y1] (Liang-Barsky against the window shrunk by 1e-9 m).
        @param x0 Window start along x in m.
        @param x1 Window end along x in m.
        @param y0 Window start along y in m.
        @param y1 Window end along y in m.
        @return bool.
        """
        if segs.shape[0] == 0:
            return False
        e = 1e-9
        xa, ya, xb, yb = segs[:, 0], segs[:, 1], segs[:, 2], segs[:, 3]
        near = (np.maximum(xa, xb) > x0 + e) & (np.minimum(xa, xb) < x1 - e) & (np.maximum(ya, yb) > y0 + e) & (np.minimum(ya, yb) < y1 - e)
        if not near.any():
            return False
        xa, ya, xb, yb = xa[near], ya[near], xb[near], yb[near]
        t0, t1 = np.zeros(xa.size), np.ones(xa.size)
        ok = np.ones(xa.size, bool)
        for d, a, lo, hi in ((xb - xa, xa, x0 + e, x1 - e), (yb - ya, ya, y0 + e, y1 - e)):
            flat = d == 0.0
            ok &= ~flat | ((a > lo) & (a < hi))
            dd = np.where(flat, 1.0, d)
            ta, tb = (lo - a) / dd, (hi - a) / dd
            t0 = np.where(flat, t0, np.maximum(t0, np.minimum(ta, tb)))
            t1 = np.where(flat, t1, np.minimum(t1, np.maximum(ta, tb)))
        return bool((ok & (t0 < t1 - 1e-12)).any())

    for k, v in enumerate(problem.vias):
        if shares[k] <= 0.0:
            continue
        if len(win) >= FEM_MAX_PATCHES:
            rods.append(k)
            continue
        half = _window_half(v, h_fine)
        x0, x1, y0, y1 = v.x - half, v.x + half, v.y - half, v.y + half
        ok = x0 > 1e-9 and y0 > 1e-9 and x1 < b.width - 1e-9 and y1 < b.height - 1e-9
        ok = ok and not crowded(k, x0, x1, y0, y1)
        ok = ok and not has_line(bxs, x0, x1) and not has_line(bys, y0, y1) and not crossed(x0, x1, y0, y1)
        if ok and outline is not None:
            # The window must lie wholly inside the outline: its centre and corners are inside (no outline line crosses it, tested above)
            px = np.array([v.x, x0, x1, x0, x1])
            py = np.array([v.y, y0, y0, y1, y1])
            ok = bool(geometry.points_in_polygon(px, py, outline).all())
        if ok:
            for w in win:
                if abs(w["cx"] - v.x) < w["half"] + half - 1e-9 and abs(w["cy"] - v.y) < w["half"] + half - 1e-9:
                    ok = False
                    break
                if not compatible(x0, x1, w["cx"] - w["half"], w["cx"] + w["half"]) or not compatible(y0, y1, w["cy"] - w["half"], w["cy"] + w["half"]):
                    ok = False
                    break
        if ok:
            radii, n_barrel, kind = _ring_radii(v, plating)
            if radii[-1] > 0.8 * half:
                ok = False
        if ok:
            win.append({"via": k, "cx": v.x, "cy": v.y, "half": half})
        else:
            rods.append(k)
    return win, rods


def _axes(problem, cell_mm, refine, shares):
    """!
    @brief The node lines of the tensor grid and the via windows.
    @param problem A Problem.
    @param cell_mm Plan cell in mm (the coarse element).
    @param refine Ratio of the cell to the fine element near the heaters and via patches, at least 1.
    @param shares Board share of every via.
    @return Tuple (xn, yn, windows, rods).
    @throws ValueError If the cell is too fine, the break lines are too many or the axis too long.
    """
    b = problem.board
    h_plan = float(cell_mm) * 1e-3
    if not (math.isfinite(h_plan) and cell_mm >= FEM_MIN_CELL_MM):
        raise ValueError(f"the FEM needs a cell of at least {FEM_MIN_CELL_MM:g} mm")
    refine = max(float(refine), 1.0)
    h_fine = h_plan / refine
    if h_fine < 1e-5:
        raise ValueError("the fine element of the FEM would be below 10 µm: use a coarser cell or a smaller refinement")
    cands_x = [(0.0, 0), (b.width, 0)]
    cands_y = [(0.0, 0), (b.height, 0)]
    zones_x, zones_y = [], []
    margin = 2.0 * max(float(np.max(b.gap_thicknesses())) if b.layers > 1 else 0.0, 1e-4)
    for poly, rank in _polygons(problem):
        xs, ys = _edge_lines(poly)
        cands_x += [(float(v), rank) for v in xs]
        cands_y += [(float(v), rank) for v in ys]
    for h in problem.heaters:
        if len(h.polygon) >= 3:
            p = np.asarray(h.polygon, float)
            zones_x.append((p[:, 0].min() - margin, p[:, 0].max() + margin))
            zones_y.append((p[:, 1].min() - margin, p[:, 1].max() + margin))
    bx = _merge_lines(cands_x, b.width, h_plan)
    by = _merge_lines(cands_y, b.height, h_plan)
    windows, rods = _select_windows(problem, bx, by, h_fine, shares)
    wx = [(w["cx"] - w["half"], w["cx"] + w["half"]) for w in windows]
    wy = [(w["cy"] - w["half"], w["cy"] + w["half"]) for w in windows]
    xn = _grid1d(b.width, bx + [v for a in wx for v in a], zones_x + wx, h_fine, h_plan)
    yn = _grid1d(b.height, by + [v for a in wy for v in a], zones_y + wy, h_fine, h_plan)
    for a in sorted(set((round(a, 12), round(c, 12)) for a, c in wx)):
        xn = _uniform_window(xn, a[0], a[1], PATCH_NSIDE)
    for a in sorted(set((round(a, 12), round(c, 12)) for a, c in wy)):
        yn = _uniform_window(yn, a[0], a[1], PATCH_NSIDE)
    if xn.size - 1 > FEM_MAX_AXIS or yn.size - 1 > FEM_MAX_AXIS:
        raise ValueError(f"the cell of {cell_mm:g} mm gives more than {FEM_MAX_AXIS} elements along one side of the board: use a coarser cell")
    return xn, yn, windows, rods


def _slab_layout(problem, gap_elements):
    """!
    @brief The z slabs of the board (copper layers and gaps) from the top, without the blocks.
    @param problem A Problem.
    @param gap_elements Elements across every dielectric gap, at least 1.
    @return List of dict(kind 'cu' or 'gap', layer, gap, dz array).
    """
    b = problem.board
    tc = np.asarray(b.copper_thickness, float)
    out = []
    n = max(int(gap_elements), 1)
    if b.layers == 1:
        t_lam = float(b.slab_thicknesses()[0] - tc[0])
        out.append({"kind": "cu", "layer": 0, "gap": -1, "dz": np.full(copper_slab_count(tc[0]), tc[0] / copper_slab_count(tc[0]))})
        if t_lam > 0:
            out.append({"kind": "gap", "layer": 0, "gap": -1, "dz": graded_gap(t_lam, n)})
        return out
    gaps = b.gap_thicknesses()
    for l in range(b.layers):
        c = copper_slab_count(tc[l])
        out.append({"kind": "cu", "layer": l, "gap": -1, "dz": np.full(c, tc[l] / c)})
        if l < b.layers - 1:
            out.append({"kind": "gap", "layer": l, "gap": l, "dz": graded_gap(float(gaps[l]), n)})
    return out


def _boundary_edges(quads, ids):
    """!
    @brief Edges that belong to exactly one quad of a set.
    @param quads All quads (Q, 4).
    @param ids Quad ids of the set.
    @return numpy.ndarray (B, 2) of node ids.
    """
    q = quads[ids]
    e = np.stack([q, np.roll(q, -1, axis=1)], axis=2).reshape(-1, 2)
    key = np.sort(e, axis=1)
    big = int(quads.max()) + 1
    k = key[:, 0].astype(np.int64) * big + key[:, 1]
    _, inv, cnt = np.unique(k, return_inverse=True, return_counts=True)
    return e[cnt[inv.ravel()] == 1]


def _build_plan(problem, xn, yn, windows):
    """!
    @brief The plan quads: the tensor grid with the window cells replaced by the O-grid patches.
    @param problem A Problem.
    @param xn Node lines along x in m.
    @param yn Node lines along y in m.
    @param windows The patched vias (dict via, cx, cy, half).
    @return Plan.
    """
    b = problem.board
    nx, ny = xn.size - 1, yn.size - 1
    X, Y = np.meshgrid(xn, yn)
    xy_t = np.column_stack([X.ravel(), Y.ravel()])
    nid = np.arange((nx + 1) * (ny + 1)).reshape(ny + 1, nx + 1)
    q_t = np.stack([nid[:-1, :-1], nid[:-1, 1:], nid[1:, 1:], nid[1:, :-1]], axis=2).reshape(-1, 4)
    cxm = 0.5 * (xn[:-1] + xn[1:])
    cym = 0.5 * (yn[:-1] + yn[1:])
    keep = np.ones((ny, nx), bool)
    for w in windows:
        jx = (cxm > w["cx"] - w["half"]) & (cxm < w["cx"] + w["half"])
        jy = (cym > w["cy"] - w["half"]) & (cym < w["cy"] + w["half"])
        keep[np.ix_(jy, jx)] = False
    # Active: the cells whose centroid is inside a rectilinear outline (the break lines make that exact)
    if b.has_outline():
        CX, CY = np.meshgrid(cxm, cym)
        act = geometry.points_in_polygon(CX.ravel(), CY.ravel(), np.asarray(b.outline, float)).reshape(ny, nx)
    else:
        act = np.ones((ny, nx), bool)
    flat_keep = keep.ravel()
    idx_t = np.cumsum(flat_keep) - 1
    qid = np.where(keep, idx_t.reshape(ny, nx), -1)
    quads = [q_t[flat_keep]]
    tag = [np.zeros(int(flat_keep.sum()), np.int8)]
    via = [np.full(int(flat_keep.sum()), -1, np.int64)]
    active = [act.ravel()[flat_keep]]
    xy = [xy_t]
    n_nodes = xy_t.shape[0]
    plating = b.via_plating
    for w in windows:
        v = problem.vias[w["via"]]
        radii, n_barrel, kind = _ring_radii(v, plating)
        radii = [r * AREA_FIX for r in radii]                      # equal-area polygons: the plating ring has the area of the annulus
        s0 = 0.55 * radii[0] / math.sqrt(2.0)
        n_inner = 1                                              # one blended level between the inner square and the first circle
        pxy, pq, ring, outer = _ogrid(w["cx"], w["cy"], s0, radii, PATCH_NSIDE, w["half"], 2, n_inner)
        # The window loop nodes are the nodes of the tensor grid: take their ids from the lattice
        ix0 = int(np.searchsorted(xn, w["cx"] - w["half"] - 1e-9))
        iy0 = int(np.searchsorted(yn, w["cy"] - w["half"] - 1e-9))
        per = nid[iy0:iy0 + PATCH_NSIDE + 1, ix0:ix0 + PATCH_NSIDE + 1]
        per_ids = np.concatenate([per[0, :-1], per[:-1, PATCH_NSIDE], per[PATCH_NSIDE, :0:-1], per[::-1, 0][:-1]])
        mapping = np.full(pxy.shape[0], -1, np.int64)
        mapping[outer] = per_ids
        free = mapping < 0
        mapping[free] = n_nodes + np.arange(int(free.sum()))
        n_nodes += int(free.sum())
        xy.append(pxy[free])
        quads.append(mapping[pq])
        # Material of every ring: inside the first circle (rings up to n_inner + 1) the core, then the plating, then the board
        t = np.zeros(pq.shape[0], np.int8)
        t[ring <= n_inner + 1] = 1
        if kind != "solid":
            t[(ring > n_inner + 1) & (ring <= n_inner + 1 + n_barrel)] = 2
        tag.append(t)
        via.append(np.full(pq.shape[0], w["via"], np.int64))
        active.append(np.ones(pq.shape[0], bool))
    xy = np.vstack(xy)
    quads = np.vstack(quads)
    pts = xy[quads]
    x0, x1 = pts[:, :, 0].min(axis=1), pts[:, :, 0].max(axis=1)
    y0, y1 = pts[:, :, 1].min(axis=1), pts[:, :, 1].max(axis=1)
    px, py = pts[:, :, 0], pts[:, :, 1]
    area = 0.5 * np.abs((px * np.roll(py, -1, axis=1) - np.roll(px, -1, axis=1) * py).sum(axis=1))
    rect = np.zeros(quads.shape[0], bool)
    rect[:int(flat_keep.sum())] = True
    return Plan(xy=xy, quads=quads, x0=x0, x1=x1, y0=y0, y1=y1, area=area, rect=rect, tag=np.concatenate(tag), via=np.concatenate(via),
                active=np.concatenate(active), qid=qid, xn=xn, yn=yn)


def _coarser_cell(cell_mm, ratio):
    """!
    @brief The advice of a refusal for too many unknowns: which cell to use, like the memory lines of the other models (review of the window: 'use a coarser cell' gave no number).
    @details The plan unknowns fall about as 1 / cell^2 and the through-thickness planes do not change with the cell, so the cell is scaled by the square root of the
             ratio, with 5 % to spare, and rounded up to 0.1 mm; it is an estimate ('about').
    @param cell_mm Cell of the refused mesh in mm.
    @param ratio Unknowns of the refused mesh divided by the limit (> 1).
    @return str, for example 'use a cell of about 1.4 mm or more'.
    """
    cell = math.ceil(cell_mm * math.sqrt(max(ratio, 1.0)) * 1.05 * 10.0 - 1e-9) / 10.0
    return f"use a cell of about {cell:.1f} mm or more"


def _layout(problem, cell_mm, gap_elements, refine):
    """!
    @brief The geometry of the mesh: axes, plan, slabs, regions and the exact count of the unknowns.
    @param problem A validated Problem.
    @param cell_mm Plan cell in mm.
    @param gap_elements Elements across every dielectric gap.
    @param refine Ratio of the cell to the fine element near the heaters and via patches.
    @return _Layout.
    @throws ValueError With the reason, when the mesh cannot be built.
    """
    _check_supported(problem)
    b = problem.board
    shares = problem.via_board_shares()
    xn, yn, windows, rods = _axes(problem, cell_mm, refine, shares)
    board_slabs = _slab_layout(problem, gap_elements)
    n_board = sum(len(s["dz"]) for s in board_slabs)
    # The blocks add slabs: a pad and 2 to 8 block slabs on every face that has one
    faces = {}
    for k, s in enumerate(problem.heatsinks):
        if s.is_block() and len(s.polygon) >= 3:
            face = 0 if (s.layer == 0 or b.layers == 1) else 1
            faces.setdefault(face, []).append(k)
    n_blk = {f: int(np.clip(math.ceil(max(problem.heatsinks[k].thickness for k in ks) / BLOCK_SLAB - 1e-9), BLOCK_SLABS[0], BLOCK_SLABS[1])) for f, ks in faces.items()}
    n_planes_est = n_board + 1 + sum(1 + n_blk[f] for f in faces)
    nxy = (xn.size - 1) * (yn.size - 1)
    if nxy * n_planes_est > FEM_MAX_UNKNOWNS * 1.5:
        # The tensor count is an upper bound of the count that the plan would give: refuse without building the plan
        raise ValueError(f"the FEM mesh would have about {nxy * n_planes_est} unknowns, more than the {FEM_MAX_UNKNOWNS} it accepts: "
                         + _coarser_cell(cell_mm, nxy * n_planes_est / FEM_MAX_UNKNOWNS))
    plan = _build_plan(problem, xn, yn, windows)
    Q = plan.quads.shape[0]
    warnings: List[str] = []
    # The open core of a hollow via: no element (the hole is empty and its wall adiabatic)
    open_core = np.zeros(Q, bool)
    for w in windows:
        v = problem.vias[w["via"]]
        radii, n_barrel, kind = _ring_radii(v, b.via_plating)
        if kind == "open":
            open_core |= (plan.via == w["via"]) & (plan.tag == 1)
    board_q = np.flatnonzero(plan.active & ~open_core)
    sets: Dict[object, np.ndarray] = {"board": board_q, "all": np.flatnonzero(plan.active)}
    # Blocks: the quads whose centroid is inside the polygon (the sides are break lines, so this is exact)
    cx, cy = plan.cx, plan.cy
    blks = []
    taken = {0: np.zeros(Q, bool), 1: np.zeros(Q, bool)}
    for face, ks in faces.items():
        for k in ks:
            s = problem.heatsinks[k]
            inside = geometry.points_in_polygon(cx, cy, np.asarray(s.polygon, float)) & plan.active
            ids = np.flatnonzero(inside)
            if ids.size == 0:
                continue
            if (taken[face] & inside).any():
                raise ValueError("the FEM does not accept two metal blocks that overlap on the same face")
            taken[face] |= inside
            sets[("blk", k)] = ids
            blks.append({"k": k, "face": face, "ids": ids, "n": n_blk[face], "dz_pad": max(s.interface_resistance(), 1e-7) * K_PAD, "dz_blk": s.thickness / n_blk[face]})
    # The z slabs from the top: top block slabs, the board, bottom block slabs
    zs = []
    top = [bk for bk in blks if bk["face"] == 0]
    bot = [bk for bk in blks if bk["face"] == 1]
    if top:
        zs += [{"kind": "blk", "layer": 0, "region": "blk", "face": 0, "slot": i} for i in range(n_blk[0])]
        zs.append({"kind": "pad", "layer": 0, "region": "blk", "face": 0, "slot": n_blk[0]})
    b0 = len(zs)
    for sl in board_slabs:
        for i in range(len(sl["dz"])):
            zs.append({"kind": sl["kind"], "layer": sl["layer"], "gap": sl["gap"], "region": "board", "dz": float(sl["dz"][i])})
    b1 = len(zs)
    if bot:
        zs.append({"kind": "pad", "layer": b.layers - 1, "region": "blk", "face": 1, "slot": 0})
        zs += [{"kind": "blk", "layer": b.layers - 1, "region": "blk", "face": 1, "slot": 1 + i} for i in range(n_blk[1])]
    n_planes = len(zs) + 1
    Np = plan.xy.shape[0]
    # Node usage by plane: a plane is used by the nodes of the quads of the slabs above and below it
    node_mask: Dict[object, np.ndarray] = {}

    def nodes_of(key):
        """!
        @brief Boolean mask over the plan nodes used by a region.
        @param key Region key in `sets`.
        @return numpy.ndarray (Np,) bool.
        """
        if key not in node_mask:
            m = np.zeros(Np, bool)
            m[plan.quads[sets[key]].ravel()] = True
            node_mask[key] = m
        return node_mask[key]

    def key_of(s, slab):
        """!
        @brief The regions (keys) of a slab: the board, or the blocks of its face.
        @param s Slab index.
        @param slab The slab dict.
        @return List of keys.
        """
        if slab["region"] == "board":
            return ["board"]
        return [("blk", bk["k"]) for bk in blks if bk["face"] == slab["face"]]

    nid = np.full((n_planes, Np), -1, np.int64)
    total = 0
    for p in range(n_planes):
        used = np.zeros(Np, bool)
        for s in (p - 1, p):
            if 0 <= s < len(zs):
                for key in key_of(s, zs[s]):
                    used |= nodes_of(key)
        nid[p, used] = total + np.arange(int(used.sum()))
        total += int(used.sum())
    if total > FEM_MAX_UNKNOWNS:
        raise ValueError(f"the FEM mesh has {total} unknowns, more than the {FEM_MAX_UNKNOWNS} it accepts: " + _coarser_cell(cell_mm, total / FEM_MAX_UNKNOWNS))
    # z of every node of every plane
    z = np.full((n_planes, Np), np.nan)
    zb = np.concatenate([[0.0], np.cumsum([s["dz"] for s in zs[b0:b1]])])
    for i, p in enumerate(range(b0, b1 + 1)):
        z[p, :] = zb[i]
    for face in (0, 1):
        for bk in [x for x in blks if x["face"] == face]:
            nodes = np.flatnonzero(nodes_of(("blk", bk["k"])))
            if face == 0:
                # From the board face upwards: the pad first, then the block slabs, thinner towards the outside
                zc = 0.0
                for p in range(b0 - 1, -1, -1):
                    slot_dz = bk["dz_pad"] if zs[p]["kind"] == "pad" else bk["dz_blk"]
                    zc -= slot_dz
                    _set_z(z, p, nodes, zc)
            else:
                zc = zb[-1]
                for p in range(b1 + 1, n_planes):
                    slot_dz = bk["dz_pad"] if zs[p - 1]["kind"] == "pad" else bk["dz_blk"]
                    zc += slot_dz
                    _set_z(z, p, nodes, zc)
    return _Layout(plan=plan, windows=windows, rods=rods, zs=zs, sets=sets, blocks=blks, b0=b0, b1=b1, n_planes=n_planes, nid=nid, z=z, n_unknowns=total,
                   open_core=open_core, warnings=warnings)


def _set_z(z, p, nodes, value):
    """!
    @brief Set the z of the nodes of a block plane, refusing two blocks that disagree on a shared node.
    @param z The z array (planes, nodes).
    @param p Plane index.
    @param nodes Plan node ids.
    @param value z in m.
    @return None.
    @throws ValueError If a node already has another z (touching blocks of different thickness).
    """
    cur = z[p, nodes]
    bad = np.isfinite(cur) & (np.abs(cur - value) > 1e-12)
    if bad.any():
        raise ValueError("the FEM needs touching metal blocks on one face to have the same thickness and interface (they share nodes)")
    z[p, nodes] = value


def unknowns(problem, cell_mm: float = 2.0, gap_elements: int = 6, refine: float = 2.0) -> Tuple[int, int, int, int]:
    """!
    @brief Number of unknowns of the FEM mesh of a problem, counted without building the 3D arrays.
    @details The same plan and slab layout as `build`, so the count is exactly the number of nodes of the mesh that `build` returns. It refuses, with the reason, what `build`
             refuses before it has a mesh (a slanted outline, too many break lines, a cell that is too fine, more than FEM_MAX_UNKNOWNS).
    @param problem A Problem.
    @param cell_mm Plan cell in mm (the coarse element).
    @param gap_elements Elements across every dielectric gap, count.
    @param refine Ratio of the cell to the fine element near the heaters and via patches.
    @return Tuple (unknowns, node planes, plan nodes along x - 1, plan nodes along y - 1) (the last two are the elements of the tensor grid).
    @throws ValueError With the reason, when no mesh can be built.
    """
    problem.validate()
    lay = _layout(problem, cell_mm, gap_elements, refine)
    return lay.n_unknowns, lay.n_planes, lay.plan.xn.size - 1, lay.plan.yn.size - 1


# ----------------------------------------------------------------------------------------------------------------------------------------
# Fill and shares per quad


def _crossed_quads(plan, poly):
    """!
    @brief The tensor quads whose open interior a polygon edge crosses.
    @param plan A Plan.
    @param poly Polygon vertices (n, 2) in m.
    @return numpy.ndarray of quad ids.
    """
    p = np.asarray(poly, float)
    q = np.roll(p, -1, axis=0)
    xn, yn = plan.xn, plan.yn
    nx, ny = xn.size - 1, yn.size - 1
    found = []
    for (xa, ya), (xb, yb) in zip(p, q):
        if xa == xb and ya == yb:
            continue
        i0 = int(np.clip(np.searchsorted(xn, min(xa, xb), side="right") - 1, 0, nx - 1))
        i1 = int(np.clip(np.searchsorted(xn, max(xa, xb), side="left"), 0, nx))
        j0 = int(np.clip(np.searchsorted(yn, min(ya, yb), side="right") - 1, 0, ny - 1))
        j1 = int(np.clip(np.searchsorted(yn, max(ya, yb), side="left"), 0, ny))
        i1, j1 = max(i1, i0 + 1), max(j1, j0 + 1)
        ids = plan.qid[j0:j1, i0:i1].ravel()
        ids = ids[ids >= 0]
        if ids.size == 0:
            continue
        # Liang-Barsky against the quad shrunk by 1e-9 m: a segment on a break line or touching a corner does not cross the interior
        e = 1e-9
        xl, xh = plan.x0[ids] + e, plan.x1[ids] - e
        yl, yh = plan.y0[ids] + e, plan.y1[ids] - e
        dx, dy = xb - xa, yb - ya
        t0 = np.zeros(ids.size)
        t1 = np.ones(ids.size)
        ok = np.ones(ids.size, bool)
        for d, a, lo, hi in ((dx, xa, xl, xh), (dy, ya, yl, yh)):
            if d == 0.0:
                ok &= (a > lo) & (a < hi)
            else:
                ta, tb = (lo - a) / d, (hi - a) / d
                t0 = np.maximum(t0, np.minimum(ta, tb))
                t1 = np.minimum(t1, np.maximum(ta, tb))
        ok &= t0 < t1 - 1e-12
        found.append(ids[ok])
    return np.unique(np.concatenate(found)) if found else np.zeros(0, np.int64)


def _poly_share(plan, poly):
    """!
    @brief The share of every plan quad that lies inside a polygon.
    @details A quad no polygon edge crosses is 1 or 0 by its centroid; a tensor quad that an edge crosses gets the exact overlap area (`geometry.polygon_overlap_area`); the quads of
             a via patch are 1 or 0 by their centroid (exact: no polygon edge crosses a via window, `_select_windows`).
    @param plan A Plan.
    @param poly Polygon vertices (n, 2) in m.
    @return numpy.ndarray (Q,) in [0, 1].
    """
    p = np.asarray(poly, float)
    out = np.zeros(plan.quads.shape[0])
    lo, hi = p.min(axis=0), p.max(axis=0)
    cand = np.flatnonzero((plan.x1 > lo[0]) & (plan.x0 < hi[0]) & (plan.y1 > lo[1]) & (plan.y0 < hi[1]))
    if cand.size == 0:
        return out
    out[cand] = geometry.points_in_polygon(plan.cx[cand], plan.cy[cand], p)
    for k in _crossed_quads(plan, p):
        r = np.array([[plan.x0[k], plan.y0[k]], [plan.x1[k], plan.y0[k]], [plan.x1[k], plan.y1[k]], [plan.x0[k], plan.y1[k]]])
        out[k] = min(geometry.polygon_overlap_area(p, r) / plan.area[k], 1.0)
    return out


def _zone_fill(plan, zones):
    """!
    @brief Copper fill of every plan quad from the zones of one layer: zones of the same fill add and are clipped to one, zones of different fills are taken from the largest down.
    @details The rule of `copper._zone_union`, on the quads of the plan instead of a uniform grid.
    @param plan A Plan.
    @param zones Zones of one layer.
    @return numpy.ndarray (Q,) in [0, 1].
    """
    groups: Dict[float, np.ndarray] = {}
    for z in zones:
        if len(z.polygon) < 3:
            continue
        g = groups.setdefault(float(z.fill), np.zeros(plan.quads.shape[0]))
        g += _poly_share(plan, z.polygon)
    share = np.zeros(plan.quads.shape[0])
    fill = np.zeros(plan.quads.shape[0])
    for f in sorted(groups, reverse=True):
        take = np.minimum(np.minimum(groups[f], 1.0), 1.0 - share)
        share += take
        fill += f * take
    return fill


def _raster_fill(plan, raster, pix, width, height):
    """!
    @brief Copper fill of every plan quad from an imported mask: the mean of the raster over the quad (exact for a tensor quad, the pixel of the centroid for a via patch).
    @param plan A Plan.
    @param raster uint8 coverage (rows from the top), 0..255.
    @param pix Pixel in m.
    @param width Board width in m.
    @param height Board height in m.
    @return numpy.ndarray (Q,) in [0, 1].
    """
    rows, cols = raster.shape
    flipped = raster[::-1].astype(np.float64)                      # rows from the bottom, at y = height - rows * pix
    integral = np.zeros((rows + 1, cols + 1))
    integral[1:, 1:] = flipped.cumsum(axis=0).cumsum(axis=1)
    y_base = height - rows * pix

    def corner(u, v):
        """!
        @brief Integral of the raster over [0, u] x [0, v] pixels (bilinear: the pixels are constant).
        @param u Position along x in pixels.
        @param v Position along y in pixels.
        @return numpy.ndarray.
        """
        u = np.clip(u, 0.0, cols)
        v = np.clip(v, 0.0, rows)
        iu = np.minimum(np.floor(u).astype(np.int64), cols - 1)
        iv = np.minimum(np.floor(v).astype(np.int64), rows - 1)
        fu, fv = u - iu, v - iv
        return ((1 - fu) * (1 - fv) * integral[iv, iu] + fu * (1 - fv) * integral[iv, iu + 1] + (1 - fu) * fv * integral[iv + 1, iu] + fu * fv * integral[iv + 1, iu + 1])

    tot = corner(plan.x1 / pix, (plan.y1 - y_base) / pix) - corner(plan.x0 / pix, (plan.y1 - y_base) / pix) - corner(plan.x1 / pix, (plan.y0 - y_base) / pix) \
        + corner(plan.x0 / pix, (plan.y0 - y_base) / pix)
    fill = tot / 255.0 / np.maximum((plan.x1 - plan.x0) * (plan.y1 - plan.y0) / (pix * pix), 1e-300)
    out = np.clip(fill, 0.0, 1.0)
    pr = ~plan.rect
    if pr.any():
        ju = np.clip((plan.cx[pr] / pix).astype(np.int64), 0, cols - 1)
        jv = np.clip(((plan.cy[pr] - y_base) / pix).astype(np.int64), 0, rows - 1)
        out[pr] = flipped[jv, ju] / 255.0
    return out


def _rod_fraction(problem, plan, via_index, a_via):
    """!
    @brief Spread the barrel area of a rod via over the plan quads under its drill: the share of the area of each quad that the barrel occupies.
    @param problem A Problem.
    @param plan A Plan.
    @param via_index Index of the via.
    @param a_via Copper-equivalent area of the barrel in m2.
    @return Tuple (quad ids, area fraction (n,)).
    """
    v = problem.vias[via_index]
    r = 0.5 * v.diameter
    rad = r * np.sqrt((np.arange(ROD_RINGS) + 0.5) / ROD_RINGS)
    ang = (np.arange(ROD_PER_RING) + 0.5) / ROD_PER_RING * 2.0 * math.pi
    px = np.concatenate([[v.x], (v.x + rad[:, None] * np.cos(ang)).ravel()])
    py = np.concatenate([[v.y], (v.y + rad[:, None] * np.sin(ang)).ravel()])
    ix = np.searchsorted(plan.xn, px, side="right") - 1
    iy = np.searchsorted(plan.yn, py, side="right") - 1
    nx, ny = plan.xn.size - 1, plan.yn.size - 1
    inb = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
    q = np.where(inb, plan.qid[np.clip(iy, 0, ny - 1), np.clip(ix, 0, nx - 1)], -1)
    q = q[(q >= 0)]
    q = q[plan.active[q]]
    if q.size == 0:
        return q, np.zeros(0)
    ids, cnt = np.unique(q, return_counts=True)
    return ids, np.minimum(a_via * cnt / px.size / plan.area[ids], 1.0)


# ----------------------------------------------------------------------------------------------------------------------------------------
# The model


def _h_on_quads(h, plan, width, height, default):
    """!
    @brief A film coefficient per plan quad from a scalar or an array on a regular grid of the board.
    @param h A number in W/m2K, or an array (ny, nx) on a regular grid of the board (rows from the bottom), or None for `default`.
    @param plan A Plan.
    @param width Board width in m.
    @param height Board height in m.
    @param default Value in W/m2K when h is None.
    @return numpy.ndarray (Q,) in W/m2K.
    """
    if h is None:
        return np.full(plan.quads.shape[0], float(default))
    a = np.asarray(h, float)
    if a.ndim == 0:
        return np.full(plan.quads.shape[0], float(a))
    ny, nx = a.shape
    ix = np.clip((plan.cx / width * nx).astype(np.int64), 0, nx - 1)
    iy = np.clip((plan.cy / height * ny).astype(np.int64), 0, ny - 1)
    return a[iy, ix]


def build(problem, cell_mm: float = 2.0, gap_elements: int = 6, refine: float = 2.0, h_top=None, h_bottom=None) -> FemMesh:
    """!
    @brief Build the finite-element model of a problem, or refuse with the reason.
    @details Materials per element (the 3D solid's rule where the geometry is not resolved: a copper slab of fill f has kx = f k_cu + (1 - f) k_lam, kz likewise with the
             through-thickness conductivity of the adjacent gaps), the barrel of a via as copper elements (a patch) or a rod added to kz (the others), the heaters as a volumetric
             source in the copper slabs of their layer with the exact area under the polygon, the films on the top and bottom faces (`h_top`, `h_bottom`, plus the `h_extra`
             of a plain heatsink under its polygon, none under a block), the edge film on every wall of the outline in every board slab, and the blocks with their pad, exposed
             face and walls (the fin ratio on the exposed face only, `blocks.exposed_h`, `blocks.wall_h`). The temperatures are rises over the ambient.
    @param problem A Problem.
    @param cell_mm Plan cell in mm (the coarse element; the fine element near the heaters is cell / refine).
    @param gap_elements Elements across every dielectric gap, count (2 to 24 in the options).
    @param refine Ratio of the cell to the fine element near the heaters and via patches, at least 1.
    @param h_top Top face coefficient in W/m2K: a number, an array (ny, nx) on a regular grid of the board, or None for `board.h_top` (the computed-h loop of `api` passes its arrays).
    @param h_bottom Bottom face coefficient, as h_top (None: `board.h_bottom`).
    @return FemMesh.
    @throws ValueError With the reason, when the mesh cannot be built or the problem is invalid.
    """
    problem.validate()
    lay = _layout(problem, cell_mm, gap_elements, refine)
    plan, zs, nid, zz = lay.plan, lay.zs, lay.nid, lay.z
    b = problem.board
    m = b.materials
    kcu = m.k_copper
    Q = plan.quads.shape[0]
    L = b.layers
    tc = np.asarray(b.copper_thickness, float)
    gaps = b.gap_thicknesses()
    g_kz, g_kip, _ = b.gap_properties()
    k_lam = b.layer_laminate()[0]
    kz_lam = np.array([float(np.dot([gaps[g] for g in a], [g_kz[g] for g in a]) / sum(gaps[g] for g in a)) if (a := [g for g in (l - 1, l) if 0 <= g < L - 1]) else m.k_fr4_through
                       for l in range(L)])
    warnings = list(lay.warnings)

    # --- Copper fill of every layer per plan quad (imported masks replace the zones of their layer)
    source = copper.CopperSource.of(problem)
    fill = np.zeros((L, Q))
    for l in range(L):
        if source is not None and l in source.layers:
            fill[l] = _raster_fill(plan, source.raster(l), source.pix, b.width, b.height)
        else:
            fill[l] = _zone_fill(plan, [z for z in problem.zones if z.layer == l])
    if source is not None:
        warnings.append("the FEM reads the imported copper as the mean of the mask over every element, as the 3D solid reads it per cell: on an imported board it is a different stencil, not a better answer")
    # --- Vias: patch quads carry the barrel; the others add their copper area to kz under the drill
    via_frac = np.zeros(Q)
    for k in lay.rods:
        # The samples of the drill that fall off the board are dropped by `_rod_fraction`, so they give the board share themselves: multiplying by `shares[k]` too counted it twice
        ids, frac = _rod_fraction(problem, plan, k, problem.vias[k].thermal_area(b.via_plating, kcu))
        via_frac[ids] += frac
    via_frac = np.minimum(via_frac, 1.0)
    if lay.rods:
        warnings.append(f"{len(lay.rods)} of {len(lay.rods) + len(lay.windows)} vias are a rod of the barrel area spread over the elements under the drill (no room for a conforming barrel)")

    # --- Elements and materials, slab by slab (the elements of one slab are contiguous: `ranges[s]` is their first and last id)
    elems, kx_l, kz_l, slab_of, quad_of, ranges = [], [], [], [], [], {}
    cursor = 0
    barrel_vias = {w["via"]: _ring_radii(problem.vias[w["via"]], b.via_plating)[2] for w in lay.windows}
    for s, sl in enumerate(zs):
        groups = []                                                # (quad ids, kx, kz) of the regions of this slab
        if sl["region"] == "board":
            ids = lay.sets["board"]
            if sl["kind"] == "cu":
                f = fill[sl["layer"]][ids]
                fe = np.minimum(f + via_frac[ids], 1.0)
                kx = f * kcu + (1.0 - f) * k_lam[sl["layer"]]
                kz = fe * kcu + (1.0 - fe) * (kz_lam[sl["layer"]] if L > 1 else m.k_fr4_through)
            else:
                if sl["gap"] >= 0:
                    kx = np.full(ids.size, float(g_kip[sl["gap"]]))
                    kzb = float(g_kz[sl["gap"]])
                else:
                    kx = np.full(ids.size, m.k_fr4_inplane)
                    kzb = m.k_fr4_through
                kz = via_frac[ids] * kcu + (1.0 - via_frac[ids]) * kzb
            # The barrel and the core of a patched via, over every board slab
            pt = plan.tag[ids]
            barrel = pt == 2
            kx = np.where(barrel, kcu, kx)
            kz = np.where(barrel, kcu, kz)
            core = pt == 1
            if core.any():
                for w_via, kind in barrel_vias.items():
                    sel = core & (plan.via[ids] == w_via)
                    if sel.any():
                        kf = kcu if kind == "solid" else problem.vias[w_via].fill_k
                        kx[sel] = kf
                        kz[sel] = kf
            groups.append((ids, kx, kz))
        else:
            # A block or pad slab: every block of the face (the node z already holds its own thickness)
            for bk in [x for x in lay.blocks if x["face"] == sl["face"]]:
                ids = lay.sets[("blk", bk["k"])]
                kk = K_PAD if sl["kind"] == "pad" else problem.heatsinks[bk["k"]].k
                groups.append((ids, np.full(ids.size, kk), np.full(ids.size, kk)))
        first_id = cursor
        for ids, kx, kz in groups:
            elems.append(np.hstack([nid[s][plan.quads[ids]], nid[s + 1][plan.quads[ids]]]))
            kx_l.append(kx)
            kz_l.append(kz)
            slab_of.append(np.full(ids.size, s))
            quad_of.append(ids)
            cursor += ids.size
        ranges[s] = (first_id, cursor)
    elems = np.vstack(elems)
    E = elems.shape[0]
    # Nodes: from the planes
    nodes = np.empty((lay.n_unknowns, 3))
    for p in range(lay.n_planes):
        sel = nid[p] >= 0
        pts = plan.xy[sel]
        zp = zz[p][sel]
        if not np.isfinite(zp).all():
            raise ValueError("internal: a node plane has no z (a block plane that no block owns)")
        nodes[nid[p][sel]] = np.column_stack([pts, zp])
    model = femcore.Model(nodes, elems)
    model.k[:, 0] = np.concatenate(kx_l)
    model.k[:, 1] = model.k[:, 0]
    model.k[:, 2] = np.concatenate(kz_l)
    elem_slab = np.concatenate(slab_of)
    elem_quad = np.concatenate(quad_of)
    copper_slabs = [[s for s, sl in enumerate(zs) if sl["kind"] == "cu" and sl["layer"] == l and sl["region"] == "board"] for l in range(L)]

    # --- Heaters: a volumetric source in the copper slabs of the layer, exact area under the polygon
    heater_elems = []
    cu_total = {l: sum(zs[s]["dz"] for s in copper_slabs[l]) for l in range(L)}
    # element offsets by slab for the board
    for h in problem.heaters:
        w = _poly_share(plan, h.polygon) * plan.area
        w = np.where(plan.active & ~lay.open_core, w, 0.0)
        tot = float(w.sum())
        if tot <= 0.0:
            # A part off the board: its power goes to the nearest board quad (the program's rule for the other models)
            bq = lay.sets["board"]
            c = geometry.polygon_centroid(h.polygon)
            k = bq[int(np.argmin((plan.cx[bq] - c[0]) ** 2 + (plan.cy[bq] - c[1]) ** 2))]
            w = np.zeros(Q)
            w[k] = plan.area[k]
            tot = float(w.sum())
            warnings.append(f"the heater {h.name or ''} has no area on the board: its power goes to the nearest element")
        ids_all = []
        # A thick outer copper layer (several slabs) takes the heat of a part through its face, as a prescribed flux over the footprint: the part sits on that face, and the
        # surface read-out of a thick plate (case 2 of Muzychka, Culham and Yovanovich, docs/validation.md 55) is the point of the model. A thin layer (one slab) keeps the
        # volumetric source: through 35 um the two differ by micro-kelvin, and the mesh and the frozen numbers of the boards of the harness do not change.
        slabs_l = copper_slabs[h.layer]
        if len(slabs_l) > 1 and (h.layer == 0 or h.layer == L - 1):
            top = h.layer == 0
            a, c = ranges[slabs_l[0] if top else slabs_l[-1]]
            q_s = elem_quad[a:c]
            share_q = w[q_s] / plan.area[q_s]
            sel = np.nonzero(share_q > 0)[0]
            nodes_f = elems[a:c][sel][:, :4] if top else elems[a:c][sel][:, 4:]
            model.add_faces(nodes_f, flux=h.power * share_q[sel] / tot, label="source")
            ids_all.append(a + sel)
            heater_elems.append(np.concatenate(ids_all))
            continue
        for s in slabs_l:
            a, c = ranges[s]
            ids_s = np.arange(a, c)
            q_s = elem_quad[a:c]
            share_q = w[q_s] / plan.area[q_s]
            model.q[ids_s] += h.power * share_q / (tot * cu_total[h.layer])
            ids_all.append(ids_s[share_q > 0])
        heater_elems.append(np.concatenate(ids_all) if ids_all else np.zeros(0, np.int64))

    # --- Films
    ht = _h_on_quads(h_top, plan, b.width, b.height, b.h_top)
    hb = _h_on_quads(h_bottom, plan, b.width, b.height, b.h_bottom)
    he_top, he_bot = np.zeros(Q), np.zeros(Q)
    for s in problem.heatsinks:
        if not s.is_block() and len(s.polygon) >= 3:
            (he_top if (s.layer == 0 or L == 1) else he_bot)[:] += s.h_extra * _poly_share(plan, s.polygon)
    covered = {0: np.zeros(Q, bool), 1: np.zeros(Q, bool)}
    for bk in lay.blocks:
        covered[bk["face"]][bk["ids"]] = True
    board_q = lay.sets["board"]
    top_plane, bot_plane = lay.b0, lay.b1
    sel = board_q[~covered[0][board_q]]
    hh = ht[sel] + he_top[sel]
    keep = hh > 0
    model.add_faces(nid[top_plane][plan.quads[sel[keep]]], h=hh[keep], label="top")
    sel = board_q[~covered[1][board_q]]
    hh = hb[sel] + he_bot[sel]
    keep = hh > 0
    model.add_faces(nid[bot_plane][plan.quads[sel[keep]]], h=hh[keep], label="bottom")
    # The edge film on every wall of the outline, in every board slab
    if b.h_side and b.h_side > 0:
        edges = _boundary_edges(plan.quads, lay.sets["all"])
        for s in range(lay.b0, lay.b1):
            f = np.column_stack([nid[s][edges[:, 0]], nid[s][edges[:, 1]], nid[s + 1][edges[:, 1]], nid[s + 1][edges[:, 0]]])
            model.add_faces(f, h=b.h_side, label="edge")
    # The blocks: the exposed face with the fin ratio, the walls without it, and nothing under the block (the board face is covered)
    for bk in lay.blocks:
        hs = problem.heatsinks[bk["k"]]
        face = bk["face"]
        ids = bk["ids"]
        h_face = ht[ids] if face == 0 else hb[ids]
        h_exp = np.array([blocks.exposed_h(hs, float(x)) for x in h_face])
        outer = 0 if face == 0 else len(zs)
        model.add_faces(nid[outer][plan.quads[ids]], h=h_exp, label="block_top" if face == 0 else "block_bottom")
        h_wall = float(blocks.wall_h(hs, float(np.mean(h_face))))
        edges = _boundary_edges(plan.quads, ids)
        # Only the real metal slabs have a wall in the air: the interface pad is a fictitious layer (its height is the contact resistance times K_PAD), so it carries no film
        slab_ids = [s for s, sl in enumerate(zs) if sl["region"] == "blk" and sl["face"] == face and sl["kind"] == "blk"]
        for s in slab_ids:
            f = np.column_stack([nid[s][edges[:, 0]], nid[s][edges[:, 1]], nid[s + 1][edges[:, 1]], nid[s + 1][edges[:, 0]]])
            model.add_faces(f, h=h_wall, label="block_top" if face == 0 else "block_bottom")
    vol = float(model.element_volumes()[np.isin(elem_slab, np.arange(lay.b0, lay.b1))].sum())
    return FemMesh(model=model, n_unknowns=lay.n_unknowns, n_elements=E, plan=plan, slabs=zs, planes=lay.n_planes, elem_slab=elem_slab, elem_quad=elem_quad,
                   copper_slabs=copper_slabs, heater_elems=heater_elems, warnings=warnings, n_patches=len(lay.windows), n_rods=len(lay.rods), volume_board=vol)
