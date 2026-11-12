#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Data figure of the via-well-sheet-order investigation: the shift of the hottest rise when the well reads the sheet after the laminate rule, against the cell, FVM and FDM.
@details Runs the program (imported, never edited) on the boards of `lib/cases.py` with a via 3 mm and 0.16 mm from the right edge, h_side 10 W/m2K, two layers, fill 1 and 0.2,
         cells 1, 0.5, 0.25 mm; about ten seconds. Writes `figures/fig_02_order_shift_vs_cell.png`.
         Run from the repository root: `.venv/bin/python research/via-well-sheet-order/scripts/make_figures.py`.
"""

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "lib"))
import cases                                                                # noqa: E402
import matplotlib                                                           # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                             # noqa: E402

FIG = os.path.join(HERE, "figures")
CELLS = [1.0, 0.5, 0.25]


def shift_vs_cell():
    """!
    @brief Plot the shift after - before of the hottest rise against the cell.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for model, ls in (("fvm", "-"), ("fdm", "--")):
        for fill, d, color in ((1.0, 0.16, "#1f77b4"), (0.2, 3.0, "#d62728"), (0.2, 0.16, "#ff7f0e")):
            p = cases.board(2, fill, 10.0, d)
            ys = [1000 * (cases.rise(p, c, model, "after") - cases.rise(p, c, model, "before")) for c in CELLS]
            ax.plot(CELLS, ys, ls, marker="o", color=color, label=f"{model.upper()}, fill {fill:g}, via {d:g} mm from the edge")
    ax.set_xscale("log")
    ax.set_xticks(CELLS)
    ax.minorticks_off()
    ax.set_xticklabels([f"{c:g}" for c in CELLS])
    ax.set_xlabel("cell (mm)")
    ax.set_ylabel("hottest rise, after - before (mK)")
    ax.set_title("Two layers, h_side 10 W/m2K: the other order reads hotter by tens of mK at most", fontsize=9)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_02_order_shift_vs_cell.png"), dpi=105)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    shift_vs_cell()
