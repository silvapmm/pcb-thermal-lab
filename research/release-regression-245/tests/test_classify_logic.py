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
    # the 3D solid with vias has a measured bound of 0.3 K (first run); 0.5 K is a rule that is covered but outside its range
    assert by[("plate_vias", "solid3d")]["t_max"] == "expected_out_of_range"


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


def test_a_shift_outside_its_bound_is_an_alarm():
    """!
    @brief Review: a covered shift outside its bound (size or direction) counts as an alarm, so `--strict` and the freeze refuse it.
    @return None.
    """
    assert "expected_out_of_range" in C.ALARMS
    a = rset("a", [rec("example_board", "fvm", 2.0, 85.34)])
    b = rset("b", [rec("example_board", "fvm", 2.0, 85.34 + 5.0)])               # +5 K: inside the general 45 % of the rise, far above the reviewed 0.8 K
    d = C.diff_sets(a, b, TABLE)
    assert [m["class"] for m in d["entries"][0]["metrics"] if m["name"] == "t_max"] == ["expected_out_of_range"]
    assert d["summary"]["alarms"] > 0


def test_each_bound_applies_only_to_its_unit():
    """!
    @brief Review: a bound in K is not compared with a field checksum or a count, `rel` bounds counts and `abs_w` the heat balance.
    @return None.
    """
    rule = {"id": "X", "direction": "any", "abs_k": [0, 1.0], "rel": [0, 0.5], "abs_w": [0, 1e-9]}
    assert C.in_range(rule, 5000.0, 1e6, 50.0, "field")                          # a checksum moves by thousands when a temperature moves by 1 K
    assert not C.in_range(rule, 2.0, 80.0, 50.0, "temperature")
    assert C.in_range(rule, 2.0, 8000, 50.0, "count")                             # 2 of 8000 is inside 0.5
    assert not C.in_range(rule, 5000, 8000, 50.0, "count")
    assert not C.in_range(rule, 0.5, 5.0, 50.0, "balance")                      # half a watt of power lost is never round-off
    assert C.in_range(rule, 1e-13, 5.0, 50.0, "balance")


def test_per_cell_limits_replace_the_general_bound():
    """!
    @brief Review: a limit for "board|model|cell" wins over "board|model", which wins over "board", which wins over the rule's own bound in K.
    @return None.
    """
    rule = {"id": "X", "direction": "down", "abs_k": [0, 30], "limits": {"b|fdm|1": {"abs_k": [0, 28]}, "b|fdm": {"abs_k": [0, 7]}, "b": {"abs_k": [0, 2]}}}
    assert C.in_range(rule, -21.8, 252.0, 227.0, "temperature", "b", "fdm", 1.0)
    assert not C.in_range(rule, -21.8, 252.0, 227.0, "temperature", "b", "fdm", 0.5)      # "b|fdm": 7 K
    assert not C.in_range(rule, -3.0, 232.0, 207.0, "temperature", "b", "fvm", 2.0)       # "b": 2 K
    assert C.in_range(rule, -3.0, 232.0, 207.0, "temperature", "c", "fvm", 2.0)           # no limit: the rule's 30 K
    assert not C.in_range(rule, +1.0, 232.0, 207.0, "temperature", "b", "fdm", 1.0)       # direction


def test_the_table_has_a_measured_limit_for_every_bounded_scope():
    """!
    @brief Review: every quantified or derived rule carries limits for each board, model and cell of its scope (written by study_tighten_table.py), and the FDM hot spot of
           the part across the outline is bounded per cell, not by the general 30 K.
    @return None.
    """
    for r in TABLE["rules"]:
        if r["status"] == "to be explained":
            continue
        assert r.get("limits"), r["id"]
        for b in r["boards"]:
            for m in r["models"]:
                for c in (2.0, 1.0, 0.5):
                    assert C.limit_key(b, m, c) in r["limits"], (r["id"], b, m, c)
    R1a = {r["id"]: r for r in TABLE["rules"]}["R1a"]
    assert R1a["limits"]["part_across_outline|fdm|1"]["abs_k"][1] < 30 and R1a["limits"]["part_across_outline|fdm|0.5"]["abs_k"][1] < 10
    for e in TABLE["transients"]["may_move"]:
        assert "rel_change" in e and e.get("limits"), e["id"]


def test_a_bounded_time_to_63_percent_is_expected_inside_and_an_alarm_outside():
    """!
    @brief Review: the times to 63 % of the may_move entries are bounded per board and model.
    @return None.
    """
    table = {"transients": {"must_not_move": [], "may_move": [{"id": "T", "boards": ["b"], "models": ["fvm"], "rel_change": [0, 0.01], "limits": {"b|fvm": [0, 0.05]}}]}}
    rows = [{"board": "b", "model": "fvm", "part": "U", "old": 10.0, "new": 10.4, "change": 0.04, "identical": False},
            {"board": "b", "model": "fvm", "part": "V", "old": 10.0, "new": 11.0, "change": 0.10, "identical": False}]
    out = C.classify_transients(rows, table)
    assert [r["class"] for r in out] == ["expected", "expected_out_of_range"]


def test_bit_tolerance_on_the_heat_balance_is_not_relative_to_round_off():
    """!
    @brief Review: with PCBT_FROZEN_BIT_TOL a balance error of 1e-14 W that becomes 1e-13 W after a library update is not a difference (it was: the tolerance was relative to
           the round-off itself).
    @return None.
    """
    a = rset("v2.4.4", [rec("plate_uniform", "fvm", 2.0, 80.0, balance_error=-4.4e-14)], "2.4.4")
    f = F.build(a, a, "2.4.5")
    run = [rec("plate_uniform", "fvm", 2.0, 80.0 + 3e-11, balance_error=-1.15e-13)]
    assert F.compare(f, run)                                                   # exact by default
    assert not F.compare(f, run, bit_tol_k=1e-9)
    assert F.compare(f, [rec("plate_uniform", "fvm", 2.0, 80.0, balance_error=1e-3)], bit_tol_k=1e-9)
