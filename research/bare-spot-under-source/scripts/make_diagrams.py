#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation of the bare spot: the section of a part over a copper-free window and over copper, the nodes of the layered model and the nodes proposed, and the top view with the refined cells.
@details Figures 01 to 03 of figures/ (the data figures from 04 on are drawn by make_figures.py). No study is run; the geometry is the board of the sweep (30 mm board, 6 mm part, 1.53 mm gap
         of the two-layer 1.6 mm board; the vertical scale of the section is exaggerated for the copper).
         Files: fig_01_part_over_bare_window.png, fig_02_nodes_of_the_layered_model.png, fig_03_top_view_refined_cells.png.
         Usage: python research/bare-spot-under-source/scripts/make_diagrams.py   (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import diagram_kit as dk                                                    # noqa: E402
from matplotlib.patches import Circle, Rectangle                            # noqa: E402

OUT = HERE.parent / "figures"


def section(ax, bare, title):
    """!
    @brief Section of a two-layer board with a part on the top face: heat entering the top face and the paths down to the plane.
    @param ax Axes.
    @param bare True: the top copper has a window under the part; False: copper under the part.
    @param title Title.
    @return None.
    """
    ax.set_xlim(0, 12)
    ax.set_ylim(-0.4, 6.2)
    ax.set_title(title, fontsize=9)
    zt, gap, tcu = 4.4, 2.6, 0.22                       # top of the board, gap thickness (drawn), copper thickness (drawn)
    # laminate
    dk.layer(ax, 0.5, zt - tcu - gap, 11, gap, dk.FR4)
    # planes
    dk.layer(ax, 0.5, zt - tcu - gap - tcu, 11, tcu, dk.COPPER, "bottom copper (plane)", 7)
    if bare:
        dk.layer(ax, 0.5, zt - tcu, 3.4, tcu, dk.COPPER)
        dk.layer(ax, 8.1, zt - tcu, 3.4, tcu, dk.COPPER)
        ax.text(2.2, zt + 0.3, "window (no copper)", ha="center", fontsize=7)
        ax.annotate("", (3.9, zt + 0.25), (8.1, zt + 0.25), arrowprops={"arrowstyle": "<->", "linewidth": 0.8})
        # laminate fills the window: lighter strip on top
        ax.add_patch(Rectangle((3.9, zt - tcu), 4.2, tcu, facecolor=dk.FR4, edgecolor="k", linewidth=0.8))
    else:
        dk.layer(ax, 0.5, zt - tcu, 11, tcu, dk.COPPER, "top copper", 7)
    # the part
    ax.add_patch(Rectangle((4.4, zt + 0.35), 3.2, 0.9, facecolor="#555555", edgecolor="k"))
    ax.text(6, zt + 0.8, "part, power P", color="white", ha="center", va="center", fontsize=8)
    for x in (4.9, 5.5, 6.1, 6.7, 7.2):
        dk.arrow(ax, x, zt + 0.35, x, zt + 0.02, color=dk.HEAT, width=1.0)
    if bare:
        # heat goes down through the laminate and fans out sideways at the window edge
        for x in (4.9, 6.0, 7.1):
            dk.arrow(ax, x, zt - tcu, x, zt - tcu - gap + 0.2, color=dk.HEAT, width=1.2)
        for sgn in (-1, 1):
            xe = 6 + sgn * 2.1
            dk.arrow(ax, xe - sgn * 0.6, zt - 0.5, xe + sgn * 1.2, zt - 0.1, color=dk.BLUE, width=1.0)
        ax.text(6, zt - gap / 2 - 0.2, "vertical conduction through the laminate:\n$R = d / (k_z A)$, large", ha="center", fontsize=7.5, color=dk.HEAT)
        ax.text(10.2, zt - 1.0, "a little heat leaves\nsideways into the copper\nat the window edge\n(through a thin skin)", fontsize=7, color=dk.BLUE, ha="center")
    else:
        for sgn in (-1, 1):
            dk.arrow(ax, 6 + sgn * 1.5, zt - tcu / 2, 6 + sgn * 4.8, zt - tcu / 2, color=dk.BLUE, width=1.4)
        for x in (1.6, 3.0, 9.0, 10.4):
            dk.arrow(ax, x, zt - tcu, x, zt - tcu - gap + 0.2, color=dk.HEAT, width=1.0)
        ax.text(6, zt - gap / 2 - 0.2, "copper spreads the heat first (2D), then it goes down\nthrough the laminate over a large area", ha="center", fontsize=7.5, color=dk.BLUE)
    ax.annotate("", (11.8, zt - tcu), (11.8, zt - tcu - gap), arrowprops={"arrowstyle": "<->", "linewidth": 0.8})
    ax.text(11.9, zt - tcu - gap / 2, "d", fontsize=8, va="center")
    ax.text(6, -0.25, "ambient (films on both faces)", ha="center", fontsize=7)


def fig_section(path):
    """!
    @brief Figure 01: the part over a bare window and over copper.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(13, 4.6, 1, 2)
    section(a, True, "Part over a copper-free window")
    section(b, False, "Part over copper")
    dk.save(fig, path)


def fig_nodes(path):
    """!
    @brief Figure 02: the one-node-per-layer construction of the program at a bare spot and the nodes proposed.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 5.2, 1, 3)
    titles = ["Program: one node per copper layer", "Proposed: n nodes in the gap (n = 3 drawn)", "What the nodes represent"]
    for ax, t in zip(axs, titles):
        ax.set_xlim(0, 10)
        ax.set_ylim(-1.4, 7.2)
        ax.set_title(t, fontsize=9)
    # panel 1 and 2: a row of five cells in section: copper | bare | bare | bare | copper
    for k, ax in enumerate(axs[:2]):
        n = 1 if k == 0 else 3
        xs = np.linspace(0.8, 9.2, 5)
        top, bot, h = 6.0, 1.2, 0.0
        zs = np.linspace(top, bot, n + 1)
        for i, x in enumerate(xs):
            bare = i in (1, 2, 3)
            # node column
            ax.add_patch(Rectangle((x - 0.8, bot - 0.15), 1.6, top - bot + 0.3, facecolor=dk.FR4 if bare else "#f1e3c9", edgecolor="k", linewidth=0.6, alpha=0.6))
            ax.add_patch(Circle((x, top), 0.16, facecolor=dk.HEAT if bare else dk.COPPER, edgecolor="k", zorder=5))
            ax.add_patch(Circle((x, bot), 0.16, facecolor=dk.COPPER, edgecolor="k", zorder=5))
            for j in range(1, n):
                if bare:
                    ax.add_patch(Circle((x, zs[j]), 0.13, facecolor="#6fa8dc", edgecolor="k", zorder=5))
            for j in range(n):
                if bare or k == 0:
                    ax.plot([x, x], [zs[j], zs[j + 1]], color="k", linewidth=1.0)
            if bare and k == 1:
                pass
        # lateral links at the top node row
        for i in range(4):
            col = dk.HEAT if (i in (0, 3)) else "k"
            ax.plot([xs[i], xs[i + 1]], [top, top], color=col, linewidth=2.6 if i in (0, 3) else 0.8)
        if k == 0:
            ax.text(5, -1.1, "red: the link between the bare node and the copper node has the\nconductance of a slab $k_{xy} d/2$ thick, at any cell size", ha="center", fontsize=7, color=dk.HEAT)
            ax.text(5, 0.3, "(the plane node below is isothermal)", ha="center", fontsize=7)
        else:
            for j in range(1, n):
                for i in range(1, 3):
                    ax.plot([xs[i], xs[i + 1]], [zs[j], zs[j]], color="#6fa8dc", linewidth=0.8)
            ax.text(5, -1.2, "the bare column has laminate nodes: the lateral link of the top node is\nonly $k_{xy} d/(2n)$ thick, deeper nodes carry the rest; a margin of\ncells around the window is refined too (not walled in)", ha="center", fontsize=7, color=dk.BLUE)
            ax.text(5, 0.3, "copper cells far from the window keep one link", ha="center", fontsize=7)
        ax.text(0.1, top, "top\nlayer", fontsize=7, va="center")
        ax.text(0.1, bot, "plane", fontsize=7, va="center")
    # panel 3: slabs held by the nodes
    ax = axs[2]
    for n, x0, lab in ((1, 1.0, "program"), (3, 5.5, "n = 3")):
        d = 4.8
        z = np.linspace(6.0, 6.0 - d, n + 1)
        ax.add_patch(Rectangle((x0, 6.0 - d), 2.8, d, facecolor=dk.FR4, edgecolor="k"))
        for j in range(n + 1):
            ax.plot([x0, x0 + 2.8], [z[j], z[j]], color="k", linewidth=0.8, linestyle=":")
        # slabs: node at each boundary holds half of the adjacent sub-gaps
        for j in range(n + 1):
            lo = z[j] - (z[j] - z[j + 1]) / 2 if j < n else z[j]
            hi = z[j] + (z[j - 1] - z[j]) / 2 if j > 0 else z[j]
            ax.add_patch(Rectangle((x0 + 2.9, lo), 0.3, hi - lo, facecolor="#6fa8dc" if 0 < j < n else dk.COPPER, edgecolor="k", linewidth=0.6))
            ax.add_patch(Circle((x0, z[j]), 0.12, facecolor="k", zorder=5))
        ax.text(x0 + 1.4, 6.6, lab, ha="center", fontsize=8)
    ax.text(5, -0.2, "each node holds the laminate half a sub-gap on either side;\nits temperature is the mean of that slab", ha="center", fontsize=7)
    dk.save(fig, path)


def fig_top(path):
    """!
    @brief Figure 03: top view of the window, the part and the cells that are refined (bare cells plus a margin of about one gap thickness).
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(12, 5.6, 1, 2)
    size, cell, part, win, gap = 30.0, 1.0, 6.0, 8.0, 1.53
    n = int(size / cell)
    for ax, margin, title in ((a, 0, "bare cells only (margin 0): walled in"), (b, int(np.ceil(gap / cell)) + 1, "bare cells + margin of about one gap thickness")):
        ax.set_xlim(8, 22)
        ax.set_ylim(8, 22)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=9)
        x0, x1 = 15 - win / 2, 15 + win / 2
        for i in range(n):
            for j in range(n):
                cx, cy = i + 0.5, j + 0.5
                bare = x0 < cx < x1 and x0 < cy < x1
                dist = max(x0 - cx, cx - x1, x0 - cy, cy - x1, 0)
                refined = bare or (dist > 0 and dist <= margin * cell)
                col = "#6fa8dc" if refined and not bare else (dk.FR4 if bare else dk.COPPER)
                ax.add_patch(Rectangle((i, j), 1, 1, facecolor=col, edgecolor="white", linewidth=0.4))
        ax.add_patch(Rectangle((15 - part / 2, 15 - part / 2), part, part, fill=False, edgecolor="k", linewidth=2.0))
        ax.text(15, 15, "part", ha="center", va="center", fontsize=9)
    fig.text(0.5, 0.01, "green: bare cell; blue: copper cell refined too (the extra laminate nodes reach out about one gap thickness); orange: copper cell, program's own single link. Cell 1 mm, window 8 mm, part 6 mm, gap 1.53 mm.", ha="center", fontsize=7)
    dk.save(fig, path)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_section(OUT / "fig_01_part_over_bare_window.png")
    fig_nodes(OUT / "fig_02_nodes_of_the_layered_model.png")
    fig_top(OUT / "fig_03_top_view_refined_cells.png")
    print("diagrams written to", OUT)
