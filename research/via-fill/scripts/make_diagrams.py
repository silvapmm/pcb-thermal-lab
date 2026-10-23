"""!
@file make_diagrams.py
@brief Schematic diagrams of the via fills: the cross-section of a barrel open, with a resin plug, with conductive paste and with electroplated copper, and the heat path through the barrel and its fill.
@details Pure drawing, symbolic labels; the conductivities quoted (resin 0.3 W/mK, conductive paste 8, copper 385) are those of the program's via-fill library, and the finding that only a copper fill matters (3.3 times the barrel, -3.9 K on the example board) is that of the README of this folder. Writes figures/fig_04_via_fills_schematic.png.
         Also writes figures/fig_05_via_array_under_a_part.png (the array under a part, the heat path and the resistance of nine vias).
         Run: .venv/bin/python research/via-fill/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np


from matplotlib.patches import Circle, Polygon, Rectangle                 # noqa: E402

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


def via_array(path):
    """!
    @brief Draw the via array under a part (top view and section) and the resistance it gives for an open barrel and for a copper fill (the arithmetic of README 4.1 and 4.2).
    @param path Output file.
    @return None.
    """
    fig, (a1, a2, a3) = dk.canvas(15, 5.0, 1, 3, ratios=[1, 1.3, 1])
    # top view: 3 x 3 vias under the part
    a1.set_xlim(0, 8)
    a1.set_ylim(-1.2, 8.4)
    a1.set_aspect("equal")
    a1.add_patch(Rectangle((0.3, 0.3), 7.4, 7.4, facecolor=dk.FR4, edgecolor="k"))
    a1.add_patch(Rectangle((1.4, 1.4), 5.2, 5.2, facecolor=dk.COPPER, edgecolor="k"))
    a1.add_patch(Rectangle((2.2, 2.2), 3.6, 3.6, facecolor="#555555", edgecolor="k", alpha=0.35))
    for i in range(3):
        for j in range(3):
            a1.add_patch(Circle((2.8 + i * 1.2, 2.8 + j * 1.2), 0.38, facecolor="white", edgecolor="k", linewidth=1.2))
            a1.add_patch(Circle((2.8 + i * 1.2, 2.8 + j * 1.2), 0.38, fill=False, edgecolor=dk.COPPER, linewidth=2.2))
    a1.text(4, 8.0, "top view: 3 x 3 vias under the part", ha="center", fontsize=9, fontweight="bold")
    a1.text(4, -0.4, "0.3 mm vias, shaded square: the footprint\non its copper pad (example board)", ha="center", va="top", fontsize=7.5)
    # section: heat down the barrels to the far side
    a2.set_xlim(0, 12)
    a2.set_ylim(-0.8, 7)
    dk.layer(a2, 1, 1.5, 10, 3.2, dk.FR4)
    a2.text(2.3, 3.1, "FR-4,\n1.6 mm", ha="center", fontsize=7.5)
    dk.layer(a2, 1, 4.7, 10, 0.25, dk.COPPER)
    dk.layer(a2, 1, 1.25, 10, 0.25, dk.COPPER)
    dk.box(a2, 3.2, 5.1, 5.6, 0.9, "part (heat source)", "#f4b6b6", size=8)
    for x in (4.0, 6.0, 8.0):
        a2.add_patch(Rectangle((x - 0.25, 1.25), 0.5, 3.7, facecolor="white", edgecolor="k"))
        a2.add_patch(Rectangle((x - 0.25, 1.25), 0.07, 3.7, facecolor=dk.COPPER, edgecolor="k"))
        a2.add_patch(Rectangle((x + 0.18, 1.25), 0.07, 3.7, facecolor=dk.COPPER, edgecolor="k"))
        dk.arrow(a2, x, 5.0, x, 1.0, color=dk.HEAT, width=1.3)
    a2.text(6, 6.6, "section: the heat goes down the copper of the barrels", ha="center", fontsize=9, fontweight="bold")
    a2.text(6, 0.45, "to the far side of the board, then into the air", ha="center", fontsize=7.5, style="italic")
    a2.text(6, -0.6, "R = L / (k_Cu A_eq): a long thin conductor, the wall only unless the bore is copper", ha="center", fontsize=7)
    # bars of resistance (arithmetic of one-via figures)
    a3.set_xlim(0, 10)
    a3.set_ylim(-1.2, 8.4)
    a3.text(5, 8.0, "nine vias in parallel", ha="center", fontsize=9, fontweight="bold")
    for k, (name, one, color) in enumerate((("open or resin", 192.4, "#c9c9c9"), ("copper fill", 58.8, dk.COPPER))):
        y = 5.0 - k * 2.6
        a3.add_patch(Rectangle((0.3, y), 9 * one / 192.4, 1.4, facecolor=color, edgecolor="k"))
        a3.text(0.3, y + 1.55, f"{name}: {one} K/W each", va="bottom", fontsize=7.5)
        a3.text(0.3, y - 0.2, f"9 in parallel: {one / 9:.1f} K/W (arithmetic)", fontsize=7.5, va="top")
    a3.text(5, -0.5, "example board, finite volumes: 85.87 C open,\n85.87 resin, 81.98 C copper fill (-3.89 K)", ha="center", va="top", fontsize=7.5, color=dk.HEAT)
    dk.save(fig, path, "A via array under a part: where the heat goes and what the fill changes (README 4.1 and 4.2)")


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
    via_array(OUT / "fig_05_via_array_under_a_part.png")


if __name__ == "__main__":
    main()
