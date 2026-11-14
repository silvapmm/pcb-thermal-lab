#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_laminate_edge_band.py
@brief The laminate band along the board edge (laminate.edge_band, fix/laminate-edge-band; adopts research/laminate-edge-band after its review).
@details With an edge coefficient the copper nodes held the whole slab of the edge, laminate included, at the copper temperature, so the edge film was overstated and the board read
         cold (-15 % of the rise on a 3.2 mm two-layer board at 200 W/m2K). The gaps that are cut now also carry their interior laminate nodes in a band along the edge (the cells
         that touch it grown by laminate.margin_cells), so the film acts on the laminate. The references are the hottest rises of an independent 3D finite-volume solver on a graded
         mesh (research/laminate-edge-band 11.1; 30 x 20 mm, two layers of 35 um, part of 2 W and 10 mm, faces 10 W/m2K, ambient 25 degC), typed here as numbers.
         Tests: the accuracy against them (FVM and FDM), the old error on the same boards, no change without an edge coefficient, the width of the band, the film applied once, the
         unknown count, the heat balance with the symmetric LU, and the warning above 200 W/m2K.
"""

import logging

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, checks, fdm, fvm, laminate, simulate

# Hottest rise in K of the converged 3D reference (key: thickness mm, h_side W/m2K, position of the part)
REFERENCE = {(3.2, 200.0, "corner"): 80.11228, (3.2, 200.0, "centre"): 60.70826, (1.6, 200.0, "corner"): 92.14954, (0.8, 200.0, "corner"): 111.89275}


def plate(thickness, h_side, pos, layers=2):
    """!
    @brief The 30 x 20 mm board of the reference cases.
    @param thickness Board thickness in mm.
    @param h_side Edge coefficient in W/m2K (None: insulated).
    @param pos "corner" or "centre".
    @param layers Copper layers.
    @return Problem.
    """
    p = Problem.new(width_mm=30, height_mm=20, layers=layers, thickness_mm=thickness, copper_um=35.0, ambient=25.0, h_top=10.0, h_bottom=10.0, h_side=h_side)
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, 30, 20))
    x0, y0 = (0.0, 0.0) if pos == "corner" else (10.0, 5.0)
    p.add_heater(1, 2.0, rect=(x0, y0, x0 + 10, y0 + 10))
    return p


def rise(p, model, cell):
    """!
    @brief Hottest rise of one model.
    @param p Problem.
    @param model "fvm" or "fdm".
    @param cell Cell size in mm.
    @return float Rise in K.
    """
    return simulate(p, SolverOptions(cell_mm=cell, models=(model,))).results[model].t_max - 25.0


def without_band(monkeypatch):
    """!
    @brief Switch off the band (the plan of the earlier versions).
    @param monkeypatch pytest fixture.
    @return None.
    """
    monkeypatch.setattr(laminate, "edge_band", lambda edge, d, dx, active: np.zeros(np.asarray(active).shape, dtype=bool))


@pytest.mark.parametrize("model,worst", [("fvm", -2.5), ("fdm", -2.8)])
@pytest.mark.parametrize("cell", [0.5, 0.25])
def test_the_band_alone_is_within_three_percent_of_the_converged_reference_at_200(model, worst, cell):
    # Measured (research/laminate-edge-band 11.2, 11.4, 11.5): the FVM -2.3 / -1.7 / -0.9 / -1.0 % and the FDM -2.5 / -1.9 / -1.2 / -1.2 % at 0.5 mm on the four cases, none below
    # the bounds, and never hotter than the reference at these cells; the program without the band: -15.2 / -11.2 % on the 3.2 mm board
    for (t, hs, pos), ref in REFERENCE.items():
        err = 100.0 * (rise(plate(t, hs, pos), model, cell) / ref - 1.0)
        assert worst < err < 0.5, (t, hs, pos, err)


@pytest.mark.parametrize("model", ["fvm", "fdm"])
def test_without_the_band_the_same_boards_read_far_too_cool(model, monkeypatch):
    # This test fails on a tree whose plan has no band: the thick board loses 11 to 17 % of the rise
    without_band(monkeypatch)
    err = 100.0 * (rise(plate(3.2, 200.0, "corner"), model, 0.5) / REFERENCE[(3.2, 200.0, "corner")] - 1.0)
    assert err < -10.0, err
    err = 100.0 * (rise(plate(3.2, 200.0, "centre"), model, 0.5) / REFERENCE[(3.2, 200.0, "centre")] - 1.0)
    assert err < -8.0, err


@pytest.mark.parametrize("h_side", [None, 0.0])
def test_without_an_edge_coefficient_the_networks_are_bit_for_bit_the_earlier_ones(h_side, monkeypatch):
    # The band exists only with h_side above zero: the same matrices and solution with and without the function
    for p in (plate(3.2, h_side, "corner"), plate(1.6, h_side, "centre", layers=4)):
        a, b = fvm.Network(p, 30, 20), fdm.Network(p, 1.0)
        ta, tb = a.solve_steady()[0], b.solve_steady()[0]
        without_band(monkeypatch)
        c, d = fvm.Network(p, 30, 20), fdm.Network(p, 1.0)
        monkeypatch.undo()
        assert (a.K != c.K).nnz == 0 and np.array_equal(a.C, c.C) and np.array_equal(ta, c.solve_steady()[0])
        assert (b.K != d.K).nnz == 0 and np.array_equal(b.C, d.C) and np.array_equal(tb, d.solve_steady()[0])


def test_one_layer_boards_and_boards_with_a_metal_block_keep_the_earlier_treatment(monkeypatch):
    one = plate(1.6, 50.0, "corner", layers=1)
    block = plate(1.6, 50.0, "corner")
    block.add_heatsink(1, 20.0, rect=(0, 0, 12, 12), thickness_mm=3.0, name="block")
    for p in (one, block):
        a = fvm.Network(p, 30, 20)
        without_band(monkeypatch)
        b = fvm.Network(p, 30, 20)
        monkeypatch.undo()
        assert (a.K != b.K).nnz == 0


@pytest.mark.parametrize("t,hs", [(3.2, 200.0), (1.6, 50.0)])
def test_the_width_of_the_band_does_not_matter_from_one_gap_thickness(t, hs, monkeypatch):
    # Within 0.5 point of the rise between a margin of one gap thickness and the program's margin (research/laminate-edge-band 5, 6.1)
    p = plate(t, hs, "corner")
    cell = 0.5
    base = rise(p, "fvm", cell)
    narrow = lambda d, dx: int(np.ceil(d / dx - 1e-9))                         # noqa: E731  (the thickness of the gap in cells, without the extra cell)
    wide = lambda d, dx: int(np.ceil(d / dx - 1e-9)) + 4                       # noqa: E731
    out = []
    for fn in (narrow, wide):
        monkeypatch.setattr(laminate, "margin_cells", fn)
        out.append(rise(p, "fvm", cell))
        monkeypatch.undo()
    assert max(abs(100.0 * (r / base - 1.0)) for r in out) < 0.5, (base, out)


def test_the_edge_film_of_the_interior_laminate_nodes_is_applied_once():
    # g = h_side th L / (1 + h_side dx / (2 k_xy)) on a left-edge cell away from the corners: the cut-cell film runs once, after the band (not twice, not on the copper node)
    p = plate(3.2, 200.0, "corner")
    net = fvm.Network(p, 60, 40)
    kz, kxy, _ = p.board.gap_properties()
    d = float(p.board.gap_thicknesses()[0])
    n = net.ladder.plans[0].n
    th = d / n                                                            # thickness of one interior sub-gap node (the copper nodes keep half a sub-gap each)
    j = 20
    expect = 200.0 * th * net.dy / (1.0 + 200.0 * 0.5 * net.dx / kxy[0])
    # interior layers: nodes 2 .. 2 + n - 2
    for k in range(2, 2 + n - 1):
        assert net.g_side[k, j, 0] == pytest.approx(expect, rel=1e-9), k


def test_the_unknown_count_includes_the_band():
    # fvm.unknowns and fdm.unknowns count as the network will (the memory guard and the display of the cell size use them)
    p = plate(3.2, 200.0, "corner")
    n_fvm, _, _, _ = fvm.unknowns(p, 0.5)
    net = fvm.Network(p, 60, 40)
    assert n_fvm == int((~net.drop).sum())
    n_fdm, _, _, _ = fdm.unknowns(p, 0.5)
    assert n_fdm == int((~fdm.Network(p, 0.5).drop).sum())
    # the 30 x 20 mm, 3.2 mm board at 0.5 mm: 1.92 times the two copper nodes (research/laminate-edge-band 7)
    assert n_fvm / (2 * 60 * 40) == pytest.approx(1.92, abs=0.02)
    # without an edge coefficient there is no band and nothing to count
    assert fvm.unknowns(plate(3.2, None, "corner"), 0.5)[0] == 2 * 60 * 40


@pytest.mark.parametrize("pos", ["corner", "centre"])
def test_heat_balance_and_the_symmetric_lu_with_the_band(pos, caplog):
    # The band changes the matrix, not its symmetry or the conservation: the power is all lost (faces and edge), the symmetric LU passes its probe (no fallback warning)
    p = plate(3.2, 500.0, pos)
    with caplog.at_level(logging.WARNING, logger="pcbthermal.fvm"):
        r = fvm.solve_steady(p, cell_mm=0.5)
    assert abs(r.balance_error) < 1e-9
    assert "non-symmetric" not in caplog.text and "default mode" not in caplog.text
    net = fvm.Network(p, 60, 40)
    K = net.K.tocsr()
    assert abs(K - K.T).max() <= 1e-12 * abs(K).max()
    assert abs(fdm.solve_steady(p, cell_mm=0.5).balance_error) < 1e-9


def test_the_band_follows_the_outline():
    # An outline board: the band is the cells the outline crosses, grown by the margin, on the board only
    p = Problem.new(40.0, 40.0, 2, 1.6, 35, ambient=25.0, h_top=10.0, h_bottom=10.0, h_side=50.0)
    p.add_full_copper()
    p.set_outline([[0, 10], [20, 0], [40, 10], [40, 30], [20, 40], [0, 30]])
    p.add_heater(1, 2.0, rect=(17, 17, 23, 23))
    net = fvm.Network(p, 40, 40)
    fl = net.ladder.plans[0].flagged
    assert fl.any() and not fl[20, 20] and not (fl & ~net.active).any()
    assert abs(fvm.solve_steady(p, cell_mm=1.0).balance_error) < 1e-9


def test_a_warning_above_200_for_the_layered_fvm_and_fdm_only():
    # check_edge_laminate: edge coefficient above 200 W/m2K, two or more layers, a gap that is cut, FVM or FDM
    hot, cool = plate(3.2, 500.0, "corner"), plate(3.2, 200.0, "corner")
    w = checks.check_edge_laminate(hot, ("fvm",))
    assert len(w) == 1 and "500" in w[0] and "too cool" in w[0] and "--laminate-n-max" in w[0]
    assert checks.check_edge_laminate(hot, ("fdm", "lumped"))
    assert not checks.check_edge_laminate(hot, ("lumped", "analytic", "solid3d"))
    assert not checks.check_edge_laminate(cool, ("fvm", "fdm"))                      # 200 is the limit itself: silent
    assert not checks.check_edge_laminate(plate(3.2, None, "corner"), ("fvm",))
    assert not checks.check_edge_laminate(plate(3.2, 500.0, "corner", layers=1), ("fvm",))
    thin = plate(0.8, 500.0, "corner")
    with laminate.using(s_max=5.0e-3):                                                # no gap is cut: the thin-laminate text, not silence (tested below)
        w = checks.check_edge_laminate(thin, ("fvm",))
        assert len(w) == 1 and "no gap is cut" in w[0]
    from pcbthermal.uicontext import using_ui
    with using_ui("gui"):
        text = checks.check_edge_laminate(hot, ("fvm",))[0]
    assert "Laminate sub-gaps" in text and "--" not in text.replace("--laminate", "")
    assert not any(k in text for k in ("research/", "fix/", "feature/"))
    # it is part of the model-limit warnings of a run
    assert any("edge coefficient" in str(x).lower() for x in checks.check_model_limits(hot, ("fvm",)))


def test_the_edge_warning_names_the_via_effect_and_has_no_stackup_clause():
    # research/strong-edge-laminate 8: the via effect near a strong edge reads lower still. The clause about the simple stack-up of three or more layers (equal slabs T / L) is gone:
    # since fix/simple-stackup-physical-layers the simple and the advanced stack-up are the same board, so the text is the same for both
    from pcbthermal.model import Dielectric
    two = checks.check_edge_laminate(plate(1.6, 1000.0, "corner"), ("fvm",))[0]
    assert "via" in two and "helps more than shown" in two and "simple stack-up" not in two
    assert "finite-element" in two and "HOT" in two and "not a bound" in two          # the 4-layer numbers are against a finite-element solution; eight sub-gaps read hot at a 0.25 mm cell
    four = plate(1.6, 1000.0, "corner", layers=4)
    text = checks.check_edge_laminate(four, ("fvm",))[0]
    assert "simple stack-up" not in text and "simple stack-up" not in checks.line(text)
    gap = (1.6 - 4 * 0.035) / 3 * 1e-3
    four.board.dielectrics = [Dielectric(thickness=gap, k_through=0.3, k_inplane=0.9) for _ in range(3)]
    adv = checks.check_edge_laminate(four, ("fvm",))
    assert adv and adv[0] == text
    assert not any(k in text for k in ("research/", "fix/", "feature/"))


def test_a_warning_for_the_lumped_and_analytic_when_the_edge_is_cooled_strongly_for_the_thickness():
    # check_reduced_edge_laminate (review): the Lumped and Analytic keep the edge film at the copper temperature, as the FVM did before the band; they read the 60 x 40 mm,
    # 1.6 mm board with a corner part -5.2 % (Analytic) at 200 W/m2K against a converged independent 3D solver (77.66 K), where the FVM with the band is -0.6 %
    w = checks.check_reduced_edge_laminate(plate(1.6, 100.0, "corner"), ("analytic",))
    assert len(w) == 1 and "Analytic model keeps" in w[0] and "FVM or the FDM" in w[0]
    assert "Lumped and Analytic models" in checks.check_reduced_edge_laminate(plate(3.2, 50.0, "corner"), ("fvm", "lumped", "analytic"))[0]
    assert not checks.check_reduced_edge_laminate(plate(1.6, 50.0, "corner"), ("analytic",))              # 80 W/m2K mm: about -1 %, silent
    assert not checks.check_reduced_edge_laminate(plate(3.2, 200.0, "corner"), ("fvm", "fdm", "solid3d"))
    assert not checks.check_reduced_edge_laminate(plate(3.2, None, "corner"), ("analytic",))
    assert not checks.check_reduced_edge_laminate(plate(3.2, 200.0, "corner", layers=1), ("analytic",))
    text = checks.check_reduced_edge_laminate(plate(3.2, 200.0, "corner"), ("lumped",))[0]
    assert not any(k in text for k in ("research/", "fix/", "feature/"))
    assert any("Lumped model keeps" in str(x) for x in checks.check_model_limits(plate(3.2, 200.0, "corner"), ("lumped",)))


def test_a_turned_board_converges_to_the_aligned_one_and_to_the_independent_reference():
    # Review of the turn spread: the 20 mm square of tests/helpers/cut_cell_boards.edge_board (1.6 mm, 200 W/m2K, part 3 mm off-grid by 0.5 mm, both faces 10 W/m2K) turned by
    # 0 / 22.5 / 45 degrees. With the band the peak spreads 1.0 K at 1 mm, 0.26 K at 0.5 mm and 0.05 K at 0.25 mm (measured): a discretisation error of the half-cell film on the
    # laminate nodes (cell Biot number h_side dx / k_xy = 0.22 at 1 mm), which falls with the cell; the aligned square is the one that is off at 1 mm (+0.7 % of the rise, the
    # turned ones -0.3 %) against the converged reference of research/laminate-edge-band lib/graded3d.py on the same board (113.31 K, 32 laminate sub-slabs).
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))
    import cut_cell_boards as bd
    ref = 113.31
    # Re-baselined in fix/drawn-layers-edge-film-centroid: with the film from the centroid the aligned square reads 112.03 K and the turned ones 112.47 and 112.48 K at 0.5 mm
    # (spread 0.45 K, was under 0.35 K); all three stay below the reference 113.31 K
    for cell, spread in ((1.0, 1.2), (0.5, 0.5)):
        peaks = []
        for angle in (0.0, 22.5, 45.0):
            p = bd.edge_board(angle=angle, h_side=200.0, pc=0.5, box=32.0)
            p.board.h_bottom = 10.0
            peaks.append(fvm.solve_steady(p, cell_mm=cell).t_max - 25.0)
        assert max(peaks) - min(peaks) < spread, (cell, peaks)
        assert all(abs(x / ref - 1.0) < 0.015 for x in peaks), (cell, peaks)


def test_the_edge_warning_also_fires_when_no_laminate_gap_is_cut():
    # research/strong-edge-laminate (study_thin_laminate.py), docs/validation.md 44: six layers in 1.6 mm have gaps of 0.28 mm, under the 0.4 mm sub-gap, so the rule cuts nothing and
    # the warning used to be silent while the FVM reads -2 to -6 % at 1000 W/m2K (against a finite-element solution; the cell-centred reference made it -6 to -11); two trigger paths: a cut gap (the older text) and an uncut one (the thin-laminate text)
    from pcbthermal.model import Dielectric
    six = plate(1.6, 1000.0, "corner", layers=6)
    assert all(laminate.n_for_gap(float(d), *laminate.parameters()) == 1 for d in six.board.gap_thicknesses())
    w = checks.check_edge_laminate(six, ("fvm",))
    assert len(w) == 1 and "no gap is cut" in w[0] and "-2 to -6 %" in w[0] and "not a bound" in w[0] and "finite-element" in w[0] and "HOT" in w[0]
    # the numbers are against an independent finite-element solution (tmp finite-element comparison, validation 44): about half the earlier cell-centred-reference figures; the old ones are gone
    assert "-6 to -11 %" not in w[0] and "not fully known" not in w[0]
    assert not any(k in w[0] for k in ("research/", "fix/", "feature/"))
    assert checks.check_edge_laminate(six, ("fdm",)) and not checks.check_edge_laminate(six, ("lumped", "analytic", "solid3d"))
    assert not checks.check_edge_laminate(plate(1.6, 200.0, "corner", layers=6), ("fvm",))          # 200 W/m2K is the limit itself
    assert not checks.check_edge_laminate(plate(1.6, None, "corner", layers=6), ("fvm",))
    assert not checks.check_edge_laminate(plate(1.6, 1000.0, "corner", layers=1), ("fvm",))
    # a gap that is cut keeps the older text; shortening the longest sub-gap cuts the thin gaps and switches the path
    with laminate.using(s_max=0.1e-3, n_max=8):
        assert "no gap is cut" not in checks.check_edge_laminate(six, ("fvm",))[0]
    cut = checks.check_edge_laminate(plate(3.2, 1000.0, "corner"), ("fvm",))[0]
    assert "no gap is cut" not in cut
    from pcbthermal.uicontext import using_ui
    with using_ui("gui"):
        text = checks.check_edge_laminate(six, ("fvm",))[0]
    assert "Laminate sub-gap" in text and "--" not in text
    with using_ui("cli"):
        assert "--laminate-s-max-mm" in checks.check_edge_laminate(six, ("fvm",))[0]
    # an advanced stack-up with thin gaps takes the same path
    adv = plate(1.6, 1000.0, "corner", layers=4)
    adv.board.dielectrics = [Dielectric(thickness=0.3e-3, k_through=0.3, k_inplane=0.9) for _ in range(3)]
    assert "no gap is cut" in checks.check_edge_laminate(adv, ("fvm",))[0]
    # it is part of the model-limit warnings of a run, and the one-line form is short
    assert any("no gap is cut" in str(x) for x in checks.check_model_limits(six, ("fvm",)))


def test_the_via_clauses_of_the_edge_warnings_appear_only_with_the_model_and_a_via():
    # Texts of fix/via-and-edge-warning-texts: the FDM, 3D solid and Analytic via-effect clauses need the model in the run and a via on the board
    bare = plate(1.6, 1000.0, "corner", layers=4)
    withvia = plate(1.6, 1000.0, "corner", layers=4)
    withvia.add_via(5.0, 15.0)
    fvm = checks.check_edge_laminate(withvia, ("fvm",))[0]
    assert "The FDM also reads" not in fvm and "The 3D solid reads" not in fvm
    fdm = checks.check_edge_laminate(withvia, ("fvm", "fdm", "solid3d"))[0]
    assert "The FDM also reads the effect of the vias low" in fdm and "The 3D solid reads the effect of the vias too large" in fdm
    assert "The FDM also reads" not in checks.check_edge_laminate(bare, ("fvm", "fdm", "solid3d"))[0]
    for text in (fdm, fdm.short if hasattr(fdm, "short") else ""):
        assert not any(k in text for k in ("research/", "fix/", "feature/"))
    # the one-line forms carry the clauses too, and end with one full stop (the review found '... coarse cell.; FDM ...')
    assert "FDM via effect 4 to 9 % low" in fdm.short and "3D solid via effect up to 26 % too large" in fdm.short
    assert ".;" not in fdm.short and fdm.short.endswith("too large.")
    # the 3D solid alone beside the FVM: its clause without the FDM one, in the long and the short text
    solid = checks.check_edge_laminate(withvia, ("fvm", "solid3d"))[0]
    assert "The 3D solid reads the effect of the vias too large" in solid and "The FDM also reads" not in solid
    assert "3D solid via effect" in solid.short and "FDM via effect" not in solid.short
    # the 3D solid without a layered model gets no edge-laminate warning at all (the same trigger as the FVM/FDM text)
    assert checks.check_edge_laminate(withvia, ("solid3d",)) == []
    # the thin-laminate form (no gap cut, six layers in 1.0 mm) takes the same clauses
    thin = plate(1.0, 1000.0, "corner", layers=6)
    thin.add_via(5.0, 15.0)
    uncut = checks.check_edge_laminate(thin, ("fvm", "fdm", "solid3d"))[0]
    assert "no laminate gap cut" in uncut.short and "The FDM also reads" in uncut
    assert ".;" not in uncut.short and "FDM via effect" in uncut.short
    ana = checks.check_reduced_edge_laminate(withvia, ("analytic",))[0]
    assert "effect of the vias too small near such an edge" in ana
    assert "effect of the vias" not in checks.check_reduced_edge_laminate(bare, ("analytic",))[0]
    assert "effect of the vias" not in checks.check_reduced_edge_laminate(withvia, ("lumped",))[0]
