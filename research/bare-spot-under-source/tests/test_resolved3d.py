#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_resolved3d.py
@brief Tests of the resolved 3D solver of the bare-spot investigation: series circuit, energy balance, a copper mask, the closed series of Muzychka et al. (2003).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))

import closed_forms as cf                                                   # noqa: E402
import resolved3d as r3                                                     # noqa: E402


def test_column_matches_series_circuit():
    """!
    @brief A source over the whole top face of an anisotropic three-slab column equals the series circuit (to round-off) and the energy balance closes.
    @return None.
    """
    n, dx = 6, 1e-3
    slabs = [(35e-6, 385.0, 385.0, 1), (0.5e-3, 0.9, 0.3, 5), (35e-6, 385.0, 385.0, 1)]
    r = r3.solve(dx, n, n, slabs, (0, 0, n * dx, n * dx), 2.0, 10.0, 200.0)
    exact = cf.column_rise(2.0, (n * dx) ** 2, [(35e-6, 385.0), (0.5e-3, 0.3), (35e-6, 385.0)], 10.0, 200.0)
    # The top face temperature is corrected from the cell centre; the column is exact for a linear profile
    assert abs(r["max"] - exact) / exact < 1e-6
    assert abs(r["balance"] - 1.0) < 1e-9


def test_plate_against_published_series():
    """!
    @brief A 4 x 4 mm source in the middle of a 10 x 10 x 1 mm isotropic plate (k 0.3, bottom film 500): the mean source rise equals Eq. 27 of Muzychka et al. within 1 %.
    @return None.
    """
    dx, n = 0.1e-3, 100
    r = r3.solve(dx, n, n, [(1e-3, 0.3, 0.3, 20)], (3e-3, 3e-3, 7e-3, 7e-3), 1.0, 0.0, 500.0)
    exact = cf.plate_mean_rise(10e-3, 10e-3, 4e-3, 4e-3, 5e-3, 5e-3, 1e-3, 0.3, 500.0, 1.0)
    assert abs(r["mean"] - exact) / exact < 0.01
    assert abs(r["balance"] - 1.0) < 1e-9


def test_window_mask_is_laminate_in_the_top_layer():
    """!
    @brief With the window the top layer is laminate there: the peak rises against full copper and the balance still closes.
    @return None.
    """
    n, dx = 20, 0.25e-3
    gaps, tcu = [0.2e-3], [35e-6, 35e-6]
    src = (2e-3, 2e-3, 3e-3, 3e-3)
    full = r3.solve(dx, n, n, r3.build_slabs(2, None, 385.0, gaps, tcu, 6, 0.9, 0.3), src, 1.0, 10.0, 100.0)
    m = r3.window_masks(n, n, dx, 2, (1.5e-3, 1.5e-3, 3.5e-3, 3.5e-3))
    win = r3.solve(dx, n, n, r3.build_slabs(2, m, 385.0, gaps, tcu, 6, 0.9, 0.3), src, 1.0, 10.0, 100.0)
    assert win["max"] > full["max"] * 1.5
    assert abs(win["balance"] - 1.0) < 1e-9


def test_vertical_convergence():
    """!
    @brief The peak over a bare window changes by under 1 % when the gap sub-slabs double.
    @return None.
    """
    n, dx = 16, 0.25e-3
    m = r3.window_masks(n, n, dx, 2, (0, 0, 3e-3, 3e-3))
    peaks = []
    for ns in (6, 12):
        peaks.append(r3.solve(dx, n, n, r3.build_slabs(2, m, 385.0, [0.3e-3], [35e-6, 35e-6], ns, 0.9, 0.3), (0, 0, 2e-3, 2e-3), 0.25, 10.0, 100.0)["max"])
    assert abs(peaks[0] - peaks[1]) / peaks[1] < 0.01
