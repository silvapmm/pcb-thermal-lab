#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_version_comparison.py
@brief Tests of the version-comparison generator on synthetic result sets (no program is imported).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import make_version_comparison as V                                         # noqa: E402

TABLE = {"baseline": "v1.0.0", "target": "1.1.0",
         "items": [{"id": "I1", "title": "Better cover"}],
         "rules": [{"id": "R1", "item": "I1", "boards": ["b1"], "models": ["fvm"], "cells": "*", "metrics": ["t_max"], "direction": "up", "rel_rise": [0, 0.5], "status": "quantified"}],
         "must_not_move": [], "transients": {}}


def rec(board, model, t_max, cell=2.0, status="ok", warnings=None):
    """!
    @brief A synthetic steady record.
    @param board Board name.
    @param model Model key.
    @param t_max Hottest temperature in degC.
    @param cell Cell size in mm.
    @param status Record status.
    @param warnings List of warning texts.
    @return dict.
    """
    return {"board": board, "model": model, "cell_mm": cell, "solver": "direct", "status": status, "reason": "", "unknowns": 10, "ambient": 25.0, "t_max": t_max,
            "t_mean": t_max - 5.0, "t_min": 25.0, "power_in": 1.0, "balance_error": 0.0, "layer_mean": [t_max - 6.0], "warnings": warnings or [], "parts": None, "blocks": None,
            "t_sum": t_max * 10.0, "t_sumsq": t_max ** 2 * 10.0, "seconds": 0.1}


def rset(version, records, label=None):
    """!
    @brief A synthetic result set.
    @param version Program version text.
    @param records List of records.
    @param label Label (default "v" + version).
    @return dict.
    """
    return {"label": label or "v" + version, "program": {"version": version}, "environment": {"numpy": "x"}, "records": records, "sor": [], "transients": []}


def test_shift_pct_and_item():
    """!
    @brief The hottest-point row holds the shift in K, the percent of the old rise and the item title.
    @return None.
    """
    a = rset("1.0.0", [rec("b1", "fvm", 125.0), rec("b1", "fdm", 125.0)])
    b = rset("1.1.0", [rec("b1", "fvm", 135.0), rec("b1", "fdm", 125.0)])
    text, rows, _ = V.build(a, b, TABLE)
    assert len(rows) == 1
    r = rows[0]
    assert abs(r["shift_k"] - 10.0) < 1e-12 and abs(r["shift_pct"] - 10.0) < 1e-9          # rise 100 K, shift 10 K
    assert r["class"] == "expected" and "I1 Better cover" in r["items"]
    assert "| b1 | fvm | 2 | 125.0000 | 135.0000 | +10.0000 | +10.00 |" in text
    assert "b1: fdm (2 mm)" in text                                                          # the unchanged record is listed as bit-identical


def test_unexplained_is_not_invented():
    """!
    @brief A shift no rule covers is reported as unexplained, never given an item.
    @return None.
    """
    a = rset("1.0.0", [rec("b2", "fvm", 100.0)])
    b = rset("1.1.0", [rec("b2", "fvm", 101.0)])
    _, rows, _ = V.build(a, b, TABLE)
    assert rows[0]["class"] == "unexplained" and rows[0]["items"] == ""


def test_pair_without_table_quotes_changelog():
    """!
    @brief With no table nothing is classified and the CHANGELOG section is quoted.
    @return None.
    """
    a = rset("1.0.0", [rec("b1", "fvm", 100.0)])
    b = rset("1.1.0", [rec("b1", "fvm", 101.0)])
    log = "## [1.1.0] - x\n\n### Fixed\n- a thing\n\n## [1.0.0] - y\n"
    text, rows, _ = V.build(a, b, None, changelog=V.changelog_section(log, "1.1.0"))
    assert rows[0]["class"] == "not classified"
    assert "> - a thing" in text and "1.0.0] - y" not in text


def test_status_change_is_listed():
    """!
    @brief A record that could run in one version and not in the other is named, not skipped.
    @return None.
    """
    a = rset("1.0.0", [rec("b1", "fvm", 100.0, status="error")])
    b = rset("1.1.0", [rec("b1", "fvm", 101.0)])
    text, _, _ = V.build(a, b, TABLE)
    assert "b1 / fvm / 2 mm: error to ok" in text


def test_pair_table_only_for_its_pair_and_history(tmp_path):
    """!
    @brief The table is used for its own pair only; the history has a summary and one chapter per pair, newest first, and the figure is reused on a second run.
    @param tmp_path pytest temporary folder.
    @return None.
    """
    s0 = rset("1.0.0", [rec("b1", "fvm", 100.0)])
    s1 = rset("1.1.0", [rec("b1", "fvm", 110.0)])
    s2 = rset("1.2.0", [rec("b1", "fvm", 110.0)], label="develop")
    s2["tree_state"] = "unreleased"
    assert V.pair_table(TABLE, s0, s1) is TABLE and V.pair_table(TABLE, s1, s2) is None
    log = "## [Unreleased]\n- later\n\n## [1.1.0] - x\n- earlier\n"
    text = V.build_history([s0, s1, s2], TABLE, log, ["v0.9: cannot run"], 2.0, tmp_path, ["note line"], boards=("b1",))
    assert text.index("Results of develop against v1.1.0") < text.index("Results of v1.1.0 against v1.0.0")
    assert "| b1 | fvm | 100.000 | 110.000 | 110.000 |" in text and "v0.9: cannot run" in text and "note line" in text
    assert "> - later" in text
    files = sorted(p.name for p in tmp_path.glob("fig_*.png"))
    assert files == ["fig_04_version_hottest_canonical_boards.png", "fig_05_version_shift_v1.0.0_vs_v1.1.0.png"]
    V.build_history([s0, s1, s2], TABLE, log, [], 2.0, tmp_path, [])
    assert sorted(p.name for p in tmp_path.glob("fig_*.png")) == files                       # same name part: same number


def test_availability_and_missing_model(tmp_path):
    """!
    @brief The availability table counts statuses per version and names what did not run.
    @param tmp_path pytest temporary folder.
    @return None.
    """
    s0 = rset("1.0.0", [rec("b1", "fvm", 100.0), {**rec("b1", "fdm", 0.0), "status": "not_available", "reason": "model 'fdm' does not exist in this release", "t_max": None},
                        {**rec("b2", "fvm", 0.0), "status": "not_available", "reason": "AttributeError: no set_outline", "t_max": None}])
    s0["boards"] = {"b2": {"not_available": "AttributeError: no set_outline"}}
    s1 = rset("1.1.0", [rec("b1", "fvm", 101.0), rec("b1", "fdm", 90.0), rec("b2", "fvm", 80.0)])
    t = V.availability_table([s0, s1])
    assert "| v1.0.0 | 3 | 1 | 2 | 0 | 0 | 1 | fvm |" in t and "| v1.1.0 | 3 | 3 | 0 | 0 | 0 | 2 | fvm, fdm |" in t
    lines = "\n".join(V.unavailable_lines([s0, s1]))
    assert "board b2: AttributeError: no set_outline" in lines and "models without a run: fdm" in lines


def test_error_against_reference_and_notes():
    """!
    @brief The error against the reference is rise / reference - 1 per version, the mean absolute error needs every reference board, and pair notes appear in the chapter.
    @return None.
    """
    refs = {"b1": {"2": 100.0}, "b2": {"2": 50.0}}
    s0 = rset("1.0.0", [rec("b1", "fvm", 135.0), rec("b2", "fvm", 85.0)])         # rises 110 and 60: +10 % and +20 %
    s1 = rset("1.1.0", [rec("b1", "fvm", 125.0), rec("b2", "fvm", 75.0)])         # rises 100 and 50: 0 %
    rows = V.error_rows([s0, s1], refs)
    assert abs(rows[("b1", "fvm", 2.0)][0] - 0.10) < 1e-12 and abs(rows[("b2", "fvm", 2.0)][1]) < 1e-12
    assert abs(V.mean_abs_error(rows, 2, 2.0)["fvm"][0] - 15.0) < 1e-9 and V.mean_abs_error(rows, 2, 2.0)["fvm"][1] == 0.0
    assert V.mean_abs_error(rows, 2, 2.0)["fdm"] == [None, None]
    text, _, _ = V.build(s0, s1, None, pair_notes={"implemented": ["item A"], "reading": ["moved by item A"]})
    assert "* item A" in text and "* moved by item A" in text and "Hottest point moved, per model" in text
