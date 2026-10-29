#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_natural_form.py
@brief Board.natural_form: the general (default) and laminar forms of Churchill and Chu for a vertical board; the default leaves every result unchanged.
"""

import json

import pytest

from pcbthermal import Problem, SolverOptions, cli, simulate
from pcbthermal.convection import NATURAL_FORMS, air_properties, board_h, h_natural_vertical, rayleigh
from pcbthermal.examples import example_board
from pcbthermal.model import new_problem, problem_from_dict, problem_to_dict


def general_by_hand(t_surface, t_ambient, height):
    """!
    @brief The general Churchill and Chu form written out as it was before the option existed (the reference for "bit-identical").
    @param t_surface Surface temperature in degC.
    @param t_ambient Air temperature in degC.
    @param height Plate height in m.
    @return h in W/m2K.
    """
    props = air_properties(0.5 * (t_surface + t_ambient))
    ra = rayleigh(max(abs(t_surface - t_ambient), 1e-3), height, props)
    nu = (0.825 + 0.387 * ra ** (1.0 / 6.0) / (1.0 + (0.492 / props["pr"]) ** (9.0 / 16.0)) ** (8.0 / 27.0)) ** 2
    return nu * props["k"] / height


def test_the_default_is_the_general_form_and_bit_identical_to_the_old_code():
    assert NATURAL_FORMS == ("general", "laminar")
    assert Problem.new(100, 80, 2).board.natural_form == "general" and new_problem().board.natural_form == "general"
    for height, ts in ((0.05, 35.0), (0.08, 70.0), (0.2, 85.0)):
        assert h_natural_vertical(ts, 25.0, height)[0] == general_by_hand(ts, 25.0, height)
        assert h_natural_vertical(ts, 25.0, height, "general")[0] == general_by_hand(ts, 25.0, height)


def test_the_laminar_form_against_the_research_table():
    # research/effective-conductivity README 4.7 (difference laminar / general, air at the film temperature)
    for height, rise, expected in ((0.050, 10, +0.065), (0.100, 10, +0.026), (0.100, 30, -0.001), (0.200, 30, -0.075), (0.200, 60, -0.095)):
        gen = h_natural_vertical(25.0 + rise, 25.0, height)[0]
        lam = h_natural_vertical(25.0 + rise, 25.0, height, "laminar")[0]
        assert lam / gen - 1.0 == pytest.approx(expected, abs=0.004), (height, rise)


def test_an_unknown_form_is_refused():
    with pytest.raises(ValueError):
        h_natural_vertical(60.0, 25.0, 0.1, "turbulent")
    p = Problem.new(100, 80, 2)
    p.board.natural_form = "turbulent"
    with pytest.raises(ValueError):
        p.validate()


def test_json_roundtrip_and_old_files_without_the_key():
    p = example_board()
    p.board.natural_form = "laminar"
    data = json.loads(json.dumps(problem_to_dict(p)))
    assert data["board"]["natural_form"] == "laminar" and problem_from_dict(data).board.natural_form == "laminar"
    del data["board"]["natural_form"]                                          # A file written before the option existed
    assert problem_from_dict(data).board.natural_form == "general"


def test_horizontal_boards_ignore_the_form():
    a = Problem.new(100, 80, 2)
    b = Problem.new(100, 80, 2)
    b.board.natural_form = "laminar"
    for p in (a, b):
        p.board.h_mode = "computed"
    assert board_h(a.board, 70.0, 60.0)[:2] == board_h(b.board, 70.0, 60.0)[:2]


def test_the_form_changes_the_example_board_by_under_one_percent_of_the_rise():
    # research/effective-conductivity README 4.8 B: -0.7 to +0.2 % of the rise on the example board turned to the vertical
    rises = {}
    for form in NATURAL_FORMS:
        p = example_board()
        p.board.h_mode, p.board.orientation, p.board.natural_form = "computed", "vertical", form
        rises[form] = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0)).reference.t_max - p.board.ambient
    change = rises["laminar"] / rises["general"] - 1.0
    assert -0.01 < change < 0.005 and change != 0.0


def test_default_results_are_unchanged_by_the_option():
    # Computed h on a vertical board with the default form equals the explicit "general" one, to the last bit
    t = []
    for form in (None, "general"):
        p = example_board()
        p.board.h_mode, p.board.orientation = "computed", "vertical"
        if form:
            p.board.natural_form = form
        t.append(simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0)).reference.t_max)
    assert t[0] == t[1]


def test_cli_natural_form(tmp_path, capsys):
    path = tmp_path / "b.pcbt.json"
    cli.main(["example", str(path), "--which", "example"])
    out = []
    for form in ("general", "laminar"):
        cli.main(["run", str(path), "--model", "fvm", "--cell-mm", "2", "--out", str(tmp_path / form), "--no-plots", "--orientation", "vertical", "--natural-form", form])
        out.append(capsys.readouterr().out)
    assert out[0] != out[1]


def test_the_laminar_form_is_the_boundary_layer_solution_plus_its_leading_edge_constant():
    # Independent check of the coefficients (0.670, the exponent 4/9 and the Prandtl function) that does not come from the same compilation: the laminar
    # similarity solution of a vertical isothermal plate (Ostrach 1953, with the Prandtl fit of LeFevre 1956), Nu = 4/3 (Gr/4)^(1/4) g(Pr),
    # g(Pr) = 0.75 Pr^(1/2) / (0.609 + 1.221 Pr^(1/2) + 1.238 Pr)^(1/4). The Ra^(1/4) term of the laminar form is that solution within 0.21 % (measured)
    # for every board size and rise; the constant 0.68 is the correction of the leading edge.
    for height, rise in ((0.05, 10.0), (0.1, 60.0), (0.2, 30.0), (0.4, 60.0)):
        ts = 25.0 + rise
        props = air_properties(0.5 * (ts + 25.0))
        ra = rayleigh(rise, height, props)
        pr = props["pr"]
        nu_laminar = h_natural_vertical(ts, 25.0, height, "laminar")[0] * height / props["k"]
        g = 0.75 * pr ** 0.5 / (0.609 + 1.221 * pr ** 0.5 + 1.238 * pr) ** 0.25
        nu_similarity = 4.0 / 3.0 * (ra / pr / 4.0) ** 0.25 * g
        assert nu_laminar - 0.68 == pytest.approx(nu_similarity, rel=0.004), (height, rise)


def test_the_laminar_form_warns_above_its_range():
    # A 1 m vertical board at about 60 K has Ra near 2e9: the laminar form is outside its range and the program says so; the general form does not warn
    msgs = {}
    for form in NATURAL_FORMS:
        p = Problem.new(1000, 1000, 2).add_full_copper()
        p.add_heater(1, 400.0, rect=(400, 400, 600, 600))
        p.board.h_mode, p.board.orientation, p.board.natural_form = "computed", "vertical", form
        sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=20.0))
        msgs[form] = [w for w in sim.warnings if "laminar form" in w]
        assert f"vertical board ({form} form)" in sim.report()
    assert msgs["general"] == [] and len(msgs["laminar"]) == 1
