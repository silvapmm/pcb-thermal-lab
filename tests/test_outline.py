"""!
@file test_outline.py
@brief Boards with an outline polygon: a rectangle drawn as a polygon changes nothing, a smaller outline equals the smaller board, energy closes, models agree.
"""

import math

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, fdm, fvm, simulate
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


# Outline sides that lie exactly on grid lines: the edge loss must not depend on which side of the line the board is
T60 = [[0, 30], [20, 30], [20, 0], [40, 0], [40, 30], [60, 30], [60, 60], [0, 60]]


def square(angle, side=40.0, centre=(30.0, 30.0)):
    """!
    @brief A square turned by an angle about its centre.
    @param angle Rotation in degrees (0 = sides along the grid).
    @param side Side in mm.
    @param centre Centre (x, y) in mm.
    @return List of the four vertices in mm (counter-clockwise).
    """
    r = side / math.sqrt(2.0)
    return [[centre[0] + r * math.cos(math.radians(angle + 45 + 90 * k)), centre[1] + r * math.sin(math.radians(angle + 45 + 90 * k))]
            for k in range(4)]


def ellipse(a, b, centre, n=128):
    """!
    @brief An ellipse drawn as a polygon.
    @param a Semi-axis along x in mm.
    @param b Semi-axis along y in mm.
    @param centre Centre (x, y) in mm.
    @param n Number of sides.
    @return List of the vertices in mm.
    """
    return [[centre[0] + a * math.cos(2 * math.pi * k / n), centre[1] + b * math.sin(2 * math.pi * k / n)] for k in range(n)]


DISC = ellipse(28.0, 28.0, (30.0, 30.0))
ELLIPSE = ellipse(28.0, 22.0, (30.0, 30.0))


def perimeter_mm(outline):
    """!
    @brief Geometric perimeter of a closed polygon (the independent reference of the edge length).
    @param outline Vertices in mm.
    @return Perimeter in mm.
    """
    o = np.asarray(outline, dtype=float)
    return float(np.sum(np.hypot(*(np.roll(o, -1, axis=0) - o).T)))


def closed_tau(p):
    """!
    @brief Closed-form time constant C/G of a full-copper board with an outline: face films over the area, edge film over the perimeter.
    @param p Problem.
    @return Time constant in seconds.
    """
    b = p.board
    m = b.materials
    t_cu = float(np.sum(b.copper_thickness))
    c_area = m.rho_copper * m.cp_copper * t_cu + (b.thickness - t_cu) * float(np.mean(b.layer_laminate()[1]))
    area = polygon_area(b.outline)
    return c_area * area / ((b.h_top + b.h_bottom) * area + b.h_side * b.thickness * perimeter_mm(np.asarray(b.outline) * 1000.0) / 1000.0)


def t_pair(power):
    """!
    @brief A full-copper 60 mm board cut to a T and the same T upside down, with a 6 mm part inside the arm of each.
    @param power Power of the part in W.
    @return Tuple (T, mirror image) of Problem.
    """
    up = Problem.new(60.0, 60.0, 2).add_full_copper()
    up.add_heater(1, power, rect=(27, 40, 33, 46), name="U")
    up.set_outline(T60)
    down = Problem.new(60.0, 60.0, 2).add_full_copper()
    down.add_heater(1, power, rect=(27, 14, 33, 20), name="U")
    down.set_outline([[x, 60 - y] for x, y in T60])
    return up, down


OUTLINES = [
    ([[0, 0], [60, 0], [60, 40], [0, 40]], 2.0),       # rectangle: the top side on an interior grid line, board below
    (L_SHAPE, 2.0), (L_SHAPE, 1.0),                    # sides on interior grid lines, board above/below
    (T60, 2.0), (T60, 1.0), ([[x, 60 - y] for x, y in T60], 1.0),
    (square(45), 1.0),                                 # a diamond
    # Slanted and curved sides cross cells with a sliver of board that no cover sample falls in (the cell is off the board):
    # 2 to 6 % of the perimeter was dropped there, at every cell size
    (square(3), 1.0), (square(10), 0.5), (square(30), 2.0), (DISC, 1.0), (DISC, 0.5), (ELLIPSE, 1.0),
]


@pytest.mark.parametrize("outline,cell_mm", OUTLINES)
def test_fvm_and_fdm_count_the_whole_perimeter_of_the_outline(outline, cell_mm):
    # The edge conductances the solvers use, divided by h_side x slab, are the length of the outline they count
    p = Problem.new(60.0, 60.0, 2).add_full_copper()
    p.set_outline(outline)
    b = p.board
    n = int(round(60.0 / cell_mm))
    net = fvm.Network(p, n, n, assemble=False, with_blocks=False)
    counted = net.g_side[:b.layers].sum() / (b.h_side * float(np.sum(b.slab_thicknesses()))) * 1000.0
    assert counted == pytest.approx(perimeter_mm(outline), rel=1e-3)
    nd = fdm.Network(p, cell_mm)
    counted = nd.g_side[:b.layers].sum() / (b.h_side * float(np.sum(b.slab_thicknesses()))) * 1000.0
    assert counted == pytest.approx(perimeter_mm(outline), rel=1e-3)


def test_a_t_and_its_mirror_image_give_the_same_answer():
    # With the edge sample of a grid-line side given to the cell off the board, the T lost 29 % of its perimeter and its mirror image 12 %
    up, down = t_pair(2.0)
    for model in ("fvm", "solid3d"):
        o = SolverOptions(models=(model,), cell_mm=2.0)
        a, b = simulate(up, o).results[model].t_max, simulate(down, o).results[model].t_max
        assert a == pytest.approx(b, abs=1e-6)


@pytest.mark.parametrize("cell_mm", [2.0, 1.0])
def test_time_constant_of_a_t_matches_the_closed_form(cell_mm):
    # tau = C / G with the face films over the area and the edge film over the whole perimeter (106.72 s against 104.85 before the correction)
    for p in t_pair(2.0):
        n = int(round(60.0 / cell_mm))
        net = fvm.Network(p, n, n, assemble=False, with_blocks=False)
        assert fvm.board_time_constant(net) == pytest.approx(closed_tau(p), rel=5e-4)


@pytest.mark.parametrize("outline,cell_mm", [(DISC, 1.0), (DISC, 0.5), (ELLIPSE, 1.0), (square(10), 1.0)])
def test_time_constant_of_a_curved_board_matches_the_closed_form(outline, cell_mm):
    # A large edge film makes the edge count; the slivers of board in cells off the board used to drop part of it (+0.8 % on the disc)
    p = Problem.new(60.0, 60.0, 2).add_full_copper()
    p.set_outline(outline)
    p.board.h_side = 100.0
    n = int(round(60.0 / cell_mm))
    net = fvm.Network(p, n, n, assemble=False, with_blocks=False)
    assert fvm.board_time_constant(net) == pytest.approx(closed_tau(p), rel=1e-3)


def test_a_turned_square_gives_the_answer_of_the_square_on_the_grid():
    # The physics is the same whatever the angle; a square turned by 3 degrees read 1.0 K (1.6 % of the rise) hotter before the correction
    def turned(angle):
        p = Problem.new(60.0, 60.0, 2).add_full_copper()
        p.add_heater(1, 2.0, polygon=ellipse(4.0, 4.0, (30.0, 30.0), 64), name="U")
        p.set_outline(square(angle))
        p.board.h_side = 100.0
        return simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
    ref = turned(0.0)
    for angle in (3.0, 30.0):
        r = turned(angle)
        assert r.t_max == pytest.approx(ref.t_max, abs=0.01 * ref.delta_t)
        assert r.t_mean == pytest.approx(ref.t_mean, abs=0.003 * ref.delta_t)


def test_edge_length_on_board_moves_the_lost_slivers_to_the_nearest_board_cell():
    # Direct check of the geometry helper: nothing off the board, the perimeter kept, and only cells next to the lost ones receive length
    from pcbthermal.geometry import edge_length_on_board, edge_length_per_cell
    p = Problem.new(60.0, 60.0, 2).add_full_copper().set_outline(square(30))
    active = p.board.cover(30, 30, 2e-3, 2e-3) > 0
    raw = edge_length_per_cell(p.board.outline, 30, 30, 2e-3, 2e-3)
    on = edge_length_on_board(p.board.outline, 30, 30, 2e-3, 2e-3, active)
    assert (raw * active).sum() < 0.97 * raw.sum()                       # the case does have slivers off the board
    assert on[~active].sum() == 0.0
    assert on.sum() == pytest.approx(perimeter_mm(square(30)) / 1000.0, rel=1e-9)
    grew = np.argwhere(on > raw + 1e-15)
    lost = np.argwhere((raw > 0) & ~active)
    assert all(np.min(np.max(np.abs(lost - g), axis=1)) <= 1 for g in grew)
