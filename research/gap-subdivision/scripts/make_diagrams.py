#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation of the gap subdivision: the section of a board under a source (uniform copper and a copper pad), the nodes of the layered model with 1, 2, 4 and 8 nodes through a gap, and the top view of the test boards and of the cells that get extra nodes.
@details Figures 01 to 03 of figures/ (the data figures from 04 on are drawn by make_figures.py). No study is run; the proportions are those of the baseline board (30 mm board, 3 mm source, 10 mm pad, 1.6 mm gap, 35 um copper), with the copper
         thickness exaggerated in the section. Files: fig_01_section_under_the_source.png, fig_02_nodes_through_the_gap.png, fig_03_top_view_of_the_boards.png.
         Usage: python research/gap-subdivision/scripts/make_diagrams.py   (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import diagram_kit as dk                                                    # noqa: E402
from matplotlib.patches import Circle, Rectangle                            # noqa: E402

OUT = HERE.parent / "figures"


def section(ax, pad, title):
    """!
    @brief Section of a two-layer board with a source on the top face: heat entering, the paths through the gap and the lateral fan-out at the edge of a pad.
    @param ax Axes.
    @param pad True: the top copper is a pad of 10 mm and the laminate shows around it; False: the top copper covers the board.
    @param title Title.
    @return None.
    """
    ax.set_xlim(0, 12)
    ax.set_ylim(-0.6, 6.6)
    ax.set_title(title, fontsize=9)
    zt, gap, tcu = 4.6, 2.8, 0.22                       # top of the board, gap thickness (drawn), copper thickness (drawn)
    dk.layer(ax, 0.5, zt - tcu - gap, 11, gap, dk.FR4)
    dk.layer(ax, 0.5, zt - tcu - gap - tcu, 11, tcu, dk.COPPER, "bottom copper (plane or empty: both drawn in the study)", 6.5)
    if pad:
        dk.layer(ax, 3.2, zt - tcu, 5.6, tcu, dk.COPPER, "", 7)
        ax.text(8.9, zt + 0.15, "copper pad (10 mm)", ha="left", fontsize=7)
        ax.text(1.8, zt - tcu / 2 - 0.5, "bare laminate\n(top face in air)", ha="center", fontsize=7)
    else:
        dk.layer(ax, 0.5, zt - tcu, 11, tcu, dk.COPPER, "top copper", 7)
    # the source
    ax.add_patch(Rectangle((5.2, zt + 0.35), 1.6, 0.7, facecolor="#555555", edgecolor="k"))
    ax.text(6, zt + 0.7, "source P", color="white", ha="center", va="center", fontsize=8)
    for x in (5.5, 6.0, 6.5):
        dk.arrow(ax, x, zt + 0.35, x, zt + 0.02, color=dk.HEAT, width=1.0)
    # spreading in the copper
    for sgn in (-1, 1):
        dk.arrow(ax, 6 + sgn * 1.2, zt - tcu / 2, 6 + sgn * (2.6 if pad else 4.6), zt - tcu / 2, color=dk.BLUE, width=1.3)
    if pad:
        # heat crosses the gap under the pad and, at the pad edge, runs sideways in the upper laminate with a vertical gradient
        for x in (4.2, 6.0, 7.8):
            dk.arrow(ax, x, zt - tcu, x, zt - tcu - gap + 0.15, color=dk.HEAT, width=1.1)
        for sgn in (-1, 1):
            xe = 6 + sgn * 2.8
            dk.arrow(ax, xe, zt - tcu - 0.1, xe + sgn * 1.8, zt - tcu - 0.55, color=dk.BLUE, width=1.1)
            dk.arrow(ax, xe, zt - tcu - 0.9, xe + sgn * 1.4, zt - tcu - 1.2, color=dk.BLUE, width=0.8)
        ax.text(6, zt - gap / 2 - 0.45, "vertical conduction: $R = d/(k_z A)$", ha="center", fontsize=7.5, color=dk.HEAT)
        ax.text(10.1, zt - 1.7, "sideways in the laminate,\nhotter at the top of the gap\nthan at the bottom:\na gradient across d", fontsize=7, color=dk.BLUE, ha="center")
    else:
        for x in (1.6, 3.0, 4.4, 6.0, 7.6, 9.0, 10.4):
            dk.arrow(ax, x, zt - tcu, x, zt - tcu - gap + 0.15, color=dk.HEAT, width=1.0)
        ax.text(6, zt - gap / 2 - 0.45, "copper above and below spreads the heat;\nthe gap carries it vertically: $R = d/(k_z A)$", ha="center", fontsize=7.5, color=dk.HEAT)
    ax.annotate("", (11.8, zt - tcu), (11.8, zt - tcu - gap), arrowprops={"arrowstyle": "<->", "linewidth": 0.8})
    ax.text(11.9, zt - tcu - gap / 2, "d", fontsize=8, va="center")
    ax.text(6, -0.45, "ambient (films on both faces)", ha="center", fontsize=7)


def fig_section(path):
    """!
    @brief Figure 01: the board under a source, with copper everywhere and with a pad.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(13, 4.8, 1, 2)
    section(a, False, "Uniform copper: the gap is a vertical resistance")
    section(b, True, "Copper pad: the laminate around it has a gradient across the gap")
    dk.save(fig, path)


def fig_nodes(path):
    """!
    @brief Figure 02: the program's one node per copper layer with half of each adjacent gap, and the gap cut into n = 2, 4, 8 sub-gaps (equal and graded).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 5.6, 1, 5)
    cases = [(1, "equal", "Program: n = 1\\n(one link, k_z A / d)"), (2, "equal", "n = 2 equal"), (4, "equal", "n = 4 equal"), (4, "graded", "n = 4 graded 2:1"), (8, "graded", "n = 8 graded 2:1")]
    for ax, (n, grading, title) in zip(axs, cases):
        ax.set_xlim(0, 4)
        ax.set_ylim(-0.8, 7.0)
        ax.set_title(title.replace("\\n", "\n"), fontsize=8)
        top, gap, tcu = 6.0, 5.0, 0.18
        dk.layer(ax, 0.6, top - gap, 2.8, gap, dk.FR4)
        dk.layer(ax, 0.6, top, 2.8, tcu, dk.COPPER)
        dk.layer(ax, 0.6, top - gap - tcu, 2.8, tcu, dk.COPPER)
        if grading == "equal":
            w = np.ones(n)
        else:
            w = np.array([2.0 ** min(i, n - 1 - i) for i in range(n)])
        z = top - np.concatenate([[0.0], np.cumsum(w / w.sum() * gap)])
        # Node heights: the copper node of the top layer, the n - 1 new nodes at the sub-gap boundaries, the copper node of the bottom layer
        pts = [top + tcu / 2] + list(z[1:-1]) + [top - gap - tcu / 2]
        for j, zj in enumerate(pts):
            ax.add_patch(Circle((2.0, zj), 0.11, facecolor=dk.COPPER if j in (0, n) else "#6fa8dc", edgecolor="k", zorder=5))
            if 0 < j < n:
                ax.plot([0.6, 3.4], [zj] * 2, color="k", linewidth=0.4, linestyle=":")
        for a, b in zip(pts[:-1], pts[1:]):
            ax.plot([2.0, 2.0], [a, b], color="k", linewidth=1.1)
        ax.text(3.5, top - gap / 2, f"{n} link{'s' if n > 1 else ''}", fontsize=7, va="center")
        if n > 1:
            ax.text(0.55, top - gap / 2, "each new node holds\nthe laminate of its\nslab and conducts\nsideways: $k_{xy} t$", fontsize=5.8, ha="right", va="center")
        ax.text(2.0, -0.6, f"unknowns per cell: {n + 1}", ha="center", fontsize=7)
    dk.save(fig, path, "Nodes through one dielectric gap (copper node at mid-thickness of its layer; blue nodes are new)")


def fig_top_view(path):
    """!
    @brief Figure 03: top view of the test boards and of the cells that get extra nodes (all, only under the pad, bare cells plus a margin).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 3.6, 1, 5)
    size, src, pad, cell, margin = 30.0, 3.0, 10.0, 0.5, 4
    titles = ["Uniform copper", "Pad, bottom copper full", "Cells with extra nodes: all", "only under the pad (probe)", "bare cells + margin of a gap"]
    for k, (ax, t) in enumerate(zip(axs, titles)):
        ax.set_xlim(0, size)
        ax.set_ylim(0, size)
        ax.set_aspect("equal")
        ax.set_title(t, fontsize=8)
        ax.add_patch(Rectangle((0, 0), size, size, facecolor=dk.FR4 if k in (1, 2, 3, 4) else dk.COPPER, edgecolor="k"))
        c = size / 2
        if k in (1, 2, 3, 4):
            ax.add_patch(Rectangle((c - pad / 2, c - pad / 2), pad, pad, facecolor=dk.COPPER, edgecolor="k"))
        if k == 2:
            ax.add_patch(Rectangle((0, 0), size, size, facecolor="#6fa8dc", alpha=0.35))
        if k == 3:
            ax.add_patch(Rectangle((c - pad / 2, c - pad / 2), pad, pad, facecolor="#6fa8dc", alpha=0.45))
        if k == 4:
            m = margin * cell + 0.0
            ax.add_patch(Rectangle((0, 0), size, size, facecolor="#6fa8dc", alpha=0.35))
            ax.add_patch(Rectangle((c - pad / 2 + m, c - pad / 2 + m), pad - 2 * m, pad - 2 * m, facecolor=dk.COPPER, edgecolor="k", alpha=1.0))
        ax.add_patch(Rectangle((c - src / 2, c - src / 2), src, src, facecolor="#555555", edgecolor="k"))
        ax.axis("on")
        ax.set_xticks([0, 15, 30])
        ax.set_yticks([0, 15, 30])
        ax.tick_params(labelsize=6)
    dk.save(fig, path, "Test boards (30 mm, 3 mm source, 10 mm pad) and the cells that get extra nodes in the gap (blue); mm")


def main():
    """!
    @brief Draw the three diagrams.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    fig_section(OUT / "fig_01_section_under_the_source.png")
    fig_nodes(OUT / "fig_02_nodes_through_the_gap.png")
    fig_top_view(OUT / "fig_03_top_view_of_the_boards.png")
    print("figures written to", OUT)


if __name__ == "__main__":
    main()
