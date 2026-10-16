"""!
@file test_fdm.py
@brief The finite-difference comparison model: same physics as the FVM, different discretisation.
"""

import pytest

from pcbthermal import SolverOptions, fdm, fvm, simulate
from pcbthermal.examples import example_board
from pcbthermal.model import reference_problem


def test_fdm_matches_the_fvm_on_a_uniform_board_and_converges():
    p = reference_problem(layers=2, heater_mm=20.0, power=5.0)
    reference = fvm.solve_steady(p, 0.5).t_max
    for cell in (4.0, 2.0, 1.0):
        r = fdm.solve_steady(p, cell)
        assert r.t_max == pytest.approx(reference, abs=0.8)               # Same equations, only point sampling differs
        assert abs(r.balance_error) < 1e-9 and r.power_in == pytest.approx(5.0)
    errors = [abs(fdm.solve_steady(p, c).t_max - reference) for c in (4.0, 1.0)]
    assert errors[1] < errors[0] + 0.05


def test_fdm_on_the_example_board_with_both_face_means():
    p = example_board()
    ref = fvm.solve_steady(p, 0.5).t_max
    for mean in ("arithmetic", "harmonic"):
        r = fdm.solve_steady(p, 1.0, mean)
        assert r.t_max == pytest.approx(ref, abs=1.5) and abs(r.balance_error) < 1e-9
        assert r.T.shape == (4, 81, 101)                                  # Nodes, not cells
    assert any("comparison" in w for w in fdm.solve_steady(p, 2.0).warnings)


def test_fdm_is_selectable_through_the_api_and_has_no_time_simulation():
    from pcbthermal.examples import example_profile_board
    s = simulate(example_board(), SolverOptions(models=("fvm", "fdm"), cell_mm=2.0))
    assert set(s.results) == {"fvm", "fdm"} and s.results["fdm"].t_max == pytest.approx(s.results["fvm"].t_max, abs=1.5)
    t = simulate(example_profile_board(), SolverOptions(models=("fvm", "fdm"), cell_mm=2.0))
    assert set(t.profile_results) == {"fvm"} and not t.profile_error
    only = simulate(example_profile_board(), SolverOptions(models=("fdm",), cell_mm=2.0))
    assert "needs the FVM" in only.profile_error
    with pytest.raises(ValueError):
        SolverOptions(models=("fem",)).validate()


def test_cli_compare(tmp_path, capsys):
    from pcbthermal import cli
    path = tmp_path / "e.pcbt.json"
    cli.main(["example", str(path), "--which", "example"])
    assert cli.main(["run", str(path), "--model", "compare", "--cell-mm", "2", "--out", str(tmp_path / "o"), "--no-plots"]) == 0
    assert "fdm" in capsys.readouterr().out
