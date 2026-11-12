#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures from the printed numbers: error of the FDM against the copper-edge position (fig 02), against the finite-element limit at two cells (fig 03), against the independent 3D solver (fig 04).
@details Reads `out/cause.json` (`study_cause.py`) and `out/independent.json` (`study_independent_3d.py`); run those first. Run from the repository root:
         `.venv/bin/python research/fdm-inset-edge/scripts/make_figures.py`. The figures are written to `research/fdm-inset-edge/figures/`.
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "..", "figures")
OUT = os.path.join(HERE, "..", "out")
COL = {"FVM": "#2a6fb0", "FDM (program)": "#b0261c", "FDM face fill": "#2a8a3a"}


def fig_position(cause):
    """!
    @brief Error against the copper-edge position (table D).
    @param cause Dict of cause.json.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=False)
    for ax, h in zip(axs, (200.0, 1000.0)):
        pos = [0.30, 0.375, 0.45, 0.50, 0.55, 0.625]
        for j, name in enumerate(COL):
            ax.plot(pos, [cause[f"D|{h}|{p}"][j] for p in pos], "o-", color=COL[name], label=name)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_title(f"h_side {h:.0f} W/m2K, cell 0.25 mm")
        ax.set_xlabel("copper edge inside the wall (mm); nodes at multiples of 0.25 mm")
    axs[0].set_ylabel("hottest rise, % of the FVM at 0.0625 mm")
    axs[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_02_error_against_edge_position.png"), dpi=130)
    plt.close(fig)


def fig_fem(cause):
    """!
    @brief Error against the finite-element limit at two cells (table A, shipped laminate rule).
    @param cause Dict of cause.json.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(7, 4))
    labels, w = [], 0.26
    keys = [(c, h) for c in (0.5, 0.25) for h in (10.0, 200.0, 1000.0)]
    for j, name in enumerate(COL):
        ax.bar([i + (j - 1) * w for i in range(len(keys))], [cause[f"A|{c}|{h}"][j] for c, h in keys], width=w, color=COL[name], label=name)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([f"{c} mm\n{h:.0f}" for c, h in keys], fontsize=8)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("hottest rise vs finite-element limit, %")
    ax.set_title("10 mm plate, copper 0.5 mm inside the wall (cell, h_side)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_03_inset_plate_against_fem.png"), dpi=130)
    plt.close(fig)


def fig_indep(ind):
    """!
    @brief Error against the independent 3D solver on the copper-edge boards of validation 41.
    @param ind Dict of independent.json.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(9, 4))
    keys = [k for k in ind if not k.startswith("strips")]
    for j, name in enumerate(COL):
        ax.bar([i + (j - 1) * 0.26 for i in range(len(keys))], [ind[k][j] for k in keys], width=0.26, color=COL[name], label=name)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([k.replace("|", "\n") for k in keys], fontsize=7)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_ylabel("hottest rise vs independent 3D, %")
    ax.set_title("Copper-edge boards of validation 41 (name, cell mm); strips board in the README table")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_04_against_independent_3d.png"), dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    c = json.load(open(os.path.join(OUT, "cause.json")))
    fig_position(c)
    fig_fem(c)
    fig_indep(json.load(open(os.path.join(OUT, "independent.json"))))
