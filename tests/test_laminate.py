#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_laminate.py
@brief The laminate of a one-layer board: node layers under the copper in the FVM, FDM and Lumped, the series film in the Analytic model, and the bottom face for the computed coefficients.
"""

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, fdm, fvm, laminate, simulate, solid3d
from pcbthermal.model import Materials


def one_layer(pad, thickness_mm=1.6, isotropic=True):
    """!
    @brief A 60 x 60 mm one-layer board with full copper or a 20 mm pad and a 6 mm part of 1 W.
    @param pad True for a 20 mm pad, False for full copper.
    @param thickness_mm Board thickness in mm.
    @param isotropic True for FR-4 of 0.3 W/mK in both directions (as in the independent check of the research folder).
    @return Problem.
    """
    mat = Materials(k_fr4_through=0.3, k_fr4_inplane=0.3) if isotropic else Materials()
    p = Problem.new(60.0, 60.0, layers=1, thickness_mm=thickness_mm, copper_um=35, ambient=25.0, h_top=10.0, h_bottom=15.0, h_side=None, materials=mat)
    if pad:
        p.add_zone(1, rect=(20, 20, 40, 40))
    else:
        p.add_full_copper()
    p.add_heater(1, 1.0, rect=(27, 27, 33, 33), name="U")
    return p


def rise(r):
    return r.t_max - 25.0


def test_nodes_add_up_to_the_board_and_only_a_one_layer_board_has_them():
    p = one_layer(False)
    lam = laminate.nodes(p.board)
    assert lam.count == laminate.LAMINATE_NODES == 2
    assert lam.copper_slab + lam.slabs.sum() == pytest.approx(1.6e-3)
    assert laminate.nodes(Problem.new(60.0, 60.0, 2).board) is None
    net = fvm.Network(p, 30, 30)
    assert net.nl == 3 and net.laminate_layers == [1, 2] and net.g_bottom[0].sum() == 0.0 and net.g_bottom[2].sum() > 0.0


@pytest.mark.parametrize("model", ["fvm", "fdm"])
def test_a_uniform_one_layer_board_matches_the_series_closed_form(model):
    # Full copper heated all over, no edge loss: top film on the copper node, bottom film in series with the laminate
    p = Problem.new(50.0, 50.0, layers=1, thickness_mm=1.6, copper_um=35, ambient=25.0, h_top=10.0, h_bottom=15.0, h_side=None).add_full_copper()
    p.add_heater(1, 5.0, rect=(0, 0, 50, 50), name="U")
    b = p.board
    t_lam = b.thickness - b.copper_thickness[0]
    expected = 5.0 / (0.05 * 0.05 * (10.0 + 1.0 / (1.0 / 15.0 + t_lam / b.materials.k_fr4_through)))
    r = (fvm.solve_steady(p, 5.0) if model == "fvm" else fdm.solve_steady(p, 5.0))
    assert rise(r) == pytest.approx(expected, rel=1e-9)
    assert abs(r.balance_error) < 1e-9 and r.T.shape[0] == 1


def test_the_layered_models_follow_the_3d_solid_on_a_one_layer_board():
    # The 3D solid agrees with an independent 3D solver within 0.2 % on these boards (research/effective-conductivity 4.11);
    # before the laminate nodes the FVM was 1.9 % low with full copper and 10 % low with the pad
    for pad, tol_fvm in ((False, 0.005), (True, 0.04)):
        p = one_layer(pad)
        ref = rise(solid3d.solve_steady(p, 0.5))
        res = simulate(p, SolverOptions(models=("fvm", "fdm", "lumped", "analytic"), cell_mm=0.5)).results
        assert abs(rise(res["fvm"]) / ref - 1.0) < tol_fvm
        if not pad:
            assert abs(rise(res["fdm"]) / ref - 1.0) < 0.005
            assert abs(rise(res["lumped"]) / ref - 1.0) < 0.03
            assert abs(rise(res["analytic"]) / ref - 1.0) < 0.01


def test_sor_cg_and_direct_agree_on_a_one_layer_board():
    p = one_layer(True, isotropic=False)
    net = fvm.Network(p, 60, 60)
    direct, _ = net.solve_steady("direct")
    cg, _ = net.solve_steady("cg", rtol=1e-12)
    sor, res, info = net.solve_sor(tol=1e-10)
    assert info["converged"] and np.abs(cg - direct).max() < 1e-6 and np.abs(sor - direct).max() < 1e-6


def test_the_transient_ends_on_the_steady_state_and_the_bottom_face_is_cooler():
    p = one_layer(True, isotropic=False)
    steady = fvm.solve_steady(p, 2.0)
    tr = fvm.solve_transient(p, 20.0 * fvm.estimate_time_constant(p), n_out=20, cell_mm=2.0)
    assert tr.t_max[-1] == pytest.approx(steady.t_max, abs=1e-3)
    assert 25.0 < steady.extras["bottom_face_mean"] < steady.layer_mean[0]


def test_computed_coefficients_use_the_bottom_face():
    p = one_layer(True, isotropic=False)
    p.board.h_mode = "computed"
    r = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0)).results["fvm"]
    from pcbthermal import convection
    _, hb, _ = convection.board_h(p.board, r.layer_mean[0], r.extras["bottom_face_mean"])
    assert r.extras["h_bottom"] == pytest.approx(hb, abs=0.02)
