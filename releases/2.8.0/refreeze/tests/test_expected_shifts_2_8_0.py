#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_expected_shifts_2_8_0.py
@brief Tests of the record that the refreeze of 2.8.0 left: the frozen file, the item table and the diff report agree.
@details Before the refreeze these tests certified the preview table against the pending files. The pending files are folded into `tests/regression/data/v2.8.0.json` and deleted, so the tests now read what remains: the frozen file, the table `expected_shifts_2.8.0.json` and `DIFF_v2.7.1_vs_final.md`. Light, no solver. Run from the repository root:

         .venv/bin/python -m pytest -q releases/2.8.0/refreeze/tests
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FROZEN = ROOT / "tests" / "regression" / "data" / "v2.8.0.json"
REFERENCE = ROOT / "releases" / "regression-harness" / "reference"
DIFF = ROOT / "releases" / "2.8.0" / "refreeze" / "DIFF_v2.7.1_vs_final.md"


def _diff_text():
    """!
    @brief The text of the diff report of the refreeze.
    @return str.
    """
    return DIFF.read_text(encoding="utf-8")


def test_the_diff_report_has_no_alarm_and_every_shift_is_expected():
    """!
    @brief The report says 0 alarms, 3882 shifted numbers, all `expected`, none unexplained or must-not-move, 54 identical records.
    @return None
    """
    text = _diff_text()
    assert "alarms (unexplained, must-not-move or out of range): **0**" in text
    assert "Records identical in every number: 54" in text
    rows = dict(re.findall(r"^\| (\w+) \| (\d+) \|$", text, flags=re.M))
    assert rows["expected"] == "3882"
    for other in ("expected_out_of_range", "to_be_explained", "unexplained", "must_not_move"):
        assert rows[other] == "0", other
    assert "None." in text.split("### Alarms")[1].split("###")[0]


def test_the_frozen_file_is_the_reference_and_holds_the_new_records():
    """!
    @brief The frozen file equals the copy in the harness reference folder, says 0 alarms, has 332 records, 28 skipped and the 60 finite-element entries (20 boards x 3 cells; 38 with numbers, 22 skipped); the pending files are gone.
    @return None
    """
    assert FROZEN.read_bytes() == (REFERENCE / "v2.8.0.json").read_bytes()
    data = json.loads(FROZEN.read_text(encoding="utf-8"))
    assert data["version"] == "2.8.0" and data["alarms_when_frozen"] == 0 and data["to_be_explained_when_frozen"] == 0
    assert len(data["records"]) == 332 and len(data["skipped"]) == 28 and len(data["transients"]) == 70
    fem = [k for k in list(data["records"]) + list(data["skipped"]) if "|fem|" in k]
    assert len(fem) == 60 and len({k.split("|")[0] for k in fem}) == 20       # 20 boards x 3 cells: 38 with numbers, 22 skipped (too many unknowns)
    assert not list((FROZEN.parent / "pending").glob("*.json"))


def test_the_table_has_no_open_rule_and_holds_the_3d_solid():
    """!
    @brief The item table has 13 rules, none without an item (no `??`), and the 3D solid is in the must-not-move list; no 3D solid record moved in the frozen file against its shifts.
    @return None
    """
    table = json.loads((REFERENCE / "expected_shifts_2.8.0.json").read_text(encoding="utf-8"))
    assert len(table["rules"]) == 13
    assert not [r for r in table["rules"] if "??" in r["item"]]
    assert "solid3d" in json.dumps(table["must_not_move"])
    assert not re.search(r"\| solid3d \|[^\n]*\| expected \|", _diff_text())
