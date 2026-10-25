"""!
@file make_diagrams.py
@brief Schematic diagrams of the five models of the program: how each one represents the board (cells, nodes, rings, cosine modes, slabs).
@details Pure drawing, no data. Writes figures/fig_08_the_five_models_schematic.png.
         Also writes figures/fig_09_where_models_fail.png (the cases where the reduced models fail) and figures/fig_10_measurement_setup.png (the planned measurement on a physical board).
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
    ax.text(3.0, -1.1, "unknown at the centre of a cell; the reference model;\na one-layer board: two laminate nodes under the copper", ha="center", fontsize=7)
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
    ax.text(0, -4.0, "rings by distance from the footprint, joined by\nresistances; vertical and surface losses per ring;\nrings narrower than a cell are merged", ha="center", fontsize=7)
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
    ax.legend(fontsize=7, loc="upper right")
    ax.text(0.5, 0.65, "T = sum of cos(m pi x / L) cos(n pi y / L) modes;\nlocal corrections for vias and heatsinks", ha="center", fontsize=7, transform=ax.transData)
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
    ax.text(5, 1.2, "real slabs: copper (thin) and laminate gaps (n slabs);\ncells of the plan grid in each slab; steady state only;\nrefused above 250 000 unknowns", ha="center", fontsize=7)
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


def measurement_setup(path):
    """!
    @brief Draw the planned measurement on a physical board: a heater resistor of known electrical power, thermocouples at several distances, an infrared camera looking at a painted area, an ambient thermocouple and a still-air enclosure, with the chain from the reading to the comparison with the models (docs/measurement-protocol.md).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(15, 5.6, 1, 2, ratios=[1.1, 1])
    a = axs[0]
    a.set_xlim(0, 12); a.set_ylim(0, 9)
    a.add_patch(Rectangle((0.5, 0.5), 11, 7.6, fc="none", ec="grey", ls="--"))
    a.text(6, 8.4, "still-air enclosure (nothing blows on the board)", ha="center", fontsize=8, color="grey")
    dk.layer(a, 2.0, 2.4, 8.0, 0.25, "#e0a458"); dk.layer(a, 2.0, 2.65, 8.0, 0.6, "#9bbf8a")
    for x in (3.0, 4.5, 6.0, 7.5):
        a.add_patch(Rectangle((x - 0.15, 3.25), 0.3, 0.3, fc="#2ca02c", ec="k"))
    a.text(5.25, 3.9, "thermocouples at 1, 5, 10, 15 mm", fontsize=7.5, ha="center", color="#2ca02c")
    dk.box(a, 2.2, 3.25, 0.8, 0.5, "R", "#f4b6b6", size=7)
    a.text(1.0, 4.2, "heater resistor,\nV and I measured\n(4 wires): P known", fontsize=7.5, va="bottom")
    a.add_patch(Polygon([[5.0, 7.6], [7.0, 7.6], [6.4, 6.2], [5.6, 6.2]], fc="#d9d9d9", ec="k"))
    a.text(6.0, 7.0, "IR camera", ha="center", fontsize=7)
    a.plot([6.0, 8.6], [6.2, 3.25], ":", color="grey"); a.add_patch(Rectangle((8.3, 3.25), 0.6, 0.15, fc="k"))
    a.text(10.0, 4.3, "area painted matt black\n(known emissivity)", fontsize=7.5, ha="center")
    a.add_patch(Rectangle((10.7, 5.0), 0.3, 0.3, fc="#1f77b4", ec="k")); a.text(10.9, 5.5, "ambient\nthermocouple", fontsize=7, ha="center")
    dk.layer(a, 3.2, 1.6, 0.2, 0.8, "#b9c4cc"); dk.layer(a, 8.6, 1.6, 0.2, 0.8, "#b9c4cc")
    a.text(6, 1.0, "board on thin supports, horizontal, layer 1 up", ha="center", fontsize=8)
    a.text(6, 0.1, "", fontsize=1)
    a = axs[1]
    a.set_xlim(0, 10); a.set_ylim(0, 9)
    a.text(5, 8.4, "from the reading to the comparison", ha="center", fontsize=9, fontweight="bold")
    steps = [("measure the board:\ncopper thickness, stack-up,\nemissivity of a coupon", 7.0), ("steady state at three powers\n(checks the non-linearity of h)", 5.6),
             ("run the five models on the\nGerber of the same board", 4.2), ("compare in K and in % of the rise,\nwith the uncertainty of the reading", 2.8),
             ("fit h on one power, predict\nthe others (calibrate_convection)", 1.4)]
    for t, y in steps:
        dk.box(a, 1.2, y - 0.5, 7.6, 1.0, t, "#cfe3f5", size=7.5)
    for y in (7.0, 5.6, 4.2, 2.8):
        dk.arrow(a, 5, y - 0.5, 5, y - 0.9)
    dk.save(fig, path, "Planned: a measurement on a physical board (docs/measurement-protocol.md)")


def main():
    """!
    @brief Draw the five models, the cases where the reduced models fail and the planned measurement, and save the three figures.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig, axs = dk.canvas(17, 4.6, 1, 5)
    fvm(axs[0])
    fdm(axs[1])
    lumped(axs[2])
    analytic(axs[3])
    solid3d(axs[4])
    dk.save(fig, OUT / "fig_08_the_five_models_schematic.png", "The five models of the program: how each one represents the board")
    measurement_setup(OUT / "fig_10_measurement_setup.png")
    where_models_fail(OUT / "fig_09_where_models_fail.png")


if __name__ == "__main__":
    main()
