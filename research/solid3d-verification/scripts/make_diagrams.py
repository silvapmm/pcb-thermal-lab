"""!
@file make_diagrams.py
@brief Schematic diagrams of the layered models against the 3D solid: one node per copper layer with sheet conductances, against real slabs with the vertical gradient resolved, and the verification ladder against exact and independent references.
@details Pure drawing; the accuracy numbers quoted (FVM within 0.4 to 2.4 % of the 3D rise, Lumped 2 to 7 %, Analytic 0.2 % on uniform copper and up to 24 % with a 20 mm pad) are those of the README of this folder. Writes figures/fig_04_layered_vs_3d_schematic.png.
         Also writes figures/fig_08_heat_spreading_layered_and_3d.png (spreading under a small heater, layered and 3D).
         Run: .venv/bin/python research/solid3d-verification/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

from matplotlib.patches import Circle, Polygon, Rectangle                 # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def layered(ax):
    """!
    @brief The layered idealisation: one temperature node per copper layer, a sheet conductance in the plane and a conductance between nodes.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ys = [7.0, 4.8, 2.6]
    for k, y in enumerate(ys):
        dk.layer(ax, 1.5, y, 9, 0.35, dk.COPPER)
        ax.plot([2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5], [y + 0.17] * 8, "ko", markersize=4)
        ax.text(0.2, y + 0.1, f"layer {k + 1}", fontsize=7)
        if k < 2:
            dk.layer(ax, 1.5, y - 1.6, 9, 1.6, dk.FR4)
            ax.annotate("", (6.0, y - 1.6), (6.0, y), arrowprops={"arrowstyle": "<->", "color": dk.BLUE, "linewidth": 1.8})
            ax.text(6.2, y - 0.9, "conductance between nodes\n(laminate, vias)", fontsize=6.5, color=dk.BLUE)
    ax.text(6, 8.3, "in the plane: the sheet conductance of the copper plus the laminate share", ha="center", fontsize=7)
    ax.text(6, 0.9, "the temperature is uniform across the thickness of a node;\nthe cheapest and the reference of the program's models", ha="center", fontsize=7.5, style="italic")
    ax.set_title("1. the layered models (FVM, FDM, Lumped, Analytic)", fontsize=9)


def slabs(ax):
    """!
    @brief The 3D solid: copper slabs, several laminate slabs per gap, a via as a copper rod, heat in the top slab.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ys = [7.0, 4.8, 2.6]
    for k, y in enumerate(ys):
        dk.layer(ax, 1.5, y, 9, 0.35, dk.COPPER)
        if k < 2:
            for t in range(4):
                dk.layer(ax, 1.5, y - 0.4 * (t + 1), 9, 0.4, dk.FR4)
    dk.layer(ax, 5.8, 2.6, 0.5, 4.75, dk.COPPER)
    ax.text(6.5, 5.9, "via: copper rod\n(barrel area)", fontsize=6.5)
    ax.annotate("", (3.5, 7.5), (3.5, 7.35), arrowprops={"arrowstyle": "->", "color": dk.HEAT, "linewidth": 2})
    dk.arrow(ax, 3.5, 8.4, 3.5, 7.4, color=dk.HEAT, width=2)
    ax.text(3.8, 8.1, "heat enters on the copper slab", fontsize=7, color=dk.HEAT)
    ax.text(6, 0.9, "the vertical gradient inside each gap is resolved (n slabs);\nplan cells in every slab; steady state only", ha="center", fontsize=7.5, style="italic")
    ax.set_title("2. the 3D solid: real slabs", fontsize=9)


def ladder(ax):
    """!
    @brief The verification ladder: exact solutions, convergence, an independent finite-element solution, and what the layered models do against it.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    steps = [("exact solutions: a spreading resistance (Yovanovich), uniform cases", "#cfe3f5"),
             ("grid convergence of the solid (a convergence index)", "#cfe3f5"),
             ("an independent 3D finite-element solution (offline)", "#d6ecd0"),
             ("layered models against it: FVM within 0.4 to 2.4 % of the 3D rise,\nLumped 2 to 7 %, Analytic 0.2 % on uniform copper, up to 24 % with a 20 mm pad", "#fbe3c2")]
    for k, (t, c) in enumerate(steps):
        y = 7.6 - 2.4 * k
        dk.box(ax, 0.3, y, 9.4, 1.7, t, c, k == 3, 7.5)
        if k:
            dk.arrow(ax, 5, y + 2.4, 5, y + 1.7)
    ax.set_title("3. how the solid and the layered models were verified", fontsize=9)


def spreading(path):
    """!
    @brief Draw a small heater on a copper pad: the heat leaving through the thickness and the layered model's single node per layer, and the outer copper that dissipates by itself (README 2).
    @param path Output file.
    @return None.
    """
    fig, (a1, a2, a3) = dk.canvas(15, 5.0, 1, 3)
    for a in (a1, a2, a3):
        a.set_xlim(0, 10)
        a.set_ylim(-1.0, 8.0)
    # layered: one node per copper layer, heat moves in the plane
    dk.layer(a1, 0.5, 5.3, 9.0, 0.2, dk.COPPER)
    dk.layer(a1, 0.5, 3.5, 9.0, 1.8, dk.FR4)
    dk.layer(a1, 0.5, 3.3, 9.0, 0.2, dk.COPPER)
    dk.box(a1, 4.0, 6.0, 2.0, 0.8, "heater", "#f4b6b6", size=8)
    for x in (1.2, 8.8):
        dk.arrow(a1, 5.0, 5.4, x, 5.4, color=dk.HEAT, width=1.0)
    dk.arrow(a1, 5.0, 5.3, 5.0, 3.4, color=dk.HEAT, width=1.4)
    for y in (5.4, 3.4):
        a1.plot([5.0], [y], "ks", markersize=6)
    a1.text(5, 7.6, "layered models", ha="center", fontsize=9, fontweight="bold")
    a1.text(5, 2.6, "one node per copper layer:\nheat spreads in the plane of the node\nand through one conductance between nodes", ha="center", va="top", fontsize=7.5)
    # 3D: heat also spreads in a cone inside the laminate
    dk.layer(a2, 0.5, 5.3, 9.0, 0.2, dk.COPPER)
    dk.layer(a2, 0.5, 3.5, 9.0, 1.8, dk.FR4)
    dk.layer(a2, 0.5, 3.3, 9.0, 0.2, dk.COPPER)
    dk.box(a2, 4.0, 6.0, 2.0, 0.8, "heater", "#f4b6b6", size=8)
    for k in range(-3, 4):
        a2.annotate("", (5.0 + k * 0.9, 3.45), (5.0 + k * 0.18, 5.3), arrowprops={"arrowstyle": "->", "color": dk.HEAT, "linewidth": 1.0})
    a2.text(5, 7.6, "3D solid", ha="center", fontsize=9, fontweight="bold")
    a2.text(5, 2.6, "real slabs: the heat also fans out inside\nthe laminate; on uniform boards the layered\nmodels land within 0.7 % of it", ha="center", va="top", fontsize=7.5)
    # one-sided pad dissipating
    dk.layer(a3, 0.5, 3.5, 9.0, 1.8, dk.FR4)
    dk.layer(a3, 2.5, 5.3, 5.0, 0.25, dk.COPPER)
    dk.box(a3, 4.0, 6.0, 2.0, 0.8, "heater", "#f4b6b6", size=8)
    dk.arrow(a3, 5.0, 6.0, 5.0, 5.6, color=dk.HEAT, width=1.4)
    for x in (2.8, 3.6, 6.4, 7.2):
        dk.arrow(a3, x, 5.7, x, 6.9, color=dk.BLUE, width=1.0)
    a3.text(5, 7.6, "copper pad on one side, no vias", ha="center", fontsize=9, fontweight="bold")
    a3.text(5, 2.6, "the pad dissipates and spreads by itself;\nLumped up to +107 %, Analytic up to -63 %\n(the input checks warn)", ha="center", va="top", fontsize=7.5, color=dk.HEAT)
    dk.save(fig, path, "Heat spreading in the layered models and in the 3D solid (README 2)")


def main():
    """!
    @brief Draw the three panels and save the figure.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig, axs = dk.canvas(16, 5.6, 1, 3)
    layered(axs[0])
    slabs(axs[1])
    ladder(axs[2])
    dk.save(fig, OUT / "fig_04_layered_vs_3d_schematic.png", "The layered models and the 3D solid: schematics")
    spreading(OUT / "fig_08_heat_spreading_layered_and_3d.png")


if __name__ == "__main__":
    main()
