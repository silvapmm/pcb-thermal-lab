#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_pending_coverage.py
@brief Question: is every number that moved between the last release and the tree under test covered by an item of the tree (a pending-shift file), or by nothing but the last bit of a floating-point sum? Writes the answer as JSON.
@details Usage, from the repository root:

         .venv/bin/python research/release-regression-245/scripts/study_pending_coverage.py out/v2.4.5.json out/develop-tip.json [--pending tests/regression/data/pending] [--out out/pending_coverage.json]

         Every metric of every record that differs between the two result sets is put in one of three classes: `last_bit` (absolute difference at most 1e-8 K or 1e-10 of the
         value, the policy of the frozen-numbers test), `covered` (the record is in a pending file of the tree and the new value equals the value stored there within the same
         tolerance) or `unexplained`. The times to 63 % are checked against the `transients` entry of the pending files in the same way. The number of unexplained shifts must be 0.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lib"))

import regress_classify as C                                                # noqa: E402

ABS_TOL = 1e-8                                                              # K: the frozen-numbers policy for temperatures
REL_TOL = 1e-10                                                             # relative: the policy for field checksums and counts


def same(a, b):
    """!
    @brief Two numbers equal under the frozen-numbers policy.
    @param a First number.
    @param b Second number.
    @return bool.
    """
    return abs(a - b) <= max(ABS_TOL, REL_TOL * max(abs(a), abs(b)))


def load_pending(folder):
    """!
    @brief Read the pending-shift files of a folder.
    @param folder Folder of the `<topic>.json` files.
    @return tuple (dict "board|model|cell" -> list of (topic, metrics dict), dict "board|model" -> list of (topic, part -> t63)).
    """
    steady, trans = {}, {}
    for p in sorted(Path(folder).glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        for k, v in d.get("records", {}).items():
            steady.setdefault(k, []).append((p.stem, v.get("metrics", {})))
        for k, v in d.get("transients", {}).items():
            trans.setdefault(k, []).append((p.stem, v.get("t63", {})))
    return steady, trans


def coverage(base, new, pending_dir):
    """!
    @brief Classify every shifted number between two result sets against the pending-shift files.
    @param base Earlier result set.
    @param new Result set under test.
    @param pending_dir Folder of the pending files.
    @return dict: counts (identical, last_bit, covered, unexplained), records_last_bit (int), records_covered (sorted keys), rows (hottest-point rows and unexplained rows), transients (rows).
    """
    steady, trans = load_pending(pending_dir)
    ia, ib = C.index(base), C.index(new)
    rows, counts = [], {"identical": 0, "last_bit": 0, "covered": 0, "unexplained": 0}
    records_last_bit, records_covered = set(), set()
    for k in sorted(set(ia) & set(ib)):
        board, model, cell, solver = k
        if solver != "direct" or ia[k]["status"] != "ok" or ib[k]["status"] != "ok":
            continue
        ma, mb = C.metrics_of(ia[k]), C.metrics_of(ib[k])
        key = f"{board}|{model}|{cell:g}"
        pend = steady.get(key, [])
        for name in sorted(set(ma) | set(mb)):
            va, vb = ma.get(name), mb.get(name)
            if va == vb:
                counts["identical"] += 1
                continue
            if va is None or vb is None:
                rows.append({"record": key, "metric": name, "class": "unexplained", "old": va, "new": vb})
                counts["unexplained"] += 1
                continue
            if same(va, vb):
                counts["last_bit"] += 1
                records_last_bit.add(key)
                continue
            hit = [t for t, m in pend if name in m and same(m[name], vb)]
            if hit:
                counts["covered"] += 1
                records_covered.add(key)
                rows.append({"record": key, "metric": name, "class": "covered", "old": va, "new": vb, "delta": vb - va, "topic": hit})
            else:
                counts["unexplained"] += 1
                rows.append({"record": key, "metric": name, "class": "unexplained", "old": va, "new": vb, "delta": vb - va})
    trows = []
    for t in C.transient_diff(base, new):
        if t["identical"]:
            continue
        if t["old"] is not None and t["new"] is not None and same(t["old"], t["new"]):
            counts["last_bit"] += 1
            continue
        hit = [tp for tp, m in trans.get(f"{t['board']}|{t['model']}", []) if t["part"] in m and same(m[t["part"]], t["new"])] if t["new"] is not None else []
        cls = "covered" if hit else "unexplained"
        counts[cls] += 1
        trows.append({"record": f"{t['board']}|{t['model']}|{t['part']}", "class": cls, "old": t["old"], "new": t["new"], "topic": hit})
    return {"counts": counts, "records_last_bit": len(records_last_bit), "records_covered": sorted(records_covered), "rows": rows, "transients": trows}


def main(argv=None):
    """!
    @brief Compare two result sets against the pending files.
    @param argv Argument list (default: sys.argv[1:]).
    @return int 0 when no shift is unexplained, 1 otherwise.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("base")
    ap.add_argument("new")
    ap.add_argument("--pending", default=str(ROOT.parents[1] / "tests" / "regression" / "data" / "pending"))
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    out = coverage(C.load_set(a.base), C.load_set(a.new), a.pending)
    counts = out["counts"]
    print(f"metrics: {counts}")
    print(f"records with a last-bit change: {out['records_last_bit']}; records covered by a pending file: {len(out['records_covered'])}")
    for r in out["rows"]:
        if r["class"] == "unexplained":
            print("UNEXPLAINED", r)
    for r in out["transients"]:
        print("time", r["class"], r["record"], r["old"], "->", r["new"], r["topic"])
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 1 if counts["unexplained"] else 0


if __name__ == "__main__":
    sys.exit(main())
