#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_expected_shifts_2_8_0.py
@brief Question: which frozen numbers may move between v2.7.1 and 2.8.0, by which item, and by how much? Writes `reference/expected_shifts_2.8.0.json` for the refreeze of 2.8.0.
@details The 2.8.0 version of `releases/regression-harness/scripts/make_expected_shifts.py` (the 2.7.0 script has its items and its two result sets written in). Differences:

         * the baseline is the tag v2.7.1, which moved no frozen number (its final opinion, `releases/2.7.1/final-opinion/README.md` 3), so the baseline numbers are also those of
           `tests/regression/data/v2.7.0.json`;
         * the four items of this cycle that move records are read from the pending files (`face-film-half-slab`, `drawn-copper-faces`, `lumped-first-link-edge`,
           `block-exact-cover`) and a record that a later file took over is credited to every item through `also_moved_by` (`make_expected_shifts.attribute`);
         * the three harness boards of `drawn-copper-faces` (`drawn_*`) are in no frozen file: their shifts are attributed by board and model (`NEW_BOARD_ITEMS`);
         * the surface read-out and the finite-element model are ADDITIONS, not shifts: the table carries an `added_metrics` list (metrics that only the 2.8.0 run has, read by
           `regress_classify.diff_sets`), the finite-element records exist only in the new set, and the 3D solid is a `must_not_move` entry (no item of the cycle reaches it).

         Two ways to run it, from the repository root:

         .venv/bin/python releases/2.8.0/refreeze/scripts/make_expected_shifts_2_8_0.py --preview
             Reads only JSON files that are in git: the baseline is `tests/regression/data/v2.7.0.json`, the new numbers are the same file with the pending files applied. It runs no solver,
             writes the PROVISIONAL table (limits = 1.25 x the shifts the pending files hold; the `drawn_*` boards get derived bounds) and takes seconds.
         .venv/bin/python releases/2.8.0/refreeze/scripts/make_expected_shifts_2_8_0.py releases/regression-harness/out/v2.7.1.json releases/regression-harness/out/final.json
             Reads the two result sets of the harness (`study_baseline_release.py --tag v2.7.1`, `study_run_suite.py --label final`), measures every limit on them (including the
             `drawn_*` boards) and writes the FINAL table. Run it BEFORE `study_diff.py`: the table is a hypothesis that the diff holds the tree to.
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

OUT_TABLE = REPO / "releases" / "regression-harness" / "reference" / "expected_shifts_2.8.0.json"
FROZEN = REPO / "tests" / "regression" / "data" / "v2.7.0.json"
PENDING = REPO / "tests" / "regression" / "data" / "pending"

# Pending-file name to item id (`lumped-part-readout` is the older file that `lumped-first-link-edge` replaced; a name not in the map is its own id)
ID = {"face-film-half-slab": "M1", "drawn-copper-faces": "M2", "lumped-first-link-edge": "M3", "lumped-part-readout": "M3", "block-exact-cover": "M4",
      "fem-records": "A1", "surface-records": "A2"}

# Items of the table: (id, title, branch, evidence, what it moves)
ITEMS = [
    ("M1", "Every face film of a copper node passes the half copper layer", "fix/face-film-half-slab", "docs/validation.md 55; CHANGELOG 2.8.0",
     "FVM, FDM, Lumped and Analytic of every board, at every cell: hotter, median 2e-5 K and at most 0.040 K on the finned block (the heat into the block moves by 1.1e-3 W); the 3D solid moves nowhere"),
    ("M2", "Drawn copper read as imported copper (exact fill, flow-based faces) in the FVM and FDM", "fix/drawn-copper-faces", "docs/validation.md 51; research/drawn-copper-faces README 7",
     "FVM and FDM of the boards with a drawn layer that has a cell cut by a zone edge, at 2 mm (their other copper edges lie on cell lines), and their times to 63 %; the three new harness boards drawn_*"),
    ("M3", "Lumped part rows read the own peak of the part; the first link sees the images of the board sides", "fix/lumped-part-readout + fix/lumped-edge-first-link",
     "docs/validation.md 48 and 53; research/lumped-edge-link README 3.6",
     "Lumped of every board (51 records at 2, 1 and 0.5 mm, 12 times to 63 %): part rows up (up to 14.9 K on the part peak of a lone part), the board maximum -0.5 to +3.1 % of the rise"),
    ("M4", "Exact cover of a metal block (Analytic tiles)", "fix/block-exact-cover", "docs/validation.md 54", "Analytic of finned_block at 1 and 0.5 mm (+0.09 K); no other record moves"),
    ("A1", "Finite-element comparison model (key fem): ADDED records", "feature/fem-model", "docs/validation.md 56 and 57; releases/2.8.0/fem-model/DESIGN.md",
     "none: the records exist only in the 2.8.0 run (and in fem-records.json); they are additions, not shifts"),
    ("A2", "Surface read-out of the FVM, FDM and FEM: ADDED metrics", "fix/thick-plate-surface-estimate + feature/surface-always-both + fix/fem-solve-speed",
     "docs/theory.md 1.2c; releases/2.8.0/fem-model/SURFACE_ALWAYS.md", "none: new metrics surface:*, part:*:t_max_surface, part:*:t_mean_surface on existing records of the FVM, FDM and the SOR runs; no old metric moves"),
    ("A3", "Conjugate-gradient tolerance of the FEM 1e-10 (was 1e-12)", "fix/fem-solve-speed", "releases/2.8.0/fem-model/SPEED_NOTES.md; REVIEW_SPEED.md",
     "none of the old records: the FEM records are new; they are not bit-identical from run to run above FEM_DIRECT_MAX (5e-10 K measured) and are held under the tolerance, never exact"),
    ("M0", "Items with no frozen record", "fix/analytic-transient-hot-point; thick-plate, convection and edge warning texts; typical-value marks; the calculator and GUI items",
     "CHANGELOG 2.8.0", "none: the Analytic transient item moved no harness record after its review (releases/2.8.0/reviews/analytic-transient-hot-point.md); a shift attributed to a text or GUI item would be a defect"),
    ("L8", "Round-off", "last bits of the sums (order of the operations)", "CLAUDE.md Decisions Log (symmetric LU)", "at most 1e-8 K")]

# Boards that no frozen file holds (drawn-copper-faces added them to the harness): the items by model. The Lumped and the Analytic never see the drawn-copper change.
NEW_BOARD_PATTERN = "drawn_*"
NEW_BOARD_ITEMS = {"fvm": ("M1", "M2"), "fdm": ("M1", "M2"), "lumped": ("M1", "M3"), "analytic": ("M1",), "fvm_sor": ("M1", "M2")}

# Metrics that only the 2.8.0 run has: not shifts (regress_classify.diff_sets reads this list). "fvm_sor" because the SOR runs carry the surface read-out too.
ADDED_METRICS = [{"id": "A2", "boards": "*", "models": ["fvm", "fdm", "fvm_sor"], "cells": "*",
                  "metrics": ["surface:*", "part:*:t_max_surface", "part:*:t_mean_surface"],
                  "note": "surface read-out of 2.8.0 added to the records (fix/fem-solve-speed, feature/surface-always-both); never a rule on `status`: it would also excuse a failed run"}]


def board_of(key):
    """!
    @brief Board name of a key `board|model|cell` or `board|model`.
    @param key The key.
    @return str.
    """
    return key.split("|")[0]


def extra_items(key, model):
    """!
    @brief Items of a record on a board that no pending file holds (the `drawn_*` boards).
    @param key Record key `board|model|cell` or `board|model`.
    @param model Model key (`fvm_sor` for a SOR run).
    @return tuple of item ids, empty for every other board.
    """
    import fnmatch
    return NEW_BOARD_ITEMS.get(model, ()) if fnmatch.fnmatchcase(board_of(key), NEW_BOARD_PATTERN) else ()


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
    shifting = {n: p for n, p in P.items() if not (p.get("new_models") or p.get("new_readouts"))}
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


def load_preview():
    """!
    @brief Baseline and new numbers from the committed files only: the frozen file of 2.7.0, and the same with the pending files applied.
    @return tuple (base, final, tbase, tfinal, P): dicts of metrics by `board|model|cell`, dicts of times to 63 % by `board|model`, the pending files by name.
    """
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))
    P = {os.path.basename(f)[:-5]: json.loads(Path(f).read_text(encoding="utf-8")) for f in sorted(glob.glob(str(PENDING / "*.json")))}
    base = {k: r["metrics"] for k, r in frozen["records"].items()}
    final = dict(base)
    tbase = {k: t["t63"] for k, t in frozen["transients"].items()}
    tfinal = dict(tbase)
    for p in P.values():
        if p.get("new_models") or p.get("new_readouts"):
            continue                                                       # additions: neither a shift nor in the baseline
        final.update({k: r["metrics"] for k, r in p.get("records", {}).items()})
        tfinal.update({k: t["t63"] for k, t in p.get("transients", {}).items()})
    return base, final, tbase, tfinal, P


def load_sets(base_path, final_path):
    """!
    @brief Baseline and new numbers from two result sets of the harness (steady, SOR and times to 63 %).
    @param base_path Result set of the tag v2.7.1.
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


def derived_new_board_rules(first_id):
    """!
    @brief Bounds for the `drawn_*` boards when no run of them is available (preview mode): DERIVED from the evidence of the items, not measured.
    @details Drawn copper (validation 51.3): the FVM heater mean moves by up to about 1.4 to 4 points of the rise and the FDM stripes board by 11 points; the Lumped by M3 (-3.1 to
             +3.1 % of the rise); the Analytic only by M1 (about 1e-5 of the rise). The bounds are in fractions of the rise of the old hottest point (`rel_rise`); the final run replaces them.
    @param first_id Number to start the rule ids from.
    @return list of rule dicts.
    """
    spec = {"fvm": (("M1", "M2"), 0.06), "fdm": (("M1", "M2"), 0.15), "lumped": (("M1", "M3"), 0.06), "analytic": (("M1",), 0.001)}
    return [{"id": f"D{first_id + i}", "item": "+".join(its), "boards": [NEW_BOARD_PATTERN], "models": [m], "cells": "*", "metrics": "*", "direction": "any", "rel_rise": [0, hi],
             "abs_w": [0, 0.01], "rel": [0, 1], "status": "derived",
             "note": "the drawn_* boards are in no frozen file: bound DERIVED from the evidence of the items (validation 51.3 and 53), replaced by the measured limit of the final run"}
            for i, (m, (its, hi)) in enumerate(spec.items())]


def transient_rules(tbase, tfinal, P, preview):
    """!
    @brief The `may_move` entries of the times to 63 %.
    @param tbase Baseline times by `board|model`.
    @param tfinal New times by `board|model`.
    @param P Pending files by name.
    @param preview True to add the derived entries of the `drawn_*` boards.
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
    if preview:
        for m, hi in (("fvm", 0.3), ("fdm", 0.4), ("lumped", 0.2), ("analytic", 0.01)):
            may.append({"id": f"T{len(may) + 1}", "boards": [NEW_BOARD_PATTERN], "models": [m], "direction": "any", "rel_change": [0, hi],
                        "item": "+".join(NEW_BOARD_ITEMS[m]), "note": "time to 63 %: bound DERIVED for the drawn_* boards, replaced by the measured limit of the final run"})
    return {"must_not_move": [], "may_move": may + [{"id": "T0", "boards": "*", "models": "*", "direction": "any", "rel_change": [0, 1e-6], "note": "round-off of the time to 63 %"}]}


def build_table(base, final, tbase, tfinal, P, sor_base=None, sor_final=None, preview=False):
    """!
    @brief The whole table.
    @param base Baseline metrics by `board|model|cell`.
    @param final New metrics.
    @param tbase Baseline times to 63 %.
    @param tfinal New times to 63 %.
    @param P Pending files by name.
    @param sor_base Baseline SOR metrics (result-set mode).
    @param sor_final New SOR metrics.
    @param preview True when the numbers come from the frozen file and the pending files (provisional table).
    @return dict, the content of `expected_shifts_2.8.0.json`.
    """
    rules = steady_rules(base, final, P, sor_base, sor_final)
    if preview:
        rules = rules[:-1] + derived_new_board_rules(len(rules)) + rules[-1:]   # R0 stays last
    how = ("Same reading as expected_shifts_2.7.0.json. Baseline: the tag v2.7.1 (it moved no frozen number: its numbers are those of v2.7.0.json). Items M1 to M4 come from the four "
           "pending files of 2.8.0 that hold records (one record in one file; `also_moved_by` credits the older items); the finite-element records and the surface read-out are ADDITIONS "
           "(`added_metrics`, records only in the new set), not shifts; the 3D solid is `must_not_move` (no item of the cycle reaches it). The numeric limits are 1.25 times the shifts of the run "
           "that made the table: the table does not predict the sizes, it holds the next version to them.")
    if preview:
        how = ("PROVISIONAL (made by --preview from tests/regression/data/v2.7.0.json and the pending files, no solver run; the drawn_* boards have derived bounds). Regenerate it from the two "
               "result sets of the harness before study_diff.py. ") + how
    return {"format": 1, "baseline": "v2.7.1", "target": "2.8.0", "provisional": bool(preview), "how_to_read": how,
            "items": [{"id": a, "title": t, "branch": br, "evidence": ev, "moves": mv} for a, t, br, ev, mv in ITEMS],
            "rules": rules,
            "must_not_move": [{"id": "N1", "boards": "*", "models": ["solid3d"], "cells": "*", "metrics": "*",
                               "reason": "no item of 2.8.0 reaches the 3D solid on a harness board (it already had the series film of the half cell; the block cover moves only the Analytic records); pending files hold no solid3d record"}],
            "added_metrics": ADDED_METRICS, "transients": transient_rules(tbase, tfinal, P, preview), "board_matrix": {}}


def main(argv=None):
    """!
    @brief Parse the arguments, build the table from the frozen and pending files (--preview) or from two result sets, and write it.
    @param argv List of arguments (default: sys.argv[1:]).
    @return int exit code (0).
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("sets", nargs="*", help="result set of v2.7.1 and result set of the tree (omit with --preview)")
    ap.add_argument("--preview", action="store_true", help="provisional table from the frozen file and the pending files, no result sets")
    ap.add_argument("--out", default=str(OUT_TABLE))
    a = ap.parse_args(argv)
    if a.preview:
        base, final, tb, tf, P = load_preview()
        table = build_table(base, final, tb, tf, P, preview=True)
    else:
        if len(a.sets) != 2:
            ap.error("give the two result sets, or --preview")
        base, final, tb, tf, sb, sf, P = load_sets(*a.sets)
        table = build_table(base, final, tb, tf, P, sb, sf)
    Path(a.out).write_text(json.dumps(table, indent=1) + "\n", encoding="utf-8")
    unexplained = [r["id"] for r in table["rules"] if "??" in r["item"]]
    print(f"{len(table['rules'])} rules, {len(table['transients']['may_move'])} transient rules, {len(table['added_metrics'])} added-metric scope(s), written to {a.out}")
    print("records with no item (to be explained):", unexplained or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
