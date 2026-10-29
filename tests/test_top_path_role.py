"""!
@file test_top_path_role.py
@brief Only a component has a top path: a pure source that carries theta and theta_sa (through the API or a JSON file) ignores them.
@details Before the correction `Heater.top_resistance()` looked only at theta and theta_sa while the split of the power used the junction resistance of the
         role: a source with a leftover theta got r_top > 0 in the report with no heat through the top (case A), and with a base interface it
         switched on a top path that the interface does not show and cooled the part by 39 K (case B).
"""

import itertools

import pytest

from pcbthermal import Problem, SolverOptions, simulate


def board(role, theta, theta_sa, base=0.0):
    """!
    @brief A 50 x 40 mm two-layer board with full copper and a 2 W part of 1 cm2 with a heatsink of theta_sa on top.
    @param role Heater role ("", "source" or "component").
    @param theta Junction-to-pad resistance in K/W.
    @param theta_sa Heatsink resistance in K/W.
    @param base Interface under a pure source in K cm2/W.
    @return Problem.
    """
    p = Problem.new(50, 40, 2).add_full_copper()
    p.add_heater(1, 2.0, rect=(20, 15, 30, 25), name="U", theta=theta, theta_sa=theta_sa, role=role)
    p.heaters[0].base_interface = base
    return p


def row_of(p):
    """!
    @brief The row of the part in the report of an FVM run on a coarse cell.
    @param p Problem.
    @return Tuple (row, hottest temperature in degC).
    """
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))
    return sim.heater_rows()[0], sim.results["fvm"].t_max


@pytest.mark.parametrize("base", [0.0, 3.0])
def test_a_source_with_leftover_theta_has_no_top_path(base):
    source = board("source", 5.0, 20.0, base)
    assert source.heaters[0].top_resistance() == 0.0
    row, t_source = row_of(source)
    assert row["r_top"] == 0.0 and row["power_top_w"] == 0.0
    # The same part without the heatsink fields: the field is bit for bit the same, nothing goes up
    _, t_plain = row_of(board("source", 0.0, 0.0, base))
    assert t_source == t_plain


def test_the_same_network_as_a_component_still_sends_heat_up():
    row, t_comp = row_of(board("component", 3.0, 20.0))
    assert row["r_top"] > 0.0 and row["power_top_w"] > 0.5
    _, t_source = row_of(board("source", 0.0, 0.0, 3.0))
    assert t_comp < t_source - 10.0                       # The heatsink on the component cools the board by tens of kelvin


def test_one_predicate_for_every_role_and_every_field():
    for role, theta, theta_sa, base in itertools.product(("", "source", "component"), (0.0, 5.0), (0.0, 20.0), (0.0, 3.0)):
        p = board(role, theta, theta_sa, base)
        h = p.heaters[0]
        row, _ = row_of(p)
        expected = h.is_component() and theta > 0 and theta_sa > 0
        assert h.has_top_path() == expected
        assert (h.top_resistance() > 0) == expected
        assert (row["r_top"] > 0) == expected
        if row["power_top_w"] > 0:
            assert row["r_top"] > 0
