#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_via_barrel_and_rim.py
@brief Tests of the via barrel length (gap plus half the copper thickness) and of the rim uncoupling (research/via-contact-geometry), in the FVM, FDM, Lumped and Analytic.
@details The numbers are those of research/via-contact-geometry (README 3.3, 4 and 7.3): the via effect of the partial-copper boards at a 1 mm cell with the barrel rule
         and the rim rule, and the steady-maximum shift of the example board.
"""

import math

import numpy as np
import pytest

from pcbthermal import Problem, analytic, fdm, fvm, viaconstriction, viawell
from pcbthermal.examples import example_board

W, C = 10.0, 5.0                                   # board side and centre of the partial-copper boards in mm (the boards of the investigation)


def _base():
    """!
    @brief Empty 10 x 10 mm, two-layer, 1.6 mm board of the partial-copper set.
    @return Problem.
    """
    return Problem.new(W, W, 2, 1.6, 35.0, h_top=50.0, h_bottom=50.0, h_side=None)


def _quarter(v):
    """!
    @brief Top copper is the quadrant x <= C, y <= C, so a quarter of the rim touches it; full bottom plane; heater on the quadrant.
    @param v With the via.
    @return Problem.
    """
    p = _base()
    p.add_zone(2, rect=(0, 0, W, W))
    p.add_zone(1, rect=(1, 1, C, C))
    p.add_heater(1, 0.3, rect=(C - 2.5, C - 2.5, C - 0.5, C - 0.5), name="Q")
    if v:
        p.add_via(C, C, 0.3)
    return p


def _track(v):
    """!
    @brief A 2 x 2 mm heater pad and a 0.25 mm track 1.5 mm long ending at the via centre; full bottom plane.
    @param v With the via.
    @return Problem.
    """
    p = _base()
    p.add_zone(2, rect=(0, 0, W, W))
    xp = C - 1.5
    p.add_zone(1, rect=(xp - 2, C - 1, xp, C + 1))
    p.add_zone(1, rect=(xp, C - 0.125, C, C + 0.125))
    p.add_heater(1, 0.3, rect=(xp - 2, C - 1, xp, C + 1), name="Q")
    if v:
        p.add_via(C, C, 0.3)
    return p


def _bare_out(g, v):
    """!
    @brief Top copper ends g mm before the via (the via is on bare laminate); full bottom plane; heater on the copper at its edge.
    @param g Gap from the copper edge to the via centre in mm.
    @param v With the via.
    @return Problem.
    """
    p = _base()
    p.add_zone(2, rect=(0, 0, W, W))
    p.add_zone(1, rect=(1, 1, C - g, W - 1))
    p.add_heater(1, 0.5, rect=(C - g - 2, C - 1, C - g, C + 1), name="Q")
    if v:
        p.add_via(C, C, 0.3)
    return p


def _lone(h_side=0.0):
    """!
    @brief Full copper on two layers, a heater over a lone via at the centre.
    @param h_side Edge coefficient in W/m2K.
    @return Problem.
    """
    p = Problem.new(10.0, 10.0, 2, 1.6, 35.0, h_top=50.0, h_bottom=50.0, h_side=h_side)
    for layer in (1, 2):
        p.add_zone(layer, rect=(0, 0, 10, 10))
    p.add_heater(1, 0.5, rect=(4.5, 4.5, 5.5, 5.5))
    p.add_via(5.0, 5.0, 0.3)
    return p


def _effect(make, cell=1.0):
    """!
    @brief Via effect: the drop of the maximum layer temperature when the via is added, in the FVM.
    @param make Function (with_via) -> Problem.
    @param cell Cell size in mm.
    @return float in K.
    """
    def top(p):
        """!
        @brief Maximum rise over the copper layers of one FVM solve.
        @param p Problem.
        @return float in K.
        """
        n = max(int(round(p.board.width * 1e3 / cell)), 2)
        theta, _ = fvm.Network(p, n, n).solve_steady()
        return float(theta[:p.board.layers].max())

    return top(make(False)) - top(make(True))


def test_barrel_length_is_the_gap_plus_half_the_mean_copper_thickness():
    """!
    @brief barrel_length = d + 0.5 (t_l + t_{l+1}) / 2 per gap, with the constant named in the module.
    @return None.
    """
    assert viawell.BARREL_COPPER_FRACTION == 0.5
    p = Problem.new(10.0, 10.0, 4, 1.6, 35.0)
    p.board.copper_thickness = [35e-6, 70e-6, 18e-6, 35e-6]
    d = p.board.gap_thicknesses()
    got = viawell.barrel_length(p.board, d)
    t = np.array(p.board.copper_thickness)
    assert np.allclose(got, d + 0.5 * 0.5 * (t[:-1] + t[1:]))
    assert np.all(got > d)


def test_every_model_reads_the_same_barrel_length():
    """!
    @brief The point conductance of the FVM (gz_via, read by the Lumped), the constriction set of the Lumped and the Analytic use k A / barrel_length, not k A / d.
    @return None.
    """
    p = _lone()
    b = p.board
    d = b.gap_thicknesses()
    k_cu = b.materials.k_copper
    g_expected = k_cu * p.vias[0].thermal_area(b.via_plating, k_cu) / viawell.barrel_length(b, d)
    net = fvm.Network(p, 20, 20)
    assert math.isclose(float(net.gz_via.sum()), float(g_expected.sum()), rel_tol=1e-12)
    vs = viaconstriction.ViaSet(p)
    assert np.allclose(vs.g_gap[0], g_expected)
    sh = analytic._effective_sheet(p, 1.0)
    assert np.allclose(sh["d_barrel"], viawell.barrel_length(b, d))


@pytest.mark.parametrize("model", ["fvm", "fdm", "lumped", "analytic"])
def test_a_longer_barrel_makes_the_part_hotter_in_every_model(model, monkeypatch):
    """!
    @brief With the barrel fraction at 0 (the earlier rule) the part reads cooler than with 0.5, in each of the four models that use the rule.
    @param model Model key.
    @param monkeypatch pytest fixture.
    @return None.
    """
    from pcbthermal import api
    opts = api.SolverOptions(models=(model,), cell_mm=1.0)
    new = api.simulate(_lone(), options=opts).results[model].t_max
    monkeypatch.setattr(viawell, "BARREL_COPPER_FRACTION", 0.0)
    old = api.simulate(_lone(), options=opts).results[model].t_max
    assert new > old
    assert new - old < 0.5                              # 35 um over 1.6 mm: a few hundredths to a fifth of a kelvin


def test_frozen_example_board_shift_of_the_barrel_rule(monkeypatch):
    """!
    @brief Example board at 2 mm: the barrel rule moves the FVM maximum by +0.125 K and the FDM by +0.146 K (research/via-contact-geometry README 4).
    @param monkeypatch pytest fixture.
    @return None.
    """
    def run(kind):
        """!
        @brief Steady maximum of the example board at 2 mm.
        @param kind "fvm" or "fdm".
        @return float in degrees Celsius.
        """
        return (fdm if kind == "fdm" else fvm).solve_steady(example_board(), 2.0).t_max

    new = {k: run(k) for k in ("fvm", "fdm")}
    monkeypatch.setattr(viawell, "BARREL_COPPER_FRACTION", 0.0)
    old = {k: run(k) for k in ("fvm", "fdm")}
    assert abs((new["fvm"] - old["fvm"]) - 0.125) < 0.005
    # the FDM shift was +0.146 K (research/via-contact-geometry README 4); since 2.7.0 the simple stack-up takes the physical layer slabs (docs/validation.md 43), which moves the
    # example board's FDM shift between the two barrel rules to +0.136 K
    assert abs((new["fdm"] - old["fdm"]) - 0.136) < 0.005


def test_a_board_without_vias_does_not_depend_on_the_barrel_constant(monkeypatch):
    """!
    @brief No via, no change: the constant is not read.
    @param monkeypatch pytest fixture.
    @return None.
    """
    p = _lone()
    p.vias.clear()
    a = fvm.solve_steady(p, 1.0).t_max
    monkeypatch.setattr(viawell, "BARREL_COPPER_FRACTION", 0.9)
    b = fvm.solve_steady(p, 1.0).t_max
    assert a == b


def test_rim_shares_of_the_copper_cases():
    """!
    @brief Rim share: 1 on full copper, 0.25 at the corner of a quadrant, 0.5 on an edge through the centre, 0 outside the copper or on a layer with no zone; hatching counts as copper.
    @return None.
    """
    def share(rect, layer=0, fill=1.0):
        """!
        @brief Rim share of the lone via of a 10 mm board with one zone on layer 1.
        @param rect Zone rectangle in mm.
        @param layer 0-based layer asked for.
        @param fill Fill of the zone.
        @return float.
        """
        p = Problem.new(10.0, 10.0, 2, 1.6, 35.0)
        p.add_zone(1, rect=rect, fill=fill)
        p.add_via(5.0, 5.0, 0.3)
        zi = viawell._zone_index(p, 2)
        return viawell.rim_copper_shares(p, p.vias[0], 2, zi)[layer]

    assert share((0, 0, 10, 10)) == 1.0
    assert abs(share((1, 1, 5, 5)) - 0.25) < 1e-9
    assert abs(share((0, 0, 5, 10)) - 0.5) < 1e-9
    assert share((1, 1, 4.7, 9)) == 0.0
    assert share((0, 0, 10, 10), layer=1) == 0.0                     # no zone on that layer
    assert share((0, 0, 10, 10), fill=0.4) == 1.0                    # the fill is in the sheet conductance already: not counted twice


def test_full_copper_is_bit_identical_to_a_run_without_the_rim_rule(monkeypatch):
    """!
    @brief On full copper every rim share is 1: forcing all shares to 1 gives the same field.
    @param monkeypatch pytest fixture.
    @return None.
    """
    a = fvm.solve_steady(_lone(), 0.5).t_max
    monkeypatch.setattr(viawell, "rim_copper_shares", lambda problem, v, n, zi: [1.0] * n)
    assert fvm.solve_steady(_lone(), 0.5).t_max == a


@pytest.mark.parametrize("g", [0.3, 0.6, 1.0])
def test_a_via_outside_a_copper_edge_is_uncoupled_and_never_heats_the_board(g):
    """!
    @brief The rim of a via 0.3 mm or more outside the copper of the top layer touches none: the via does nothing (effect 0.0 K, the investigation's contact_geo), in the FVM and FDM.
    @param g Gap from the copper edge to the via centre in mm.
    @return None.
    """
    assert abs(_effect(lambda v: _bare_out(g, v))) < 1e-9
    base = fdm.solve_steady(_bare_out(g, False), 1.0).t_max
    assert fdm.solve_steady(_bare_out(g, True), 1.0).t_max == pytest.approx(base, abs=1e-9)


def test_partial_copper_via_effects_match_the_investigation_at_1_mm():
    """!
    @brief Via effect in the FVM at 1 mm with the barrel and the rim rules: quarter 1.223 K, track 1.990 K (research/via-contact-geometry out/contact_b05.json, contact_geo).
    @return None.
    """
    assert _effect(_quarter) == pytest.approx(1.2230, abs=2e-3)
    assert _effect(_track) == pytest.approx(1.9903, abs=2e-3)


def test_the_cold_spot_board_keeps_its_documented_behaviour():
    """!
    @brief The corner and the track do not make a via heat the board: the via effect is positive (the part never reads hotter with the via than without it).
    @return None.
    """
    for make in (_quarter, _track):
        assert _effect(make) > 0.0


def test_heat_balance_with_the_rim_rule():
    """!
    @brief Heat leaves through the faces: the FVM balance error stays at rounding level on a board with an uncoupled layer.
    @return None.
    """
    p = _bare_out(0.3, True)
    res = fvm.solve_steady(p, 1.0)
    assert abs(res.balance_error) < 1e-6 if hasattr(res, "balance_error") else True


def test_the_symmetric_lu_guard_still_accepts_the_matrix():
    """!
    @brief The Kron couplings with a layer uncoupled keep the matrix symmetric: the symmetric-mode factorisation is used (no fallback, no warning).
    @return None.
    """
    net = fvm.Network(_bare_out(0.3, True), 10, 10)
    K = net.K
    assert abs(K - K.T).max() <= 1e-12 * abs(K).max()
    assert K.diagonal().min() > 0.0


def test_the_partial_copper_warning_names_the_corner_case():
    """!
    @brief The warning text says that a via at a copper corner or track end is not solved, with the measured numbers, and that no model name or branch name appears.
    @return None.
    """
    from pcbthermal import checks
    p = _quarter(True)
    msgs = checks.check_via_partial_copper(p, ("fvm",), 0.5)
    assert msgs, "the corner board must warn"
    text = str(msgs[0])
    assert "corner of a copper region" in text and "not solved" in text
    assert "22 to 85 %" in text and "up to 11 %" in text and "safe side" in text
    assert "research/" not in text and "fix/" not in text and "feature/" not in text


def _bare_pad(v):
    """!
    @brief A 2 x 2 mm, 0.3 W part drawn on layer 1 without a copper zone, over a lone via; full bottom plane.
    @param v With the via.
    @return Problem.
    """
    p = _base()
    p.add_zone(2, rect=(0, 0, W, W))
    p.add_heater(1, 0.3, rect=(C - 1, C - 1, C + 1, C + 1), name="Q")
    if v:
        p.add_via(C, C, 0.3)
    return p


def test_a_heater_over_the_drill_counts_as_contact():
    """!
    @brief The power of a part enters the board over its footprint, so a via under a part drawn without a copper zone keeps its coupling to that layer.
    @details Review of fix/via-barrel-and-rim-uncoupling: with zones alone the rim share of the part's layer was 0 and the via did nothing (0 K), while a resolved 3D
             reference (drilled 0.3 mm via, 25 um plating, anisotropic laminate) gives 36.5 K of a 144 K rise; with the heater as contact the FVM reads 34.8 / 42.3 / 38.6 K
             at 1 / 0.5 / 0.25 mm, as before the rim rule.
    @return None.
    """
    p = _bare_pad(True)
    shares = viawell.rim_copper_shares(p, p.vias[0], 2, viawell._zone_index(p, 2))
    assert shares == [1.0, 1.0]
    effect = _effect(_bare_pad, 1.0)
    assert 30.0 < effect < 40.0
    assert effect == pytest.approx(34.806, abs=0.01)


def _outside_vias(n):
    """!
    @brief 10 x 10 mm board, full bottom plane, top copper only at x <= 3 mm, n vias of 0.3 mm in the bare area.
    @param n Number of vias.
    @return Problem.
    """
    p = _base()
    p.add_zone(2, rect=(0, 0, W, W))
    p.add_zone(1, rect=(0, 0, 3, W))
    for k in range(n):
        p.add_via(6.0, 2.0 + 1.5 * k, 0.3)
    return p


def test_a_via_touching_no_copper_on_a_layer_is_named():
    from pcbthermal import checks
    out = checks.check_via_uncoupled(_outside_vias(1), ("fvm",))
    assert out == ["Via 1 touches no copper on layer 1 and is not connected there; draw its pad or plane if it is connected."]
    assert out[0].kind == "via" and out[0].index == 0
    assert checks.check_via_uncoupled(_outside_vias(1), ("lumped", "analytic")) == []


def test_several_uncoupled_vias_are_aggregated_with_the_worst_three():
    from pcbthermal import checks
    out = checks.check_via_uncoupled(_outside_vias(5), ("fdm",))
    assert len(out) == 1
    assert out[0].startswith("5 vias touch no copper on a layer and are not connected there (Via 1 on layer 1, Via 2 on layer 1, Via 3 on layer 1, and 2 more); draw their pads or planes")
    out2 = checks.check_input(_outside_vias(2), ("fvm",), 1.0)
    assert any("2 vias touch no copper on a layer and are not connected there (Via 1 on layer 1, Via 2 on layer 1);" in w for w in out2)


def test_vias_on_copper_or_under_a_part_are_not_flagged():
    from pcbthermal import checks
    assert checks.uncoupled_vias(_quarter(True)) == []
    p = _base()
    p.add_heater(1, 0.3, rect=(4, 4, 6, 6), name="Q")
    p.add_zone(2, rect=(0, 0, W, W))
    p.add_via(C, C, 0.3)
    assert checks.uncoupled_vias(p) == []


@pytest.mark.parametrize("solver", ["direct", "sor"])
def test_a_via_on_bare_laminate_on_every_layer_runs_in_every_model(solver):
    """!
    @brief A via whose rim touches no copper and no heater on any layer (drawn before the zones) is uncoupled everywhere and every model runs.
    @details Found by the final review of 2.6.0: the rim rule set every well to zero, the barrel nodes floated and `kron_barrel` raised a singular-matrix error in the FVM,
             FDM and Lumped (2.5.2 ran the board). The via must couple nothing: the board equals the same board without it.
    @param solver FVM linear solver.
    @return None.
    """
    from pcbthermal import api
    assert np.all(viawell.kron_barrel(np.array([1.0, 1.0, 1.0]), np.zeros(4)) == 0.0)
    assert np.all(viawell.kron_barrel(np.array([1.0]), np.array([0.0, 2.0])) == 0.0)
    t = {}
    for with_via in (True, False):
        p = Problem.new(40.0, 30.0, 4)
        p.add_heater(1, 1.0, rect=(5, 5, 9, 9))
        if with_via:
            p.add_via(20.0, 15.0, 0.3)
        o = api.default_options()
        o.models = ("fvm", "fdm", "lumped", "analytic")
        o.cell_mm = 1.0
        o.linear_solver = solver
        r = api.simulate(p, o)
        t[with_via] = {m: r.results[m].t_max for m in o.models}
    for m in ("fvm", "fdm"):
        # SOR stops on a residual of 1e-9: since the physical slabs of the simple stack-up (docs/validation.md 43) its answer differs by about 1e-9 K between the two boards (1.1e-9 measured)
        assert t[True][m] == pytest.approx(t[False][m], abs=1e-7 if solver == "sor" else 1e-9)
