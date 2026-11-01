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
FIRST_NUMBER = 4                                                            # first figure number this script may use
CANONICAL = ("example_board", "plate_uniform", "plate_pad", "plate_vias", "t_outline")          # boards of the summary table
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
    # 02 and 03 belong to make_figures.py (shift map, error against the reference): numbers below FIRST_NUMBER are never given out here
    return fig_dir / f"fig_{max(max(nums) if nums else 0, FIRST_NUMBER - 1) + 1:02d}_{name}.png"


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


def changelog_section(text, version):
    """!
    @brief The section of one version in CHANGELOG.md, verbatim.
    @param text Content of CHANGELOG.md.
    @param version Version text such as "2.4.5" or "Unreleased".
    @return str (empty when the section is not found).
    """
    m = re.search(r"^## \[" + re.escape(version) + r"\].*?(?=^## \[|\Z)", text, re.S | re.M)
    return m.group(0).strip() if m else ""


def status_lines(diff):
    """!
    @brief Records whose status (ok, skipped, error) differs between the two sets.
    @param diff Output of diff_sets.
    @return list of str.
    """
    return [f"* {e['board']} / {e['model']} / {e['cell_mm']:g} mm: {e['status_old']} to {e['status_new']}" for e in diff["entries"] if e["status_old"] != e["status_new"]]


def build(base, new, table, fig_dir=None, level=1, changelog=None, link="../figures/"):
    """!
    @brief Build the chapter text (and the figure when a folder is given).
    @param base Earlier result set.
    @param new Result set under test.
    @param table The expected-shifts table of the new release, or None when the pair has no table (then no shift is classified and the CHANGELOG section is quoted instead).
    @param fig_dir Folder for the figure, or None for no figure.
    @param level Heading level of the chapter title (2 when the chapter is a part of a longer document).
    @param changelog Text of the CHANGELOG section of the new version, quoted verbatim when there is no table.
    @param link Path prefix of the figure in the Markdown link.
    @return tuple (markdown text, rows of the hottest-point table, figure path or None).
    """
    classified = table is not None
    if not classified:
        table = {"items": [], "rules": [], "must_not_move": [], "transients": {}}
    titles, rule_item = item_titles(table)
    diff = C.diff_sets(base, new, table)
    trans = C.classify_transients(C.transient_diff(base, new), table)
    rows = fill_rise(hottest_rows(diff, titles, rule_item), base)
    if not classified:
        for r in rows:
            r["class"], r["items"] = "not classified", "no table of expected shifts for this pair; see the CHANGELOG section below"
    ident = identical_records(base, new, diff)
    s = diff["summary"]
    bl, nl = vlabel(base), vlabel(new)
    md = [f"# Results of {nl} against {bl}", ""]
    if base.get("environment") != new.get("environment"):
        md += [f"**Warning: the two sets were run in different environments** ({base.get('environment')} against {new.get('environment')}); the last digits of the bit-identical test are not reliable.", ""]
    md += [f"Environment of the new set: {new.get('environment')}. Cells in the sets: {sorted({float(r['cell_mm']) for r in new.get('records', [])}, reverse=True)} mm.", "",
           f"Records compared: {s['identical_records'] + len(diff['entries'])} (skipped or failed in both: {s['skipped_in_both']}). Bit-identical in every number and in the warnings: {s['identical_records']}. "
           f"Hottest point moved: {len(rows)}." + (f" Alarms (unexplained, must-not-move, out of range): {s['alarms']}." if classified else " Alarms: not applicable, the pair has no table."), "",
           ]
    if classified:
        md += ["| Class of the shifted numbers (all metrics) | Count |", "| :-- | --: |"]
        md += [f"| {c} | {s['counts'].get(c, 0)} |" for c in C.CLASSES + ("warnings_only",)]
        md += ["", "## Items of the release", "", "| Item | What |", "| :-- | :-- |"] + [f"| {i} | {t} |" for i, t in titles.items()]
    else:
        md += ["No table of expected shifts exists for this pair, so no shift is classified here and none is explained by a cause of mine. What the maintainers recorded for the later version (CHANGELOG, verbatim):", "",
               "\n".join("> " + ln for ln in changelog.splitlines()) if changelog else "(no CHANGELOG section found)"]
    st = status_lines(diff)
    if st:
        md += ["", "## Records whose status changed (could run in one version and not in the other)", ""] + st
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
        md += ["", "## Figure", "", f"![shift of the hottest point]({link}{fig.name})", "",
               f"*Figure {fig.name[4:6]} (`figures/{fig.name}`): the shift of the hottest point of every record that moved, per board and model, one panel per cell size; symmetric-log axis, linear below {LINTHRESH_K} K.*"]
    if level > 1:
        md = [("#" * (level - 1) + x) if x.startswith("#") else x for x in md]
    return "\n".join(md) + "\n", rows, fig


def vlabel(result_set):
    """!
    @brief Short name of a result set in the tables: the program version, or the label for the unreleased tree.
    @param result_set A result set.
    @return str.
    """
    return result_set["label"] if result_set.get("tree_state") == "unreleased" else "v" + result_set["program"]["version"]


def summary_table(sets, boards, cell):
    """!
    @brief Hottest point of some boards in every version, per model.
    @param sets Result sets in version order.
    @param boards Board names.
    @param cell Cell size in mm.
    @return str (Markdown); a record that did not run shows its status instead of a number.
    """
    head = "| Board | Model | " + " | ".join(vlabel(x) for x in sets) + " |"
    lines = [head, "| :-- | :-- | " + " | ".join("--:" for _ in sets) + " |"]
    idx = [C.index(x) for x in sets]
    for b in boards:
        for m in MODELS:
            cells = []
            for ix in idx:
                r = ix.get((b, m, float(cell), "direct"))
                cells.append("not in set" if r is None else (f"{r['t_max']:.3f}" if r["status"] == "ok" and r.get("t_max") is not None else r["status"]))
            lines.append(f"| {b} | {m} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def pair_table(table, base, new):
    """!
    @brief The expected-shifts table when it was written for exactly this pair of program versions, else None.
    @param table The table (dict) or None.
    @param base Earlier result set.
    @param new Later result set.
    @return dict or None.
    """
    if table and table.get("baseline", "").lstrip("v") == base["program"]["version"] and str(table.get("target")) == new["program"]["version"] and new.get("tree_state") != "unreleased":
        return table
    return None


def build_history(sets, table, changelog_text, not_run, cell, fig_dir, notes, boards=CANONICAL, link="../figures/"):
    """!
    @brief The whole document: summary of the hottest point across all versions, then one chapter per consecutive pair, newest first.
    @param sets Result sets in version order (oldest first).
    @param table Table of expected shifts of one release (used for the pair it was written for) or None.
    @param changelog_text Text of CHANGELOG.md.
    @param not_run List of strings "version: reason" for versions the harness could not run.
    @param cell Cell size for the summary table in mm.
    @param fig_dir Folder for the figures or None.
    @param notes List of extra lines placed after the introduction (for example items still missing in the last tree).
    @param boards Boards of the summary table.
    @param link Path prefix of the figures in the Markdown links.
    @return str.
    """
    labels = [vlabel(x) for x in sets]
    md = ["# Results across program versions", "",
          "Every number comes from result sets of the regression harness (`research/release-regression-245`): the same 17 boards, five models, direct solver, run on each tag extracted with `git archive`; "
          "nothing is estimated. A shift is explained only when the table of expected shifts of that release links it to an item; otherwise the CHANGELOG section of the later version is quoted and the shift is left unclassified.", ""]
    md += [f"Versions compared (oldest first): {', '.join(labels)}.", ""]
    if not_run:
        md += ["## Versions the harness could not run", ""] + [f"* {x}" for x in not_run] + [""]
    md += notes + [""] if notes else []
    md += [f"## Hottest point of canonical boards across versions (cell {cell:g} mm, degC)", "",
           summary_table(sets, boards, cell)]
    for a, b in reversed(list(zip(sets[:-1], sets[1:]))):
        unreleased = b.get("tree_state") == "unreleased"
        ch = changelog_section(changelog_text, "Unreleased" if unreleased else b["program"]["version"])
        text, _rows, _fig = build(a, b, pair_table(table, a, b), fig_dir, level=2, changelog=ch, link=link)
        md.append(text)
    return "\n".join(md)


def main(argv=None):
    """!
    @brief Read the two sets and the table, write the chapter and the figure.
    @param argv List of arguments (default: sys.argv[1:]).
    @return int exit code (0).
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("sets", nargs="+", help="result sets, oldest first (two for one pair; more for a chain of consecutive pairs with a summary)")
    ap.add_argument("--changelog", default=str(ROOT.parents[1] / "CHANGELOG.md"), help="CHANGELOG.md, quoted for the pairs that have no table")
    ap.add_argument("--not-run", action="append", default=[], help="'version: reason' for a version the harness could not run (chain mode, repeatable)")
    ap.add_argument("--note", action="append", default=[], help="extra line for the introduction (chain mode, repeatable)")
    ap.add_argument("--summary-cell", type=float, default=1.0, help="cell size of the summary table in mm")
    ap.add_argument("--unreleased-last", action="store_true", help="the last set is the current tree (unreleased): its pair gets no table")
    ap.add_argument("--table", default=str(ROOT / "reference" / "expected_shifts.json"), help="table of expected shifts of the later version")
    ap.add_argument("--out", default=None, help="Markdown output (default out/version_comparison_<base>_vs_<new>.md)")
    ap.add_argument("--fig-dir", default=str(ROOT / "figures"))
    ap.add_argument("--link", default="../figures/", help="path prefix of the figures in the Markdown (for a file in docs/: ../research/release-regression-245/figures/)")
    ap.add_argument("--no-figure", action="store_true")
    a = ap.parse_args(argv)
    sets = [C.load_set(x) for x in a.sets]
    if len(sets) < 2:
        ap.error("give at least two result sets")
    if a.unreleased_last:
        sets[-1]["tree_state"] = "unreleased"
    table = json.loads(Path(a.table).read_text(encoding="utf-8"))
    fig_dir = None if a.no_figure else a.fig_dir
    if len(sets) == 2 and not a.unreleased_last:
        base, new = sets
        text, rows, fig = build(base, new, table, fig_dir)
        out = Path(a.out) if a.out else ROOT / "out" / f"version_comparison_{slug(base['label'])}_vs_{slug(new['label'])}.md"
    else:
        cl = Path(a.changelog).read_text(encoding="utf-8") if Path(a.changelog).exists() else ""
        text, rows, fig = build_history(sets, table, cl, a.not_run, a.summary_cell, fig_dir, a.note, link=a.link), [], None
        out = Path(a.out) if a.out else ROOT / "out" / "version-comparison.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"written {out} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
