#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_batch1_sources.py
@brief Tests of the scripts of the reading pass (README section 8): each checks a number printed in a source that was read, or a closed-form limit.
@details Run: .venv/bin/python -m pytest -q research/theory-sources/tests/test_batch1_sources.py (from the repository root; a few seconds).
"""

import sys
from pathlib import Path

import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import study_flux_tube_sources as ft  # noqa: E402
import study_lee_lemczyk_vias as lly  # noqa: E402
import study_plate_asymptotes_sources as pa  # noqa: E402
import study_via_array_sources as va  # noqa: E402


def test_shen_optimum_diameters_and_penalties():
    """!@brief Shen and others (2019) pages 5 to 7: optimum 0.25 mm (air), about 0.8 mm (solder), +44 % and +23 % penalties, pattern II 86.6 % of pattern I."""
    out = va.part1()
    assert abs(out["air"][0] - 0.25) < 0.01 and abs(out["solder"][0] - 0.8) < 0.05
    assert abs(out["air"][1] - 44.0) < 2.0 and abs(out["solder"][1] - 23.0) < 2.0
    assert abs(out["air"][2] - 0.866) < 0.005


def test_flux_tube_series_against_printed_correlation_and_table():
    """!@brief Yovanovich and others (1998) equations 22 and 24 agree to 2e-4 and give 32/(3 pi^2) at small eps; Yovanovich (2003) Table 3, eps = 0.5, isoflux 0.4092, m = -1/2 0.3342."""
    for e in (0.1, 0.3, 0.5, 0.7):
        assert abs(ft.psi_isoflux_series(e) - ft.psi_24(e)) < 2e-4
    # eps = 0.01 (4000 roots resolve it): 32/(3 pi^2) - 1.41042 eps is the small-source expansion
    assert abs(ft.psi_isoflux_series(0.01) - (32 / (3 * np.pi ** 2) - 1.41042 * 0.01)) < 2e-3
    assert abs(ft.psi_isoflux_series(0.5) - 0.4092) < 1e-4
    assert abs(ft.psi_isothermal_flux_series(0.5) - 0.3342) < 1e-4


def test_dryden_thick_layer_limit():
    """!@brief Equation 39 of Yovanovich and others (1998) against the integral of equation 34 for t/a = 5 (within 0.2 %)."""
    k1, a = 400.0, 1e-3
    for ratio in (10.0, 100.0):
        k2 = k1 / ratio
        ex = ft.rc_integral(k1, k2, a, 5 * a)
        thick = 1 / (4 * k1 * a) - (1 / (2 * np.pi * k1 * a)) * (1 / 5.0) * np.log(2 / (1 + k1 / k2))
        assert abs(thick / ex - 1) < 2e-3


def test_yovanovich_1993_natural_form_is_close_to_churchill_chu():
    """!@brief Equation 25 of Yovanovich (1993) is within 0.5 % of the Ra^(1/4) coefficient of the laminar Churchill-Chu form for every Prandtl number; its small-Pr limit is sqrt(2/pi) Pr^(1/4)."""
    for pr in (0.01, 0.71, 7.0, 100.0):
        assert abs(pa.coeff_natural_y93(pr) / pa.coeff_natural_churchill(pr) - 1) < 0.005
    # the small-Pr limit of Nu = c Ra^(1/4): c -> sqrt(2/pi) Pr^(1/4)
    assert abs(pa.coeff_natural_y93(1e-6) / (np.sqrt(2 / np.pi) * 1e-6 ** 0.25) - 1) < 0.01


def test_lee_lemczyk_unit_pieces():
    """!@brief The barrel of equation 2 is the tube formula; equation 3 in the thick limit is the constriction of a disc (about 0.85 of 0.27/(k b))."""
    r = lly.r_barrel(386.0, 5e-6, 14e-6, 17.5e-6)
    assert abs(r - 37.40) < 0.05
    rb = lly.r_pad_via(386.0, 55e-6, 500e-6, 1e-9, 17.5e-6)
    assert 0.7 < rb / (0.2701 / (386.0 * 17.5e-6)) < 1.0
