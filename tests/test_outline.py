"""!
@file test_outline.py
@brief Boards with an outline polygon: a rectangle drawn as a polygon changes nothing, a smaller outline equals the smaller board, energy closes, models agree.
"""

import math

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, fvm, simulate
from pcbthermal.examples import example_board
from pcbthermal.geometry import polygon_area
from pcbthermal.model import problem_from_dict, problem_to_dict

L_SHAPE = [[0, 0], [60, 0], [60, 20], [30, 20], [30, 40], [0, 40]]


def board(outline=None, width=60, height=40, layers=2, power=2.0, heater=(8, 8, 14, 14)):
    """!
    @brief A board with full copper on every layer and one heater.
    @param outline Outline polygon in mm or None.
    @param width Box width in mm.
    @param height Box height in mm.
    @param layers Number of layers.
    @param power Heater power in W.
    @param heater Rectangle of the heater in mm.
    @return Problem.
    """
    p = Problem.new(width, height, layers)
    p.board.h_mode = "manual"
    p.board.h_top = p.board.h_bottom = 12.0
    for l in range(1, layers + 1):
        p.add_zone(l, rect=(0.5, 0.5, width - 0.5, height - 0.5))
    p.add_heater(1, power, rect=heater, name="U1")
    p.add_via(11, 11, 0.3)
    if outline is not None:
        p.set_outline(outline)
    return p


def run(p, model, cell=1.0):
    """!
    @brief Run one model.
    @param p Problem.
    @param model Model key.
    @param cell Cell size in mm.
    @return SteadyResult.
    """
    return simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model]


@pytest.mark.parametrize("model", ["fvm", "fdm", "solid3d"])
def test_rectangle_as_polygon_is_identical_to_no_outline(model):
    a = run(board(), model)
    b = run(board([[0, 0], [60, 0], [60, 40], [0, 40]]), model)
    assert b.t_max == pytest.approx(a.t_max, abs=1e-9) and b.t_mean == pytest.approx(a.t_mean, abs=1e-9)


@pytest.mark.parametrize("model", ["fvm", "fdm", "solid3d"])
def test_outline_smaller_than_the_box_equals_the_smaller_board(model):
    small = board(None, width=30, height=40)
    cut = board([[0, 0], [30, 0], [30, 40], [0, 40]], width=60, height=40)
    cut.zones = [z for z in cut.zones]                                   # The copper keeps its full size: only the board shape limits it
    a, b = run(small, model), run(cut, model)
    # Same copper on the board (the zone beyond the outline is not board), same edges: the same temperatures
    assert b.t_max == pytest.approx(a.t_max, abs=0.05) and b.t_mean == pytest.approx(a.t_mean, abs=0.05)


@pytest.mark.parametrize("model", ["fvm", "fdm", "solid3d"])
def test_energy_balance_and_blank_cells_on_an_l_shaped_board(model):
    r = run(board(L_SHAPE), model)
    assert abs(r.balance_error) < 1e-9
    mask = r.arrays["board_mask"]
    assert not mask.all() and 0.7 < mask.mean() < 0.8                 # An L covers 75 % of its box
    assert r.t_min >= 25.0 - 1e-9 and r.t_max_location is not None


def test_models_agree_on_the_l_shape_and_the_heat_must_go_round_the_corner():
    rect = run(board(), "fvm").t_max
    t = {m: run(board(L_SHAPE), m).t_max for m in ("fvm", "fdm", "solid3d")}
    assert t["fvm"] > rect                                            # Less board, hotter heater
    assert abs(t["fdm"] - t["fvm"]) < 0.03 * (t["fvm"] - 25.0)
    assert abs(t["solid3d"] - t["fvm"]) < 0.03 * (t["fvm"] - 25.0)


def test_lumped_and_analytic_run_on_the_equivalent_rectangle_with_a_warning():
    sim = simulate(board(L_SHAPE), SolverOptions(models=("fvm", "lumped", "analytic"), cell_mm=2.0))
    assert list(sim.results) == ["fvm", "lumped", "analytic"] and any("same area" in w for w in sim.warnings)
    one = simulate(board(L_SHAPE), SolverOptions(models=("lumped",), cell_mm=2.0))        # Alone it runs too
    assert one.results["lumped"].t_max > 25.0
    from pcbthermal import analytic
    with pytest.raises(ValueError):                                                        # The model itself still needs a rectangle
        analytic.solve_steady(board(L_SHAPE))


def test_transient_power_outside_and_validation_and_json():
    p = board(L_SHAPE, heater=(40, 25, 50, 35))                       # Heater in the cut-out corner: off the board
    assert any("outside the board" in w for w in simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0)).warnings)
    q = board(L_SHAPE)
    tr = fvm.solve_transient(q, t_end=200.0, n_out=5, cell_mm=2.0)
    assert tr.t_max[-1] > tr.t_max[0]
    r = problem_from_dict(problem_to_dict(q))
    assert np.allclose(r.board.outline, q.board.outline) and run(r, "fvm").t_max == pytest.approx(run(q, "fvm").t_max)
    assert "outline_mm" not in problem_to_dict(board())["board"]
    for bad in ([[0, 0], [10, 0]], [[0, 0], [60, 40], [60, 0], [0, 40]], [[0, 0], [70, 0], [70, 40]]):     # Two vertices, bow tie, outside the box
        with pytest.raises(ValueError):
            board(bad).validate()


@pytest.mark.parametrize("model", ["fvm", "fdm", "solid3d"])
def test_a_part_off_the_board_still_delivers_its_power(model):
    p = board(L_SHAPE, heater=(40, 25, 50, 35))                       # Entirely in the cut-out corner
    r = run(p, model)
    assert abs(r.balance_error) < 1e-9 and r.power_in == pytest.approx(2.0)


def _ellipse(w_mm, h_mm, n=48):
    """!
    @brief Ellipse inscribed in the box, as a polygon.
    @param w_mm Box width in mm.
    @param h_mm Box height in mm.
    @param n Number of vertices.
    @return List of [x, y] in mm.
    """
    return [[w_mm / 2 * (1 + math.cos(2 * math.pi * k / n)), h_mm / 2 * (1 + math.sin(2 * math.pi * k / n))] for k in range(n)]


def test_equivalent_rectangle_keeps_area_and_moves_the_elements():
    """The box is scaled by sqrt(area ratio), positions scale with it, heater sizes stay, and a rectangular board is returned unchanged."""
    p = example_board()
    same, s1 = p.equivalent_rectangle()
    assert s1 == 1.0 and same.board.width == p.board.width
    p.set_outline(_ellipse(p.board.width * 1000, p.board.height * 1000))
    area = polygon_area(p.board.outline)
    q, s = p.equivalent_rectangle()
    assert not q.board.has_outline() and q.board.width * q.board.height == pytest.approx(area, rel=1e-9)
    assert s == pytest.approx(math.sqrt(area / (p.board.width * p.board.height)))
    for h0, h1 in zip(p.heaters, q.heaters):
        assert np.ptp(h1.polygon, axis=0) == pytest.approx(np.ptp(h0.polygon, axis=0))           # Same size
        assert h1.polygon.min() >= -1e-12 and h1.polygon[:, 0].max() <= q.board.width + 1e-12     # Inside the new box
    assert p.board.has_outline()                                                                  # The original is untouched


def test_lumped_and_analytic_on_an_ellipse_beat_the_bounding_box():
    """Parts away from the edge of an ellipse: the rectangle of the same area is within 5 % of the FVM rise and clearly better than the bounding box."""
    p = example_board()
    p.set_outline(_ellipse(p.board.width * 1000, p.board.height * 1000))
    sim = simulate(p, SolverOptions(models=("fvm", "lumped", "analytic"), cell_mm=2.0))
    assert any("same area" in w for w in sim.warnings)
    rise = sim.results["fvm"].delta_t
    box = example_board()
    box_sim = simulate(box, SolverOptions(models=("lumped", "analytic"), cell_mm=2.0))
    for m in ("lumped", "analytic"):
        err = abs(sim.results[m].t_max - sim.results["fvm"].t_max) / rise
        assert err < 0.05
        assert err < abs(box_sim.results[m].t_max - sim.results["fvm"].t_max) / rise            # Better than the bounding box
        assert sim.results[m].T.shape[0] == sim.results["fvm"].T.shape[0] and sim.results[m].dx > 0
        x, y = sim.results[m].t_max_location[1:]
        assert 0 <= x <= p.board.width and 0 <= y <= p.board.height                               # Back in the real box


ROUND = [[30 + 29.9 * math.cos(a), 30 + 29.9 * math.sin(a)] for a in np.linspace(0, 2 * math.pi, 64, endpoint=False)]


@pytest.mark.parametrize("model", ["fvm", "fdm"])
def test_time_constant_and_step_responses_leave_out_the_cells_off_the_board(model):
    # The cells off a round board are pinned to ambient with 1 W/K; counted as a path to the air they made the time constant 0.2 s instead of
    # about 100 s, and the step responses stopped long before the steady state
    square, disc = board(width=60, height=60, heater=(27, 27, 33, 33)), board(ROUND, width=60, height=60, heater=(27, 27, 33, 33))
    assert fvm.estimate_time_constant(disc) == pytest.approx(fvm.estimate_time_constant(square), rel=0.05)
    from pcbthermal import fdm
    times, z, rth = (fvm.step_responses(disc, cell_mm=2.0) if model == "fvm" else fdm.step_responses(disc, cell_mm=2.0))
    assert times[-1] > 100.0 and z[0, -1] == pytest.approx(rth[0], rel=1e-3)


def test_transient_mean_counts_only_the_board():
    p = board(ROUND, width=60, height=60, heater=(27, 27, 33, 33))
    tr = fvm.solve_transient(p, 200.0, n_out=10, cell_mm=2.0)
    net = fvm.Network(p, 30, 30)
    w = net.cover * net.dx * net.dy
    last = tr.frames[-1]
    assert tr.t_mean[-1] == pytest.approx((last * w).sum() / (last.shape[0] * w.sum()), rel=1e-12)
    assert tr.t_mean[-1] > last.mean()                                    # the plain mean counted the cells at ambient off the board
