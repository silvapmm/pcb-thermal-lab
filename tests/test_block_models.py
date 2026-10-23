"""!
@file test_block_models.py
@brief The metal block in the Lumped model (one more layer of the ring network) and in the Analytic model (a graph of tiles in the Green-function correction), against the FVM.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research", "block-and-fins", "scripts"))

import block_equivalent_study as study                                         # noqa: E402
from pcbthermal import SolverOptions, analytic, fvm, lumped, simulate          # noqa: E402

CASES = [((20, 10, 80, 70), (35, 25, 65, 55), 3.0, 204.0, 5e-4, None),
         ((5, 5, 95, 75), (25, 20, 75, 60), 1.0, 50.0, 2e-3, None),
         ((30, 20, 70, 60), (30, 20, 70, 60), 6.0, 204.0, 1e-4, None),
         ((10, 10, 90, 70), (40, 30, 60, 50), 3.0, 386.0, 5e-4, None),
         ((20, 10, 80, 70), (35, 25, 65, 55), 3.0, 204.0, 5e-4, (15.0, 1.5, 8.0))]


@pytest.mark.parametrize("rect,pad,thick,k,r_c,fins", CASES)
@pytest.mark.parametrize("model", [lumped, analytic])
def test_block_in_lumped_and_analytic_is_within_6_percent_of_the_fvm(model, rect, pad, thick, k, r_c, fins):
    p = study.make_case(rect, pad, thick, k, r_c, fins)
    ref = fvm.solve_steady(p, 1.0)
    got = model.solve_steady(p, cell_mm=1.0)
    assert abs(got.t_max - ref.t_max) < 0.06 * (ref.t_max - 25.0)
    assert got.power_out["blocks"] > 0.1 * got.power_in                          # The block takes a real share of the heat


def test_the_block_changes_the_answer_in_the_right_direction():
    """A block cools: without it the same board is hotter in every model; a thicker block cools a little more."""
    for model in (lumped, analytic, fvm):
        thin = model.solve_steady(study.make_case((20, 10, 80, 70), (35, 25, 65, 55), 1.0, 204.0, 5e-4), cell_mm=1.0).t_max
        thick = model.solve_steady(study.make_case((20, 10, 80, 70), (35, 25, 65, 55), 6.0, 204.0, 5e-4), cell_mm=1.0).t_max
        assert thick < thin


def test_simulate_runs_every_model_with_a_block_and_says_how():
    sim = simulate(study.make_case((20, 10, 80, 70), (35, 25, 65, 55), 3.0, 204.0, 5e-4), SolverOptions(models=("fvm", "lumped", "analytic"), cell_mm=2.0))
    assert set(sim.results) == {"fvm", "lumped", "analytic"}
    assert any("ring network" in w for w in sim.results["lumped"].warnings) and any("tiles" in w for w in sim.results["analytic"].warnings)
    from pcbthermal import SquareWave
    p = study.make_case((20, 10, 80, 70), (35, 25, 65, 55), 3.0, 204.0, 5e-4)
    p.heaters[0].set_profile(SquareWave(10.0, 20.0, 0.5))
    sim = simulate(p, SolverOptions(models=("fvm", "lumped"), cell_mm=2.0))
    assert "fvm" in sim.profile_results and "lumped" not in sim.profile_results
    assert any("time simulation not run" in w and "lumped" in w for w in sim.warnings)


def test_analytic_forces_the_local_corrections_for_a_block_and_the_transients_still_refuse_it():
    p = study.make_case((20, 10, 80, 70), (35, 25, 65, 55), 3.0, 204.0, 5e-4)
    r = analytic.solve_steady(p, cell_mm=1.0, local_corrections=False)
    assert any("local corrections" in w for w in r.warnings)
    with pytest.raises(ValueError, match="metal block"):
        lumped.step_responses(p, cell_mm=2.0)
