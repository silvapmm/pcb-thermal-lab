#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_graded3d.py
@brief Tests of the reviewer's graded-grid solver: the 1D column of a bare top layer against the series circuit, the energy balance, the extrapolation of a refinement sequence.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))

import closed_forms as cf                                                   # noqa: E402
import graded3d as G                                                        # noqa: E402


def test_column_with_a_bare_top_layer_is_the_series_circuit():
    """!
    @brief A part over the whole board with no copper in the top layer is a 1D column: laminate (top layer and gap) then copper, films on both faces.
    @return None.
    """
    r = G.solve("2L 1.6 mm", 30e-3, scale=4.0, part=30e-3, window_layers=(0,))
    t, d = 35e-6, 1.6e-3 - 70e-6
    exact = cf.column_rise(1.0, (30e-3) ** 2, [(t, 0.3), (d, 0.3), (t, 385.0)], 10.0, 10.0)
    assert abs(r["peak"] / exact - 1.0) < 1e-9
    assert abs(r["balance"] - 1.0) < 1e-9


def test_window_board_balance_and_extrapolation():
    """!
    @brief The energy balance closes on a window board, and the fit v0 + C s^p recovers a known limit and order.
    @return None.
    """
    r = G.solve("2L 0.8 mm", 6e-3, scale=4.0)
    assert abs(r["balance"] - 1.0) < 1e-9
    v0, p = G.extrapolate((2.0, 1.0, 0.5), [10.0 + 3.0 * s ** 1.5 for s in (2.0, 1.0, 0.5)])
    assert abs(v0 - 10.0) < 1e-9 and abs(p - 1.5) < 1e-6
