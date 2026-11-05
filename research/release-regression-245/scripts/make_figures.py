#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the release regression, drawn from the result sets in `out/`: the shift of the hottest point of every board and model, coloured by class (fig_02), and the error of each model against the independent solver before and after (fig_03).
@details Usage, from the repository root, after `study_diff.py` and `study_references.py`:

         .venv/bin/python research/release-regression-245/scripts/make_figures.py out/v2.4.4.json out/rc.json [--cell 1.0]

         Files: fig_02_shift_map.png, fig_03_error_vs_reference.png (figures 01 is the flow diagram of make_diagrams.py). Nothing is drawn that the result sets do not hold.

         The result sets are not committed (they are git-ignored in out/), so the committed figure is fig_04_frozen_times.png, drawn from the frozen reference file alone:

             .venv/bin/python research/release-regression-245/scripts/make_figures.py --frozen research/release-regression-245/reference/v2.4.5.json
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "lib"))

import matplotlib                                                           # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402
import numpy as np                                                          # noqa: E402

import regress_classify as C                                                # noqa: E402
import regress_refsolve as R                                                # noqa: E402

OUT = ROOT / "figures"
COLORS = {"expected": "#2ca02c", "expected_out_of_range": "#ff7f0e", "to_be_explained": "#bcbd22", "unexplained": "#d62728", "must_not_move": "#8c0000", "identical": "#dddddd"}
MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")


def shift_map(base, new, table, cell):
    """!
    @brief Matrix board x model of the shift of the hottest point at one cell size, each square coloured by its class.
    @param base Earlier result set.
    @param new Result set under test.
    @param table Expected-shifts table.
    @param cell Cell size in mm.
    @return None (writes fig_02_shift_map.png).
    """
    diff = C.diff_sets(base, new, table)
    boards = list(new["boards"])
    cls, val = {}, {}
    for e in diff["entries"]:
        if abs(e["cell_mm"] - cell) > 1e-9:
            continue
        for m in e["metrics"]:
            if m["name"] == "t_max":
                cls[(e["board"], e["model"])], val[(e["board"], e["model"])] = m["class"], m["delta"]
    fig, ax = plt.subplots(figsize=(8, 0.45 * len(boards) + 1.6))
    for i, b in enumerate(boards):
        for j, m in enumerate(MODELS):
            k = (b, m)
            c = cls.get(k, "identical")
            ax.add_patch(plt.Rectangle((j, -i - 1), 0.95, 0.9, facecolor=COLORS[c], edgecolor="k", linewidth=0.4))
            if k in val and val[k] is not None:
                ax.text(j + 0.475, -i - 0.55, f"{val[k]:+.2f}", ha="center", va="center", fontsize=7)
    ax.set_xlim(0, len(MODELS))
    ax.set_ylim(-len(boards) - 0.2, 0)
    ax.set_xticks([j + 0.475 for j in range(len(MODELS))])
    ax.set_xticklabels(MODELS)
    ax.set_yticks([-i - 0.55 for i in range(len(boards))])
    ax.set_yticklabels(boards, fontsize=8)
    ax.set_title(f"Shift of the hottest point [K], cell {cell:g} mm: {new['label']} against {base['label']}", fontsize=9)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, facecolor=v, edgecolor="k") for v in COLORS.values()], labels=list(COLORS), fontsize=7, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_shift_map.png", dpi=105)
    plt.close(fig)


def error_bars(base, new, refs):
    """!
    @brief Error of the rise against the independent solver, before and after, for the reference boards at each cell size.
    @param base Earlier result set.
    @param new Result set under test.
    @param refs Output of regress_refsolve.compute_references.
    @return None (writes fig_03_error_vs_reference.png).
    """
    eb = {(e["board"], e["model"], e["cell_mm"]): e["error"] * 100 for e in R.errors(base, refs)}
    ea = {(e["board"], e["model"], e["cell_mm"]): e["error"] * 100 for e in R.errors(new, refs)}
    boards = sorted({k[0] for k in eb} | {k[0] for k in ea})
    cell = 1.0
    fig, axs = plt.subplots(1, len(boards), figsize=(3.2 * len(boards), 3.4), sharey=True, squeeze=False)
    x = np.arange(len(MODELS))
    for ax, b in zip(axs[0], boards):
        ax.bar(x - 0.2, [eb.get((b, m, cell), np.nan) for m in MODELS], 0.4, label=base["label"], color="#9ecae1")
        ax.bar(x + 0.2, [ea.get((b, m, cell), np.nan) for m in MODELS], 0.4, label=new["label"], color="#3182bd")
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(MODELS, rotation=45, fontsize=7)
        ax.set_title(b, fontsize=8)
    axs[0][0].set_ylabel(f"error of the rise [%], cell {cell:g} mm")
    axs[0][0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_03_error_vs_reference.png", dpi=105)
    plt.close(fig)


def frozen_times(reference):
    """!
    @brief Draw the times to 63 % of the step response held by the frozen reference file (committed, so no result set is needed): one column per board, one marker per model, the first part of the board.
    @param reference Path of `reference/v<version>.json`.
    @return None (writes fig_04_frozen_times.png).
    """
    data = json.loads(Path(reference).read_text(encoding="utf-8"))
    boards = sorted({k.split("|")[0] for k in data["transients"]})
    fig, ax = plt.subplots(figsize=(9, 4))
    for model, marker in zip(MODELS, "osv^D"):
        xs, ys = [], []
        for i, b in enumerate(boards):
            rec = data["transients"].get(f"{b}|{model}")
            if rec and rec["t63"]:
                xs.append(i)
                ys.append(next(iter(rec["t63"].values())))
        ax.plot(xs, ys, marker, label=model, ms=6, alpha=0.8)
    ax.set_xticks(range(len(boards)))
    ax.set_xticklabels(boards, rotation=70, ha="right", fontsize=7)
    ax.set_yscale("log")
    ax.set_ylabel("time to 63 % of the step (s), first part")
    ax.set_title(f"Frozen reference v{data['version']}: {len(data['transients'])} step responses (board x model)", fontsize=9)
    ax.legend(ncol=5, fontsize=8, loc="lower right")
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(OUT / "fig_04_frozen_times.png", dpi=140)
    plt.close(fig)


def main(argv=None):
    """!
    @brief Draw the data figures.
    @param argv List of arguments (default: sys.argv[1:]).
    @return int exit code (0).
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("base", nargs="?", help="earlier result set (omit it with --frozen)")
    ap.add_argument("new", nargs="?", help="result set under test (omit it with --frozen)")
    ap.add_argument("--frozen", metavar="REFERENCE", help="draw only fig_04 from a frozen reference file (reference/v<version>.json); needs no result set")
    ap.add_argument("--cell", type=float, default=1.0)
    ap.add_argument("--table", default=str(ROOT / "reference" / "expected_shifts.json"))
    ap.add_argument("--references", default=str(ROOT / "out" / "references.json"))
    a = ap.parse_args(argv)
    OUT.mkdir(exist_ok=True)
    if a.frozen:
        frozen_times(a.frozen)
        return 0
    base, new = C.load_set(a.base), C.load_set(a.new)
    shift_map(base, new, json.loads(Path(a.table).read_text(encoding="utf-8")), a.cell)
    if Path(a.references).exists():
        error_bars(base, new, json.loads(Path(a.references).read_text(encoding="utf-8")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
