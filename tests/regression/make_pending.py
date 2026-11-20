#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_pending.py
@brief Writes a pending shift (`data/pending/<name>.json`): the new numbers of the frozen records that a decided model change moves, between two releases.
@details Why: the frozen file `data/v<version>.json` holds the numbers of a release and can only be remade after the version bump (`study_freeze_reference.py` refuses a run of
         another version). A `feature/` or `fix/` branch that moves records on purpose before the next release records the new numbers here instead, so that the battery stays
         green, the moved records are still held (to the same tolerance) and `v<version>.json` keeps meaning "the numbers of that release". The test applies every pending file
         whose `base_version` is the version of the newest frozen file; at the next release the refreeze folds the shifts in, and the pending files are deleted (the test fails
         on a pending file of an older base, as a reminder).

         Usage, from the repository root, after the change is reviewed (only the records named are run and written):

             .venv/bin/python tests/regression/make_pending.py lumped-zones --board plate_vias --model lumped \
                 --item "Zonal Lumped model" --branch feature/lumped-zones --why "..."

         `--no-times` writes only the steady records and `--times-only` only the times to 63 % (a change that moves one kind and not the other).

         A NEW model (one that no frozen record has, a comparison model added by a feature) adds records and moves none: `--new-model fem --cell 2 --cell 1` runs it on the named boards
         at those cells, keeps what finishes (a board it refuses or a run above the cap of the harness is left out, not recorded) and writes the pending file with `"new_models"`
         naming it, so that the test knows the records are additions and not shifts. Since 2.9.0 the new model also adds its TIME records (`board|model` -> time to 63 % per part, the
         read-out of `regress_harness.t63`) for the boards it runs, unless `--no-times`; a time record of a model that is not in `new_models` is still refused by the test.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))


def s_cap(name, frozen):
    """!
    @brief A cap of the harness as the frozen file recorded it.
    @param name Key of frozen["settings"] ("max_unknowns" or "solid_cap").
    @param frozen Content of the frozen file.
    @return int.
    """
    return frozen["settings"][name]


def main(argv=None):
    """!
    @brief Run the named records of the newest frozen file with the tree as it is and write them as a pending shift.
    @param argv List of arguments (default: sys.argv[1:]).
    @return int exit code (0, or 2 when a named board or model is not in the frozen file).
    """
    import os
    import tempfile
    # The same private, empty configuration as the test (conftest.private_config): the user's defaults must not enter the numbers
    os.environ["PCBTHERMAL_CONFIG"] = tempfile.mkdtemp(prefix="pcbt_frozen_cfg_")
    from pcbthermal import defaults, model
    defaults._CACHE.pop("stamp", None)
    model.reload_libraries()
    import regress_boards as B
    import regress_classify as C
    import regress_frozen as F
    import regress_harness as H
    import test_frozen_numbers as T

    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("name", help="file name without extension (the topic of the branch)")
    ap.add_argument("--board", action="append", required=True, help="board name (repeat for several)")
    ap.add_argument("--model", action="append", default=[], help="model key (repeat for several)")
    ap.add_argument("--new-model", action="append", default=[], help="a model that the frozen file does not hold: its records are ADDED (needs --cell)")
    ap.add_argument("--cell", action="append", type=float, default=[], help="cell in mm of the added records (repeat); a record is added only when it finishes")
    ap.add_argument("--item", required=True, help="the change that moves the records")
    ap.add_argument("--branch", required=True, help="branch of the change")
    ap.add_argument("--why", required=True, help="why the records move (one or two sentences)")
    ap.add_argument("--evidence", default="", help="where the shift is measured and explained")
    ap.add_argument("--new-readouts", action="store_true", help="ADD the metrics that no frozen record holds (the surface read-out) to the existing records of the named models and boards "
                    "(a file with \"new_readouts\": it moves no frozen number)")
    ap.add_argument("--no-times", action="store_true", help="write only the steady records (a change that moves no time to 63 %%, or whose times belong to another pending file)")
    ap.add_argument("--times-only", action="store_true", help="write only the times to 63 %% (the steady records of the named boards do not move)")
    a = ap.parse_args(argv)
    frozen = F.load(T.FROZEN_FILE)
    s = frozen["settings"]
    records, transients, skipped = {}, {}, {}
    if not a.model and not a.new_model and not a.new_readouts:
        print("refused: name --model (existing records) or --new-model with --cell")
        return 2
    if a.new_readouts:
        if not a.model:
            print("refused: --new-readouts needs --model")
            return 2
        for board in a.board:
            p = B.build(board)
            for model in a.model:
                for k, old in frozen["records"].items():
                    if not k.startswith(f"{board}|{model}|") or k in frozen["skipped"]:
                        continue
                    rec = H.run_one(p, board, model, float(k.split("|")[2]), s_cap("max_unknowns", frozen), s_cap("solid_cap", frozen))
                    if rec["status"] != "ok":
                        print(f"refused: {k} did not run ({rec['status']}: {rec.get('reason', '')})")
                        return 2
                    added = {n: v for n, v in C.metrics_of(rec).items() if n not in old["metrics"]}
                    if added:
                        records[k] = {"class": "added", "metrics": added}
    for board in [] if a.new_readouts else (a.board if a.new_model else []):
        if board not in frozen["boards"]:
            print(f"refused: board {board} is not in {T.FROZEN_FILE.name}")
            return 2
        p = B.build(board)
        for model in a.new_model:
            for cell in a.cell:
                k = F.key(board, model, cell)
                if k in frozen["records"]:
                    print(f"refused: {k} is already in {T.FROZEN_FILE.name}: it is not a new record")
                    return 2
                rec = H.run_one(p, board, model, cell, s_cap("max_unknowns", frozen), s_cap("solid_cap", frozen))
                if rec["status"] == "skipped":
                    print(f"left out: {k}: {rec.get('reason', '')}")
                    continue
                if rec["status"] != "ok":
                    print(f"refused: {k} did not run ({rec['status']}: {rec.get('reason', '')})")
                    return 2
                records[k] = {"class": "new", "metrics": C.metrics_of(rec)}
            tk = f"{board}|{model}"
            if tk not in frozen["transients"] and not a.no_times and p.heaters and any(k.startswith(f"{board}|{model}|") for k in records):
                t = H.t63(p, model, s["transient_cell"])
                if t["status"] == "ok":
                    transients[tk] = {"class": "new", "t63": {q["name"]: q["t63_s"] for q in t["parts"] if q["t63_s"] is not None}}
                else:
                    print(f"left out: {tk} time to 63 %: {t['status']} {t.get('reason', '')}")
    for board in [] if a.new_readouts else a.board:
        if board not in frozen["boards"]:
            print(f"refused: board {board} is not in {T.FROZEN_FILE.name}")
            return 2
        p = B.build(board)
        for model in a.model:
            keys = [k for k in frozen["records"] if k.startswith(f"{board}|{model}|")]
            if not keys:
                print(f"refused: no record {board}|{model} in {T.FROZEN_FILE.name}")
                return 2
            for k in ([] if a.times_only else keys):
                rec = H.run_one(p, board, model, float(k.split("|")[2]), s["max_unknowns"], s["solid_cap"])
                if rec["status"] == "skipped":
                    # A change that adds unknowns can push a record over the size cap of the harness: it leaves the frozen set and is held as skipped
                    skipped[k] = rec.get("reason", "skipped")
                    continue
                if rec["status"] != "ok":
                    print(f"refused: {k} did not run ({rec['status']}: {rec.get('reason', '')})")
                    return 2
                records[k] = {"class": "moved", "metrics": C.metrics_of(rec)}
            tk = f"{board}|{model}"
            if tk in frozen["transients"] and not a.no_times:
                t = H.t63(p, model, s["transient_cell"])
                if t["status"] == "ok":
                    transients[tk] = {"class": "moved", "t63": {q["name"]: q["t63_s"] for q in t["parts"] if q["t63_s"] is not None}}
    out = {"format": F.FORMAT, "base_version": frozen["version"], "item": a.item, "branch": a.branch, "why": a.why, "evidence": a.evidence,
           "records": records, "transients": transients}
    if a.new_model:
        out["new_models"] = sorted(a.new_model)
    if a.new_readouts:
        out["new_readouts"] = True
    if skipped:
        out["skipped"] = skipped
    path = HERE / "data" / "pending" / f"{a.name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(records)} records, {len(skipped)} now skipped, {len(transients)} times to 63 %)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
