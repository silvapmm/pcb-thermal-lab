"""!
@file make_diagrams.py
@brief Schematic diagrams of the layered models against the 3D solid: one node per copper layer with sheet conductances, against real slabs with the vertical gradient resolved, and the verification ladder against exact and independent references.
@details Pure drawing; the accuracy numbers quoted (FVM within 0.4 to 2.4 % of the 3D rise, Lumped 2 to 7 %, Analytic 0.2 % on uniform copper and up to 24 % with a 20 mm pad) are those of the README of this folder. Writes figures/fig_04_layered_vs_3d_schematic.png.
         Run: .venv/bin/python research/solid3d-verification/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

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


if __name__ == "__main__":
    main()
