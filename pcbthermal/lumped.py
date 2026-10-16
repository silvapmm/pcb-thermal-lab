"""!
@file lumped.py
@brief Lumped-parameter thermal network (LPTN): one ring network per heater, superposed.

@details The model is the azimuthal average of the same per-cell network the FVM solver uses.
For every heater the board cells are binned in concentric rings by their distance to the
heater centroid (ring 0 is the heater footprint, the outer rings grow geometrically up to the
farthest board cell). For every layer and ring the quantities are aggregated from the real
geometry, so copper, vias, sinks and the board edges are seen where they actually are:

- lateral conduction between rings k and k+1 of a layer:
  G = 2 pi f S / ln(r_{k+1} / r_k), with S the harmonic mean of the ring sheet conductances,
  r the area-mean (rms) radius of the rings and f the fraction of the circle that lies inside
  the board (adiabatic edges, so a corner heater spreads over a quarter circle only),
- vertical conduction: the sum of the cell conductances of the ring (dielectric and vias),
- conductance to ambient: the sums of the cell conductances (top, bottom, sinks, edges).

Each heater gives a small dense linear system, solved exactly. Because the problem is linear,
the temperature at any point is the sum of the rises caused by every heater (mutual heating
comes from interpolating the radial profile of one heater at the distance of the other). The peak
inside a footprint adds the exact uniform-disc relation T_peak - T_mean = Q_lateral / (8 pi S).
"""

import numpy as np

from .fvm import Network
from .geometry import polygon_area, polygon_centroid
from .results import SteadyResult


def _ring_network(net, cx, cy, layer, power, rings, r_foot):
    """!
    @brief Build and solve the ring network of one heater.
    @param net Network (per-cell arrays) of the problem.
    @param cx Heater centroid x (m).
    @param cy Heater centroid y (m).
    @param layer 0-based heater layer.
    @param power Heater power (W).
    @param rings Number of rings outside the footprint.
    @param r_foot Equivalent footprint radius (m).
    @return Dict with theta (L, R), r_rms (R), peak_extra, S0 and the heat leaving by each path.
    """
    L, ny, nx = net.nl, net.ny, net.nx
    cell = net.dx * net.dy
    xs = (np.arange(nx) + 0.5) * net.dx
    ys = (np.arange(ny) + 0.5) * net.dy
    d = np.hypot(xs[None, :] - cx, ys[:, None] - cy)               # Distance of every cell centre

    # --- Ring membership: ring 0 = footprint, then geometric growth up to the farthest cell
    r_max = max(d.max() * 1.0000001, r_foot * 1.5)
    bounds = r_foot * (r_max / r_foot) ** (np.arange(rings + 1) / rings)
    idx = np.minimum(np.searchsorted(bounds, d, side="right"), rings)
    cnt = np.bincount(idx.ravel(), minlength=rings + 1)
    # Remap so that no ring is empty (very thin rings on a coarse grid)
    used = np.flatnonzero(cnt > 0)
    remap = np.full(rings + 1, -1)
    remap[used] = np.arange(len(used))
    idx = remap[idx]
    R = len(used)
    cnt = cnt[used]
    area = cnt * cell
    flat = idx.ravel()

    def ring_sum(a):
        # Sum of a per-cell array over the cells of every ring
        return np.bincount(flat, weights=a.ravel(), minlength=R)

    r_rms = np.sqrt(ring_sum(d ** 2) / cnt)
    r_in = np.concatenate([[0.0], bounds[used][:-1]]) if R > 1 else np.array([0.0])
    r_out = bounds[used]
    full_area = np.pi * (r_out ** 2 - r_in ** 2)
    arc = np.clip(area / np.maximum(full_area, 1e-30), 1e-3, 1.0)   # Fraction of each ring inside the board

    S = np.array([ring_sum(net.S[l]) / cnt for l in range(L)])       # Mean sheet conductance (W/K)
    g_top = np.array([ring_sum(net.g_top[l]) for l in range(L)])
    g_bot = np.array([ring_sum(net.g_bottom[l]) for l in range(L)])
    g_sink = np.array([ring_sum(net.g_sink[l]) for l in range(L)])
    g_side = np.array([ring_sum(net.g_side[l]) for l in range(L)])
    gz = np.array([ring_sum(net.gz[l]) for l in range(L - 1)]) if L > 1 else np.zeros((0, R))

    n = L * R
    K = np.zeros((n, n))

    def couple(a, b, g):
        K[a, a] += g
        K[b, b] += g
        K[a, b] -= g
        K[b, a] -= g

    for l in range(L):
        for k in range(R - 1):
            s_h = 2.0 * S[l, k] * S[l, k + 1] / (S[l, k] + S[l, k + 1])
            f = 0.5 * (arc[k] + arc[k + 1])
            ln = max(np.log(r_rms[k + 1] / max(r_rms[k], 1e-12)), 1e-3)
            couple(l * R + k, l * R + k + 1, 2.0 * np.pi * f * s_h / ln)
        if l < L - 1:
            for k in range(R):
                couple(l * R + k, (l + 1) * R + k, gz[l, k])
    g_amb = (g_top + g_bot + g_sink + g_side).ravel()
    K[np.arange(n), np.arange(n)] += g_amb
    Q = np.zeros(n)
    Q[layer * R] = power
    theta = np.linalg.solve(K, Q)
    th = theta.reshape(L, R)

    # --- Peak inside the footprint from the lateral outflow of ring 0
    lat = 2.0 * np.pi * 0.5 * (arc[0] + arc[1]) * S[layer, 0] / max(np.log(r_rms[1] / r_rms[0]), 1e-3) * (th[layer, 0] - th[layer, 1]) if R > 1 else 0.0
    peak_extra = max(lat, 0.0) / (8.0 * np.pi * S[layer, 0])
    return {"theta": th, "r_rms": r_rms, "peak_extra": peak_extra, "S0": S[layer, 0],
            "out": {"top": float((g_top * th).sum()), "bottom": float((g_bot * th).sum()),
                    "sinks": float((g_sink * th).sum()), "sides": float((g_side * th).sum())},
            "residual": float(np.linalg.norm(K @ theta - Q) / np.linalg.norm(Q))}


def solve_steady(problem, rings=10, cell_mm=1.0):
    """!
    @brief Steady-state solution of the ring networks (one per heater) with superposition.
    @param problem A Problem.
    @param rings Number of rings outside each footprint (more rings = finer radial resolution).
    @param cell_mm Raster size (mm) used to aggregate the real geometry into rings.
    @return SteadyResult with an approximate temperature field T of shape (layers, ny, nx).
    """
    problem.validate()
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 8)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 8)
    net = Network(problem, nx, ny, assemble=False)
    L = net.nl
    power = problem.total_power()
    xs = (np.arange(nx) + 0.5) * net.dx
    ys = (np.arange(ny) + 0.5) * net.dy

    theta_field = np.zeros((L, ny, nx))
    nets, centres = [], []
    out = {"top": 0.0, "bottom": 0.0, "sinks": 0.0, "sides": 0.0}
    res = 0.0
    for h in problem.heaters:
        if h.power <= 0:
            continue
        cx, cy = polygon_centroid(h.polygon)
        r_foot = max(np.sqrt(polygon_area(h.polygon) / np.pi), 0.5 * max(net.dx, net.dy))
        rn = _ring_network(net, cx, cy, h.layer, h.power, rings, r_foot)
        nets.append((h, rn))
        centres.append((cx, cy))
        d = np.hypot(xs[None, :] - cx, ys[:, None] - cy)
        for l in range(L):
            # Radial profile interpolated at the distance of every cell (constant outside the ring range)
            theta_field[l] += np.interp(d, rn["r_rms"], rn["theta"][l])
        for k in out:
            out[k] += rn["out"][k]
        res = max(res, rn["residual"])

    T = theta_field + b.ambient
    # --- Peaks: own footprint peak plus the rise caused by the other heaters at its centroid
    t_peak, where = float(T.max()), (0, 0.0, 0.0)
    for j, (hj, rj) in enumerate(nets):
        theta_j = rj["theta"][hj.layer, 0] + rj["peak_extra"]
        for i, (hi, ri) in enumerate(nets):
            if i != j:
                dist = np.hypot(centres[j][0] - centres[i][0], centres[j][1] - centres[i][1])
                theta_j += np.interp(dist, ri["r_rms"], ri["theta"][hj.layer])
        if theta_j + b.ambient > t_peak:
            t_peak, where = float(theta_j + b.ambient), (hj.layer, centres[j][0], centres[j][1])
    if where == (0, 0.0, 0.0) and nets:
        l, i, j = np.unravel_index(int(np.argmax(T)), T.shape)
        where = (int(l), float(xs[j]), float(ys[i]))

    return SteadyResult(
        model="lumped", ambient=b.ambient, power_in=power, t_max=t_peak, t_min=float(T.min()),
        t_mean=float(T.mean()), layer_mean=[float(T[l].mean()) for l in range(L)],
        t_max_location=where, T=T, dx=net.dx, dy=net.dy, power_out=out, residual=res,
        extras={"heater_networks": float(len(nets)), "rings": float(rings),
                "peak_correction_k": float(max((r["peak_extra"] for _, r in nets), default=0.0))},
    )
