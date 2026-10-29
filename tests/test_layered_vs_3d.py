"""!
@file test_layered_vs_3d.py
@brief The layered models of the program against an independent 3D conduction solver (tests/helpers/layered3d.py, which imports nothing from the program) on a laminate coupon and on a one-layer board.

@details The numbers are those measured in research/effective-conductivity (README 4.5 and 4.11): on a Cu / FR-4 / Cu coupon of 50 x 50 mm the FVM, the 3D solid and the
         Analytic model are within 0.2 % of the independent solver, the FDM within 1.2 % and the Lumped within 0.3 % (0.5 mm cells); on a one-layer board the FVM is within 0.1 % with full
         copper and 2.5 % low with a 20 mm pad, where the FDM (-7.4 %), the Lumped (-14.7 %) and the Analytic (-28.8 %) are documented limits (roadmap), tested as ranges so
         that an improvement or a regression is noticed (the ranges are those measured on the 1 mm cells of the test). The coupon test uses the 16 mm source (epsilon 0.1) on 1 mm cells (the study uses 0.5 mm; the 1 mm cells keep every test to seconds).
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))
import layered3d as L                                          # noqa: E402

from pcbthermal import Problem, SolverOptions, simulate        # noqa: E402
from pcbthermal.model import Materials                         # noqa: E402

# --- The Cu / FR-4 / Cu coupon of Culham and Yovanovich (1998), case 2 (research/effective-conductivity/scripts/study_program_vs_coupon.py)
CU_T, GAP, K_CU, K_FR4, POWER, H, WIDTH = 35.6e-6, 1.5789e-3, 400.0, 0.4, 2.5, 5.0, 50e-3


def coupon_reference(side_mm, dx=1.0e-3):
    """!
    @brief Mean rise of the top copper under the centred source in the independent solver.
    @param side_mm Side of the centred square source in mm.
    @param dx Cell size in m.
    @return float Rise in K.
    """
    n = int(round(WIDTH / dx))
    c, s = WIDTH / 2, side_mm * 1e-3
    res = L.solve(dx, n, n, [(CU_T, K_CU, 1), (GAP, K_FR4, 8), (CU_T, K_CU, 1)], (c - s / 2, c - s / 2, c + s / 2, c + s / 2), POWER, H, H, film_under_source=True)
    return res["cell_mean_source"]


def coupon_program(side_mm, model, cell_mm=1.0):
    """!
    @brief Mean rise of the top copper under the centred source in one model of the program.
    @param side_mm Side of the centred square source in mm.
    @param model Model key.
    @param cell_mm Cell size in mm.
    @return float Rise in K.
    """
    mat = Materials(k_copper=K_CU, k_fr4_through=K_FR4, k_fr4_inplane=K_FR4)
    p = Problem.new(50.0, 50.0, layers=2, thickness_mm=(2 * CU_T + GAP) * 1e3, copper_um=CU_T * 1e6, ambient=0.0, h_top=H, h_bottom=H, h_side=None, materials=mat)
    p.add_full_copper()
    c = 25.0
    p.add_heater(1, POWER, rect=(c - side_mm / 2, c - side_mm / 2, c + side_mm / 2, c + side_mm / 2), name="U")
    T = np.asarray(simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm)).results[model].T)[0]
    ny, nx = T.shape
    xs, ys = (np.arange(nx) + 0.5) * (WIDTH / nx), (np.arange(ny) + 0.5) * (WIDTH / ny)
    h = side_mm * 1e-3 / 2
    mask = (np.abs(xs[None, :] - WIDTH / 2) < h) & (np.abs(ys[:, None] - WIDTH / 2) < h)
    return float(T[mask].mean())


# Tolerance of every model on the 16 mm source, relative to the independent solver: the documented worst case over the source sizes on 0.5 mm cells
# (README 4.5: 0.2 % for FVM, 3D solid and Analytic, 1.2 % for the FDM, 0.3 % for the Lumped). Measured here on 1 mm cells: fvm -0.02, fdm -0.59, solid3d +0.00,
# lumped +0.27, analytic -0.06 % (on 0.5 mm cells: -0.02, -0.29, +0.00, +0.15, -0.03 %; the 0.5 mm reference solve takes about 85 s, so the test uses 1 mm)
COUPON_TOLERANCE = {"fvm": 0.002, "solid3d": 0.002, "analytic": 0.002, "lumped": 0.003, "fdm": 0.012}


@pytest.fixture(scope="module")
def coupon_16mm():
    """!
    @brief The independent rise for the 16 mm source, computed once.
    @return float Rise in K.
    """
    return coupon_reference(16.0)


@pytest.mark.parametrize("model", sorted(COUPON_TOLERANCE))
def test_every_layered_model_matches_the_independent_solver_on_the_coupon(model, coupon_16mm):
    r = coupon_program(16.0, model)
    assert r == pytest.approx(coupon_16mm, rel=COUPON_TOLERANCE[model])


# --- A one-layer board (research/effective-conductivity/scripts/study_one_layer_independent.py)
CU1, H_TOP, H_BOTTOM, CELL, K_LAM = 35e-6, 10.0, 15.0, 1.0, 0.3


def one_layer_program(model, pad, thickness_mm=1.6):
    """!
    @brief Rise of the hottest point of a 60 x 60 mm one-layer board with a 6 x 6 mm part of 1 W.
    @param model Model key.
    @param pad True for a 20 mm copper pad at the centre, False for full copper.
    @param thickness_mm Board thickness in mm.
    @return float Rise in K.
    """
    p = Problem.new(60.0, 60.0, layers=1, thickness_mm=thickness_mm, copper_um=CU1 * 1e6, ambient=25.0, h_top=H_TOP, h_bottom=H_BOTTOM, h_side=None,
                    materials=Materials(k_fr4_through=K_LAM, k_fr4_inplane=K_LAM))
    if pad:
        p.add_zone(1, rect=(20, 20, 40, 40))
    else:
        p.add_full_copper()
    p.add_heater(1, 1.0, rect=(27, 27, 33, 33), name="U")
    return simulate(p, SolverOptions(models=(model,), cell_mm=CELL)).results[model].t_max - 25.0


def one_layer_reference(pad, thickness_mm=1.6):
    """!
    @brief Rise of the hottest top copper cell of the same board in the independent solver (copper in the pad, laminate elsewhere in the copper slab).
    @param pad True for a 20 mm copper pad at the centre, False for full copper.
    @param thickness_mm Board thickness in mm.
    @return float Rise in K.
    """
    n = int(round(60.0 / CELL))
    if pad:
        xs = (np.arange(n) + 0.5) * CELL
        inside = (np.abs(xs[None, :] - 30.0) < 10.0) & (np.abs(xs[:, None] - 30.0) < 10.0)
        k_top = np.where(inside, Materials().k_copper, K_LAM)
    else:
        k_top = Materials().k_copper
    res = L.solve(CELL * 1e-3, n, n, [(CU1, k_top, 1), (thickness_mm * 1e-3 - CU1, K_LAM, 8)], (27e-3, 27e-3, 33e-3, 33e-3), 1.0, H_TOP, H_BOTTOM, film_under_source=True)
    return res["cell_max_source"]


def test_one_layer_board_with_full_copper_the_fvm_and_the_3d_solid_match():
    ref = one_layer_reference(False)
    assert one_layer_program("fvm", False) == pytest.approx(ref, rel=0.002)       # measured -0.01 % (1 mm cells; -0.0 % on 0.5 mm)
    assert one_layer_program("solid3d", False) == pytest.approx(ref, rel=0.002)   # measured +0.00 %
    assert one_layer_program("fdm", False) == pytest.approx(ref, rel=0.002)       # measured -0.01 %
    # The two fast models with full copper (measured on 1 mm cells: Lumped +1.20 %, Analytic -0.83 %)
    assert one_layer_program("lumped", False) / ref - 1.0 == pytest.approx(0.012, abs=0.005)
    assert one_layer_program("analytic", False) / ref - 1.0 == pytest.approx(-0.0083, abs=0.005)


def test_one_layer_board_with_a_pad_documented_errors():
    # The research folder measured these on 0.5 mm cells: FVM -2.5, FDM -7.4, Lumped -14.7, Analytic -28.8 %. On the 1 mm cells of this fast test the pad edge is
    # sampled more coarsely and the errors are larger (measured here: -3.0, -12.6, -17.0 and -30.2 %), so the ranges below are those of the 1 mm cells.
    ref = one_layer_reference(True)
    err = {m: one_layer_program(m, True) / ref - 1.0 for m in ("fvm", "solid3d", "fdm", "lumped", "analytic")}
    assert err["fvm"] == pytest.approx(-0.030, abs=0.01)
    assert err["solid3d"] == pytest.approx(0.001, abs=0.005)                      # +0.2 % at 0.5 mm; it was +40 % without the laminate
    # Documented limits of the other three on a bare pad (docs/versions.md, chapter Planned): all low, and in this order
    assert err["fdm"] == pytest.approx(-0.126, abs=0.02)
    assert err["lumped"] == pytest.approx(-0.170, abs=0.02)
    assert err["analytic"] == pytest.approx(-0.302, abs=0.03)
    assert err["fvm"] > err["fdm"] > err["lumped"] > err["analytic"]
