#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_plate_series.py
@brief The series reference against the independent 3D solver and the closed 1D column.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path[:0] = [os.path.join(HERE, "..", "lib"), os.path.join(ROOT, "tests", "helpers")]
import layered3d as L                                          # noqa: E402
import plate_series as ps                                      # noqa: E402


def test_one_dimensional_column():
    """!
    @brief A source as large as a plate side (a ~ W): the difference tends to q t / (2 k) of the column.
    @return None.
    """
    W, t, k, h = 0.05, 0.002, 150.0, 400.0
    s, m = ps.rises(W, W * 0.999, t, k, h, q=1000.0, modes=200)
    assert abs((s - m) - 1000.0 * t / (2 * k)) / (1000.0 * t / (2 * k)) < 2e-3


def test_against_layered3d():
    """!
    @brief Surface and thickness-mean rise at the centre against the finite-volume 3D solver (adiabatic top, film bottom).
    @return None.
    """
    W, a, t, k, h, P = 0.05, 0.01, 0.005, 150.0, 400.0, 10.0
    dx, n = 0.5e-3, 100
    c = W / 2
    r = L.solve(dx, n, n, [(t, k, 8)], (c - a / 2, c - a / 2, c + a / 2, c + a / 2), P, 0.0, h)
    dz = np.array(r["dz"])
    col = np.tensordot(dz / dz.sum(), r["T"], axes=(0, 0))
    j = n // 2
    sl = (slice(j - 1, j + 1), slice(j - 1, j + 1))
    s3, m3 = float(r["surface_top"][sl].mean()), float(col[sl].mean())
    s, m = ps.rises(W, a, t, k, h, P / a**2, modes=300)
    assert abs(s - s3) / s3 < 0.01 and abs((s - m) - (s3 - m3)) / (s3 - m3) < 0.05


def test_biot_limits():
    """!
    @brief Small Bi and thin plate: the fraction goes to zero; thick plate with strong film: it grows.
    @return None.
    """
    assert ps.delta_fraction(1e-4, 0.01) < 1e-3
    assert ps.delta_fraction(0.3, 2.0) > 0.1


def test_busbar_closed_form():
    """!
    @brief Joule-heated slab with a film on both faces: (mean - surface) / surface rise = Bi / 6 (checked by integrating the parabola numerically).
    @return None.
    """
    t, k, h, g = 3e-3, 385.0, 15.0, 1e6
    z = np.linspace(-t / 2, t / 2, 200001)
    ts = g * t / (2 * h)                                         # surface rise: g t / 2 leaves through each face
    T = ts + g * (t**2 / 4 - z**2) / (2 * k)
    assert abs((T.mean() - T[0]) / T[0] - (h * t / k) / 6) < 1e-6


def test_plate_width_is_a_third_group():
    """!
    @brief Review: the fraction depends on the plate width W/a, not only on Bi and t/a. The 2 mm copper plate (h 1000, 4 mm source) of study_thick_cases.py,
           50 mm wide (12.5 a), reads 10.72 % in the independent 3D solver; the series at that width reproduces it, and at 5 a the same Bi and t/a read about a third.
    @return None.
    """
    s, m = ps.rises(0.05, 4e-3, 2e-3, 385.0, 1000.0, 10.0 / 16e-6, modes=400)
    assert abs(100 * (s - m) / s - 10.72) < 0.2
    bi, ta = 1000.0 * 2e-3 / 385.0, 0.5
    assert ps.delta_fraction(bi, ta, 12.5) > 2.5 * ps.delta_fraction(bi, ta, 5.0)
