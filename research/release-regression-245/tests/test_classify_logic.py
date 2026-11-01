#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_classify_logic.py
@brief Tests of the pure logic of the regression harness (no program is imported): the classification of shifts, the frozen-file build and compare, and the shipped table.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import regress_classify as C                                                # noqa: E402
import regress_frozen as F                                                  # noqa: E402

TABLE = json.loads((HERE.parent / "reference" / "expected_shifts.json").read_text(encoding="utf-8"))


def rec(board, model, cell, t_max, parts=None, unknowns=100, status="ok", **kw):
    """!
    @brief A synthetic run record.
    @param board Board name.
    @param model Model key.
    @param cell Cell size in mm.
    @param t_max Hottest temperature in degC.
    @param parts Optional list of part dicts.
    @param unknowns Unknown count.
    @param status Record status.
    @param kw Other fields.
    @return dict.
    """
    r = {"board": board, "model": model, "cell_mm": cell, "solver": "direct", "status": status, "reason": "", "unknowns": unknowns, "ambient": 25.0, "t_max": t_max,
         "t_mean": t_max - 10.0, "t_min": 25.0, "power_in": 5.0, "balance_error": 0.0, "layer_mean": [t_max - 12.0, t_max - 14.0], "warnings": [], "parts": parts,
         "blocks": None, "t_sum": t_max * 100.0, "t_sumsq": t_max ** 2 * 100.0, "seconds": 1.0}
    r.update(kw)
    return r


def rset(label, records, version="x"):
    """!
    @brief A synthetic result set.
    @param label Label.
    @param records List of records.
    @param version Program version string.
    @return dict.
    """
    return {"label": label, "program": {"version": version}, "records": records, "sor": [], "transients": [], "boards": {r["board"]: {} for r in records},
            "environment": {}, "settings": {"models": [], "cells": [], "max_unknowns": 1, "solid_cap": 1, "transient_cell": 1.0}}


def test_identical_sets_have_no_shift():
    a = rset("a", [rec("plate_uniform", "fvm", 1.0, 80.0)])
    d = C.diff_sets(a, a, TABLE)
    assert d["summary"]["identical_records"] == 1 and d["summary"]["alarms"] == 0 and not d["entries"]


def test_a_shift_on_a_board_that_must_not_move_is_an_alarm():
    a = rset("a", [rec("plate_uniform", "fvm", 1.0, 80.0)])
    b = rset("b", [rec("plate_uniform", "fvm", 1.0, 80.0 + 1e-9)])
    d = C.diff_sets(a, b, TABLE)
    assert d["summary"]["counts"]["must_not_move"] > 0 and d["summary"]["alarms"] > 0


def test_a_laminate_shift_inside_the_bound_is_expected_and_a_fall_is_out_of_range():
    a = rset("a", [rec("plate_pad", "fvm", 1.0, 100.0)])
    up = rset("b", [rec("plate_pad", "fvm", 1.0, 110.0)])                    # +10 K of a 75 K rise: 13 %, inside 45 %
    down = rset("c", [rec("plate_pad", "fvm", 1.0, 90.0)])
    cu = C.diff_sets(a, up, TABLE)["entries"][0]["metrics"]
    assert [m["class"] for m in cu if m["name"] == "t_max"] == ["expected"]
    cd = C.diff_sets(a, down, TABLE)["entries"][0]["metrics"]
    assert [m["class"] for m in cd if m["name"] == "t_max"] == ["expected_out_of_range"]


def test_a_shift_with_no_rule_is_unexplained_and_a_known_item_without_size_is_to_be_explained():
    a = rset("a", [rec("unknown_board", "lumped", 1.0, 100.0), rec("plate_vias", "solid3d", 1.0, 100.0)])
    b = rset("b", [rec("unknown_board", "lumped", 1.0, 100.0 + 1e-9), rec("plate_vias", "solid3d", 1.0, 100.5)])
    d = C.diff_sets(a, b, TABLE)
    by = {(e["board"], e["model"]): {m["name"]: m["class"] for m in e["metrics"]} for e in d["entries"]}
    assert by[("unknown_board", "lumped")]["t_max"] == "unexplained"
    assert by[("plate_vias", "solid3d")]["t_max"] == "to_be_explained"


def test_a_change_of_warnings_alone_is_not_a_shift():
    a = rset("a", [rec("plate_pad", "fvm", 1.0, 100.0, warnings=["x"])])
    b = rset("b", [rec("plate_pad", "fvm", 1.0, 100.0, warnings=["x", "y"])])
    d = C.diff_sets(a, b, TABLE)
    assert d["summary"]["counts"]["warnings_only"] == 1 and d["summary"]["alarms"] == 0
    assert d["entries"][0]["warnings_added"] == ["y"]


def test_every_rule_and_entry_of_the_table_is_well_formed():
    ids = [r["id"] for r in TABLE["rules"]] + [m["id"] for m in TABLE["must_not_move"]]
    assert len(ids) == len(set(ids))
    for r in TABLE["rules"]:
        assert r["status"] in ("quantified", "derived", "to be explained")
        assert r["item"] in {i["id"] for i in TABLE["items"]}
        if r["status"] == "quantified":
            assert "abs_k" in r or "rel_rise" in r or "rel" in r, r["id"]
    import regress_boards as B                                              # imports no program at module level
    known = set(B.board_names()) | {"*"}
    for scope in TABLE["rules"] + TABLE["must_not_move"]:
        b = scope["boards"]
        assert b == "*" or set(b) <= known, (scope["id"], set(b) - known)
    assert set(TABLE["board_matrix"]) <= known


def test_frozen_build_marks_unchanged_records_bit_and_compares_within_the_tolerance():
    a = rset("v2.4.4", [rec("plate_uniform", "fvm", 2.0, 80.0), rec("plate_pad", "fvm", 2.0, 100.0)], "2.4.4")
    b = rset("rc", [rec("plate_uniform", "fvm", 2.0, 80.0), rec("plate_pad", "fvm", 2.0, 110.0)], "2.4.5")
    f = F.build(a, b, "2.4.5")
    assert f["records"]["plate_uniform|fvm|2"]["class"] == "bit" and f["records"]["plate_pad|fvm|2"]["class"] == "moved"
    assert not F.compare(f, [rec("plate_uniform", "fvm", 2.0, 80.0), rec("plate_pad", "fvm", 2.0, 110.0 + 5e-7)])
    assert F.compare(f, [rec("plate_pad", "fvm", 2.0, 110.0 + 5e-6)])
    assert F.compare(f, [rec("plate_uniform", "fvm", 2.0, 80.0 + 1e-12)])               # a bit record is exact
    assert not F.compare(f, [rec("plate_uniform", "fvm", 2.0, 80.0 + 1e-12)], bit_tol_k=1e-9)
    assert F.compare(f, [rec("plate_pad", "fvm", 2.0, 110.0, unknowns=101)])           # the unknown count is exact


def test_first_run_corrections_of_the_table():
    """!
    @brief The table entries corrected by the first run of the harness classify the shifts that raised false alarms.
    @return None.
    """
    # the SOR of the plain plate moves inside its stopping tolerance (relaxation factor of 2.4.5), not an alarm
    cls, rules, _ = C.classify_shift(TABLE, "plate_uniform", "fvm_sor", 2.0, "t_max", 159.0524330838, 159.0524331286, 134.0)
    assert cls == "expected" and "R6a" in rules
    # the direct FVM on the same board must still not move at all
    cls, _, _ = C.classify_shift(TABLE, "plate_uniform", "fvm", 2.0, "t_max", 159.05, 159.06, 134.0)
    assert cls == "must_not_move"
    # the FDM hottest point under a part across the outline moves down with the part weights (item I1)
    cls, rules, _ = C.classify_shift(TABLE, "part_across_outline", "fdm", 2.0, "t_max", 246.76, 230.52, 221.0)
    assert cls == "expected" and "R1a" in rules
    # the Analytic mean under a part on an outline board moves a little (read-out on the real outline)
    cls, rules, _ = C.classify_shift(TABLE, "round_outline", "analytic", 2.0, "part:U:t_mean", 170.73, 170.01, 150.0)
    assert cls == "expected" and "R1e" in rules
    # but its hottest point on the same board does not move
    cls, _, _ = C.classify_shift(TABLE, "round_outline", "analytic", 2.0, "t_max", 175.0, 175.5, 150.0)
    assert cls == "must_not_move"
