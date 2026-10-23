"""!
@file make_diagrams.py
@brief Schematic diagrams of the via fills: the cross-section of a barrel open, with a resin plug, with conductive paste and with electroplated copper, and the heat path through the barrel and its fill.
@details Pure drawing, symbolic labels; the conductivities quoted (resin 0.3 W/mK, conductive paste 8, copper 385) are those of the program's via-fill library, and the finding that only a copper fill matters (3.3 times the barrel, -3.9 K on the example board) is that of the README of this folder. Writes figures/fig_04_via_fills_schematic.png.
         Run: .venv/bin/python research/via-fill/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def barrel(ax, x, fill_color, title, k_text):
    """!
    @brief The cross-section of one via barrel with the board around it and the fill in the bore.
    @param ax Axes.
    @param x Left of the drawing.
    @param fill_color Colour of the fill (white for an open barrel).
    @param title Title of the drawing.
    @param k_text Conductivity text.
    @return None.
    """
    dk.layer(ax, x, 0.5, 2.6, 4.0, dk.FR4)
    dk.layer(ax, x, 4.5, 2.6, 0.25, dk.COPPER)
    dk.layer(ax, x, 0.25, 2.6, 0.25, dk.COPPER)
    ax.add_patch(Rectangle((x + 0.9, 0.25), 0.8, 4.5, facecolor=fill_color, edgecolor="k"))
    ax.add_patch(Rectangle((x + 0.9, 0.25), 0.12, 4.5, facecolor=dk.COPPER, edgecolor="k"))
    ax.add_patch(Rectangle((x + 1.58, 0.25), 0.12, 4.5, facecolor=dk.COPPER, edgecolor="k"))
    ax.text(x + 1.3, 5.2, title, ha="center", fontsize=8, fontweight="bold")
    ax.text(x + 1.3, -0.4, k_text, ha="center", fontsize=7)
    dk.arrow(ax, x + 0.4, 4.9, x + 0.4, 0.3, color=dk.HEAT, width=1.2)


def main():
    """!
    @brief Draw the four barrels and the formula panel and save the figure.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig, ax = dk.canvas(15, 5.6)
    ax.set_xlim(-0.2, 15)
    ax.set_ylim(-1.6, 6.2)
    barrel(ax, 0.0, "white", "open barrel", "air in the bore:\nonly the plated wall conducts")
    barrel(ax, 3.2, "#d9c9a3", "resin plug", "k = 0.3 W/mK (like FR-4):\n'filled' by the fabricator,\nthermally almost open")
    barrel(ax, 6.4, "#b8a9c9", "conductive paste", "k = 8 W/mK:\n27 times the resin, still\n2 % of copper")
    barrel(ax, 9.6, dk.COPPER, "electroplated copper fill", "k = 385 W/mK:\n3.3 times the barrel,\n-3.9 K on the example board")
    dk.box(ax, 12.7, 1.0, 2.2, 3.6, "thermal area\nA = pi d t (wall)\n+ A_bore k_fill / k_Cu\n\nonly a copper fill\nchanges the result", "#fbe3c2", size=7)
    dk.save(fig, OUT / "fig_04_via_fills_schematic.png", "What fills a via barrel: cross-sections and the heat path")


if __name__ == "__main__":
    main()
