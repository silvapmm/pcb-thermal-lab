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
         The lateral links in every layer are closed forms of the equivalent discs (radii of the core and of the footprint areas): A to C the Krogh mean-to-wall resistance of the
         annulus, `krogh(S_A, a_f, r_c)` times `OPTIONS["link_scale"]`; A to ring 1 the mean-to-outer-wall resistance of the annulus (uniform source, insulated inner side) plus the
         half ring of the program. The peak of the source layer is the hottest point of the annulus: the net lateral generation of A (what goes to C plus what goes to ring 1)
         spread uniformly gives the profile between the two walls, the maximum at the radius where the radial flow changes sign (`annulus_excess`), times the shape factor
         `4 (phi_mean - phi_min)` of the real footprint against the disc, which is 1 for a disc.
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "research", "lumped-analytic-vias", "lib"))
sys.path.insert(0, HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import constriction as cr                                                   # noqa: E402
import lumped_groups as lg                                                  # noqa: E402
import lumped_patch as lp                                                   # noqa: E402

OPTIONS = {"link_scale": 1.0, "out_scale": 1.0, "max_core": 0.92, "core_r": 0.7071, "peak": "annulus", "macro_outside": True, "link": "krogh"}
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


def core_mask(net, cov, prob):
    """!
    @brief The cells of the footprint that the dense groups of vias cover.
    @param net Network (grid).
    @param cov Footprint coverage (ny, nx).
    @param prob The Problem (vias).
    @return numpy.ndarray bool (ny, nx), or None when no group of two or more vias lies in the footprint.
    """
    from pcbthermal.geometry import cell_index_of_point
    if prob is None or len(prob.vias) < 2:
        return None
    pts = np.array([(v.x, v.y) for v in prob.vias])
    d_nn, group = lg._groups(pts)
    foot = cov > 0
    core = np.zeros(foot.shape, bool)
    for g in np.unique(group):
        mem = np.flatnonzero(group == g)
        cells = []
        for i in mem:
            ci, cj = cell_index_of_point(prob.vias[i].x, prob.vias[i].y, net.nx, net.ny, net.dx, net.dy)
            if foot[ci, cj]:
                cells.append((ci, cj, i))
        if len(cells) < 2:
            continue
        seed = np.zeros(foot.shape, bool)
        for ci, cj, _ in cells:
            seed[ci, cj] = True
        r = OPTIONS["core_r"] * float(np.mean([d_nn[i] for _, _, i in cells]))
        dist = ndimage.distance_transform_edt(~seed, sampling=(net.dy, net.dx))
        core |= (dist <= r) & foot
    return core if core.any() else None


def zoned_network(net, cov, layer, power, rings):
    """!
    @brief `lumped._heater_network` with the footprint cut into the rest A (node 0) and the core C (node 1) when a group of vias covers only part of it.
    @param net Network (per-cell arrays) of the problem.
    @param cov Footprint coverage of the heater, array (ny, nx).
    @param layer 0-based heater layer.
    @param power Heater power (W).
    @param rings Number of rings outside the footprint.
    @return dict as `lumped._heater_network` (theta of shape (L, R + 1)); the program's own network if no zone split applies.
    """
    from pcbthermal import lumped
    prob = lp.PROBLEM["p"]
    L, ny, nx = net.nl, net.ny, net.nx
    cell = net.dx * net.dy
    foot = cov > 0
    core = core_mask(net, cov, prob)
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
    gz = np.array([ring_sum(net.gz[l]) for l in range(nb - 1)]) if nb > 1 else np.zeros((0, R))
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

    def r_ac(l):
        if S[l, 0] <= 0 or S[l, 1] <= 0:
            return np.inf
        if OPTIONS["link"] == "loss" and g_loss_a(l) > 0:
            return OPTIONS["link_scale"] * cr.cell_with_loss(S[l, 0], g_loss_a(l), r_c, a_f, 1.0)["R_c"]
        return OPTIONS["link_scale"] * cr.krogh(S[l, 0], a_f, r_c)

    def r_a2(l):
        if R < 3 or S[l, 0] <= 0 or S[l, 2] <= 0:
            return np.inf
        half_k1 = 0.5 * thick[2] / (S[l, 2] * length[2])
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
    if OPTIONS["peak"] == "annulus":
        excess = shape * annulus_excess(S[layer, 0], r_c, a_f, q_in, q_out)
    else:
        excess = 0.0
    peak_extra = max(excess, th[layer, 1] - th[layer, 0], 0.0)
    LAST.clear()
    LAST.update(r_c=r_c, a_f=a_f, frac_c=frac_c, q_in=q_in, q_out=q_out, excess=excess, theta=th.copy(), shape=shape, cnt=cnt.copy())
    rho = rho_mean.copy()
    rho[0], rho[1] = 0.0, 1e-9                                               # keep the profile increasing for the interpolation of the temperature map
    return {"theta": th, "rho": rho, "dist": dist, "peak_extra": peak_extra,
            "K": K, "C": np.zeros(n), "R": R, "layer": layer, "r01": r_a2(layer), "peak_coef": 0.0,
            "out": {"top": float((g_top * th).sum()), "bottom": float((g_bot * th).sum()),
                    "heatsinks": float((g_heatsink * th).sum()), "sides": float((g_side * th).sum())}
                   | ({"blocks": float((g_block * th).sum())} if net.block_info else {}),
            "residual": float(np.linalg.norm(K @ theta - Q) / np.linalg.norm(Q))}


def _plain(net, cov, layer, power, rings):
    """!
    @brief The network of the program with the micro wells and the group term of `lumped_groups` (no zones).
    @param net Network.
    @param cov Footprint coverage.
    @param layer Heater layer.
    @param power Power in W.
    @param rings Rings.
    @return dict as `lumped._heater_network`.
    """
    return _STATE["plain"](net, cov, layer, power, rings)


_STATE = {}


@contextlib.contextmanager
def patched(link_scale=1.0, out_scale=1.0, max_core=0.92, core_r=0.7071, peak="annulus", macro_outside=True, link="krogh"):
    """!
    @brief Install the zoned Lumped model; restore the program on exit.
    @param link_scale Factor on the A-to-C link resistance (the cell-problem calibration knob).
    @param out_scale Factor on the annulus-to-ring-1 resistance.
    @param max_core Largest share of the footprint the core may cover before the footprint stays one node.
    @param core_r Radius of the core around the vias, in nearest-neighbour distances.
    @param peak "annulus" (the hottest point of the annulus) or "none".
    @param macro_outside True: keep the group term for groups outside the footprint.
    @param link "krogh" (lossless closed form) or "loss" (the lossy cell of `constriction.cell_with_loss`, the loss of the rest of the footprint in the layer).
    @return Context manager.
    """
    from pcbthermal import lumped
    old_opts = dict(OPTIONS)
    OPTIONS.update(link_scale=link_scale, out_scale=out_scale, max_core=max_core, core_r=core_r, peak=peak, macro_outside=macro_outside, link=link)
    old_net, old_solve = lumped._heater_network, lumped.solve_steady
    macro = "all" if macro_outside else "none"
    try:
        # The plain network: wells in every ring, the group term outside the footprint only (skip_rings = (0,))
        with lg.patched(macro=macro):
            lg.OPTIONS["skip_rings"] = (0,)
            _STATE["plain"] = lumped._heater_network
            lumped._heater_network = zoned_network

            yield
    finally:
        lumped._heater_network = old_net
        lumped.solve_steady = old_solve
        OPTIONS.clear()
        OPTIONS.update(old_opts)
