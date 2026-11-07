#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file viawell.py
@brief Mean-potential treatment of a via barrel on the grid of the FVM and FDM networks (footprint, Peaceman wells, Kron reduction).

@details A via is one conductor. Instead of putting the barrel conductance of every gap in the cell that holds the via centre (a point link, which does not
converge when the cell is refined: the constriction at the point grows like ln(1/dx)), the sheet of layer l reaches the barrel through the weighted mean
temperature of a footprint of cells, T_l = sum_a w_a T_{l,a} (a prescribed flux distribution w), with a Peaceman well of conductance
G_c = 2 pi S / ln(r_eff / r_t) between that mean and the barrel. The barrel nodes are eliminated (Kron reduction), which leaves the couplings G[l, m]
between the layer means; the matrix gets G[l, m] u u^T with u = e_l (x) w - e_m (x) w for every pair of layers, so no unknown is added and K stays
symmetric, positive semidefinite, with zero row sum from the via.

* Footprint: the area of the disc of the via over the cells that are on the board (cover > 0), weighted by the cover and normalised; if its lattice
  effective radius r_eff is smaller than the target r_t = e^(-1/4) r_via (the radius of the uniform sink density of the layered idealisation) the disc is
  enlarged, centre fixed, until r_eff = r_t.
* Effective radius of a distribution w on the square lattice: ln(r_eff / dx) = (pi / 2) (E - kappa), E = sum_ab w_a w_b a(a - b), a the potential kernel of
  the five-point stencil (exact recurrence up to offset 12, asymptote beyond), kappa = (2 gamma + 3 ln 2) / pi.
* Sheet conductance of the well: that of the cell with the largest weight, per unit of board (the cover factor of the cell is divided out).

The research is in research/point-via-convergence (treatment, convergence), research/sor-with-via-couplings and research/via-real-board.
* Barrel length: the barrel conductance over a gap is k_cu A / (d + a t_bar), a = BARREL_COPPER_FRACTION = 0.5, t_bar the mean copper thickness of the two layers
  (`barrel_length`; the same length is used by the Lumped and Analytic models and not by the 3D solid, which draws the barrel through its copper slabs).
* Contact: a layer whose zones touch none of the rim of the drill is left uncoupled, a rim partly on copper scales the well by the share (`rim_copper_shares`);
  a via at the corner of a copper region is NOT solved (the footprint was tuned for a full plane): it reads too hot, see checks.partial_copper_vias.
* Edge image (FVM only): the lattice kernel has no image of a board edge, and the footprint sits at cell centres, not at the via, so a via within about one cell
  of a straight edge saw the image of the edge at the wrong distance (the via effect read +14.5 % high at 1 mm for a via 0.16 mm from the edge). The well
  gets the term c = sum over the walls [ln D_lat - ln D_true] (D_true = 2 max(distance, r_via) the distance to the mirror image of the via, D_lat the lattice
  mean distance of the footprint to its own mirror image), G_c = 2 pi S / (ln(r_eff / r_t) + c); at a corner the diagonal image is added. The mirror image
  is that of an insulated edge and is used also for a cooled edge (a Robin image was studied and is not worth its code: research/via-edge-image 3).
  Only the walls of `image_walls` are imaged: none within EDGE_GUARD_CELLS of a reflex corner or a short or slanted side, where the infinite mirror of a side
  that ends there overstates the wall (docs/validation.md 28.1).
@note Not covered cleanly by the image (`edge_via_indices` lists them for the warning): the FDM and the 3D solid, a cell of 2 mm or more (the image is applied,
      the via is a fraction of a cell), an outline with a slanted or curved side, a short step or a reflex corner near the via, a via whose centre is within its radius of the wall.
"""

import math

import numpy as np

from .geometry import cell_index_of_point, points_in_polygon

EULER_GAMMA = 0.5772156649015329
KAPPA = (2.0 * EULER_GAMMA + 3.0 * math.log(2.0)) / math.pi        # asymptotic constant of the potential kernel of the five-point stencil
TARGET_RATIO = math.exp(-0.25)                                      # r_t / r_via: the radius of the uniform sink density over the disc of the via
POINT_SINK_RADIUS = math.exp(-math.pi * KAPPA / 2.0)               # equivalent radius of a point sink on the lattice, in cells (0.1985: the exact infinite-lattice value; Peaceman's radial argument gives exp(-pi/2) = 0.2079, Ibraguimov 2022, Theorem 1)
EDGE_REACH_CELLS = 6.0                                              # a wall counts when its distance from the via centre is at most this many cells
EDGE_GUARD_CELLS = 0.6                                              # no image when a reflex vertex, a slanted or a short side is nearer than this many cells (image_walls)
BARREL_COPPER_FRACTION = 0.5                                        # extra barrel length per gap in units of the mean copper thickness of the two layers around it (docs/theory.md 2.6)
RIM_SAMPLES = 48                                                    # samples on the rim of the drill for the contact test (a multiple of 4, offset by half a step so that none lies on an axis-parallel copper edge through the centre)
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


def enlarged_footprint(cx, cy, r_via, dx, origin, cover, dy, origin_y, need):
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
    @return dict {(i, j): w} (the disc radius is found by bisection after a doubling search bounded by the board size).
    """
    h = math.sqrt(dx * dy)

    def make(radius):
        return restrict_to_board(disc_weights(cx, cy, radius, dx, origin, dy, origin_y), cover)

    limit = max(cover.shape) * max(dx, dy)
    lo, hi = r_via, 2.0 * r_via
    while effective_radius(make(hi), h) < need and hi < limit:
        lo, hi = hi, 2.0 * hi
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if effective_radius(make(mid), h) < need:
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
    G = 0.5 * (G + G.T)                                               # the solve is symmetric only to rounding; the matrix K must be so exactly
    np.fill_diagonal(G, 0.0)
    G[G < 1e-14 * max(float(G.max()), 1e-300)] = 0.0                  # rounding of the elimination
    return G


def barrel_length(board, d):
    """!
    @brief Length of the via barrel over every gap, the dielectric gap plus half the mean copper thickness of the two layers around it.
    @param board The Board (only its copper thicknesses are read).
    @param d Gap thicknesses in m, shape (L-1,).
    @return numpy.ndarray (L-1,) of d + BARREL_COPPER_FRACTION * (t_l + t_{l+1}) / 2 in m. The copper nodes sit at the mid-planes of the layers, so the dielectric gap alone
            leaves out the barrel inside the copper; the plane around it shunts that part, which the measured fraction accounts for (research/via-contact-geometry).
    """
    d = np.asarray(d, dtype=float)
    t = np.asarray(board.copper_thickness, dtype=float)
    if len(t) != len(d) + 1:
        return d
    return d + BARREL_COPPER_FRACTION * 0.5 * (t[:-1] + t[1:])


def rim_copper_shares(problem, v, n_layers, zone_index):
    """!
    @brief Share of the rim of the drill of a via that lies on copper, per layer.
    @param problem The Problem (imported copper counts as full contact: the masks are not read here).
    @param v The Via.
    @param n_layers Number of layers L.
    @param zone_index List per layer of (polygon, xmin, xmax, ymin, ymax) of the zones with fill above zero (see `_zone_index`).
    @return list of L floats in [0, 1]; 0 means that the barrel touches no copper on that layer.
    """
    if problem.imported is not None:
        return [1.0] * n_layers
    ang = (np.arange(RIM_SAMPLES) + 0.5) * 2.0 * math.pi / RIM_SAMPLES
    r = v.diameter / 2.0
    px, py = v.x + r * np.cos(ang), v.y + r * np.sin(ang)
    out = []
    for l in range(n_layers):
        covered = np.zeros(RIM_SAMPLES, dtype=bool)
        for poly, x0, x1, y0, y1 in zone_index[l]:
            if v.x + r < x0 or v.x - r > x1 or v.y + r < y0 or v.y - r > y1:
                continue                                              # the rim is outside the box of the zone
            covered |= points_in_polygon(px, py, poly)
            if covered.all():
                break
        out.append(float(covered.mean()))
    return out


def _zone_index(problem, n_layers):
    """!
    @brief Zones of every layer with their bounding boxes, for the rim test.
    @param problem The Problem.
    @param n_layers Number of layers L.
    @return list per layer of (polygon array, xmin, xmax, ymin, ymax) in m; zones with no copper (fill 0) are left out.
    """
    index = [[] for _ in range(n_layers)]
    for z in problem.zones:
        if 0 <= z.layer < n_layers and z.fill > 0.0:
            p = np.asarray(z.polygon, dtype=float)
            index[z.layer].append((p, p[:, 0].min(), p[:, 0].max(), p[:, 1].min(), p[:, 1].max()))
    return index


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
           moved to the nearest active cell; kept so that the call sites of the FVM and FDM (and the research patches that match them by text) do not change.
    @return Tuple (blocks, gz_via): blocks is a list of (rows, cols, w, G) with the cell indices (integer arrays), the weights (sum 1) and the
            layer-to-layer conductances G (L, L) in W/K; gz_via is the array (L-1, ny, nx) with the barrel conductance in the cell of the via centre
            (the point treatment of the earlier versions, kept for the Lumped model, which reads rings of cells). A via whose drill disc has no board
            cell is left out of both, and so is a via whose drill disc is off the board by the geometric test (model.Problem.via_board_shares), the
            one the warning and the Lumped and Analytic runs use.
    """
    b = problem.board
    k_cu = b.materials.k_copper
    L = len(d) + 1
    blocks = []
    gz_via = np.zeros((L - 1, ny, nx))
    oy = origin * dy / dx                      # lower y edge of row 0 (-dy/2 for the FDM nodes)
    d_barrel = barrel_length(b, d)             # the barrel is longer than the gap by half the copper thickness (BARREL_COPPER_FRACTION)
    zone_index = _zone_index(problem, L) if problem.vias else None
    for v, share in zip(problem.vias, problem.via_board_shares()):
        if share <= 0.0:
            # The drill disc is off the board (the geometric test of checks.check_problem and of the Lumped and Analytic runs): the via conducts nothing,
            # also when it falls in a cut cell whose board part does not reach it (a cover test alone kept it there, 0.15 to 0.22 K on a small T)
            continue
        gv = k_cu * v.thermal_area(b.via_plating, k_cu) / d_barrel         # barrel conductance of every gap (W/K)
        w, r_eff, r_t = footprint(v.x, v.y, v.diameter / 2.0, dx, origin, cover, dy, oy)
        if not w:
            # No cell of the board under the drill disc: the via conducts nothing. (It used to be moved onto the nearest board cell at the full barrel
            # conductance, which made a via off the outline of a T worth 2.7 K instead of nothing.)
            continue
        ip, jp = cell_index_of_point(v.x - origin, v.y - oy, nx, ny, dx, dy)
        gz_via[:, ip, jp] += gv
        ic, jc = max(w, key=w.get)
        # Sheet conductance per unit of board: the cell value carries the cover factor
        s_cell = [float(S[l, ic, jc]) / float(cover[ic, jc]) for l in range(L)]
        c = 0.0
        if origin == 0.0:
            # The edge image acts on the cell-centred grid only (the half volumes at the edge nodes of the FDM are left alone)
            walls = image_walls(problem, v, EDGE_REACH_CELLS * max(dx, dy), max(dx, dy))
            if walls:
                r_via = v.diameter / 2.0
                h = math.sqrt(dx * dy)
                for _ in range(5):
                    # The footprint and c depend on each other through the enlargement; a negative c would need a negative resistance
                    c = edge_term(w, dx, dy, (v.x, v.y), r_via, walls)
                    if math.log(r_eff / r_t) + c > 1e-9:
                        break
                    w = enlarged_footprint(v.x, v.y, r_via, dx, origin, cover, dy, oy, r_t * math.exp(-c) * (1.0 + 1e-6))
                    r_eff = effective_radius(w, h)
                    ic, jc = max(w, key=w.get)
                    s_cell = [float(S[l, ic, jc]) / float(cover[ic, jc]) for l in range(L)]
                else:
                    c = edge_term(w, dx, dy, (v.x, v.y), r_via, walls)
        shares = rim_copper_shares(problem, v, L, zone_index)
        if min(shares) < 1.0:
            # The rim is partly or not at all on copper: the sheet conductance of the well is the footprint mean (weights w) of that of the cells, not that of the heaviest cell
            # (which can be a bare one or a copper one by the side of the barrel); a footprint with copper on its whole rim keeps the earlier value, bit for bit
            s_cell = [sum(wk * float(S[l, k[0], k[1]]) / float(cover[k[0], k[1]]) for k, wk in w.items()) for l in range(L)]
        g_well = [well_conductance(s_cell[l], r_eff, r_t, c) if s_cell[l] > 0 else 0.0 for l in range(L)]
        # Contact: a layer whose copper does not touch the rim of the drill is not joined to the barrel (the lattice of the footprint would otherwise carry heat
        # into a plane the barrel never reaches); a rim partly on copper scales the well by the share. Full contact leaves the well as it was (bit for bit).
        for l, f in enumerate(shares):
            if f < 1.0:
                g_well[l] = 0.0 if f <= 0.0 else g_well[l] * f
        keys = list(w)
        blocks.append((np.array([k[0] for k in keys]), np.array([k[1] for k in keys]), np.array([w[k] for k in keys]), kron_barrel(gv, g_well)))
    return blocks, gz_via


def matrix_entries(blocks, idx):
    """!
    @brief COO entries of the via couplings, G[l, m] u u^T with u = e_l (x) w - e_m (x) w for every pair of layers of every via.
    @param blocks List from `build`.
    @param idx Index array (layers, ny, nx) of the unknowns.
    @return Tuple (rows, cols, vals) of lists of arrays, ready to extend the lists of the assembly.
    """
    rows, cols, vals = [], [], []
    for ci, cj, w, G in blocks:
        ww = np.outer(w, w).ravel()
        n = len(w)
        L = G.shape[0]
        for l in range(L):
            for m in range(l + 1, L):
                g = G[l, m]
                if g <= 0:
                    continue
                a = np.repeat(idx[l, ci, cj], n)                             # row: cell a of layer l, column: cell a' of layer l
                a2 = np.tile(idx[l, ci, cj], n)
                bb = np.repeat(idx[m, ci, cj], n)
                b2 = np.tile(idx[m, ci, cj], n)
                rows.extend([a, bb, a, bb])
                cols.extend([a2, b2, b2, a2])
                vals.extend([g * ww, g * ww, -g * ww, -g * ww])
    return rows, cols, vals


def unknown_blocks(blocks, idx, n_layers):
    """!
    @brief Flat unknown indices of the cells of every via (footprint cells of the board layers), vias that share a cell merged: the blocks of the block SOR.
    @param blocks List from `build`.
    @param idx Index array (layers, ny, nx) of the unknowns.
    @param n_layers Number of board layers the vias join.
    @return List of sorted integer arrays.
    """
    merged = []
    for ci, cj, _w, _G in blocks:
        s = set(idx[:n_layers, ci, cj].ravel().tolist())
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
