"""!
@file make_diagrams.py
@brief Schematic diagrams of the five models of the program: how each one represents the board (cells, nodes, rings, cosine modes, slabs).
@details Pure drawing, no data. Writes figures/fig_04_the_five_models_schematic.png.
         Also writes figures/fig_05_where_models_fail.png (the cases where the reduced models fail).
         Run: .venv/bin/python research/models-comparison/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

from matplotlib.patches import Circle, Polygon, Rectangle                 # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def fvm(ax):
    """!
    @brief Cell-centred finite volumes: cells with their centre and a face conductance between neighbours.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(-0.2, 6.2)
    ax.set_ylim(-1.6, 6.4)
    ax.set_aspect("equal")
    for i in range(6):
        for j in range(6):
            ax.add_patch(Rectangle((i, j), 1, 1, fill=(i in (2, 3) and j in (2, 3)), facecolor="#f7d4d4", edgecolor="k", linewidth=0.7))
            ax.plot(i + 0.5, j + 0.5, "k.", markersize=3)
    ax.annotate("", (3.5, 2.5), (2.5, 2.5), arrowprops={"arrowstyle": "<->", "color": dk.BLUE, "linewidth": 2})
    ax.text(3.0, 2.2, "face", color=dk.BLUE, fontsize=7, ha="center")
    ax.text(3.0, -1.1, "unknown at the centre of a cell;\nthe reference model", ha="center", fontsize=7)
    ax.set_title("FVM (reference)\ncell-centred finite volumes", fontsize=9)


def fdm(ax):
    """!
    @brief Node-centred finite differences: nodes on a grid, half cells at the border.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(-0.2, 6.2)
    ax.set_ylim(-1.6, 6.4)
    ax.set_aspect("equal")
    for i in range(7):
        for j in range(7):
            ax.plot(i * 6 / 6.0, j, "ko", markersize=3 if 0 < i < 6 and 0 < j < 6 else 5)
            if i < 6:
                ax.plot([i, i + 1], [j, j], color="0.6", linewidth=0.8)
            if j < 6:
                ax.plot([i, i], [j, j + 1], color="0.6", linewidth=0.8)
    ax.add_patch(Rectangle((-0.5, -0.5), 7, 7, fill=False, edgecolor="r", linestyle=":", linewidth=0.8))
    ax.text(3.0, -1.1, "unknowns on the nodes; border nodes own half a cell;\nsame layered physics as the FVM", ha="center", fontsize=7)
    ax.set_title("FDM\nnode-centred finite differences", fontsize=9)


def lumped(ax):
    """!
    @brief The ring network around a heater footprint.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(-3.4, 3.4)
    ax.set_ylim(-4.6, 3.4)
    ax.set_aspect("equal")
    ax.add_patch(Rectangle((-0.6, -0.6), 1.2, 1.2, facecolor="#f7d4d4", edgecolor="k"))
    for r in (1.0, 1.7, 2.4, 3.0):
        ax.add_patch(Rectangle((-r, -r), 2 * r, 2 * r, fill=False, edgecolor=dk.BLUE, linewidth=1.2))
    for r0, r1 in ((0.6, 1.0), (1.0, 1.7), (1.7, 2.4), (2.4, 3.0)):
        ax.plot([r0 + 0.02, r1 - 0.02], [0, 0], color="k", linewidth=2)
    ax.text(0, -4.0, "rings by distance from the footprint, joined by\nresistances; vertical and surface losses per ring", ha="center", fontsize=7)
    ax.set_title("Lumped (LPTN)\nthermal network of rings per heater", fontsize=9)


def analytic(ax):
    """!
    @brief The first modes of the cosine series.
    @param ax Axes.
    @return None.
    """
    ax.axis("on")
    x = np.linspace(0, 1, 200)
    for m in (1, 2, 3, 4):
        ax.plot(x, np.cos(m * np.pi * x) / m + 3 - m * 0.0, label=f"m = {m}", linewidth=1.4)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["0", "L"])
    ax.set_yticks([])
    ax.legend(fontsize=7, loc="lower left")
    ax.text(0.5, 0.75, "T = sum of cos(m pi x / L) cos(n pi y / L) modes;\nlocal corrections for vias and heatsinks", ha="center", fontsize=7, transform=ax.transData)
    ax.set_ylim(0.6, 4.6)
    ax.set_title("Analytic (Fourier series)\nmultilayer cosine series", fontsize=9)


def solid3d(ax):
    """!
    @brief The slabs of the 3D solid: copper slabs, laminate gaps, via rods.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ys = [6.4, 5.0, 3.6, 2.2]
    for k, y in enumerate(ys):
        dk.layer(ax, 1, y, 8, 0.25, dk.COPPER)
        if k < 3:
            for t in range(3):
                dk.layer(ax, 1, y - 0.45 * (t + 1), 8, 0.45, dk.FR4)
    dk.layer(ax, 4.6, 2.2, 0.5, 4.45, dk.COPPER)
    ax.text(5.3, 7.2, "via: a copper rod of the barrel's area", fontsize=7)
    ax.text(5, 1.2, "real slabs: copper (thin) and laminate gaps (n slabs);\ncells of the plan grid in each slab; steady state only", ha="center", fontsize=7)
    ax.set_title("3D solid\nfinite volumes with real slabs", fontsize=9)


def board_case(ax, title, copper, heater, result):
    """!
    @brief Draw one top view of a board with a copper zone and a heater, with the error the Lumped and Analytic models make on it.
    @param ax Axes.
    @param title Title of the drawing.
    @param copper Copper zone as (x, y, width, height) on a 10 x 7 board.
    @param heater Heater as (x, y, width, height).
    @param result Text with the errors.
    @return None.
    """
    ax.set_xlim(0, 10)
    ax.set_ylim(-1.6, 8.0)
    ax.set_aspect("equal")
    ax.add_patch(Rectangle((0, 0), 10, 7, facecolor=dk.FR4, edgecolor="k"))
    ax.add_patch(Rectangle(copper[:2], copper[2], copper[3], facecolor=dk.COPPER, edgecolor="k"))
    ax.add_patch(Rectangle(heater[:2], heater[2], heater[3], facecolor="#c0392b", edgecolor="k"))
    ax.text(5, 7.5, title, ha="center", fontsize=9, fontweight="bold")
    ax.text(5, -0.3, result, ha="center", va="top", fontsize=7.5, color=dk.HEAT)


def where_models_fail(path):
    """!
    @brief Draw the cases where the Lumped and Analytic models stop being reliable, next to an ordinary one (README 2).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(15, 4.6, 1, 4)
    board_case(axs[0], "ordinary board", (0.5, 0.5, 9.0, 6.0), (4.0, 2.7, 2.0, 1.6), "every model within a few\npercent of the FVM")
    board_case(axs[1], "copper edge across a heater", (0.5, 0.5, 4.5, 6.0), (3.6, 2.7, 2.8, 1.6), "Lumped -27 %, Analytic -25 %\n(the input checks warn)")
    board_case(axs[2], "heater in a corner", (0.5, 0.5, 9.0, 6.0), (0.7, 0.7, 1.8, 1.6), "Lumped -8.7 %")
    board_case(axs[3], "long thin heater", (0.5, 0.5, 9.0, 6.0), (1.0, 3.2, 8.0, 0.6), "Lumped +9.5 %")
    dk.save(fig, path, "Where the reduced models stop being reliable (error against the FVM, README 2)")


def main():
    """!
    @brief Draw the five models and save the figure.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig, axs = dk.canvas(17, 4.6, 1, 5)
    fvm(axs[0])
    fdm(axs[1])
    lumped(axs[2])
    analytic(axs[3])
    solid3d(axs[4])
    dk.save(fig, OUT / "fig_04_the_five_models_schematic.png", "The five models of the program: how each one represents the board")
    where_models_fail(OUT / "fig_05_where_models_fail.png")


if __name__ == "__main__":
    main()
