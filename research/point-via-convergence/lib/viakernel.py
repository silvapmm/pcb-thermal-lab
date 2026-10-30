#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file viakernel.py
@brief The treatments of a via barrel on a grid of cells (point, spread over the disc, spread over the ring, Peaceman well, tuned kernel): weights and well conductances.
@details Everything here is geometry and linear algebra on the lattice; nothing imports the program. A treatment turns one via (centre, radius, barrel conductances per gap)
         and the sheet conductance of the layers into
         * `weights`: a dict {(i, j): w} of cell indices with weights that sum to 1 (the share of the barrel conductance of every gap that sits in that cell), and
         * `r_well`: the radius used for the well resistance, or None (no well).
         The well of a layer is a link of conductance Gc = 2 pi S / ln(r_eq / r_via) between the sheet node and the barrel (Peaceman's well index); the barrel is a chain of
         nodes, one per layer, joined by the gap conductances, and `kron_barrel` eliminates the barrel nodes to give the conductances between the sheet nodes of the cell.
         Treatments (names used by the studies):
         * `point`      the program: all the barrel conductance in the cell of the centre, no well;
         * `area`       weights = area of the disc (radius of the via) inside every cell;
         * `ring`       weights = length of the circle of the via inside every cell (the flux of an equipotential cylinder is uniform on its circumference);
         * `peaceman`   a point with wells while r_eq = 0.1985 dx exceeds the via radius, otherwise the disc area weights (plan (a) of the roadmap);
         * `tuned`      a point with wells while r_eq exceeds the via radius, otherwise the disc-shaped kernel of the radius R_s for which the lattice effective radius equals the
                        via radius (`lattice.effective_radius`): continuous at the change, exact in the sense of the mean potential for any cell size.
"""

import math

import numpy as np

import lattice


def disc_weights(cx, cy, radius, dx, origin=0.0, sub=16, kind="area"):
    """!
    @brief Weights of a disc (area) or a circle (length) of a given radius over the cells of a square grid.
    @param cx Centre x in m.
    @param cy Centre y in m.
    @param radius Radius in m (0 = a point).
    @param dx Cell size in m.
    @param origin Position of the lower edge of cell 0 in m (0 for cell-centred volumes, -dx/2 for node-centred control volumes at i dx).
    @param sub Samples per cell side for the area (and per quarter of circle of resolution for the ring, in units of cells).
    @param kind "area" or "ring".
    @return dict {(i, j): weight} with the weights summing to 1; i is the row (y), j the column (x).
    """
    if radius <= 1e-12 * dx:
        return {(int(math.floor((cy - origin) / dx)), int(math.floor((cx - origin) / dx))): 1.0}
    n0x, n0y = int(math.floor((cx - radius - origin) / dx)), int(math.floor((cy - radius - origin) / dx))
    n1x, n1y = int(math.floor((cx + radius - origin) / dx)), int(math.floor((cy + radius - origin) / dx))
    out = {}
    if kind == "area":
        # Sub-sample every cell of the bounding window on a sub x sub grid: the share inside the circle
        s = (np.arange(sub) + 0.5) / sub
        for j in range(n0x, n1x + 1):
            for i in range(n0y, n1y + 1):
                xs = origin + (j + s) * dx
                ys = origin + (i + s) * dx
                X, Y = np.meshgrid(xs, ys)
                f = float(np.mean((X - cx) ** 2 + (Y - cy) ** 2 <= radius ** 2))
                if f > 0:
                    out[(i, j)] = f
    else:
        m = max(int(math.ceil(2 * math.pi * radius / dx * sub)), 64)    # points along the circle
        t = (np.arange(m) + 0.5) / m * 2 * math.pi
        px, py = cx + radius * np.cos(t), cy + radius * np.sin(t)
        cj = np.floor((px - origin) / dx).astype(int)
        ci = np.floor((py - origin) / dx).astype(int)
        for i, j in zip(ci, cj):
            out[(int(i), int(j))] = out.get((int(i), int(j)), 0.0) + 1.0
    if not out:                                                       # a disc smaller than one sample: a point
        return {(int(math.floor((cy - origin) / dx)), int(math.floor((cx - origin) / dx))): 1.0}
    tot = sum(out.values())
    return {k: v / tot for k, v in out.items()}


def energy(weights):
    """!
    @brief Pair energy E = sum w_a w_b a(a - b) of a weight dict (see lattice.effective_radius).
    @param weights dict {(i, j): w}.
    @return float E.
    """
    keys = list(weights)
    return _energy(keys, [weights[k] for k in keys])


def _energy(keys, w):
    """!
    @brief Pair energy of weights on integer cells.
    @param keys List of (i, j).
    @param w List of weights.
    @return float E.
    """
    o = np.array(keys, dtype=int)
    w = np.asarray(w, dtype=float)
    d = o[:, None, :] - o[None, :, :]
    return float(w @ lattice.a_of(d[..., 0], d[..., 1]) @ w)


def effective_radius(weights, dx):
    """!
    @brief Effective radius in m of a distributed sink.
    @param weights dict {(i, j): w}.
    @param dx Cell size in m.
    @return float ln r_eff = (pi / 2)(E - kappa) in lattice units, times dx.
    """
    keys = list(weights)
    e = _energy(keys, [weights[k] for k in keys])
    return dx * math.exp(math.pi / 2.0 * (e - lattice.KAPPA))


def mix_weights(w_a, w_b, beta):
    """!
    @brief Convex mixture (1 - beta) w_a + beta w_b of two weight dicts.
    @param w_a First dict {(i, j): w}.
    @param w_b Second dict.
    @param beta Share of the second.
    @return dict of the mixture.
    """
    out = {}
    for k, v in w_a.items():
        out[k] = out.get(k, 0.0) + (1.0 - beta) * v
    for k, v in w_b.items():
        out[k] = out.get(k, 0.0) + beta * v
    return out


def tuned_weights(cx, cy, r_via, dx, origin=0.0, r_point=None, sub=48):
    """!
    @brief Weights whose effective radius (mean-potential sense) equals the via radius.
    @details First the point in the cell of the centre (the program's choice) is mixed with the area weights of the disc of the via, with the share beta that gives the
             radius wanted. The area weights of a via on a cell corner are four equal quarters, whose effective radius (0.72 dx) is larger than any small via, so the mixture is
             needed; when even the pure disc is too small (a fine grid, where the disc covers many cells and its uniform area weights have a radius e^(-1/4) times that of
             the circle), the disc radius is enlarged instead until the radius wanted is reached.
    @param cx Centre x in m.
    @param cy Centre y in m.
    @param r_via Via radius in m (the effective radius wanted).
    @param dx Cell size in m.
    @param origin Lower edge of cell 0 in m.
    @param r_point Effective radius of a point sink in m (default 0.1985 dx).
    @param sub Samples per cell side for the area weights.
    @return dict {(i, j): w}, or None when the via is smaller than a point sink on this grid (a well is needed instead).
    """
    r0 = lattice.R_EQ_EXACT * dx if r_point is None else r_point
    if r_via <= r0:
        return None
    w_pt = disc_weights(cx, cy, 0.0, dx, origin)
    w_ar = disc_weights(cx, cy, r_via, dx, origin, sub, "area")
    if effective_radius(w_ar, dx) >= r_via:
        lo, hi = 0.0, 1.0
        for _ in range(40):                                              # r_eff grows with beta
            mid = 0.5 * (lo + hi)
            if effective_radius(mix_weights(w_pt, w_ar, mid), dx) < r_via:
                lo = mid
            else:
                hi = mid
        return mix_weights(w_pt, w_ar, 0.5 * (lo + hi))
    lo, hi = r_via, 2.0 * r_via
    while effective_radius(disc_weights(cx, cy, hi, dx, origin, sub, "area"), dx) < r_via:
        lo, hi = hi, 2.0 * hi
    for _ in range(30):                                                  # enlarge the disc until the radius is reached
        mid = 0.5 * (lo + hi)
        if effective_radius(disc_weights(cx, cy, mid, dx, origin, sub, "area"), dx) < r_via:
            lo = mid
        else:
            hi = mid
    return disc_weights(cx, cy, 0.5 * (lo + hi), dx, origin, sub, "area")


def disc_target_weights(cx, cy, r_via, r_target, dx, origin=0.0, sub=48):
    """!
    @brief Area weights of the via disc, enlarged only if its effective radius is below the radius wanted; always centred on the true position of the via.
    @details The footprint of the recommended treatment: the disc of the via itself (so that the barrel is where it is, not moved to the cell that holds its centre); when the
             lattice effective radius of that footprint is already above the target, the surplus is a positive Peaceman well and nothing else is done; when it is below (the disc
             lies inside one cell, or on fine cells where the uniform area weights have a radius e^(-1/4) times that of the circle), the radius of the disc is enlarged until the
             effective radius equals the target, which keeps the footprint centred.
    @param cx Centre x in m.
    @param cy Centre y in m.
    @param r_via Drill radius in m (the geometric disc).
    @param r_target Effective radius wanted in m.
    @param dx Cell size in m.
    @param origin Lower edge of cell 0 in m.
    @param sub Samples per cell side.
    @return dict {(i, j): w}.
    """
    w = disc_weights(cx, cy, r_via, dx, origin, sub, "area")
    if effective_radius(w, dx) >= r_target:
        return w
    lo, hi = r_via, 2.0 * r_via
    while effective_radius(disc_weights(cx, cy, hi, dx, origin, sub, "area"), dx) < r_target:
        lo, hi = hi, 2.0 * hi
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if effective_radius(disc_weights(cx, cy, mid, dx, origin, sub, "area"), dx) < r_target:
            lo = mid
        else:
            hi = mid
    return disc_weights(cx, cy, 0.5 * (lo + hi), dx, origin, sub, "area")


def kron_barrel(g_gap, g_well):
    """!
    @brief Conductances between the sheet nodes of the layers joined by a barrel with wells.
    @param g_gap Array (L-1,) of the barrel conductance of every gap in W/K (infinite values are allowed).
    @param g_well Array (L,) of the well conductance of every layer in W/K (0 = the layer has no contact with the barrel).
    @return numpy.ndarray (L, L) of the conductances G[l, m] (symmetric, zero diagonal) of the network that remains after eliminating the barrel nodes (Kron reduction).
    """
    g_gap = np.asarray(g_gap, dtype=float)
    g_well = np.asarray(g_well, dtype=float)
    n = len(g_well)
    if np.isinf(g_well).any():                                        # an infinite well: the sheet mean is the barrel potential
        finite = g_well[np.isfinite(g_well)]
        g_well = np.where(np.isinf(g_well), 1e12 * max(float(finite.max()) if finite.size else 0.0, float(np.max(g_gap[np.isfinite(g_gap)])) if np.isfinite(g_gap).any() else 1.0), g_well)
    # Nodal matrix of the whole star: [sheet nodes 0..n-1, barrel nodes n..2n-1]; the sheet nodes are the ones kept
    big = 1e15 * max(float(g_well.max()), 1e-30)
    gg = np.where(np.isfinite(g_gap), g_gap, big)
    Y = np.zeros((2 * n, 2 * n))

    def link(a, b, g):
        Y[a, a] += g
        Y[b, b] += g
        Y[a, b] -= g
        Y[b, a] -= g

    for l in range(n):
        link(l, n + l, g_well[l])
    for k in range(n - 1):
        link(n + k, n + k + 1, gg[k])
    Yss, Ysb, Ybb = Y[:n, :n], Y[:n, n:], Y[n:, n:]
    Yred = Yss - Ysb @ np.linalg.solve(Ybb + 1e-300 * np.eye(n), Ysb.T)
    G = -Yred.copy()
    np.fill_diagonal(G, 0.0)
    return G


def well_conductance(s_sheet, r_eq, r_via):
    """!
    @brief Peaceman well conductance of one sheet.
    @param s_sheet Sheet conductance S of the sheet at the via in W/K.
    @param r_eq Equivalent radius of the point sink on the grid in m.
    @param r_via Radius of the via in m.
    @return float 2 pi S / ln(r_eq / r_via) in W/K (infinite if r_eq <= r_via).
    """
    if r_eq <= r_via:
        return math.inf
    return 2.0 * math.pi * s_sheet / math.log(r_eq / r_via)
