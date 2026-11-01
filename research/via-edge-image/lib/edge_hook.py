#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file edge_hook.py
@brief Candidate corrections of the via well near a board edge, installed on `pcbthermal.viawell.build` in memory (the program is not edited).
@details Background. The mean-potential via (viawell.py) joins each plane to the barrel by a well of conductance G_c = 2 pi S / ln(r_eff / r_t). The lattice carries the sheet
         outside the footprint, edge included, but the footprint sits at the cell centres, not at the via: a 0.3 mm via 0.16 mm from the edge on a 1 mm cell has its true image
         at D_true = 0.32 mm and the grid image at D_lat = 1.0 mm. The well must carry the difference.
         Candidates (`mode`):
         * "program"  nothing (develop as it is);
         * "mirror"   insulated wall: c = ln(D_lat / D_true) per wall (+ the diagonal image at a corner), G_c = 2 pi S / (ln(r_eff / r_t) + c)   [the proposal of research/via-real-board];
         * "robin"    wall with an edge film: the image of a point source is a point image plus a line image with the density exp(-s / l) beyond the wall,
                      Phi(D) = ln D - (2 / l) int_0^inf exp(-s / l) ln(D + s) ds, l = S / (h_side slab) the length of the film (Phi = ln D for l -> inf, -ln D for l -> 0);
                      c = Phi_lat - Phi_true, the same operator applied to the lattice image of the footprint and to the true image of the via. Derived here (the half-plane Robin
                      Green function, checked in tests/test_edge_hook.py against the boundary condition); at a corner the single-wall terms are summed and the diagonal image
                      of the insulated case is added only when the film length exceeds 20 cells (otherwise the corner of a cooled edge is not treated).
         The footprint is the program's (`viawell.footprint`, restricted to the board); when c is so negative that the well would need a negative resistance the footprint is enlarged
         (smallest radius with ln(r_eff / r_t) + c > 0) instead of clipping the well to infinity. Walls: the box edges, or the axis-parallel segments of the outline within `reach` cells.
         FVM only (origin 0): the edge nodes of the FDM are half volumes and are left alone.
"""

import contextlib
import math

import numpy as np

from pcbthermal import viawell
from pcbthermal.geometry import cell_index_of_point

KAPPA = viawell.KAPPA
_GL_X, _GL_W = np.polynomial.laguerre.laggauss(24)                          # Gauss-Laguerre nodes for the line image
STATS = {"vias": 0, "edge_vias": 0, "enlarged": 0, "inf_wells": 0}


def lattice_log(di, dj, dx):
    """!
    @brief Lattice distance in logarithm units: ln dx + (pi / 2)(a(d) - kappa), the potential kernel read at real offsets (bilinear between the exact integer values).
    @param di Offset along rows in cells (array).
    @param dj Offset along columns in cells (array).
    @param dx Cell size in m.
    @return numpy.ndarray ln(distance / 1 m) in the lattice sense (asymptotically ln of the Euclidean distance).
    """
    di = np.asarray(di, dtype=float)
    dj = np.asarray(dj, dtype=float)
    i0, j0 = np.floor(di + 1e-9), np.floor(dj + 1e-9)
    fi, fj = di - i0, dj - j0
    i0, j0 = i0.astype(int), j0.astype(int)
    a = ((1 - fi) * (1 - fj) * viawell.lattice_kernel(i0, j0) + fi * (1 - fj) * viawell.lattice_kernel(i0 + 1, j0)
         + (1 - fi) * fj * viawell.lattice_kernel(i0, j0 + 1) + fi * fj * viawell.lattice_kernel(i0 + 1, j0 + 1))
    return math.log(dx) + math.pi / 2.0 * (a - KAPPA)


def walls_for(problem, v, reach):
    """!
    @brief The straight walls near a via: the box edges, or the axis-parallel outline segments, at most one per axis (the nearest).
    @param problem The Problem.
    @param v The Via.
    @param reach Largest distance from the via centre to a wall that counts, in m.
    @return list of (axis, position) with axis "x" or "y", positions in m (at most two).
    """
    b = problem.board
    cand = {"x": [], "y": []}
    if b.outline is None:
        cand["x"] = [0.0, b.width]
        cand["y"] = [0.0, b.height]
    else:
        pts = [(float(p[0]), float(p[1])) for p in b.outline]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            if abs(x1 - x0) < 1e-12 and min(y0, y1) - reach <= v.y <= max(y0, y1) + reach:
                cand["x"].append(x0)
            elif abs(y1 - y0) < 1e-12 and min(x0, x1) - reach <= v.x <= max(x0, x1) + reach:
                cand["y"].append(y0)
    out = []
    for axis, pos in (("x", v.x), ("y", v.y)):
        near = [(abs(pos - p), p) for p in cand[axis] if abs(pos - p) <= reach]
        if near:
            out.append((axis, min(near)[1]))
    return out


def _centres(w, dx):
    """!
    @brief Cell-centre coordinates of a footprint.
    @param w dict {(i, j): weight}.
    @param dx Cell size in m (cell-centred grid, origin 0).
    @return tuple (weights, X, Y) of arrays; X along columns, Y along rows.
    """
    keys = list(w)
    return (np.array([w[k] for k in keys]), (np.array([k[1] for k in keys]) + 0.5) * dx, (np.array([k[0] for k in keys]) + 0.5) * dx)


def phi_lattice(w, dx, wall, ell, via_side):
    """!
    @brief Image potential of the footprint at its own cells for one wall, lattice sense: ln D_lat for an insulated wall, with the line image for a film.
    @param w Footprint weights {(i, j): w}.
    @param dx Cell size in m.
    @param wall (axis, position) of the wall.
    @param ell Film length l = S / (h_side slab) in m (math.inf: insulated).
    @param via_side +1 when the board lies at larger coordinate than the wall (wall at the low side), -1 otherwise.
    @return float Phi_lat (logarithm units, metres).
    """
    wt, X, Y = _centres(w, dx)
    axis, p = wall
    Xi, Yi = (2 * p - X, Y) if axis == "x" else (X, 2 * p - Y)

    def mean_log(shift):
        """!
        @brief sum_ab w_a w_b lattice_log of the offsets between the cells and the images pushed `shift` metres beyond the wall.
        @param shift Distance beyond the wall in m.
        @return float.
        """
        xs, ys = (Xi - via_side * shift, Yi) if axis == "x" else (Xi, Yi - via_side * shift)
        return float(wt @ lattice_log((Y[:, None] - ys[None, :]) / dx, (X[:, None] - xs[None, :]) / dx, dx) @ wt)

    phi = mean_log(0.0)
    if math.isinf(ell):
        return phi
    line = float(sum(wg * mean_log(ell * t) for t, wg in zip(_GL_X, _GL_W)))          # int exp(-s/l) f(s) ds / l by Gauss-Laguerre
    return phi - 2.0 * line


def phi_true(delta, r_via, ell):
    """!
    @brief Image potential of the true via (a point image at 2 delta) for one wall.
    @param delta Distance of the via centre from the wall in m.
    @param r_via Drill radius in m (the distance is clipped at this value: a via cut by the edge).
    @param ell Film length in m (math.inf: insulated).
    @return float Phi_true.
    """
    d = 2.0 * max(delta, r_via)
    if math.isinf(ell):
        return math.log(d)
    return math.log(d) - 2.0 * float(sum(wg * math.log(d + ell * t) for t, wg in zip(_GL_X, _GL_W)))


def edge_term(w, dx, via_xy, r_via, walls, ells, mode):
    """!
    @brief The extra term c of the well for the walls near a via.
    @param w Footprint weights {(i, j): w}.
    @param dx Cell size in m.
    @param via_xy Via centre (x, y) in m.
    @param r_via Drill radius in m.
    @param walls list of (axis, position) from `walls_for`.
    @param ells Film length of the plane in m for each wall (math.inf: insulated); ignored in mode "mirror".
    @param mode "mirror" or "robin".
    @return float c = sum over the walls of Phi_lat - Phi_true, plus the diagonal image at a corner (insulated).
    """
    x, y = via_xy
    c = 0.0
    deltas = []
    for (axis, p), ell in zip(walls, ells):
        e = math.inf if mode == "mirror" else ell
        delta = abs((x if axis == "x" else y) - p)
        deltas.append(delta)
        side = 1.0 if (x if axis == "x" else y) > p else -1.0
        c += phi_lattice(w, dx, (axis, p), e, side) - phi_true(delta, r_via, e)
    if len(walls) == 2 and (mode == "mirror" or min(ells) > 20.0 * dx):
        # The diagonal image of a corner (insulated walls): the footprint mirrored about both walls
        wt, X, Y = _centres(w, dx)
        Xi, Yi = X, Y
        for axis, p in walls:
            Xi, Yi = (2 * p - Xi, Yi) if axis == "x" else (Xi, 2 * p - Yi)
        d = lattice_log((Y[:, None] - Yi[None, :]) / dx, (X[:, None] - Xi[None, :]) / dx, dx)
        c += float(wt @ d @ wt) - math.log(2.0 * max(math.hypot(*deltas), r_via))
    return c


def _enlarged(v_x, v_y, r_via, dx, origin, cover, dy, oy, need):
    """!
    @brief Smallest disc footprint (centre fixed, restricted to the board) whose effective radius is at least `need`.
    @param v_x Via centre x in m.
    @param v_y Via centre y in m.
    @param r_via Drill radius in m.
    @param dx Cell size in m.
    @param origin Lower x edge of cell 0 in m.
    @param cover Board share of every cell.
    @param dy Cell size in y in m.
    @param oy Lower y edge of row 0 in m.
    @param need Required effective radius in m.
    @return dict footprint weights.
    """
    h = math.sqrt(dx * dy)

    def make(radius):
        return viawell.restrict_to_board(viawell.disc_weights(v_x, v_y, radius, dx, origin, dy, oy), cover)

    lo, hi = r_via, 2.0 * r_via
    limit = max(cover.shape) * max(dx, dy)
    while viawell.effective_radius(make(hi), h) < need and hi < limit:
        lo, hi = hi, 2.0 * hi
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if viawell.effective_radius(make(mid), h) < need:
            lo = mid
        else:
            hi = mid
    return make(hi)


def build_edge(problem, d, S, cover, dx, dy, nx, ny, origin, active, mode="mirror", reach_cells=6.0):
    """!
    @brief `viawell.build` with the edge term in the wells; identical to the program's when no wall is near a via or mode is "program".
    @param problem The Problem.
    @param d Gap thicknesses in m.
    @param S Sheet conductances in W/K (L, ny, nx).
    @param cover Board share of every cell.
    @param dx Cell size in x in m.
    @param dy Cell size in y in m.
    @param nx Cells along x.
    @param ny Cells along y.
    @param origin Lower x edge of cell 0 in m (the correction acts only for 0).
    @param active Unused (as in the program).
    @param mode "mirror" or "robin".
    @param reach_cells Distance in cells within which a wall counts.
    @return tuple (blocks, gz_via) as `viawell.build`.
    """
    b = problem.board
    k_cu = b.materials.k_copper
    L = len(d) + 1
    slab = b.slab_thicknesses()
    hs = float(b.h_side or 0.0)
    blocks = []
    gz_via = np.zeros((L - 1, ny, nx))
    oy = origin * dy / dx
    for v, share in zip(problem.vias, problem.via_board_shares()):
        if share <= 0.0:
            continue
        STATS["vias"] += 1
        gv = k_cu * v.thermal_area(b.via_plating, k_cu) / d
        w, r_eff, r_t = viawell.footprint(v.x, v.y, v.diameter / 2.0, dx, origin, cover, dy, oy)
        if not w:
            continue
        ip, jp = cell_index_of_point(v.x - origin, v.y - oy, nx, ny, dx, dy)
        gz_via[:, ip, jp] += gv
        ic, jc = max(w, key=w.get)
        s_cell = [float(S[l, ic, jc]) / float(cover[ic, jc]) for l in range(L)]
        h = math.sqrt(dx * dy)
        walls = walls_for(problem, v, reach_cells * max(dx, dy)) if origin == 0.0 else []
        cs = [0.0] * L
        if walls:
            STATS["edge_vias"] += 1
            r_via = v.diameter / 2.0
            for _ in range(5):                                         # footprint and c depend on each other through the enlargement
                for l in range(L):
                    ell = math.inf if (mode == "mirror" or hs <= 0.0 or s_cell[l] <= 0) else s_cell[l] / (hs * slab[l])
                    cs[l] = edge_term(w, h, (v.x, v.y), r_via, walls, [ell] * len(walls), mode)
                worst = min(cs[l] for l in range(L) if s_cell[l] > 0) if any(s > 0 for s in s_cell) else 0.0
                if math.log(r_eff / r_t) + worst > 1e-9:
                    break
                w = _enlarged(v.x, v.y, r_via, dx, origin, cover, dy, oy, r_t * math.exp(-worst) * (1.0 + 1e-6))
                r_eff = viawell.effective_radius(w, h)
                ic, jc = max(w, key=w.get)
                s_cell = [float(S[l, ic, jc]) / float(cover[ic, jc]) for l in range(L)]
                STATS["enlarged"] += 1
        g_well = []
        for l in range(L):
            if s_cell[l] <= 0:
                g_well.append(0.0)
                continue
            den = math.log(r_eff / r_t) + cs[l]
            g_well.append(math.inf if den <= 1e-12 else 2.0 * math.pi * s_cell[l] / den)
        STATS["inf_wells"] += int(any(math.isinf(g) for g in g_well))
        keys = list(w)
        blocks.append((np.array([k[0] for k in keys]), np.array([k[1] for k in keys]), np.array([w[k] for k in keys]), viawell.kron_barrel(gv, g_well)))
    return blocks, gz_via


@contextlib.contextmanager
def patched(mode="mirror", **kw):
    """!
    @brief Install `build_edge` in place of `viawell.build` for the FVM and FDM networks built inside the block.
    @param mode "program" (no change), "mirror" or "robin".
    @param kw Further keywords of `build_edge` (reach_cells).
    @return Context manager; the counters of the last block are in STATS.
    """
    original = viawell.build
    STATS.update(vias=0, edge_vias=0, enlarged=0, inf_wells=0)
    if mode != "program":
        viawell.build = lambda *a, **k: build_edge(*a, mode=mode, **kw)
    try:
        yield
    finally:
        viawell.build = original
