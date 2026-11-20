#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_frozen_numbers.py
@brief Compares a live run of the five models on the 17 regression boards with the numbers frozen at the release (`data/v2.6.0.json`) under one tolerance policy.
@details The frozen file is made at a release by `releases/regression-harness/scripts/study_freeze_reference.py` (CLAUDE.md, "Branches and Versions") and copied to
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
      pending files are folded into the refreeze of the next release (releases/regression-harness/INTEGRATION.md section 2) and deleted. If nobody decided the
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
          "releases/regression-harness/scripts/study_freeze_reference.py (see CLAUDE.md, 'Branches and Versions')")
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
    frozen = F.load(FROZEN_FILE)
    data = {"records": {**frozen["records"], **with_pending(frozen)["records"]}}   # the records that a pending file ADDS (a new model) are run too; a skipped one still runs
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
    return sorted(k for k in with_pending(F.load(FROZEN_FILE))["transients"]
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
    @return dict: a copy with the pending records in place, the records a pending file lists under "skipped" moved from "records" to "skipped" (pushed over the size cap of the
            harness by the change), and "pending" listing the files applied.
    """
    out = copy.deepcopy(data)
    out["pending"] = []
    loaded = [(path, json.loads(path.read_text(encoding="utf-8"))) for path in _pending_files()]
    # A file with "new_readouts" ADDS metrics (a read-out that no frozen record has, such as the surface) to records that exist: it is merged after the shifts, into the
    # record as the shifts left it, and changes no number that the frozen file or a shift holds: a metric the record already has keeps its value (a shift file made
    # with the newer harness may hold the same read-out, measured on the tree of its own change, and that number must win over the older addition)
    for path, pend in sorted(loaded, key=lambda x: bool(x[1].get("new_readouts"))):
        if pend.get("base_version") != data["version"]:
            continue
        if pend.get("new_readouts"):
            for k, rec in pend.get("records", {}).items():
                if k in out["records"]:
                    out["records"][k]["metrics"] = {**rec["metrics"], **out["records"][k]["metrics"]}
            out["pending"].append(path.name)
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


def test_no_record_or_time_is_in_two_pending_files():
    """!
    @brief A frozen record (or time to 63 %) that two decided changes move has ONE entry, in one pending file, regenerated with both changes in the tree.
    @details The files are applied in name order and the last wins, so a record in two files would silently hold the number of whichever sorts later, which neither change
             produced alone: the branch that moves a record already in a pending file regenerates it into its own file and removes it from the older one.
    @return None.
    """
    seen = {}
    for path in _pending_files():
        pend = json.loads(path.read_text(encoding="utf-8"))
        if pend.get("new_readouts"):                                  # it adds metrics to a record, it does not replace it
            continue
        for kind in ("records", "transients"):
            for key in pend.get(kind, {}):
                assert (kind, key) not in seen, f"{kind[:-1]} {key} is in both {seen[(kind, key)]} and {path.name}"
                seen[(kind, key)] = path.name


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
        # A pending file may ADD the records of a model that the frozen file does not hold ("new_models": a comparison model added by a feature): they are new keys of
        # that model only; every other record must be one the frozen file holds
        if pend.get("new_readouts"):
            # Only additions: every record exists (frozen, or added by a new model), and no metric of it is a number the frozen file already holds
            assert not pend.get("transients") and not pend.get("skipped"), f"{path.name}: a new read-out file holds records only"
            for k, rec in pend.get("records", {}).items():
                assert k in data["records"], f"{path.name}: {k} is not in {FROZEN_FILE.name}"
                clash = set(rec["metrics"]) & set(data["records"][k]["metrics"])
                assert not clash, f"{path.name}: {k} already holds {sorted(clash)[:3]}: a read-out file only adds"
            continue
        new = set(pend.get("new_models", []))
        added = {k for k in pend.get("records", {}) if k.split("|")[1] in new}
        assert not added & set(data["records"]), f"{path.name}: added records that {FROZEN_FILE.name} already holds"
        assert set(pend.get("records", {})) - added <= set(data["records"]), f"{path.name}: records that are not in {FROZEN_FILE.name}"
        assert set(pend.get("skipped", {})) <= set(data["records"]), f"{path.name}: skipped records that are not in {FROZEN_FILE.name}"
        assert not set(pend.get("skipped", {})) & set(pend.get("records", {})), f"{path.name}: a record cannot be both moved and skipped"
        problem = pending_time_problem(pend, data)
        assert problem is None, f"{path.name}: {problem}"


def pending_time_problem(pend, data):
    """!
    @brief The first thing wrong with the times to 63 % of a pending file, or None: a time record must be one the frozen file holds (a shift) or an ADDITION of a model listed in
           the file's `new_models` (a new comparison model's time) that the frozen file does not hold.
    @param pend Content of the pending file.
    @param data Content of the frozen file.
    @return str or None.
    """
    new = set(pend.get("new_models", []))
    times = set(pend.get("transients", {}))
    added = {k for k in times if k.split("|")[1] in new}
    if added & set(data["transients"]):
        return f"added times to 63 % that {FROZEN_FILE.name} already holds: {sorted(added & set(data['transients']))[:3]}"
    extra = times - added - set(data["transients"])
    if extra:
        return f"times to 63 % that are not in {FROZEN_FILE.name} and are not those of a new model: {sorted(extra)[:3]}"
    return None


def test_a_pending_file_may_add_the_time_records_of_a_new_model_and_nothing_else():
    """!
    @brief The time records of a model listed in `new_models` are accepted as additions; a time record of a model that is not listed, or one the frozen file already holds, is refused.
    @return None.
    """
    data = {"version": "9.9.9", "transients": {"a|fvm": {"class": "bit", "t63": {"U": 1.0}}}}
    ok = {"new_models": ["fem"], "transients": {"a|fem": {"class": "new", "t63": {"U": 2.0}}}}
    assert pending_time_problem(ok, data) is None
    assert pending_time_problem({"transients": {"a|fem": {"class": "new", "t63": {}}}}, data) is not None           # the model is not in new_models
    held = {"version": "9.9.9", "transients": {"a|fem": {"class": "bit", "t63": {"U": 1.0}}}}
    assert pending_time_problem(ok, held) is not None                                                                  # a time the frozen file already holds is not an addition
    assert pending_time_problem({"transients": {"a|fvm": {"class": "moved", "t63": {"U": 1.1}}}}, data) is None        # a shift of a frozen time stays valid
    assert with_pending_adds_times(ok, data) == {"a|fvm", "a|fem"}


def with_pending_adds_times(pend, data):
    """!
    @brief The time keys that `with_pending` yields for a synthetic pending file (it needs the same base version).
    @param pend Pending content without a base version.
    @param data Frozen content with a version.
    @return set of keys.
    """
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "x.json").write_text(json.dumps(dict(pend, base_version=data["version"])), encoding="utf-8")
        old = globals()["PENDING_DIR"]
        globals()["PENDING_DIR"] = Path(d)
        try:
            return set(with_pending({**data, "records": {}, "skipped": {}})["transients"])
        finally:
            globals()["PENDING_DIR"] = old


def test_a_pending_skip_moves_the_record_out_of_the_checked_set(tmp_path, monkeypatch):
    """!
    @brief The "skipped" list of a pending file takes a record out of "records" into "skipped" (so a run that is now over the cap passes and a run that still finishes fails),
           moved records are replaced, and a pending file of another base version is ignored.
    @param tmp_path Folder of the synthetic pending files (pytest fixture).
    @param monkeypatch Pytest fixture that points the module at that folder.
    @return None.
    """
    data = {"version": "9.9.9", "records": {"a|solid3d|1": {"class": "bit", "metrics": {"t_max": 1.0}}, "b|fvm|1": {"class": "bit", "metrics": {"t_max": 2.0}}},
            "transients": {}, "skipped": {}}
    (tmp_path / "x.json").write_text(json.dumps({"base_version": "9.9.9", "records": {"b|fvm|1": {"class": "moved", "metrics": {"t_max": 3.0}}},
                                                 "skipped": {"a|solid3d|1": "too many unknowns"}}), encoding="utf-8")
    (tmp_path / "old.json").write_text(json.dumps({"base_version": "1.0.0", "skipped": {"b|fvm|1": "old"}}), encoding="utf-8")
    monkeypatch.setitem(globals(), "PENDING_DIR", tmp_path)
    out = with_pending(data)
    assert "a|solid3d|1" not in out["records"] and out["skipped"] == {"a|solid3d|1": "too many unknowns"}
    assert out["records"]["b|fvm|1"]["metrics"]["t_max"] == 3.0 and out["pending"] == ["x.json"]
    assert data["records"]["a|solid3d|1"] and not data["skipped"]                     # the frozen content itself is not edited
    still_runs = [{"board": "a", "model": "solid3d", "cell_mm": 1.0, "status": "ok"}]
    now_skipped = [{"board": "a", "model": "solid3d", "cell_mm": 1.0, "status": "skipped", "reason": "too many unknowns"}]
    assert F.compare(out, now_skipped) == [] and F.compare(out, still_runs)


def test_a_new_readouts_file_only_adds_metrics_and_cannot_hide_a_shift(tmp_path, monkeypatch):
    """!
    @brief A pending file with "new_readouts" adds metrics to the record as the shifts left it, whatever the order of the file names; a metric the record already holds
           (frozen or shifted) keeps its value, and a run that moves an old metric is still reported.
    @param tmp_path Folder of the synthetic pending files (pytest fixture).
    @param monkeypatch Pytest fixture that points the module at that folder.
    @return None.
    """
    data = {"version": "9.9.9", "records": {"b|fvm|1": {"class": "bit", "metrics": {"t_max": 2.0, "t_mean": 1.5}}}, "transients": {}, "skipped": {}}
    # "a.json" sorts before the shift "x.json": the addition must still be merged after it; its stale "t_max" must not replace the shifted value
    (tmp_path / "a.json").write_text(json.dumps({"base_version": "9.9.9", "new_readouts": True,
                                                 "records": {"b|fvm|1": {"class": "added", "metrics": {"surface:top:t_max": 2.5, "t_max": 99.0}}}}), encoding="utf-8")
    (tmp_path / "x.json").write_text(json.dumps({"base_version": "9.9.9", "records": {"b|fvm|1": {"class": "moved", "metrics": {"t_max": 3.0, "t_mean": 1.5}}}}),
                                     encoding="utf-8")
    monkeypatch.setitem(globals(), "PENDING_DIR", tmp_path)
    out = with_pending(data)
    assert out["records"]["b|fvm|1"]["metrics"] == {"t_max": 3.0, "t_mean": 1.5, "surface:top:t_max": 2.5}
    assert out["pending"] == ["x.json", "a.json"]
    base = {"board": "b", "model": "fvm", "cell_mm": 1.0, "status": "ok", "t_mean": 1.5, "surface": {"top": {"t_max": 2.5}}}
    assert F.compare(out, [dict(base, t_max=3.0)]) == []
    assert F.compare(out, [dict(base, t_max=3.1)]), "a shift of an old metric must be reported with a read-out file present"
    assert F.compare(out, [dict(base, t_max=3.0, surface={"top": {"t_max": 2.6}})]), "a shift of the added read-out must be reported"
    assert F.compare(out, [dict(base, t_max=3.0, surface=None)]), "a read-out that disappears must be reported"


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
    if model == "fem":
        # The finite-element model solves a mesh of more than femcore.FEM_DIRECT_MAX unknowns by conjugate gradients with the optional package pyamg
        from pcbthermal import femcore
        n = frozen_data["records"].get(F.key(board, model, cell), {}).get("metrics", {}).get("unknowns", 0)
        if n > femcore.FEM_DIRECT_MAX and not femcore.available():
            pytest.skip(f"{board} at {cell} mm: the finite-element mesh has {n} unknowns and needs the package pyamg (pip install pyamg)")
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
