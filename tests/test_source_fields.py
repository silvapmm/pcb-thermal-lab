#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_source_fields.py
@brief A heat source (role "source") ignores the junction and package fields and the input check says so; the fields that work on a source keep working.
@details `theta`, `theta_jc_top`, `theta_sa`, `interface`, `contact_area`, `pad_thickness` and `pad_k` describe a junction and a package top, which a pure source has
         not. `tj_max`, `psi_jb` and `power_tc` do work on a source: the device temperature is the hottest point under the footprint when there is no theta.
"""

import pytest

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.checks import check_problem


def board(**fields):
    """!
    @brief A 50 x 40 mm two-layer board with full copper and a 2 W heat source of 1 cm2.
    @param fields Extra arguments of add_heater (for example tj_max).
    @return Problem.
    """
    p = Problem.new(50, 40, 2).add_full_copper()
    p.add_heater(1, 2.0, rect=(20, 15, 30, 25), name="U", role="source", **fields)
    return p


def source_warnings(p):
    """!
    @brief The warnings that mention the ignored fields of a source.
    @param p Problem.
    @return List of str.
    """
    return [str(w) for w in check_problem(p) if "heat source ignores" in str(w)]


def test_a_source_that_carries_component_fields_is_warned():
    w = source_warnings(board(theta=5.0, theta_sa=20.0))
    assert len(w) == 1 and "theta" in w[0] and "theta_sa" in w[0]
    assert "U" in w[0] and "Component" in w[0]


def test_a_plain_source_a_component_and_a_source_with_working_fields_are_not_warned():
    assert not source_warnings(board())
    assert not source_warnings(board(tj_max=125.0, psi_jb=3.0, power_tc=0.004))
    comp = Problem.new(50, 40, 2).add_full_copper()
    comp.add_heater(1, 2.0, rect=(20, 15, 30, 25), name="U", role="component", theta=5.0, theta_sa=20.0)
    assert not source_warnings(comp)


def test_tj_max_and_the_power_coefficient_work_on_a_source_at_the_hottest_point():
    plain = simulate(board(), SolverOptions(models=("fvm",), cell_mm=2.0))
    row_plain = plain.heater_rows()[0]
    limit = simulate(board(tj_max=125.0), SolverOptions(models=("fvm",), cell_mm=2.0)).heater_rows()[0]
    # With no theta the device temperature is the hottest board point under the footprint: the margin is computed from it
    assert limit["margin_k"] == pytest.approx(125.0 - plain.results["fvm"].t_max, abs=0.05)
    assert limit["p_limit_w"] > 2.0
    # A positive coefficient of the power raises the dissipation at the hotter temperature: the loop converges to a higher power than the nominal
    tc = simulate(board(power_tc=0.004), SolverOptions(models=("fvm",), cell_mm=2.0))
    assert tc.results["fvm"].t_max > plain.results["fvm"].t_max
