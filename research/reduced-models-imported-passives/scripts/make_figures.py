#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures of the data: the ladder of rises from the uniform sheet to the imported copper, the cell convergence of the FVM reference, and the error against the local variables.
@details Reads out/decomposition_*.csv, out/decomposition_rp2040_0.5_kappa.csv and out/convergence_rp2040.csv (the studies must have been run). Writes fig_03_ladder.png,
         fig_04_cell_convergence.png, fig_05_error_vs_variables.png into figures/. Run: .venv/bin/python research/reduced-models-imported-passives/scripts/make_figures.py
"""

import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
FIG = HERE.parent / "figures"


def read(path):
    """!
    @brief Read a CSV with numbers as floats.
    @param path File.
    @return list of dict.
    """
    return [{k: (float(v) if k not in ("board", "part") else v) for k, v in r.items()} for r in csv.DictReader(open(path))]


def fig_ladder():
    """!
    @brief Rise of each part against the copper treatment, from the uniform sheet to the imported copper; the reduced models as end markers.
    @return None.
    """
    rows = read(OUT / "decomposition_rp2040_0.5.csv")
    steps = ["F_unif", "F_t10", "F_t5", "F_t2", "F_t1", "F_fill", "F_imp"]
    labels = ["uniform\nsheet", "tiles\n10 mm", "tiles\n5 mm", "tiles\n2 mm", "tiles\n1 mm", "cell fill\n0.5 mm", "imported\n(faces)"]
    fig, ax = plt.subplots(figsize=(9, 5))
    for r in rows:
        c = "#1f77b4" if r["side_mm"] < 1.5 else ("#e08a00" if r["side_mm"] < 3 else "#2ca02c")
        ax.plot(range(7), [r[s] for s in steps], "-", color=c, alpha=0.55, lw=1)
        ax.plot([7.2], [r["L_imp"]], "v", color=c, ms=4); ax.plot([7.6], [r["A_imp"]], "^", color=c, ms=4)
    ax.set_xticks(list(range(7)) + [7.2, 7.6]); ax.set_xticklabels(labels + ["Lumped", "Analytic"], fontsize=7)
    ax.set_yscale("log"); ax.set_ylabel("rise of the hottest copper node for 1 W (K)")
    ax.plot([], [], color="#1f77b4", label="part side < 1.5 mm (0402 and the like)"); ax.plot([], [], color="#e08a00", label="1.5 to 3 mm"); ax.plot([], [], color="#2ca02c", label="> 3 mm")
    ax.legend(fontsize=7); ax.grid(alpha=0.3, which="both")
    ax.set_title("RP2040, 27 heat sources, cell 0.5 mm: the FVM rise grows as finer copper is shown; the reduced models stay at the left", fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "fig_03_ladder.png", dpi=105)


def fig_convergence():
    """!
    @brief FVM rise against the cell for the imported copper and the arithmetic cell fill, per part.
    @return None.
    """
    rows = read(OUT / "convergence_rp2040.csv")
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for n in sorted({r["part"] for r in rows}):
        s = sorted([r for r in rows if r["part"] == n], key=lambda r: -r["cell"])
        ax.plot([r["cell"] for r in s], [r["imported"] for r in s], "o-", label=n + " imported")
        ax.plot([r["cell"] for r in s], [r["fill"] for r in s], "x--", alpha=0.5, color=ax.lines[-1].get_color())
    ax.set_xscale("log"); ax.invert_xaxis(); ax.set_xlabel("cell (mm)"); ax.set_ylabel("FVM rise for 1 W (K)")
    ax.set_xticks([1, 0.5, 0.25]); ax.set_xticklabels(["1", "0.5", "0.25"]); ax.legend(fontsize=6, ncol=2); ax.grid(alpha=0.3)
    ax.set_title("FVM reference of the small parts against the cell (solid: imported copper; dashed: arithmetic fill)", fontsize=8)
    fig.tight_layout(); fig.savefig(FIG / "fig_04_cell_convergence.png", dpi=105)


def fig_variables():
    """!
    @brief Lumped and Analytic error against four local variables (RP2040, 27 parts).
    @return None.
    """
    rows = read(OUT / "decomposition_rp2040_0.5_kappa.csv")
    fig, axs = plt.subplots(1, 4, figsize=(13, 3.6), sharey=True)
    for ax, (k, t) in zip(axs, (("side_mm", "part side (mm)"), ("kappa_5", "constriction factor kappa (5 mm window)"), ("fill_5", "copper fill in 10 x 10 mm"), ("dist_bare_mm", "distance to bare laminate (mm)"))):
        x = np.array([min(r[k], 100.0) for r in rows])
        ax.plot(x, [100 * (r["L_imp"] / r["F_imp"] - 1) for r in rows], "v", color="#1f77b4", label="Lumped")
        ax.plot(x, [100 * (r["A_imp"] / r["F_imp"] - 1) for r in rows], "^", color="#d62728", label="Analytic")
        ax.set_xlabel(t, fontsize=8); ax.grid(alpha=0.3)
        if k == "kappa_5":
            ax.set_xscale("log")
    axs[0].set_ylabel("model against FVM (%)"); axs[0].legend(fontsize=7)
    fig.suptitle("No single local variable explains the error (cut-off pads plotted at kappa = 100)", fontsize=9)
    fig.tight_layout(); fig.savefig(FIG / "fig_05_error_vs_variables.png", dpi=105)


if __name__ == "__main__":
    FIG.mkdir(exist_ok=True)
    fig_ladder(); fig_convergence(); fig_variables()
