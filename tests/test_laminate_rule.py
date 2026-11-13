#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_laminate_rule.py
@brief The rule of the laminate nodes (laminate.py) in the FVM and FDM: where the nodes are, that copper everywhere is the earlier model bit for bit, the accuracy over a window in the copper
       against an independent 3D solver, the heat balance, the ragged and the block SOR solves, the face of a part and the counts.

@details Written for fix/laminate-nodes (research/laminate-nodes). The accuracy tests use tests/helpers/layered3d.py, which imports nothing from the program: on a 1.6 mm two-layer board with a
         6 mm window in the top copper under a 6 mm part, the FVM was 18 % low with one node per layer (the earlier network, `ladder=False`) and is about 3 % low with the rule.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))
import layered3d as L                                          # noqa: E402

from pcbthermal import Problem, analysis, fdm, fvm, laminate, lumped   # noqa: E402
from pcbthermal.model import Materials                         # noqa: E402

CU, K_LAM, K_CU, SIZE, H = 35e-6, 0.3, 400.0, 30.0, 10.0
MATERIALS = Materials(k_fr4_through=K_LAM, k_fr4_inplane=K_LAM)       # isotropic laminate: the independent solver has isotropic cells


def window_board(layers=2, thickness_mm=1.6, window=6.0, part=6.0, bare_bottom=False):
    """!
    @brief A 30 x 30 mm board whose top copper has a square window under a centred 1 W part (the rest of the top copper, and a full bottom layer, are copper).
    @param layers Copper layers (2 or more; the inner and bottom layers are full copper).
    @param thickness_mm Board thickness in mm.
    @param window Side of the window in mm.
    @param part Side of the part in mm.
    @param bare_bottom True: no copper on the bottom layer (a pad-like board when `window` is zero).
    @return Problem.
    """
    p = Problem.new(SIZE, SIZE, layers, thickness_mm, CU * 1e6, ambient=25.0, h_top=H, h_bottom=H, h_side=None, materials=MATERIALS)
    c, w = SIZE / 2, window / 2
    for r in ((0, 0, SIZE, c - w), (0, c + w, SIZE, SIZE), (0, c - w, c - w, c + w), (c + w, c - w, SIZE, c + w)):
        if r[2] > r[0] and r[3] > r[1]:
            p.add_zone(1, rect=r)
    for layer in range(2, layers + 1):
        if not (bare_bottom and layer == layers):
            p.add_zone(layer, rect=(0, 0, SIZE, SIZE))
    p.add_heater(1, 1.0, rect=(c - part / 2, c - part / 2, c + part / 2, c + part / 2), name="U")
    return p


def reference_peak(window, thickness_mm=1.6, dx_mm=0.25):
    """!
    @brief Rise of the face under the part, in the independent 3D solver, for window_board(2, thickness_mm, window).
    @param window Side of the window in mm.
    @param thickness_mm Board thickness in mm.
    @param dx_mm Cell size in mm.
    @return float Rise in K.
    """
    n = int(round(SIZE / dx_mm))
    xs = (np.arange(n) + 0.5) * dx_mm
    inside = (np.abs(xs[None, :] - SIZE / 2) < window / 2) & (np.abs(xs[:, None] - SIZE / 2) < window / 2)
    k_top = np.where(inside, K_LAM, K_CU)
    gap = thickness_mm * 1e-3 - 2 * CU
    c = SIZE / 2e3
    res = L.solve(dx_mm * 1e-3, n, n, [(CU, k_top, 1), (gap, K_LAM, 8), (CU, K_CU, 1)], (c - 3e-3, c - 3e-3, c + 3e-3, c + 3e-3), 1.0, H, H, film_under_source=True)
    return res["max_source"]


def peak_rise(p, cell_mm, model=fvm):
    """!
    @brief Hottest temperature under the part, as the application reports it, as a rise.
    @param p Problem.
    @param cell_mm Cell size in mm.
    @param model fvm or fdm.
    @return float Rise in K.
    """
    r = model.solve_steady(p, cell_mm)
    return analysis.heater_stats(r, p)[0]["t_max"] - p.board.ambient


def test_the_numbers_of_the_rule():
    assert [laminate.n_for_gap(d) for d in (0.2e-3, 0.4e-3, 0.8e-3, 1.53e-3, 1.6e-3, 3.2e-3, 10e-3)] == [1, 1, 2, 4, 4, 4, 4]
    assert laminate.n_for_gap(1.6e-3, 0.2e-3, 8) == 8 and laminate.n_for_gap(1.6e-3, 0.4e-3, 1) == 1
    assert laminate.margin_cells(1.53e-3, 0.5e-3) == 5 and laminate.margin_cells(0.1e-3, 1e-3) == 2
    assert laminate.parameters() == (laminate.S_MAX, laminate.N_MAX)


def test_the_parameters_are_the_constants_and_n_max_1_turns_the_cutting_off(monkeypatch):
    assert laminate.parameters() == (laminate.S_MAX, laminate.N_MAX)
    # n_max = 1 turns the cutting off: the network of a copper-everywhere-but-a-window board has no interior node
    monkeypatch.setattr(laminate, "parameters", lambda: (laminate.S_MAX, 1))
    assert fvm.Network(window_board(), 60, 60).nl == 2


def test_the_cells_with_the_nodes_are_the_bare_cells_plus_the_margin():
    p = window_board()
    cell = 0.5
    net = fvm.Network(p, 60, 60)
    plan = net.ladder.plans[0]
    assert plan.n == 4 and plan.flagged.shape == (60, 60)
    bare = net.fill[0] < 1.0
    assert bare.sum() == 12 * 12                                     # the 6 mm window on 0.5 mm cells
    assert plan.flagged[bare].all()                                  # every bare cell has its nodes
    m = laminate.margin_cells(1.53e-3, cell * 1e-3)                  # 5 cells
    assert plan.flagged[30, 30 + 6 + m - 1] and not plan.flagged[30, 30 + 6 + m + 1]      # margin to the right of the window; none beyond
    assert not plan.flagged[0, 0] and plan.flagged.sum() < 60 * 60 / 2
    # The unknowns: 2 copper layers everywhere + 3 interior nodes in the flagged cells only
    assert int((~net.drop).sum()) == 2 * 3600 + 3 * int(plan.flagged.sum())


def test_copper_in_every_cell_is_the_earlier_model_bit_for_bit(monkeypatch):
    # Two to six layers with copper everywhere, vias and a heater: the rule changes nothing, not even in the last bit. Without an edge coefficient: with one, the laminate band
    # along the edge cuts the gaps there on purpose (test_the_edge_band_cuts_the_gaps_along_the_edge_of_a_board_with_full_copper)
    for layers in (2, 4, 6):
        p = Problem.new(40.0, 30.0, layers, 1.6, 35, ambient=25.0, h_top=10.0, h_bottom=12.0, h_side=None)
        p.add_full_copper()
        p.add_heater(1, 2.0, rect=(10, 8, 18, 16), name="U")
        p.add_via(14, 12, 0.3)
        new, old = fvm.Network(p, 40, 30), fvm.Network(p, 40, 30, ladder=False)
        assert new.nl == old.nl == layers and new.drop is not None and not new.drop.any()
        assert (new.K != old.K).nnz == 0 and np.array_equal(new.Q, old.Q) and np.array_equal(new.C, old.C)
        assert np.array_equal(new.solve_steady()[0], old.solve_steady()[0])
        # The same for the FDM (the rule switched off for the second network)
        a = fdm.Network(p, 1.0)
        monkeypatch.setattr(laminate, "uses_rule", lambda problem: False)
        b = fdm.Network(p, 1.0)
        monkeypatch.undo()
        assert a.nl == b.nl == layers and (a.K != b.K).nnz == 0 and np.array_equal(a.C, b.C)


def test_the_edge_band_cuts_the_gaps_along_the_edge_of_a_board_with_full_copper():
    # With an edge coefficient the cells that touch the edge, grown by the margin of the rule, carry the interior laminate nodes even over full copper (laminate.edge_band):
    # the film of the edge acts on the laminate, which is cooler than the copper. Everything else is the earlier network.
    p = Problem.new(40.0, 30.0, 2, 1.6, 35, ambient=25.0, h_top=10.0, h_bottom=12.0, h_side=5.0)
    p.add_full_copper()
    p.add_heater(1, 2.0, rect=(10, 8, 18, 16), name="U")
    net, old = fvm.Network(p, 40, 30), fvm.Network(p, 40, 30, ladder=False)
    plan = net.ladder.plans[0]
    m = laminate.margin_cells(plan.d, net.dx)
    assert plan.n == 4 and plan.flagged.any() and net.nl == 2 + 3
    # Flagged: the border cells grown by the margin, nothing in the middle of the board
    yy, xx = np.mgrid[0:30, 0:40]
    dist = np.minimum.reduce([xx, 39 - xx, yy, 29 - yy])
    assert np.array_equal(plan.flagged, dist <= m)
    assert plan.flagged.sum() < 40 * 30 / 2
    # Unknowns: the copper nodes everywhere plus 3 interior nodes in the band only
    assert int((~net.drop).sum()) == 2 * 1200 + 3 * int(plan.flagged.sum())
    # Capacity and the vertical conductance are conserved; the steady solution is a little hotter (the laminate at the edge is cooler than the copper, so less heat leaves there)
    assert net.C.sum() == pytest.approx(old.C.sum(), rel=1e-12)
    t_new, t_old = net.solve_steady()[0].max(), old.solve_steady()[0].max()
    assert t_old < t_new < t_old + 0.5
    # The FDM cuts its nodes in the same way and the edge coefficient 0 or None leaves both as they were
    f = fdm.Network(p, 1.0)
    assert f.ladder.plans[0].flagged.any() and f.ladder.plans[0].flagged[0, 0] and not f.ladder.plans[0].flagged[15, 20]
    p.board.h_side = 0.0
    assert not fvm.Network(p, 40, 30).ladder.refined() and not fdm.Network(p, 1.0).ladder.refined()


def test_a_window_in_the_copper_is_close_to_the_independent_solver_and_the_earlier_network_was_not():
    p = window_board()
    ref = reference_peak(6.0)
    new = peak_rise(p, 0.5)
    net = fvm.Network(p, 60, 60, ladder=False)                       # one node per copper layer, one link per gap
    old = net.solve_steady()[0][0].max()
    # Measured here (isotropic laminate of 0.3 W/mK, reference on 0.25 mm cells with 8 sub-slabs through the gap): rule -1.0 %, earlier network -9.4 %
    # (research/laminate-nodes had -3.1 and -18.4 % with an in-plane k of 0.9 W/mK)
    assert 100 * (new / ref - 1) == pytest.approx(-1.0, abs=1.0)
    assert 100 * (old / ref - 1) < -6.0                              # this test fails on the earlier network
    # A thicker laminate (3.2 mm, also n = 4) leaves more: measured -4.9 % against -26.1 % for one node per layer
    p3 = window_board(thickness_mm=3.2)
    ref3 = reference_peak(6.0, 3.2)
    assert abs(peak_rise(p3, 0.5) / ref3 - 1) < 0.08
    assert fvm.Network(p3, 60, 60, ladder=False).solve_steady()[0][0].max() / ref3 - 1 < -0.2


def test_the_one_layer_board_follows_the_same_rule():
    p = Problem.new(SIZE, SIZE, 1, 1.6, 35, ambient=25.0, h_top=H, h_bottom=15.0, h_side=None, materials=MATERIALS)
    p.add_zone(1, rect=(10, 10, 20, 20))
    p.add_heater(1, 1.0, rect=(12, 12, 18, 18), name="U")
    net = fvm.Network(p, 60, 60)
    # A copper node, three interior nodes where the laminate is bare (and a margin), the bottom node everywhere
    assert net.ladder.plans[0].n == 4 and net.nl == 5 and net.laminate_layers == [4] and net.g_bottom[0].sum() == 0.0 and net.g_bottom[4].sum() > 0.0
    n = int(round(SIZE / 0.5))
    xs = (np.arange(n) + 0.5) * 0.5
    inside = (np.abs(xs[None, :] - 15) < 5) & (np.abs(xs[:, None] - 15) < 5)
    ref = L.solve(0.5e-3, n, n, [(CU, np.where(inside, K_CU, K_LAM), 1), (1.6e-3 - CU, K_LAM, 8)], (12e-3, 12e-3, 18e-3, 18e-3), 1.0, H, 15.0, film_under_source=True)["max_source"]
    assert 100 * (peak_rise(p, 0.5) / ref - 1) == pytest.approx(-1.8, abs=1.2)       # measured -1.80 %; the two nodes of the earlier version: -4.08 %
    old = fvm.Network(p, 60, 60, ladder=False).solve_steady()[0][0].max()
    assert 100 * (old / ref - 1) < -3.0


def test_heat_balance_ragged_solve_and_conjugate_gradients_agree_with_the_full_matrix():
    first = window_board()
    for p in (first, window_board(bare_bottom=True, window=0.0)):
        r = fvm.solve_steady(p, 1.0)
        assert abs(r.balance_error) < 1e-9
        net = fvm.Network(p, 30, 30)
        assert net.drop.any() == (p is first)      # interior nodes outside the flagged cells are left out of the factorisation (a bare bottom flags every cell: nothing to drop)
        ragged = net.solve_steady("direct")[0]
        import scipy.sparse.linalg as spla
        full = spla.spsolve(net.K.tocsc(), net.Q.ravel()).reshape(ragged.shape)       # the dense matrix, pinned rows included
        assert np.abs(ragged - full).max() < 1e-9
        assert np.abs(net.solve_steady("cg", rtol=1e-12)[0] - ragged).max() < 1e-7
        assert not ragged[net.drop].any()                            # a dropped node is exactly the ambient


def test_block_sor_solves_the_refined_columns():
    # A point red-black colouring does not exist for an even n where refined and single-link columns meet; the plan columns are relaxed as blocks.
    cases = [window_board(), window_board(bare_bottom=True, window=0.0)]
    one = Problem.new(SIZE, SIZE, 1, 1.6, 35, ambient=25.0, h_top=H, h_bottom=15.0, h_side=None)
    one.add_zone(1, rect=(10, 10, 20, 20))
    one.add_heater(1, 1.0, rect=(12, 12, 18, 18))
    cases.append(one)
    cases.append(window_board(layers=4))
    withvias = window_board()
    withvias.add_via(5, 5, 0.3)
    withvias.add_via(25, 10, 0.3)
    withvias.add_via(15, 20, 0.3)
    cases.append(withvias)
    for p in cases:
        net = fvm.Network(p, 30, 30)
        assert net.ladder is not None and net.nl > net.n_board            # The laminate nodes exist, so the column blocks are what is tested
        d = net.solve_steady("direct")[0]
        s, res, info = net.solve_sor(tol=1e-10)
        assert info["converged"] and info.get("fallback") is None and res < 1e-9, info
        assert np.abs(s - d).max() < 1e-6
    # The api route (the application's SOR choice) gives the direct answer too
    a, b = fvm.solve_steady(window_board(), 1.0), fvm.solve_steady(window_board(), 1.0, method="sor", sor_tol=1e-10)
    assert b.extras["converged"] == 1.0 and abs(a.t_max - b.t_max) < 1e-6


def test_the_single_link_of_a_cell_with_absent_copper_is_lengthened():
    # A 0.2 mm gap is not cut (n = 1); where the top copper is absent the path through the gap is longer by half a copper thickness
    p = window_board(thickness_mm=0.27)                              # gap 0.2 mm
    net = fvm.Network(p, 30, 30)
    old = fvm.Network(p, 30, 30, ladder=False)
    assert net.nl == 2 and net.ladder.plans[0].n == 1
    d = 0.27e-3 - 2 * CU
    bare = net.fill[0] < 1.0
    assert bare.any()
    assert np.allclose(net.gz[0][bare], old.gz[0][bare] * d / (d + CU / 2), rtol=1e-12)
    assert np.array_equal(net.gz[0][~bare], old.gz[0][~bare])        # untouched where both layers have copper


def test_the_face_term_is_added_to_the_peak_of_a_part_over_absent_copper_only():
    p = window_board(window=8.0, part=4.0)                           # part wholly over the window
    r = fvm.solve_steady(p, 1.0)
    st = analysis.heater_stats(r, p)[0]
    cell = 1e-6
    k = K_LAM
    flux_term = r.arrays["face_peak"][0].max()
    assert flux_term == pytest.approx((1.0 / 16.0) * CU / (2 * k * cell), rel=1e-9)        # 1 W over 16 cells, the full term (the cells are bare)
    node = r.T[0][r.arrays["face_peak"][0] > 0].max()
    assert st["t_max"] == pytest.approx(node + flux_term, rel=1e-12)
    assert st["t_mean"] > r.T[0][r.arrays["face_peak"][0] > 0].mean()
    # Copper under the part: no term at all, and the reported peak is the node's
    q = window_board(window=0.0)
    rq = fvm.solve_steady(q, 1.0)
    assert "face_peak" not in rq.arrays and analysis.heater_stats(rq, q)[0]["t_max"] == rq.T[0].max()


def test_a_sliver_of_absent_copper_gets_a_share_of_the_face_term():
    # A zone of fill 0.97 under the part: the bare strip of a 1 mm cell is 30 um, far below four copper thicknesses (140 um)
    p = Problem.new(SIZE, SIZE, 2, 1.6, 35, ambient=25.0, h_top=H, h_bottom=H, h_side=None, materials=MATERIALS)
    p.add_zone(1, rect=(0, 0, SIZE, SIZE), fill=0.97)
    p.add_zone(2, rect=(0, 0, SIZE, SIZE))
    p.add_heater(1, 1.0, rect=(13, 13, 17, 17))
    r = fvm.solve_steady(p, 1.0)
    full = (1.0 / 16.0) * CU / (2 * K_LAM * 1e-6)
    assert r.arrays["face_peak"][0].max() == pytest.approx(full * (0.03 * 1e-3) / (4 * CU), rel=1e-9)
    assert r.arrays["face_mean"][0].max() == pytest.approx(full * 0.03, rel=1e-9)             # the mean weights the term by the bare share


def test_the_fdm_has_the_rule_too():
    p = window_board()
    ref = reference_peak(6.0)
    net = fdm.Network(p, 0.5)
    assert net.nl == 5 and net.drop.any() and net.n_board == 2
    r = fdm.solve_steady(p, 0.5)
    assert abs(r.balance_error) < 1e-9
    new = analysis.heater_stats(r, p)[0]["t_max"] - 25.0
    # measured -7.1 % with the arithmetic face mean, -3.2 % with the harmonic mean (fix/fdm-harmonic-face-mean: no leak across the window edge), -1.76 % with the face sheet from the
    # copper fill of the cells (fix/fdm-copper-edge-faces); still below the FVM (node sampling at the window edge)
    assert 100 * (new / ref - 1) == pytest.approx(-1.76, abs=0.5)


def test_the_extra_nodes_hold_the_heat_capacity_the_copper_nodes_gave_up():
    for p in (window_board(), window_board(bare_bottom=True, window=0.0)):
        new, old = fvm.Network(p, 30, 30), fvm.Network(p, 30, 30, ladder=False)
        assert new.C.sum() == pytest.approx(old.C.sum(), rel=1e-12)
        assert (new.g_amb.sum() - new.g_pin.sum()) == pytest.approx(old.g_amb.sum() - old.g_pin.sum(), rel=1e-12)
    one = Problem.new(SIZE, SIZE, 1, 1.6, 35, ambient=25.0, h_top=H, h_bottom=15.0, h_side=3.0)
    one.add_zone(1, rect=(10, 10, 20, 20))
    one.add_heater(1, 1.0, rect=(12, 12, 18, 18))
    new, old = fvm.Network(one, 30, 30), fvm.Network(one, 30, 30, ladder=False)
    assert new.C.sum() == pytest.approx(old.C.sum(), rel=1e-12)
    assert (new.g_amb.sum() - new.g_pin.sum()) == pytest.approx(old.g_amb.sum() - old.g_pin.sum(), rel=1e-12)       # the edge conductance is shared out, not lost
    # The transient ends at the steady state
    tr = fvm.solve_transient(one, t_end=20000.0, n_out=10, cell_mm=1.0)
    assert tr.t_max[-1] == pytest.approx(fvm.solve_steady(one, 1.0).t_max, rel=2e-3)


def test_a_metal_block_keeps_the_earlier_treatment_and_the_lumped_the_earlier_network(monkeypatch):
    p = window_board()
    p.add_heatsink(1, 10.0, rect=(8, 8, 22, 22), thickness_mm=2.0)
    net = fvm.Network(p, 30, 30)
    assert net.ladder is None and net.drop is None and net.nl == 3    # two copper layers and the block
    q = window_board()
    # The Lumped reads the earlier network (one link per gap): its answer does not depend on the rule
    base = lumped.solve_steady(q).t_max
    monkeypatch.setattr(laminate, "uses_rule", lambda problem: False)
    assert lumped.solve_steady(q).t_max == base


def test_an_inner_node_of_a_thick_simple_stack_up_gives_up_only_the_laminate_it_holds():
    # Review of fix/laminate-nodes: in the simple stack-up every node holds thickness / layers - t_cu of laminate. On a 3.2 mm three-layer board that is 1.03 mm for the
    # inner node, while the rule (n = 4 in both gaps) asked it for 2 x (d / 2 - d / 8) = 1.16 mm where its copper is absent: the node was clipped to zero capacity and lateral
    # conductance, its edge conductance went negative and the board gained 1.6 % of heat capacity. The moves are now scaled to what the node holds.
    for thickness in (3.2, 2.8):
        p = Problem.new(SIZE, SIZE, 3, thickness, 35, ambient=25.0, h_top=H, h_bottom=H, h_side=5.0)
        p.add_zone(1, rect=(0, 0, SIZE, SIZE))
        p.add_zone(2, rect=(0, 0, SIZE / 2, SIZE))                  # inner layer bare on one half: both gaps refined there
        p.add_zone(3, rect=(0, 0, SIZE, SIZE))
        p.add_heater(1, 1.0, rect=(12, 12, 18, 18))
        # The rule shares the edge conductance out among the nodes without losing any: checked on the network without the series film of the cut cells
        # (fvm.Network._cut_edge_film), which then puts each node's share behind the conduction to the edge with that node's own sheet. A laminate node has a far smaller sheet
        # than a copper node, so the film there is reduced (by 1.1e-4 to 1.3e-4 of the whole edge conductance on these boards, measured): the earlier check at 1e-12 on the
        # default network could not hold once the film was in series, and it is replaced by the bound below
        for kw in ({"cut_cells": False}, {}):
            net, old = fvm.Network(p, 30, 30, **kw), fvm.Network(p, 30, 30, ladder=False, **kw)
            assert net.ladder.plans[0].n == 4 and net.ladder.plans[0].flagged.any()
            assert net.C.sum() == pytest.approx(old.C.sum(), rel=1e-12)
            g_new, g_old = net.g_amb.sum() - net.g_pin.sum(), old.g_amb.sum() - old.g_pin.sum()
            if kw:
                assert g_new == pytest.approx(g_old, rel=1e-10)
            else:
                assert g_old * (1.0 - 1e-3) < g_new <= g_old * (1.0 + 1e-12)
            assert net.C[:3].min() > 0.0 and net.g_side.min() >= 0.0
        f = fdm.Network(p, 1.0)
        assert f.C[:3].min() > 0.0 and f.g_side.min() >= 0.0
