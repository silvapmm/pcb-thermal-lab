#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_series.py
@brief Tests of the exact layered series (lib/series.py) against the series circuit, the published single-layer and two-layer solutions, and the semi-infinite limit.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "bare-spot-under-source", "lib"))

import closed_forms as CF                                                   # noqa: E402  (Muzychka, Culham, Yovanovich 2003, Eq. 27)
import series as S                                                          # noqa: E402
import yovanovich1999 as Y                                                  # noqa: E402


def test_whole_face_source_is_the_series_circuit():
    """!
    @brief A source over the whole top face has no spreading: the rise is the 1D column with the films (exact).
    @return None.
    """
    a = 20e-3
    layers = [(35e-6, 385.0, 385.0), (1.2e-3, 0.9, 0.3), (35e-6, 385.0, 385.0)]
    got = S.source_rise(a, a, layers, 10.0, 25.0, 2.0, (a / 2, a), (a / 2, a), nmax=50)[0]
    r_path = sum(t / kz for t, _, kz in layers) + 1.0 / 25.0
    want = 2.0 / a ** 2 / (10.0 + 1.0 / r_path)
    assert abs(got / want - 1) < 1e-12


def test_single_layer_matches_muzychka_2003():
    """!
    @brief One isotropic layer, a 4 mm source on a 10 mm plate: the series agrees with Eq. 27 of Muzychka, Culham and Yovanovich (2003) to 1e-4.
    @return None.
    """
    a, k, t, h = 10e-3, 0.3, 1e-3, 500.0
    want = CF.plate_mean_rise(a, a, 4e-3, 4e-3, a / 2, a / 2, t, k, h, 1.0)
    got = S.source_rise(a, a, [(t, k, k)], 0.0, h, 1.0, (a / 2, 4e-3), (a / 2, 4e-3), window=(4e-3, 4e-3), nmax=800)[0]
    assert abs(got / want - 1) < 1e-4


def test_two_layers_match_yovanovich_1999():
    """!
    @brief Two layers of very different conductivity (copper-like over FR-4-like): Rs of the series equals Eq. 14 with phi of Eq. 15 to 1e-5, and phi reduces to Eq. 17 for a deep second layer.
    @return None.
    """
    for t1, t2, k1, k2, h in [(1e-3, 1e-3, 10, 1, 500), (0.5e-3, 1.5e-3, 200, 0.3, 10), (0.035e-3, 1.6e-3, 385, 0.3, 10)]:
        want = Y.spreading_resistance(3e-3, 3e-3, 15e-3, 15e-3, t1, t2, k1, k2, h, terms=800)
        got = S.spreading_resistance(30e-3, 30e-3, 6e-3, 6e-3, [(t1, k1, k1), (t2, k2, k2)], h, nmax=800)
        assert abs(got / want - 1) < 1e-5
    # Eq. 17 (semi-infinite second layer)
    z = np.array([100.0, 500.0, 2000.0])
    kap = 0.3 / 200.0
    e = np.exp(2 * z * 0.5e-3)
    eq17 = ((e - 1) * kap + (e + 1)) / ((e + 1) * kap + (e - 1))
    assert np.allclose(Y.phi(z, 0.5e-3, 3.0, 200.0, 0.3, 10.0), eq17, rtol=1e-9)
