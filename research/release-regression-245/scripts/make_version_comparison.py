#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_version_comparison.py
@brief Question: how do the results of the program differ between two versions, board by board and model by model? Writes a Markdown chapter and a figure from two result sets and the table of expected shifts.
@details Usage, from the repository root:

         .venv/bin/python research/release-regression-245/scripts/make_version_comparison.py out/v2.4.4.json out/v2.4.5.json \\
                 --table research/release-regression-245/reference/expected_shifts_2.4.5.json

         The inputs are two result sets written by `study_baseline_release.py` / `study_run_suite.py` (the tag runs of the harness). Everything printed is read from them:
         the hottest point before and after, the shift in K and in percent of the old rise over the ambient, the item of the release that the table links to the shift (rule to item),
         the records that are bit-identical, the times to 63 % that moved and the warning texts that changed. Nothing is estimated. The classification is the one of `regress_classify.py`
         (the same as `study_diff.py`). The chapter goes to `out/version_comparison_<base>_vs_<new>.md` (git-ignored) and the figure to `figures/fig_NN_version_shift_<base>_<new>.png`
         (NN is the next free number of the folder, reused when the file already exists). The frozen files `reference/v*.json` hold one revision only (no earlier value to compare), so
         a comparison needs two result sets.
"""

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lib"))

import matplotlib                                                           # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402

import regress_classify as C                                                # noqa: E402

MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")
MARKERS = {"fvm": "o", "fdm": "s", "lumped": "^", "analytic": "v", "solid3d": "D"}
LINTHRESH_K = 0.01                                                          # below this the symlog axis is linear: shifts under 0.01 K are drawn on a linear stretch


def item_titles(table):
    """!
    @brief Titles of the release items and the item of each rule.
    @param table The expected-shifts table.
    @return tuple (item id -> title, rule id -> item id).
    """
    titles = {i["id"]: i.get("title", "") for i in table.get("items", [])}
    rule_item = {r["id"]: r.get("item", "") for r in table.get("rules", [])}
    return titles, rule_item


def explain(rules, titles, rule_item):
    """!
    @brief Text naming the items of the release behind a list of rule ids.
    @param rules List of rule ids from the classification.
    @param titles Item id to title.
    @param rule_item Rule id to item id.
    @return str, for example "I3 Laminate nodes; I4 Point via" (rule ids of must_not_move entries are shown as they are).
    """
    out = []
    for rid in rules:
        iid = rule_item.get(rid, rid)
        text = f"{iid} {titles[iid]}" if iid in titles else str(iid)
        if text not in out:
            out.append(text)
    return "; ".join(out)


def hottest_rows(diff, titles, rule_item):
    """!
    @brief One row per record whose hottest point moved.
    @param diff Output of regress_classify.diff_sets.
    @param titles Item id to title.
    @param rule_item Rule id to item id.
    @return list of dicts: board, model, cell, old, new, shift_k, shift_pct, class, items, rise_k (rise over the ambient of the old hottest point, K).
    """
    rows = []
    for e in diff["entries"]:
        tm = next((m for m in e["metrics"] if m["name"] == "t_max"), None)
        if tm is None or tm["delta"] is None:
            continue
        # The ambient is not in the entry; the classification keeps the rise only inside, so it is recovered by the caller through `ambient` (see fill_rise)
        rows.append({"board": e["board"], "model": e["model"], "cell": e["cell_mm"], "old": tm["old"], "new": tm["new"], "shift_k": tm["delta"], "class": tm["class"],
                     "items": explain(tm["rules"], titles, rule_item), "note": tm.get("note", "")})
    return rows


def fill_rise(rows, base):
    """!
    @brief Add the rise of the old hottest point over the ambient and the shift as a percent of it.
    @param rows Rows of hottest_rows (changed in place).
    @param base Earlier result set (holds the ambient of every record).
    @return The same list.
    """
    idx = {(r["board"], r["model"], float(r["cell_mm"])): r for r in base.get("records", []) if r.get("solver", "direct") == "direct"}
    for row in rows:
        rec = idx.get((row["board"], row["model"], float(row["cell"])))
        amb = rec.get("ambient") if rec else None
        rise = (row["old"] - amb) if amb is not None else None
        row["rise_k"] = rise
        row["shift_pct"] = (100.0 * row["shift_k"] / rise) if rise else None
    return rows


def identical_records(base, new, diff):
    """!
    @brief Records whose numbers are bit-identical in both sets (a change of warning texts alone does not count as a shift).
    @param base Earlier result set.
    @param new Result set under test.
    @param diff Output of diff_sets.
    @return dict board -> list of (model, cell) that are identical, ok in both.
    """
    moved = {(e["board"], e["model"], float(e["cell_mm"])) for e in diff["entries"] if e["metrics"]}
    a, b = C.index(base), C.index(new)
    out = {}
    for k in sorted(set(a) & set(b)):
        board, model, cell, solver = k
        if solver != "direct" or a[k]["status"] != "ok" or b[k]["status"] != "ok":
            continue
        if (board, model, cell) not in moved:
            out.setdefault(board, []).append((model, cell))
    return out


def fmt(x, digits=4, sign=False):
    """!
    @brief Number for a table cell.
    @param x Number or None.
    @param digits Decimals.
    @param sign True to show the sign.
    @return str.
    """
    if x is None:
        return ""
    return f"{x:+.{digits}f}" if sign else f"{x:.{digits}f}"


def hottest_table(rows):
    """!
    @brief Markdown table of the hottest-point shifts, sorted by cell, board, model.
    @param rows Rows of hottest_rows with the rise filled in.
    @return str.
    """
    lines = ["| Board | Model | Cell [mm] | Tmax old [degC] | Tmax new [degC] | Shift [K] | Shift [% of old rise] | Class | Item of the release |",
             "| :-- | :-- | --: | --: | --: | --: | --: | :-- | :-- |"]
    for r in sorted(rows, key=lambda r: (-r["cell"], r["board"], r["model"])):
        lines.append(f"| {r['board']} | {r['model']} | {r['cell']:g} | {fmt(r['old'])} | {fmt(r['new'])} | {fmt(r['shift_k'], 4, True)} | {fmt(r['shift_pct'], 2, True)} | {r['class']} | {r['items']} |")
    return "\n".join(lines) + "\n"


def transient_table(trans):
    """!
    @brief Markdown table of the times to 63 % that moved.
    @param trans Output of classify_transients.
    @return str.
    """
    moved = [t for t in trans if t["class"] != "identical"]
    if not moved:
        return "None: every time to 63 % is identical.\n"
    lines = ["| Board | Model | Part | Old [s] | New [s] | Change [%] | Class | Rules |", "| :-- | :-- | :-- | --: | --: | --: | :-- | :-- |"]
    for t in moved:
        ch = f"{t['change'] * 100:+.2f}" if t["change"] is not None else ""
        lines.append(f"| {t['board']} | {t['model']} | {t['part']} | {fmt(t['old'])} | {fmt(t['new'])} | {ch} | {t['class']} | {', '.join(t['rules'])} |")
    return "\n".join(lines) + f"\n\n{len(moved)} of {len(trans)} times changed; {len(trans) - len(moved)} are identical.\n"


def warning_lines(diff):
    """!
    @brief The warning texts added and removed, one line per record.
    @param diff Output of diff_sets.
    @return list of str.
    """
    out = []
    for e in diff["entries"]:
        if e["warnings_added"] or e["warnings_removed"]:
            parts = [f"added: {w}" for w in e["warnings_added"]] + [f"removed: {w}" for w in e["warnings_removed"]]
            out.append(f"* {e['board']} / {e['model']} / {e['cell_mm']:g} mm: " + " | ".join(parts))
    return out


def slug(label):
    """!
    @brief File-name part of a label.
    @param label Result set label such as "v2.4.4-q".
    @return str of letters, digits and dots.
    """
    return re.sub(r"[^A-Za-z0-9.]+", "_", label)


def figure_path(fig_dir, name):
    """!
    @brief Path of the figure: the number of an existing file with the same name part, else the next free number of the folder.
    @param fig_dir Folder of the figures.
    @param name Name part after the number, without extension.
    @return Path.
    """
    fig_dir = Path(fig_dir)
    fig_dir.mkdir(parents=True, exist_ok=True)
    nums = []
    for p in fig_dir.glob("fig_*.png"):
        m = re.match(r"fig_(\d+)_(.*)\.png$", p.name)
        if m:
            if m.group(2) == name:
                return p
            nums.append(int(m.group(1)))
    return fig_dir / f"fig_{(max(nums) if nums else 0) + 1:02d}_{name}.png"


def draw_figure(rows, path, base_label, new_label):
    """!
    @brief Shift of the hottest point per board and model, one panel per cell size, on a symmetric-log axis.
    @param rows Rows of hottest_rows (records whose hottest point moved).
    @param path Output PNG.
    @param base_label Label of the earlier set.
    @param new_label Label of the set under test.
    @return None (writes the file).
    """
    cells = sorted({r["cell"] for r in rows}, reverse=True)
    boards = sorted({r["board"] for r in rows})
    fig, axes = plt.subplots(1, max(1, len(cells)), figsize=(4.6 * max(1, len(cells)) + 1.5, 0.32 * max(6, len(boards)) + 2.2), sharey=True, squeeze=False)
    for ax, cell in zip(axes[0], cells):
        for m in MODELS:
            pts = [(r["shift_k"], boards.index(r["board"])) for r in rows if r["cell"] == cell and r["model"] == m]
            if pts:
                ax.scatter([p[0] for p in pts], [p[1] for p in pts], marker=MARKERS[m], s=34, label=m, alpha=0.85)
        ax.set_xscale("symlog", linthresh=LINTHRESH_K)
        ax.axvline(0, color="grey", lw=0.8)
        ax.set_title(f"cell {cell:g} mm")
        ax.set_xlabel(f"shift of the hottest point [K]\n(symlog, linear below {LINTHRESH_K} K)")
        ax.set_yticks(range(len(boards)))
        ax.set_yticklabels(boards)
        ax.grid(True, alpha=0.3)
    axes[0][0].legend(fontsize=8, loc="best", title="model")
    fig.suptitle(f"{new_label} minus {base_label}: only the records whose hottest point moved (bit-identical records are not drawn)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def build(base, new, table, fig_dir=None):
    """!
    @brief Build the chapter text (and the figure when a folder is given).
    @param base Earlier result set.
    @param new Result set under test.
    @param table The expected-shifts table of the new release.
    @param fig_dir Folder for the figure, or None for no figure.
    @return tuple (markdown text, rows of the hottest-point table, figure path or None).
    """
    titles, rule_item = item_titles(table)
    diff = C.diff_sets(base, new, table)
    trans = C.classify_transients(C.transient_diff(base, new), table)
    rows = fill_rise(hottest_rows(diff, titles, rule_item), base)
    ident = identical_records(base, new, diff)
    s = diff["summary"]
    bl, nl = base["label"], new["label"]
    md = [f"# Results of {nl} (program {new['program']['version']}) against {bl} (program {base['program']['version']})", ""]
    if base.get("environment") != new.get("environment"):
        md += [f"**Warning: the two sets were run in different environments** ({base.get('environment')} against {new.get('environment')}); the last digits of the bit-identical test are not reliable.", ""]
    md += [f"Environment of the new set: {new.get('environment')}. Cells in the sets: {sorted({float(r['cell_mm']) for r in new.get('records', [])}, reverse=True)} mm.", "",
           f"Records compared: {s['identical_records'] + len(diff['entries'])} (skipped or failed in both: {s['skipped_in_both']}). Bit-identical in every number and in the warnings: {s['identical_records']}. "
           f"Hottest point moved: {len(rows)}. Alarms (unexplained, must-not-move, out of range): {s['alarms']}.", "",
           "| Class of the shifted numbers (all metrics) | Count |", "| :-- | --: |"]
    md += [f"| {c} | {s['counts'].get(c, 0)} |" for c in C.CLASSES + ("warnings_only",)]
    md += ["", "## Items of the release", "", "| Item | What |", "| :-- | :-- |"] + [f"| {i} | {t} |" for i, t in titles.items()]
    md += ["", "## Hottest point, every record that moved", "",
           "The shift in percent is relative to the rise of the old hottest point over the ambient of the record. The item is the one the table of expected shifts links to the shift.", "", hottest_table(rows)]
    other = [e for e in diff["entries"] if e["metrics"] and not any(m["name"] == "t_max" for m in e["metrics"])]
    md += [f"Records where the hottest point is the same but another number moved (layer mean, a part, the unknowns, the heat split): {len(other)}.", ""]
    for e in other[:60]:
        names = ", ".join(sorted({m["name"] for m in e["metrics"]})[:6])
        md.append(f"* {e['board']} / {e['model']} / {e['cell_mm']:g} mm: {names}")
    md += ["", "## Bit-identical records (steady state, status ok in both)", ""]
    for board, lst in sorted(ident.items()):
        by = {}
        for model, cell in lst:
            by.setdefault(model, []).append(f"{cell:g}")
        md.append(f"* {board}: " + "; ".join(f"{m} ({', '.join(c)} mm)" for m, c in sorted(by.items())))
    md += ["", "## Time to 63 % of the steady resistance that moved", "", transient_table(trans), "## Warning texts that changed", ""]
    w = warning_lines(diff)
    md += w if w else ["None."]
    fig = None
    if fig_dir is not None and rows:
        fig = figure_path(fig_dir, f"version_shift_{slug(bl)}_vs_{slug(nl)}")
        draw_figure(rows, fig, bl, nl)
        md += ["", "## Figure", "", f"![shift of the hottest point](../figures/{fig.name})", "",
               f"*Figure {fig.name[4:6]} (`figures/{fig.name}`): the shift of the hottest point of every record that moved, per board and model, one panel per cell size; symmetric-log axis, linear below {LINTHRESH_K} K.*"]
    return "\n".join(md) + "\n", rows, fig


def main(argv=None):
    """!
    @brief Read the two sets and the table, write the chapter and the figure.
    @param argv List of arguments (default: sys.argv[1:]).
    @return int exit code (0).
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("base", help="result set of the earlier version (out/v2.4.4.json)")
    ap.add_argument("new", help="result set of the later version (out/v2.4.5.json)")
    ap.add_argument("--table", default=str(ROOT / "reference" / "expected_shifts.json"), help="table of expected shifts of the later version")
    ap.add_argument("--out", default=None, help="Markdown output (default out/version_comparison_<base>_vs_<new>.md)")
    ap.add_argument("--fig-dir", default=str(ROOT / "figures"))
    ap.add_argument("--no-figure", action="store_true")
    a = ap.parse_args(argv)
    base, new = C.load_set(a.base), C.load_set(a.new)
    table = json.loads(Path(a.table).read_text(encoding="utf-8"))
    text, rows, fig = build(base, new, table, None if a.no_figure else a.fig_dir)
    out = Path(a.out) if a.out else ROOT / "out" / f"version_comparison_{slug(base['label'])}_vs_{slug(new['label'])}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"written {out} ({len(rows)} rows)" + (f" and {fig}" if fig else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
