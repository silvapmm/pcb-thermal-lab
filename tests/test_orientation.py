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
    """!
    @brief The two horizontal faces against their laws written out: up 0.54 Ra^(1/4) (Lloyd and Moran / textbooks), down 0.475 Ra^(1/5).
    @details The face turned down is the mean of the laminar Goldstein-Lau constants (0.44 to 0.527, Yovanovich and Jafarpur 1993, p 8) with the exponent 1/5 of every
             published form read (Lienhard 2024 eq. 8.38, 8.39); the McAdams 0.27 Ra^(1/4) it replaced is not used. The constant 0.52 of Incropera and DeWitt was not confirmed.
    @return None.
    """
    p = board()
    t_top, t_bottom, amb = 70.0, 60.0, p.board.ambient
    h_top, h_bottom, info = board_h(p.board, t_top, t_bottom)
    length = (0.100 * 0.080) / (2 * (0.100 + 0.080))                          # Lloyd and Moran: area over perimeter
    for name, ts, coeff, expo in (("top", t_top, 0.54, 0.25), ("bottom", t_bottom, 0.475, 0.2)):
        props = air_properties(0.5 * (ts + amb))
        ra = rayleigh(ts - amb, length, props)
        assert 1e4 < ra < 1e7                                                  # Inside the range of both correlations
        expected = coeff * ra ** expo * props["k"] / length                    # Nu = C Ra^n, h = Nu k / L
        assert info[name]["convection"] == pytest.approx(expected, rel=1e-12)
    assert h_top > h_bottom                                                    # Layer 1 faces up: it loses more heat than the last layer
    # A surface colder than the air swaps the roles of up and down
    cold_up, _ = h_natural_horizontal(10.0, 25.0, length, True)
    cold_down, _ = h_natural_horizontal(10.0, 25.0, length, False)
    assert cold_up < cold_down


def _nu_down(ra):
    """!
    @brief Nusselt number of the face turned down at a given Rayleigh number, through the program's function.
    @param ra Rayleigh number (dimensionless) of the face, at air near 40 degC.
    @return Nu = h L / k.
    """
    length, ambient = 0.02, 25.0
    props = air_properties(40.0)
    # Choose the surface excess that gives the Rayleigh number asked for at the film temperature of about 40 degC
    dt = 30.0
    scale = ra / rayleigh(dt, length, air_properties(0.5 * (ambient + dt + ambient)))
    length = length * scale ** (1.0 / 3.0)
    h, got = h_natural_horizontal(ambient + dt, ambient, length, False)
    return h * length / air_properties(0.5 * (2 * ambient + dt))["k"], got, props


@pytest.mark.parametrize("ra", [1e3, 1e4, 1e5, 1e6])
def test_face_down_law_has_the_exponent_one_fifth_and_the_goldstein_lau_level(ra):
    nu, got, _ = _nu_down(ra)
    assert got == pytest.approx(ra, rel=1e-9)
    assert nu == pytest.approx(0.475 * ra ** 0.2, rel=1e-9)
    # The old McAdams form is outside the band of the published 1/5 laws (0.475 .. 0.524) below Ra 1e5
    if ra <= 1e4:
        assert nu > 0.27 * ra ** 0.25 * 1.1


def test_face_down_h_scales_as_the_fifth_root_of_the_rayleigh_number():
    """!
    @brief At a fixed length h goes as dT^(1/5) (air properties aside): a Rayleigh number 32 times larger gives h twice as large in Nu terms.
    @return None.
    """
    nu1, _, _ = _nu_down(2e3)
    nu2, _, _ = _nu_down(2e3 * 32.0)
    assert nu2 / nu1 == pytest.approx(2.0, rel=1e-9)


def test_face_down_nusselt_is_continuous_and_increasing_in_the_rayleigh_number():
    ras = [10.0 ** (k / 4.0) for k in range(4, 37)]                            # 10 to 1e9
    nus = [_nu_down(r)[0] for r in ras]
    assert all(b > a for a, b in zip(nus, nus[1:]))
    assert max(b / a for a, b in zip(nus, nus[1:])) < 1.6                      # No jump between neighbours (a quarter decade apart)


def test_face_down_hand_calculation_of_a_textbook_style_board():
    """!
    @brief A 100 x 80 mm face at 20 K excess: Nu = 0.475 Ra^(1/5) written out with Pr and the properties of the film.
    @return None.
    """
    length = (0.100 * 0.080) / (2 * (0.100 + 0.080))
    props = air_properties(35.0)
    ra = 9.80665 * props["beta"] * 20.0 * length ** 3 / (props["nu"] * props["alpha"])
    h, got = h_natural_horizontal(45.0, 25.0, length, False)
    assert got == pytest.approx(ra, rel=1e-9)
    assert h == pytest.approx(0.475 * ra ** 0.2 * props["k"] / length, rel=1e-9)
    assert 3.0 < h < 5.0                                                       # About 4 W/m2K, the usual order of the lower face of a PCB


def test_face_down_changes_only_the_horizontal_board_at_computed_h():
    """!
    @brief The vertical board and the manual coefficients never call the face-down law, so they do not move with it.
    @return None.
    """
    import pcbthermal.convection as conv
    saved = (conv.DOWN_COEFFICIENT, conv.DOWN_EXPONENT)
    try:
        results = {}
        for tag, (c, n) in (("old", (0.27, 0.25)), ("new", saved)):
            conv.DOWN_COEFFICIENT, conv.DOWN_EXPONENT = c, n
            results[tag] = {o: simulate(board(o), SolverOptions(models=("fvm",), cell_mm=2.0)).results["fvm"].t_max for o in ("horizontal", "vertical")}
    finally:
        conv.DOWN_COEFFICIENT, conv.DOWN_EXPONENT = saved
    assert results["old"]["vertical"] == results["new"]["vertical"]
    assert results["new"]["horizontal"] < results["old"]["horizontal"]         # The new law gives more heat loss on the lower face at these Ra


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
