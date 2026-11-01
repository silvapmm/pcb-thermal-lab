#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Schematic diagrams of the real-boards investigation: the chain from the files of a board to the models, the paste layer as a component footprint (what a click picks), and copper finer than the cell.
@details Pure drawing, no data and no program; the shapes are in research/diagram_kit.py. Writes figures/fig_01_import_chain.png, fig_02_paste_to_footprint.png and fig_03_fine_copper_cell.png.
         Not yet drawn (planned, need the results of the studies): the memory per unknown against the unknowns (make_figures.py), the step responses by cell size (make_figures.py).
         Run (from the repository root): .venv/bin/python research/gerber-real-boards/scripts/make_diagrams.py   (needs matplotlib only)
"""

import sys
from pathlib import Path

import numpy as np
from matplotlib.patches import Polygon, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def import_chain(path):
    """!
    @brief The chain from the files of a board to the models of the program, with the places where a decision or a warning sits.
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(11, 5.2)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 5.2)
    dk.box(ax, 0.1, 3.6, 2.2, 1.2, "Gerber set\ncopper, outline,\ndrill, paste", "#cfe3f5")
    dk.box(ax, 0.1, 1.8, 2.2, 1.2, "placement file\n(CSV) or Gerber X3\ncomponent layer", "#cfe3f5")
    dk.box(ax, 0.1, 0.1, 2.2, 1.2, "ODB++ (planned)\ncomponents, packages", "#e8e8e8")
    dk.box(ax, 3.1, 3.6, 2.2, 1.2, "own reader\n(NumPy)\nmasks per layer", "#d8ecd0")
    dk.box(ax, 3.1, 1.8, 2.2, 1.2, "paste groups\n(TO.C or proximity)\nregistered on the\nplacement", "#d8ecd0")
    dk.box(ax, 6.1, 3.6, 2.2, 1.2, "copper mapping\nfaces per cell\n(+ fine-copper warning)", "#fbe3b6")
    dk.box(ax, 6.1, 1.8, 2.2, 1.2, "parts: footprint,\nheat source by click", "#fbe3b6")
    dk.box(ax, 8.8, 2.7, 2.1, 1.4, "program network\n(FVM; Lumped and\nAnalytic with a\nwarning)", "#f4b6b6", bold=True)
    dk.box(ax, 8.8, 0.6, 2.1, 1.1, "project file 2\n(masks embedded\nor referenced)", "#e8e8e8")
    for y in (4.2, 2.4):
        dk.arrow(ax, 2.3, y, 3.1, y)
        dk.arrow(ax, 5.3, y, 6.1, y)
    dk.arrow(ax, 8.3, 4.1, 8.8, 3.6)
    dk.arrow(ax, 8.3, 2.4, 8.8, 3.1)
    dk.arrow(ax, 9.85, 2.7, 9.85, 1.7)
    dk.arrow(ax, 2.3, 0.7, 3.1, 2.0, style="->")
    ax.text(5.5, 0.35, "Studies: mapping default, time and memory, transient, paste, Lumped/Analytic rule, rare primitives, fine copper", fontsize=7, style="italic", ha="center")
    dk.save(fig, path, "From the files of a board to the models (the chain this investigation tests)")


def paste_to_footprint(path):
    """!
    @brief A QFN seen from above: the paste openings, the group, the three candidate footprints and the click.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(10, 4.2, 1, 3)
    titles = ["paste openings", "group + footprint candidates", "click picks the group"]
    for ax, t in zip(axs, titles):
        ax.set_xlim(-4, 4)
        ax.set_ylim(-4, 4)
        ax.set_aspect("equal")
        ax.set_title(t, fontsize=9)
        # the 28 perimeter pads (7 per side) and the exposed-pad windows (2 x 2)
        pads = []
        for i in range(7):
            u = -1.8 + 0.6 * i
            for (x, y, w, h) in ((u, 2.6, 0.3, 0.8), (u, -2.6, 0.3, 0.8), (2.6, u, 0.8, 0.3), (-2.6, u, 0.8, 0.3)):
                pads.append((x - w / 2, y - h / 2, w, h))
        for (x0, y0, w, h) in ((-1.4, -1.4, 1.2, 1.2), (0.2, -1.4, 1.2, 1.2), (-1.4, 0.2, 1.2, 1.2), (0.2, 0.2, 1.2, 1.2)):
            pads.append((x0, y0, w, h))
        for (x0, y0, w, h) in pads:
            ax.add_patch(Rectangle((x0, y0), w, h, facecolor="#7a7a7a", edgecolor="none"))
    # panel 2: bounding box, hull (an octagon here), largest opening (one window; the exposed pad is split in four)
    ax = axs[1]
    ax.add_patch(Rectangle((-3.3, -3.3), 6.6, 6.6, fill=False, edgecolor=dk.BLUE, linewidth=1.6))
    ax.text(-3.2, 3.5, "bounding box", color=dk.BLUE, fontsize=7)
    hull = np.array([[-1.8, 3.0], [1.8, 3.0], [3.0, 1.8], [3.0, -1.8], [1.8, -3.0], [-1.8, -3.0], [-3.0, -1.8], [-3.0, 1.8]])
    ax.add_patch(Polygon(hull, fill=False, edgecolor="#2ca02c", linewidth=1.6, linestyle="--"))
    ax.text(-3.9, -3.8, "convex hull", color="#2ca02c", fontsize=7)
    ax.add_patch(Rectangle((-1.4, -1.4), 2.8, 2.8, fill=False, edgecolor=dk.HEAT, linewidth=1.6, linestyle=":"))
    ax.text(0.3, -1.9, "exposed pad", color=dk.HEAT, fontsize=7)
    # panel 3: the click
    ax = axs[2]
    ax.add_patch(Rectangle((-3.3, -3.3), 6.6, 6.6, facecolor="#f4b6b6", alpha=0.35, edgecolor=dk.HEAT, linewidth=1.4))
    ax.plot([0.75], [0.75], marker="+", color="k", markersize=14, markeredgewidth=2)
    ax.text(0.95, 0.95, "click", fontsize=8)
    ax.text(0, -3.8, "reference U1 from TO.C or from the placement file", fontsize=7, ha="center")
    dk.save(fig, path, "The paste layer as a component: groups of openings, three footprints for the heat source, one click")


def fine_copper(path):
    """!
    @brief Copper finer than the cell: stripes under a grid, the cells that are neither empty nor full, and the thin copper the cell cannot resolve.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(10, 4.2, 1, 2)
    for ax, cell, title in ((axs[0], 1.0, "cell 1.0 mm: 0.2 mm stripes at 0.4 mm pitch\n(every cell mixed, all copper thinner than the cell)"),
                            (axs[1], 0.2, "cell 0.2 mm: the same copper\n(cells are nearly empty or full along the stripes)")):
        ax.set_xlim(0, 4)
        ax.set_ylim(0, 4)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=8)
        for y in np.arange(0, 4, 0.4):
            ax.add_patch(Rectangle((0, y), 4, 0.2, facecolor=dk.COPPER, edgecolor="none"))
        for g in np.arange(0, 4 + 1e-9, cell):
            ax.plot([g, g], [0, 4], color="k", linewidth=0.5)
            ax.plot([0, 4], [g, g], color="k", linewidth=0.5)
    axs[0].text(2, -0.35, "heat across the stripes must cross every clearance: the arithmetic fill assumes it does not", fontsize=7, ha="center")
    dk.save(fig, path, "Copper finer than the cell: what the cell conductance can only approximate")


def main():
    """!
    @brief Draw all the diagrams.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    import_chain(OUT / "fig_01_import_chain.png")
    paste_to_footprint(OUT / "fig_02_paste_to_footprint.png")
    fine_copper(OUT / "fig_03_fine_copper_cell.png")


if __name__ == "__main__":
    main()
