#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_orientation.py
@brief Board orientation follows from the layer numbering (layer 1 = top, faces up): the computed convection against the textbook formulas and the behaviour they imply.
"""

import math

import pytest

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.convection import air_properties, board_h, h_natural_horizontal, h_natural_vertical, rayleigh


def board(orientation="horizontal", mode="computed", width=100.0, height=80.0):
    """!
    @brief A two-layer board with copper on both faces and a heater on layer 1.
    @param orientation "horizontal" or "vertical".
    @param mode "computed" or "manual" heat transfer.
    @param width Width in mm.
    @param height Height in mm.
    @return Problem.
    """
    p = Problem.new(width, height, 2)
    p.board.h_mode, p.board.orientation = mode, orientation
    p.board.h_top, p.board.h_bottom = 10.0, 10.0
    p.add_zone(1, rect=(2, 2, width - 2, height - 2))
    p.add_zone(2, rect=(2, 2, width - 2, height - 2))
    p.add_heater(1, 3.0, rect=(width / 2 - 5, height / 2 - 5, width / 2 + 5, height / 2 + 5))
    return p


def test_horizontal_board_matches_the_textbook_formulas_written_out_by_hand():
    p = board()
    t_top, t_bottom, amb = 70.0, 60.0, p.board.ambient
    h_top, h_bottom, info = board_h(p.board, t_top, t_bottom)
    length = (0.100 * 0.080) / (2 * (0.100 + 0.080))                          # Lloyd and Moran: area over perimeter
    for name, ts, coeff in (("top", t_top, 0.54), ("bottom", t_bottom, 0.27)):
        props = air_properties(0.5 * (ts + amb))
        ra = rayleigh(ts - amb, length, props)
        assert 1e4 < ra < 1e7                                                  # Inside the range of the 0.54 and 0.27 correlations
        expected = coeff * ra ** 0.25 * props["k"] / length                    # Nu = C Ra^(1/4), h = Nu k / L
        assert info[name]["convection"] == pytest.approx(expected, rel=1e-12)
    assert h_top > h_bottom                                                    # Layer 1 faces up: it loses more heat than the last layer
    # At the same Rayleigh number the facing-down coefficient is half of the facing-up one
    up, _ = h_natural_horizontal(70.0, amb, length, True)
    down, _ = h_natural_horizontal(70.0, amb, length, False)
    assert down == pytest.approx(0.5 * up)
    # A surface colder than the air swaps the roles of up and down
    cold_up, _ = h_natural_horizontal(10.0, 25.0, length, True)
    cold_down, _ = h_natural_horizontal(10.0, 25.0, length, False)
    assert cold_up < cold_down


def test_vertical_board_uses_the_plate_formula_on_both_faces():
    p = board("vertical")
    h_top, h_bottom, info = board_h(p.board, 70.0, 70.0)
    expected, _ = h_natural_vertical(70.0, p.board.ambient, 0.080)
    assert info["top"]["convection"] == pytest.approx(expected) and info["bottom"]["convection"] == pytest.approx(expected)
    assert h_top == pytest.approx(h_bottom)


def test_the_upper_face_takes_more_heat_than_the_lower_one_only_when_horizontal():
    ratios = {}
    for orientation in ("horizontal", "vertical"):
        res = simulate(board(orientation), SolverOptions(models=("fvm",), cell_mm=2.0)).reference
        ratios[orientation] = res.power_out["top"] / res.power_out["bottom"]
        assert abs(res.balance_error) < 1e-9
    assert ratios["horizontal"] > ratios["vertical"] * 1.05                    # The orientation changes where the heat goes
    assert ratios["vertical"] == pytest.approx(1.0, abs=0.12)                  # Both faces alike (the heater is on layer 1, a little more through it)


def test_typed_coefficients_ignore_the_orientation():
    a = simulate(board("horizontal", "manual"), SolverOptions(models=("fvm",), cell_mm=2.0)).reference.t_max
    b = simulate(board("vertical", "manual"), SolverOptions(models=("fvm",), cell_mm=2.0)).reference.t_max
    assert a == pytest.approx(b, abs=1e-12)


def test_only_horizontal_and_vertical_exist():
    p = board()
    p.board.orientation = "horizontal_down"
    with pytest.raises(ValueError):
        p.validate()
