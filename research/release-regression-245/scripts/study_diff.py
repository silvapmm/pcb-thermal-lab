#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_diff.py
@brief Question: which numbers moved between two revisions, and is every shift explained by an item of the release? Diffs two result sets and classifies each shift against `reference/expected_shifts.json`.
@details Usage, from the repository root:

         .venv/bin/python research/release-regression-245/scripts/study_diff.py out/v2.4.4.json out/rc.json
         .venv/bin/python research/release-regression-245/scripts/study_diff.py out/v2.4.4.json out/rc.json --strict      # exit code 1 on an alarm

         Writes `out/diff_<base>_vs_<new>.json` (every shift with its class and rules) and `out/diff_<base>_vs_<new>.md` (the tables below) and prints the Markdown:
         the counts per class, the alarms (`unexplained`, `must_not_move`), the shift of the maximum temperature of every record that moved, the changes of the time to 63 %, the SOR
         sweeps, the checks each result set must satisfy by itself (the Lumped and Analytic cell clamp, SOR equal to direct, heat balance), the warnings added and removed, and the
         matrix of what each board should show (from the table). The classes are defined in `regress_classify.py`. A shift is never judged by this script beyond the table: a
         `to_be_explained` shift needs a study or a decision of the maintainer.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lib"))

import regress_classify as C                                                # noqa: E402


def matrix_markdown(table):
    """!
    @brief The per-board expectations of the table as Markdown.
    @param table The expected-shifts table.
    @return str.
    """
    lines = ["| Board | FVM | FDM | Lumped | Analytic | 3D solid |", "| :-- | :-- | :-- | :-- | :-- | :-- |"]
    for board, row in table.get("board_matrix", {}).items():
        if "all" in row:
            lines.append(f"| {board} | {row['all']} | | | | |")
        else:
            lines.append(f"| {board} | " + " | ".join(row.get(m, "") for m in ("fvm", "fdm", "lumped", "analytic", "solid3d")) + " |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    """!
    @brief Diff, classify, write and print.
    @param argv List of arguments (default: sys.argv[1:]).
    @return int exit code: 1 with --strict when there is an alarm or an internal check failed, else 0.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("base", help="result set of the earlier revision (out/v2.4.4.json)")
    ap.add_argument("new", help="result set of the revision under test (out/rc.json)")
    ap.add_argument("--table", default=str(ROOT / "reference" / "expected_shifts.json"))
    ap.add_argument("--strict", action="store_true", help="exit code 1 when there is an alarm or a failed check")
    a = ap.parse_args(argv)
    base, new = C.load_set(a.base), C.load_set(a.new)
    table = json.loads(Path(a.table).read_text(encoding="utf-8"))
    diff = C.diff_sets(base, new, table)
    sor = C.diff_sets(base, new, table, key="sor")
    trans = C.classify_transients(C.transient_diff(base, new), table)
    checks = {base["label"]: C.internal_checks(base), new["label"]: C.internal_checks(new)}
    out_dir = ROOT / "out"
    out_dir.mkdir(exist_ok=True)
    stem = f"diff_{base['label']}_vs_{new['label']}"
    (out_dir / f"{stem}.json").write_text(json.dumps({"diff": diff, "sor": sor, "transients": trans, "checks": checks}, indent=1), encoding="utf-8")

    md = [f"# {new['label']} ({new['program']['version']}) against {base['label']} ({base['program']['version']})", ""]
    if base.get("environment") != new.get("environment"):
        # 'identical' and must_not_move are exact float equality: another NumPy or SciPy moves the last digits (review: 79 false alarms with NumPy 2.3.5 / SciPy 1.16.3)
        md += [f"**Warning: the two sets were run in different environments** ({base.get('environment')} against {new.get('environment')}); run both in the same one.", ""]
    md += [
          C.markdown(diff, base["label"], new["label"]),
          "## The SOR runs (2 mm)", "", C.sor_table(base, new), f"Shifts of the SOR temperatures: {sor['summary']['counts']}", "",
          "## Time to 63 % of the steady resistance (first part)", "",
          "| Board | Model | Part | Old [s] | New [s] | Change | Class | Rules |", "| :-- | :-- | :-- | --: | --: | --: | :-- | :-- |"]
    for r in trans:
        if r["class"] != "identical":
            md.append(f"| {r['board']} | {r['model']} | {r['part']} | {r['old'] if r['old'] is not None else ''} | {r['new'] if r['new'] is not None else ''} | "
                      f"{('%+.2f %%' % (r['change'] * 100)) if r['change'] is not None else ''} | {r['class']} | {', '.join(r['rules'])} |")
    md.append(f"\nTime to 63 %: {sum(1 for r in trans if r['class'] == 'identical')} identical, {sum(1 for r in trans if r['class'] != 'identical')} changed.\n")
    bad_checks = 0
    md += ["## Checks that each set must satisfy by itself", "", "| Set | Check | Board | Model | Value | Ok |", "| :-- | :-- | :-- | :-- | --: | :-- |"]
    for label, items in checks.items():
        for c in items:
            if not c["ok"]:
                bad_checks += 1
                md.append(f"| {label} | {c['check']} | {c['board']} | {c['model']} | {c['value']:.3g} | NO |")
        md.append(f"| {label} | all {len(items)} checks | | | | {'yes' if all(c['ok'] for c in items) else 'NO'} |")
    md += ["", "## Warnings added and removed (texts only, not shifts)", ""]
    n = 0
    for e in diff["entries"]:
        if e["warnings_added"] or e["warnings_removed"]:
            n += 1
            md.append(f"* {e['board']} / {e['model']} / {e['cell_mm']:g} mm: " + "; ".join([f"+ {w[:110]}" for w in e["warnings_added"]] + [f"- {w[:110]}" for w in e["warnings_removed"]]))
    if not n:
        md.append("None.")
    md += ["", "## What each board should show (from `reference/expected_shifts.json`)", "", matrix_markdown(table)]
    if diff["missing"]["only_in_base"] or diff["missing"]["only_in_new"]:
        md += ["## Records present in one set only", "", f"Only in {base['label']}: {diff['missing']['only_in_base']}", f"Only in {new['label']}: {diff['missing']['only_in_new']}", ""]
    text = "\n".join(md)
    (out_dir / f"{stem}.md").write_text(text, encoding="utf-8")
    print(text)
    alarms = diff["summary"]["alarms"] + sor["summary"]["alarms"] + sum(1 for r in trans if r["class"] in C.ALARMS)
    print(f"\nalarms: {alarms}; failed checks: {bad_checks}; written to {out_dir / (stem + '.md')}")
    return 1 if (a.strict and (alarms or bad_checks)) else 0


if __name__ == "__main__":
    sys.exit(main())
