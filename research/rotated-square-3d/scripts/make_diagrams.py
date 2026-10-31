#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation of the rotated square: the grid cells that the outline cuts (aligned, shifted by half a cell, turned), the section of an edge cell with the path of the heat, and the edge resistances of the program and of the cut-cell copy.
@details Figures 01 to 03 of figures/ (the data figures from 04 on are drawn by make_figures.py). No solver is run: the cut cells of figure 01 come from
         `lib/cutcell.py` (the same sampling the copy uses) and the proportions of figures 02 and 03 are those of the study boards (1 mm cells, 1.6 mm
         board, copper exaggerated). Files: fig_01_cut_cells.png, fig_02_section_of_an_edge_cell.png, fig_03_edge_resistances.png.
         Usage: python research/rotated-square-3d/scripts/make_diagrams.py   (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parent / "lib"))

import diagram_kit as dk                                                    # noqa: E402
import cutcell                                                              # noqa: E402
import rotsq                                                                # noqa: E402
from matplotlib.patches import Polygon, Rectangle                          # noqa: E402

OUT = HERE.parent / "figures"


def cells_panel(ax, angle, shift, title):
    """!
    @brief Draw a corner region of a square board on a 1 mm grid: each cell shaded by its board fraction, the outline, and the lengths of the edge in the cells.
    @param ax Axes.
    @param angle Turn of the square in degrees.
    @param shift Shift of the board against the grid in cells (both directions).
    @param title Title.
    @return None.
    """
    n, c = 14, 1e-3
    side, box = 10.0, 14.0
    poly_mm = rotsq.turned_square(side, angle, (box / 2 + shift, box / 2 + shift))
    g = cutcell.cut_geometry(np.array(poly_mm) * 1e-3, n, n, c, c)
    for i in range(n):
        for j in range(n):
            cv = g["cover"][i, j]
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=(0.88, 0.64, 0.35, cv) if cv > 0 else "none", edgecolor="#bbbbbb", lw=0.5))
            if 0 < cv < 1:
                ax.plot(g["xc"][i, j] / c, g["yc"][i, j] / c, "k.", ms=3)           # Centroid of the board part of a cut cell
    ax.add_patch(Polygon(poly_mm, closed=True, fill=False, edgecolor="#1f77b4", lw=1.6))
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, fontsize=8)


def fig_cut_cells():
    """!
    @brief Figure 01: the same square on the grid three ways.
    @return None.
    """
    fig, axs = dk.canvas(10.5, 3.9, 1, 3)
    for ax in axs:
        ax.axis("on")
    cells_panel(axs[0], 0, 0.0, "aligned: every edge cell is whole\n(centre 0.5 cell from the edge)")
    cells_panel(axs[1], 0, 0.5, "shifted by half a cell: edge cells half board\n(centroid of the board part 0.25 cell from the edge)")
    cells_panel(axs[2], 27, 0.0, "turned 27 degrees: cells cut at every depth,\nfrom slivers to nearly whole (dots: centroids)")
    dk.save(fig, OUT / "fig_01_cut_cells.png")


def fig_section():
    """!
    @brief Figure 02: section through one edge cell (copper on both faces, four dielectric slabs) in three positions of the outline, with the heat paths and the distances the models use.
    @return None.
    """
    fig, axs = dk.canvas(10.5, 4.2, 1, 3)
    cases = [("aligned: whole cell", 1.0), ("shifted: half board", 0.5), ("turned: thin sliver", 0.2)]
    for ax, (name, cov) in zip(axs, cases):
        ax.set_xlim(-0.1, 1.5)
        ax.set_ylim(-0.7, 3.9)
        ax.set_title(name, fontsize=9)
        xe = cov                                                  # The board fills the left part of the cell, width cov; the outline is at x = cov
        dk.layer(ax, 0.0, 2.75, xe, 0.18, dk.COPPER)
        for k in range(4):
            dk.layer(ax, 0.0, 0.55 + 0.55 * (3 - k), xe, 0.55, dk.FR4)
        dk.layer(ax, 0.0, 0.37, xe, 0.18, dk.COPPER)
        ax.add_patch(Rectangle((0, 0.37), 1.0, 2.56, fill=False, edgecolor="#777777", ls=":", lw=0.8))   # The grid cell
        ax.plot([0.5], [1.65], "o", color="#d62728", ms=6)                                              # Cell centre: the node of the program
        ax.text(0.5, 3.35, "red: node of the program\n(cell centre, d = 0.5 cell)", ha="center", va="bottom", fontsize=6.5, color="#d62728")
        cx = xe / 2.0
        ax.plot([cx], [1.65], "s", color="#2ca02c", ms=5)                                               # Centroid of the board part: the node of the copy
        ax.text(cx, 3.05, "green: centroid, d = " + f"{cov / 2:.2f} cell", ha="center", va="bottom", fontsize=6.5, color="#2ca02c")
        ax.annotate("", xy=(xe, 0.2), xytext=(0.5, 0.2), arrowprops=dict(arrowstyle="<->", color="#d62728", lw=1.0))
        ax.annotate("", xy=(xe, 0.0), xytext=(cx, 0.0), arrowprops=dict(arrowstyle="<->", color="#2ca02c", lw=1.0))
        for yy in (2.25, 1.7, 1.15, 0.65):
            dk.arrow(ax, xe + 0.02, yy, xe + 0.25, yy, color=dk.HEAT, width=1.2)
        ax.text(1.12, 1.45, "edge\nfilm h", fontsize=7, color=dk.HEAT, va="center")
        if cov < 1.0:
            ax.text(0.5, -0.45, "program: conducts with k x cover (path 1 / cover too long)", ha="center", fontsize=6.2, color="#d62728")
    dk.save(fig, OUT / "fig_02_section_of_an_edge_cell.png")


def fig_resistances():
    """!
    @brief Figure 03: the edge element of one cell and slab in the program and in the cut-cell copy, as resistances.
    @return None.
    """
    fig, axs = dk.canvas(10.5, 3.2, 1, 2)
    for ax, (title, lines) in zip(axs, [
            ("program (one cell, one slab)", ["node  --  d / (k c L dz)  --  1 / (h L dz)  --  air", "d = (dx + dy) / 4 always;  k c = conductivity x cover;",
                                              "L = outline length in the cell (moved to the nearest board cell if the cell is off)", "whole cell: c = 1, d = dx / 2: right",
                                              "half cell: c = 0.5: the conduction term doubles;  sliver: 1 / c times too long"]),
            ("cut-cell copy (one cell, one slab)", ["node  --  d / (k L dz)  --  1 / (h L dz)  --  air", "d = c dx dy / (2 L): half the depth of the board strip behind the outline",
                                                    "k = full conductivity;  links to the neighbours: aperture x dy x dz / (d1/k + d2/k)", "d1, d2 = distances from the face to the two centroids",
                                                    "whole cell: d = dx / 2 as before; half cell: d = dx / 4"])]):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        ax.set_title(title, fontsize=9)
        dk.resistor(ax, 0.8, 3.6, 5.0, "conduction", color="#2ca02c" if "copy" in title else "#d62728")
        dk.resistor(ax, 4.4, 7.2, 5.0, "film", color=dk.BLUE)
        ax.text(0.5, 5.0, "node", ha="right", va="center", fontsize=7)
        ax.text(7.5, 5.0, "air", ha="left", va="center", fontsize=7)
        for k, t in enumerate(lines):
            ax.text(0.2, 3.7 - 0.75 * k, t, fontsize=6.8, va="center")
    dk.save(fig, OUT / "fig_03_edge_resistances.png")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_cut_cells()
    fig_section()
    fig_resistances()
