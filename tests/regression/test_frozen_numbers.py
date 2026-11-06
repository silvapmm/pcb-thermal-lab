#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_frozen_numbers.py
@brief Compares a live run of the five models on the 17 regression boards with the numbers frozen at the release (`data/v2.5.0.json`) under one tolerance policy.
@details The frozen file is made at a release by `research/release-regression-245/scripts/study_freeze_reference.py` (CLAUDE.md, "Branches and Versions") and copied to
         `tests/regression/data/v<version>.json`; the test reads the newest. Tolerance policy (the same for every record, `regress_frozen.py`): temperatures 1e-8 K, field
         checksums 1e-10 relative, heat balance 1e-9 W, unknown counts and skipped status exactly, time to 63 % 1e-6 relative. Defaults: the 2 mm cell, all boards and models, with
         the times to 63 % (about 30 s). Environment variables:

         * `PCBT_FROZEN_CELLS`: comma-separated cell sizes in mm ("2" by default; "2,1,0.5" in the release procedure, about 2 minutes);
         * `PCBT_FROZEN_BOARDS`, `PCBT_FROZEN_MODELS`: comma-separated names (default all in the file);
         * `PCBT_FROZEN_TRANSIENTS`: "0" to leave out the times to 63 % (default "1");
         * `PCBT_FROZEN_EXACT`: "1" to demand equality of every float (only on the machine and libraries that froze the file);
         * `PCBT_FROZEN_FILE`: another frozen file.
@note A failure is not automatically a defect: when a number moved for a reason that was decided (a model change), record the moved records as a pending shift in the same
      commit (`make_pending.py`, `data/pending/<topic>.json`: the item, the branch, why, the new numbers) and say why; the frozen file of the release is not edited, and the
      pending files are folded into the refreeze of the next release (research/release-regression-245/INTEGRATION.md section 2) and deleted. If nobody decided the
      change, it is a regression.
"""

import copy
import json
import os
import re
from pathlib import Path

import pytest

import regress_frozen as F

HERE = Path(__file__).resolve().parent


def _newest_file():
    """!
    @brief The frozen file to read: `PCBT_FROZEN_FILE`, else the newest `data/v<version>.json`.
    @return Path (it may not exist).
    """
    if os.environ.get("PCBT_FROZEN_FILE"):
        return Path(os.environ["PCBT_FROZEN_FILE"])
    files = sorted((HERE / "data").glob("v*.json"), key=lambda p: tuple(int(x) for x in re.findall(r"\d+", p.stem)))
    return files[-1] if files else HERE / "data" / "v0.0.0.json"


FROZEN_FILE = _newest_file()
MISSING = not FROZEN_FILE.exists()
REASON = (f"frozen numbers {FROZEN_FILE.name} not found in tests/regression/data: make them at the release with "
          "research/release-regression-245/scripts/study_freeze_reference.py (see CLAUDE.md, 'Branches and Versions')")
EXACT = os.environ.get("PCBT_FROZEN_EXACT", "0") == "1"


def _csv(name, default):
    """!
    @brief A comma-separated environment variable as a list.
    @param name Variable name.
    @param default Value when it is not set (a string, "" for no filter).
    @return List of non-empty strings.
    """
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


def _cases():
    """!
    @brief The (board, model, cell) triples to run: the frozen records that pass the filters of the environment variables.
    @return List of tuples, sorted by board then cell (one board is built once per module).
    """
    if MISSING:
        return []
    data = F.load(FROZEN_FILE)
    cells, boards, models = [float(x) for x in _csv("PCBT_FROZEN_CELLS", "2")], _csv("PCBT_FROZEN_BOARDS", ""), _csv("PCBT_FROZEN_MODELS", "")
    out = []
    for k in data["records"]:
        b, m, c = k.split("|")
        if float(c) in cells and (not boards or b in boards) and (not models or m in models):
            out.append((b, m, float(c)))
    return sorted(out, key=lambda t: (t[0], t[2], t[1]))


def _transient_keys():
    """!
    @brief The "board|model" keys of the times to 63 % to run (none when the transients are switched off).
    @return Sorted list of keys.
    """
    if MISSING or os.environ.get("PCBT_FROZEN_TRANSIENTS", "1") != "1":
        return []
    boards, models = _csv("PCBT_FROZEN_BOARDS", ""), _csv("PCBT_FROZEN_MODELS", "")
    return sorted(k for k in F.load(FROZEN_FILE)["transients"]
                  if (not boards or k.split("|")[0] in boards) and (not models or k.split("|")[1] in models))


PENDING_DIR = HERE / "data" / "pending"


def _pending_files():
    """!
    @brief The pending shifts (`data/pending/*.json`, written by make_pending.py): new numbers of frozen records that a decided change moved before the next release.
    @return Sorted list of Path.
    """
    return sorted(PENDING_DIR.glob("*.json")) if PENDING_DIR.is_dir() else []


def with_pending(data):
    """!
    @brief The frozen numbers with the pending shifts of the same base version applied (each moved record and time to 63 % replaced by its new numbers).
    @details The frozen file of a release is never edited between releases: a model change on purpose records the records it moves in a pending file (the item, the branch,
             why), so the battery stays green and the moved records are still held to the same tolerance. A pending file of another base version is not applied
             (test_pending_shifts_belong_to_the_frozen_release fails on it: it must be folded into the refreeze of the release and deleted).
    @param data Content of the frozen file (F.load()).
    @return dict: a copy with the pending records in place, and "pending" listing the files applied.
    """
    out = copy.deepcopy(data)
    out["pending"] = []
    for path in _pending_files():
        pend = json.loads(path.read_text(encoding="utf-8"))
        if pend.get("base_version") != data["version"]:
            continue
        out["records"].update(pend.get("records", {}))
        for k, reason in pend.get("skipped", {}).items():       # A record the change pushed over the size cap of the harness: now skipped, no longer run
            out["records"].pop(k, None)
            out["skipped"][k] = reason
        out["transients"].update(pend.get("transients", {}))
        out["pending"].append(path.name)
    return out


@pytest.fixture(scope="module")
def frozen_data():
    """!
    @brief The frozen file with the pending shifts of its version applied (the module is skipped with a message when the file is absent).
    @return dict.
    """
    if MISSING:
        pytest.skip(REASON)
    return with_pending(F.load(FROZEN_FILE))


@pytest.fixture(scope="module")
def boards_cache():
    """!
    @brief Built boards by name (a board is built once and copied by the run).
    @return dict.
    """
    return {}


def _board(boards_cache, name):
    """!
    @brief A board of the suite, built once per module.
    @param boards_cache dict of the fixture.
    @param name Board name.
    @return A Problem.
    """
    import regress_boards as B
    if name not in boards_cache:
        boards_cache[name] = B.build(name)
    return boards_cache[name]


def test_pending_shifts_belong_to_the_frozen_release():
    """!
    @brief Every pending shift names the version of the newest frozen file, the change and its reason, and replaces only records and times that the frozen file holds.
    @details A pending file of an older version is left over after a release: its shifts are in the new frozen file, so it must be deleted (CLAUDE.md, "Frozen numbers").
    @return None.
    """
    if MISSING:
        pytest.skip(REASON)
    data = F.load(FROZEN_FILE)
    for path in _pending_files():
        pend = json.loads(path.read_text(encoding="utf-8"))
        assert pend.get("format") == F.FORMAT, f"{path.name}: format {pend.get('format')} is not {F.FORMAT}"
        assert pend.get("base_version") == data["version"], (f"{path.name} shifts the numbers of {pend.get('base_version')}, the newest frozen file is "
                                                             f"{data['version']}: fold it into the refreeze of the release and delete it")
        assert pend.get("item") and pend.get("branch") and pend.get("why"), f"{path.name}: the item, the branch and the reason are required"
        assert set(pend.get("records", {})) <= set(data["records"]), f"{path.name}: records that are not in {FROZEN_FILE.name}"
        assert set(pend.get("skipped", {})) <= set(data["records"]), f"{path.name}: skipped records that are not in {FROZEN_FILE.name}"
        assert set(pend.get("transients", {})) <= set(data["transients"]), f"{path.name}: times to 63 % that are not in {FROZEN_FILE.name}"


def test_the_frozen_file_is_present_and_complete():
    """!
    @brief The file exists (skipped with a message otherwise), names its version and holds the records of the default set.
    @return None.
    """
    if MISSING:
        pytest.skip(REASON)
    data = F.load(FROZEN_FILE)
    assert data["version"], "the frozen file does not name its version"
    assert data["records"], "the frozen file has no records"
    assert _cases(), "the filters of the environment variables select no record of the frozen file"


@pytest.mark.parametrize("board,model,cell", _cases() or [pytest.param("-", "-", 0.0, marks=pytest.mark.skip(reason=REASON))])
def test_run_agrees_with_the_frozen_numbers(board, model, cell, frozen_data, boards_cache):
    """!
    @brief One live run of a model on a board compared with its frozen record.
    @param board Board name.
    @param model Model key.
    @param cell Cell size in mm.
    @param frozen_data The frozen file.
    @param boards_cache Built boards.
    @return None.
    """
    import regress_harness as H
    s = frozen_data["settings"]
    rec = H.run_one(_board(boards_cache, board), board, model, cell, s["max_unknowns"], s["solid_cap"])
    diffs = F.compare(frozen_data, [rec], exact=EXACT)
    assert not diffs, "\n".join(diffs[:20])


@pytest.mark.parametrize("key", _transient_keys() or [pytest.param("-", marks=pytest.mark.skip(reason=REASON if MISSING else "times to 63 % switched off"))])
def test_time_to_63_percent_agrees_with_the_frozen_numbers(key, frozen_data, boards_cache):
    """!
    @brief The time to 63 % of the step response of a model on a board compared with the frozen one.
    @param key "board|model".
    @param frozen_data The frozen file.
    @param boards_cache Built boards.
    @return None.
    """
    import regress_harness as H
    board, model = key.split("|")
    t = H.t63(_board(boards_cache, board), model, frozen_data["settings"]["transient_cell"])
    t["board"] = board
    diffs = F.compare(frozen_data, [], [t], exact=EXACT)
    assert not diffs, "\n".join(diffs[:20])


def test_comparison_reports_a_perturbed_number(frozen_data, boards_cache):
    """!
    @brief The comparison can fail: one live run agrees with its frozen record, and a perturbed copy of that record is reported (the tolerance policy is checked at its edges).
    @param frozen_data The frozen file.
    @param boards_cache Built boards.
    @return None.
    """
    import regress_classify as C
    import regress_harness as H
    key = "plate_uniform|fvm|2"
    assert key in frozen_data["records"], "the cheapest record of the suite is missing from the frozen file"
    s = frozen_data["settings"]
    rec = H.run_one(_board(boards_cache, "plate_uniform"), "plate_uniform", "fvm", 2.0, s["max_unknowns"], s["solid_cap"])
    assert F.compare(frozen_data, [rec]) == [], "the live run must agree with the frozen record"

    metrics = frozen_data["records"][key]["metrics"]
    temp = next(n for n in sorted(metrics) if C.metric_group(n) == "temperature" and metrics[n] is not None)

    def perturbed(name, delta):
        # a deep copy, so the frozen data of the other tests is never changed
        f = copy.deepcopy(frozen_data)
        f["records"][key]["metrics"][name] = metrics[name] + delta
        return f

    assert not F.compare(perturbed(temp, 5e-9), [rec]), "5e-9 K is inside the tolerance"
    assert F.compare(perturbed(temp, 5e-8), [rec]), "5e-8 K must be reported"
    assert F.compare(perturbed(temp, 1e-3), [rec]), "1e-3 K must be reported"
    assert F.compare(perturbed(temp, 1e-12), [rec], exact=True), "exact mode must report 1e-12 K"
    # a count is exact, a field checksum is relative (1e-10), the heat balance is absolute (1e-9 W)
    assert F.compare(perturbed("unknowns", 1), [rec])
    assert not F.compare(perturbed("t_sum", metrics["t_sum"] * 1e-12), [rec])
    assert F.compare(perturbed("t_sum", metrics["t_sum"] * 1e-8), [rec])
    assert not F.compare(perturbed("balance_error", 1e-12), [rec])
    assert F.compare(perturbed("balance_error", 1e-6), [rec])
    # a record absent from the file and a run that no longer finishes are reported
    assert F.compare({**frozen_data, "records": {}}, [rec])
    assert F.compare(frozen_data, [dict(rec, status="error", reason="boom")])


def test_comparison_reports_a_perturbed_time_to_63_percent(frozen_data):
    """!
    @brief A time to 63 % that moves by more than 1e-6 relative is reported, one below it is not.
    @param frozen_data The frozen file.
    @return None.
    """
    key = sorted(frozen_data["transients"])[0]
    board, model = key.split("|")
    t63 = frozen_data["transients"][key]["t63"]
    name = sorted(t63)[0]

    def run(factor):
        # every part keeps its frozen time except the first one, which is scaled
        parts = [{"name": n, "t63_s": v * (factor if n == name else 1.0)} for n, v in sorted(t63.items())]
        return {"board": board, "model": model, "status": "ok", "parts": parts}

    assert F.compare(frozen_data, [], [run(1.0)]) == []
    assert F.compare(frozen_data, [], [run(1.0 + 1e-8)]) == []
    assert F.compare(frozen_data, [], [run(1.0 + 1e-4)])
    assert F.compare(frozen_data, [], [run(1.0)], exact=True) == []
    assert F.compare(frozen_data, [], [run(1.0 + 1e-12)], exact=True)
