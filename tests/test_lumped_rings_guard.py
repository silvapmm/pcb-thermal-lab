#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_lumped_rings_guard.py
@brief lumped.solve_steady, step_responses and run_profile refuse rings below 3 or not an integer (as SolverOptions refuses lumped_rings below 3).
"""

import numpy as np
import pytest

from pcbthermal import Problem, lumped, profiles
from pcbthermal.api import SolverOptions
from pcbthermal.model import SquareWave


def _board():
    """!
    @brief A small board with one heater that has a square-wave profile.
    @return Problem.
    """
    p = Problem.new(30.0, 30.0, 2).add_zone(1, rect=(0, 0, 30, 30))
    p.add_heater(1, 1.0, rect=(13, 13, 17, 17))
    h = p.heaters[0]
    h.profile = SquareWave(p_on=2.0, period=1.0, duty=0.5, p_off=0.0)
    return p


def _steady(p, rings):
    """!
    @brief Call solve_steady with the given rings.
    @param p Problem.
    @param rings Rings value under test (count).
    @return The result.
    """
    return lumped.solve_steady(p, rings, 2.0)


def _steps(p, rings):
    """!
    @brief Call step_responses with the given rings.
    @param p Problem.
    @param rings Rings value under test (count).
    @return The result.
    """
    return lumped.step_responses(p, rings, 2.0, stages=2)


def _profile(p, rings):
    """!
    @brief Call run_profile with the given rings (the decisions come from the unit step response at the default rings).
    @param p Problem.
    @param rings Rings value under test (count).
    @return The result.
    """
    t, z, r = lumped.step_responses(p, 10, 2.0, stages=4)
    dec = profiles.decide(p, profiles.StepResponse("lumped", t, z, r), 0.0)
    opt = profiles.ProfileOptions(threshold_c=0.0, duration="stable", stable_c=0.5, theta=0.5)
    return lumped.run_profile(p, dec, opt, rings, 2.0)


CALLS = [_steady, _steps, _profile]


@pytest.mark.parametrize("call", CALLS)
@pytest.mark.parametrize("bad", [0, 1, 2, -1, 2.5, 3.0, True, False, "3", None, 1.0])
def test_bad_rings_are_refused(call, bad):
    with pytest.raises(ValueError, match=r"rings must be an integer >= 3"):
        call(_board(), bad)


@pytest.mark.parametrize("call", CALLS)
def test_numpy_integer_rings_are_accepted(call):
    assert call(_board(), np.int64(4)) is not None


def test_default_and_minimum_rings_are_accepted():
    p = _board()
    assert lumped.solve_steady(p, cell_mm=2.0).t_max > p.board.ambient
    assert lumped.solve_steady(p, 3, 2.0).t_max > p.board.ambient
    assert lumped.step_responses(p, cell_mm=2.0, stages=2) is not None


def test_numpy_rings_give_the_same_number_as_int():
    p = _board()
    assert lumped.solve_steady(p, np.int32(5), 2.0).t_max == lumped.solve_steady(p, 5, 2.0).t_max


def test_same_limit_as_solver_options():
    # SolverOptions refuses lumped_rings below 3 with the same minimum
    with pytest.raises(ValueError, match="lumped_rings must be >= 3"):
        SolverOptions(lumped_rings=2).validate()
    assert lumped.RINGS_MIN == 3
