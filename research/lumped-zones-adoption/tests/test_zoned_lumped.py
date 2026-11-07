#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_zoned_lumped.py
@brief Tests of the zoned Lumped proposal on the 2.4.5 program: the closed forms, the equality with the program when the zones are off, the invariants of the network and the helper rules.
@details The 16 tests pass (about a second). Run: `.venv/bin/python -m pytest research/lumped-zones-adoption/tests -q` from the repository root.
         The tests that build a board use small boards (20 mm, 0.5 to 1 mm cells) and take seconds; none needs the fine-grid references.
"""

import math
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FOLDER, "lib"))

import zref                                                                  # noqa: E402
import zoned_lumped as zl                                                    # noqa: E402
from pcbthermal import lumped, viaconstriction                               # noqa: E402
from pcbthermal.fvm import Network                                           # noqa: E402

SMALL = dict(layers=4, n=5, pitch=1.2, dia=0.3, fill=385.0, side=24.0, src=10.0, power=3.0)


@pytest.fixture(autouse=True)
def program_as_released():
    """!
    @brief "The program" of these tests is the one-node network of release 2.4.5: since the adoption (feature/lumped-zones) the program has the zones itself, so its switch
           `lumped.ZONES` is turned off for every test of this folder and restored after it.
    @return None (a generator fixture).
    """
    saved = lumped.ZONES
    lumped.ZONES = False
    yield
    lumped.ZONES = saved


def build(spec, cell_mm=0.5):
    """!
    @brief The Problem of a spec, its network on the Lumped grid, the via set and the footprint coverage of the first heater.
    @param spec Spec dict of `refs.make_problem`.
    @param cell_mm Raster in mm.
    @return Tuple (problem, net, vias or None, cov).
    """
    zref.pc.load_libraries()
    p = zref.refs.make_problem(spec)
    b = p.board
    nx, ny = int(round(b.width * 1000 / cell_mm)), int(round(b.height * 1000 / cell_mm))
    net = Network(p, nx, ny, assemble=False, with_blocks=True, ladder=False)
    vias = viaconstriction.ViaSet(p) if p.vias else None
    return p, net, vias, lumped._footprint_coverage(net, p.heaters[0])


def same_network(a, b, tol=1e-10):
    """!
    @brief Compare two heater-network dicts: temperatures, peak, matrix and capacities.
    @param a First dict.
    @param b Second dict.
    @param tol Relative tolerance.
    @return None (asserts).
    """
    assert a["theta"].shape == b["theta"].shape
    assert np.allclose(a["theta"], b["theta"], rtol=tol, atol=tol)
    # the Bessel factors of the interior relations are a difference of nearly equal numbers for a small footprint: 1e-13 in the loss gives 1e-7 in the peak
    assert a["peak_extra"] == pytest.approx(b["peak_extra"], rel=1e-5, abs=1e-10)
    assert np.allclose(a["K"], b["K"], rtol=tol, atol=tol)
    assert np.allclose(a["C"], b["C"], rtol=tol)


def test_annulus_limits():
    """!
    @brief The annulus resistance tends to 1/(8 pi S) of a uniformly heated disc as the inner radius goes to zero and vanishes as the inner radius reaches the outer one.
    @return None.
    """
    s = 0.37
    assert zl.annulus_out_resistance(s, 1e-9, 3e-3) == pytest.approx(1.0 / (8.0 * math.pi * s), rel=1e-6)
    assert zl.annulus_out_resistance(s, 2.99e-3, 3e-3) < 0.02 / (8.0 * math.pi * s)
    assert zl.annulus_out_resistance(s, 3e-3, 3e-3) == 0.0


def test_link_of_concentric_discs_is_krogh_plus_core_internal():
    """!
    @brief For a disc core in a disc footprint the logarithmic-potential link equals the Krogh resistance of the annulus plus 1/(8 pi S) of the core.
    @return None.
    """
    n, dx = 160, 0.05e-3
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.hypot(xx - n / 2 + 0.5, yy - n / 2 + 0.5) * dx
    r_c, a_f = 2.0e-3, 3.8e-3
    core = (r <= r_c).astype(float)
    ann = ((r > r_c) & (r <= a_f)).astype(float)
    s = 0.9
    pot = zl.mutual_potentials(ann, core, dx, dx, 700, "block")
    r_num = pot / (2.0 * math.pi * s)
    r_ref = viaconstriction.krogh(s, a_f, r_c) + 1.0 / (8.0 * math.pi * s)
    assert r_num == pytest.approx(r_ref, rel=0.03)


def test_block_points_keep_the_weight_and_the_centroid():
    """!
    @brief Blocks conserve the total weight and the weighted centroid of the region and keep about the wanted number of points.
    @return None.
    """
    w = np.zeros((90, 70))
    w[10:80, 5:65] = 1.0
    pos, wb, db = zl.block_points(w, 1e-3, 1e-3, 700)
    assert wb.sum() == pytest.approx(w.sum())
    yy, xx = np.nonzero(w)
    assert (pos * wb[:, None]).sum(axis=0) / wb.sum() == pytest.approx([xx.mean() * 1e-3, yy.mean() * 1e-3], rel=1e-9)
    assert len(pos) <= 1.2 * 700 + 50
    assert np.all(db > 0)


def test_footprint_potentials_stride_is_the_program():
    """!
    @brief `mode="stride"` returns what the program's function returns.
    @return None.
    """
    p, net, vias, cov = build(SMALL)
    a = zl.footprint_potentials(cov, net.dx, net.dy, "stride")
    b = lumped._footprint_potentials(cov, net.dx, net.dy)
    assert a == b


def test_footprint_potentials_blocks_against_every_cell():
    """!
    @brief On a 20 mm square at 0.5 mm (1600 cells, above the 900 of the program) the block decimation is within 1 % of the exact potentials in both terms.
    @return None.
    """
    n, dx = 60, 0.5e-3
    cov = np.zeros((n, n))
    cov[10:50, 10:50] = 1.0
    ex = zl.footprint_potentials_exact(cov, dx, dx)
    bl = zl.footprint_potentials(cov, dx, dx, "block")
    assert (bl[1] - bl[0]) == pytest.approx(ex[1] - ex[0], rel=0.01)
    assert (bl[0] - bl[2]) == pytest.approx(ex[0] - ex[2], rel=0.01)


def test_disc_footprint_closed_form():
    """!
    @brief The exact potentials of a fine disc give 1/4 for both terms (mean to boundary and mean to centre) within 3 %.
    @return None.
    """
    n, dx = 100, 0.1e-3
    yy, xx = np.mgrid[0:n, 0:n]
    cov = (np.hypot(xx - n / 2 + 0.5, yy - n / 2 + 0.5) * dx <= 3.5e-3).astype(float)
    pad = np.zeros((n + 20, n + 20))
    pad[10:-10, 10:-10] = cov
    ex = zl.footprint_potentials_exact(pad, dx, dx)
    # the boundary cells lie half a cell inside the disc, so the continuous 1/4 becomes 1/4 - dx / (2 a)
    assert (ex[1] - ex[0]) == pytest.approx(0.25 - dx / (2 * 3.5e-3), rel=0.01)
    assert (ex[0] - ex[2]) == pytest.approx(0.25, rel=0.03)


def test_zone_code_off_or_without_vias_is_the_program():
    """!
    @brief With `zones=False` on a board with vias, and with zones on a board without vias, the network equals the program's.
    @return None.
    """
    p, net, vias, cov = build(SMALL)
    ref = lumped._heater_network(net, cov, 0, 3.0, 10, vias)
    with zl.patched(zones=False):
        same_network(ref, zl.heater_network(net, cov, 0, 3.0, 10, vias))
    p0, net0, _, cov0 = build({**SMALL, "n": 0})
    ref0 = lumped._heater_network(net0, cov0, 0, 3.0, 10, None)
    with zl.patched():
        same_network(ref0, zl.heater_network(net0, cov0, 0, 3.0, 10, None))


def test_group_outside_the_footprint_is_the_program():
    """!
    @brief A group of vias entirely outside the footprint leaves the zones off and the network equal to the program's (the macro term stays in the rings).
    @return None.
    """
    spec = dict(layers=4, n=3, pitch=3.5, dia=0.3, fill=385.0, side=30.0, src=6.0, src_wh=(6.0, 6.0), offset=(9.0, 0.0))
    p, net, vias, cov = build(spec)
    ref = lumped._heater_network(net, cov, 0, 3.0, 10, vias)
    with zl.patched():
        net_z = zl.heater_network(net, cov, 0, 3.0, 10, vias)
    assert net_z["nz"] == 1
    same_network(ref, net_z)


def test_via_couplings_equal_the_programs_without_zone_nodes():
    """!
    @brief `via_couplings` with no zone node returns the couplings of `viaconstriction.ring_couplings` and a barrel-only part.
    @return None.
    """
    p, net, vias, cov = build(SMALL)
    # the node index of the program: footprint = 0, everything else 1 (two nodes are enough for the comparison)
    idx = np.where(cov > 0, 0, 1)
    cnt = np.bincount(idx.ravel(), minlength=2)
    L, nb = net.nl, net.n_board

    def ring_sum(a):
        return np.bincount(idx.ravel(), weights=a.ravel(), minlength=2)
    S = np.array([ring_sum(net.S[l]) / cnt for l in range(L)])
    g_top = np.array([ring_sum(net.g_top[l]) for l in range(L)])
    g_bot = np.array([ring_sum(net.g_bottom[l]) for l in range(L)])
    gz_diel = np.array([ring_sum(net.gz[l]) for l in range(nb - 1)])
    ref = viaconstriction.ring_couplings(vias, net, idx, 2, cnt, S, g_top, g_bot, gz_diel, nb)
    mine, via_gz, seen = zl.via_couplings(vias, net, idx, 2, cnt, S, g_top, g_bot, gz_diel, nb)
    assert set(ref) == set(mine)
    for key in ref:
        assert np.allclose(ref[key], mine[key], rtol=1e-12, atol=0.0)
    assert via_gz and seen
    for key, g in via_gz.items():
        assert np.all(g >= 0.0)


def test_zoned_network_invariants():
    """!
    @brief The zoned network of a 5 x 5 array under a 10 mm source: two footprint nodes, source and heat capacity conserved, energy balance, positive definite symmetric matrix, A hotter than the rings.
    @return None.
    """
    p, net, vias, cov = build(SMALL)
    ref = lumped._heater_network(net, cov, 0, 3.0, 10, vias)
    for macro in ("none", "cap"):
        with zl.patched(zone_macro=macro):
            z = zl.heater_network(net, cov, 0, 3.0, 10, vias)
        assert z["nz"] == 2 and z["R"] == ref["R"] + 1
        assert z["source"].sum() == pytest.approx(1.0)
        assert z["C"].sum() == pytest.approx(ref["C"].sum(), rel=1e-12)           # the same cells, the same heat capacity
        assert z["residual"] < 1e-9
        K = z["K"]
        assert np.allclose(K, K.T, rtol=1e-12, atol=1e-18)
        assert np.linalg.eigvalsh(K).min() > 0.0
        total_out = sum(z["out"].values())
        assert total_out == pytest.approx(3.0, rel=1e-6)
        assert z["theta"][0, 0] > z["theta"][0, 2]


def test_macro_term_in_the_zone_lowers_the_core_coupling():
    """!
    @brief Keeping the macro term in the zone nodes (`Z_cap`) can only lower the vertical coupling of the core between the first two planes.
    @return None.
    """
    p, net, vias, cov = build(SMALL)
    res = {}
    for macro in ("none", "cap"):
        with zl.patched(zone_macro=macro):
            z = zl.heater_network(net, cov, 0, 3.0, 10, vias)
        K, R = z["K"], z["R"]
        res[macro] = -K[0 * R + 1, 1 * R + 1]                                       # coupling C1-C2 (minus the off-diagonal element)
    assert res["cap"] <= res["none"] * (1.0 + 1e-12)


def test_dead_vias_leave_the_peak_near_the_program():
    """!
    @brief Vias that conduct nothing (plating 1e-12 m, open barrel) change the maximum by less than 6 % of the rise: the review's regression of the earlier folder, on the 2.4.5 well.
    @return None.
    """
    spec = {**SMALL, "fill": 0.0}
    p = zref.refs.make_problem(spec)
    p.board.via_plating = 1e-12
    q0 = zref.hz.no_vias(p)
    base = zref.pc.max_rise(q0, "lumped", 0.5)
    for name in ("Z_none", "Z_cap"):
        with zref.VARIANTS[name]():
            d = zref.pc.max_rise(p, "lumped", 0.5) - base
        assert abs(d) < 0.06 * base


def test_patched_restores_the_program():
    """!
    @brief The context manager puts the program's functions back, also after an exception.
    @return None.
    """
    net_fn, own_fn = lumped._heater_network, lumped._own_point
    with pytest.raises(RuntimeError):
        with zl.patched():
            assert lumped._heater_network is zl.heater_network
            raise RuntimeError("boom")
    assert lumped._heater_network is net_fn and lumped._own_point is own_fn
    assert zl.OPTIONS["zones"] is True


def test_tied_cell():
    """!
    @brief The tied cell equals the asked cell without vias and follows a tenth of the core with them, between 0.5 and the asked cell.
    @return None.
    """
    p = zref.refs.make_problem({**SMALL, "n": 0})
    assert zl.tied_cell_mm(p, 1.0) == 1.0
    p = zref.refs.make_problem(SMALL)                                               # core 6.5 mm across
    assert zl.tied_cell_mm(p, 1.0) == pytest.approx(0.65, rel=0.02)
    assert zl.tied_cell_mm(p, 0.5) == 0.5
    sparse = zref.refs.make_problem(dict(SMALL, n=3, pitch=3.0, src=12.0))          # core 10.2 mm across
    assert zl.tied_cell_mm(sparse, 1.0) == 1.0


def test_zone_warnings():
    """!
    @brief The warnings: none without a core, elongated footprint, core off the centre, core under ten cells across.
    @return None.
    """
    class N:
        dx = dy = 1e-3
    cov = np.zeros((40, 40))
    cov[10:30, 10:30] = 1.0
    assert zl.zone_warnings(N, cov, None) == []
    core = np.zeros((40, 40), bool)
    core[15:25, 15:25] = True
    assert zl.zone_warnings(N, cov, core) == []                                      # square, centred, ten cells across
    cov_long = np.zeros((40, 40))
    cov_long[15:25, 5:35] = 1.0
    assert any("elongated" in t for t in zl.zone_warnings(N, cov_long, core))
    off = np.zeros((40, 40), bool)
    off[10:20, 10:20] = True
    assert any("off" in t for t in zl.zone_warnings(N, cov, off))
    small = np.zeros((40, 40), bool)
    small[18:24, 18:24] = True
    assert any("coarser" in t for t in zl.zone_warnings(N, cov, small))


def test_step_response_ends_at_the_steady_value():
    """!
    @brief The zoned step response ends within 3 % of its steady value and starts below it, in both zone variants; the program's response is not touched by the patch.
    @return None.
    """
    p = zref.refs.make_problem(dict(SMALL, side=20.0))
    t0, z0, r0 = lumped.step_responses(p, cell_mm=1.0)
    for name in ("Z_none", "Z_cap"):
        with zref.VARIANTS[name]():
            t, z, r = zl.step_responses_zoned(p, cell_mm=1.0)
        assert z[0, -1] == pytest.approx(r[0], rel=0.03)
        assert z[0, 0] < r[0]
        assert np.all(np.diff(z[0]) > -1e-9)
    t1, z1, r1 = lumped.step_responses(p, cell_mm=1.0)
    assert np.allclose(z0, z1) and np.allclose(r0, r1)


def test_profile_runner_with_zones_ends_on_the_average_and_follows_the_wave():
    """!
    @brief The square-wave profile with the zones: the periodic mean equals the steady maximum of the average power (the start state), the peak exceeds it, and the run with the program's unpatched adapter does not (the source on A alone).
    @return None (asserts).
    """
    from pcbthermal import profiles
    from pcbthermal.model import SquareWave
    zref.pc.load_libraries()
    p = zref.refs.make_problem(dict(SMALL, src=10.0))
    h = p.heaters[0]
    h.profile = SquareWave(p_on=h.power / 0.5, period=1.0, duty=0.5, p_off=0.0)
    opt = profiles.ProfileOptions(threshold_c=0.0, duration="stable", stable_c=0.05, theta=0.5)
    resp = profiles.StepResponse("lumped", *lumped.step_responses(p, 10, 0.5))
    dec = profiles.decide(p, resp, 0.0)
    with zref.VARIANTS["Z_none"]():
        res = lumped.run_profile(p, dec, opt, 10, 0.5)
        assert zl.LAST["nz"] == 2
    amb = p.board.ambient
    # the mean of the periodic state is the steady value of the average power to within the cycle ripple of the peak formula
    assert res.t_max.mean() - amb == pytest.approx(res.steady_average_max - amb, rel=0.05)
    assert res.t_max.max() > res.steady_average_max
    assert res.t_max.min() < res.steady_average_max
    # the unpatched adapter puts all the power on A: hotter than the patched run
    with zref.VARIANTS["Z_none"]():
        saved = lumped._LumpedAdapter.advance
        lumped._LumpedAdapter.advance = zl.advance_245         # the program's adapter splits the source itself since the adoption: the 2.4.5 step is the control
        try:
            bad = lumped.run_profile(p, dec, opt, 10, 0.5)
        finally:
            lumped._LumpedAdapter.advance = saved
    assert bad.t_max.max() > res.t_max.max() + 1.0
    # the patch is removed on exit
    assert lumped._LumpedAdapter.advance is not zl._advance_zoned


def test_shen_equations_and_the_unit_cell_solver():
    """!
    @brief The paper's equations at the Fig. 17 geometry, the one-dimensional no-via resistance, and the axisymmetric solver against a closed form (a solid column of copper: R = t / (k A) for a uniform flux).
    @return None (asserts).
    """
    import shen_case as sc
    assert sc.shen_array_resistance() == pytest.approx(1.587, abs=0.002)
    assert sc.shen_no_via_resistance() == pytest.approx(145.17, abs=0.05)
    # a column of one material (copper everywhere, no hole): the solver must give t / (k pitch^2) for the stack of copper layers and the gaps all at k = 393
    saved = (sc.K_FR4_THROUGH, sc.K_FR4_INPLANE)
    r = sc.unit_cell(phi=2.0e-6 + 2 * sc.T_PTH, k_fill=sc.K_CU, k_fr4_z=sc.K_CU, k_fr4_r=sc.K_CU, nr_out=12, nr_barrel=2, nr_hole=2)
    assert (sc.K_FR4_THROUGH, sc.K_FR4_INPLANE) == saved
    # the heat loads the area outside the hole only (a hole of 1 um radius) and the cell area is pitch^2: R = t / (k A_cell) with the disc of the same area
    assert r == pytest.approx(sc.T_BOARD / (sc.K_CU * (sc.PHI + sc.SPACING) ** 2), rel=0.01)
    # the program's own board is within 3 % of the solver on the full 12 x 12 array (FVM at 0.1 mm, a few tenths of a second)
    from pcbthermal import SolverOptions, simulate
    zref.pc.load_libraries()
    prob = sc.program_problem()
    t = simulate(prob, SolverOptions(models=("fvm",), cell_mm=0.1)).results["fvm"].t_max - prob.board.ambient
    ref = sc.unit_cell(**dict(nr_out=96, nz_gap=28, nz_cu=8, nr_barrel=10, nr_hole=10)) / 144
    # 2.6.0 (fix/via-barrel-and-rim-uncoupling) lengthens the barrel by half the copper thickness: 1.4728 K -> 1.5777 K here, so the program reads +8.0 % above this resolved
    # axisymmetric reference (it was +0.8 %). The shift is explained by that item and measured here, not hidden: the item rests on research/via-contact-geometry
    # (a 3D cell with the barrel through the copper), which this case does not reproduce; reported to the maintainer as a flagged difference.
    assert t == pytest.approx(ref, rel=0.09)
    from pcbthermal import viawell
    saved_fraction = viawell.BARREL_COPPER_FRACTION
    viawell.BARREL_COPPER_FRACTION = 0.0                                       # the 2.5.x barrel (gap alone): the agreement the study was written with
    try:
        t0 = simulate(prob, SolverOptions(models=("fvm",), cell_mm=0.1)).results["fvm"].t_max - prob.board.ambient
    finally:
        viawell.BARREL_COPPER_FRACTION = saved_fraction
    assert t0 == pytest.approx(ref, rel=0.03)
    assert t > t0                                                              # the longer barrel can only add resistance


def test_fallback_decision_does_not_jump_with_the_raster():
    """!
    @brief The inverted-T example board (nine vias scaled to 3.02 mm pitch under a 10 mm part, a core of 82 % of the footprint at 1.0 mm and 95 % at 0.5 mm on the Lumped grid): with the share rule "fine" the choice is the one-node network (the program's value) at every raster, with the grid rule it jumps by 2.9 K between 1.0 and 0.5 mm.
    @return None (asserts).
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(FOLDER)), "tests", "regression"))
    import regress_boards as rbd
    zref.pc.load_libraries()
    p = rbd.build("example_cut_to_T")
    prog = {c: zref.pc.max_rise(p, "lumped", c) for c in (1.0, 0.75, 0.5)}
    with zl.patched(zone_macro="none", share_rule="fine"):
        fine = {c: zref.pc.max_rise(p, "lumped", c) for c in (1.0, 0.75, 0.5)}
    with zl.patched(zone_macro="none"):
        grid = {c: zref.pc.max_rise(p, "lumped", c) for c in (1.0, 0.75, 0.5)}
    for c in prog:
        assert fine[c] == pytest.approx(prog[c], abs=1e-4)
    assert abs(grid[1.0] - grid[0.5]) > 2.0                       # the jump of the grid rule


def test_fine_share_ignores_the_vias_outside_the_footprint_box():
    """!
    @brief The share counted on the fine grid equals the share of the core on a whole-board 0.1 mm grid for a 5 x 5 array that straddles the footprint edge (6 mm off the centre of a 12 mm part); the first version moved the vias outside the box of the footprint onto its border cells (the grid index is clipped) and read 0.136 instead of 0.118 (review).
    @return None (asserts).
    """
    spec = dict(layers=4, n=5, pitch=1.2, dia=0.3, fill=385.0, side=30.0, src=12.0, src_wh=(12.0, 12.0), offset=(6.0, 0.0))
    p, net, vias, cov = build(spec, 0.5)
    share = zl.fine_core_share(net, cov, vias)
    _, net_f, vias_f, cov_f = build(spec, 0.1)
    core = zl.core_mask(net_f, cov_f, vias_f)
    ref = float((core * cov_f).sum() / cov_f.sum())
    assert share == pytest.approx(ref, abs=1e-9)
    assert share < 0.125
