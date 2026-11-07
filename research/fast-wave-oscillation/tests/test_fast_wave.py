#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fast_wave.py
@brief Tests of the independent reference and of the closed-form estimator of research/fast-wave-oscillation.

@details The reference is checked against the semi-infinite solid (erfc closed form) and a steady series circuit; the estimator against the reference; the program's finding (0.75 K against 6.3 K)
is reproduced. Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q research/fast-wave-oscillation/tests`.
"""

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..")))

import axisym_stack as A                                             # noqa: E402
import columns as Cn                                                 # noqa: E402
import impedance as I                                                # noqa: E402


def test_semi_infinite_solid_step():
    # A bare slab heated on its top face: T = 2 q sqrt(t / pi) / e with e = sqrt(k rho c), until the heat reaches the back
    st = A.Stack(layers=1, thickness=8e-3, copper=False, kz=0.3)
    area = 1e-4
    m = Cn.exact_column(st, area, 0.0, 0.0, n_cu=4, n_gap=24)
    e = np.sqrt(st.kz * st.rho_cp_lam)
    for t in (0.3, 1.0):                                              # The source is spread over the first 35 um, so the top cell reads t_cu / (2 k A) = 0.58 K/W below the surface value
        exact = 2.0 * np.sqrt(t / np.pi) / (e * area)
        assert m.step([t], "top")[0] == pytest.approx(exact, abs=0.58 + 0.1)


def test_steady_state_is_a_series_parallel_circuit():
    st = A.Stack(layers=2)
    area = 1e-4
    m = Cn.exact_column(st, area, 10.0, 10.0)
    r_lam = (st.thickness - 2 * st.t_cu) / (st.kz * area)
    r_cu = st.t_cu / (st.k_cu * area)
    g = 10.0 * area + 1.0 / (r_lam + 2 * r_cu + 1.0 / (10.0 * area))
    assert m.rth["top"] == pytest.approx(1.0 / g, rel=2e-3)


def test_program_value_of_the_lumped_column_matches_the_programs_swing():
    # The lumped column is the program's node structure: its 20 Hz swing is the 0.75 K that the program prints (profiles.decide, 10 mm part, 2 layers)
    st = A.Stack(layers=2)
    r = Cn.lumped_column(st, 1e-4, 10.0, 10.0).square_wave(1 / 20.0, 0.3, "top")
    assert 10.0 * (r[0] - r[1]) == pytest.approx(0.753, abs=0.01)


@pytest.mark.parametrize("layers,side,f", [(2, 10.0, 20.0), (2, 2.0, 1.0), (4, 5.0, 100.0), (1, 5.0, 0.3)])
def test_estimator_against_the_axisymmetric_reference(layers, side, f):
    st = A.Stack(layers=layers)
    a = A.part_radius(side * 1e-3)
    ref = A.Reference(st, a, A.rectangle_radius(60e-3, 40e-3), 10.0, 10.0)
    mx, mn = ref.square_wave(1.0 / f, 0.3, "center")
    assert I.square_swing(st, 1.0 / f, 0.3, a, 10.0, 10.0) == pytest.approx(mx - mn, rel=0.07)


def test_the_program_understates_the_fast_wave():
    pytest.importorskip("pcbthermal")
    from pcbthermal import profiles
    from pcbthermal.model import Problem, SquareWave
    p = Problem.new(60, 40, 2, 1.6, h_top=10, h_bottom=10, h_side=0.0).add_full_copper()
    p.add_heater(1, 10.0, rect=(25, 15, 35, 25), profile=SquareWave(p_on=10.0, period=0.05, duty=0.3))
    d = profiles.decide(p, profiles.step_response_fvm(p, 2.0), 1.0)[0]
    st = A.Stack(layers=2)
    ref = A.Reference(st, A.part_radius(10e-3), A.rectangle_radius(60e-3, 40e-3), 10.0, 10.0)
    mx, mn = ref.square_wave(0.05, 0.3, "center")
    assert d.oscillation == pytest.approx(0.75, abs=0.03)
    assert 10.0 * (mx - mn) == pytest.approx(6.37, abs=0.1)
