#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file viawell.py
@brief Star treatment of a via barrel on the grid of the FVM and FDM networks (footprint, Peaceman wells calibrated on the lattice, Schur complement).

@details A via is one conductor. Instead of putting the barrel conductance of every gap in the cell that holds the via centre (a point link, which does not
converge when the cell is refined: the constriction at the point grows like ln(1/dx)), the barrel of each layer is an equipotential node that the sheet of the
layer reaches through a conductance to every cell of a footprint, g_a = c S w_a (a star, the barrel nodes of the layers joined by the barrel conductance of the
gaps). The barrel nodes are eliminated (Schur complement of a resistor network), which leaves a dense symmetric block M over the (layer, cell) unknowns of the
via: zero row sums, so no unknown is added and no heat is lost, symmetric positive semidefinite, and **every off-diagonal entry non-positive**, so K stays an
M-matrix (the maximum principle holds with vias, also where the copper covers only part of the footprint). The earlier treatment took the weighted MEAN of the
footprint temperatures (a prescribed flux w), whose couplings had positive entries and drew heat from bare cells that could not supply it (a cold spot).
The conductance c of the star is calibrated on the lattice (`star_scale`): a lone via in a uniform sheet keeps the resistance of the Peaceman well,
D = ln(h / r_t) / (2 pi S) from the distance h of one cell to the target radius, so the convergence of the point-via work (research/point-via-convergence) is kept.

* Footprint: the area of the disc of the via over the cells that are on the board (cover > 0), weighted by the cover and normalised; if its lattice
  effective radius r_eff is smaller than the target r_t = e^(-1/4) r_via (the radius of the uniform sink density of the layered idealisation) the disc is
  enlarged, centre fixed, until r_eff = r_t.
* Effective radius of a distribution w on the square lattice: ln(r_eff / dx) = (pi / 2) (E - kappa), E = sum_ab w_a w_b a(a - b), a the potential kernel of
  the five-point stencil (exact recurrence up to offset 12, asymptote beyond), kappa = (2 gamma + 3 ln 2) / pi.
* Weights of a layer: the geometric footprint when the sheet conductance per unit of board (the cover factor divided out) is the same on all its cells, otherwise
  the disc share times that conductance, renormalised and enlarged until its effective radius reaches the target, so a bare cell next to the barrel takes almost
  none of the heat but is still coupled through its own (small) conductance.

The research is in research/point-via-convergence (treatment, convergence), research/sor-with-via-couplings, research/via-real-board and research/via-partial-copper (the star).
* Edge image (FVM only): the lattice kernel has no image of a board edge, and the footprint sits at cell centres, not at the via, so a via within about one cell
  of a straight edge saw the image of the edge at the wrong distance (the via effect read +14.5 % high at 1 mm for a via 0.16 mm from the edge). The well
  gets the term K_ab = sum over the walls [ln D_lat(a, b') - ln D_true] (D_true = 2 max(distance, r_via) the distance to the mirror image of the via, D_lat the
  lattice distance from cell a to the mirror image of cell b) in the lattice potential of the calibration (`edge_kernel`); at a corner the diagonal image is added.
  For a flux equal to the weights this is the number c of the earlier mean-potential well (`edge_term`, still used to enlarge the footprint when c would need a
  negative resistance); the star's flux follows the cells that carry the heat, so the matrix is what composes. The mirror image
  is that of an insulated edge and is used also for a cooled edge (a Robin image was studied and is not worth its code: research/via-edge-image 3).
  Only the walls of `image_walls` are imaged: none within EDGE_GUARD_CELLS of a reflex corner or a short or slanted side, where the infinite mirror of a side
  that ends there overstates the wall (docs/validation.md 28.1).
@note Not covered cleanly by the image (`edge_via_indices` lists them for the warning): the FDM and the 3D solid, a cell of 2 mm or more (the image is applied,
      the via is a fraction of a cell), an outline with a slanted or curved side, a short step or a reflex corner near the via, a via whose centre is within its radius of the wall.
"""

import math

import numpy as np
from scipy.optimize import brentq

from .geometry import cell_index_of_point

EULER_GAMMA = 0.5772156649015329
KAPPA = (2.0 * EULER_GAMMA + 3.0 * math.log(2.0)) / math.pi        # asymptotic constant of the potential kernel of the five-point stencil
TARGET_RATIO = math.exp(-0.25)                                      # r_t / r_via: the radius of the uniform sink density over the disc of the via
POINT_SINK_RADIUS = math.exp(-math.pi * KAPPA / 2.0)               # equivalent radius of a point sink on the lattice, in cells (0.1985: the exact infinite-lattice value; Peaceman's radial argument gives exp(-pi/2) = 0.2079, Ibraguimov 2022, Theorem 1)
EDGE_REACH_CELLS = 6.0                                              # a wall counts when its distance from the via centre is at most this many cells
EDGE_GUARD_CELLS = 0.6                                              # no image when a reflex vertex, a slanted or a short side is nearer than this many cells (image_walls)
SAMPLES = 24                                                        # samples per cell side for the area of the disc


def kernel_table(n=12):
    """!
    @brief Exact values of the potential kernel a(x, y) of the five-point stencil for 0 <= x, y <= n (harmonic recurrence from the diagonal).
    @param n Largest offset in cells (dimensionless).
    @return numpy.ndarray of shape (n + 1, n + 1), symmetric, a[0, 0] = 0, a[1, 0] = 1.
    @note The forward recurrence amplifies rounding by about 6 per step; n = 12 keeps the error below 1e-6.
    """
    a = np.zeros((n + 2, n + 2))
    for k in range(1, n + 2):
        a[k, k] = 4.0 / math.pi * sum(1.0 / (2 * j - 1) for j in range(1, k + 1))      # exact diagonal values
    a[1, 0] = a[0, 1] = 1.0
    for m in range(1, n + 1):
        # a(m+1, m) from the harmonic equation at the diagonal node (m, m)
        a[m + 1, m] = a[m, m + 1] = 2.0 * a[m, m] - a[m, m - 1]
        for y in range(m - 1, -1, -1):
            # harmonic at (m, y), with a(m, -1) = a(m, 1) by symmetry
            ym = a[m, y - 1] if y > 0 else a[m, 1]
            a[m + 1, y] = a[y, m + 1] = 4.0 * a[m, y] - a[m - 1, y] - a[m, y + 1] - ym
    return a[:n + 1, :n + 1]


_TABLE = kernel_table(12)


def lattice_kernel(dx, dy):
    """!
    @brief Potential kernel at integer offsets, exact in the table and asymptotic beyond it.
    @param dx Offset in cells along x (integer or integer array, dimensionless).
    @param dy Offset in cells along y (integer or integer array, dimensionless).
    @return float or numpy.ndarray The kernel value a(dx, dy).
    """
    x, y = np.abs(np.asarray(dx)), np.abs(np.asarray(dy))
    n = _TABLE.shape[0] - 1
    inside = (x <= n) & (y <= n)
    far = (2.0 / math.pi) * np.log(np.maximum(np.hypot(x, y), 1.0)) + KAPPA     # error O(r^-2): below 1e-3 beyond r = 12
    return np.where(inside, _TABLE[np.minimum(x, n), np.minimum(y, n)], far)


def effective_radius(weights, dx):
    """!
    @brief Effective radius of a distributed sink on the lattice (the mean-potential sense).
    @param weights dict {(i, j): w} with weights that sum to 1.
    @param dx Cell size in m.
    @return float r_eff in m, ln(r_eff / dx) = (pi / 2)(E - kappa).
    """
    keys = np.array(list(weights), dtype=int)
    w = np.array(list(weights.values()), dtype=float)
    d = keys[:, None, :] - keys[None, :, :]
    e = float(w @ lattice_kernel(d[..., 0], d[..., 1]) @ w)
    return dx * math.exp(math.pi / 2.0 * (e - KAPPA))


def disc_weights(cx, cy, radius, dx, origin=0.0, dy=None, origin_y=None):
    """!
    @brief Area of a disc inside each cell of a grid, as weights that sum to 1 (a point when the disc is smaller than the sampling).
    @param cx Centre x in m.
    @param cy Centre y in m.
    @param radius Radius in m (0 = a point).
    @param dx Cell size along x in m.
    @param origin Lower x edge of cell 0 in m (0 for cell-centred volumes, -dx/2 for node-centred control volumes).
    @param dy Cell size along y in m (None = dx). The grid is round(W / cell) by round(H / cell), so dy differs from dx when the two sides do not round
           alike (60 x 41 mm at 2 mm: dy = 2.05 mm); reading the rows with dx put the footprint up to one cell away from the via.
    @param origin_y Lower y edge of row 0 in m (None = origin scaled by dy / dx, so -dy/2 for node-centred control volumes).
    @return dict {(i, j): weight}; i is the row (y), j the column (x). Indices may fall outside the grid.
    """
    dy = dx if dy is None else dy
    oy = origin * dy / dx if origin_y is None else origin_y
    point = {(int(math.floor((cy - oy) / dy)), int(math.floor((cx - origin) / dx))): 1.0}
    if radius <= 1e-12 * min(dx, dy):
        return point
    j0, i0 = int(math.floor((cx - radius - origin) / dx)), int(math.floor((cy - radius - oy) / dy))
    j1, i1 = int(math.floor((cx + radius - origin) / dx)), int(math.floor((cy + radius - oy) / dy))
    # One sample grid for the whole window: SAMPLES points per cell side, reshaped to (cells, SAMPLES)
    s = (np.arange(SAMPLES) + 0.5) / SAMPLES
    xs = origin + (np.arange(j0, j1 + 1)[:, None] + s[None, :]) * dx
    ys = oy + (np.arange(i0, i1 + 1)[:, None] + s[None, :]) * dy
    inside = (xs[None, :, None, :] - cx) ** 2 + (ys[:, None, :, None] - cy) ** 2 <= radius ** 2      # (rows, cols, sy, sx)
    share = inside.mean(axis=(2, 3))
    out = {(i0 + a, j0 + c): float(share[a, c]) for a, c in zip(*np.nonzero(share > 0))}
    if not out:
        return point
    tot = sum(out.values())
    return {k: v / tot for k, v in out.items()}


def restrict_to_board(weights, cover):
    """!
    @brief Keep the cells that are on the board, weighted by their cover, and renormalise.
    @param weights dict {(i, j): w}.
    @param cover Array (ny, nx) of the share of every cell that is board (dimensionless; ones for a rectangle).
    @return dict {(i, j): w} with weights that sum to 1, empty when no cell is on the board.
    """
    ny, nx = cover.shape
    out = {k: w * float(cover[k]) for k, w in weights.items() if 0 <= k[0] < ny and 0 <= k[1] < nx and cover[k] > 0}
    tot = sum(out.values())
    return {k: v / tot for k, v in out.items()} if tot > 0 else {}


def enlarged_footprint(cx, cy, r_via, dx, origin, cover, dy, origin_y, need, rel=None):
    """!
    @brief Smallest disc footprint (centre fixed, restricted to the board) whose lattice effective radius is at least `need`.
    @param cx Via centre x in m.
    @param cy Via centre y in m.
    @param r_via Drill radius in m.
    @param dx Cell size in m.
    @param origin Lower x edge of cell 0 in m.
    @param cover Array (ny, nx) of the board share of each cell (dimensionless).
    @param dy Cell size along y in m.
    @param origin_y Lower y edge of row 0 in m.
    @param need Required effective radius in m.
    @param rel Optional array (ny, nx) of the sheet conductance per unit of board of a layer (any scale, W/K): the weight of a cell is the share of the disc
           times rel, renormalised (cells that cannot carry the heat get almost none of it); None = the share of the disc alone.
    @return dict {(i, j): w} (the disc radius is found by bisection after a doubling search bounded by the board size).
    """
    h = math.sqrt(dx * dy)

    def make(radius):
        """!
        @brief Footprint weights of a disc of a given radius.
        @param radius Disc radius in m.
        @return dict {(i, j): w}, possibly empty.
        """
        g = restrict_to_board(disc_weights(cx, cy, radius, dx, origin, dy, origin_y), cover)
        if rel is None:
            return g
        g = {k: x * float(rel[k]) for k, x in g.items() if rel[k] > 0.0}
        tot = sum(g.values())
        return {k: x / tot for k, x in g.items()} if tot > 0.0 else {}

    def reach(radius):
        """!
        @brief Effective radius of the footprint of a given disc (0 when it is empty).
        @param radius Disc radius in m.
        @return float r_eff in m.
        """
        wr = make(radius)
        return effective_radius(wr, h) if wr else 0.0

    limit = max(cover.shape) * max(dx, dy)
    lo, hi = r_via, 2.0 * r_via
    while reach(hi) < need and hi < limit:
        lo, hi = hi, 2.0 * hi
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if reach(mid) < need:
            lo = mid
        else:
            hi = mid
    return make(hi)


def footprint(cx, cy, r_via, dx, origin, cover, dy=None, origin_y=None):
    """!
    @brief Footprint of a via: the disc of the via on the cells of the board, enlarged (centre fixed) until its effective radius reaches the target.
    @param cx Via centre x in m.
    @param cy Via centre y in m.
    @param r_via Drill radius in m.
    @param dx Cell size in m.
    @param origin Lower edge of cell 0 in m.
    @param cover Array (ny, nx) of the board share of each cell (dimensionless).
    @param dy Cell size along y in m (None = dx; see disc_weights).
    @param origin_y Lower y edge of row 0 in m (None = origin scaled by dy / dx).
    @return Tuple (weights, r_eff, r_target): dict {(i, j): w} (empty when the via has no cell on the board), effective radius in m and target radius in m.
    """
    r_t = TARGET_RATIO * r_via
    dy = dx if dy is None else dy
    h = math.sqrt(dx * dy)                     # lattice spacing of the effective radius (the kernel is that of square cells; dy / dx is 1 +- 1 / (2 n))
    w = restrict_to_board(disc_weights(cx, cy, r_via, dx, origin, dy, origin_y), cover)
    if not w:
        return {}, 0.0, r_t
    r_eff = effective_radius(w, h)
    if r_eff >= r_t:
        return w, r_eff, r_t
    # Enlarge the disc until the lattice effective radius equals the target (r_eff grows with the radius); the size of the board bounds the search
    w = enlarged_footprint(cx, cy, r_via, dx, origin, cover, dy, origin_y, r_t)
    return w, effective_radius(w, h), r_t


def lattice_log(di, dj, h):
    """!
    @brief Lattice distance in logarithm units, ln h + (pi / 2)(a(d) - kappa), the potential kernel read at real offsets (bilinear between the exact integer values).
    @param di Offset along rows in cells (array, dimensionless).
    @param dj Offset along columns in cells (array, dimensionless).
    @param h Cell size in m.
    @return numpy.ndarray ln(distance / 1 m) in the lattice sense (asymptotically the logarithm of the Euclidean distance).
    """
    di = np.asarray(di, dtype=float)
    dj = np.asarray(dj, dtype=float)
    i0, j0 = np.floor(di + 1e-9), np.floor(dj + 1e-9)          # the tolerance keeps an offset that is an integer up to rounding on its own node
    fi, fj = di - i0, dj - j0
    i0, j0 = i0.astype(int), j0.astype(int)
    a = ((1 - fi) * (1 - fj) * lattice_kernel(i0, j0) + fi * (1 - fj) * lattice_kernel(i0 + 1, j0)
         + (1 - fi) * fj * lattice_kernel(i0, j0 + 1) + fi * fj * lattice_kernel(i0 + 1, j0 + 1))
    return math.log(h) + math.pi / 2.0 * (a - KAPPA)


def edge_walls(problem, v, reach):
    """!
    @brief The straight walls near a via: the box edges, or the axis-parallel outline segments, at most one per axis (the nearest).
    @param problem The Problem.
    @param v The Via (x, y in m).
    @param reach Largest distance from the via centre to a wall that counts, in m.
    @return Tuple (walls, clean): walls is a list of (axis, position) with axis "x" or "y" and the position in m (at most two); clean is False when the
            outline has a slanted, curved or short (shorter than `reach`) side, or a corner that the walls do not describe, within `reach` of the via
            (then the image is incomplete and the warning stays).
    @note On an outline a segment counts only when the via projects inside it; a reflex corner (a T, an L) is therefore never closed by an image of the
          missing side, and a via near a vertex that is not a convex corner of two found walls is reported as not clean.
    """
    walls, bad = edge_scan(problem, v, reach)
    return walls, bad > reach


def image_walls(problem, v, reach, cell):
    """!
    @brief The walls whose mirror image the well of a via gets (`build`): the walls of `edge_scan` that are nearer to the via than every feature that is not
           a straight wall, and none when such a feature is within `EDGE_GUARD_CELLS` cells of the via.
    @details Next to a reflex corner (a T, an L) the side the via faces ends at the corner, so its infinite mirror overstates the wall: measured against a
             resolved reference (`docs/validation.md` 28.1) the image put a via 0.26 mm from the reflex corner of an inverted T at -13.5 % (1 mm cell) against
             -2.9 % without it, and a via whose near side was too short to count got the image of a farther side behind it (+1 to +2 points worse). The guard
             removes those cases; the warning stays for every via that is not clean (`edge_walls`).
    @param problem The Problem.
    @param v The Via (x, y in m).
    @param reach Largest distance from the via centre to a wall that counts, in m.
    @param cell Cell size in m (the larger of dx and dy).
    @return list of (axis, position) as in `edge_walls` (possibly empty).
    """
    walls, bad = edge_scan(problem, v, reach)
    if bad < EDGE_GUARD_CELLS * cell:
        return []
    pos = {"x": v.x, "y": v.y}
    return [(a, q) for a, q in walls if abs(pos[a] - q) < bad]


def edge_scan(problem, v, reach):
    """!
    @brief The straight walls near a via and the distance to the nearest feature of the outline that is not one (shared by `edge_walls` and `image_walls`).
    @param problem The Problem.
    @param v The Via (x, y in m).
    @param reach Largest distance from the via centre to a wall or a feature that counts, in m.
    @return Tuple (walls, bad): walls as in `edge_walls`; bad is the distance in m from the via centre to the nearest slanted, curved or short side, side
            beyond whose end the via projects, or vertex that is not the convex corner of the two walls found, within `reach` (math.inf when there is none).
    """
    b = problem.board
    if not b.has_outline():
        # A rectangle: the four sides, always long enough
        cand = {"x": [0.0, b.width], "y": [0.0, b.height]}
        pos = {"x": v.x, "y": v.y}
        out = []
        for axis in ("x", "y"):
            near = [(abs(pos[axis] - p), p) for p in cand[axis] if abs(pos[axis] - p) <= reach]
            if near:
                out.append((axis, min(near)[1]))
        return out, math.inf
    pts = [(float(p[0]), float(p[1])) for p in b.outline]
    cand = {"x": [], "y": []}
    bad = math.inf
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        # Distance from the via centre to the segment
        sx, sy = x1 - x0, y1 - y0
        ln2 = sx * sx + sy * sy
        t = 0.0 if ln2 == 0.0 else min(max(((v.x - x0) * sx + (v.y - y0) * sy) / ln2, 0.0), 1.0)
        dist = math.hypot(v.x - (x0 + t * sx), v.y - (y0 + t * sy))
        if dist > reach:
            continue
        if abs(sx) < 1e-12 and abs(sy) >= reach and min(y0, y1) <= v.y <= max(y0, y1):
            cand["x"].append(x0)
        elif abs(sy) < 1e-12 and abs(sx) >= reach and min(x0, x1) <= v.x <= max(x0, x1):
            cand["y"].append(y0)
        else:
            bad = min(bad, dist)                # slanted, curved (many short sides), a short step, or the via projects beyond the end of the side
    out = []
    for axis, pos in (("x", v.x), ("y", v.y)):
        near = [(abs(pos - p), p) for p in cand[axis] if abs(pos - p) <= reach]
        if near:
            out.append((axis, min(near)[1]))
    # A vertex within reach must be a convex corner of the two walls found (the walls meet exactly there)
    found = dict(out)
    for (x, y) in pts:
        dv = math.hypot(v.x - x, v.y - y)
        if dv <= reach and not (len(out) == 2 and abs(found["x"] - x) < 1e-12 and abs(found["y"] - y) < 1e-12):
            bad = min(bad, dv)
    return out, bad


def edge_term(w, dx, dy, via_xy, r_via, walls):
    """!
    @brief The extra logarithm c of the well for the mirror images of the straight walls near a via.
    @param w Footprint weights {(i, j): w} (cell-centred grid, origin 0).
    @param dx Cell size in x in m.
    @param dy Cell size in y in m.
    @param via_xy Via centre (x, y) in m.
    @param r_via Drill radius in m.
    @param walls list of (axis, position) from `edge_walls`.
    @return float c = sum over the walls of [mean lattice log of the footprint to its own mirror image - ln(2 max(distance, r_via))], plus the same difference
            for the diagonal image when there are two walls (a corner). Positive when the lattice image is farther than the true one.
    """
    h = math.sqrt(dx * dy)
    keys = list(w)
    wt = np.array([w[k] for k in keys])
    X = (np.array([k[1] for k in keys]) + 0.5) * dx
    Y = (np.array([k[0] for k in keys]) + 0.5) * dy

    def mean_log(Xi, Yi):
        """!
        @brief Mean lattice log between the footprint cells and an image of the footprint.
        @param Xi Image x of every cell in m.
        @param Yi Image y of every cell in m.
        @return float sum_ab w_a w_b ln(lattice distance).
        """
        return float(wt @ lattice_log((Y[:, None] - Yi[None, :]) / h, (X[:, None] - Xi[None, :]) / h, h) @ wt)

    c = 0.0
    deltas = []
    Xd, Yd = X, Y
    for axis, p in walls:
        delta = abs((via_xy[0] if axis == "x" else via_xy[1]) - p)
        deltas.append(delta)
        Xi, Yi = (2.0 * p - X, Y) if axis == "x" else (X, 2.0 * p - Y)
        c += mean_log(Xi, Yi) - math.log(2.0 * max(delta, r_via))
        Xd, Yd = (2.0 * p - Xd, Yd) if axis == "x" else (Xd, 2.0 * p - Yd)
    if len(walls) == 2:
        # The diagonal image of a corner: the footprint mirrored about both walls
        c += mean_log(Xd, Yd) - math.log(2.0 * max(math.hypot(*deltas), r_via))
    return c


def edge_kernel(keys, dx, dy, via_xy, r_via, walls):
    """!
    @brief The edge term as a matrix over the cells of a footprint: K[a, b] such that sum_ab w_a w_b K[a, b] = `edge_term`.
    @details K[a, b] = sum over the walls of [lattice log from cell a to the mirror image of cell b - ln(2 max(distance, r_via))] (+ the diagonal image at a corner):
             how much more resistive than the true image the lattice image is for a flux that goes in at b and is read at a. The star coupling needs the matrix because
             its flux is not the weight w (it follows the cells that carry the heat), where the mean-potential well had a prescribed flux and needed only the number.
    @param keys List of the (i, j) cells of the footprint (cell-centred grid, origin 0).
    @param dx Cell size in x in m.
    @param dy Cell size in y in m.
    @param via_xy Via centre (x, y) in m.
    @param r_via Drill radius in m.
    @param walls list of (axis, position) from `edge_walls` / `image_walls`.
    @return numpy.ndarray (n, n) in logarithm units (dimensionless).
    """
    h = math.sqrt(dx * dy)
    X = (np.array([k[1] for k in keys]) + 0.5) * dx
    Y = (np.array([k[0] for k in keys]) + 0.5) * dy
    K = np.zeros((len(keys), len(keys)))
    deltas = []
    Xd, Yd = X, Y
    for axis, p in walls:
        delta = abs((via_xy[0] if axis == "x" else via_xy[1]) - p)
        deltas.append(delta)
        Xi, Yi = (2.0 * p - X, Y) if axis == "x" else (X, 2.0 * p - Y)
        K += lattice_log((Y[:, None] - Yi[None, :]) / h, (X[:, None] - Xi[None, :]) / h, h) - math.log(2.0 * max(delta, r_via))
        Xd, Yd = (2.0 * p - Xd, Yd) if axis == "x" else (Xd, 2.0 * p - Yd)
    if len(walls) == 2:
        K += lattice_log((Y[:, None] - Yd[None, :]) / h, (X[:, None] - Xd[None, :]) / h, h) - math.log(2.0 * max(math.hypot(*deltas), r_via))
    return K


def tuned_footprint(cx, cy, r_via, dx, origin, cover, dy=None, origin_y=None):
    """!
    @brief Footprint of a via for the 3D solid, whose cells carry the copper area of the barrel (no well): the weights whose effective radius equals 0.78 r_via.
    @details The point in the cell of the centre is mixed with the area weights of the disc of radius r_t = 0.78 r_via, with the share beta that gives
             r_eff = r_t (r_eff grows with beta); when even the pure disc is below r_t (fine cells, where uniform area weights have a radius e^(-1/4) times
             that of the circle) the disc is enlarged until r_eff = r_t. A point when r_t is below the radius of a point sink on this grid (a coarse cell).
             Measured on the 3 x 3 board (research/point-via-convergence, README 6): the gain of a copper fill is within 0.3 K of the fine-grid value
             from 1 to 0.17 mm; the plain disc footprint is not enough (it has no well and leaves -5.29 K at 0.5 mm).
    @param cx Via centre x in m.
    @param cy Via centre y in m.
    @param r_via Drill radius in m.
    @param dx Cell size in m.
    @param origin Lower edge of cell 0 in m.
    @param cover Array (ny, nx) of the board share of each cell (dimensionless).
    @param dy Cell size along y in m (None = dx; see disc_weights).
    @param origin_y Lower y edge of row 0 in m (None = origin scaled by dy / dx).
    @return dict {(i, j): w} with weights that sum to 1; the cell of the centre alone when no refinement applies (the board part of the drill disc when
            that cell is off the board); empty when the drill disc has no cell on the board (the via conducts nothing).
    """
    r_t = TARGET_RATIO * r_via
    ny, nx = cover.shape
    dy = dx if dy is None else dy
    oy = origin * dy / dx if origin_y is None else origin_y
    h = math.sqrt(dx * dy)                     # lattice spacing of the effective radius (see footprint)
    point = {(min(max(int(math.floor((cy - oy) / dy)), 0), ny - 1), min(max(int(math.floor((cx - origin) / dx)), 0), nx - 1)): 1.0}
    on_board = restrict_to_board(disc_weights(cx, cy, r_via, dx, origin, dy, oy), cover)
    if not on_board:
        return {}                              # No cell of the board under the drill disc: the via conducts nothing
    if cover[next(iter(point))] <= 0.0:
        # The centre is off the board but part of the disc is on it: the fallback is the board part of the drill disc, never a cell off the board
        # (the point cell is off the board and its copper would be lost, while the FVM and FDM keep the via)
        point = on_board
    if r_t <= POINT_SINK_RADIUS * h:
        return point
    w_pt = disc_weights(cx, cy, 0.0, dx, origin, dy, oy)

    def make(radius, beta=1.0):
        w_ar = disc_weights(cx, cy, radius, dx, origin, dy, oy)
        mix = {}
        for k, v in w_pt.items():
            mix[k] = mix.get(k, 0.0) + (1.0 - beta) * v
        for k, v in w_ar.items():
            mix[k] = mix.get(k, 0.0) + beta * v
        return restrict_to_board(mix, cover)

    w = make(r_t)
    if not w:
        return point
    if effective_radius(w, h) >= r_t:
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            wm = make(r_t, mid)
            if wm and effective_radius(wm, h) < r_t:
                lo = mid
            else:
                hi = mid
        return make(r_t, 0.5 * (lo + hi)) or point
    limit = max(cover.shape) * max(dx, dy)
    lo, hi = r_t, 2.0 * r_t
    while effective_radius(make(hi), h) < r_t and hi < limit:
        lo, hi = hi, 2.0 * hi
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if effective_radius(make(mid), h) < r_t:
            lo = mid
        else:
            hi = mid
    return make(hi)


def well_conductance(s_sheet, r_eff, r_t, c=0.0):
    """!
    @brief Peaceman well conductance between the footprint mean and the barrel.
    @param s_sheet Sheet conductance of the layer at the via in W/K.
    @param r_eff Effective radius of the footprint in m.
    @param r_t Target radius of the barrel in m.
    @param c Edge term of the well in logarithm units (dimensionless, see `edge_term`; 0 away from an edge, where the result is that of the earlier versions bit for bit).
    @return float 2 pi S / (ln(r_eff / r_t) + c) in W/K, infinite when the denominator is not positive.
    """
    if c == 0.0:
        if r_eff <= r_t * (1.0 + 1e-9):
            return math.inf
        return 2.0 * math.pi * s_sheet / math.log(r_eff / r_t)
    den = math.log(r_eff / r_t) + c
    return math.inf if den <= 1e-9 else 2.0 * math.pi * s_sheet / den


def kron_barrel(g_gap, g_well):
    """!
    @brief Conductances between the layer means joined by a barrel with wells (the barrel nodes eliminated).
    @param g_gap Array (L-1,) of the barrel conductance of every gap in W/K.
    @param g_well Array (L,) of the well conductance of every layer in W/K (0 = no contact, inf = the mean is the barrel potential).
    @return numpy.ndarray (L, L) of the conductances G[l, m] (symmetric, zero diagonal) in W/K.
    """
    g_gap = np.asarray(g_gap, dtype=float)
    g_well = np.asarray(g_well, dtype=float)
    n = len(g_well)
    if np.isinf(g_well).any():
        # An infinite well: replace it by a conductance far above every other one in the star (the Schur complement then ties the mean to the barrel)
        finite = g_well[np.isfinite(g_well)]
        ref = max(float(finite.max()) if finite.size else 0.0, float(g_gap.max()) if g_gap.size else 1.0)
        g_well = np.where(np.isinf(g_well), 1e12 * ref, g_well)
    # Nodal matrix of the star: [layer means 0..n-1, barrel nodes n..2n-1]; the means are kept
    Y = np.zeros((2 * n, 2 * n))

    def link(a, b, g):
        Y[a, a] += g
        Y[b, b] += g
        Y[a, b] -= g
        Y[b, a] -= g

    for l in range(n):
        link(l, n + l, g_well[l])
    for k in range(n - 1):
        link(n + k, n + k + 1, g_gap[k])
    Yss, Ysb, Ybb = Y[:n, :n], Y[:n, n:], Y[n:, n:]
    G = -(Yss - Ysb @ np.linalg.solve(Ybb + 1e-300 * np.eye(n), Ysb.T))
    np.fill_diagonal(G, 0.0)
    G[G < 1e-14 * max(float(G.max()), 1e-300)] = 0.0                  # rounding of the elimination
    return G


STAR_CAP = 1e6                                                      # total conductance of the star over S when the footprint alone is already resistive enough (nearly an equipotential)
_STAR_CACHE = {}                                                    # dimensionless star scales by footprint shape (see star_scale)
_STAR_CACHE_MAX = 20000


class Block:
    """!
    @brief The coupling of one via: it unpacks like the earlier 4-tuple (rows, cols, w, G) and carries the dense coupling over its (layer, cell) pairs.
    """

    def __init__(self, layer_cells, M, G):
        """!
        @brief Store the coupling of one via.
        @param layer_cells List over the board layers of integer arrays (n_l, 2) of the (row, col) cells joined to the barrel in that layer (possibly empty).
        @param M Dense symmetric matrix (n, n) in W/K over the concatenated (layer, cell) pairs, zero row sums, non-positive off-diagonal entries.
        @param G Array (L, L) of the total conductance between the cells of two layers, -sum M[a, b] over a in l, b in m, in W/K.
        """
        self.layer_cells, self.M, self.G = layer_cells, M, G
        union = sorted({(int(c[0]), int(c[1])) for cells in layer_cells for c in cells})
        self.rows = np.array([c[0] for c in union], dtype=int)
        self.cols = np.array([c[1] for c in union], dtype=int)
        self.w = np.full(len(union), 1.0 / max(len(union), 1))         # informative: the union is shared out equally (each layer has its own weights in M)

    def __iter__(self):
        """!
        @brief Unpack as (rows, cols, w, G) like the earlier tuple of the mean-potential treatment.
        @return iterator over (rows, cols, w, G): the union of the cells, equal weights on it, the layer-to-layer conductances.
        """
        return iter((self.rows, self.cols, self.w, self.G))

    def __getitem__(self, i):
        """!
        @brief Index like the earlier 4-tuple.
        @param i Position 0 to 3 (rows, cols, w, G).
        @return The element.
        """
        return (self.rows, self.cols, self.w, self.G)[i]

    def flat(self, idx):
        """!
        @brief Indices of the (layer, cell) pairs of the block in the unknowns.
        @param idx Index array (layers, ny, nx) of the unknowns.
        @return numpy.ndarray of integers, in the order of the rows of `M`.
        """
        parts = [idx[l][c[:, 0], c[:, 1]] for l, c in enumerate(self.layer_cells) if len(c)]
        return np.concatenate(parts) if parts else np.zeros(0, dtype=int)


def star_scale(cells, w, kmat, ratio):
    """!
    @brief Total conductance of the star of one layer, in units of the sheet conductance, so that a lone via in a uniform sheet keeps the resistance of the well.
    @details The barrel of a layer is an equipotential node reached from the cell a of the footprint through g_a = c S w_a. A unit flux into the cells (f_a, sum 1) gives the
             barrel a potential delta above the far-field logarithm, f_a / (c S w_a) - sum_b C_ab f_b = delta with the lattice potential C_ab = (a(a - b) - kappa) / (4 S).
             The required delta is that of the Peaceman well without an edge, D = ln(h / r_t) / (2 pi S). Near a straight edge the lattice potential gets the matrix of
             `edge_kernel`, C_ab + K_ab / (2 pi S): the grid has the wall, but at the mirror of the cells and not of the via, and the star's flux f follows the cells that
             carry the heat, so the correction is a matrix (for f = w it is the number `edge_term` that the mean-potential well used).
             With S = 1, g = 1 / c and the eigenpairs (lambda_k, v_k) of W^(1/2) C W^(1/2): delta = 1 / sum_k q_k^2 / (g - lambda_k), q_k = v_k . W^(1/2) 1, which grows
             with g without a pole for g >= 0 (-C is positive definite on the fluxes of zero total, so only the eigenvalue along W^(1/2) 1 can be positive and the pole of
             the sum at it is a zero of delta), so c is found by Brent's method on g. D is negative when the cell is smaller than the target radius. When even an
             equipotential footprint is not resistive enough (delta at g = 0 not below D) the star gets the conductance STAR_CAP (nearly an equipotential), the case of the
             earlier 'infinite well'.
    @param cells Array (n, 2) of integer (row, col) cell indices of the footprint.
    @param w Array (n,) of the weights (sum 1).
    @param kmat Array (n, n) from `edge_kernel` (dimensionless), or None away from an edge.
    @param ratio Lattice spacing over the target radius, h / r_t (dimensionless).
    @return float c (dimensionless, units of S): the total conductance of the star over the sheet conductance.
    """
    key = (tuple((cells - cells.min(axis=0)).ravel().tolist()), tuple(np.round(w, 10).tolist()),
           None if kmat is None else tuple(np.round(kmat, 9).ravel().tolist()), round(float(ratio), 9))
    hit = _STAR_CACHE.get(key)
    if hit is not None:
        return hit
    d = cells[:, None, :] - cells[None, :, :]
    C = (lattice_kernel(d[..., 0], d[..., 1]) - KAPPA) / 4.0
    if kmat is not None:
        C = C + kmat / (2.0 * math.pi)
    target = math.log(ratio) / (2.0 * math.pi)
    sw = np.sqrt(w)
    lam, vec = np.linalg.eigh(sw[:, None] * C * sw[None, :])
    q2 = (vec.T @ sw) ** 2

    def delta(g):
        """!
        @brief Potential of the star node over the far-field logarithm for a unit flux, at g = 1 / c.
        @param g Inverse of the star conductance (dimensionless, above the largest eigenvalue).
        @return float delta (dimensionless).
        """
        with np.errstate(divide="ignore"):
            return 1.0 / float(np.sum(q2 / (g - lam)))

    lo = 1.0 / STAR_CAP
    if delta(lo) >= target:
        result = STAR_CAP                       # even an equipotential footprint is not resistive enough: nearly an equipotential star
    else:
        hi = max(1.0, 2.0 * (abs(target) + float(np.abs(lam).max())))
        while delta(hi) < target:
            hi *= 2.0
        result = 1.0 / brentq(lambda g: delta(g) - target, lo, hi, xtol=1e-14, rtol=1e-13)
    if len(_STAR_CACHE) >= _STAR_CACHE_MAX:
        _STAR_CACHE.clear()
    _STAR_CACHE[key] = result
    return result


def star_coupling(layer_cells, layer_w, layer_sbar, gv, ratio, kmats):
    """!
    @brief Dense coupling of the star treatment of one via: a barrel node per layer reached by g_a = c S w_a from the cells of the layer, the barrel nodes eliminated.
    @param layer_cells List over the layers of integer arrays (n_l, 2) (row, col) of the footprint cells (possibly empty).
    @param layer_w List over the layers of weight arrays (n_l,), each summing to 1.
    @param layer_sbar List over the layers of the weighted mean sheet conductance of the footprint in W/K (0 = the layer does not touch the barrel).
    @param gv Array (L-1,) of the barrel conductance of every gap in W/K.
    @param ratio Lattice spacing over the target radius, h / r_t (dimensionless).
    @param kmats List over the layers of the edge matrix of `edge_kernel` (or None away from an edge).
    @return Tuple (M, G): the dense matrix (n, n) in W/K over the concatenated (layer, cell) pairs (the Schur complement of the resistor network: symmetric, zero row sums,
            every off-diagonal entry non-positive) and the layer-to-layer conductances (L, L) in W/K.
    """
    L = len(layer_cells)
    sizes = [len(c) for c in layer_cells]
    off = np.concatenate([[0], np.cumsum(sizes)]).astype(int)
    n = int(off[-1])
    g = np.zeros(n)
    lay = np.zeros(n, dtype=int)
    for l in range(L):
        lay[off[l]:off[l + 1]] = l
        if sizes[l]:
            g[off[l]:off[l + 1]] = star_scale(layer_cells[l], layer_w[l], kmats[l], ratio) * layer_sbar[l] * layer_w[l]
    # Nodal matrix of the barrel nodes: the star totals on the diagonal, the barrel gaps in series between neighbouring layers
    Ybb = np.zeros((L, L))
    for l in range(L):
        Ybb[l, l] += g[off[l]:off[l + 1]].sum()
    for k in range(L - 1):
        Ybb[k, k] += gv[k]
        Ybb[k + 1, k + 1] += gv[k]
        Ybb[k, k + 1] -= gv[k]
        Ybb[k + 1, k] -= gv[k]
    Ybb += 1e-300 * np.eye(L)
    Z = np.linalg.inv(Ybb)
    M = np.diag(g) - np.outer(g, g) * Z[np.ix_(lay, lay)]
    M = 0.5 * (M + M.T)                                              # exactly symmetric: the symmetric LU checks it
    G = np.zeros((L, L))
    for l in range(L):
        for m in range(l + 1, L):
            G[l, m] = G[m, l] = -float(M[off[l]:off[l + 1], off[m]:off[m + 1]].sum())
    return M, G


def build(problem, d, S, cover, dx, dy, nx, ny, origin, active):
    """!
    @brief Couplings of every via of a problem on a grid.
    @param problem The Problem.
    @param d Gap thicknesses in m, shape (L-1,).
    @param S Sheet conductances in W/K, shape (>= L, ny, nx) (they carry the board cover of the cell).
    @param cover Board share of every cell, shape (ny, nx) (dimensionless).
    @param dx Cell size in x in m.
    @param dy Cell size in y in m (rows are placed with dy; the effective radius uses sqrt(dx dy), the kernel being that of square cells).
    @param nx Cells (nodes) along x.
    @param ny Cells (nodes) along y.
    @param origin Lower x edge of cell 0 in m (0 for the FVM, -dx/2 for the FDM nodes); the y edge is origin * dy / dx (-dy/2 for the FDM).
    @param active Boolean array (ny, nx) of the cells on the board. Unused since a via without board under its drill disc is skipped instead of being
           moved to the nearest active cell; kept so that the call sites of the FVM and FDM do not change.
    @return Tuple (blocks, gz_via): blocks is a list of `Block` (they unpack as (rows, cols, w, G): the cells of the union, equal weights on them and the
            layer-to-layer conductances in W/K) that carry the dense star coupling of the via; gz_via is the array (L-1, ny, nx) with the barrel conductance in
            the cell of the via centre (the point treatment of the earlier versions, kept for the Lumped model, which reads rings of cells). A via whose drill
            disc has no board cell is left out of both, and so is a via whose drill disc is off the board by the geometric test (model.Problem.via_board_shares),
            the one the warning and the Lumped and Analytic runs use.
    @note The footprint of a layer is the geometric one when the sheet conductance per unit of board is the same on all its cells, and otherwise the disc weighted by
          that conductance (a cell that cannot carry the heat takes almost none of it), enlarged until its effective radius reaches the target. The edge term
          is computed from the weights of each layer.
    """
    b = problem.board
    k_cu = b.materials.k_copper
    L = len(d) + 1
    blocks = []
    gz_via = np.zeros((L - 1, ny, nx))
    oy = origin * dy / dx                      # lower y edge of row 0 (-dy/2 for the FDM nodes)
    h = math.sqrt(dx * dy)
    safe_cover = np.where(cover > 0, cover, 1.0)
    rel_all = [np.where(cover > 0, S[l] / safe_cover, 0.0) for l in range(L)]       # sheet conductance per unit of board (the cell value carries the cover factor)
    empty = (np.zeros((0, 2), dtype=int), np.zeros(0), 0.0, None)                   # a layer that does not touch the barrel
    for v, share in zip(problem.vias, problem.via_board_shares()):
        if share <= 0.0:
            # The drill disc is off the board (the geometric test of checks.check_problem and of the Lumped and Analytic runs): the via conducts nothing,
            # also when it falls in a cut cell whose board part does not reach it (a cover test alone kept it there, 0.15 to 0.22 K on a small T)
            continue
        gv = k_cu * v.thermal_area(b.via_plating, k_cu) / d                # barrel conductance of every gap (W/K)
        r_via = v.diameter / 2.0
        w0, r_eff0, r_t = footprint(v.x, v.y, r_via, dx, origin, cover, dy, oy)
        if not w0:
            # No cell of the board under the drill disc: the via conducts nothing. (It used to be moved onto the nearest board cell at the full barrel
            # conductance, which made a via off the outline of a T worth 2.7 K instead of nothing.)
            continue
        ip, jp = cell_index_of_point(v.x - origin, v.y - oy, nx, ny, dx, dy)
        gz_via[:, ip, jp] += gv
        keys0 = list(w0)
        walls = []
        if origin == 0.0:
            # The edge image acts on the cell-centred grid only (the half volumes at the edge nodes of the FDM are left alone)
            walls = image_walls(problem, v, EDGE_REACH_CELLS * max(dx, dy), max(dx, dy))
        memo = {}
        parts = []
        for l in range(L):
            rel = rel_all[l]
            vals = np.array([float(rel[k]) for k in keys0])
            top = float(vals.max())
            if top <= 0.0:
                parts.append(empty)
                continue
            pattern = tuple(np.round(vals / top, 9).tolist())
            if pattern not in memo:
                uniform = float(vals.min()) >= top * (1.0 - 1e-9)
                weighting = None if uniform else rel
                if uniform:
                    w, r_eff = w0, r_eff0
                else:
                    w = enlarged_footprint(v.x, v.y, r_via, dx, origin, cover, dy, oy, r_t, weighting)
                    r_eff = effective_radius(w, h) if w else 0.0
                c = 0.0
                if walls and w:
                    for _ in range(5):
                        # The footprint and c depend on each other through the enlargement; a negative c would need a negative resistance
                        c = edge_term(w, dx, dy, (v.x, v.y), r_via, walls)
                        if math.log(r_eff / r_t) + c > 1e-9:
                            break
                        w = enlarged_footprint(v.x, v.y, r_via, dx, origin, cover, dy, oy, r_t * math.exp(-c) * (1.0 + 1e-6), weighting)
                        r_eff = effective_radius(w, h)
                    else:
                        c = edge_term(w, dx, dy, (v.x, v.y), r_via, walls)
                memo[pattern] = (w, edge_kernel(list(w), dx, dy, (v.x, v.y), r_via, walls) if (walls and w) else None)
            w, kmat = memo[pattern]
            if not w:
                parts.append(empty)
                continue
            ks = list(w)
            parts.append((np.array(ks, dtype=int), np.array([w[k] for k in ks]), float(sum(w[k] * rel[k] for k in ks)), kmat))
        layer_cells = [p[0] for p in parts]
        M, G = star_coupling(layer_cells, [p[1] for p in parts], [p[2] for p in parts], gv, h / r_t, [p[3] for p in parts])
        blocks.append(Block(layer_cells, M, G))
    return blocks, gz_via


def matrix_entries(blocks, idx):
    """!
    @brief COO entries of the via couplings: the dense star coupling M of every via over its (layer, cell) unknowns.
    @param blocks List from `build`.
    @param idx Index array (layers, ny, nx) of the unknowns.
    @return Tuple (rows, cols, vals) of lists of arrays, ready to extend the lists of the assembly.
    """
    rows, cols, vals = [], [], []
    for bl in blocks:
        flat = bl.flat(idx)
        n = len(flat)
        rows.append(np.repeat(flat, n))
        cols.append(np.tile(flat, n))
        vals.append(bl.M.ravel())
    return rows, cols, vals


def unknown_blocks(blocks, idx, n_layers):
    """!
    @brief Flat unknown indices of the (layer, cell) pairs of every via, vias that share an unknown merged: the blocks of the block SOR.
    @param blocks List from `build`.
    @param idx Index array (layers, ny, nx) of the unknowns.
    @param n_layers Number of board layers the vias join (unused: a block holds the pairs the via couples).
    @return List of sorted integer arrays.
    """
    merged = []
    for bl in blocks:
        s = set(bl.flat(idx).tolist())
        for other in [m for m in merged if m & s]:
            s |= other
            merged.remove(other)
        merged.append(s)
    return [np.array(sorted(s)) for s in merged]


def edge_via_indices(problem, nx, ny, dx, dy, cover):
    """!
    @brief Indices of the vias that touch the edge of the board: the edge of the box, or an outline edge, within one cell of the via centre.
    @param problem The Problem.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell size in x in m.
    @param dy Cell size in y in m.
    @param cover Board share of every cell, shape (ny, nx) (dimensionless).
    @return List of via indices (0-based); a via with no board under its drill disc is not listed (it is ignored by every model).
    @note The test is on the cells: the via is near an edge when a cell within one cell of its centre is partly or wholly off the board, or when the
          centre is within one cell of the box edge. The lattice kernel has no image of the edge, so the via effect is too large there (README of
          research/via-real-board, 3.1: +12 to +15 % at 1 mm for a via 0.16 mm from the edge).
    """
    b = problem.board
    out = []
    for k, (v, share) in enumerate(zip(problem.vias, problem.via_board_shares())):
        if share <= 0.0:
            continue                            # Off the board: ignored by every model (checks.check_problem says so), so it touches no edge
        near_box = min(v.x, b.width - v.x, v.y, b.height - v.y) < max(dx, dy)
        near_outline = False
        if not near_box and b.has_outline():
            i, j = cell_index_of_point(v.x, v.y, nx, ny, dx, dy)
            win = cover[max(i - 1, 0):i + 2, max(j - 1, 0):j + 2]
            near_outline = bool((win < 1.0).any())
        if near_box or near_outline:
            out.append(k)
    return out
