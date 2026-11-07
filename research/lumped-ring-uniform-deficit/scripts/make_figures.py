#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures of the numbers of the studies: deficit against board size, against the distance to an edge, on the parts of three imported boards, and the closed-form ratio of the strip to the annulus.
@details Reads out/*.json written by the studies (study_board_size_sweep.py, study_edge_distance.py, study_imported_parts.py) and writes figures/fig_03 to fig_06. Run from the repository root
         after the studies: .venv/bin/python research/lumped-ring-uniform-deficit/scripts/make_figures.py
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
FIG = HERE.parent / "figures"


def fig_board_size():
    """!
    @brief Figure 3: error of the Lumped hottest node against the diagonal of the board, for three source sizes, program and proposal.
    @return None.
    """
    rows = json.loads((OUT / "sweep_board.json").read_text())
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    for side, col in ((1.0, "#d62728"), (3.0, "#ff7f0e"), (10.0, "#1f77b4")):
        sel = [r for r in rows if r["side"] == side]
        x = [np.hypot(*r["board"]) for r in sel]
        ax.plot(x, [100 * (r["program"]["hot"] / r["fvm_hot"] - 1) for r in sel], "o-", color=col, label=f"program, {side:g} mm source")
        ax.plot(x, [100 * (r["cap 1 a"]["hot"] / r["fvm_hot"] - 1) for r in sel], "s--", color=col, mfc="none", label=f"first ring at most 1 a, {side:g} mm")
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("board diagonal (mm): 30 x 20, 60 x 40, 100 x 80, 200 x 150")
    ax.set_ylabel("Lumped / FVM - 1, hottest node (%)")
    ax.legend(fontsize=7)
    ax.set_title("Uniform two-layer board, centred source, 1 W", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "fig_03_deficit_against_board_size.png", dpi=105)
    plt.close(fig)


def fig_edge():
    """!
    @brief Figure 4: error against the distance of the source to the edge (and the corner), 3 and 10 mm sources.
    @return None.
    """
    rows = json.loads((OUT / "edge_distance.json").read_text())
    fig, axs = plt.subplots(1, 2, figsize=(9.5, 3.8), sharey=True)
    for ax, side in zip(axs, (3.0, 10.0)):
        for place, ls in (("edge", "-"), ("corner", ":")):
            sel = [r for r in rows if r["side"] == side and r["place"] == place]
            d = [r["d"] for r in sel]
            ax.plot(d, [r["program"] for r in sel], "o" + ls, color="#d62728", label=f"program, {place}")
            ax.plot(d, [r["cap 1 a"] for r in sel], "s" + ls, color="#1f77b4", mfc="none", label=f"first ring at most 1 a, {place}")
            ax.plot(d, [r["analytic"] for r in sel], "^" + ls, color="#2ca02c", mfc="none", label=f"Analytic, {place}")
        ax.axhline(0, color="k", lw=0.6)
        ax.set_xlabel("distance of the source to the board edge (mm)")
        ax.set_title(f"{side:g} mm source, 100 x 80 mm board", fontsize=9)
    axs[0].set_ylabel("model / FVM - 1, hottest node (%)")
    axs[0].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(FIG / "fig_04_deficit_near_an_edge.png", dpi=105)
    plt.close(fig)


def fig_parts():
    """!
    @brief Figure 5: the uniform-sheet error of every part of RP2040, oswlight and CO60, program, the two candidates and the Analytic.
    @return None.
    """
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.6), sharey=True)
    series = (("program", "cap-1-a", "#d62728", "o", "Lumped, program"), ("cap 1 a", "cap-1-a", "#1f77b4", "s", "Lumped, first ring at most 1 a"),
              ("first 1.5 cells", "first-1.5-cells", "#9467bd", "D", "Lumped, first ring 1.5 cells"), ("analytic", "cap-1-a", "#2ca02c", "^", "Analytic"))
    for ax, board in zip(axs, ("rp2040", "oswlight", "co60")):
        for k, (key, slug, col, mk, lab) in enumerate(series):
            rows = [r for r in json.loads((OUT / f"imported_parts_{board}_{slug}.json").read_text()) if "uniform" in r]
            if board == "co60" and slug == "cap-1-a":
                pass
            v = [100 * (r["uniform"][key] / r["uniform"]["fvm"] - 1) for r in rows]
            ax.plot(np.full(len(v), k) + np.linspace(-0.2, 0.2, len(v)), v, mk, color=col, mfc="none", ms=4, label=lab)
        ax.axhline(0, color="k", lw=0.6)
        ax.set_xticks([])
        ax.set_title(f"{board}", fontsize=9)
    axs[0].set_ylabel("model / FVM - 1 on the uniform sheet (%)")
    axs[0].legend(fontsize=6, loc="lower left")
    fig.tight_layout()
    fig.savefig(FIG / "fig_05_uniform_sheet_parts.png", dpi=105)
    plt.close(fig)


def fig_ratio():
    """!
    @brief Figure 6: the resistance of the first half ring as a strip over that of the annulus, against the ring width over the footprint radius (closed form, pure conduction).
    @return None.
    """
    t = np.logspace(-1, 2, 100)
    a = 1.0
    b = a + t
    exact = (b * b * np.log(b / a) - (b * b - a * a) / 2) / (b * b - a * a) / (2 * np.pi)
    strip = t * t / (2 * np.pi * (b * b - a * a))
    fig, ax = plt.subplots(figsize=(5.6, 3.6))
    ax.semilogx(t, strip / exact, color="#d62728")
    ax.axhline(1, color="k", lw=0.6)
    ax.set_xlabel("first ring width / footprint radius (t / a)")
    ax.set_ylabel("R(strip) / R(annulus)")
    ax.set_title("Footprint boundary to the mean of the first ring (illustrative: closed form, no vertical loss)", fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / "fig_06_strip_against_annulus.png", dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    fig_board_size()
    fig_edge()
    fig_parts()
    fig_ratio()
