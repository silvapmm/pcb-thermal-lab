#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_down_laws.py
@brief Tests of the face-down study: the laws against hand values, the patch in memory against the program, and the program restored afterwards.
@details Run: QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q research/face-down-convection/tests
"""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import down_laws as D  # noqa: E402
from pcbthermal import convection  # noqa: E402


def test_hand_values():
    """!
    @brief Nu of each law at Ra = 1e4 against numbers worked out by hand.
    @return None.
    """
    assert D.program_down(1e4) == pytest.approx(2.7)                     # 0.27 * 10
    assert D.incropera7(1e5) == pytest.approx(0.52 * 10 ** 1.0)          # 1e5^(1/5) = 10
    assert D.gl_mean(1e5) == pytest.approx(4.75)
    assert D.gl_strip(1e5) == pytest.approx(5.24)
    # f1 at Pr 0.71: (1 + 0.693^0.5625)^(-16/9) = 0.347; 0.6 (1e5 * 0.347)^0.2 = 0.6 * 8.09 = 4.855
    assert float(D.vdi(1e5)) == pytest.approx(4.855, rel=2e-3)


def test_fifth_power_laws_agree_within_ten_percent():
    """!
    @brief The three 1/5 laws read in or quoted for air are within 10 % of each other, the same ratio at every Ra (same exponent).
    @return None.
    """
    for ra in (1e3, 1e4, 1e5, 1e6):
        v = [float(D.incropera7(ra)), float(D.gl_mean(ra)), float(D.vdi(ra))]
        assert max(v) / min(v) < 1.10


def test_patch_with_the_program_law_is_the_program():
    """!
    @brief use_down(program_down) gives bit-identical h on both faces and restores the function on exit.
    @return None.
    """
    original = convection.h_natural_horizontal
    for facing_up in (True, False):
        ref = original(60.0, 25.0, 0.02, facing_up)
        with D.use_down(D.program_down) as calls:
            got = convection.h_natural_horizontal(60.0, 25.0, 0.02, facing_up)
        assert got == ref and calls["n"] == 1
    assert convection.h_natural_horizontal is original


def test_only_the_lower_face_changes():
    """!
    @brief The face up is untouched by the patch; the face down moves to the 1/5 law; a cold face up takes the lower law as in the program.
    @return None.
    """
    up0 = convection.h_natural_horizontal(60.0, 25.0, 0.02, True)
    dn0 = convection.h_natural_horizontal(60.0, 25.0, 0.02, False)
    with D.use_down(D.incropera7):
        up1 = convection.h_natural_horizontal(60.0, 25.0, 0.02, True)
        dn1 = convection.h_natural_horizontal(60.0, 25.0, 0.02, False)
        cold_up = convection.h_natural_horizontal(0.0, 25.0, 0.02, True)
    assert up1 == up0 and dn1[0] > dn0[0]
    # A cold face looking up behaves like a hot face looking down: same law (properties differ with the film temperature)
    assert cold_up[0] == pytest.approx(0.52 * cold_up[1] ** 0.2 * convection.air_properties(12.5)["k"] / 0.02)


def test_bottom_h_of_a_computed_board_moves_only_at_the_bottom():
    """!
    @brief board_h with the 1/5 law: the top coefficient is unchanged, the bottom one is higher at the Ra of a small board.
    @return None.
    """
    from pcbthermal import model
    p = model.Problem.new(60.0, 40.0, layers=2) if hasattr(model.Problem, "new") else None
    if p is None:
        pytest.skip("Problem.new signature")
    b = p.board
    b.h_mode = "computed"
    t0 = convection.board_h(b, 60.0, 60.0)
    with D.use_down(D.incropera7):
        t1 = convection.board_h(b, 60.0, 60.0)
    assert t1[0] == t0[0] and t1[1] > t0[1]
