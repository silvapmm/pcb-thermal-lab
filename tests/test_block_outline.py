"""!
@file test_block_outline.py
@brief A metal block that extends beyond the board outline is cut at the outline in the FVM, FDM and 3D solid, and the input check says so.
@details Before the correction the block conducted into the cells off the board, which are pinned to the ambient: on a board cut at x = 20 mm with a
         block that reached x = 10 mm the FVM and the 3D solid read about 38 degC too cold (66.8 and 67.2 against 104.7 and 105.0 degC) and no
         warning fired, because the check measured the block against the box of the board and not against its outline.
"""

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.checks import check_problem


def cut_board(block_rect):
    """!
    @brief A 60 x 40 mm two-layer board cut at x = 20 mm, a 3 W part and a 3 mm aluminium block on the bottom face.
    @param block_rect Rectangle (x0, y0, x1, y1) of the block in mm.
    @return Problem.
    """
    p = Problem.new(60, 40, 2).add_full_copper()
    p.set_outline([[20, 0], [60, 0], [60, 40], [20, 40]])
    p.add_heater(1, 3.0, rect=(35, 15, 45, 25), name="U")
    p.add_heatsink(2, 15.0, rect=block_rect, thickness_mm=3.0, k=205.0, name="Al")
    return p


def hottest(p, model):
    """!
    @brief Maximum temperature of one model on a problem.
    @param p Problem.
    @param model Model key.
    @return Temperature in degC.
    """
    return simulate(p, SolverOptions(models=(model,), cell_mm=1.0)).results[model].t_max


@pytest.mark.parametrize("model", ["fvm", "fdm", "solid3d"])
def test_block_beyond_the_outline_equals_the_block_cut_at_the_outline(model):
    beyond = hottest(cut_board((10, 5, 50, 35)), model)          # reaches x = 10 mm, 10 mm beyond the cut
    clipped = hottest(cut_board((20, 5, 50, 35)), model)         # the same block cut at x = 20 mm
    # The rise is about 80 K; the old code was 38 K cold here, the cell sampling of the cut edge is a few hundredths of a kelvin
    assert beyond == pytest.approx(clipped, abs=0.3)


def test_the_check_measures_the_block_against_the_outline():
    inside = [str(w) for w in check_problem(cut_board((20, 5, 50, 35))) if "metal block" in str(w)]
    beyond = [str(w) for w in check_problem(cut_board((10, 5, 50, 35))) if "metal block" in str(w)]
    assert not any("outside the board" in w for w in inside)
    assert any("outside the board outline" in w and "cut" in w for w in beyond)


def test_lumped_and_analytic_still_run_with_a_block_beyond_the_outline():
    sim = simulate(cut_board((10, 5, 50, 35)), SolverOptions(models=("fvm", "lumped", "analytic"), cell_mm=1.0))
    assert all(np.isfinite(sim.results[m].t_max) for m in ("fvm", "lumped", "analytic"))
