"""!
@file make_diagrams.py
@brief Schematic diagrams of the Gerber models phase: the laminate the 3D solid lacks under a single copper layer (README 4.39) and the chain of references used to validate the models on the rectangle board (README 4.37).
@details Pure drawing, no data and no program; every number is quoted from the README sections named. Writes figures/fig_13_laminate_single_layer_schematic.png and figures/fig_14_validation_chain_schematic.png.
         Run: .venv/bin/python research/gerber-models/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def stack(ax, x, with_laminate, title, result):
    """!
    @brief The cross-section of a single-copper-layer board under a heater, with or without the laminate slab.
    @param ax Axes.
    @param x Left of the drawing.
    @param with_laminate True to draw the laminate slab under the copper.
    @param title Title of the drawing.
    @param result Text with the heater temperature found.
    @return None.
    """
    dk.layer(ax, x, 3.0, 4.4, 0.35, dk.COPPER, "one copper layer")
    if with_laminate:
        dk.layer(ax, x, 1.6, 4.4, 1.4, dk.FR4, "laminate slab")
    else:
        ax.text(x + 2.2, 2.3, "(no slab: the sheet\\nhas no way down)".replace("\\n", "\n"), ha="center", fontsize=7, style="italic")
    dk.box(ax, x + 1.5, 3.7, 1.4, 0.6, "heater", "#f4b6b6", size=8)
    dk.arrow(ax, x + 2.2, 3.7, x + 2.2, 3.4, color=dk.HEAT)
    ax.text(x + 2.2, 4.8, title, ha="center", fontsize=9, fontweight="bold")
    ax.text(x + 2.2, 0.9, result, ha="center", fontsize=8)


def laminate(path):
    """!
    @brief Draw the 3D solid on one copper layer as it is and with the laminate slab added.
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(13, 4.6)
    ax.set_xlim(0, 13)
    ax.set_ylim(0.4, 5.3)
    stack(ax, 0.2, False, "3D solid today", "pad 10 x 10 mm: 346.1 K\n(FVM 155.4, FDM 150.3)")
    stack(ax, 6.6, True, "with the laminate slab added", "174.0 K, equal to the same board\nbuilt with two layers (174.5 K)")
    dk.save(fig, path, "The 3D solid under a single copper layer: the missing laminate (README 4.39)")


def chain(path):
    """!
    @brief Draw the validation chain: the mask solved pixel by pixel as reference, the models and what each result means.
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(14, 5.4)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 5.6)
    dk.box(ax, 0.1, 2.2, 2.6, 1.4, "rectangle board\n(known copper,\nexact geometry)", dk.COPPER, size=8)
    dk.box(ax, 3.4, 4.0, 3.6, 1.2, "Question 1: does each model\nconverge to its own limit?\n(cell 2 mm down to 0.1 mm)", "#cfe3f5", size=8)
    dk.box(ax, 3.4, 0.3, 3.6, 1.2, "Question 2: how far is that\nlimit from an independent one?\n(different formulation)", "#cfe3f5", size=8)
    dk.arrow(ax, 2.7, 3.2, 3.4, 4.5)
    dk.arrow(ax, 2.7, 2.6, 3.4, 1.0)
    dk.box(ax, 7.7, 4.0, 6.1, 1.2, "FVM 98.0 K and FDM 97.0 K at 0.1 mm: same limit (1 %)\nthe FVM is 6.4 % low at 1 mm when copper edges fall\nbetween cells: the grid, not the model", "#e3f1df", size=7)
    dk.box(ax, 7.7, 2.15, 6.1, 1.3, "Lumped 82.5 K (-15.8 %), Analytic 72.2 K (-26.3 %):\nthey do not react to the cell, a different physics;\ninsensitive is not accurate", "#fbe3c2", size=7)
    dk.box(ax, 7.7, 0.3, 6.1, 1.2, "3D solid 104 to 106 K, +7 to +9 % above the layered FVM:\nthe layered models are on the cool side\nfor a heater on a small pad", "#e3f1df", size=7)
    dk.arrow(ax, 7.0, 4.6, 7.7, 4.6)
    dk.arrow(ax, 7.0, 0.9, 7.7, 0.9)
    dk.arrow(ax, 7.0, 4.3, 7.7, 2.9, width=0.9)
    dk.save(fig, path, "How the models are validated on the rectangle board (README 4.37): no measurement yet")


def main():
    """!
    @brief Draw and save the diagrams of this folder.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    laminate(OUT / "fig_13_laminate_single_layer_schematic.png")
    chain(OUT / "fig_14_validation_chain_schematic.png")


if __name__ == "__main__":
    main()
