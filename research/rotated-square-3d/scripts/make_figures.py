#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figures of the rotated-square investigation, drawn from the numbers the studies saved in out/ (run the studies first).
@details Figures 04 to 08 of figures/ (the drawings 01 to 03 come from make_diagrams.py): the dependence of the answer on the shift and the turn
         against the number of cells per side (study_cut_cells.py, with --fine for the last point), the difference caused by turning the square at
         three edge coefficients (study_remeasure.py), the error against the axisymmetric reference on a round board (study_disc.py) and the total
         edge conductance against the angle (study_edge_conductance.py); figure 08 (added by the review) the error against the continuum value of the
         independent quarter-board solver (study_square_reference.py).
Usage: .venv/bin/python research/rotated-square-3d/scripts/make_figures.py   (from the repository root)
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import runs   # noqa: E402

OUT = HERE.parent / "figures"
COL = {"solid3d": "#d62728", "kx_physical": "#ff7f0e", "strip": "#9467bd", "cutcell": "#2ca02c", "fvm": "#1f77b4", "fdm": "#8c564b"}
NAME = {"solid3d": "program 3D", "kx_physical": "copy: physical k", "strip": "copy: strip distance", "cutcell": "copy: cut cells", "fvm": "FVM", "fdm": "FDM"}


def fig_ladder():
    """!
    @brief Figure 04: absolute difference to the aligned board against the cells per side, for a half-cell shift and a 20 degree turn.
    @return None.
    """
    d = runs.load("cut_cells.json")
    if d is None:
        return
    cells = sorted({float(k.split("|")[0]) for k in d}, reverse=True)
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, lay, title in zip(axs, ("shift 1/2 cell", "turned 20"), ("straight edge shifted by half a cell", "square turned by 20 degrees")):
        for m in ("solid3d", "kx_physical", "strip", "cutcell", "fvm", "fdm"):
            xs, ys = [], []
            for c in cells:
                a, b = d.get(f"{c:g}|aligned|{m}"), d.get(f"{c:g}|{lay}|{m}")
                if a is not None and b is not None:
                    xs.append(20.0 / c)
                    ys.append(max(abs(b - a), 0.01))
            ax.plot(xs, ys, "o-", color=COL[m], label=NAME[m], lw=1.4 if m in ("solid3d", "cutcell") else 0.9)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xticks([20, 40, 80, 160], ["20", "40", "80", "160"])   # plain ticks: the default log labels overlapped
        ax.minorticks_off()
        ax.set_xlabel("cells per side of the 20 mm board")
        ax.set_title(title, fontsize=9)
        ax.grid(alpha=0.3, which="both")
    axs[0].set_ylabel("|T_max - T_max aligned| (K), floor 0.01")
    axs[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_04_shift_and_turn_vs_cells.png", dpi=105)
    plt.close(fig)


def fig_remeasure():
    """!
    @brief Figure 05: the difference to the aligned square for the square turned 20 degrees alone, 40 mm board, 1 mm cells, against the edge coefficient.
    @return None.
    """
    d = runs.load("remeasure.json")
    if d is None:
        return
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    hs = [10, 100, 1000]
    for m in ("fvm", "fdm", "solid3d", "cutcell"):
        ax.plot(hs, [d[f"{h}|board only 20"][m] - d[f"{h}|aligned"][m] for h in hs], "o-", color=COL[m], label=NAME[m])
    ax.set_xscale("log")
    ax.set_xlabel("h_side (W/m2K)")
    ax.set_ylabel("T_max turned 20 deg minus aligned (K)")
    ax.set_title("40 mm square, 1 mm cells, part on the grid", fontsize=9)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_05_turned_square_vs_h_side.png", dpi=105)
    plt.close(fig)


def fig_disc():
    """!
    @brief Figure 06: error of the 3D solid and of the cut-cell copy against the axisymmetric reference on a round board.
    @return None.
    """
    d = runs.load("disc.json")
    if d is None:
        return
    fig, ax = plt.subplots(figsize=(5.4, 3.6))
    cells = (1.0, 0.5, 0.25)
    for hs, ls in ((100, ":"), (1000, "-"), (5000, "--")):
        for m in ("solid3d", "cutcell"):
            ref = d[f"{hs}|ref"]
            ax.plot([40.0 / c for c in cells], [100.0 * (d[f"{hs}|{c:g}|{m}"] - ref) / ref for c in cells], "o", ls=ls, color=COL[m], label=f"{NAME[m]}, h_side {hs}")
    ax.set_xscale("log")
    ax.set_xlabel("cells across the 40 mm disc")
    ax.set_ylabel("error of the rise (%)")
    ax.axhline(0, color="k", lw=0.6)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(OUT / "fig_06_disc_against_axisymmetric.png", dpi=105)
    plt.close(fig)


def fig_conductance():
    """!
    @brief Figure 07: total side conductance of the 3D network of a turned square, as a ratio to the aligned square, against the edge coefficient.
    @return None.
    """
    d = runs.load("edge_conductance.json")
    if d is None:
        return
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    hs = [10, 100, 1000, 5000]
    for m, key in (("solid3d", "program"), ("cutcell", "cutcell")):
        ax.plot(hs, [d[f"{h}|20"][key] / d[f"{h}|0"][key] for h in hs], "o-", color=COL[m], label=NAME[m] + ", turned 20")
    ax.axhline(1.0, color="k", lw=0.6)
    ax.set_xscale("log")
    ax.set_xlabel("h_side (W/m2K)")
    ax.set_ylabel("G side turned / G side aligned")
    ax.set_title("same perimeter (160 mm), 1 mm cells", fontsize=9)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_07_edge_conductance_ratio.png", dpi=105)
    plt.close(fig)


def fig_square_reference():
    """!
    @brief Figure 08 (review): signed error of the maximum temperature against the continuum value of the independent quarter-board solver,
           20 mm board at h_side 2000, for the half-cell shift and the turns of 20 and 45 degrees, against the cells per side.
    @return None.
    """
    d = runs.load("square_reference.json")
    if d is None:
        return
    ref = d["20mm_2000_square"]["richardson"]
    cells = (0.5, 0.25, 0.125)
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.4), sharey=True)
    styles = {"solid3d": ("program 3D", COL["solid3d"], "-"), "cutcell": ("copy: cut cells", COL["cutcell"], "-"),
              "cutcell_src8": ("copy: cut cells, part sampled 8 x 8", COL["cutcell"], "--")}
    for ax, lay in zip(axs, ("shift 1/2 cell", "turned 20", "turned 45")):
        for m, (label, col, ls) in styles.items():
            ax.plot([20.0 / c for c in cells], [d[f"20mm|{c:g}|{lay}|{m}"] - ref for c in cells], "o", ls=ls, color=col, label=label)
        ax.plot([20.0 / c for c in cells], [d[f"20mm|{c:g}|aligned|solid3d"] - ref for c in cells], "s:", color="k", label="aligned (no cut cell)")
        ax.axhline(0.0, color="k", lw=0.6)
        ax.set_xscale("log")
        ax.set_xticks([40, 80, 160], ["40", "80", "160"])
        ax.minorticks_off()
        ax.set_title(lay, fontsize=9)
        ax.set_xlabel("cells per side of the 20 mm board")
        ax.grid(alpha=0.3)
    axs[0].set_ylabel(f"T_max minus continuum {ref:.2f} degC (K)")
    axs[0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(OUT / "fig_08_square_against_continuum.png", dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_ladder()
    fig_remeasure()
    fig_disc()
    fig_conductance()
    fig_square_reference()
