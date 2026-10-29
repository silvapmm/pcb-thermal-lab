#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_stackup.py
@brief Simple and advanced stack-up: per-layer copper, per-gap dielectric thickness and material, in every model, in the files.
"""

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.model import DIELECTRICS, Dielectric, problem_from_dict, problem_to_dict

MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")


def board(advanced=None, layers=4, power=3.0):
    """!
    @brief A 60 x 40 mm board with full copper on every layer, vias under a 6 x 6 mm heater on the top layer.
    @param advanced Optional list of (thickness mm, k_through, k_inplane) per gap, or None for the simple stack-up.
    @param layers Number of copper layers.
    @param power Heater power in W.
    @return Problem.
    """
    p = Problem.new(60, 40, layers, thickness_mm=1.6)
    p.board.h_mode = "manual"
    p.board.h_top, p.board.h_bottom = 12.0, 12.0
    for l in range(1, layers + 1):
        p.add_zone(l, rect=(2, 2, 58, 38))
    p.add_heater(1, power, rect=(27, 17, 33, 23), name="U1")
    for x in (28, 30, 32):
        for y in (18, 20, 22):
            p.add_via(x, y, 0.3)
    if advanced:
        p.board.make_advanced()
        for d, (t, kz, kp) in zip(p.board.dielectrics, advanced):
            d.thickness, d.k_through, d.k_inplane = t * 1e-3, kz, kp
        p.board.thickness = p.board.total_thickness()
    return p


def tmax(p, model, cell=1.0):
    """!
    @brief Hottest temperature of one model.
    @param p Problem.
    @param model Model key.
    @param cell Cell size in mm.
    @return Temperature in degC.
    """
    return simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max


def test_simple_mode_is_unchanged_and_the_geometry_helpers_are_consistent():
    p = board()
    b = p.board
    assert not b.is_advanced() and b.total_thickness() == b.thickness
    assert np.allclose(b.slab_thicknesses(), b.thickness / b.layers)
    assert np.allclose(b.gap_thicknesses(), b.dielectric_thickness())
    b.make_advanced()
    assert b.is_advanced() and len(b.dielectrics) == 3
    # The same board described gap by gap: the total thickness and the gaps are those of the simple description
    assert b.total_thickness() == pytest.approx(1.6e-3) and np.allclose(b.gap_thicknesses(), (1.6e-3 - 4 * 35e-6) / 3)
    assert b.slab_thicknesses().sum() == pytest.approx(b.total_thickness())
    b.make_simple()
    assert not b.is_advanced() and b.thickness == pytest.approx(1.6e-3)


def test_advanced_with_equal_gaps_is_close_to_simple_in_every_model():
    gap = (1.6 - 4 * 0.035) / 3
    for model in MODELS:
        s = tmax(board(), model)
        a = tmax(board([(gap, 0.3, 0.9)] * 3), model)
        assert a == pytest.approx(s, rel=0.03, abs=1.0), model          # Only the lumping of the laminate into the layer nodes differs


@pytest.mark.parametrize("model", MODELS)
def test_thin_prepreg_under_the_heater_cools_it_and_a_conductive_core_cools_more(model):
    thick = tmax(board([(0.5, 0.3, 0.9)] * 3), model)
    thin_top = tmax(board([(0.1, 0.3, 0.9), (0.7, 0.3, 0.9), (0.1, 0.3, 0.9)]), model)
    conductive = tmax(board([(0.1, 2.0, 2.0), (0.7, 0.3, 0.9), (0.1, 2.0, 2.0)]), model)
    assert conductive < thin_top - 0.5 and thin_top < thick + 1e-6, (model, thick, thin_top, conductive)


def test_models_agree_on_a_non_uniform_stack():
    stack = [(0.15, 0.4, 1.0), (0.9, 0.3, 0.9), (0.2, 2.0, 2.0)]
    t = {m: tmax(board(stack), m) for m in MODELS}
    rise = {m: v - 25.0 for m, v in t.items()}
    assert abs(rise["fdm"] - rise["fvm"]) < 0.04 * rise["fvm"]
    assert abs(rise["solid3d"] - rise["fvm"]) < 0.08 * rise["fvm"]
    assert abs(rise["lumped"] - rise["fvm"]) < 0.20 * rise["fvm"]
    assert abs(rise["analytic"] - rise["fvm"]) < 0.20 * rise["fvm"]


def test_copper_thickness_per_layer_changes_the_result_in_every_model():
    base, heavy = board(), board()
    heavy.board.copper_thickness = [70e-6, 35e-6, 35e-6, 70e-6]
    for model in MODELS:
        assert tmax(heavy, model) < tmax(base, model), model


def test_energy_balance_in_the_advanced_stack_and_time_response():
    stack = [(0.1, 0.4, 1.0), (1.0, 0.3, 0.9), (0.1, 0.4, 1.0)]
    sim = simulate(board(stack), SolverOptions(models=("fvm", "fdm"), cell_mm=1.0))
    for r in sim.results.values():
        assert abs(r.balance_error) < 1e-9
    from pcbthermal import fvm
    tr = fvm.solve_transient(board(stack), t_end=300.0, n_out=6, cell_mm=2.0)
    assert tr.t_max[-1] > tr.t_max[0]                                    # Heats up in time with the real masses of each layer


def test_json_round_trip_and_validation():
    p = board([(0.2, 0.4, 1.0), (0.8, 2.0, 2.0), (0.2, 0.69, 0.69)])
    p.board.dielectrics[1].name = DIELECTRICS[4][0]
    p.board.copper_thickness = [70e-6, 35e-6, 35e-6, 70e-6]
    q = problem_from_dict(problem_to_dict(p))
    assert q.board.is_advanced() and [d.name for d in q.board.dielectrics] == [d.name for d in p.board.dielectrics]
    assert np.allclose(q.board.gap_thicknesses(), p.board.gap_thicknesses()) and q.board.copper_thickness == p.board.copper_thickness
    assert q.board.total_thickness() == pytest.approx(p.board.total_thickness())
    assert tmax(q, "fvm") == pytest.approx(tmax(p, "fvm"), abs=1e-9)
    # A simple board has no "dielectrics" key and stays simple
    assert "dielectrics" not in problem_to_dict(board())["board"]
    bad = board([(0.2, 0.4, 1.0)] * 3)
    bad.board.dielectrics.pop()
    with pytest.raises(ValueError):
        bad.validate()
    bad = board([(0.2, 0.4, 1.0)] * 3)
    bad.board.dielectrics[0] = Dielectric(thickness=0.0)
    with pytest.raises(ValueError):
        bad.validate()


def test_uniform_board_matches_the_exact_series_circuit_gap_by_gap():
    """With the heater and the copper covering the whole board and insulated edges the problem is one-dimensional: a chain of layer nodes joined by k/d of every gap."""
    gaps = [(0.12, 0.4, 1.0), (0.9, 2.0, 2.0), (0.25, 0.3, 0.9)]
    p = Problem.new(40, 40, 4, thickness_mm=1.6)
    p.board.h_mode, p.board.h_top, p.board.h_bottom, p.board.h_side = "manual", 14.0, 9.0, None
    for l in range(1, 5):
        p.add_zone(l, rect=(0, 0, 40, 40))
    p.add_heater(1, 3.0, rect=(0, 0, 40, 40))
    p.board.make_advanced()
    for d, (t, kz, kp) in zip(p.board.dielectrics, gaps):
        d.thickness, d.k_through, d.k_inplane = t * 1e-3, kz, kp
    area = 0.04 * 0.04
    g = [kz / (t * 1e-3) * area for t, kz, _ in gaps]                    # W/K of every gap over the whole board
    K = np.zeros((4, 4))
    for i, gi in enumerate(g):
        K[i, i] += gi; K[i + 1, i + 1] += gi; K[i, i + 1] -= gi; K[i + 1, i] -= gi
    K[0, 0] += 14.0 * area
    K[3, 3] += 9.0 * area
    exact = np.linalg.solve(K, np.array([3.0, 0.0, 0.0, 0.0])) + 25.0
    res = simulate(p, SolverOptions(models=("fvm", "fdm"), cell_mm=4.0))
    for m in ("fvm", "fdm"):
        assert np.allclose(res.results[m].T[:, 3, 3], exact, atol=1e-6), (m, res.results[m].T[:, 3, 3], exact)
