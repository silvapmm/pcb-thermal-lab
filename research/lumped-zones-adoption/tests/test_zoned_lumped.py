#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_zoned_lumped.py
@brief Tests of the zoned Lumped proposal on the 2.4.5 program: the closed forms, the equality with the program when the zones are off, the invariants of the network and the helper rules.
@details WRITTEN BUT NOT YET RUN (the machine was busy when the work was prepared). Run: `.venv/bin/python -m pytest research/lumped-zones-adoption/tests -q` from the repository root.
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
    assert a["peak_extra"] == pytest.approx(b["peak_extra"], rel=1e-8, abs=1e-10)
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
    assert (ex[1] - ex[0]) == pytest.approx(0.25, rel=0.03)
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
