#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_figures.py
@brief Figures of the investigation: the board with its bare-laminate corner (fig_01) and the board maximum against the cell size (fig_02).
@details Run from the repository root: `nice -n 10 .venv/bin/python research/drawn-ell-fvm-fdm/scripts/make_figures.py`. fig_02 re-runs the FVM and the FDM at six cells
         (a few seconds each); the finite-element reference line is the plateau printed by `study_graded_fem.py` (105.25, 105.08, 105.26 K at plan sizes 0.25, 0.125 and 0.0625 mm).
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                     # noqa: E402
from matplotlib.patches import Rectangle            # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import study_readouts as S                          # noqa: E402

OUT = HERE.parent / "figures"
REF_PEAK = 105.2        # K, plateau of study_graded_fem.py (mean of the three finest, printed 105.248, 105.079, 105.262)


def fig_board():
    """!
    @brief Top view of the L board: copper, part, bare-laminate corner and the cell lines of the 1 mm grid.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(5.6, 5.4))
    ax.add_patch(Rectangle((0, 0), 20, 20, fc="#f3e9c6", ec="k", lw=1.2))                           # laminate (board)
    for (x0, y0, x1, y1) in [(1.2, 1.2, 18.8, 10.8), (1.2, 10.8, 10.8, 18.8)]:                      # top copper, the L
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#d98b4a", ec="none", alpha=0.85))
    ax.add_patch(Rectangle((8, 8), 4, 4, fc="none", ec="crimson", lw=2))                            # the part
    ax.add_patch(Rectangle((10.8, 10.8), 1.2, 1.2, fc="#ffe9e9", ec="crimson", hatch="///", lw=0))  # the bare corner under the part
    for g in range(21):
        ax.axvline(g, color="0.8", lw=0.4, zorder=0)
        ax.axhline(g, color="0.8", lw=0.4, zorder=0)
    ax.annotate("bare laminate under the part\n(1.2 x 1.2 mm), hottest point", (11.4, 11.4), (12.6, 15.5), arrowprops=dict(arrowstyle="->"), fontsize=8)
    ax.text(3, 5, "top copper (L)\nbottom copper 1.2 mm\ninside the wall", fontsize=8)
    ax.text(8.2, 7.2, "part, 4 mm, 1 W", color="crimson", fontsize=8)
    ax.set_xlim(-0.5, 20.5)
    ax.set_ylim(-0.5, 20.5)
    ax.set_aspect("equal")
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_title("drawn_ell, top view, 1 mm grid lines")
    fig.tight_layout()
    fig.savefig(OUT / "fig_01_board_and_bare_corner.png", dpi=130)


def fig_cells():
    """!
    @brief Board maximum of the FVM and the FDM against the cell, with the resolved reference.
    @return None.
    """
    cells = [2.0, 1.0, 0.8, 0.5, 0.4, 0.25, 0.2]
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    for m, mk in (("fvm", "o-"), ("fdm", "s--")):
        ax.plot(cells, [S.run_one("drawn_ell", m, c)["tmax"] for c in cells], mk, label=f"{m.upper()} board maximum (hottest node)")
    ax.axhline(REF_PEAK, color="k", lw=1.2, label="independent FEM, converged (105.2 K)")
    ax.set_xscale("log")
    ax.invert_xaxis()
    ax.set_xlabel("cell (mm)")
    ax.set_ylabel("board maximum, rise over ambient (K)")
    ax.set_title("drawn_ell: the hottest point does not converge monotonically")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "fig_02_board_maximum_against_cell.png", dpi=130)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_board()
    fig_cells()
