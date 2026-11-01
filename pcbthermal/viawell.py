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
@note The board-edge image of the via (the kernel has no image of an edge) is not modelled; `edge_via_indices` lists the vias that are too near an edge, for a warning.
"""

import math

import numpy as np

from .geometry import cell_index_of_point

EULER_GAMMA = 0.5772156649015329
KAPPA = (2.0 * EULER_GAMMA + 3.0 * math.log(2.0)) / math.pi        # asymptotic constant of the potential kernel of the five-point stencil
TARGET_RATIO = math.exp(-0.25)                                      # r_t / r_via: the radius of the uniform sink density over the disc of the via
POINT_SINK_RADIUS = math.exp(-math.pi * KAPPA / 2.0)               # equivalent radius of a point sink on the lattice, in cells (0.1985)
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

    def make(radius):
        return restrict_to_board(disc_weights(cx, cy, radius, dx, origin, dy, origin_y), cover)

    w = make(r_via)
    if not w:
        return {}, 0.0, r_t
    r_eff = effective_radius(w, h)
    if r_eff >= r_t:
        return w, r_eff, r_t
    # Enlarge the disc until the lattice effective radius equals the target (r_eff grows with the radius); the size of the board bounds the search
    limit = max(cover.shape) * max(dx, dy)
    lo, hi = r_via, 2.0 * r_via
    while effective_radius(make(hi), h) < r_t and hi < limit:
        lo, hi = hi, 2.0 * hi
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if effective_radius(make(mid), h) < r_t:
            lo = mid
        else:
            hi = mid
    w = make(hi)
    return w, effective_radius(w, h), r_t


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


def well_conductance(s_sheet, r_eff, r_t):
    """!
    @brief Peaceman well conductance between the footprint mean and the barrel.
    @param s_sheet Sheet conductance of the layer at the via in W/K.
    @param r_eff Effective radius of the footprint in m.
    @param r_t Target radius of the barrel in m.
    @return float 2 pi S / ln(r_eff / r_t) in W/K, infinite when r_eff <= r_t.
    """
    if r_eff <= r_t * (1.0 + 1e-9):
        return math.inf
    return 2.0 * math.pi * s_sheet / math.log(r_eff / r_t)


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
    for v, share in zip(problem.vias, problem.via_board_shares()):
        if share <= 0.0:
            # The drill disc is off the board (the geometric test of checks.check_problem and of the Lumped and Analytic runs): the via conducts nothing,
            # also when it falls in a cut cell whose board part does not reach it (a cover test alone kept it there, 0.15 to 0.22 K on a small T)
            continue
        gv = k_cu * v.thermal_area(b.via_plating, k_cu) / d                # barrel conductance of every gap (W/K)
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
        g_well = [well_conductance(s_cell[l], r_eff, r_t) if s_cell[l] > 0 else 0.0 for l in range(L)]
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
