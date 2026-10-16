"""!
@file analysis.py
@brief Post-processing of steady results: hotspots, gradients, zone and heater statistics.

All functions take a SteadyResult that carries a temperature field (T is not None) and,
where needed, the Problem that produced it.
"""

import numpy as np
from scipy import ndimage

from .geometry import coverage_fraction


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
    for l in range(result.T.shape[0]):
        mask = result.T[l] > threshold
        labels, n = ndimage.label(mask)
        for k in range(1, n + 1):
            region = labels == k
            vals = np.where(region, result.T[l], -np.inf)
            i, j = np.unravel_index(int(np.argmax(vals)), vals.shape)
            out.append({"layer": l + 1, "t_max": float(vals[i, j]),
                        "x_mm": (j + 0.5) * result.dx * 1000.0, "y_mm": (i + 0.5) * result.dy * 1000.0,
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


def _footprint_stats(result, polygon, layer):
    """!
    @brief Coverage-weighted mean and maximum temperature under a polygon on one layer.
    @param result A SteadyResult with a field.
    @param polygon Vertices (n, 2) in metres.
    @param layer 0-based layer.
    @return Tuple (mean, max, min) or (nan, nan, nan) if the polygon covers no cell.
    """
    ny, nx = result.T.shape[1:]
    cov = coverage_fraction(polygon, nx, ny, result.dx, result.dy, samples=4)
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
        mean, mx, mn = _footprint_stats(result, z.polygon, z.layer)
        rows.append({"name": z.name or f"Zone {k + 1}", "layer": z.layer + 1,
                     "t_mean": mean, "t_max": mx, "t_min": mn})
    return rows


def heater_stats(result, problem):
    """!
    @brief Temperatures under every heater, including the junction temperature when theta_jb is set.
    @param result A SteadyResult with a field.
    @param problem The Problem that owns the heaters.
    @return List of dicts: name, layer (1-based), power_w, t_mean, t_max, t_junction (None without theta_jb).
    """
    _require_field(result)
    rows = []
    for k, h in enumerate(problem.heaters):
        mean, mx, _ = _footprint_stats(result, h.polygon, h.layer)
        rows.append({"name": h.name or f"Heater {k + 1}", "layer": h.layer + 1, "power_w": h.power,
                     "t_mean": mean, "t_max": mx,
                     "t_junction": mx + h.power * h.theta_jb if h.theta_jb > 0 else None})
    return rows
