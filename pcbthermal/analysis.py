#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file analysis.py
@brief Post-processing of steady results: hotspots, gradients, zone and heater statistics.

All functions take a SteadyResult that carries a temperature field (T is not None) and,
where needed, the Problem that produced it.
"""

import numpy as np
from scipy import ndimage

from .geometry import BOARD_SAMPLES, coverage_fraction, part_weights, points_in_polygon


def _require_field(result):
    """!
    @brief Make sure a result carries a temperature field.
    @param result A SteadyResult.
    @throws ValueError If the model does not resolve a field.
    """
    if result.T is None:
        raise ValueError(f"the '{result.model}' result has no temperature field")


def hotspots(result, threshold):
    """!
    @brief Connected regions hotter than a threshold, per layer.
    @param result A SteadyResult with a field.
    @param threshold Temperature limit in degC.
    @return List of dicts sorted by temperature: layer (1-based), t_max, x_mm, y_mm, area_mm2, cells.
    """
    _require_field(result)
    out = []
    cell_area = result.dx * result.dy
    xs, ys = result.coords()
    for l in range(result.T.shape[0]):
        mask = result.T[l] > threshold
        labels, n = ndimage.label(mask)
        for k in range(1, n + 1):
            region = labels == k
            vals = np.where(region, result.T[l], -np.inf)
            i, j = np.unravel_index(int(np.argmax(vals)), vals.shape)
            out.append({"layer": l + 1, "t_max": float(vals[i, j]),
                        "x_mm": xs[j] * 1000.0, "y_mm": ys[i] * 1000.0,
                        "area_mm2": float(region.sum() * cell_area * 1e6), "cells": int(region.sum())})
    return sorted(out, key=lambda r: -r["t_max"])


def gradient_magnitude(result):
    """!
    @brief Magnitude of the in-plane temperature gradient of every layer.
    @param result A SteadyResult with a field.
    @return Array (layers, ny, nx) in K/mm.
    """
    _require_field(result)
    g = np.empty_like(result.T)
    for l in range(result.T.shape[0]):
        gy, gx = np.gradient(result.T[l], result.dy * 1000.0, result.dx * 1000.0)
        g[l] = np.hypot(gx, gy)
    return g


def _board_mask(result, outline):
    """!
    @brief Which samples of a result field lie on the board (cells or nodes the models take as on the board).
    @details Off the board the FVM, FDM and 3D solid pin the field to the ambient (and the Lumped and Analytic fields, stretched back from
             the rectangle of the same area, hold values that belong to no board), so a statistic over a polygon that crosses the outline
             must leave those samples out. The test is the one of the models: board cover of at least 0.01, sampled BOARD_SAMPLES x BOARD_SAMPLES (8 x 8) on the cells
             (FVM, 3D solid) and the same lattice averaged on the nodes (FDM).
    @param result A SteadyResult with a field.
    @param outline Board outline vertices (n, 2) in metres, or None for a rectangular board.
    @return Boolean array (ny, nx) of the field, or None for a rectangular board (every sample is on it).
    """
    if outline is None:
        return None
    ny, nx = result.T.shape[1:]
    if result.grid == "nodes":
        # The node control volume shares the four cells around the node (as fdm._node_average does)
        c = coverage_fraction(outline, nx - 1, ny - 1, result.dx, result.dy, BOARD_SAMPLES)
        acc = np.zeros((ny, nx))
        cnt = np.zeros((ny, nx))
        for di in (0, 1):
            for dj in (0, 1):
                acc[di:di + ny - 1, dj:dj + nx - 1] += c
                cnt[di:di + ny - 1, dj:dj + nx - 1] += 1.0
        return acc / cnt >= 0.01
    return coverage_fraction(outline, nx, ny, result.dx, result.dy, BOARD_SAMPLES) >= 0.01


def _footprint_stats(result, polygon, layer, outline=None):
    """!
    @brief Coverage-weighted mean and maximum temperature under a polygon on one layer, over the part of it that is on the board.
    @details With an outline, a cell is weighted by the share of it that is both in the polygon and on the board (the cells off the board
             hold the ambient and would pull the mean and the minimum down); without one the weight is the coverage of the polygon.
    @param result A SteadyResult with a field.
    @param polygon Vertices (n, 2) in metres.
    @param layer 0-based layer.
    @param outline Board outline vertices (n, 2) in metres, or None for a rectangular board.
    @return Tuple (mean, max, min) or (nan, nan, nan) if the polygon covers no cell of the board.
    """
    ny, nx = result.T.shape[1:]
    on_board = _board_mask(result, outline)
    if result.grid == "nodes":
        # A node field has no cells: use the nodes inside the polygon (with the left and bottom edge in)
        xs, ys = result.coords()
        X, Y = np.meshgrid(xs, ys)
        cov = points_in_polygon(X.ravel(), Y.ravel(), polygon).reshape(X.shape).astype(float)
    else:
        # Share of every cell in the polygon and on the board (the plain coverage without an outline)
        # Same lattice as the models on an outline; the plain 4 x 4 coverage of a rectangular board is kept (its numbers do not change)
        cov = part_weights(polygon, outline, nx, ny, result.dx, result.dy, samples=BOARD_SAMPLES if outline is not None else 4)
    if on_board is not None:
        cov = cov * on_board
    if cov.sum() <= 0:
        return float("nan"), float("nan"), float("nan")
    T = result.T[min(layer, result.T.shape[0] - 1)]
    inside = cov > 0
    return float((T * cov).sum() / cov.sum()), float(T[inside].max()), float(T[inside].min())


def zone_stats(result, problem):
    """!
    @brief Mean, maximum and minimum temperature of every copper zone.
    @param result A SteadyResult with a field.
    @param problem The Problem that owns the zones.
    @return List of dicts: name, layer (1-based), t_mean, t_max, t_min.
    """
    _require_field(result)
    rows = []
    for k, z in enumerate(problem.zones):
        mean, mx, mn = _footprint_stats(result, z.polygon, z.layer, problem.board.outline)
        rows.append({"name": z.name or f"Zone {k + 1}", "layer": z.layer + 1,
                     "t_mean": mean, "t_max": mx, "t_min": mn})
    return rows


RING_INNER = 0.5e-3           # The reference ring of the junction-to-board parameter starts 0.5 mm outside the package outline (m)
RING_OUTER = 1.5e-3           # and ends 1.5 mm outside it, around the 1 mm of the JEDEC definition (m)


def _ring_mean(result, polygon, layer, outline=None):
    """!
    @brief Mean board temperature in a ring around a footprint (the reference of the junction-to-board characterisation parameter).
    @param result A SteadyResult with a field.
    @param polygon Footprint vertices (n, 2) in metres; its bounding box is the package outline.
    @param layer 0-based layer of the part.
    @param outline Board outline vertices (n, 2) in metres, or None for a rectangular board; the samples of the ring off the board are left out.
    @return Mean temperature in degC, or None when the grid has no cell centre of the board in the ring (a coarse grid).
    """
    xs, ys = result.coords()
    x0, y0 = polygon.min(axis=0)
    x1, y1 = polygon.max(axis=0)
    X, Y = np.meshgrid(xs, ys)
    outer = (X >= x0 - RING_OUTER) & (X <= x1 + RING_OUTER) & (Y >= y0 - RING_OUTER) & (Y <= y1 + RING_OUTER)
    inner = (X >= x0 - RING_INNER) & (X <= x1 + RING_INNER) & (Y >= y0 - RING_INNER) & (Y <= y1 + RING_INNER)
    ring = outer & ~inner
    on_board = _board_mask(result, outline)
    if on_board is not None:
        ring &= on_board                         # Off the board the field is the ambient: not a board temperature
    if not ring.any():
        return None
    return float(result.T[min(layer, result.T.shape[0] - 1)][ring].mean())


def part_split(heater, t_max, power, ambient):
    """!
    @brief Junction temperature and the heat taken by the top path of one part, for the hottest board point under it.
    @details Junction node joined to the board by theta and to the ambient by the top resistance R: with P_b the heat into the board,
             Tj - Ta = (T_max - Ta) + P_b theta and P_b = P - (Tj - Ta)/R, hence Tj - Ta = (T_max - Ta + P theta)/(1 + theta/R).
             The top heat is limited to [0, P] (the board does not feed the part). Without a top path all the power enters the board.
    @param heater A Heater.
    @param t_max Hottest board temperature under the footprint in degC.
    @param power Total power dissipated by the part in W.
    @param ambient Ambient temperature in degC.
    @return Tuple (t_junction or None without theta in degC, power_top in W).
    """
    theta = heater.junction_theta()                      # A component: its junction-to-pad theta; a pure source: the interface under it (0 = direct contact)
    if theta <= 0:
        return None, 0.0
    r_top = heater.top_resistance()
    if r_top <= 0:
        return t_max + power * theta, 0.0
    rise = (t_max - ambient + power * theta) / (1.0 + theta / r_top)
    p_top = min(max(rise / r_top, 0.0), power)
    return t_max + (power - p_top) * theta, p_top


def heater_stats(result, problem, powers=None):
    """!
    @brief Temperatures under every heater and, for a part, the junction temperature, its margin and the power limit.
    @details With the junction-to-pad resistance theta Tj = hottest board point under the footprint + P_board theta (worst case: P_board = P, all the power enters the board;
             with a top path P_board = P minus the heat of the top path, see part_split);
             with psi_jb the second estimate is Tj = mean board temperature in the 0.5 to 1.5 mm ring around the outline + psi_jb P. The device temperature
             used for the limit is Tj (or the hottest point under a part without theta). The power limit is the dissipation that brings the device to tj_max
             with the board's response of this run (linear in the power for constant coefficients).
    @param result A SteadyResult with a field.
    @param problem The Problem that owns the heaters.
    @param powers Powers actually dissipated in W, one per heater (default: the powers of the problem; they differ when a power temperature coefficient is set).
    @return List of dicts: name, layer (1-based), power_w, power_nominal_w (the power typed), t_mean, t_max, t_junction (None without theta), t_ring (None on a coarse grid),
            t_junction_psi (None without psi_jb), power_top_w and power_board_w (split of the power between the top path and the board), r_top (K/W, 0 without a top path), tj_max (0 = none), margin_k (None without tj_max), p_limit_w (None without tj_max), theta, psi_jb, power_tc.
    """
    _require_field(result)
    rows = []
    amb = result.ambient
    for k, h in enumerate(problem.heaters):
        power = h.power if powers is None else float(powers[k])
        mean, mx, _ = _footprint_stats(result, h.polygon, h.layer, problem.board.outline)
        tj, p_top = part_split(h, mx, power, amb)
        device = tj if tj is not None else mx
        ring = _ring_mean(result, h.polygon, h.layer, problem.board.outline)
        row = {"name": h.name or f"Heater {k + 1}", "layer": h.layer + 1, "power_w": power, "t_mean": mean, "t_max": mx,
               "power_nominal_w": h.power, "t_junction": tj, "t_ring": ring,
               "t_junction_psi": ring + (power - p_top) * h.psi_jb if (h.psi_jb > 0 and ring is not None) else None,
               "tj_max": h.tj_max, "margin_k": h.tj_max - device if h.tj_max > 0 else None, "p_limit_w": None,
               "theta": h.junction_theta(), "psi_jb": h.psi_jb, "power_tc": h.power_tc,
               "power_top_w": p_top, "power_board_w": power - p_top, "r_top": h.top_resistance()}
        if h.tj_max > 0 and power > 0 and device > amb:
            row["p_limit_w"] = power * (h.tj_max - amb) / (device - amb)
        rows.append(row)
    return rows


def block_stats(result, problem):
    """!
    @brief Temperature of the metal blocks and the heat they take, one row per face that carries blocks.
    @param result A SteadyResult from the FVM or the FDM (other models have no blocks).
    @param problem The Problem that owns the heatsinks.
    @return List of dicts: name, face ("top" or "bottom"), t_mean, t_max, w_to_block (heat entering the block through the interface,
            W) and w_to_air (heat leaving through its exposed surface, W); empty without blocks.
    """
    rows = []
    n = problem.board.layers
    for face, tag in ((0, "top"), (1, "bottom")):
        if f"block_{tag}_max" not in result.extras:
            continue
        names = [s.name or f"Heatsink {k + 1}" for k, s in enumerate(problem.heatsinks)
                 if s.is_block() and (0 if (s.layer == 0 or n == 1) else 1) == face]
        rows.append({"name": ", ".join(names), "face": tag, "t_mean": result.extras[f"block_{tag}_mean"],
                     "t_max": result.extras[f"block_{tag}_max"], "w_to_block": result.extras[f"block_{tag}_w_to_block"],
                     "w_to_air": result.extras[f"block_{tag}_w_to_air"]})
    return rows

