#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_tighten_table.py
@brief Question: how large is each shift that a rule of the table explains on the reviewed run, and what is the tight bound per board and model? Writes the `limits` of every rule from two result sets.
@details The general bound of a rule is the hypothesis of the documents (for example 45 % of the rise for the laminate rule); on most boards the reviewed candidate moves far less
         (0.3 K on the example board), so a general bound would hide a defect of the same size as the release items. This script measures, for every rule and every
         board and model in its scope, the largest shift that the rule matched (temperatures in K, unknown counts as a fraction, the heat balance in W) and writes
         `limits` = margin x measured, with a floor, into a copy of the table (with the sign of every temperature shift above the floor: a later shift
         of more than the floor the other way is out of range); the may_move entries of the times to 63 % get `limits` on the relative change.
         Usage, from the repository root (the full sets, so that every cell is covered):

         .venv/bin/python research/release-regression-245/scripts/study_tighten_table.py out/v2.4.4-full.json out/rc-full.json --out reference/expected_shifts.json

         Run it once on the reviewed candidate, read the printed table (every limit with what it was measured from) and commit the table; the next diff then alarms on any shift
         that is larger than the reviewed one by more than the margin, or that goes the other way.
"""

import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lib"))

import regress_classify as C                                                # noqa: E402

MARGIN = 1.25                    # limit = MARGIN x the measured shift (per board, model and cell)
FLOOR = {"abs_k": 0.05, "rel": 0.001, "abs_w": 1e-9, "rel_change": 0.01}    # a rule that matched only tiny shifts still allows this much


def _up(x):
    """!
    @brief Round a positive bound up to two significant digits (so that the table reads cleanly and the bound stays above the value).
    @param x Positive number.
    @return float.
    """
    if x <= 0:
        return 0.0
    e = math.floor(math.log10(x)) - 1
    return float(f"{math.ceil(round(x / 10 ** e, 9)) * 10 ** e:.12g}")           # the text form drops binary noise such as 4.800000000000001


def measure(base, new, table):
    """!
    @brief Largest shift that each quantified rule matched, per (rule id, "board|model", bound key).
    @param base Earlier result set.
    @param new Result set under test.
    @param table The expected-shifts table.
    @return tuple (sizes, signs): sizes {(rule id, "board|model|cell", key): largest size}; signs {(rule id, "board|model|cell"): {metric: sign}} of the temperature
            shifts larger than the floor.
    """
    out, signs = {}, {}
    for key in ("records", "sor"):
        a, b = C.index(base, key), C.index(new, key)
        for k in set(a) & set(b):
            ra, rb = a[k], b[k]
            board, model, cell, solver = k
            mname = model if solver == "direct" else f"{model}_{solver}"
            ma, mb = C.metrics_of(ra), C.metrics_of(rb)
            for name in set(ma) & set(mb):
                if ma[name] == mb[name]:
                    continue
                group = C.metric_group(name)
                if group == "temperature":
                    bk, size = "abs_k", abs(mb[name] - ma[name])
                elif group == "count":
                    bk, size = "rel", abs(mb[name] - ma[name]) / abs(ma[name]) if ma[name] else 0.0
                elif group == "balance":
                    bk, size = "abs_w", abs(mb[name] - ma[name])
                else:
                    continue                                                # field checksums are not bounded
                for r in table["rules"]:
                    if r.get("status") != "to be explained" and C.scope_matches(r, board, mname, cell, name):
                        kk = (r["id"], C.limit_key(board, mname, cell), bk)
                        out[kk] = max(out.get(kk, 0.0), size)
                        if bk == "abs_k" and size > FLOOR["abs_k"]:
                            signs.setdefault(kk[:2], {})[name] = 1 if mb[name] > ma[name] else -1
    return out, signs


def tighten(base, new, table, margin=MARGIN):
    """!
    @brief Copy of the table with `limits` on every quantified or derived rule (every board, model and cell of its scope) and on every may_move entry of the transients.
    @param base Earlier result set.
    @param new Result set under test.
    @param table The expected-shifts table.
    @param margin Factor on the largest measured shift.
    @return tuple (new table, list of printable lines).
    """
    t = json.loads(json.dumps(table))
    meas, signs = measure(base, new, table)
    boards_run = {r["board"] for r in new["records"]}
    cells = sorted({float(r["cell_mm"]) for r in new["records"]}, reverse=True)
    lines = []
    for r in t["rules"]:
        if r.get("status") == "to be explained":
            continue
        groups = set()
        mets = r.get("metrics", "*")
        for g, bk in (("temperature", "abs_k"), ("count", "rel"), ("balance", "abs_w")):
            if mets == "*" or g in mets or any(C.metric_group(m.replace("*", "x")) == g for m in mets if m not in C.GROUPS):
                groups.add(bk)
        boards = sorted(boards_run) if r["boards"] == "*" else r["boards"]
        models = r["models"] if r["models"] != "*" else ["fvm", "fdm", "lumped", "analytic", "solid3d"]
        limits = {}
        for b in boards:
            for m in models:
                for c in cells:
                    bm = C.limit_key(b, m, c)
                    lim = {}
                    for bk in sorted(groups):
                        v = meas.get((r["id"], bm, bk), 0.0)
                        lim[bk] = [0, _up(max(FLOOR[bk], margin * v))]
                        if v:
                            lines.append(f"{r['id']:4s} {bm:34s} {bk:6s} measured {v:.4g} -> limit {lim[bk][1]:.4g}")
                    sg = signs.get((r["id"], bm))
                    if sg:
                        lim["signs"] = dict(sorted(sg.items()))                 # each temperature that moved by more than the floor: the way it went (the other way is an alarm)
                    limits[bm] = lim
        r["limits"] = limits
    rows = C.transient_diff(base, new)
    for e in t.get("transients", {}).get("may_move", []):
        limits = {}
        for row in rows:
            if row["change"] is not None and C.scope_matches(e, row["board"], row["model"], 0.0, "t63"):
                bm = f"{row['board']}|{row['model']}"
                limits[bm] = max(limits.get(bm, 0.0), abs(row["change"]))
        e["limits"] = {bm: [0, _up(max(FLOOR["rel_change"], margin * v))] for bm, v in sorted(limits.items())}
        e["rel_change"] = [0, FLOOR["rel_change"]]                          # a board of the entry that did not move on the reviewed run may move by 1 % at most
        for bm, v in sorted(limits.items()):
            lines.append(f"{e['id']:4s} {bm:30s} t63    measured {v:.4g} -> limit {e['limits'][bm][1]:.4g}")
    return t, lines


def dump(table):
    """!
    @brief The table as JSON text with one rule or entry per line (readable diffs).
    @param table The table.
    @return str.
    """
    parts = ["{"]
    keys = list(table)
    for i, k in enumerate(keys):
        v = table[k]
        end = "," if i < len(keys) - 1 else ""
        if isinstance(v, list) and v and isinstance(v[0], dict):
            parts.append(f'  {json.dumps(k)}: [')
            parts += [f"    {json.dumps(x)}" + ("," if j < len(v) - 1 else "") for j, x in enumerate(v)]
            parts.append(f"  ]{end}")
        elif isinstance(v, dict):
            parts.append(f'  {json.dumps(k)}: {{')
            sub = list(v)
            for j, sk in enumerate(sub):
                sv = v[sk]
                if isinstance(sv, list):
                    parts.append(f'    {json.dumps(sk)}: [')
                    parts += [f"      {json.dumps(x)}" + ("," if jj < len(sv) - 1 else "") for jj, x in enumerate(sv)]
                    parts.append("    ]" + ("," if j < len(sub) - 1 else ""))
                else:
                    parts.append(f"    {json.dumps(sk)}: {json.dumps(sv)}" + ("," if j < len(sub) - 1 else ""))
            parts.append(f"  }}{end}")
        else:
            parts.append(f"  {json.dumps(k)}: {json.dumps(v)}{end}")
    parts.append("}")
    return "\n".join(parts) + "\n"


def main(argv=None):
    """!
    @brief Measure, tighten, print and write.
    @param argv List of arguments (default: sys.argv[1:]).
    @return int exit code 0.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("base", help="result set of the earlier revision (full set)")
    ap.add_argument("new", help="result set of the reviewed candidate (full set)")
    ap.add_argument("--table", default=str(ROOT / "reference" / "expected_shifts.json"))
    ap.add_argument("--out", required=True, help="where to write the table with the limits")
    ap.add_argument("--margin", type=float, default=MARGIN)
    a = ap.parse_args(argv)
    table = json.loads(Path(a.table).read_text(encoding="utf-8"))
    t, lines = tighten(C.load_set(a.base), C.load_set(a.new), table, a.margin)
    print("\n".join(lines))
    Path(a.out).write_text(dump(t), encoding="utf-8")
    print(f"written to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
