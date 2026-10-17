"""!
@file test_solid3d.py
@brief The 3D finite-volume solid: agreement with the layered FVM, vias, metal blocks, energy balance, size limit and use in the API.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
import copper_dissipation as cd                                       # noqa: E402
from pcbthermal import Problem, SolverOptions, fvm, simulate, solid3d  # noqa: E402
from pcbthermal.examples import example_board, example_profile_board   # noqa: E402
from pcbthermal.model import reference_problem                         # noqa: E402
from test_blocks import board                                          # noqa: E402


def rise_error(a, b, ambient=25.0):
    return abs((a - ambient) / (b - ambient) - 1.0)


def test_uniform_board_matches_the_layered_fvm_and_conserves_energy():
    p = reference_problem(layers=4, heater_mm=20.0, power=5.0)
    r, f = solid3d.solve_steady(p, 1.0), fvm.solve_steady(p, 1.0)
    assert rise_error(r.t_max, f.t_max) < 0.01
    assert abs(r.balance_error) < 1e-9 and r.residual < 1e-9 and r.power_in == pytest.approx(5.0)
    assert r.T.shape == f.T.shape and r.model == "solid3d"


def test_example_board_with_vias_and_heatsink():
    p = example_board()
    r, f = solid3d.solve_steady(p, 1.0), fvm.solve_steady(p, 1.0)
    assert rise_error(r.t_max, f.t_max) < 0.02                         # Vias carry their real copper area
    assert abs(r.balance_error) < 1e-9
    assert r.power_out["heatsinks"] > 0 and r.power_out["sides"] > 0


def test_small_pad_is_where_the_3d_differs_and_dielectric_slabs_converge():
    p = cd.board(None)                                                 # Copper only as large as the heater
    a, b = solid3d.solve_steady(p, 1.0, 4), solid3d.solve_steady(p, 1.0, 8)
    assert rise_error(a.t_max, b.t_max) < 0.01                          # 4 slabs per gap is converged to 1 %
    f = fvm.solve_steady(p, 1.0)
    assert a.t_max > f.t_max                                           # The layered model misses the spreading inside the gap
    assert rise_error(a.t_max, f.t_max) < 0.15


def test_metal_block_in_3d_matches_the_layered_models():
    p = board()
    r, f = solid3d.solve_steady(p, 1.0), fvm.solve_steady(p, 1.0)
    assert rise_error(r.t_max, f.t_max) < 0.02
    assert abs(r.balance_error) < 1e-9 and "blocks" in r.power_out
    assert r.extras["block_bottom_w_to_block"] == pytest.approx(r.extras["block_bottom_w_to_air"], rel=2e-3)
    assert r.extras["block_bottom_w_to_block"] == pytest.approx(f.extras["block_bottom_w_to_block"], rel=0.05)
    assert r.arrays["block_T"].shape[0] == 1 and r.extras["block_bottom_max"] > r.extras["block_bottom_mean"] > 25.0
    assert solid3d.solve_steady(board(False), 1.0).t_max > r.t_max      # The block cools


def test_too_large_a_model_is_refused_and_simulate_skips_it(monkeypatch):
    p = example_board()
    monkeypatch.setattr(solid3d, "MAX_CELLS", 1000)                    # Pretend the machine is small
    with pytest.raises(ValueError, match="unknowns"):
        solid3d.solve_steady(p, 2.0)
    sim = simulate(p, SolverOptions(models=("fvm", "solid3d"), cell_mm=2.0))
    assert set(sim.results) == {"fvm"} and any("3D solid was not run" in w for w in sim.warnings)
    with pytest.raises(ValueError):                                     # Alone there is nothing else to answer
        simulate(p, SolverOptions(models=("solid3d",), cell_mm=2.0))


def test_solid3d_in_the_api_and_with_profiles():
    sim = simulate(example_board(), SolverOptions(models=("fvm", "solid3d"), cell_mm=2.0))
    assert set(sim.results) == {"fvm", "solid3d"}
    assert abs(sim.results["solid3d"].t_max - sim.results["fvm"].t_max) < 3.0
    prof = simulate(example_profile_board(), SolverOptions(models=("fvm", "solid3d"), cell_mm=4.0))
    assert "fvm" in prof.profile_results and "solid3d" not in prof.profile_results   # Steady state only
    only = simulate(example_profile_board(), SolverOptions(models=("solid3d",), cell_mm=4.0))
    assert only.profile_error and "steady state only" in only.profile_error
