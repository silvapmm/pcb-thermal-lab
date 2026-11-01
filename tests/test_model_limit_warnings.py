#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_model_limit_warnings.py
@brief Warnings about the documented limits of the models (Analytic copper spread, bare laminate, vias): they appear where the research measured the
       error, stay silent on the example boards, and never change a result.
"""

import glob
import os

import numpy as np

from pcbthermal import Problem, SolverOptions, project, simulate
from pcbthermal.checks import check_model_limits, check_via_limits

EXAMPLES = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "examples", "*.pcbt.json")))


def pad_board(pad_mm=10.0, dielectric_mm=0.1):
    """!
    @brief A 60 x 60 mm two-layer board of the given thickness: top copper only on a pad under the part, no copper on the bottom layer
           (the `gap0.1-empty` kind of row of research/gap-subdivision, where the program's own spread was silent: 0.004 against 0.28).
    @param pad_mm Side of the top copper pad in mm.
    @param dielectric_mm Total board thickness in mm (the gap between the two copper layers is of this order).
    @return Problem.
    """
    p = Problem.new(60, 60, 2, thickness_mm=dielectric_mm)
    p.add_zone(1, rect=(30 - pad_mm / 2, 30 - pad_mm / 2, 30 + pad_mm / 2, 30 + pad_mm / 2))
    p.add_heater(1, 1.0, rect=(27, 27, 33, 33), name="U")
    return p


def test_analytic_spread_warning_on_thin_gap_pad():
    """!
    @brief The new trigger fires on a pad over a thin gap with a bare second layer (the case the program's own spread missed).
    @return None.
    """
    res = simulate(pad_board(), SolverOptions(models=("analytic",), cell_mm=0.5)).results["analytic"]
    assert any("copper coverage varies around the heaters" in w for w in res.warnings)


def test_analytic_spread_silent_on_uniform_and_examples():
    """!
    @brief No spread warning on a uniform board or on the example boards.
    @return None.
    """
    p = Problem.new(40, 40, 2)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(15, 15, 25, 25))
    res = simulate(p, SolverOptions(models=("analytic",), cell_mm=1.0)).results["analytic"]
    assert not any("copper coverage varies" in w for w in res.warnings)
    for f in EXAMPLES:
        r = simulate(project.load_project(f).problem, SolverOptions(models=("analytic",), cell_mm=1.0)).results["analytic"]
        assert not any("copper coverage varies" in w for w in r.warnings), f


def window_board(window_mm, layers=2, part_mm=6.0):
    """!
    @brief The board of research/bare-spot-under-source: 30 mm, full copper on every layer except a centred square window in the top
           layer, a centred square part on top.
    @param window_mm Side of the window in mm (0: full copper).
    @param layers Copper layers.
    @param part_mm Side of the part in mm.
    @return Problem.
    """
    p = Problem.new(30, 30, layers)
    a, b = 15 - window_mm / 2, 15 + window_mm / 2
    for layer in range(1, layers + 1):
        if layer == 1 and window_mm > 0:
            # Four rectangles around the window, edges on the same lines
            for r in ((0, 0, 30, a), (0, b, 30, 30), (0, a, a, b), (b, a, 30, b)):
                p.add_zone(1, rect=r)
        else:
            p.add_zone(layer, rect=(0, 0, 30, 30))
    p.add_heater(1, 1.0, rect=(15 - part_mm / 2, 15 - part_mm / 2, 15 + part_mm / 2, 15 + part_mm / 2), name="U")
    return p


def test_bare_laminate_warning_on_the_windows_of_the_study():
    """!
    @brief Every window of the bare-spot study (2 to 20 mm under a 6 mm part, 2 and 4 layers, cells of 0.5 to 2 mm) warns the layered
           models and only them. Regression: a trigger on the mean fill of the footprint was silent on all of them (mean fill 0.89 and
           0.56 for the 2 and 4 mm windows, 0 for the others).
    @return None.
    """
    for layers in (2, 4):
        for window in (2, 4, 6, 8, 12, 20):
            for cell in (0.5, 1.0, 2.0):
                w = check_model_limits(window_board(window, layers), ("fvm", "solid3d"), cell)
                assert len(w) == 1 and "bare laminate" in w[0] and w[0].kind == "heater" and w[0].index == 0, (layers, window, cell)
                assert "(fvm)" in w[0]
    assert check_model_limits(window_board(6), ("solid3d",), 1.0) == []


def test_bare_laminate_warning_on_a_small_pad_off_the_centre():
    """!
    @brief A part whose centre is off its small pad (4 mm2 of copper in a corner of a 36 mm2 footprint) warns.
    @return None.
    """
    p = Problem.new(60, 60, 2)
    p.add_zone(1, rect=(28, 28, 30, 30))
    p.add_heater(1, 1.0, rect=(27, 27, 33, 33), name="U")
    assert any("bare laminate" in w for w in check_model_limits(p, ("fvm",), 1.0))


def test_bare_laminate_silent_on_copper_under_the_part():
    """!
    @brief Full copper, a pad that covers the part, a pad a little smaller than the part (the centre on copper) and a board with no
           copper at all (it has its own warnings) do not trigger it.
    @return None.
    """
    for cell in (0.5, 1.0, 2.0):
        assert check_model_limits(window_board(0, 2), ("fvm", "lumped"), cell) == []
        assert check_model_limits(window_board(0, 4), ("fvm", "lumped"), cell) == []
        assert check_model_limits(pad_board(10.0, 1.6), ("fvm", "lumped"), cell) == []
        assert check_model_limits(pad_board(5.0, 1.6), ("fvm", "lumped"), cell) == []
    none = Problem.new(60, 60, 2)
    none.add_heater(1, 1.0, rect=(27, 27, 33, 33))
    assert check_model_limits(none, ("fvm", "lumped"), 1.0) == []


def test_via_warnings():
    """!
    @brief Lumped: a part with vias under it warns once (tagged with the part); the vias outside every footprint give one warning together
           (tagged with the first), and a via off the board none; the FVM alone gives no via warning at any cell.
    @return None.
    """
    p = Problem.new(60, 60, 2)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(27, 27, 33, 33), name="U")
    p.add_via(29, 29)
    p.add_via(31, 31)
    p.add_via(10, 10)
    p.add_via(50, 10)
    w = check_model_limits(p, ("lumped",), 1.0)
    # The two far vias (nearest neighbour 40 mm) join the pair under the part into one group by the single linkage, but they lie far beyond the
    # reach of the pair, so the too-cool rule does not fire (the centred pair is the general text's case): two warnings
    assert len(w) == 2
    assert w[0].kind == "heater" and w[0].index == 0 and "2 vias under the footprint" in w[0]
    assert w[1].kind == "via" and w[1].index == 2 and "and 1 more vias" in w[1] and "outside the footprint" in w[1]
    assert "2.3 times the reference" in w[1] and "9 % of its rise" in w[1]          # The bound of an array beside a part (zones-adoption 8.4)
    for cell in (0.5, 1.0, 2.0, 4.0):
        assert check_model_limits(p, ("fvm", "fdm"), cell) == []
    q = Problem.new(60, 60, 2)
    q.add_full_copper()
    q.add_heater(1, 1.0, rect=(27, 27, 33, 33))
    q.add_via(30, 30)
    w = check_model_limits(q, ("lumped",), 1.0)
    assert len(w) == 1 and "1 via under the footprint" in w[0]


def test_via_warnings_silent_on_a_one_layer_board():
    """!
    @brief A one-layer board has no gap, so its vias change no model: the Lumped, Analytic, edge and coarse-cell via warnings stay silent there
           (they fired before, on a via near the edge and on vias outside every part, although the result does not depend on them).
    @return None.
    """
    p = Problem.new(30, 24, 1).add_zone(1, rect=(5, 5, 25, 19))
    p.add_heater(1, 1.0, rect=(12, 10, 18, 14), name="U")
    for x, y in ((8.0, 12.0), (15.0, 12.0), (29.9, 12.0)):          # beside the part, under it, at the edge of the board
        p.add_via(x, y, 0.4)
    models = ("fvm", "fdm", "lumped", "analytic", "solid3d")
    assert not [w for w in check_model_limits(p, models, 2.0) if "via" in w.lower()]
    assert check_via_limits(p, models, 2.0) == []
    # The same board on two layers does warn (the test is not vacuous)
    q = Problem.new(30, 24, 2).add_zone(1, rect=(5, 5, 25, 19))
    q.add_heater(1, 1.0, rect=(12, 10, 18, 14), name="U")
    for x, y in ((8.0, 12.0), (15.0, 12.0), (29.9, 12.0)):
        q.add_via(x, y, 0.4)
    assert [w for w in check_model_limits(q, models, 2.0) if "via" in w.lower()]
    assert check_via_limits(q, models, 2.0)


def test_warnings_do_not_change_results_and_reach_the_simulation(monkeypatch):
    """!
    @brief The warnings reach Simulation.problem_warnings, and the fields of every model are bit-identical with the check switched off.
    @param monkeypatch pytest fixture used to switch the check off.
    @return None.
    """
    from pcbthermal import checks
    p = window_board(6)
    p.add_via(15, 15)
    opts = SolverOptions(models=("fvm", "fdm", "lumped", "analytic"), cell_mm=1.0)
    sim = simulate(p, opts)
    assert any("bare laminate" in w for w in sim.problem_warnings)
    assert any("via under the footprint" in w for w in sim.problem_warnings)
    assert not any("bare laminate" in w for w in simulate(pad_board(10.0, 1.6), opts).problem_warnings)
    monkeypatch.setattr(checks, "check_model_limits", lambda *a, **k: [])
    quiet = simulate(p, opts)
    assert not any("bare laminate" in w for w in quiet.problem_warnings)
    for m in opts.models:
        assert np.array_equal(sim.results[m].T, quiet.results[m].T), m


def _via_part_board(x0, y0, x1, y1, vias, layers=2):
    """!
    @brief A 60 x 60 mm board with full copper, one part and the given vias.
    @param x0 Left edge of the part in mm.
    @param y0 Bottom edge of the part in mm.
    @param x1 Right edge of the part in mm.
    @param y1 Top edge of the part in mm.
    @param vias List of (x, y) positions in mm.
    @param layers Number of copper layers.
    @return Problem.
    """
    p = Problem.new(60, 60, layers)
    p.add_full_copper()
    p.add_heater(1, 2.0, rect=(x0, y0, x1, y1), name="U")
    for x, y in vias:
        p.add_via(x, y, 0.3)
    return p


def _grid(cx, cy, n, pitch):
    """!
    @brief An n x n array of via positions centred on a point.
    @param cx Centre x in mm.
    @param cy Centre y in mm.
    @param n Vias per side.
    @param pitch Pitch in mm.
    @return list of (x, y) in mm.
    """
    h = (n - 1) / 2
    return [(cx + (i - h) * pitch, cy + (j - h) * pitch) for i in range(n) for j in range(n)]


def _cool_warnings(p):
    """!
    @brief The warnings of the Lumped model that carry the too-cool rule of the one-node network (the zone model off: with it a part that will be split gets its text
           after the run, tests/test_lumped_zones.py).
    @param p Problem.
    @return list of str.
    """
    from pcbthermal import lumped
    lumped.ZONES = False
    try:
        return [str(w) for w in check_model_limits(p, ("lumped",), 1.0) if "too cool, unsafe" in str(w)]
    finally:
        lumped.ZONES = True


def test_lumped_cool_warning_fires_across_the_edge_and_off_centre():
    """!
    @brief An array across the edge of the footprint, an array off its centre and an elongated footprint get the too-cool warning with the kelvin and
           the percent of the rise; a centred square array, a board without vias and a one-layer board do not.
    @return None.
    """
    edge = _via_part_board(27, 27, 33, 33, _grid(33.5, 30, 5, 1.5))           # Group across the edge (columns at 30.5 to 36.5 mm; none on the edge)
    w = _cool_warnings(edge)
    assert len(w) == 1 and "about 11 K, a quarter of its rise" in w[0] and "3.2 times" in w[0] and "use the FVM" in w[0]
    off = _via_part_board(24, 26, 36, 34, _grid(31.5, 30, 5, 1.0))             # 5 x 5 array 1.5 mm off the centre of a 12 x 8 mm part
    assert len(_cool_warnings(off)) == 1 and "17.5 % of its rise" in _cool_warnings(off)[0]
    wider = _via_part_board(27, 27, 33, 33, _grid(30, 30, 7, 1.4))            # Centred, square, wider than the part (none on the edge): condition (i) alone
    assert len(_cool_warnings(wider)) == 1
    elongated = _via_part_board(22, 27, 38, 33, _grid(30, 30, 3, 1.0))        # Centred array, side ratio 2.7
    assert len(_cool_warnings(elongated)) == 1
    centred = _via_part_board(27, 27, 33, 33, _grid(30, 30, 3, 1.0))
    assert _cool_warnings(centred) == []
    assert any("under the footprint" in str(x) for x in check_model_limits(centred, ("lumped",), 1.0))   # The general text still applies
    assert _cool_warnings(_via_part_board(27, 27, 33, 33, [])) == []
    assert check_model_limits(_via_part_board(27, 27, 33, 33, _grid(33.5, 30, 5, 1.5), layers=1), ("lumped",), 1.0) == []
    assert not _cool_warnings_other(edge)                                     # The rule belongs to the Lumped model only


def _cool_warnings_other(p):
    """!
    @brief The too-cool rule text among the warnings of the models other than the Lumped (must be none).
    @param p Problem.
    @return list of str.
    """
    return [str(w) for w in check_model_limits(p, ("fvm", "fdm", "analytic"), 1.0) if "too cool, unsafe" in str(w)]


def test_lumped_cool_warning_ignores_scattered_vias_far_from_a_centred_array():
    """!
    @brief Vias scattered over the board chain a centred thermal array into one single-linkage group with them; the rule must not read that group as
           an array across the footprint edge. Before the review the rule fired on 4 of 4 centred arrays with 20 scattered vias 2 mm or more from every
           footprint (10 seeds); an array that really continues past the edge, and a scattered via next to an array via, still fire.
    @return None.
    """
    rng = np.random.default_rng(7)
    p = _via_part_board(26, 26, 34, 34, _grid(30, 30, 3, 2.0))               # Centred 3 x 3 array under an 8 mm part
    while len(p.vias) < 9 + 30:
        x, y = rng.uniform(2, 58, 2)
        if max(abs(x - 30), abs(y - 30)) > 6.0:                                # 2 mm or more outside the footprint
            p.add_via(float(x), float(y), 0.3)
    assert _cool_warnings(p) == []
    assert any("outside the footprint" in str(x) for x in check_model_limits(p, ("lumped",), 1.0))   # The aggregated outside text still applies
    p.add_via(35.0, 30.0, 0.3)                                                 # 1 mm outside the edge, one pitch from the array's outer via (32, 30)
    assert len(_cool_warnings(p)) == 1
    across = _via_part_board(26, 26, 34, 34, _grid(34, 30, 3, 2.0))           # The array itself across the edge, with the same scattered vias
    for v in p.vias[9:-1]:
        across.add_via(v.x * 1e3, v.y * 1e3, 0.3)
    assert len(_cool_warnings(across)) == 1


def test_lumped_cool_warning_is_cheap_with_two_thousand_vias():
    """!
    @brief The live check stays fast with 2000 vias under and around a part.
    @return None.
    """
    import time
    rng = np.random.default_rng(1)
    pts = [(float(a), float(b)) for a, b in rng.uniform(5, 55, (2000, 2))]
    p = _via_part_board(27, 27, 33, 33, pts)
    t0 = time.perf_counter()
    check_model_limits(p, ("lumped",), 1.0)
    assert time.perf_counter() - t0 < 0.3


def _outside_percent(problem, cell_mm):
    """!
    @brief Percentage written in the "outside the board" warning of check_problem for the first heater (0 when there is no such warning).
    @param problem The Problem.
    @param cell_mm Cell size in mm.
    @return int Percent of the footprint reported outside, 0 when silent.
    """
    import re
    from pcbthermal.checks import check_problem
    for w in check_problem(problem, cell_mm):
        m = re.search(r"(\d+) % of the footprint is outside the board", w)
        if m:
            return int(m.group(1))
    return 0


def test_small_part_inside_the_board_is_not_reported_outside():
    """!
    @brief A part under about two cells wide, wholly on the board, used to read 6 to 22 % outside (4 x 4 samples per cell); the share now comes from the
           geometry, for every size, offset and cell, with and without an outline.
    @return None.
    """
    from pcbthermal.geometry import part_board_share
    seen = 0
    for size in (1.0, 2.0, 3.0):
        for cell in (1.0, 1.7, 2.0, 2.5, 3.0, 4.0):
            for ox in np.linspace(5.0, 5.9, 7):
                p = Problem.new(30, 20, 2)
                p.add_zone(1, rect=(0, 0, 30, 20))
                p.add_heater(1, 1.0, rect=(ox, 7.7, ox + size, 7.7 + size))
                assert _outside_percent(p, cell) == 0, (size, cell, ox)
                seen += 1
    assert seen == 126
    # The share itself: exact for a rectangle on the box, 1 for a part wholly inside an outline
    sq = np.array([[1, 1], [3, 1], [3, 3], [1, 3]]) * 1e-3
    assert part_board_share(sq, 30e-3, 20e-3) == 1.0
    assert part_board_share(sq - 2e-3, 30e-3, 20e-3) == 0.25                    # A 2 mm square with its corner 1 mm beyond the corner of the board
    outline = np.array([[0, 0], [30, 0], [30, 20], [0, 20]]) * 1e-3
    assert part_board_share(sq, 30e-3, 20e-3, outline) == 1.0
    assert abs(part_board_share(sq - 2e-3, 30e-3, 20e-3, outline) - 0.25) < 0.01


def test_genuine_overlap_with_the_edge_still_warns():
    """!
    @brief A part half outside the board is reported as 50 % outside, also when it is smaller than a cell, and a part wholly beyond the edge as 100 %.
    @return None.
    """
    p = Problem.new(30, 20, 2)
    p.add_zone(1, rect=(0, 0, 30, 20))
    p.add_heater(1, 1.0, rect=(29.0, 5.0, 31.0, 7.0))
    assert _outside_percent(p, 3.0) == 50
    assert _outside_percent(p, 1.0) == 50
    q = Problem.new(30, 20, 2)
    q.add_zone(1, rect=(0, 0, 30, 20))
    q.add_heater(1, 1.0, rect=(31.0, 5.0, 33.0, 7.0))
    assert _outside_percent(q, 1.0) == 100


def test_live_input_check_is_what_a_run_reports():
    """!
    @brief checks.check_input (the live list of the application) holds the validity, model-limit and via warnings, and the run starts its warnings with the same
           texts, so the post-run list replaces the live one instead of adding to it.
    @return None.
    """
    from pcbthermal.checks import check_input
    p = window_board(6)                                          # Part on bare laminate: a model-limit warning
    p.add_via(15, 15)
    models = ("fvm", "lumped")
    live = [str(w) for w in check_input(p, models, 1.0)]
    assert any("sits on bare laminate" in w for w in live)
    assert any("under the footprint; the Lumped" in w for w in live)
    sim = simulate(p, SolverOptions(models=models, cell_mm=1.0))
    assert [str(w) for w in sim.problem_warnings[:len(live)]] == live
    # The warnings depend on the selected models: with the FVM alone the Lumped via text is gone
    assert not any("via under the footprint" in str(w) or "under the footprint; the Lumped" in str(w) for w in check_input(p, ("fvm",), 1.0))


def _many_via_board(n_scattered, outline=False):
    """!
    @brief A 200 x 150 mm four-layer board with 20 parts, a 5 x 5 array of 0.4 mm pitch under each part (a group the Lumped zone model splits) and scattered vias.
    @param n_scattered Number of scattered vias.
    @param outline True to cut the board to an ellipse (some vias and parts then lie off it).
    @return Problem.
    """
    rng = np.random.default_rng(3)
    p = Problem.new(200, 150, 4)
    for ly in (1, 2, 3, 4):
        p.add_zone(ly, rect=(0, 0, 200, 150))
    for k in range(20):
        x, y = rng.uniform(10, 180), rng.uniform(10, 130)
        p.add_heater(1, 1.0, rect=(x, y, x + rng.uniform(2, 12), y + rng.uniform(2, 12)), name=f"U{k}")
        for i in range(5):
            for j in range(5):
                p.add_via(x + 0.5 + i * 0.4, y + 0.5 + j * 0.4, 0.3)
    for x, y in rng.uniform(1, 149, (n_scattered, 2)):
        p.add_via(float(x) * 200 / 150, float(y), 0.3)
    if outline:
        t = np.linspace(0, 2 * np.pi, 128, endpoint=False)
        p.board.outline = np.c_[100e-3 + 99e-3 * np.cos(t), 75e-3 + 74e-3 * np.sin(t)]
    return p


def test_live_check_reuses_the_zone_decision_inputs():
    """!
    @brief check_model_limits builds the board and the vias of lumped.will_be_zoned once (not per part) and must decide exactly as will_be_zoned does by itself,
           on a rectangle and on an outline (where the decision is taken on the equivalent rectangle).
    @return None.
    """
    from pcbthermal import lumped
    for outline in (False, True):
        p = _many_via_board(300, outline)
        texts = [str(w) for w in check_model_limits(p, ("lumped",), 1.0)]
        on_board = np.array(p.via_board_shares()) > 0
        vx, vy = np.array([v.x for v in p.vias]), np.array([v.y for v in p.vias])
        from pcbthermal.geometry import points_in_polygon
        zoned_seen = 0
        for h in p.heaters:
            if not (points_in_polygon(vx, vy, h.polygon) & on_board).any():
                continue
            zoned = lumped.will_be_zoned(p, h)
            zoned_seen += zoned
            split = any(t.startswith(f"{h.name}:") and "splits this footprint" in t for t in texts)
            assert split == zoned, (outline, h.name)
        assert zoned_seen > 0


def test_heater_distance_is_the_per_via_loop():
    """!
    @brief The vectorised distance of every via to the nearest footprint is bit-identical to the per-via loop it replaced (it feeds the Analytic tile plan).
    @return None.
    """
    from pcbthermal import viaconstriction
    p = _many_via_board(5000)
    t = np.linspace(0, 2 * np.pi, 90, endpoint=False)
    p.add_heater(1, 1.0, polygon=np.c_[60 + 8 * np.cos(t), 60 + 5 * np.sin(t)], name="disc")
    vs = viaconstriction.ViaSet(p)
    ref = np.full(len(vs), np.inf)
    for h in p.heaters:
        poly = np.asarray(h.polygon, dtype=float)
        inside = viaconstriction.points_in_polygon(vs.x, vs.y, poly)
        ref[inside] = 0.0
        a, c = poly, np.roll(poly, -1, axis=0)
        e = c - a
        len2 = np.maximum((e ** 2).sum(axis=1), 1e-300)
        for i in np.flatnonzero(~inside):
            tt = np.clip(((vs.x[i] - a[:, 0]) * e[:, 0] + (vs.y[i] - a[:, 1]) * e[:, 1]) / len2, 0.0, 1.0)
            ref[i] = min(ref[i], float(np.hypot(vs.x[i] - (a[:, 0] + tt * e[:, 0]), vs.y[i] - (a[:, 1] + tt * e[:, 1])).min()))
    assert np.array_equal(viaconstriction.heater_distance(p, vs), ref)


def test_live_input_check_is_cheap_on_a_large_board():
    """!
    @brief The live list runs in the window's thread after every edit: with 8500 vias, 20 parts and every model it took 1.8 s (2.7 s on an outline) because the
           Lumped zone decision rebuilt the vias for every part and the Analytic plan measured the distances via by via; now about 0.2 s (0.5 s).
    @return None.
    """
    import time
    from pcbthermal.checks import check_input
    models = ("fvm", "fdm", "lumped", "analytic", "solid3d")
    for outline, limit in ((False, 0.8), (True, 1.5)):
        p = _many_via_board(8000, outline)
        check_input(p, models, 1.0)                              # Warm the imports and caches
        t0 = time.perf_counter()
        check_input(p, models, 1.0)
        assert time.perf_counter() - t0 < limit, outline
