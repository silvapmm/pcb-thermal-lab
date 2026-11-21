#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_expected_shifts_2_9_0.py
@brief Question: which frozen numbers may move between v2.8.0 and 2.9.0, by which item, and by how much? Writes `reference/expected_shifts_2.9.0.json` for the refreeze of 2.9.0.
@details The 2.9.0 version of `releases/2.8.0/refreeze/scripts/make_expected_shifts_2_8_0.py` (itself the 2.8.0 version of `releases/regression-harness/scripts/make_expected_shifts.py`). Differences:

         * the baseline is the tag v2.8.0 (its numbers are those of `tests/regression/data/v2.8.0.json`);
         * the items of this cycle that move records come from the pending files: `fem-thin-copper-source` (N1) and `solid3d-pad-inplane` (N3); `fem-transient` (N2, the time to 63 %
           of the FEM, ADDED) and `surface-readout-models` (N4, the surface read-out of the Analytic and the 3D solid, ADDED) move nothing that exists;
         * the two harness boards of this cycle (`top_block_pad`, `thick_copper_gap`) are in no frozen file and have no pending file: their shifts are attributed BY HAND
           (`NEW_BOARD_ITEMS`): the 3D solid of `top_block_pad` to the in-plane conductivity of the pad (N3), the 3D solid of `thick_copper_gap` to the copper slabs (N5), the FEM
           of both to N1; FVM, Analytic and Lumped must not move;
         * there is no `--preview` mode (the numbers are read from the two result sets only).

         From the repository root:

         .venv/bin/python releases/2.9.0/refreeze/scripts/make_expected_shifts_2_9_0.py releases/regression-harness/out/v2.8.0.json releases/regression-harness/out/final.json
             Reads the two result sets of the harness (`study_baseline_release.py --tag v2.8.0`, `study_run_suite.py --label final`), measures every limit on them and writes the table.
             Run it BEFORE `study_diff.py`: the table is a hypothesis that the diff holds the tree to.
"""

import argparse
import glob
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "releases" / "regression-harness" / "lib"))
sys.path.insert(0, str(REPO / "releases" / "regression-harness" / "scripts"))

import regress_classify as C                                                # noqa: E402
import make_expected_shifts as M                                            # noqa: E402

OUT_TABLE = REPO / "releases" / "regression-harness" / "reference" / "expected_shifts_2.9.0.json"
PENDING = REPO / "tests" / "regression" / "data" / "pending"

# Pending-file name to item id. `fem-transient` and `surface-readout-models` are files of ADDITIONS (they carry `new_time_models` / `new_readouts`), never the item of a shift.
ID = {"fem-thin-copper-source": "N1", "fem-transient": "N2", "solid3d-pad-inplane": "N3", "surface-readout-models": "N4"}

# Items of the table: (id, title, branch, evidence, what it moves)
ITEMS = [
    ("N1", "FEM part on an outer copper layer enters through its outer face", "fix/fem-thin-copper-source", "releases/2.9.0/fem-thin-copper/README.md",
     "FEM records of the boards whose part sits on copper: the column by 0.01 to 0.8 mK, drawn_ell by 0.1 to 1.5 K (2 to 0.5 mm); the surface of the FEM by up to the whole term q t / (2 k); no other model moves"),
    ("N2", "FEM time simulation: the time to 63 % of the FEM ADDED", "feature/fem-transient", "releases/2.9.0/fem-transient/MEASURED.md; docs/theory.md 4b",
     "none: the FEM times to 63 % exist only in the 2.9.0 run (the boards whose mesh at the response cell is at most the harness cap); they are additions, not shifts"),
    ("N3", "3D solid interface pad conducts across only (1e-3 W/mK in its plane)", "fix/solid3d-pad-inplane", "releases/2.9.0/solid3d-pad-inplane/README.md",
     "3D solid of the boards with a metal block (finned_block 0.002 K at most) and, by hand, top_block_pad (the hottest column 170.472 to 171.226 C at 2 mm, 170.662 to 171.439 C at 1 mm in the review of the stage-A bump); no other model moves"),
    ("N4", "Surface read-out of the Analytic and the 3D solid: ADDED metrics", "feature/surface-readout-models", "releases/2.9.0/surface-readout-models/DESIGN.md; research/surface-readout-models README 4",
     "none: the surface metrics are ADDED to the existing records of the Analytic and the 3D solid (a view); no old metric moves"),
    ("N5", "Copper slabs of the 3D solid (copper above 105 um is a slab of its own)", "feature/solid3d-copper-slabs", "releases/2.9.0/solid3d-copper-slabs/README.md",
     "3D solid of thick_copper_gap, by hand (the hottest column 172.846 to 173.367 C at 2 mm, 172.508 to 173.074 C at 1 mm in the review of the stage-A bump); the frozen boards have copper of 105 um or less and are not reached"),
    ("N0", "Items with no frozen record", "text, GUI, calculator and documentation items of 2.9.0", "CHANGELOG 2.9.0",
     "none: a shift attributed to them would be a defect"),
    ("L8", "Round-off", "last bits of the sums (order of the operations)", "CLAUDE.md Decisions Log (symmetric LU)", "at most 1e-8 K")]

# The two boards of this cycle that no frozen file holds and no pending file covers: the items by board and model, attributed by hand (the reviewer of stage A). Only a model that
# moves gets a rule (`shift_sizes` finds nothing for a record that is bit-identical); FVM, Analytic and Lumped have no entry: if one moves, it is "??" and an alarm.
NEW_BOARD_ITEMS = {"top_block_pad": {"solid3d": ("N3",), "fem": ("N1",)},
                   "thick_copper_gap": {"solid3d": ("N5",), "fem": ("N1",)}}

# Metrics that only the 2.9.0 run has: not shifts (regress_classify.diff_sets reads this list)
ADDED_METRICS = [{"id": "A4", "boards": "*", "models": ["analytic", "solid3d"], "cells": "*",
                  "metrics": ["surface:*", "part:*:t_max_surface", "part:*:t_mean_surface"],
                  "note": "surface read-out of the Analytic and the 3D solid, added to the records (feature/surface-readout-models); never a rule on `status`: it would also excuse a failed run"}]


def board_of(key):
    """!
    @brief Board name of a key `board|model|cell` or `board|model`.
    @param key The key.
    @return str.
    """
    return key.split("|")[0]


def extra_items(key, model):
    """!
    @brief Items of a record on a board that no pending file holds (the two new boards), attributed by hand.
    @param key Record key `board|model|cell` or `board|model`.
    @param model Model key (`fvm_sor` for a SOR run).
    @return tuple of item ids, empty for every other board and for a model with no entry.
    """
    return NEW_BOARD_ITEMS.get(board_of(key), {}).get(model, ())


def items_of(key, model, P, section="records", prefix=""):
    """!
    @brief Every item that moved a record or a time: the pending files that hold it, `also_moved_by`, and the board rules of the new boards.
    @param key Record key.
    @param model Model key.
    @param P Pending files by name.
    @param section `records` or `transients`.
    @param prefix `t63:` for a time.
    @return tuple of sorted item ids.
    """
    # A file of additions (a new model, a new read-out) holds the same keys as the shifts but moves nothing: it is never an item of a shift
    shifting = {n: p for n, p in P.items() if not (p.get("new_models") or p.get("new_readouts") or p.get("new_time_models"))}
    its = set(M.attribute(key, shifting, ID, section, prefix)) | set(extra_items(key, model))
    return tuple(sorted(its))


def shift_sizes(mb, mf):
    """!
    @brief Largest shift of a record by kind: temperature (K), balance (W), unknowns (fraction).
    @param mb Metrics of the baseline record (flat dict).
    @param mf Metrics of the new record.
    @return tuple (t, w, u) of floats, 0.0 when nothing of that kind moved by more than 1e-8.
    """
    t = w = u = 0.0
    for n in mf:
        if n not in mb:
            continue                                                       # an added metric is not a shift (it is in `added_metrics`)
        d = abs(mf[n] - mb[n])
        if d <= 1e-8:
            continue
        g = C.metric_group(n)
        if g == "temperature":
            t = max(t, d)
        elif g == "balance":
            w = max(w, d)
        elif g == "count":
            u = max(u, d / abs(mb[n]))
    return t, w, u


def load_sets(base_path, final_path):
    """!
    @brief Baseline and new numbers from two result sets of the harness (steady, SOR and times to 63 %).
    @param base_path Result set of the tag v2.8.0.
    @param final_path Result set of the tree.
    @return tuple (base, final, tbase, tfinal, sor_base, sor_final, P): the numbers by `board|model|cell` (only runs that are ok in both), by `board|model` for the times, and the
            pending files.
    """
    bs, fs = C.load_set(base_path), C.load_set(final_path)
    P = {os.path.basename(f)[:-5]: json.loads(Path(f).read_text(encoding="utf-8")) for f in sorted(glob.glob(str(PENDING / "*.json")))}
    out = []
    for key in ("records", "sor"):
        b, f = C.index(bs, key), C.index(fs, key)
        ob, of = {}, {}
        for (bd, m, c, s), rb in b.items():
            rf = f.get((bd, m, c, s))
            if rf is None or rb["status"] != "ok" or rf["status"] != "ok" or (key == "records" and s != "direct"):
                continue
            k = f"{bd}|{m}|{c:g}"
            ob[k], of[k] = C.metrics_of(rb), C.metrics_of(rf)
        out += [ob, of]
    tb = {f"{t['board']}|{t['model']}": {p["name"]: p["t63_s"] for p in t["parts"] if p["t63_s"] is not None} for t in bs.get("transients", []) if t["status"] == "ok"}
    tf = {f"{t['board']}|{t['model']}": {p["name"]: p["t63_s"] for p in t["parts"] if p["t63_s"] is not None} for t in fs.get("transients", []) if t["status"] == "ok"}
    return out[0], out[1], tb, tf, out[2], out[3], P


def steady_rules(base, final, P, sor_base=None, sor_final=None):
    """!
    @brief The rules of the steady records: one per (items, model), with a limit per record of 1.25 x the shift, and the SOR rules.
    @param base Baseline metrics by `board|model|cell`.
    @param final New metrics by `board|model|cell`.
    @param P Pending files by name.
    @param sor_base Baseline metrics of the SOR runs by `board|fvm|cell` (None: no SOR rules).
    @param sor_final New metrics of the SOR runs.
    @return list of rule dicts (ids R1.., S.., R0).
    """
    by = defaultdict(list)
    for k, mb in base.items():
        mf = final.get(k)
        if mf is None:
            continue
        bd, m, c = k.split("|")
        its = items_of(k, m, P)
        t, w, u = shift_sizes(mb, mf)
        if not its:
            if t or w or u:
                its = ("??",)                                              # moved with no item: an alarm in the diff until it is explained
            else:
                continue
        by[(its, m)].append((bd, float(c), k, t, w, u))
    rules = []
    for i, ((its, m), recs) in enumerate(sorted(by.items())):
        lim = {}
        for bd, c, k, t, w, u in recs:
            e = {"abs_k": [0, round(max(1.25 * t, 1e-6), 6)]}
            if w:
                e["abs_w"] = [0, max(1.25 * w, 1e-9)]
            if u:
                e["rel"] = [0, round(max(1.25 * u, 1e-3), 5)]
            lim[k] = e
        rules.append({"id": f"R{i + 1}", "item": "+".join(its), "boards": sorted({r[0] for r in recs}), "models": [m], "cells": sorted({r[1] for r in recs}), "metrics": "*",
                      "direction": "any", "abs_k": [0, 50], "abs_w": [0, 1e-6], "rel": [0, 1], "status": "quantified" if "??" not in its else "to be explained",
                      "note": "items from the pending files of the integration; limits = 1.25 x the shift of this run (floor 1e-6 K)", "limits": lim})
    for k, mb in sorted((sor_base or {}).items()):
        mf = (sor_final or {}).get(k)
        if mf is None:
            continue
        bd, _, c = k.split("|")
        t = shift_sizes(mb, mf)[0]
        if t <= 1e-8:
            continue
        its = items_of(f"{bd}|fvm|{c}", "fvm", P) or items_of(k, "fvm_sor", P)
        rules.append({"id": f"S{len(rules)}", "item": "+".join(its) or "??", "boards": [bd], "models": ["fvm_sor"], "cells": [float(c)], "metrics": "*", "direction": "any",
                      "abs_k": [0, round(max(1.25 * t, 1e-6), 6)], "abs_w": [0, 1e-6], "rel": [0, 1], "status": "quantified",
                      "note": "the SOR run reaches the direct FVM solution: the same items as the FVM record"})
    rules.append({"id": "R0", "item": "L8", "boards": "*", "models": "*", "cells": "*", "metrics": "*", "direction": "any", "abs_k": [0, 1e-8], "abs_w": [0, 1e-8], "rel": [0, 0],
                  "status": "derived", "note": "round-off of the order of the sums"})
    return rules


def transient_rules(tbase, tfinal, P):
    """!
    @brief The `may_move` entries of the times to 63 % (only the times that both result sets hold; the FEM times of 2.9.0 are additions).
    @param tbase Baseline times by `board|model`.
    @param tfinal New times by `board|model`.
    @param P Pending files by name.
    @return dict with `must_not_move` and `may_move`.
    """
    may = []
    for key, t in sorted(tfinal.items()):
        o = tbase.get(key)
        if o is None:
            continue
        mxr = max([abs(t[p] - o[p]) / o[p] for p in t if p in o and o[p]] + [0.0])
        its = items_of(key, key.split("|")[1], P, "transients", "t63:")
        if mxr > 1e-6 or its:
            bd, m = key.split("|")
            may.append({"id": f"T{len(may) + 1}", "boards": [bd], "models": [m], "direction": "any", "rel_change": [0, round(max(1.25 * mxr, 0.01), 4)],
                        "item": "+".join(its) or "??", "note": "time to 63 %"})
    added = [{"id": "A2", "boards": "*", "models": ["fem"], "note": "time to 63 % of the FEM time simulation of 2.9.0 (feature/fem-transient): only in the new run, an addition"}]
    return {"must_not_move": [], "added": added, "may_move": may + [{"id": "T0", "boards": "*", "models": "*", "direction": "any", "rel_change": [0, 1e-6], "note": "round-off of the time to 63 %"}]}


def build_table(base, final, tbase, tfinal, P, sor_base=None, sor_final=None):
    """!
    @brief The whole table.
    @param base Baseline metrics by `board|model|cell`.
    @param final New metrics.
    @param tbase Baseline times to 63 %.
    @param tfinal New times to 63 %.
    @param P Pending files by name.
    @param sor_base Baseline SOR metrics.
    @param sor_final New SOR metrics.
    @return dict, the content of `expected_shifts_2.9.0.json`.
    """
    rules = steady_rules(base, final, P, sor_base, sor_final)
    how = ("Same reading as expected_shifts_2.8.0.json. Baseline: the tag v2.8.0 (the numbers of v2.8.0.json). Items N1 and N3 come from the two pending files of 2.9.0 that hold shifted records; "
           "the FEM times to 63 % and the surface read-out of the Analytic and the 3D solid are ADDITIONS (`added_metrics`, times only in the new set), not shifts. The two new harness boards "
           "(top_block_pad, thick_copper_gap) are in no frozen file and no pending file: their items are attributed by hand (N3 and N5 for the 3D solid, N1 for the FEM); FVM, Analytic and "
           "Lumped must not move on them. The numeric limits are 1.25 times the shifts of the run that made the table: the table does not predict the sizes, it holds the next version to them.")
    return {"format": 1, "baseline": "v2.8.0", "target": "2.9.0", "provisional": False, "how_to_read": how,
            "items": [{"id": a, "title": t, "branch": br, "evidence": ev, "moves": mv} for a, t, br, ev, mv in ITEMS],
            "rules": rules, "must_not_move": [], "added_metrics": ADDED_METRICS, "transients": transient_rules(tbase, tfinal, P), "board_matrix": {}}


def main(argv=None):
    """!
    @brief Parse the arguments, build the table from two result sets and write it.
    @param argv List of arguments (default: sys.argv[1:]).
    @return int exit code (0).
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("sets", nargs=2, help="result set of v2.8.0 and result set of the tree")
    ap.add_argument("--out", default=str(OUT_TABLE))
    a = ap.parse_args(argv)
    base, final, tb, tf, sb, sf, P = load_sets(*a.sets)
    table = build_table(base, final, tb, tf, P, sb, sf)
    Path(a.out).write_text(json.dumps(table, indent=1) + "\n", encoding="utf-8")
    unexplained = [r["id"] for r in table["rules"] if "??" in r["item"]]
    print(f"{len(table['rules'])} rules, {len(table['transients']['may_move'])} transient rules, {len(table['added_metrics'])} added-metric scope(s), written to {a.out}")
    print("records with no item (to be explained):", unexplained or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
