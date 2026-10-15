"""!
@file lumped.py
@brief Lumped-parameter thermal network (LPTN): concentric rings per layer, solved exactly.

@details The heat spreads from the heater footprint into the rest of the board. The model
replaces the footprint by a disc of equal area and the board by a disc of equal area, and splits
the annulus between them into geometrically growing rings. Every layer has the same rings, so
the network has layers x (rings + 1) nodes:

- ring-to-ring conduction in a layer: G = 2 pi S / ln(r_b / r_a), where r_a, r_b are the
  area-mean radii of the two rings and S is the sheet conductance of the layer [W/K],
- layer-to-layer conduction: G = (k_fr4_through * A + n_via * k_cu * A_via) / d,
- convection to ambient on the outer surfaces (plus sinks and the edge on the last ring).

The linear system K*theta = Q is small and dense, so it is solved exactly. The peak inside the
heater footprint is estimated from the exact uniform-disc relation
T_peak - T_mean = Q_lateral / (8 pi S).
"""

import numpy as np

from .geometry import coverage_fraction, points_in_polygon, polygon_area
from .results import SteadyResult


def solve_steady(problem, rings=8, cell_mm=1.0):
    """!
    @brief Steady-state solution of the ring network.
    @param problem A Problem.
    @param rings Number of rings outside the heater footprint (more rings = finer spreading).
    @param cell_mm Raster size (mm) used to measure footprint, copper and sink areas.
    @return SteadyResult (T is None; the ring temperatures are stored in result.arrays).
    """
    problem.validate()
    b = problem.board
    m = b.materials
    W, H, Ln = b.width, b.height, b.layers
    A_pcb = W * H
    slab = b.thickness / Ln
    nx = max(int(round(W * 1000.0 / cell_mm)), 2)
    ny = max(int(round(H * 1000.0 / cell_mm)), 2)
    dx, dy = W / nx, H / ny
    cell = dx * dy
    power = problem.total_power()

    if power <= 0:
        # Nothing to simulate: the board stays at ambient
        return SteadyResult(model="lumped", ambient=b.ambient, power_in=0.0, t_max=b.ambient,
                            t_min=b.ambient, t_mean=b.ambient, layer_mean=[b.ambient] * Ln)

    # --- Footprint of all heaters (union on the raster) and its area
    foot = np.zeros((ny, nx))
    for h in problem.heaters:
        foot = np.maximum(foot, coverage_fraction(h.polygon, nx, ny, dx, dy, 4))
    A_h = float(foot.sum() * cell)
    A_h = min(max(A_h, cell), 0.95 * A_pcb)
    A_b = A_pcb - A_h

    # --- Ring geometry: equivalent radii, geometric growth of the outer radii
    r_h = np.sqrt(A_h / np.pi)
    r_b = np.sqrt(A_pcb / np.pi)
    edges = r_h * (r_b / r_h) ** (np.arange(rings + 1) / rings)         # r_h ... r_b
    r_out = np.concatenate([[r_h], edges[1:]])                          # Outer radius of ring 0..rings
    r_in = np.concatenate([[0.0], edges[:-1]])                          # Inner radius of ring 0..rings
    area = np.pi * (r_out ** 2 - r_in ** 2)                             # Ring areas (m2)
    area *= A_pcb / area.sum()                                          # Remove round-off
    r_mean = np.sqrt((r_out ** 2 + r_in ** 2) / 2.0)                    # Area-mean radius of each ring
    R = rings + 1                                                       # Rings per layer, incl. footprint
    w_ring = area / A_pcb

    # --- Copper fill of the footprint (ring 0) and of the rest of the board per layer
    fill_in = np.zeros(Ln)
    fill_out = np.zeros(Ln)
    for l in range(Ln):
        f = np.zeros((ny, nx))
        for z in problem.zones:
            if z.layer == l:
                f = np.maximum(f, coverage_fraction(z.polygon, nx, ny, dx, dy, 4) * z.fill)
        w_in = foot.sum()
        fill_in[l] = (f * foot).sum() / w_in if w_in > 0 else 0.0
        fill_out[l] = (f * (1 - foot)).sum() / max((1 - foot).sum(), 1e-12)
    tc = np.asarray(b.copper_thickness)
    S_in = fill_in * m.k_copper * tc + m.k_fr4_inplane * (slab - fill_in * tc)     # (Ln,)
    S_out = fill_out * m.k_copper * tc + m.k_fr4_inplane * (slab - fill_out * tc)

    # --- Vias split between the footprint and the rest of the board
    n_in = 0.0
    a_in = 0.0
    a_out = 0.0
    for v in problem.vias:
        a_v = v.copper_area(b.via_plating)
        inside = any(points_in_polygon(np.array([v.x]), np.array([v.y]), h.polygon)[0]
                     for h in problem.heaters)
        if inside:
            a_in += a_v
        else:
            a_out += a_v

    # --- Sink areas (times their extra coefficient) inside the footprint and elsewhere, per layer
    sink_in = np.zeros(Ln)
    sink_out = np.zeros(Ln)
    for s in problem.sinks:
        cov = coverage_fraction(s.polygon, nx, ny, dx, dy, 4)
        sink_in[s.layer] += s.h_extra * float((cov * foot).sum() * cell)
        sink_out[s.layer] += s.h_extra * float((cov * (1 - foot)).sum() * cell)

    # --- Assemble K (W/K) and Q (W); node index = layer * R + ring
    n = Ln * R
    K = np.zeros((n, n))
    Q = np.zeros(n)
    g_top = np.zeros(n)
    g_bot = np.zeros(n)
    g_sink = np.zeros(n)
    g_side = np.zeros(n)

    def couple(a, bb, g):
        # Symmetric conductance between nodes a and bb
        K[a, a] += g
        K[bb, bb] += g
        K[a, bb] -= g
        K[bb, a] -= g

    for l in range(Ln):
        base = l * R
        # Lateral conduction between consecutive rings of the layer
        for k in range(R - 1):
            S_k = S_in[l] if k == 0 else S_out[l]
            couple(base + k, base + k + 1, 2.0 * np.pi * S_k / np.log(r_mean[k + 1] / r_mean[k]))
        # Convection and sinks
        for k in range(R):
            a = area[k]
            if l == 0:
                g_top[base + k] += b.h_top * a
            if l == Ln - 1:
                g_bot[base + k] += b.h_bottom * a
            g_sink[base + k] += sink_in[l] if k == 0 else sink_out[l] * (area[k] / A_b)
        if b.h_side:
            # Edge faces hang on the outermost ring: perimeter of the board x slab thickness
            g_side[base + R - 1] += b.h_side * 2 * (W + H) * slab
        # Vertical conduction to the next layer
        if l < Ln - 1:
            d = b.dielectric_thickness()
            for k in range(R):
                a_via = a_in if k == 0 else a_out * (area[k] / A_b)
                g = (m.k_fr4_through * area[k] + m.k_copper * a_via) / d
                couple(base + k, base + R + k, g)
    g_amb = g_top + g_bot + g_sink + g_side
    K[np.arange(n), np.arange(n)] += g_amb

    # --- Heat sources enter the footprint ring of the heater layer
    for h in problem.heaters:
        Q[h.layer * R] += h.power

    theta = np.linalg.solve(K, Q)
    res = float(np.linalg.norm(K @ theta - Q) / np.linalg.norm(Q))
    th = theta.reshape(Ln, R)

    # --- Peak inside the footprint: uniform-disc relation using the lateral outflow of ring 0
    lat_out = 2.0 * np.pi * S_in / np.log(r_mean[1] / r_mean[0]) * (th[:, 0] - th[:, 1])
    peak_extra = np.maximum(lat_out, 0.0) / (8.0 * np.pi * S_in)
    layer_peak = th[:, 0] + peak_extra
    T = th + b.ambient
    t_max = float(layer_peak.max() + b.ambient)

    layer_mean = [float((T[l] * w_ring).sum()) for l in range(Ln)]
    p_out = {"top": float((g_top * theta).sum()), "bottom": float((g_bot * theta).sum()),
             "sinks": float((g_sink * theta).sum()), "sides": float((g_side * theta).sum())}
    return SteadyResult(
        model="lumped", ambient=b.ambient, power_in=power, t_max=t_max,
        t_min=float(T.min()), t_mean=float(np.mean(layer_mean)), layer_mean=layer_mean,
        t_max_location=(int(np.argmax(layer_peak)), W / 2, H / 2), power_out=p_out, residual=res,
        extras={"footprint_area_mm2": A_h * 1e6, "footprint_mean_c": float(T[:, 0].max()),
                "peak_correction_k": float(peak_extra.max()), "rings": float(rings)},
        arrays={"ring_radius_m": r_mean, "ring_temps_c": T},
    )
