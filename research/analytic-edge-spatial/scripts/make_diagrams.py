#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the edge problem of the Analytic model: where the edge heat leaves in each treatment (fig_01) and the section of a board edge with the paths of the heat (fig_02).

@details No data and no program: the shapes only (research/diagram_kit.py). The numbers they quote are those of the README.
         Run from the repository root: .venv/bin/python research/analytic-edge-spatial/scripts/make_diagrams.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

import numpy as np                                                    # noqa: E402
from matplotlib.patches import Rectangle, Polygon                     # noqa: E402

import diagram_kit as dk                                              # noqa: E402

FIG = os.path.join(os.path.dirname(HERE), "figures")


def fig_01():
    """!
    @brief Plan view of the board with a part in a corner: the three treatments of the convective edge.
    @return None.
    """
    fig, axs = dk.canvas(12.5, 4.4, 1, 3)
    titles = ["Edge moved to the faces (the program)", "Robin eigenfunctions", "Edge cells as local heatsinks (prototype)"]
    notes = ["the cosine series has an insulated edge;\nthe edge loss is spread as an extra face\ncoefficient h_edge: right only if the\nedge is at the board mean temperature",
             "the series functions themselves have the\nconvective edge: cos(lam u) / sin(lam u) with\nlam Lh tan(lam Lh) = Bi, lam Lh cot(lam Lh) = -Bi;\nthe loss is taken where the edge is",
             "insulated cosine series + a Green-function\ncorrection with conductances h_side s_l length\nin the ring of edge tiles (1 mm): a dense system,\nthe tile mean stands for the edge value"]
    for k, ax in enumerate(axs):
        ax.set_xlim(-0.8, 6.2)
        ax.set_ylim(-1.7, 4.4)
        ax.set_aspect("equal")
        ax.add_patch(Rectangle((0, 0), 5.4, 3.6, facecolor="#9bbf8a", edgecolor="k", linewidth=1.4))
        ax.add_patch(Rectangle((0, 0), 1.0, 1.0, facecolor=dk.HEAT, edgecolor="k", alpha=0.85))
        ax.text(0.5, 0.5, "part", ha="center", va="center", fontsize=7, color="w")
        ax.set_title(titles[k], fontsize=9)
        ax.text(2.7, -1.05, notes[k], ha="center", va="center", fontsize=7)
        if k == 0:
            # the same extra coefficient everywhere on the face: small arrows over the whole plan
            for x in np.arange(0.9, 5.2, 1.0):
                for y in np.arange(0.9, 3.5, 1.0):
                    if x > 1.2 or y > 1.2:
                        dk.arrow(ax, x, y, x + 0.0, y + 0.45, color="#1f77b4", width=0.9)
            ax.text(3.2, 3.85, "extra h on every face cell", fontsize=7, color="#1f77b4", ha="center")
        elif k == 1:
            # arrows leave at the four edges, longer where the edge is hotter (near the part)
            for x in np.arange(0.3, 5.3, 0.7):
                dk.arrow(ax, x, 0.0, x, -0.35 - 0.5 * np.exp(-x / 1.4), color=dk.BLUE, width=1.1)
                dk.arrow(ax, x, 3.6, x, 3.95 + 0.0, color=dk.BLUE, width=0.8)
            for y in np.arange(0.3, 3.5, 0.7):
                dk.arrow(ax, 0.0, y, -0.35 - 0.5 * np.exp(-y / 1.4), y, color=dk.BLUE, width=1.1)
                dk.arrow(ax, 5.4, y, 5.75, y, color=dk.BLUE, width=0.8)
            ax.text(3.2, 3.95, "loss where the edge is", fontsize=7, color=dk.BLUE, ha="center")
        else:
            for x in 0.3 * np.arange(18):
                for y in (0.0, 3.3):
                    ax.add_patch(Rectangle((x, y), 0.3, 0.3, facecolor="#f1c40f", edgecolor="k", linewidth=0.3, alpha=0.8))
            for y in 0.3 * np.arange(1, 11):
                for x in (0.0, 5.1):
                    ax.add_patch(Rectangle((x, y), 0.3, 0.3, facecolor="#f1c40f", edgecolor="k", linewidth=0.3, alpha=0.8))
            ax.text(3.2, 3.95, "ring of edge tiles", fontsize=7, color="#9a7d0a", ha="center")
    dk.save(fig, os.path.join(FIG, "fig_01_edge_treatments.png"))


def fig_02():
    """!
    @brief Section of a board edge: heat from a corner part flows sideways in the copper to the cooler edge and leaves by the side film.
    @return None.
    """
    fig, axs = dk.canvas(11.5, 4.0, 1, 2, ratios=[1.35, 1])
    ax = axs[0]
    ax.set_xlim(-0.8, 14.0)
    ax.set_ylim(-1.7, 3.3)
    # board section: copper, FR-4, copper from x = 0 (edge) to 11
    ax.add_patch(Rectangle((0, 1.5), 11, 0.18, facecolor=dk.COPPER, edgecolor="k", linewidth=0.8))
    ax.add_patch(Rectangle((0, 0.3), 11, 1.2, facecolor=dk.FR4, edgecolor="k", linewidth=0.8))
    ax.add_patch(Rectangle((0, 0.12), 11, 0.18, facecolor=dk.COPPER, edgecolor="k", linewidth=0.8))
    ax.add_patch(Rectangle((0.0, 1.68), 3.0, 0.5, facecolor=dk.HEAT, edgecolor="k", alpha=0.9))
    ax.text(1.5, 1.93, "part", ha="center", va="center", fontsize=7, color="w")
    ax.text(11.2, 0.85, "FR-4", ha="left", fontsize=7)
    ax.text(11.2, 1.55, "top copper", ha="left", fontsize=7)
    ax.text(11.2, 0.0, "bottom copper", ha="left", fontsize=7)
    for x in (4.0, 6.0, 8.0, 10.0):
        dk.arrow(ax, x, 2.0, x, 2.7, color=dk.BLUE)
        dk.arrow(ax, x, 0.05, x, -0.6, color=dk.BLUE)
    for yy in (0.2, 0.9, 1.6):
        dk.arrow(ax, 0.0, yy, -0.55, yy, color=dk.BLUE, width=1.1)
    ax.text(-0.5, 2.15, "h_side", fontsize=7, color=dk.BLUE)
    ax.text(7.0, 2.85, "h_top", fontsize=7, color=dk.BLUE, ha="center")
    ax.text(7.0, -0.9, "h_bottom", fontsize=7, color=dk.BLUE, ha="center")
    # lateral heat path in the top copper
    dk.arrow(ax, 3.2, 1.78, 9.5, 1.78, color=dk.HEAT, width=1.6)
    ax.text(6.3, 0.85, "heat spreads sideways in the copper", fontsize=7, color=dk.HEAT, ha="center")
    ax.set_title("Section at the edge nearest to the part", fontsize=9)
    ax.text(6.0, -1.45, "the side wall is only copper + FR-4 edge area (35 + 1560 um here): small, and the copper must carry the heat to it", fontsize=7, ha="center")
    # temperature profile along x: the board mean, and the real rise
    ax2 = axs[1]
    ax2.axis("on")
    ax2.set_title("Rise along the section (illustrative)", fontsize=9)
    x = np.linspace(0, 1, 200)
    real = 0.35 + 0.65 * x ** 0.7 * 0.0 + 0.0
    real = 0.25 + 0.75 * np.exp(-3.2 * x)
    ax2.plot(x, real, color=dk.HEAT, label="real rise (edge cooler than the part side)")
    ax2.axhline(real.mean(), color="k", linestyle="--", label="mean: where the faces transfer takes the edge loss")
    ax2.fill_between(x, real, real.mean(), where=real < real.mean(), color=dk.BLUE, alpha=0.25)
    ax2.set_xlabel("position across the board (part side to far edge)", fontsize=7)
    ax2.set_ylabel("rise", fontsize=7)
    ax2.set_yticks([])
    ax2.set_xticks([])
    ax2.legend(fontsize=6, loc="upper right")
    dk.save(fig, os.path.join(FIG, "fig_02_edge_section.png"))


def main():
    """!
    @brief Draw all the diagrams.
    @return int 0.
    """
    os.makedirs(FIG, exist_ok=True)
    fig_01()
    fig_02()
    return 0


if __name__ == "__main__":
    sys.exit(main())
