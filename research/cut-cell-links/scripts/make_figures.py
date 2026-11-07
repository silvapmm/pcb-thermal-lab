#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures of the numbers the studies printed: error against the position of the outline, the sliver curve, the spread against h_side (README figures 03 to 05).
@details Reads `out/sweep.json`, `out/small_cells.json` (written by `study_scheme_sweep.py` and `study_small_cells.py`) and writes `figures/fig_03_...` to `fig_05_...`;
         with `out/review_sliver.json` (`study_review.py sliver`) also `fig_07_sliver_models.png`.
Usage: .venv/bin/python research/cut-cell-links/scripts/make_figures.py   (from the repository root, after the studies)
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt     # noqa: E402
import numpy as np                  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "out")
FIG = os.path.join(BASE, "figures")
SCHEMES = ("program", "aperture", "aperture+film", "links", "links+film", "links+strip")
COL = {"program": "#c00000", "aperture": "#7030a0", "aperture+film": "#2e7d32", "links": "#1f4e79", "links+film": "#6fa8dc", "links+strip": "#999999"}


def fig_positions():
    """!
    @brief Figure 3: error of the peak against the position of the outline (turns, then shifts) for the square at h_side 200 and 2000, cells 1 and 0.5 mm.
    @return None.
    """
    r = json.load(open(os.path.join(OUT, "sweep.json")))
    fig, axes = plt.subplots(2, 2, figsize=(10, 6.6), sharex=True)
    labels = [f"{a}" for a in range(0, 50, 5)] + [f"s{k}" for k in range(1, 8)]
    for ax, (hs, cell) in zip(axes.ravel(), ((200.0, 1.0), (2000.0, 1.0), (200.0, 0.5), (2000.0, 0.5))):
        for s in SCHEMES:
            e = np.array(r[f"square|3.5|{hs}|{cell}|{s}"])
            ax.plot(range(len(e)), e - e[0], "o-", ms=3, lw=1.1, color=COL[s], label=s)
        ax.set_title(f"h_side {hs:g} W/m2K, cell {cell:g} mm", fontsize=9)
        ax.axvline(9.5, color="0.7", lw=0.8)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=7)
        ax.set_ylabel("error minus the aligned board's (K)", fontsize=8)
        ax.grid(alpha=0.3)
    axes[0, 0].legend(fontsize=7)
    fig.suptitle("20 mm square, part 3.5 mm off centre: error of the peak (turn in degrees, then shift in 1/8 cell), against the frame reference", fontsize=9)
    fig.savefig(os.path.join(FIG, "fig_03_error_against_position.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_spread():
    """!
    @brief Figure 4: spread of the error over the positions against h_side, one panel per case, 1 mm and 0.5 mm.
    @return None.
    """
    r = json.load(open(os.path.join(OUT, "sweep.json")))
    hs = (10.0, 50.0, 200.0, 2000.0)
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.2), sharey="row")
    for row, cell in enumerate((1.0, 0.5)):
        for col, (shape, off) in enumerate((("square", 0.0), ("square", 3.5), ("strip", 0.0))):
            ax = axes[row, col]
            for s in SCHEMES:
                sp = [np.ptp(r[f"{shape}|{off}|{h}|{cell}|{s}"]) for h in hs]
                ax.plot(hs, sp, "o-", color=COL[s], label=s, lw=1.2, ms=4)
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(f"{shape}, part offset {off:g} mm, cell {cell:g} mm", fontsize=8)
            ax.set_xlabel("h_side (W/m2K)", fontsize=8)
            ax.grid(alpha=0.3, which="both")
    axes[0, 0].set_ylabel("spread of the error (K)")
    axes[1, 0].set_ylabel("spread of the error (K)")
    axes[0, 0].legend(fontsize=7)
    fig.savefig(os.path.join(FIG, "fig_04_spread_against_hside.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_sliver():
    """!
    @brief Figure 5: the hottest temperature against the cover of the edge column (the sliver curve) for every scheme.
    @return None.
    """
    r = json.load(open(os.path.join(OUT, "small_cells.json")))
    covers = sorted({float(k.split("|")[0]) for k in r if not k.startswith("anomaly")})   # (the anomaly table of the review has its own keys)
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for s in SCHEMES:
        ax.plot(covers, [r[f"{c:g}|{s}"]["tmax"] for c in covers], "o-", ms=4, color=COL[s], label=s)
    ax.set_xscale("log")
    ax.set_xlabel("cover of the edge column c")
    ax.set_ylabel("hottest temperature (degC)")
    ax.set_title("Edge moved over a cell (1 mm), part 2 mm from it, h_side 200: the program jumps at c = 0.02", fontsize=9)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8)
    fig.savefig(os.path.join(FIG, "fig_05_sliver_curve.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_sliver_models():
    """!
    @brief Figure 7 (added by the review): error of the hottest point against the cover of the edge column, minus its value at c = 1, for the FVM schemes, the FDM and the 3D solid
           (reference: the independent two-sheet solver, `out/review_sliver.json` of `study_review.py sliver`).
    @return None.
    """
    p = os.path.join(OUT, "review_sliver.json")
    if not os.path.exists(p):
        return
    r = json.load(open(p))
    covers = (0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0)
    models = (("program", "FVM (program)", "#c00000"), ("aperture", "FVM aperture", "#7030a0"), ("aperture+film", "FVM aperture+film", "#2e7d32"),
              ("fdm", "FDM", "#1f4e79"), ("solid3d", "3D solid", "#999999"))
    fig, axes = plt.subplots(1, 2, figsize=(10.0, 3.8), sharey=True)
    for ax, hs in zip(axes, ("200", "2000")):
        for key, label, col in models:
            e = np.array([r[f"{hs}|{c:g}"][key] for c in covers])
            ax.plot(covers, e - e[-1], "o-", color=col, label=label, ms=4)
        ax.set_xscale("log")
        ax.axhline(0, color="0.6", lw=0.8)
        ax.set_xlabel("cover c of the edge column")
        ax.set_title(f"h_side {hs} W/m2K, cell 1 mm", fontsize=9)
    axes[0].set_ylabel("error minus error at c = 1 (K)")
    axes[1].legend(fontsize=8)
    fig.savefig(os.path.join(FIG, "fig_07_sliver_models.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_positions()
    fig_spread()
    fig_sliver()
    fig_sliver_models()
