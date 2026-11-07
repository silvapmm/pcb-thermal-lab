#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures from the data of the studies: the barrel-length sweep (fig_03) and the reference set (fig_04).
@details Reads out/barrel.json (study_barrel_length.py) and out/contact.json, out/solid_8.json (study_contact_set.py, study_reference_set.py). Run from the repository root:
         `.venv/bin/python research/via-contact-geometry/scripts/make_figures.py`.
"""

import json
import sys

import _bootstrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def barrel_fig():
    """!
    @brief Error of R against t_cu / gap for the program (a = 0) and the rule a = 0.5, FVM.
    @return None.
    """
    rows = json.load(open(_bootstrap.OUT / "barrel.json"))["rows"]
    x = np.array([r["t_cu"] / r["gap"] for r in rows])
    fig, axs = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for ax, rule, title in zip(axs, ("0.0", "0.5"), ("the program (barrel over d)", "barrel over d + 0.5 t_cu")):
        e = np.array([r["err"][f"fvm|{rule}"] for r in rows])
        for fill, mk in (("air", "o"), ("solder", "^")):
            m = np.array([r["fill"] == fill for r in rows])
            sc = ax.scatter(x[m], e[m], c=[r["t_cu"] * 1e6 for r, k in zip(rows, m) if k], marker=mk, s=14, cmap="viridis", label=fill)
        ax.axhline(0, color="k", lw=0.7)
        ax.set_xscale("log")
        ax.set_xlabel("t_cu / d")
        ax.set_title(title, fontsize=9)
        ax.legend(fontsize=8)
    axs[0].set_ylabel("error of the via resistance R against the axisymmetric cell, %")
    fig.colorbar(sc, ax=axs, label="copper um")
    fig.savefig(_bootstrap.FIGURES / "fig_03_barrel_sweep.png", dpi=130, bbox_inches="tight")


def set_fig():
    """!
    @brief Error of the FVM via effect in K on the cases with partial copper, per variant, at 0.5 mm.
    @return None.
    """
    res = json.load(open(_bootstrap.OUT / "contact.json"))
    solid = json.load(open(_bootstrap.OUT / "solid_8.json"))
    names = ["quarter", "track 0.25", "bareout g0.3", "bareout g0.6", "bareout g1.0"]
    variants = ("current", "sheet", "contact")
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    for ax, cell in zip(axs, (1.0, 0.5)):
        for k, v in enumerate(variants):
            vals = [res[f"{v}|{n}|fvm|{cell}"] - solid[f"{n}|solid|0.1|8"] for n in names]
            ax.bar(np.arange(len(names)) + 0.27 * (k - 1), vals, 0.27, label=v)
        ax.axhline(0, color="k", lw=0.7)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(names, rotation=20, fontsize=8)
        ax.set_title(f"cell {cell} mm", fontsize=9)
    axs[0].set_ylabel("error of the via effect, K (above 0: part reads too cool)")
    axs[0].legend(fontsize=8)
    fig.savefig(_bootstrap.FIGURES / "fig_04_partial_copper_errors.png", dpi=130, bbox_inches="tight")


if __name__ == "__main__":
    barrel_fig()
    set_fig()
    sys.exit(0)
