#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the gap-subdivision investigation, drawn from the committed CSV files of baseline/ (no study is run here).
@details Figures 04 onward of figures/ (01 to 03 are the diagrams of make_diagrams.py). The inputs are the files written by the studies: baseline/uniform.csv (study_baseline_uniform.py),
         baseline/pads.csv (study_baseline_pads.py), baseline/gap_nodes.csv (study_gap_nodes.py) and baseline/validation_impact.csv (study_validation_impact.py). A figure whose input is missing is skipped.
         Files: fig_04_baseline_uniform.png, fig_05_baseline_pads.png, fig_06_error_against_n.png, fig_07_probes.png, fig_08_validation_impact.png, fig_09_error_vs_pad_over_gap.png.
         Usage: python research/gap-subdivision/scripts/make_figures.py   (from the repository root).
"""

import csv
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import matplotlib                                                           # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402

OUT = HERE.parent / "figures"
BASE = HERE.parent / "baseline"
MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")
COL = {"fvm": "#1f77b4", "fdm": "#ff7f0e", "lumped": "#2ca02c", "analytic": "#d62728", "solid3d": "#7f7f7f"}


def read(name):
    """!
    @brief Read a CSV of baseline/ into a list of dicts.
    @param name File name.
    @return list of dict, or None when the file does not exist.
    """
    path = BASE / name
    if not path.exists():
        return None
    with open(path) as fh:
        return list(csv.DictReader(fh))


def err(r, m):
    """!
    @brief Error of a model in percent of the reference of a row.
    @param r Row.
    @param m Model key.
    @return float.
    """
    return 100.0 * (float(r[f"{m}_K"]) / float(r["ref_K"]) - 1.0)


def fig_uniform(path):
    """!
    @brief Figure 04: the five models against the exact series on uniform boards, one panel per swept parameter.
    @param path Output file.
    @return None.
    """
    rows = read("uniform.csv")
    if not rows:
        return
    panels = [("layers", "layers", "layers"), ("gap", "gap_mm", "gap (mm)"), ("copper", "copper_um", "copper (um)"), ("source", "source_mm", "source side (mm)"),
              ("board", "size_mm", "board side (mm)"), ("cell", "cell_mm", "cell (mm)"), ("h", "h_top", "h both faces (W/m2K)")]
    fig, axs = plt.subplots(1, len(panels), figsize=(18, 3.6), sharey=True)
    for ax, (sweep, key, label) in zip(axs, panels):
        sel = [r for r in rows if r["sweep"] == sweep]
        x = [float(r[key]) for r in sel]
        for m in MODELS:
            ax.plot(x, [err(r, m) for r in sel], "o-", color=COL[m], label=m, markersize=3.5, linewidth=1.2)
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_xlabel(label, fontsize=8)
        if sweep in ("gap", "h"):
            ax.set_xscale("log")
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("error against the exact series (%)")
    axs[0].legend(fontsize=7)
    fig.suptitle("Uniform boards (no patterned copper), 30 mm board, 6 mm source unless swept: nothing is more than about 1 % off except the Lumped at high h and every model at a 2 mm cell", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_pads(path):
    """!
    @brief Figure 05: the five models against the converged 3D solver on pad boards: against the pad size for three bottom constructions, and against the gap.
    @param path Output file.
    @return None.
    """
    rows = read("pads.csv")
    if not rows:
        return
    fig, axs = plt.subplots(1, 5, figsize=(18, 3.8), sharey=True)
    for ax, kind in zip(axs[:3], ("empty", "full", "pad")):
        sel = sorted([r for r in rows if r["sweep"] == "pad_size" and r["bottom"] == kind], key=lambda r: float(r["pad_mm"]))
        for m in MODELS:
            ax.plot([float(r["pad_mm"]) for r in sel], [err(r, m) for r in sel], "o-", color=COL[m], label=m, markersize=3.5, linewidth=1.2)
        ax.set_title(f"pad size, bottom: {kind}", fontsize=8)
        ax.set_xlabel("pad side (mm)", fontsize=8)
    for ax, kind in zip(axs[3:], ("empty", "full")):
        sel = sorted([r for r in rows if r["sweep"] == "gap" and r["bottom"] == kind], key=lambda r: float(r["gap_mm"]))
        for m in MODELS:
            ax.plot([float(r["gap_mm"]) for r in sel], [err(r, m) for r in sel], "o-", color=COL[m], markersize=3.5, linewidth=1.2)
        ax.set_xscale("log")
        ax.set_title(f"gap, 10 mm pad, bottom: {kind}", fontsize=8)
        ax.set_xlabel("gap (mm)", fontsize=8)
    for ax in axs:
        ax.axhline(0, color="k", linewidth=0.6)
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=7)
    axs[0].set_ylabel("error against the converged 3D solver (%)")
    axs[0].legend(fontsize=7)
    fig.suptitle("Boards with a copper pad on the top layer (30 mm, 3 mm source, cell 0.5 mm, h 10): the two-layer error of the FVM grows as the pad gets smaller and the gap thicker", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_error_n(path):
    """!
    @brief Figure 06: error against the number of sub-gaps n for several pad boards, total (against the converged solver) and through-thickness (against the same-cell 3D solver).
    @param path Output file.
    @return None.
    """
    rows = read("gap_nodes.csv")
    if not rows:
        return
    boards = []
    for r in rows:
        if r["part"] == "B" and r["board"] not in boards:
            boards.append(r["board"])
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.6), sharey=False)
    cmap = plt.get_cmap("tab20")
    for i, b in enumerate(boards):
        for ax, key in zip(axs, ("err_total_pct", "err_z_pct")):
            sel = sorted([r for r in rows if r["part"] == "B" and r["board"] == b and r["probe"] == "all-equal"], key=lambda r: int(r["n"]))
            ax.plot([int(r["n"]) for r in sel], [float(r[key]) for r in sel], "o-", color=cmap(i), markersize=3, linewidth=1.0, label=b)
    for ax, t in zip(axs, ("against the converged 3D solver (what the user sees)", "against the 3D solver on the same in-plane cell (through the gap only)")):
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_xlabel("sub-gaps n per gap (n = 1 is the program)")
        ax.set_title(t, fontsize=8)
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("error of the peak (%)")
    axs[1].legend(fontsize=6, ncol=2)
    fig.suptitle("Every cell of every gap cut into n equal sub-gaps (copy of the FVM, cell 0.5 mm)", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_probes(path):
    """!
    @brief Figure 07: the single-effect probes on pad10-full and pad20-empty.
    @param path Output file.
    @return None.
    """
    rows = read("gap_nodes.csv")
    if not rows:
        return
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8), sharey=False)
    for ax, board in zip(axs, ("pad10-full", "pad20-empty")):
        labels = []
        for r in rows:
            if r["part"] == "C" and r["board"] == board and r["probe"] not in labels:
                labels.append(r["probe"])
        keep = [l for l in labels if l.startswith(("(0)", "(1)", "(2/3) bare cells + margin of 0", "(2/3) bare cells + margin of 4", "(4)", "(5)", "(6)", "(7)"))]
        cmap = plt.get_cmap("tab20")
        for i, lab in enumerate(keep):
            sel = sorted([r for r in rows if r["part"] == "C" and r["board"] == board and r["probe"] == lab], key=lambda r: int(r["n"]))
            if len(sel) > 1:
                ax.plot([int(r["n"]) for r in sel], [float(r["err_z_pct"]) for r in sel], "o-", color=cmap(i), markersize=3, linewidth=1.0, label=lab)
        ax.axhline(0, color="k", linewidth=0.6)
        ax.set_title(f"{board}: through-thickness error (against the same-cell 3D solver)", fontsize=8)
        ax.set_xlabel("sub-gaps n")
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("error of the peak (%)")
    axs[1].legend(fontsize=5.5, ncol=1, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_validation(path):
    """!
    @brief Figure 08: how far the peak of the validation scenarios and examples moves when every gap gets 2 or 4 nodes, or 4 nodes only in bare cells plus a margin.
    @param path Output file.
    @return None.
    """
    rows = read("validation_impact.csv")
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(13, 0.28 * len(rows) + 1.6))
    y = np.arange(len(rows))
    for k, (key, lab, col) in enumerate((("n2_all", "n = 2, all cells", "#aec7e8"), ("n4_all", "n = 4, all cells", "#1f77b4"), ("n4_bare", "n = 4, bare cells + margin", "#d62728"))):
        ax.barh(y + (k - 1) * 0.27, [100 * (float(r[key]) / float(r["fvm_K"]) - 1) for r in rows], 0.26, color=col, label=lab)
    ax.set_yticks(y)
    ax.set_yticklabels([r["name"][:52] for r in rows], fontsize=6)
    ax.invert_yaxis()
    ax.axvline(0, color="k", linewidth=0.6)
    ax.set_xlabel("change of the peak against the program's FVM (% of the rise), 1 mm cell")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3, axis="x")
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def fig_scaling(path):
    """!
    @brief Figure 09: the FVM error of the pad boards against the ratio pad size / gap thickness (all the pad-size and gap rows of the baseline), and against the through conductivity.
    @param path Output file.
    @return None.
    """
    rows = read("pads.csv")
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    mark = {"empty": "s", "full": "o", "pad": "^"}
    for kind in ("empty", "full", "pad"):
        sel = [r for r in rows if r["sweep"] in ("pad_size", "gap") and r["bottom"] == kind]
        x = [float(r["pad_mm"]) / float(r["gap_mm"]) for r in sel]
        for m, c in (("fvm", COL["fvm"]), ("fdm", COL["fdm"])):
            ax.plot(x, [err(r, m) for r in sel], mark[kind], color=c, markersize=5, alpha=0.8, label=f"{m}, bottom {kind}" if kind != "pad" or m == "fvm" else None)
    ax.set_xscale("log")
    ax.axhline(0, color="k", linewidth=0.6)
    ax.axvline(8, color="gray", linestyle=":")
    ax.text(8.3, ax.get_ylim()[0] * 0.9, "pad = 8 gaps", fontsize=7, color="gray")
    ax.set_xlabel("pad side / gap thickness (the pad rows and the gap rows of the baseline, 3 mm source)")
    ax.set_ylabel("error against the converged 3D solver (%)")
    ax.legend(fontsize=6, ncol=2)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=105)
    plt.close(fig)


def main():
    """!
    @brief Draw every figure whose input exists.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    fig_uniform(OUT / "fig_04_baseline_uniform.png")
    fig_pads(OUT / "fig_05_baseline_pads.png")
    fig_error_n(OUT / "fig_06_error_against_n.png")
    fig_probes(OUT / "fig_07_probes.png")
    fig_validation(OUT / "fig_08_validation_impact.png")
    fig_scaling(OUT / "fig_09_error_vs_pad_over_gap.png")
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
