#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures of the results of research/lumped-analytic-vias from the JSON files that the studies write in out/ (and the closed form of lib/constriction.py).
@details Figures 06 to 09 (01 to 05 are drawn by make_diagrams.py):
         06 error of the via effect of the unit cell against the pitch (program and patches, Lumped and Analytic);
         07 the constriction and the barrel against the cell radius, open and copper fill (why the copper-fill gain is overstated);
         08 the copper-fill gain of the 3 x 3 array board against the pitch: reference and models;
         09 the error of the via effect on the example board and its denser arrays.
         Run the studies first (study_unit_cell.py, study_arrays.py, study_real_boards.py), then: python research/lumped-analytic-vias/scripts/make_figures.py (from the repository root).
"""

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import matplotlib                                                           # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402

import constriction as cr                                                   # noqa: E402

OUT = HERE.parent / "figures"
DATA = HERE.parent / "out"
COL = {"L_prog": "#d62728", "L_ring": "#ff9896", "L_grp0": "#1f77b4", "A_prog": "#8c564b", "A_on": "#c49c94", "A_fin": "#2ca02c", "A_bil": "#98df8a", "FVM": "0.5", "FVM_fix": "0.2"}


def fig_unit_cell(path):
    """!
    @brief Error of the via effect of the unit cell (0.3 mm, copper fill) against the pitch for the program and the patches.
    @param path Output file.
    @return None.
    """
    rows = json.load(open(DATA / "unit_cell.json"))
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, model, names in zip(axs, ("Lumped", "Analytic"), (("L_prog", "L_ring", "L_grp0"), ("A_prog", "A_on", "A_fin"))):
        for n in names:
            for layers, ls in ((2, "-"), (4, "--")):
                pts = sorted((r["task"][2], r["err"][n]) for r in rows if r["task"][0] == layers and r["task"][1] == 0.3 and r["task"][3] == 385.0)
                ax.plot([p[0] for p in pts], [p[1] for p in pts], ls, marker="o", color=COL[n], label=f"{n}, {layers} layers")
        ax.axhline(0, color="k", lw=0.6)
        ax.set_title(f"{model}: 0.3 mm via, copper fill, unit cell of a lattice", fontsize=9)
        ax.set_xlabel("pitch (mm)")
        ax.legend(fontsize=7)
    axs[0].set_ylabel("error of the via effect against the fine-grid reference (%)")
    fig.tight_layout()
    fig.savefig(path, dpi=105)


def fig_constriction(path):
    """!
    @brief The constriction of one 0.3 mm via in a 35 um plane against the cell radius, next to the barrel resistance (open, copper fill, three gaps).
    @param path Output file.
    @return None.
    """
    S, a = 0.0135, cr.ETA * 0.15e-3
    r = np.linspace(0.4e-3, 6e-3, 120)
    rc = np.array([cr.krogh(S, x, a) for x in r])
    fig, ax = plt.subplots(figsize=(6.5, 4.4))
    ax.plot(r * 1e3, rc, color="#d62728", lw=2, label="constriction of one plane, $R_c$ (Krogh cell)")
    ax.axhline(175.6 / 1.0, color="0.3", ls="--", label="barrel, open via, three gaps (175.6 K/W)")
    ax.axhline(175.6 / 3.3, color="0.3", ls=":", label="barrel, copper fill (about 53 K/W)")
    ax.set_yscale("log")
    ax.set_xlabel("cell radius R (mm)")
    ax.set_ylabel("resistance of one via (K/W)")
    ax.set_title("two planes in series with the barrel: 2 R_c against the barrel", fontsize=9)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=105)


def fig_gain(path):
    """!
    @brief Copper-fill gain of the 3 x 3 array board (4 layers, 0.3 mm) against the pitch.
    @param path Output file.
    @return None.
    """
    rows = json.load(open(DATA / "arrays.json"))
    sel = sorted((r for r in rows if r["task"][0] == "array" and r["task"][1][0] == 4 and r["task"][1][1] == 0.3), key=lambda r: r["task"][1][2])
    pitch = [r["task"][1][2] for r in sel]
    fig, ax = plt.subplots(figsize=(7, 4.4))
    ax.plot(pitch, [r["G_ref"] for r in sel], "k-o", lw=2.5, label="reference (fine-grid layered solver)")
    for n in ("FVM_fix", "L_prog", "L_grp0", "A_prog", "A_fin"):
        ax.plot(pitch, [r["E"]["385.0"][n] - r["E"]["0.0"][n] for r in sel], "-s", color=COL[n], label=n)
    ax.set_xlabel("via pitch (mm)")
    ax.set_ylabel("gain of the copper fill, K")
    ax.invert_xaxis()
    ax.legend(fontsize=7)
    ax.set_title("3 x 3 array under a 10 mm source, 4 layers, 0.3 mm drill", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=105)


def fig_real(path):
    """!
    @brief Error of the via effect on the example board and its denser arrays.
    @param path Output file.
    @return None.
    """
    rows = json.load(open(DATA / "real_boards.json"))
    names = ["FVM", "L_prog", "L_grp0", "A_prog", "A_fin"]
    labels = [f"{r['board']}\n{'Cu' if r['fill'] else 'open'}" for r in rows]
    x = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(11, 4.4))
    w = 0.16
    for i, n in enumerate(names):
        ax.bar(x + (i - 2) * w, [100 * (r["E"][n] / r["E_ref"] - 1) for r in rows], w, color=COL[n], label=n)
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("error of the via effect against FVM_fix at 0.25 mm (%)")
    ax.legend(fontsize=7, ncol=5)
    fig.tight_layout()
    fig.savefig(path, dpi=105)


def main():
    """!
    @brief Draw the figures whose data exist.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    fig_constriction(OUT / "fig_07_constriction_against_barrel.png")
    for fn, name, f in ((fig_unit_cell, "fig_06_unit_cell_error_against_pitch.png", "unit_cell.json"), (fig_gain, "fig_08_copper_fill_gain_against_pitch.png", "arrays.json"),
                        (fig_real, "fig_09_real_board_errors.png", "real_boards.json")):
        if (DATA / f).exists():
            fn(OUT / name)


if __name__ == "__main__":
    main()
