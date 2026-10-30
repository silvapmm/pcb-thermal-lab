#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the bare-spot investigation, drawn from the results of the study scripts (out/*.json).
@details Figures from 04 on (01 to 03 are the drawings of make_diagrams.py): the error of the five models against the size of the window for the four stack-ups (04), the error of the FVM with
         n laminate nodes in the gaps (05), the unknowns that the refined zone costs (06), the real-board windows (07), and the lateral-short experiment, the error against the skin kept in the
         lateral conduction (08). Run the study scripts first (study_window_sweep.py, study_real_stormduino.py, study_skin.py).
         Usage: python research/bare-spot-under-source/scripts/make_figures.py   (from the repository root).
"""

import _bootstrap  # noqa: F401  (import paths)

import json

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402

from _bootstrap import FIGURES, OUT                                         # noqa: E402

MODELS = ("fvm", "fdm", "solid3d", "lumped", "analytic")
COLORS = {"fvm": "#1f77b4", "fdm": "#ff7f0e", "solid3d": "#2ca02c", "lumped": "#d62728", "analytic": "#9467bd"}


def pct(v, r):
    """!
    @brief Error in percent.
    @param v Value.
    @param r Reference.
    @return float.
    """
    return 100.0 * (v / r - 1.0)


def fig_models():
    """!
    @brief Figure 04: error of every model against the window size, one panel per stack-up, cell 0.5 mm.
    @return None.
    """
    rows = json.load(open(OUT / "sweep_models.json"))
    stacks = []
    for r in rows:
        s = r["name"].rsplit(" w=", 1)[0]
        if s not in stacks:
            stacks.append(s)
    fig, axs = plt.subplots(1, len(stacks), figsize=(4 * len(stacks), 3.8), sharey=True)
    for ax, s in zip(axs, stacks):
        rs = [r for r in rows if r["name"].startswith(s + " w=")]
        w = [int(r["name"].rsplit("=", 1)[1]) for r in rs]
        for m in MODELS:
            ax.plot(w, [pct(r["models"]["0.5"][m], r["ref"]["max"]) for r in rs], "o-", color=COLORS[m], label=m, linewidth=1.3, markersize=4)
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_title(s, fontsize=9)
        ax.set_xlabel("window side (mm), part 6 mm")
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("peak error against the resolved 3D (%)")
    axs[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig_04_models_against_window.png", dpi=105)


def fig_nodes():
    """!
    @brief Figure 05: error of the FVM with n laminate nodes (equal sub-gaps, margin one gap thickness), windows 6 and 12 mm, cell 0.5 mm, four stack-ups.
    @return None.
    """
    rows = json.load(open(OUT / "sweep_treat.json"))
    stacks = []
    for r in rows:
        s = r["name"].rsplit(" w=", 1)[0]
        if s not in stacks:
            stacks.append(s)
    fig, axs = plt.subplots(1, len(stacks), figsize=(4 * len(stacks), 3.8), sharey=True)
    for ax, s in zip(axs, stacks):
        for w, col in ((2, "#999999"), (6, "#1f77b4"), (12, "#d62728")):
            r = next(q for q in rows if q["name"] == f"{s} w={w}")
            t = r["treat"]["0.5"]
            ns = [1, 2, 3, 4, 6]
            keys = ["program", "n=2", "n=3", "n=4", "n=6"]
            ax.plot(ns, [pct(t[k]["peak"], r["ref"]["max"]) for k in keys], "o-", color=col, label=f"window {w} mm", linewidth=1.3, markersize=4)
            if "n=2+v" in t:
                ax.plot([2, 3, 4], [pct(t[k]["peak"], r["ref"]["max"]) for k in ("n=2+v", "n=3+v", "n=4+v")], "s--", color=col, linewidth=0.9, markersize=3)
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_title(s, fontsize=9)
        ax.set_xlabel("laminate nodes per gap n (1 = the program); dashed: with the vertical correction")
        ax.xaxis.label.set_size(6)
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("peak error of the FVM (%)")
    axs[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig_05_fvm_with_laminate_nodes.png", dpi=105)


def fig_cost():
    """!
    @brief Figure 06: unknowns of the refined zone against the program's, per stack-up, window 6 mm, cells 1 and 0.5 mm.
    @return None.
    """
    rows = json.load(open(OUT / "sweep_treat.json"))
    fig, ax = plt.subplots(figsize=(6, 3.8))
    labels, vals = [], []
    for r in rows:
        if not r["name"].endswith("w=6"):
            continue
        for cell in ("1.0", "0.5"):
            t = r["treat"][cell]
            labels.append(f"{r['name'].split(' w=')[0]}\n{cell} mm")
            vals.append([t[k]["unknowns"] / t["program"]["unknowns"] for k in ("program", "n=2", "n=4", "n=6")])
    x = np.arange(len(labels))
    for j, (k, c) in enumerate((("program", "#999999"), ("n=2", "#1f77b4"), ("n=4", "#ff7f0e"), ("n=6", "#d62728"))):
        ax.bar(x + (j - 1.5) * 0.2, [v[j] for v in vals], 0.2, color=c, label=k)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6)
    ax.set_ylabel("unknowns / program's unknowns")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(FIGURES / "fig_06_cost_in_unknowns.png", dpi=105)


def fig_real():
    """!
    @brief Figure 07: the three real-board windows, error of the FVM against the cell-fill solver for the program and the treatments.
    @return None.
    """
    res = json.load(open(OUT / "real_board_treat.json"))
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, cell in zip(axs, ("1.0", "0.5")):
        keys = list(next(iter(res.values()))[cell]["treat"].keys())
        names = [json.loads(k) for k in keys]
        lab = [("program" if n["kind"] == "none" else "vert" if n["kind"] == "vert" else f"n={n['n']}+v") for n in names]
        w = 0.8 / len(res)
        for i, (key, row) in enumerate(res.items()):
            cf = row[cell]["cell_fill_solver"]["max"]
            ax.bar(np.arange(len(keys)) + i * w, [pct(row[cell]["treat"][k]["peak"], cf) for k in keys], w, label=f"{key} (fill of the hottest cell {row[cell]['cell_fill_solver']['fill_hot']:.2f})")
        ax.set_xticks(np.arange(len(keys)) + 0.3)
        ax.set_xticklabels(lab, fontsize=7)
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_title(f"cell {cell} mm", fontsize=9)
        ax.grid(alpha=0.3, axis="y")
    axs[0].set_ylabel("FVM peak against the solver on the cell fill (%)")
    axs[0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig_07_real_board_windows.png", dpi=105)


def fig_skin():
    """!
    @brief Figure 08: the error of the FVM against the thickness kept in the lateral conduction of the bare cells (the lateral-short experiment).
    @return None.
    """
    rows = json.load(open(OUT / "skin.json"))
    fig, ax = plt.subplots(figsize=(6, 3.8))
    for r in rows:
        ax.plot(r["alpha"], r["err"], "o-", label=r["label"], linewidth=1.2, markersize=3)
    ax.axhline(0, color="k", linewidth=0.6)
    ax.axvline(0.5, color="gray", linestyle=":", linewidth=0.8)
    ax.text(0.5, ax.get_ylim()[1] * 0.9, " the program (d/2)", fontsize=7)
    ax.set_xlabel("laminate kept in the lateral conduction of a bare cell, in units of the gap d")
    ax.set_ylabel("FVM peak error (%)")
    ax.legend(fontsize=6)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURES / "fig_08_lateral_short_experiment.png", dpi=105)


if __name__ == "__main__":
    FIGURES.mkdir(exist_ok=True)
    for fn, need in ((fig_models, "sweep_models.json"), (fig_nodes, "sweep_treat.json"), (fig_cost, "sweep_treat.json"), (fig_real, "real_board_treat.json"), (fig_skin, "skin.json")):
        if (OUT / need).exists():
            fn()
            print("drawn", fn.__name__)
        else:
            print("skipped", fn.__name__, "(missing", need + ")")
