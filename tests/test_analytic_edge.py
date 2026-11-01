#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_analytic_edge.py
@brief The Analytic model moves the heat lost through the board edge to the faces (Muzychka, Culham and Yovanovich 2003, AIAA 2003-4188, eq. 29).

@details Checks: (1) a closed form, the one-layer board under a heater that covers it is uniform and its rise is P / (h_faces A + h_side perimeter t), insulated or edge-cooled;
         (2) the heat balance, top + bottom + heatsinks + sides = power, with vias and a heatsink; (3) the three uniform two-layer boards of the review
         (40 x 30, 60 x 40 and 100 x 80 mm) against the FVM, where the Analytic used to read +0.8 to +7.8 % warm; (4) no edge coefficient (None or 0) leaves the
         result unchanged, and the modal matrix of the transient carries the same extra coefficient; (5) the warning appears only when the edge loss is put in the wrong place,
         with the sense of the error; (6) a board with an outline uses the perimeter of the real outline.
"""

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal import analytic

T_AMB = 25.0


def _plate(w, h, src, h_side, layers=2, thickness=1.6, h_face=10.0):
    """!
    @brief A uniform board (full copper on every layer) with a centred square source on layer 1.
    @param w Width in mm.
    @param h Height in mm.
    @param src Side of the centred square source in mm (its power is 2 W).
    @param h_side Edge coefficient in W/m2K (None = insulated).
    @param layers Number of copper layers.
    @param thickness Board thickness in mm.
    @param h_face Coefficient of both faces in W/m2K.
    @return Problem.
    """
    p = Problem.new(width_mm=w, height_mm=h, layers=layers, thickness_mm=thickness, copper_um=35.0, ambient=T_AMB, h_top=h_face, h_bottom=h_face, h_side=h_side)
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, w, h))
    p.add_heater(1, 2.0, rect=(w / 2 - src / 2, h / 2 - src / 2, w / 2 + src / 2, h / 2 + src / 2))
    return p


def _rise(p, model, cell=1.0):
    """!
    @brief Maximum rise of one model.
    @param p Problem.
    @param model Model key.
    @param cell Cell size in mm.
    @return float Rise above the ambient in K.
    """
    return simulate(p, SolverOptions(cell_mm=cell, models=(model,))).results[model].t_max - T_AMB


@pytest.mark.parametrize("h_side", [10.0, 100.0])
def test_closed_form_uniform_board(h_side):
    """The one-layer board under a heater that covers it is uniform, so the edge conductance simply adds to the loss at its node.

    theta_edge = P / (P / theta_insulated + h_side perimeter t): the insulated board (whatever its face and laminate film paths are) is
    the reference, and the edge adds h_side x perimeter x thickness in parallel.
    """
    w, h, t, hf = 40.0, 30.0, 1.6, 10.0

    def board(hs):
        p = Problem.new(width_mm=w, height_mm=h, layers=1, thickness_mm=t, copper_um=35.0, ambient=T_AMB, h_top=hf, h_bottom=hf, h_side=hs)
        p.add_zone(1, rect=(0, 0, w, h))
        p.add_heater(1, 2.0, rect=(0, 0, w, h))
        return p

    theta0 = _rise(board(None), "analytic")
    edge = h_side * 2 * (w + h) * 1e-3 * t * 1e-3                 # W/K
    expected = 2.0 / (2.0 / theta0 + edge)
    got = _rise(board(h_side), "analytic")
    assert got == pytest.approx(expected, rel=1e-9)
    assert got < theta0                                          # the edge takes heat away: strictly cooler than the insulated bar


def test_edge_cooled_bar_cooler_and_monotone():
    """More edge coefficient, cooler board; the insulated board is the upper bound."""
    rises = [_rise(_plate(40, 30, 10, hs), "analytic") for hs in (None, 10.0, 50.0)]
    assert rises[0] > rises[1] > rises[2]


@pytest.mark.parametrize("w,h,src,lo,hi", [(40, 30, 5, -0.9, 0.3), (40, 30, 20, -1.0, 0.3), (60, 40, 20, -1.0, 0.3), (100, 80, 20, -1.0, 0.3)])
def test_uniform_two_layer_boards_against_the_fvm(w, h, src, lo, hi):
    """Measured: -0.3 / -0.5 / -0.7 / -0.7 % against the FVM at 1 mm (they were +6.1 / +7.8 / +4.4 / +0.9 % with the edge left out)."""
    p = _plate(w, h, src, 10.0)
    err = 100.0 * (_rise(p, "analytic") / _rise(p, "fvm") - 1.0)
    assert lo < err < hi


def test_heat_balance_with_vias_heatsink_and_edge():
    """Every watt leaves through the faces, the heatsink or the edge, with the local (Green function) corrections on."""
    p = _plate(60, 40, 8, 25.0, layers=4, thickness=1.6)
    p.add_via_array((26, 16, 34, 24), 4, 4, diameter=0.3)
    p.add_heatsink(4, 200.0, rect=(10, 10, 20, 20))
    for local in (True, False):
        r = analytic.solve_steady(p, cell_mm=1.0, local_corrections=local)
        out = r.power_out
        assert out["sides"] > 0.0
        assert sum(out.values()) == pytest.approx(r.power_in, rel=1e-6)


def test_edge_loss_share_matches_the_fvm():
    """The share of the heat that leaves through the edge agrees with the FVM within a few percent of the power on a small board."""
    p = _plate(40, 30, 10, 10.0)
    sim = simulate(p, SolverOptions(cell_mm=1.0, models=("fvm", "analytic")))
    share_a = sim.results["analytic"].power_out["sides"] / 2.0
    share_f = sim.results["fvm"].power_out["sides"] / 2.0
    assert abs(share_a - share_f) < 0.01


@pytest.mark.parametrize("h_side", [None, 0.0])
def test_no_edge_loss_is_the_old_analytic(h_side):
    """Without an edge coefficient nothing changes: no extra key, the face and heatsink split as before, the temperature equals the insulated closed form."""
    p = _plate(60, 40, 20, h_side)
    r = analytic.solve_steady(p, cell_mm=1.0)
    assert "sides" not in r.power_out
    sh = analytic._effective_sheet(p, 1.0)
    assert np.all(sh["h_edge"] == 0.0)
    assert sh["h_tot"] == 20.0                                    # h_top + h_bottom exactly
    assert sum(r.power_out.values()) == pytest.approx(r.power_in, rel=1e-6)
    # same numbers as an edge coefficient of None on the same board (None and 0 are the same board)
    q = _plate(60, 40, 20, None)
    assert np.array_equal(r.T, analytic.solve_steady(q, cell_mm=1.0).T)


def test_transient_modal_matrix_carries_the_edge_coefficient():
    """The (0, 0) mode of the transient matrix has the row sums h_top + h_bottom + the edge coefficients of the layers, as the steady sheet does."""
    p = _plate(40, 30, 10, 10.0, layers=2)
    sh = analytic._effective_sheet(p, 1.0)
    A = analytic._modal_matrix(p, sh, 4, 1.0)
    expected = 20.0 + 10.0 * 2 * (0.040 + 0.030) * 1.6e-3 / (0.040 * 0.030)
    assert A[0, 0].sum() == pytest.approx(expected, rel=1e-9)
    p0 = _plate(40, 30, 10, None, layers=2)
    A0 = analytic._modal_matrix(p0, analytic._effective_sheet(p0, 1.0), 4, 1.0)
    assert A0[0, 0].sum() == pytest.approx(20.0, rel=1e-12)


def test_warning_only_when_the_edge_loss_is_misplaced():
    """Typical edge coefficient on a small 1.6 mm board: silent (the edge is near the mean temperature); a large coefficient on a thick board: warned,
    and the warning gives the sense of the error, low with the part at the centre, high with the part in a corner (both checked against the FVM)."""
    quiet = analytic.solve_steady(_plate(40, 30, 10, 10.0), cell_mm=1.0)
    assert not any("edge convection" in w for w in quiet.warnings)
    for pos, sense in (("centre", "low"), ("corner", "high")):
        p = _plate(100, 80, 10, 50.0, thickness=3.2)
        if pos == "corner":
            p.heaters[0].polygon = p.heaters[0].polygon - p.heaters[0].polygon.min(axis=0)       # the part moved to the corner (0, 0)
        loud = analytic.solve_steady(p, cell_mm=1.0)
        assert any("edge convection" in w and f"reads {sense}" in w for w in loud.warnings), pos
        err = _rise(p, "analytic") / _rise(p, "fvm") - 1.0
        assert (err < -0.02) if sense == "low" else (err > 0.05)


def _t_board(h_side):
    """!
    @brief The T of the frozen-number boards (80 x 60 mm box, 2 layers of full copper, a 10 mm part of 4 W in the stem).
    @param h_side Edge coefficient in W/m2K (None = insulated).
    @return Problem.
    """
    p = Problem.new(width_mm=80, height_mm=60, layers=2, thickness_mm=1.6, copper_um=35.0, ambient=T_AMB, h_top=10.0, h_bottom=15.0, h_side=h_side)
    p.set_outline([[0, 60], [0, 40], [30, 40], [30, 0], [50, 0], [50, 40], [80, 40], [80, 60]])
    for layer in (1, 2):
        p.add_zone(layer, rect=(0, 0, 80, 60))
    p.add_heater(1, 4.0, rect=(35, 10, 45, 20))
    return p


def test_outline_uses_the_perimeter_of_the_real_edge():
    """On a board with an outline the Analytic runs on the rectangle of the same area, but the edge that loses heat is the real one:
    280 mm for the T against 198 mm for the rectangle. The heat through the edge then agrees with the FVM on the real shape (it was 28 % short)."""
    eq, _ = _t_board(10.0).equivalent_rectangle()
    assert eq.board.edge_perimeter == pytest.approx(0.280, rel=1e-12)
    sim = simulate(_t_board(10.0), SolverOptions(cell_mm=1.0, models=("fvm", "analytic")))
    side_a = sim.results["analytic"].power_out["sides"]
    side_f = sim.results["fvm"].power_out["sides"]
    assert side_a == pytest.approx(side_f, rel=0.05)
    # the perimeter is not a saved field: a board without outline uses its box
    q = Problem.new(width_mm=40, height_mm=30, layers=2, thickness_mm=1.6, copper_um=35.0, h_side=10.0)
    assert getattr(q.equivalent_rectangle()[0].board, "edge_perimeter", None) is None
