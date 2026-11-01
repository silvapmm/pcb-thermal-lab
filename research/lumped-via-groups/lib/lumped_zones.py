#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file lumped_zones.py
@brief The Lumped model with the footprint cut into two zones when a group of vias covers only part of it: an in-memory copy of `lumped._heater_network` (the program is never edited).
@details The program's Lumped model has one node per layer for the whole footprint (ring 0). When a dense group of vias (the "core") sits under a larger footprint, the heat of
         the rest of the footprint must travel sideways in the source layer to reach the core, in parallel with the vertical paths of that rest (the dielectric, the film). The group
         term of `research/lumped-analytic-vias` put that sideways resistance in SERIES with the barrel (a Krogh well of the cluster in every plane), which counts the lateral
         path as if no heat took the vertical path of the rest of the footprint. Here the footprint becomes two zones, each with its own node in every layer:
         * node 0 = A, the footprint outside the core (source in proportion to its area; the vertical conductances of its own area; the link to ring 1 of the footprint boundary),
         * node 1 = C, the core (the cells within `0.7071 d_nn` of a via of a group of two or more vias in the footprint; the barrels and their micro wells; the rest of the
           source), no macro term,
         * nodes 2.. = the rings outside the footprint, as in the program.
         The proposal (the defaults of `patched`): the A-C link in every layer is the logarithmic-potential resistance of the real shapes, `(2 phi_AC - phi_AA - phi_CC) / (2 pi S)`
         (`mutual_potentials`); A to ring 1 is the mean-to-outer-wall resistance of the equivalent annulus (uniform source, insulated inner side) plus the half ring of the program.
         The peak of the source layer is the largest of three candidates: the hottest point of A (`potential_excess` with the `K0` kernel of the lossy sheet), the core mean plus
         the rise of the rim of the cell of one via (`micro_peak`), and (added by the review, option `core_peak`) the core mean plus the micro peak plus the excess of the core's
         own bump when the core is hotter than A (a core of weak or sparse vias, or vias that conduct nothing: without it the peak of such a core was its mean, 2 to 4 K low on the
         simple boards). The older closed forms of concentric discs (`geometry="disc"`, `peak="annulus"`) stay as options for the ladder of the README.
         If no core exists, or it covers more than `OPTIONS["max_core"]` of the footprint, the network is the program's (with the micro wells and no macro term in ring 0).
         `patched` installs everything; the macro term of `lumped_groups` is kept for the groups OUTSIDE the footprint (rows beside a source).
@note Steady state only (the transient attributes K, C are not built for the zoned network). Rectangular footprints; the radii are those of discs of the same area.
"""

import contextlib
import math
import os
import sys

import numpy as np
from scipy import ndimage
from scipy.special import k0

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "research", "lumped-analytic-vias", "lib"))
sys.path.insert(0, HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import constriction as cr                                                   # noqa: E402
import lumped_groups as lg                                                  # noqa: E402
import lumped_patch as lp                                                   # noqa: E402

OPTIONS = {"link_scale": 1.0, "out_scale": 1.0, "max_core": 0.92, "core_r": 0.7071, "peak": "annulus", "macro_outside": True, "link": "krogh", "micro_peak": False, "a1_other": "heated", "core_int": 0.0, "pitch_guard": 0.0, "geometry": "disc", "core_peak": False,
           "decimation": "stride"}
LAST = {}                                                                    # diagnostics of the last zoned network (zone radii, flows)


def annulus_out_resistance(S, r_c, a):
    """!
    @brief Mean-to-outer-wall resistance of an annulus with a uniform source, heat leaving only through the outer wall (inner side insulated).
    @param S Sheet conductance in W/K.
    @param r_c Inner radius in m.
    @param a Outer radius in m.
    @return float Area-mean temperature minus outer-wall temperature per watt generated in the annulus, K/W.
    """
    if a <= r_c:
        return 0.0
    # T(r) - T(a) = q/(2 S) [ (a^2 - r^2)/2 - r_c^2 ln(a/r) ], q the generation per area; mean over the annulus; per Q = q pi (a^2 - r_c^2)
    i1 = a * a * (a * a - r_c * r_c) / 4.0 - (a ** 4 - r_c ** 4) / 8.0
    i2 = r_c * r_c * (a * a / 4.0 - r_c * r_c / 2.0 * math.log(a / r_c) - r_c * r_c / 4.0)
    mean = (i1 - i2) / ((a * a - r_c * r_c) / 2.0) / (2.0 * S)
    return mean / (math.pi * (a * a - r_c * r_c))


def annulus_excess(S, r_c, a, q_in, q_out):
    """!
    @brief Hottest point of an annulus above its area mean, with a uniform net generation and given radial flows at the two walls.
    @param S Sheet conductance in W/K.
    @param r_c Inner radius in m.
    @param a Outer radius in m.
    @param q_in Heat leaving through the inner wall in W (towards the core).
    @param q_out Heat leaving through the outer wall in W.
    @return float Maximum minus mean temperature in K (0 if the net generation is not positive).
    @note I(r) = q_out - q (a^2 - r^2) / (a^2 - r_c^2) (outward flow at radius r, q = q_in + q_out the net generation), dT/dr = -I / (2 pi S r).
    """
    q = q_in + q_out
    if q <= 0 or a <= r_c:
        return 0.0
    r = np.linspace(r_c, a, 801)
    flow = q_out - q * (a * a - r * r) / (a * a - r_c * r_c)
    dT = -flow / (2.0 * math.pi * S * r)
    # trapezoid integration of T(r) from the outer wall inwards
    t = np.zeros_like(r)
    dr = np.diff(r)
    t[:-1] = -np.cumsum(((dT[:-1] + dT[1:]) / 2.0 * dr)[::-1])[::-1]
    w = 2.0 * r
    mean = float(np.sum((t[:-1] * w[:-1] + t[1:] * w[1:]) / 2.0 * dr) / (a * a - r_c * r_c))
    return float(t.max() - mean)


def core_mask(net, cov, prob, layer=0):
    """!
    @brief The cells of the footprint that the dense groups of vias cover.
    @param net Network (grid).
    @param cov Footprint coverage (ny, nx).
    @param prob The Problem (vias).
    @param layer Source layer (its fin length decides which groups are dense enough to count as a core).
    @return numpy.ndarray bool (ny, nx), or None when no group of two or more vias lies in the footprint (or none is denser than `OPTIONS["pitch_guard"]` fin lengths).
    """
    from pcbthermal.geometry import cell_index_of_point
    if prob is None or len(prob.vias) < 2:
        return None
    pts = np.array([(v.x, v.y) for v in prob.vias])
    d_nn, group = lg._groups(pts)
    foot = cov > 0
    core = np.zeros(foot.shape, bool)
    lam = math.inf
    if OPTIONS["pitch_guard"] > 0:
        # fin length of the source layer under the footprint: sqrt(S / g), g the conductance per area to the ambient and to the next layer
        cell = net.dx * net.dy
        g_area = (net.g_top[layer][foot] + net.g_bottom[layer][foot] + ((net.gz[layer][foot] + net.gz_via[layer][foot]) if layer < net.n_board - 1 else 0.0)).mean() / cell
        lam = math.sqrt(float(net.S[layer][foot].mean()) / g_area) if g_area > 0 else math.inf
    for g in np.unique(group):
        mem = np.flatnonzero(group == g)
        cells = []
        for i in mem:
            ci, cj = cell_index_of_point(prob.vias[i].x, prob.vias[i].y, net.nx, net.ny, net.dx, net.dy)
            if foot[ci, cj]:
                cells.append((ci, cj, i))
        if len(cells) < 2:
            continue
        if OPTIONS["pitch_guard"] > 0 and float(np.mean([d_nn[i] for _, _, i in cells])) > OPTIONS["pitch_guard"] * lam:
            continue                                                         # vias farther apart than the fin length act as separate sinks, not as a core
        seed = np.zeros(foot.shape, bool)
        for ci, cj, _ in cells:
            seed[ci, cj] = True
        r = OPTIONS["core_r"] * float(np.mean([d_nn[i] for _, _, i in cells]))
        dist = ndimage.distance_transform_edt(~seed, sampling=(net.dy, net.dx))
        core |= (dist <= r) & foot
    return core if core.any() else None


def mutual_potentials(w_a, w_c, dx, dy, max_cells=700):
    """!
    @brief Mean logarithmic distances between two uniform distributions of heat on the grid (the lossless link between two regions of a sheet, any shapes).
    @details For a uniform source over region A and a uniform sink over region C of equal strength Q, the temperature on an infinite sheet is
             T(x) = -(Q / (2 pi S)) [ mean over A of ln|x - y| - mean over C of ln|x - y| ], so the difference of the area means is
             T_A - T_C = (Q / (2 pi S)) (2 phi_AC - phi_AA - phi_CC), phi_XY the mean of ln|x - y| over x in X, y in Y. For concentric discs this is the Krogh resistance of the
             annulus plus Q / (8 pi S) of the core (checked in the tests); for off-centre or rectangular regions it follows the real geometry.
    @param w_a Weights of the cells of A (ny, nx), zero outside A.
    @param w_c Weights of the cells of C (ny, nx).
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param max_cells Cells kept (evenly decimated) per region.
    @return float 2 phi_AC - phi_AA - phi_CC (dimensionless).
    """
    def points(w):
        idx = np.argwhere(w > 0)
        step = max(int(np.ceil(len(idx) / max_cells)), 1)
        idx = idx[::step]
        return np.column_stack([idx[:, 1] * dx, idx[:, 0] * dy]), w[w > 0][::step], step

    def mean_log(p, wp, q, wq, same, step):
        d = np.hypot(p[:, None, 0] - q[None, :, 0], p[:, None, 1] - q[None, :, 1])
        if same:
            np.fill_diagonal(d, 0.447 * math.sqrt(dx * dy) * math.sqrt(step))        # mean log distance inside a cell
        else:
            d = np.maximum(d, 0.447 * math.sqrt(dx * dy))
        return float((np.log(d) * wp[:, None] * wq[None, :]).sum() / (wp.sum() * wq.sum()))
    pa, wa, sa = points(w_a)
    pc_, wc, sc = points(w_c)
    return 2.0 * mean_log(pa, wa, pc_, wc, False, 1) - mean_log(pa, wa, pa, wa, True, sa) - mean_log(pc_, wc, pc_, wc, True, sc)


def potential_excess(w_a, w_c, q_in, q_out, S, dx, dy, max_cells=700, lam=None, decimation=None):
    """!
    @brief Hottest point of A above its area mean for the real shapes: a uniform generation `q_in + q_out` over A, a uniform sink `q_in` over C and a far-field sink `q_out`.
    @details T(x) = -(1 / (2 pi S)) [ (q_in + q_out) phi_A(x) - q_in phi_C(x) ] + const, phi_X(x) the mean of ln|x - y| over y in X (the lossless sheet; a far-field sink adds a
             constant). The maximum over the cells of A minus their weighted mean. For concentric discs it agrees with `annulus_excess` (see the tests).
    @param w_a Weights of the cells of A.
    @param w_c Weights of the cells of C.
    @param q_in Heat that A sends to C in W.
    @param q_out Heat that A sends to ring 1 in W.
    @param S Sheet conductance in W/K.
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param max_cells Cells kept per region.
    @param lam Fin length of the layer in m (sqrt(S / g) with g the vertical loss per area): the kernel -ln d becomes K0(d / lam) of the sheet with a uniform loss; None: lossless.
    @param decimation "block" or "stride" when a zone has more than `max_cells` cells (None: `OPTIONS["decimation"]`).
    @return float K (0 if the net generation is not positive).
    """
    q = q_in + q_out
    if q <= 0:
        return 0.0
    if (decimation or OPTIONS["decimation"]) == "block":
        # blocks of k x k cells (review): every kept point is a block with its weight, its centroid and its own self distance, so the field has no aliasing
        pa, wa, da = block_points(w_a, dx, dy, max_cells)
        pc_, wc, dc = block_points(w_c, dx, dy, max_cells)
    else:
        # every step-th cell in row order (the researcher's version): on a region of more than max_cells cells the kept cells form stripes and the maximum of the
        # field over them is biased upwards (+17 to +25 % on an annulus of 2400 cells, three times on a thin one; tests)
        def points(w):
            idx = np.argwhere(w > 0)
            step = max(int(np.ceil(len(idx) / max_cells)), 1)
            idx = idx[::step]
            return np.column_stack([idx[:, 1] * dx, idx[:, 0] * dy]), w[w > 0][::step], np.full(len(idx), 0.447 * math.sqrt(dx * dy) * math.sqrt(step))
        pa, wa, da = points(w_a)
        pc_, wc, dc = points(w_c)

    def phi(p, q_pts, wq, dq, same):
        d = np.hypot(p[:, None, 0] - q_pts[None, :, 0], p[:, None, 1] - q_pts[None, :, 1])
        if same:
            d[np.arange(len(p)), np.arange(len(p))] = dq
        else:
            d = np.maximum(d, 0.447 * math.sqrt(dx * dy))
        # kernel of the sheet: -ln d (lossless) or K0(d / lam) with a vertical loss; the sign is that of -ln d so that the same formula holds
        k = -np.log(d) if lam is None else k0(d / lam)
        return (k * wq[None, :]).sum(axis=1) / wq.sum()
    t = (q * phi(pa, pa, wa, da, True) - q_in * phi(pa, pc_, wc, dc, False)) / (2.0 * math.pi * S)
    return float(t.max() - (t * wa).sum() / wa.sum())


def block_points(w, dx, dy, max_cells):
    """!
    @brief Cells of a region aggregated in blocks of k x k cells, k the smallest that keeps at most about `max_cells` blocks (the review's decimation of the potential integrals).
    @param w Weights of the cells (ny, nx), zero outside the region.
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param max_cells Largest number of blocks wanted.
    @return Tuple (positions (n, 2) in m, weights (n,), self distances (n,) in m): the weighted centroid of every block that holds part of the region, its summed weight,
            and the mean log distance inside it, `0.447 sqrt(area)` (a square of the area of the cells of the region in the block; for k = 1 the program's cell term).
    """
    n = int((w > 0).sum())
    k = max(int(math.ceil(math.sqrt(n / max_cells))), 1)
    ny, nx = w.shape
    big_y, big_x = -(-ny // k), -(-nx // k)
    wp = np.zeros((big_y * k, big_x * k))
    wp[:ny, :nx] = w
    yy, xx = np.mgrid[0:big_y * k, 0:big_x * k]

    def block_sum(a):
        # sum of the k x k cells of every block
        return a.reshape(big_y, k, big_x, k).sum(axis=(1, 3))
    wb, xb, yb, nb = block_sum(wp), block_sum(wp * xx), block_sum(wp * yy), block_sum((wp > 0).astype(float))
    m = wb > 0
    pos = np.column_stack([xb[m] / wb[m] * dx, yb[m] / wb[m] * dy])
    # self distance of a block of nb cells of the region: that of a square of the same area (for k = 1 exactly the cell term of the program and of the strided version)
    return pos, wb[m], 0.447 * np.sqrt(nb[m] * dx * dy)


def rim_minus_mean(S, R, a):
    """!
    @brief Temperature of the rim of the Krogh cell above the area mean of the cell, per watt taken by the via.
    @param S Sheet conductance in W/K.
    @param R Cell radius in m.
    @param a Radius of the via in m.
    @return float K/W: [b^2 ln b / (b^2 - 1) - 1/2] / (2 pi S) minus the Krogh mean-to-wall resistance (zero if R <= a).
    """
    if R <= a:
        return 0.0
    b = R / a
    rim = (b * b * math.log(b) / (b * b - 1.0) - 0.5) / (2.0 * math.pi * S)
    return rim - cr.krogh(S, R, a)


def micro_peak(layer, th, node, S_layer):
    """!
    @brief Rise of the hottest point of the cells of the vias above the node mean, in the source layer: the heat of one via times the rim-to-mean resistance of its cell.
    @param layer Source layer.
    @param th (L, R) temperatures of the network.
    @param node Index of the zone node that holds the vias.
    @param S_layer Sheet conductance of that node in the source layer.
    @return float K (0 if the node has no via).
    """
    seen = [g for g in lg.SEEN if g["ring"] == node]
    n = sum(g["n"] for g in seen)
    if n == 0:
        return 0.0
    i_tot = 0.0
    for (l_a, l_b), g in lp.GZVIA.items():
        if l_a == layer:
            i_tot += g[node] * (th[layer, node] - th[l_b, node])
        elif l_b == layer:
            i_tot += g[node] * (th[layer, node] - th[l_a, node])
    i_tot = max(i_tot, 0.0)
    r_cell = sum(g["r_cell"] * g["n"] for g in seen) / n
    a = sum(g["a"] * g["n"] for g in seen) / n
    return i_tot / n * rim_minus_mean(S_layer, r_cell, a)


def zoned_network(net, cov, layer, power, rings, vias=None, zone_ok=None):
    """!
    @brief `lumped._heater_network` with the footprint cut into the rest A (node 0) and the core C (node 1) when a group of vias covers only part of it.
    @param net Network (per-cell arrays) of the problem.
    @param cov Footprint coverage of the heater, array (ny, nx).
    @param layer 0-based heater layer.
    @param power Heater power (W).
    @param rings Number of rings outside the footprint.
    @param vias ViaSet that the program passes since `fix/via-constriction`; ignored (this copy builds its own via couplings from the barrels as point conductances).
    @param zone_ok Ignored (the zone decision the program passes since `feature/lumped-zones`).
    @return dict as `lumped._heater_network` (theta of shape (L, R + 1)); the program's own network if no zone split applies.
    """
    from pcbthermal import lumped
    prob = lp.PROBLEM["p"]
    L, ny, nx = net.nl, net.ny, net.nx
    cell = net.dx * net.dy
    foot = cov > 0
    core = core_mask(net, cov, prob, layer)
    if core is None or core.sum() > OPTIONS["max_core"] * foot.sum() or core.sum() == foot.sum():
        LAST.clear()
        return _plain(net, cov, layer, power, rings)
    dist = ndimage.distance_transform_edt(~foot, sampling=(net.dy, net.dx))
    outside = ~foot
    rho_max = float(dist.max()) if outside.any() else 0.0
    if rho_max > 0:
        edges = lumped.ring_edges(rho_max, net.dx, net.dy, rings)
        idx = np.where(foot, 0, 1 + np.minimum(np.searchsorted(edges[1:], dist, side="left"), len(edges) - 2))
    else:                                                                    # the footprint is the whole board: two nodes per layer and no ring outside
        edges, idx = np.array([0.0]), np.zeros((ny, nx), dtype=int)
    cnt0 = np.bincount(idx.ravel(), minlength=idx.max() + 1)
    used = np.flatnonzero(cnt0 > 0)
    remap = np.full(len(cnt0), -1)
    remap[used] = np.arange(len(used))
    idx = remap[idx]
    R0 = len(used)
    # zone indices: 0 = A (rest of the footprint), 1 = C (core), k + 1 for the outside ring k
    idx2 = np.where(idx == 0, np.where(core, 1, 0), idx + 1)
    R = R0 + 1
    cnt = np.bincount(idx2.ravel(), minlength=R)
    flat = idx2.ravel()

    def ring_sum(a):
        return np.bincount(flat, weights=a.ravel(), minlength=R)

    rho_mean = ring_sum(dist) / cnt
    thick = np.zeros(R)
    for k in range(1, R0):
        lo, hi = edges[used[k] - 1], edges[used[k]]
        thick[k + 1] = max(min(hi, rho_max) - lo, 0.5 * min(net.dx, net.dy))
    length = np.where(thick > 0, cnt * cell / np.maximum(thick, 1e-12), 0.0)
    S = np.array([ring_sum(net.S[l]) / cnt for l in range(L)])
    g_top = np.array([ring_sum(net.g_top[l]) for l in range(L)])
    g_bot = np.array([ring_sum(net.g_bottom[l]) for l in range(L)])
    g_heatsink = np.array([ring_sum(net.g_heatsink[l]) for l in range(L)])
    g_side = np.array([ring_sum(net.g_side[l]) for l in range(L)])
    nb = net.n_board
    g_block = np.array([ring_sum(net.g_block[l]) for l in range(L)])
    gz = np.array([ring_sum(net.gz[l] + net.gz_via[l]) for l in range(nb - 1)]) if nb > 1 else np.zeros((0, R))   # barrels as the point conductance of the program up to f2d5c03 (the program's FVM holds them as couplings now)
    links = [(a, b, ring_sum(g)) for a, b, g in net.extra_links]
    cov_a = float((cov * (idx2 == 0)).sum())
    cov_c = float((cov * (idx2 == 1)).sum())
    frac_c = cov_c / (cov_a + cov_c)
    # Equivalent disc radii of the zones
    r_c = math.sqrt(cnt[1] * cell / math.pi)
    a_f = math.sqrt((cnt[0] + cnt[1]) * cell / math.pi)
    phi_mean, phi_bnd, phi_min = lumped._footprint_potentials(cov, net.dx, net.dy)
    shape = 4.0 * (phi_mean - phi_min)

    # Vertical couplings with the wells of the vias (micro wells in the zones; the macro term only for groups outside the footprint)
    old_opts = dict(lg.OPTIONS)
    lg.OPTIONS["macro"] = "all" if OPTIONS["macro_outside"] else "none"
    lg.OPTIONS["skip_rings"] = (0, 1)
    try:
        GZ = lg.via_couplings(net, cov, idx2, R, cnt, ring_sum, S, g_top, g_bot, gz, nb)
    finally:
        lg.OPTIONS.clear()
        lg.OPTIONS.update(old_opts)

    area_a = cnt[0] * cell

    def g_loss_a(l):
        # vertical loss per area of the rest of the footprint in layer l: films plus the dielectric to the neighbouring layers
        g = (g_top[l, 0] + g_bot[l, 0]) / area_a
        for m in (l - 1, l):
            if 0 <= m < nb - 1:
                g += gz[m, 0] / area_a
        return g

    pot = None
    if OPTIONS["geometry"] == "potential":
        # the link of the real shapes of A and C (lossless): 2 phi_AC - phi_AA - phi_CC over 2 pi S, the core-internal resistance included
        pot = mutual_potentials(cov * (idx2 == 0), cov * (idx2 == 1), net.dx, net.dy)

    def r_ac(l):
        if S[l, 0] <= 0 or S[l, 1] <= 0:
            return np.inf
        if pot is not None:
            return OPTIONS["link_scale"] * pot / (2.0 * math.pi * S[l, 0])
        # inside the core the net injection (source, barrels, dielectric) is uniform over a disc of radius r_c, so the core mean differs from its boundary by Q / (8 pi S)
        r_int = OPTIONS["core_int"] / (8.0 * math.pi * S[l, 1])
        if OPTIONS["link"] == "loss" and g_loss_a(l) > 0:
            return OPTIONS["link_scale"] * cr.cell_with_loss(S[l, 0], g_loss_a(l), r_c, a_f, 1.0)["R_c"] + r_int
        return OPTIONS["link_scale"] * cr.krogh(S[l, 0], a_f, r_c) + r_int

    def r_a2(l):
        if R < 3 or S[l, 0] <= 0 or S[l, 2] <= 0:
            return np.inf
        half_k1 = 0.5 * thick[2] / (S[l, 2] * length[2])
        if l != layer and OPTIONS["a1_other"] == "through":
            # a layer without the source: the heat enters at the core and leaves at the rim (log profile), mean of the annulus to the outer wall
            mean = 2.0 * (a_f * a_f / 4.0 - r_c * r_c / 2.0 * math.log(a_f / r_c) - r_c * r_c / 4.0) / (a_f * a_f - r_c * r_c)
            return OPTIONS["out_scale"] * mean / (2.0 * math.pi * S[l, 0]) + half_k1
        return OPTIONS["out_scale"] * annulus_out_resistance(S[l, 0], r_c, a_f) + half_k1

    def r_ring(l, k):
        if S[l, k] <= 0 or S[l, k + 1] <= 0:
            return np.inf
        return 0.5 * thick[k] / (S[l, k] * length[k]) + 0.5 * thick[k + 1] / (S[l, k + 1] * length[k + 1])

    n = L * R
    K = np.zeros((n, n))

    def couple(a, b, g):
        K[a, a] += g
        K[b, b] += g
        K[a, b] -= g
        K[b, a] -= g

    for l in range(L):
        for rr, a_i, b_i in ((r_ac(l), 0, 1), (r_a2(l), 0, 2)):
            if np.isfinite(rr) and b_i < R:
                couple(l * R + a_i, l * R + b_i, 1.0 / rr)
        for k in range(2, R - 1):
            rr = r_ring(l, k)
            if np.isfinite(rr):
                couple(l * R + k, l * R + k + 1, 1.0 / rr)
    for (l_a, l_b), g_ab in GZ.items():
        for k in range(R):
            if g_ab[k] != 0.0:
                couple(l_a * R + k, l_b * R + k, g_ab[k])
    for a, b, g in links:
        for k in range(R):
            if g[k] > 0:
                couple(a * R + k, b * R + k, g[k])
    diag = (g_top + g_bot + g_heatsink + g_side + g_block).ravel()
    K[np.arange(n), np.arange(n)] += np.where(diag > 0, diag, 0.0)
    Q = np.zeros(n)
    Q[layer * R + 0] = power * (1.0 - frac_c)
    Q[layer * R + 1] = power * frac_c
    iso = np.diag(K) <= 0
    K[iso, iso] = 1.0
    theta = np.linalg.solve(K, Q)
    th = theta.reshape(L, R)

    # Peak of the source layer: hottest point of the annulus A (or the core if it is hotter)
    q_in = (th[layer, 0] - th[layer, 1]) / r_ac(layer) if np.isfinite(r_ac(layer)) else 0.0
    q_out = (th[layer, 0] - th[layer, 2]) / r_a2(layer) if R > 2 and np.isfinite(r_a2(layer)) else 0.0
    if OPTIONS["peak"] in ("potential", "potential_lossy"):
        lam_l = math.sqrt(S[layer, 0] / g_loss_a(layer)) if OPTIONS["peak"] == "potential_lossy" and g_loss_a(layer) > 0 else None
        excess = potential_excess(cov * (idx2 == 0), cov * (idx2 == 1), q_in, q_out, S[layer, 0], net.dx, net.dy, lam=lam_l)
    elif OPTIONS["peak"] == "annulus":
        excess = shape * annulus_excess(S[layer, 0], r_c, a_f, q_in, q_out)
    else:
        excess = 0.0
    mp = micro_peak(layer, th, 1, S[layer, 1]) if OPTIONS["micro_peak"] else 0.0
    excess_c = 0.0
    if OPTIONS["core_peak"] and th[layer, 1] > th[layer, 0] and np.isfinite(r_ac(layer)):
        # The core is hotter than the rest (sparse or weak vias, or vias that conduct nothing): its hottest point lies inside it and is above its mean by the bump of a
        # uniformly heated region that sends its net lateral heat outwards, the program's own peak formula for a footprint (lossless kernel, on the safe side). Without it
        # the peak of such a core was its mean: with vias that conduct nothing the zone model read 2 to 4 K below the program on the simple boards (review).
        q_ca = (th[layer, 1] - th[layer, 0]) / r_ac(layer)
        excess_c = potential_excess(cov * (idx2 == 1), cov * (idx2 == 0), 0.0, q_ca, S[layer, 1], net.dx, net.dy)
    peak_extra = max(excess, th[layer, 1] + mp + excess_c - th[layer, 0], 0.0)
    LAST.clear()
    LAST.update(r_c=r_c, a_f=a_f, frac_c=frac_c, q_in=q_in, q_out=q_out, excess=excess, excess_c=excess_c, theta=th.copy(), shape=shape, cnt=cnt.copy())
    rho = rho_mean.copy()
    rho[0], rho[1] = 0.0, 1e-9                                               # keep the profile increasing for the interpolation of the temperature map
    return {"theta": th, "rho": rho, "dist": dist, "peak_extra": peak_extra,
            "K": K, "C": np.zeros(n), "R": R, "layer": layer, "r01": r_a2(layer), "peak_coef": 0.0,
            "out": {"top": float((g_top * th).sum()), "bottom": float((g_bot * th).sum()),
                    "heatsinks": float((g_heatsink * th).sum()), "sides": float((g_side * th).sum())}
                   | ({"blocks": float((g_block * th).sum())} if net.block_info else {}),
            "residual": float(np.linalg.norm(K @ theta - Q) / np.linalg.norm(Q))}


def _plain(net, cov, layer, power, rings, vias=None):
    """!
    @brief The network of the program with the micro wells and the group term of `lumped_groups` (no zones).
    @param net Network.
    @param cov Footprint coverage.
    @param layer Heater layer.
    @param power Power in W.
    @param rings Rings.
    @param vias Ignored (see `zoned_network`).
    @return dict as `lumped._heater_network`.
    """
    rn = _STATE["plain"](net, cov, layer, power, rings)
    if OPTIONS["micro_peak"] and lg.SEEN:
        foot = cov > 0
        rn["peak_extra"] = rn["peak_extra"] + micro_peak(layer, rn["theta"], 0, float(net.S[layer][foot].mean()))
    return rn


_STATE = {}


@contextlib.contextmanager
def patched(link_scale=1.0, out_scale=1.0, max_core=0.92, core_r=0.7071, peak="potential_lossy", macro_outside=True, link="krogh", micro_peak=True, a1_other="heated", core_int=0.0, pitch_guard=0.0, micro_scale=1.0, geometry="potential",
            core_peak=True, decimation="block"):
    """!
    @brief Install the zoned Lumped model; restore the program on exit.
    @param link_scale Factor on the A-to-C link resistance (the cell-problem calibration knob).
    @param out_scale Factor on the annulus-to-ring-1 resistance.
    @param max_core Largest share of the footprint the core may cover before the footprint stays one node.
    @param core_r Radius of the core around the vias, in nearest-neighbour distances.
    @param peak "annulus" (the hottest point of the concentric annulus), "potential" (the real shapes through logarithmic potentials), "potential_lossy" (the same with the K0 kernel of the sheet with its vertical loss) or "none".
    @param macro_outside True: keep the group term for groups outside the footprint.
    @param geometry "disc" (equivalent concentric discs, closed forms) or "potential" (the real shapes of A and C through the logarithmic potentials; replaces the Krogh link and the core-internal term).
    @param micro_scale Factor on the micro wells of the vias (0: the planes isothermal at the barrels, the effective vertical conductivity of the array).
    @param pitch_guard Largest nearest-neighbour distance of a group, in fin lengths of the source layer, that still counts as a core (0 = no limit).
    @param core_int Factor on the resistance Q / (8 pi S) between the mean of the core and its boundary (1 = the uniform-injection disc), added to the A-C link.
    @param a1_other "heated" (the annulus with a uniform source in every layer) or "through" (the log profile of heat entering at the core, in the layers without the source).
    @param micro_peak True: add the rise of the hottest point of the cell of a via above the node mean (rim of the Krogh cell) to the peak.
    @param link "krogh" (lossless closed form) or "loss" (the lossy cell of `constriction.cell_with_loss`, the loss of the rest of the footprint in the layer).
    @param core_peak True (the review): when the core is hotter than A, the peak candidate of the core adds the bump of the core above its mean; False: the core mean plus the micro peak (the researcher's version).
    @param decimation "block" (the review: blocks of k x k cells in the peak integral) or "stride" (every step-th cell, the researcher's version) when a zone holds more than 700 cells.
    @return Context manager.
    """
    from pcbthermal import lumped
    old_opts = dict(OPTIONS)
    OPTIONS.update(link_scale=link_scale, out_scale=out_scale, max_core=max_core, core_r=core_r, peak=peak, macro_outside=macro_outside, link=link, micro_peak=micro_peak, a1_other=a1_other, core_int=core_int, pitch_guard=pitch_guard, geometry=geometry,
                   core_peak=core_peak, decimation=decimation)
    old_net, old_solve = lumped._heater_network, lumped.solve_steady
    macro = "all" if macro_outside else "none"
    try:
        # The plain network: wells in every ring, the group term outside the footprint only (skip_rings = (0,))
        with lg.patched(macro=macro):
            lg.OPTIONS["skip_rings"] = (0,)
            lg.OPTIONS["micro_scale"] = micro_scale
            _STATE["plain"] = lumped._heater_network
            lumped._heater_network = zoned_network

            yield
    finally:
        lumped._heater_network = old_net
        lumped.solve_steady = old_solve
        OPTIONS.clear()
        OPTIONS.update(old_opts)
