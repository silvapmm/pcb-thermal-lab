#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_compare_c1.py
@brief Rows C1, C2 and C6 of the FEM comparison campaign (validation 56.1, 56.2, 56.6): the steady solution of the six models (FVM, FDM, Lumped, Analytic, 3D solid, FEM) on the
       20 boards of the frozen suite at 2, 1 and 0.5 mm, hottest column rise, part means, surface read-out and heat balance, differences to the FEM and to the 3D solid.
@details It uses the harness of `tests/regression/regress_harness.py` as it is (steady runs only: no time to 63 %, no SOR), so the numbers are those the frozen numbers hold, with
         the FEM and the 3D solid on every board that fits the caps of the harness (FVM and FDM 400 000 unknowns, 3D solid 150 000, FEM 130 000 in the harness, 300 000 here: a board above a cap is
         skipped and listed, never forced).
         Run from the repository root, ONE job at a time:
         `.venv/bin/python -u releases/2.9.0/fem-campaign/scripts/study_compare_c1.py --dry-run`   (unknowns and caps, nothing is solved)
         `.venv/bin/python -u releases/2.9.0/fem-campaign/scripts/study_compare_c1.py run [--boards a,b] [--cells 2,1]`   (resumable: the file is rewritten after every board)
         `.venv/bin/python -u releases/2.9.0/fem-campaign/scripts/study_compare_c1.py refs`   (the independent layered 3D solver on the four reference boards, out/c1_refs.json, resumable)
         `.venv/bin/python releases/2.9.0/fem-campaign/scripts/study_compare_c1.py report`   (Markdown tables on stdout and in out/c1_report.md)
         The result set is `releases/2.9.0/fem-campaign/out/c1.json` (git-ignored). Every difference is signed, model minus reference, in K and as a share of the reference rise
         above the ambient; the read-out is the hottest column temperature of the field ('peak') unless the table says 'part mean' or 'surface'.
"""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = HERE.parent / "out"
RESULT = OUT / "c1.json"
REFS = OUT / "c1_refs.json"
MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d", "fem")
LABEL = {"fvm": "FVM", "fdm": "FDM", "lumped": "Lumped", "analytic": "Analytic", "solid3d": "3D solid", "fem": "FEM"}
CELLS = (2.0, 1.0, 0.5)
FEM_CAP = 300_000      # the harness caps the FEM at 130 000 unknowns; the campaign raises it to 300 000 (the 1 mm cell of the example board, about 2 GB by `memory.py`), so that the 1 mm column is complete


def tree_id():
    """!
    @brief The commit of the tree the numbers were measured on.
    @return str, the short commit hash with '+dirty' when the tree has uncommitted changes.
    """
    h = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", "pcbthermal"], capture_output=True, text=True).stdout.strip()
    return h + ("+dirty" if dirty else "")


def load_harness():
    """!
    @brief Import the regression harness of this tree (the program is the one of this checkout).
    @return tuple (regress_harness module, regress_boards module).
    """
    sys.path.insert(0, str(ROOT / "tests" / "regression"))
    import regress_harness as H
    import regress_boards as B
    return H, B


def dry_run(boards, cells):
    """!
    @brief Print the unknown counts of every board, model and cell with the cap that would skip it; nothing is solved.
    @param boards Board names.
    @param cells Cell sizes in mm.
    @return None.
    """
    H, B = load_harness()
    H.use_program(ROOT)
    caps = {"fvm": H.MAX_UNKNOWNS, "fdm": H.MAX_UNKNOWNS, "solid3d": H.SOLID_CAP, "fem": FEM_CAP}
    print("board, model, cell mm: unknowns (SKIP when above the cap)")
    for name in boards:
        problem = B.build(name)
        for model in ("fvm", "solid3d", "fem"):
            row = []
            for c in cells:
                n = H.unknowns_of(H.steady_problem(problem), model, c)
                row.append(f"{c:g} mm: {n}{' SKIP' if n is not None and n > caps[model] else ''}")
            print(f"{name:22s} {model:8s} " + "   ".join(row))


def run(boards, cells):
    """!
    @brief Run the steady suite for the six models (resumable) and write out/c1.json.
    @param boards Board names.
    @param cells Cell sizes in mm.
    @return None.
    """
    H, B = load_harness()
    OUT.mkdir(parents=True, exist_ok=True)
    original = H.run_one

    def run_one_with_fem_cap(problem, board, model, cell, max_unknowns=H.MAX_UNKNOWNS, solid_cap=H.SOLID_CAP, **kw):
        """!
        @brief The harness record with the campaign's FEM cap.
        @param problem A Problem.
        @param board Board name.
        @param model Model key.
        @param cell Cell size in mm.
        @param max_unknowns FVM and FDM cap.
        @param solid_cap 3D solid cap.
        @param kw Other arguments of the harness function.
        @return dict, the record.
        """
        return original(problem, board, model, cell, max_unknowns, solid_cap, fem_cap=FEM_CAP, **kw)

    H.run_one = run_one_with_fem_cap
    data = H.run_suite(ROOT, RESULT, "campaign-c1", boards=boards, models=MODELS, cells=cells, transients=False, sor=False, resume=True, log=print)
    data["campaign_tree"] = tree_id()
    RESULT.write_text(json.dumps(data, indent=1), encoding="utf-8")


def richardson(v2, v1, v05):
    """!
    @brief Limit of a cell sequence 2, 1 and 0.5 mm by Richardson extrapolation with the observed order.
    @param v2 Value at 2 mm.
    @param v1 Value at 1 mm.
    @param v05 Value at 0.5 mm.
    @return tuple (limit, order) or (None, None) when the sequence is not monotone or the order falls outside 0.3 to 3 (no claim then).
    """
    a, b = v2 - v1, v1 - v05
    if a * b <= 0 or abs(a) <= abs(b):
        return None, None
    p = math.log2(a / b)
    if not 0.3 <= p <= 3.0:
        return None, None
    return v05 - b / (2 ** p - 1.0), p


def refs():
    """!
    @brief Solve the four reference boards (`regress_boards.REFERENCE_SPECS`) with the independent layered 3D solver at 2, 1 and 0.5 mm (a pair already in the file is kept).
    @return None.
    """
    sys.path.insert(0, str(ROOT / "releases" / "regression-harness" / "lib"))
    import regress_refsolve as R
    H, B = load_harness()
    OUT.mkdir(parents=True, exist_ok=True)
    R.compute_references(B.REFERENCE_SPECS, CELLS, str(REFS), log=print)


def _rec(data):
    """!
    @brief Index the records by (board, model, cell).
    @param data Result set.
    @return dict.
    """
    return {(r["board"], r["model"], r["cell_mm"]): r for r in data["records"]}


def _rise(r):
    """!
    @brief Hottest column rise of a record.
    @param r Record.
    @return float rise in K, or None when the record has no number.
    """
    if r is None or r.get("status") != "ok" or r.get("t_max") is None:
        return None
    return r["t_max"] - r["ambient"]


def _pct(v, ref):
    """!
    @brief Signed difference as a share of the reference rise.
    @param v Rise of the model in K.
    @param ref Rise of the reference in K.
    @return str such as '+1.2' (percent) or '-' when a number is missing.
    """
    if v is None or ref is None or ref == 0:
        return "-"
    return f"{100.0 * (v - ref) / ref:+.1f}"


def report():
    """!
    @brief Print the Markdown tables of the campaign from out/c1.json.
    @return None.
    """
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    idx = _rec(data)
    boards = [b for b in data["boards"]]
    lines = [f"Tree {data.get('campaign_tree', '?')}, program {data['program']['version']}, harness `tests/regression/regress_harness.py`, steady runs, `{data['environment']['platform']}`.", ""]
    for cell in sorted({r["cell_mm"] for r in data["records"]}, reverse=True):
        lines += [f"### Hottest column rise [K] and difference to the FEM [% of the FEM rise], cell {cell:g} mm", "",
                  "| board | " + " | ".join(LABEL[m] for m in MODELS) + " |", "| :-- | " + " | ".join("--:" for _ in MODELS) + " |"]
        for b in boards:
            ref = _rise(idx.get((b, "fem", cell)))
            cells = []
            for m in MODELS:
                r = idx.get((b, m, cell))
                v = _rise(r)
                if v is None:
                    cells.append("skipped" if r is None or r["status"] == "skipped" else r["status"])
                elif m == "fem":
                    cells.append(f"{v:.3f}")
                else:
                    cells.append(f"{v:.3f} ({_pct(v, ref)})")
            lines.append(f"| {b} | " + " | ".join(cells) + " |")
        lines.append("")
    # the worst difference of each model to the FEM and to the 3D solid, per cell, over the boards where both exist
    lines += ["### Largest and mean absolute difference of the hottest column rise [% of the reference rise], over the boards where both numbers exist", "",
              "| cell mm | model | against | boards | mean abs | largest abs (board) | signed range |", "| --: | :-- | :-- | --: | --: | :-- | :-- |"]
    for cell in sorted({r["cell_mm"] for r in data["records"]}, reverse=True):
        for refm in ("fem", "solid3d"):
            for m in MODELS:
                if m == refm:
                    continue
                vals = []
                for b in boards:
                    v, ref = _rise(idx.get((b, m, cell))), _rise(idx.get((b, refm, cell)))
                    if v is not None and ref:
                        vals.append((100.0 * (v - ref) / ref, b))
                if vals:
                    w = max(vals, key=lambda t: abs(t[0]))
                    lines.append(f"| {cell:g} | {LABEL[m]} | {LABEL[refm]} | {len(vals)} | {sum(abs(t[0]) for t in vals) / len(vals):.2f} | {abs(w[0]):.2f} ({w[1]}) | {min(t[0] for t in vals):+.1f} to {max(t[0] for t in vals):+.1f} |")
    lines.append("")
    # part means (the column mean over the footprint of each part): more robust than the hottest cell, which can sit on a feature smaller than the cell
    lines += ["### Mean column rise under the first part [K] and difference to the FEM [% of the FEM value], cell 1 mm (the 'part mean' read-out of `analysis.heater_stats`)", "",
              "| board | " + " | ".join(LABEL[m] for m in MODELS) + " |", "| :-- | " + " | ".join("--:" for _ in MODELS) + " |"]
    for b in boards:
        def pm(m):
            """!
            @brief Part mean rise of the first part for one model at 1 mm.
            @param m Model key.
            @return float rise in K or None.
            """
            r = idx.get((b, m, 1.0))
            if r is None or r["status"] != "ok" or not r.get("parts") or r["parts"][0].get("t_mean") is None:
                return None
            return r["parts"][0]["t_mean"] - r["ambient"]
        ref_v = pm("fem")
        row = []
        for m in MODELS:
            v = pm(m)
            row.append("-" if v is None else (f"{v:.3f}" if m == "fem" else f"{v:.3f} ({_pct(v, ref_v)})"))
        lines.append(f"| {b} | " + " | ".join(row) + " |")
    lines.append("")
    # the independent layered 3D solver of tests/helpers/layered3d.py on the four boards that it can represent, solved on the same cell as the model
    ref_rise = json.loads(REFS.read_text(encoding="utf-8")) if REFS.exists() else {}
    if REFS.exists():
        ref = ref_rise
        lines += ["### Against the independent layered 3D solver (`tests/helpers/layered3d.py`, the same cell as the model), rise of the hottest top-copper cell under the source [% of the reference rise]", "",
                  "| board | cell mm | reference K | " + " | ".join(LABEL[m] for m in MODELS) + " |", "| :-- | --: | --: | " + " | ".join("--:" for _ in MODELS) + " |"]
        for b in ref:
            for c in sorted(ref[b], key=float, reverse=True):
                row = []
                for m in MODELS:
                    v = _rise(idx.get((b, m, float(c))))
                    row.append("skipped" if v is None else _pct(v, ref[b][c]))
                lines.append(f"| {b} | {c} | {ref[b][c]:.3f} | " + " | ".join(row) + " |")
        lines.append("")
    # the limit of the cell sequence of each model (Richardson with the observed order): from below for the FEM, from above for the finite volumes on a plain board
    lines += ["### Limit of the cell sequence 2, 1, 0.5 mm of the hottest column rise [K] (Richardson with the observed order p in brackets; '-' where a cell is skipped or the sequence is not monotone with an order between 0.3 and 3)", "",
              "| board | FVM | FDM | 3D solid | FEM | layered 3D reference (four boards) |", "| :-- | --: | --: | --: | --: | --: |"]
    for b in boards:
        row = []
        for m in ("fvm", "fdm", "solid3d", "fem", "ref"):
            if m == "ref":
                vals = [ref_rise.get(b, {}).get(f"{c:g}") for c in (2.0, 1.0, 0.5)] if REFS.exists() else [None] * 3
            else:
                vals = [_rise(idx.get((b, m, c))) for c in (2.0, 1.0, 0.5)]
            lim, p = richardson(*vals) if None not in vals else (None, None)
            row.append(f"{lim:.2f} ({p:.1f})" if lim is not None else "-")
        lines.append(f"| {b} | " + " | ".join(row) + " |")
    lines.append("")
    # every difference above 3 percent at 1 mm, with the warnings the run printed: warned or silent
    lines += ["### Differences above 3 % of the FEM rise at 1 mm and the warnings the run of that model printed (a count and the first words)", "",
              "| board | model | difference % | warnings of the run |", "| :-- | :-- | --: | :-- |"]
    for b in boards:
        ref_v = _rise(idx.get((b, "fem", 1.0)))
        for m in MODELS[:-1]:
            r = idx.get((b, m, 1.0))
            v = _rise(r)
            if v is None or not ref_v or abs(100 * (v - ref_v) / ref_v) <= 3.0:
                continue
            w = r.get("warnings") or []
            lines.append(f"| {b} | {LABEL[m]} | {100 * (v - ref_v) / ref_v:+.1f} | {len(w)}" + (": " + "; ".join(x[:60] for x in w[:3]) if w else " (silent)") + " |")
    lines.append("")
    # heat balance and skipped records
    lines += ["### Heat balance (power out / power in - 1, worst of the boards) and skipped records", "", "| model | worst balance error | records ok | skipped | errors |", "| :-- | --: | --: | --: | --: |"]
    for m in MODELS:
        rs = [r for r in data["records"] if r["model"] == m]
        bal = [abs(r["balance_error"]) for r in rs if r["status"] == "ok" and r.get("balance_error") is not None]
        lines.append(f"| {LABEL[m]} | {max(bal):.2e} | {sum(r['status'] == 'ok' for r in rs)} | {sum(r['status'] == 'skipped' for r in rs)} | {sum(r['status'] == 'error' for r in rs)} |" if bal else f"| {LABEL[m]} | - | 0 | {len(rs)} | 0 |")
    lines += ["", "Skipped or failed records:", ""]
    for r in data["records"]:
        if r["status"] != "ok":
            lines.append(f"* {r['board']}, {LABEL[r['model']]}, {r['cell_mm']:g} mm: {r['status']}, {r['reason'][:140]}")
    # surface read-out beside the column (C2): the top surface peak minus the column peak, and the part's own point, in K
    lines += ["", "### Surface read-out (C2): top-face surface peak minus column peak [K], cell 1 mm (where the model has a surface map)", "",
              "| board | " + " | ".join(LABEL[m] for m in MODELS) + " |", "| :-- | " + " | ".join("--:" for _ in MODELS) + " |"]
    for b in boards:
        row = []
        for m in MODELS:
            r = idx.get((b, m, 1.0))
            s = (r or {}).get("surface") if r and r["status"] == "ok" else None
            row.append(f"{s['top']['t_max'] - r['t_max']:+.2f}" if s and "top" in s and r.get("t_max") is not None else "-")
        lines.append(f"| {b} | " + " | ".join(row) + " |")
    lines += ["", "### Time of each record [s], cell 1 mm (one machine, information only)", "", "| board | " + " | ".join(LABEL[m] for m in MODELS) + " |", "| :-- | " + " | ".join("--:" for _ in MODELS) + " |"]
    for b in boards:
        row = []
        for m in MODELS:
            r = idx.get((b, m, 1.0))
            row.append(f"{r['seconds']:.1f} ({r['unknowns']})" if r and r["status"] == "ok" and r.get("seconds") is not None else "-")
        lines.append(f"| {b} | " + " | ".join(row) + " |")
    text = "\n".join(lines)
    (OUT / "c1_report.md").write_text(text, encoding="utf-8")
    print(text)


def main():
    """!
    @brief Command line of the study.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("mode", nargs="?", default="run", choices=("run", "refs", "report"))
    ap.add_argument("--dry-run", action="store_true", help="print the unknown counts and the caps, solve nothing")
    ap.add_argument("--boards", default="", help="comma list of board names (default: all)")
    ap.add_argument("--cells", default="2,1,0.5", help="comma list of cell sizes in mm")
    a = ap.parse_args()
    H, B = load_harness()
    boards = [b for b in a.boards.split(",") if b] or B.board_names()
    cells = tuple(float(c) for c in a.cells.split(","))
    if a.dry_run:
        dry_run(boards, cells)
    elif a.mode == "run":
        run(boards, cells)
    elif a.mode == "refs":
        refs()
    else:
        report()


if __name__ == "__main__":
    main()
