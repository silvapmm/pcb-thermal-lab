#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Schematic figures of `research/fin-channel-sources/`: the two flow topologies of a finned base (vertical channels and a horizontal base with a chimney) and the unit cell of the array model of Bar-Cohen, Iyengar and Kraus (2003).
@details No data is computed. Writes figures/fig_01_two_flow_topologies.png and figures/fig_06_array_unit_cell.png (the numbers 02 to 05 belong to `make_figures.py`, one numbering for both).
         Run: .venv/bin/python research/fin-channel-sources/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

from matplotlib.patches import Rectangle                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"
HOT = "#e07b6a"


def vertical_panel(ax):
    """!
    @brief Fins on a vertical base: vertical channels open at the bottom and top, the case of the Elenbaas correlation (section view across the fins).
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.5, 7.5)
    ax.set_aspect("equal")
    ax.add_patch(Rectangle((0.5, 0.5), 9, 0.5, facecolor=dk.METAL, edgecolor="k"))
    ax.text(5, 0.75, "base (vertical board face)", ha="center", va="center", fontsize=7)
    for i in range(4):
        x = 1.2 + i * 2.2
        ax.add_patch(Rectangle((x, 1.0), 0.35, 5.0, facecolor=HOT, edgecolor="k"))
    for i in range(3):
        xc = 1.55 + i * 2.2 + 0.9
        dk.arrow(ax, xc, 0.2, xc, 1.7, color=dk.BLUE)
        dk.arrow(ax, xc, 5.4, xc, 6.9, color=dk.BLUE)
    ax.text(5, 7.2, "air leaves at the top", ha="center", fontsize=7)
    ax.text(5, -0.3, "air enters at the bottom (channel length L = height of the fins' flow path)", ha="center", fontsize=7)
    ax.set_title("fins on a vertical base: vertical channels\n(Elenbaas 1942; Bar-Cohen and Rohsenow 1984)", fontsize=8)
    ax.axis("off")


def horizontal_panel(ax):
    """!
    @brief Fins up on a horizontal base: the air enters at the two open ends and rises in a central chimney (Harahap and McManus; Tari and Mehrtash).
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.5, 7.5)
    ax.set_aspect("equal")
    ax.add_patch(Rectangle((0.5, 0.5), 9, 0.5, facecolor=dk.METAL, edgecolor="k"))
    ax.text(5, 0.75, "horizontal base, length L (flow along the fins)", ha="center", va="center", fontsize=7)
    ax.add_patch(Rectangle((0.5, 1.0), 9, 2.2, facecolor=HOT, edgecolor="k", alpha=0.55))
    ax.text(5, 2.1, "fins seen from the side (height H);\nthe channels run along the page", ha="center", va="center", fontsize=6.5)
    dk.arrow(ax, -0.2, 1.7, 1.2, 1.7, color=dk.BLUE)
    dk.arrow(ax, 10.2, 1.7, 8.8, 1.7, color=dk.BLUE)
    dk.arrow(ax, 1.6, 2.7, 4.1, 3.9, color=dk.BLUE)
    dk.arrow(ax, 8.4, 2.7, 5.9, 3.9, color=dk.BLUE)
    dk.arrow(ax, 4.6, 3.4, 4.6, 5.9, color=dk.BLUE)
    dk.arrow(ax, 5.4, 3.4, 5.4, 5.9, color=dk.BLUE)
    ax.text(5, 6.3, "central chimney", ha="center", fontsize=7)
    ax.text(0.9, 4.2, "inflow from\nboth ends", ha="center", fontsize=7)
    ax.text(5, 7.2, "fin spacing S is across the page, the channel is open on top", ha="center", fontsize=6.5)
    ax.set_title("fins up on a horizontal base: two inflows and one chimney\n(no closed vertical channel; the arrays of section 7 are of this kind)", fontsize=8)
    ax.axis("off")


def fig_01():
    """!
    @brief Figure 1: the two flow topologies side by side.
    @return None.
    """
    fig, axs = dk.canvas(9.2, 4.6, 1, 2)
    vertical_panel(axs[0])
    horizontal_panel(axs[1])
    dk.save(fig, OUT / "fig_01_two_flow_topologies.png")


def fig_06():
    """!
    @brief Figure 6: the unit cell of the array model of Bar-Cohen, Iyengar and Kraus (2003): one fin, the free base of width s and the three heat paths of equation 2.
    @return None.
    """
    fig, ax = dk.canvas(7.6, 4.6)
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.2, 7.2)
    ax.set_aspect("equal")
    ax.add_patch(Rectangle((0.5, 0.2), 9, 0.7, facecolor=dk.METAL, edgecolor="k"))
    ax.text(5, 0.55, "isothermal base at theta_b", ha="center", va="center", fontsize=7)
    ax.add_patch(Rectangle((2.8, 0.9), 0.5, 5.0, facecolor=HOT, edgecolor="k"))
    ax.add_patch(Rectangle((7.3, 0.9), 0.5, 5.0, facecolor=HOT, edgecolor="k"))
    ax.annotate("", (3.3, 6.3), (7.3, 6.3), arrowprops={"arrowstyle": "<->"})
    ax.text(5.3, 6.5, "s (the channel)", ha="center", fontsize=7)
    ax.annotate("", (2.8, 5.4), (3.3, 5.4), arrowprops={"arrowstyle": "<->"})
    ax.text(3.05, 5.7, "t", ha="center", fontsize=7)
    ax.annotate("", (1.4, 0.9), (1.4, 5.9), arrowprops={"arrowstyle": "<->"})
    ax.text(1.0, 3.4, "H", ha="center", fontsize=8)
    dk.arrow(ax, 3.3, 3.0, 4.2, 3.0, color=dk.HEAT, label="")
    dk.arrow(ax, 7.3, 3.0, 6.4, 3.0, color=dk.HEAT, label="")
    ax.text(5.3, 3.3, "h_fin = Nu_fin k / s", ha="center", fontsize=7, color=dk.HEAT)
    ax.text(5.3, 2.5, "Nu_fin: eq. 13, argument eta El", ha="center", fontsize=6.5)
    dk.arrow(ax, 5.3, 0.9, 5.3, 1.9, color=dk.HEAT)
    ax.text(5.3, 1.25, "h_base A_b,f theta_b", ha="left", fontsize=6.5, color=dk.HEAT)
    dk.arrow(ax, 3.05, 6.0, 3.05, 6.9, color=dk.HEAT)
    ax.text(0.6, -0.55, "q_T = n_fin (q_fin + h_base L s theta_b),   q_fin = L k t theta_b m tanh(mH),   m = (2 h_fin / k t)^(1/2),   eta = tanh(mH) / mH",
            fontsize=7, ha="left")
    ax.text(0.6, -1.0, "the fin wall excess is eta theta_b, so the Elenbaas number of the channel uses eta El (the fixed point is solved for h_fin)", fontsize=7, ha="left")
    ax.set_title("Unit cell of the plate-fin array (Bar-Cohen, Iyengar and Kraus 2003, equations 1 to 14)", fontsize=9)
    dk.save(fig, OUT / "fig_06_array_unit_cell.png")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_01()
    fig_06()
    print("figures written to", OUT)
