#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_lumped_near_edge.py
@brief The Lumped near-edge warning (checks.check_lumped_near_edge) and the finer Lumped raster for a heat source under two cells (lumped.small_part_cell, cell_for).
@details The rule is held to the cases of research/lumped-near-edge (tests/data/lumped_near_edge_cases.json: the 180 sweep cases and the 120 random boards, with the error of the
         Lumped against the FVM measured there): 57 of the 58 cases more than 8 % too cool are flagged on the sweep and 35 of 37 on the random boards, and the 17 frozen boards flag
         exactly three. The raster rule is held to the FVM at 0.0625 mm on the 24 mm board of the study, to the memory bound, and to bit-identical rasters for boards without small parts.
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, checks, lumped, simulate

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests" / "regression"))
import regress_boards as RB  # noqa: E402

BAD = -8.0                                                       # percent of the rise: more than 8 % too cool is a bad case
DATA = json.loads((Path(__file__).parent / "data" / "lumped_near_edge_cases.json").read_text())
NAMES = re.compile(r"research/|fix/|feature/")


def _board(w, h, side, pos, h_side=10.0, power=1.0):
    """!
    @brief The uniform two-layer board of the study with a square source on layer 1.
    @param w Width in mm.
    @param h Height in mm.
    @param side Side of the source in mm.
    @param pos Centre (x, y) of the source in mm.
    @param h_side Edge coefficient in W/m2K.
    @param power Power in W.
    @return Problem.
    """
    p = Problem.new(w, h, layers=2, thickness_mm=1.6, copper_um=35.0, h_top=10.0, h_bottom=15.0, h_side=h_side)
    p.add_full_copper(fill=1.0)
    s = side / 2
    p.add_heater(1, power, rect=(pos[0] - s, pos[1] - s, pos[0] + s, pos[1] + s), name="U")
    return p


def _sweep_problem(row):
    """!
    @brief The board of one sweep row.
    @param row [W, H, side, place, gap, edge film, error].
    @return Problem.
    """
    w, h, side, place, d, hs, _ = row
    return _board(w, h, side, (d + side / 2, h / 2 if place == "edge" else d + side / 2), hs)


def _near(p):
    """!
    @brief The near-edge warnings of a problem for the Lumped model.
    @param p Problem.
    @return List of warnings.
    """
    return checks.check_lumped_near_edge(p, ("lumped",))


def test_gap_of_a_rectangular_board_and_of_an_outline():
    """!
    @brief The gap is the exact distance to the box, or to the real outline (zero for a part that crosses it or lies outside).
    @return None.
    """
    p = _board(100, 80, 5, (12.5, 40.0))
    side, gap = checks.heater_side_gap(p, p.heaters[0].polygon)
    assert side == pytest.approx(5e-3) and gap == pytest.approx(10e-3)
    q = _board(60, 60, 4, (30, 30))
    q.set_outline([(0, 0), (60, 0), (60, 20), (40, 20), (40, 60), (20, 60), (20, 20), (0, 20)])       # a T with the stem 20 mm wide
    q.heaters[0].polygon = [(22e-3, 30e-3), (30e-3, 30e-3), (30e-3, 36e-3), (22e-3, 36e-3)]            # 2 mm from the left side of the stem
    assert checks.heater_side_gap(q, q.heaters[0].polygon)[1] == pytest.approx(2e-3)
    q.heaters[0].polygon = [(15e-3, 15e-3), (25e-3, 15e-3), (25e-3, 25e-3), (15e-3, 25e-3)]             # across the notch corner
    assert checks.heater_side_gap(q, q.heaters[0].polygon)[1] == 0.0
    q.heaters[0].polygon = [(1e-3, 40e-3), (5e-3, 40e-3), (5e-3, 45e-3), (1e-3, 45e-3)]                 # outside the outline
    assert checks.heater_side_gap(q, q.heaters[0].polygon)[1] == 0.0


def test_the_threshold_is_one_side_with_a_five_millimetre_floor():
    """!
    @brief max(side, 5 mm): a 2 mm part flags at 5 mm and not at 5.2 mm, a 10 mm part flags at 9.9 mm and not at 10.5 mm; a gap of exactly 5 mm typed in mm counts.
    @return None.
    """
    assert _near(_board(100, 80, 2, (6.0, 40.0)))                # gap 5.0 mm (0.005000000000000001 m in floating point)
    assert not _near(_board(100, 80, 2, (6.2, 40.0)))
    assert _near(_board(100, 80, 10, (14.9, 40.0)))
    assert not _near(_board(100, 80, 10, (15.5, 40.0)))


def test_only_the_lumped_and_only_powered_parts():
    """!
    @brief The warning belongs to the Lumped model alone, and a part with no power is not flagged.
    @return None.
    """
    p = _board(100, 80, 5, (4.0, 40.0))
    assert checks.check_lumped_near_edge(p, ("fvm", "fdm", "analytic", "solid3d")) == []
    assert len(checks.check_input(p, ("lumped",), 0.5)) >= 1 and any("side of the board" in str(w) for w in checks.check_input(p, ("lumped",), 0.5))
    assert not any("side of the board" in str(w) for w in checks.check_input(p, ("fvm",), 0.5))
    assert _near(_board(100, 80, 5, (4.0, 40.0), power=0.0)) == []


def test_text_is_plain_tagged_and_aggregated():
    """!
    @brief One line for any number of parts, no internal names, a short form for the live list, tagged with the nearest part, the sample numbers in the full text.
    @return None.
    """
    p = _board(100, 80, 5, (4.0, 40.0))
    p.add_heater(1, 1.0, rect=(10, 10, 14, 14), name="Q1")
    p.add_heater(1, 1.0, rect=(50, 30, 54, 34), name="Q2")       # far from every side: not flagged
    (w,) = _near(p)
    assert w.kind == "heater" and w.index == 0
    text, short = str(w), checks.line(w)
    assert "U: the part is 1.5 mm from a side of the board" in text
    assert "8 to 9.5 %" in text and "22 %" in text and "sample, not a bound" in text and "FVM or the FDM" in text
    assert not NAMES.search(text) and not NAMES.search(short) and len(short) < len(text)
    p.heaters[1].polygon = [(5e-3, 5e-3), (9e-3, 5e-3), (9e-3, 9e-3), (5e-3, 9e-3)]                 # a second flagged part
    (w2,) = _near(p)
    assert str(w2).startswith("2 parts (") and "U, Q1" in str(w2)


def test_outline_gaps_with_a_reach_match_the_exact_gaps_and_stay_fast():
    """!
    @brief The live check measures only the outline segments within reach of each part: on random star outlines with turned parts inside, across and outside, the parts it
           flags are those of the exact gap, and 500 parts on an outline of 8000 points take well under a second (a call of the inside test per part took 25 s).
    @return None.
    """
    import time
    rng = np.random.default_rng(7)
    for _ in range(40):
        p = Problem.new(200, 150, layers=2, thickness_mm=1.6, copper_um=35.0, h_top=10.0, h_bottom=15.0, h_side=10.0)
        n = int(rng.integers(3, 40))
        th = np.sort(rng.uniform(0, 2 * np.pi, n))
        rr = rng.uniform(40, 74, n)
        p.set_outline(list(zip(100 + rr * np.cos(th), 75 + rr * np.sin(th))))
        polys = []
        for _ in range(20):
            x, y, s, a = rng.uniform(0, 200), rng.uniform(0, 150), rng.uniform(0.3, 12), rng.uniform(0, np.pi)
            c, d, hh = np.cos(a), np.sin(a), rng.uniform(0.2, 1.0) * s / 2
            polys.append([((x + c * u - d * v) * 1e-3, (y + d * u + c * v) * 1e-3) for u, v in ((-s / 2, -hh), (s / 2, -hh), (s / 2, hh), (-s / 2, hh))])
        lims = [max(np.sqrt(checks.polygon_area(q)), 5e-3) + 1e-9 for q in polys]
        exact = checks.heater_side_gaps(p, polys)
        reach = checks.heater_side_gaps(p, polys, lims)
        assert [g <= m for (_, g), m in zip(exact, lims)] == [g <= m for (_, g), m in zip(reach, lims)]
        assert all(ge == gr for (_, ge), (_, gr), m in zip(exact, reach, lims) if ge <= m)
    p = Problem.new(200, 150, layers=4, thickness_mm=1.6, copper_um=35.0, h_top=10.0, h_bottom=15.0, h_side=10.0)
    th = np.linspace(0, 2 * np.pi, 8000, endpoint=False)
    p.set_outline(list(zip(100 + 99 * np.cos(th), 75 + 74 * np.sin(th))))
    for i in range(500):
        x, y = 100 + rng.uniform(-60, 60), 75 + rng.uniform(-45, 45)
        p.add_heater(1, 0.1, rect=(x - 1, y - 1, x + 1, y + 1), name=f"U{i}")
    t0 = time.perf_counter()
    checks.check_lumped_near_edge(p, ("lumped",))
    assert time.perf_counter() - t0 < 2.0


def test_the_rule_reproduces_the_study_rates():
    """!
    @brief Hits on the sweep (57 of 58 bad cases; 63 false alarms) and on the 120 random boards (35 of 37; 24 false alarms) with the rule as the program applies it.
    @return None.
    """
    sweep = [(bool(_near(_sweep_problem(r))), r[6] < BAD) for r in DATA["sweep"]]
    assert sum(b for _, b in sweep) == 58
    assert sum(f and b for f, b in sweep) == 57
    assert sum(f and not b for f, b in sweep) == 63
    rnd = [((g <= max(s, checks.NEAR_EDGE_FLOOR_MM) + 1e-6), e < BAD) for s, g, e in DATA["random"]]
    assert sum(b for _, b in rnd) == 37
    assert sum(f and b for f, b in rnd) == 35
    assert sum(f and not b for f, b in rnd) == 24
    # The means quoted in the text: the flagged cases (8.2 % on the sweep, 8.3 % on the random boards), the worst at a corner
    err = np.array([r[6] for r in DATA["sweep"]])
    assert err.min() < -22.0 + 0.1 and DATA["sweep"][int(err.argmin())][3] == "corner"
    assert np.mean([r[6] for (f, _), r in zip(sweep, DATA["sweep"]) if f]) == pytest.approx(-8.2, abs=0.05)
    assert np.mean([e for (f, _), (_, _, e) in zip(rnd, DATA["random"]) if f]) == pytest.approx(-8.3, abs=0.05)


def test_the_rule_on_develop_without_the_capped_first_ring():
    """!
    @brief The same cases re-run on develop at 2.5.2 (no capped first ring; DATA sweep_develop, random_develop): the flagged parts read -9.4 % and -8.5 % on average (the text
           quotes 8 to 9.5 %), the rule catches 68 of the 86 sweep cases beyond -8 % and 34 of 38 random ones; of the 18 sweep cases it misses, 16 are a 2 mm part on the
           100 x 80 mm board 10 to 30 mm from a side and 2 a 5 mm part 10 mm from a corner (the small-part deficit of the rings, which the capped first ring removes), not the side.
    @return None.
    """
    fl = [bool(_near(_sweep_problem(r))) for r in DATA["sweep"]]
    e = np.array(DATA["sweep_develop"])
    bad = e < BAD
    assert int(bad.sum()) == 86 and int((bad & np.array(fl)).sum()) == 68
    assert np.mean(e[np.array(fl)]) == pytest.approx(-9.4, abs=0.05) and e.min() == pytest.approx(-22.0, abs=0.1)
    missed = [r for r, f, b in zip(DATA["sweep"], fl, bad) if b and not f]
    assert all(r[0] == 100.0 and r[4] >= 10.0 and (r[2] == 2.0 or (r[2] == 5.0 and r[3] == "corner")) for r in missed)
    rf = np.array([g <= max(s, checks.NEAR_EDGE_FLOOR_MM) + 1e-6 for s, g, _ in DATA["random"]])
    er = np.array(DATA["random_develop"])
    assert int((er < BAD).sum()) == 38 and int(((er < BAD) & rf).sum()) == 34
    assert np.mean(er[rf]) == pytest.approx(-8.5, abs=0.05)


def test_the_frozen_boards_flag_exactly_three():
    """!
    @brief On the 17 boards of the regression harness the rule flags t_outline, part_across_outline and example_cut_to_T and no other board.
    @return None.
    """
    got = sorted(n for n in RB.board_names() if _near(RB.build(n, REPO / "examples")))
    assert got == ["example_cut_to_T", "part_across_outline", "t_outline"]


def test_a_run_shows_the_near_edge_line_and_the_rectangle_line_once_each():
    """!
    @brief On an outline board the run's note about the equivalent rectangle and the near-edge line are two different lines, each once.
    @return None.
    """
    p = RB.build("t_outline", REPO / "examples")
    warns = [str(w) for w in simulate(p, SolverOptions(models=("lumped",), cell_mm=1.0)).warnings]
    assert sum("side of the board" in w for w in warns) == 1
    assert sum("rectangle of the same area" in w for w in warns) == 1


# --- the raster rule -------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("side, expected", [(0.2, 0.125), (0.3, 0.15), (0.5, 0.25), (0.75, 0.375)])
def test_a_source_under_two_cells_halves_its_raster(side, expected):
    """!
    @brief The raster is half the side of the smallest powered source, not below 0.125 mm.
    @param side Side of the source in mm.
    @param expected Raster in mm.
    @return None.
    """
    p = _board(24, 24, side, (12, 12))
    assert lumped.cell_for(p, 0.5) == pytest.approx(expected)
    assert lumped.cell_for(p, 0.1) == pytest.approx(expected)    # the request is clipped to 0.5 first, as always


def test_boards_without_a_small_source_keep_the_raster():
    """!
    @brief A source of one side of two cells or more, no power, or a bigger part beside a small one at zero power: the raster is the clip of every release; the 17 boards keep theirs.
    @return None.
    """
    assert lumped.cell_for(_board(24, 24, 1.0, (12, 12)), 0.5) == 0.5
    assert lumped.cell_for(_board(24, 24, 5.0, (12, 12)), 2.0) == 1.0
    assert lumped.cell_for(_board(24, 24, 0.3, (12, 12), power=0.0), 0.5) == 0.5
    for n in RB.board_names():
        p = RB.build(n, REPO / "examples")
        q = p.equivalent_rectangle()[0] if p.board.has_outline() else p
        assert lumped.small_part_cell(q, 0.5) is None
        assert lumped.small_part_refused(q, 0.5) is False


def test_the_smallest_source_decides_and_one_raster_serves_the_board():
    """!
    @brief Two parts: the raster follows the smaller one.
    @return None.
    """
    p = _board(24, 24, 0.5, (6, 6))
    p.add_heater(1, 1.0, rect=(15, 15, 20, 20), name="big")
    assert lumped.cell_for(p, 0.5) == pytest.approx(0.25)


def test_the_refinement_is_refused_when_it_does_not_fit_and_the_check_says_so(monkeypatch):
    """!
    @brief A 300 x 200 mm board at 0.125 mm is about 6.5 GB: the raster stays 0.5 mm, the live check warns once; a memory-guard limit lower than 1 GB also refuses.
    @param monkeypatch pytest fixture.
    @return None.
    """
    big = _board(300, 200, 0.2, (150, 100))
    assert lumped.small_part_cell(big, 0.5) is None and lumped.small_part_refused(big, 0.5)
    assert lumped.cell_for(big, 0.5) == 0.5
    warns = checks.check_lumped_small_part(big, ("lumped",), 0.5)
    assert len(warns) == 1 and "does not fit in the memory bound" in str(warns[0]) and not NAMES.search(str(warns[0]))
    assert checks.check_lumped_small_part(big, ("fvm",), 0.5) == []
    ok = _board(24, 24, 0.2, (12, 12))
    assert checks.check_lumped_small_part(ok, ("lumped",), 0.5) == []
    monkeypatch.setattr(lumped.memory, "limit_bytes", lambda *a, **k: 0.3e9)    # a small machine: the 24 mm board needs 0.1 GB at 0.125 mm; a 100 x 80 board needs 0.9 GB
    assert lumped.small_part_cell(_board(24, 24, 0.2, (12, 12)), 0.5) == pytest.approx(0.125)
    assert lumped.small_part_cell(_board(100, 80, 0.2, (50, 40)), 0.5) is None


def test_a_zoned_board_keeps_its_raster_and_the_check_says_so():
    """!
    @brief A board with a zoned part keeps the 0.5 mm raster of the zone model, so a 0.3 mm source beside it is not refined: the live check says why; a 1.2 mm source is
           two cells of that raster or more and gets no line.
    @return None.
    """
    p = _board(40, 40, 6.0, (20, 20), power=2.0)
    for i in range(3):
        for j in range(3):
            p.add_via(18.8 + 1.2 * i, 18.8 + 1.2 * j, 0.3)
    p.add_heater(1, 0.1, rect=(30, 30, 30.3, 30.3), name="R1")
    assert lumped.cell_for(p, 1.0) == 0.5 and lumped.cell_for(p, 0.5) == 0.5
    for cell in (0.5, 1.0):
        (w,) = checks.check_lumped_small_part(p, ("lumped",), cell)
        assert "U has a dense group of vias" in str(w) and not NAMES.search(str(w))
    p.heaters[1].polygon = [(30e-3, 30e-3), (31.2e-3, 30e-3), (31.2e-3, 31.2e-3), (30e-3, 31.2e-3)]
    assert checks.check_lumped_small_part(p, ("lumped",), 1.0) == []


def _rise_errors(side, shift):
    """!
    @brief Error of the hottest rise of the Lumped, through the API (refined raster) and at the 0.5 mm raster of the earlier releases, against the FVM at 0.0625 mm.
    @param side Side of the source in mm.
    @param shift Shift of the centre from (12, 12) mm, in both directions, in mm.
    @return tuple (refined error, 0.5 mm error) as fractions of the rise.
    """
    p = _board(24, 24, side, (12.0 + shift, 12.0 + shift))
    ref = simulate(p, SolverOptions(models=("fvm",), cell_mm=0.0625)).results["fvm"].t_max - 25.0
    new = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"].t_max - 25.0
    old = lumped.solve_steady(p, rings=10, cell_mm=0.5).t_max - 25.0
    return new / ref - 1.0, old / ref - 1.0


@pytest.mark.parametrize("side, limit", [(0.2, 0.08), (0.5, 0.03), (1.0, 0.03)])
def test_the_finer_raster_follows_the_resolved_fvm(side, limit):
    """!
    @brief 24 x 24 mm board, 1 W, source centred on a cell corner and in a cell of the 0.5 mm raster: the refined Lumped is within the limit of the FVM at 0.0625 mm
           (measured on this program: 0.2 mm -6.0 and -6.7 %, 0.5 mm +0.1 and +0.7 %, 1.0 mm +1.6 and -0.3 %; the 0.2 mm level is the deficit of the rings of a tiny
           footprint, which the capped first ring of the next version removes, the position dependence is gone).
    @param side Side of the source in mm.
    @param limit Largest absolute error as a fraction of the rise.
    @return None.
    """
    for shift in (0.0, 0.25):
        assert abs(_rise_errors(side, shift)[0]) < limit


def test_the_position_in_the_cell_no_longer_moves_a_tiny_part():
    """!
    @brief A 0.2 mm source on a corner of the 0.5 mm raster and in the middle of a cell read 13.5 and 3.6 % too cool (a spread of 10 points); with the finer raster the two
           positions differ by less than 2 points.
    @return None.
    """
    (n0, o0), (n1, o1) = _rise_errors(0.2, 0.0), _rise_errors(0.2, 0.25)
    assert abs(o0 - o1) > 0.08
    assert abs(n0 - n1) < 0.02
