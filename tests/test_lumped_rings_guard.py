#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_lumped_rings_guard.py
@brief lumped.solve_steady, step_responses and run_profile refuse rings below 3 or not an integer; SolverOptions refuses the same lumped_rings, and a
       project or defaults file that holds an integer-valued float (10.0) still loads and runs as the integer.
"""

import json
import os

import numpy as np
import pytest

from pcbthermal import Problem, defaults, lumped, profiles
from pcbthermal.api import SolverOptions, default_options, simulate
from pcbthermal.examples import example_board
from pcbthermal.model import SquareWave
from pcbthermal.project import Project, ProjectFormatError, project_from_dict, project_to_dict


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
    """!
    @brief Every entry point refuses a count below 3 or not an integer, with the message that names the rule.
    @param call Entry point wrapper.
    @param bad Rejected rings value.
    """
    with pytest.raises(ValueError, match=r"rings must be an integer >= 3"):
        call(_board(), bad)


@pytest.mark.parametrize("call", CALLS)
def test_numpy_integer_rings_are_accepted(call):
    """!
    @brief A numpy integer is a count.
    @param call Entry point wrapper.
    """
    assert call(_board(), np.int64(4)) is not None


def test_default_and_minimum_rings_are_accepted():
    """!
    @brief The default and the minimum run.
    """
    p = _board()
    assert lumped.solve_steady(p, cell_mm=2.0).t_max > p.board.ambient
    assert lumped.solve_steady(p, 3, 2.0).t_max > p.board.ambient
    assert lumped.step_responses(p, cell_mm=2.0, stages=2) is not None


def test_numpy_rings_give_the_same_number_as_int():
    """!
    @brief np.int32(5) and 5 give the same network.
    """
    p = _board()
    assert lumped.solve_steady(p, np.int32(5), 2.0).t_max == lumped.solve_steady(p, 5, 2.0).t_max


@pytest.mark.parametrize("bad", [2, 2.5, 3.0, True, "3", None])
def test_solver_options_refuse_the_same_values(bad):
    """!
    @brief SolverOptions.validate applies the rule of the entry points, so a bad value is refused when the options are made or a file opens, not at the run.
    @param bad Rejected lumped_rings value.
    """
    with pytest.raises(ValueError, match=r"lumped_rings must be an integer >= 3"):
        SolverOptions(lumped_rings=bad).validate()
    assert lumped.RINGS_MIN == 3
    SolverOptions(lumped_rings=np.int64(3)).validate()


def _project_dict(rings):
    """!
    @brief The example board as a project dict whose solver runs only the LPTN with the given stored lumped_rings.
    @param rings Stored value (as a JSON file may hold it).
    @return Dict of a project file.
    """
    d = json.loads(json.dumps(project_to_dict(Project(example_board(), SolverOptions(models=("lumped",), cell_mm=2.0)))))
    d["solver"]["lumped_rings"] = rings
    return d


def test_a_project_file_with_rings_as_10_point_0_still_runs_as_10():
    """!
    @brief Regression of the review: a project that stores 10.0 (another JSON writer, a hand edit) ran before the guard; it loads as the int 10 and gives the same number.
    """
    p10, pf = project_from_dict(_project_dict(10)), project_from_dict(_project_dict(10.0))
    assert type(pf.options.lumped_rings) is int and pf.options.lumped_rings == 10
    t10 = simulate(p10.problem, p10.options).results["lumped"].t_max
    assert simulate(pf.problem, pf.options).results["lumped"].t_max == t10


@pytest.mark.parametrize("bad", [10.5, "10", 2.0])
def test_a_project_file_with_a_bad_ring_count_is_refused_when_it_opens(bad):
    """!
    @brief A count that is not an integer, or is below 3, is refused when the file opens, with the rule in the message.
    @param bad Stored lumped_rings value.
    """
    with pytest.raises(ProjectFormatError, match=r"lumped_rings must be an integer >= 3"):
        project_from_dict(_project_dict(bad))


def test_a_defaults_file_with_rings_as_float_keeps_the_user_values():
    """!
    @brief The user's defaults file with lumped_rings 12.0 gives 12 rings and keeps the other values (a stricter check would otherwise drop them all).
    """
    os.makedirs(defaults.user_dir(), exist_ok=True)
    with open(defaults.user_file(), "w") as fh:
        json.dump({"solver": {"lumped_rings": 12.0, "cell_mm": 2.0}}, fh)
    o = default_options()
    assert type(o.lumped_rings) is int and o.lumped_rings == 12 and o.cell_mm == 2.0
