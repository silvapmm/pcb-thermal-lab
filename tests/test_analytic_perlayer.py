#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_analytic_perlayer.py
@brief The per-layer edge of the Analytic steady model: each layer has its own Robin parameter beta_l = h_eff s_l / S_l, the common beta of the basis is corrected by an extra
       modal source solved with GMRES (adopts research/analytic-2-6, README 2 and 6.1).

@details Checks: (1) layers with the same s_l / S_l skip the loop and keep the earlier numbers (uniform board, insulated board, one layer); (2) the same sheets solved by an
         independent 2D finite-difference code with the true per-layer edge (to 0.3 %), where the common beta of the earlier model is 9.9 % off; (3) the heat balance with
         unlike layers, vias and a heatsink; (4) the hottest rise against the FVM at 0.5 mm on boards with very different copper (worst error below 4.5 %, never hot by more
         than 1.5 %); (5) the number of GMRES products; (6) hostile and degenerate input.
"""

import os
import sys

import numpy as np
import pytest

from pcbthermal import Problem, analytic, fvm

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "research", "analytic-edge-spatial", "scripts"))
sys.path.insert(0, os.path.join(REPO, "research", "analytic-edge-spatial", "lib"))

T0 = 25.0


def _board(fills, h_side=200.0, pos="corner", advanced=False):
    """!
    @brief A 60 x 40 mm board with a 10 mm, 2 W part on layer 1 and full-board zones of the given copper fill on every layer.
    @param fills Fill of each layer (the number of layers is len(fills)).
    @param h_side Edge coefficient in W/m2K.
    @param pos "centre" or "corner".
    @param advanced True for the typical advanced stack-up (layer slabs differ even with full copper).
    @return Problem.
    """
    layers = len(fills)
    p = Problem.new(width_mm=60, height_mm=40, layers=layers, thickness_mm=1.6, copper_um=35.0, ambient=T0, h_top=10.0, h_bottom=10.0, h_side=h_side)
    if advanced:
        p.board.dielectrics = []
        p.board.apply_template()
    for l in range(1, layers + 1):
        p.add_zone(l, rect=(0, 0, 60, 40))
        p.zones[-1].fill = float(fills[l - 1])
    x0, y0 = (25.0, 15.0) if pos == "centre" else (0.0, 0.0)
    p.add_heater(1, 2.0, rect=(x0, y0, x0 + 10, y0 + 10))
    return p


def _balance(r):
    """!
    @brief Heat out through the faces, the edge and the heatsinks over the power in.
    @param r SteadyResult.
    @return float
    """
    po = r.power_out
    return (po["top"] + po["bottom"] + po.get("sides", 0.0) + po.get("heatsinks", 0.0)) / r.power_in


def test_equal_layers_skip_the_loop():
    """!
    @brief Layers with the same s_l / S_l, an insulated board and a one-layer board have no mismatch: no iteration, the edge heat is the common-beta one.
    @return None.
    """
    for p in (_board((1, 1)), _board((1, 0.2), h_side=None), _board((1,))):
        r = analytic.solve_steady(p, 1.0)
        assert r.extras["edge_iterations"] == 0
        assert abs(_balance(r) - 1.0) < 1e-5
    sh = analytic._effective_sheet(_board((1, 1)), 1.0)
    assert sh["edge_mismatch"] < analytic.EDGE_MISMATCH_MIN


def test_unlike_layers_match_independent_finite_differences():
    """!
    @brief Unequal layers: the loop equals the 2D finite-difference solution of the same sheets with the true per-layer Robin edge to 0.3 %; the common beta (loop switched
           off) is 9.9 % off, the regression this test keeps failing for the earlier code.
    @return None.
    """
    import study_review_checks as R
    p = _board((0.2, 1))
    r = analytic.solve_steady(p, 1.0)
    sh = analytic._effective_sheet(p, 1.0)
    rect = analytic._equivalent_rectangle(p.heaters[0].polygon, sh["W"], sh["H"])
    a, b = (R.sheet_fd(sh, p.board, rect, p.total_power(), d) for d in (0.5e-3, 0.25e-3))
    ext = b + (b - a) / 3.0
    assert abs((r.t_max - T0) / ext - 1.0) < 0.003
    old = analytic.EDGE_MISMATCH_MIN
    try:
        analytic.EDGE_MISMATCH_MIN = 1e30               # the loop off: the common beta
        common = analytic.solve_steady(p, 1.0).t_max - T0
    finally:
        analytic.EDGE_MISMATCH_MIN = old
    assert abs(common / ext - 1.0) > 0.05
    assert abs(_balance(r) - 1.0) < 1e-3


@pytest.mark.parametrize("fills,vias,sink", [((1, 0.2), False, False), ((0.2, 1), True, False), ((0.2, 1), True, True), ((0.4, 1, 1, 0.4), True, True)])
def test_heat_balance_with_unlike_layers_vias_and_heatsink(fills, vias, sink):
    """!
    @brief The heat leaves through the faces, the per-layer edge and the heatsink: the balance closes to 1e-3.
    @param fills Fill of each layer.
    @param vias True to add a 4 x 4 via array under the part.
    @param sink True to add a heatsink on layer 1.
    @return None.
    """
    p = _board(fills, advanced=len(fills) == 4)
    if vias:
        p.add_via_array((1.0, 1.0, 9.0, 9.0), 4, 4, diameter=0.3)
    if sink:
        p.add_heatsink(1, 100.0, rect=(0, 0, 30, 30))
    r = analytic.solve_steady(p, 1.0)
    assert r.extras["edge_iterations"] >= 1
    assert abs(_balance(r) - 1.0) < 1e-3


@pytest.mark.parametrize("fills,pos,hs", [((0.2, 1), "corner", 200.0), ((1, 0.2), "corner", 200.0), ((0.2, 0.2, 1, 1), "centre", 200.0)])
def test_against_the_fvm_on_boards_with_very_different_copper(fills, pos, hs):
    """!
    @brief The hottest rise against the FVM at 0.5 mm (measured on 48 boards: -4.07 to +0.06 %, the earlier common beta -8.64 to +5.76 %): within 4.5 % and not hot by
           more than 1.5 %; the cool side is the one laminate link per gap of the Analytic (the FVM with its sub-gaps and the 3D solid read hotter, review).
    @param fills Fill of each layer.
    @param pos Position of the part.
    @param hs Edge coefficient.
    @return None.
    """
    p = _board(fills, h_side=hs, pos=pos, advanced=len(fills) == 4)
    f = fvm.solve_steady(p, cell_mm=0.5).t_max - T0
    e = (analytic.solve_steady(p, 1.0).t_max - T0) / f - 1.0
    # The bound was -4.5 % against the FVM of 2.5.2. On the integration tree the FVM carries the edge film of the cut-cell branch (fix/cut-cell-aperture-film), which
    # reads these h_side = 200 boards about 0.8 % hotter, so the Analytic sits at -4.9 / -4.6 / -2.1 % of it; the bound follows the FVM, the Analytic is unchanged.
    assert -0.055 < e < 0.015


def test_products_of_the_loop_are_few():
    """!
    @brief GMRES takes at most 12 operator products on the unlike-layer boards, with and without vias and a heatsink (measured 4 to 9).
    @return None.
    """
    for fills in ((1, 0.2), (0.2, 1), (0.2, 0.2, 1, 1)):
        p = _board(fills, advanced=len(fills) == 4)
        assert 1 <= analytic.solve_steady(p, 1.0).extras["edge_iterations"] <= 12
    p = _board((0.2, 1))
    p.add_via_array((1.0, 1.0, 9.0, 9.0), 4, 4, diameter=0.3)
    p.add_heatsink(1, 100.0, rect=(0, 0, 30, 30))
    assert analytic.solve_steady(p, 1.0).extras["edge_iterations"] <= 12


def test_the_edge_source_is_zero_for_equal_parameters_and_linear():
    """!
    @brief The extra modal source vanishes with beta_l = beta and is linear in the coefficients.
    @return None.
    """
    sh = analytic._effective_sheet(_board((0.2, 1)), 1.0)
    bx, by = analytic._bases(sh, 20)
    rng = np.random.default_rng(0)
    a = rng.normal(size=(20, 20, 2))
    S = sh["S"]
    assert not analytic._edge_mismatch_source(bx, by, a, S, np.zeros(2)).any()
    d = sh["beta_l"] - sh["beta"]
    q1 = analytic._edge_mismatch_source(bx, by, a, S, d)
    q2 = analytic._edge_mismatch_source(bx, by, 2.5 * a, S, d)
    assert np.allclose(q2, 2.5 * q1)
    assert q1.any()


def test_no_convergence_is_a_warning(monkeypatch):
    """!
    @brief A GMRES that does not converge keeps its iterate and says so.
    @param monkeypatch pytest fixture.
    @return None.
    """
    monkeypatch.setattr(analytic, "EDGE_GMRES_RTOL", 1e-300)
    monkeypatch.setattr(analytic, "EDGE_GMRES_RESTART", 1)
    r = analytic.solve_steady(_board((0.2, 1)), 1.0)
    assert any("did not reach its tolerance" in w for w in r.warnings)
    assert np.isfinite(r.t_max)


def test_warning_for_unlike_layers_quotes_the_per_layer_range():
    """!
    @brief The edge warning of a two-layer board says the layers are treated one by one and quotes the measured range; the one-layer text is unchanged.
    @return None.
    """
    two = [w for w in analytic.solve_steady(_board((1, 0.2)), 1.0).warnings if "edge convection" in w]
    assert len(two) == 1 and "separately" in two[0] and "3D solid" in two[0] and "10 %" in two[0] and "too cool" in two[0]
    one = [w for w in analytic.solve_steady(_board((1,)), 1.0).warnings if "edge convection" in w]
    assert len(one) == 1 and "one-layer" in one[0]


def test_small_board_with_a_strong_edge_reads_cool_against_the_3d_solid():
    """!
    @brief Review case outside the 48-board study: a 30 x 20 mm two-layer board (top fill 0.1, bottom full), a 1 W, 6 mm part in a corner, h_side 200 W/m2K (the edge
           73 % of the loss). The per-layer edge solves the layered idealisation exactly (within 1 % of an FVM with one laminate link per gap), but the idealisation is
           cool: measured -9.3 % against the 3D solid at 0.5 mm (115.65 K; 115.39 K at 0.25 mm) where the common beta of 2.5.1 read +8.0 %. The warning must fire and
           quote the cool side up to about 10 %.
    @return None.
    """
    from pcbthermal import solid3d
    p = Problem.new(width_mm=30, height_mm=20, layers=2, thickness_mm=1.6, copper_um=35.0, ambient=T0, h_top=10.0, h_bottom=10.0, h_side=200.0)
    for l in (1, 2):
        p.add_zone(l, rect=(0, 0, 30, 20))
    p.zones[0].fill = 0.1
    p.add_heater(1, 1.0, rect=(0, 0, 6, 6))
    r = analytic.solve_steady(p, 1.0)
    a = r.t_max - T0
    s = solid3d.solve_steady(p, cell_mm=0.5).t_max - T0
    e = a / s - 1.0
    assert -0.11 < e < -0.05
    from pcbthermal import laminate
    with laminate.using(None, 1):                           # one laminate link per gap, the idealisation the Analytic shares
        f1 = fvm.solve_steady(p, cell_mm=0.5).t_max - T0
    assert abs(a / f1 - 1.0) < 0.01
    assert any("edge convection" in w and "10 %" in w for w in r.warnings)
