#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of research/small-model-defects: fig_01 (the far via joins the cluster: the two balls of the grouping rule), fig_04 (the three causes drawn on the grid: the
       centroid on a cell edge, the copper edge between two nodes of the FDM, the via on a grid line and its mirror image).
@details No data and no program run. Usage: python research/small-model-defects/scripts/make_diagrams.py   (from the repository root).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import diagram_kit as dk                                                    # noqa: E402
from matplotlib.patches import Circle, Rectangle                            # noqa: E402

OUT = HERE.parent / "figures"


def grid(ax, x0, y0, n, m, s=1.0):
    """!
    @brief Draw a grid of n x m cells.
    @param ax Axes.
    @param x0 Left corner.
    @param y0 Bottom corner.
    @param n Cells along x.
    @param m Cells along y.
    @param s Cell size.
    @return None.
    """
    for i in range(n + 1):
        ax.plot([x0 + i * s, x0 + i * s], [y0, y0 + m * s], color="#999", lw=0.6)
    for j in range(m + 1):
        ax.plot([x0, x0 + n * s], [y0 + j * s, y0 + j * s], color="#999", lw=0.6)


def fig_grouping(path):
    """!
    @brief The grouping rule on a 4 x 4 array and a far via: the ball of radius 2 d_nn of each via.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(12, 4.6, 1, 2)
    for ax, title, rule in ((a, "program: joined if distance <= 2 max(d_i, d_j)", "max"), (b, "candidate: joined if distance <= 2 min(d_i, d_j)", "min")):
        ax.set_xlim(-4, 14)
        ax.set_ylim(-4, 8)
        ax.set_aspect("equal")
        ax.add_patch(Rectangle((8.5, 0.5), 4, 4, fill=False, edgecolor="k", lw=1.2))
        for i in range(4):
            for j in range(4):
                ax.add_patch(Circle((9 + i, 1 + j), 0.12, color=dk.COPPER))
        ax.add_patch(Circle((5, 2), 0.12, color=dk.HEAT))
        ax.add_patch(Circle((5, 2), 8.0, fill=False, edgecolor=dk.HEAT, ls="--", lw=0.9, clip_on=True))
        ax.add_patch(Circle((9, 1), 2.0, fill=False, edgecolor=dk.COPPER, ls=":", lw=0.9))
        ax.text(5, 1.0, "far via\n$d_{nn}$ = 4 pitches", ha="center", fontsize=7, color=dk.HEAT)
        ax.text(10.5, 5.1, "array under the part\n(pitch 1, $d_{nn}$ = 1)", ha="center", fontsize=7)
        ax.text(-3.5, -3.2, "dashed red: ball of the far via, radius 2 $d_{nn}$ = 8; dotted: ball of an array via, radius 2", fontsize=6.5)
        ax.text(4.5, 7.2, title, ha="center", fontsize=8, weight="bold")
        ax.text(4.5, -2.0, "the far via reaches the array and is joined: one group of 17" if rule == "max" else "the array's balls (radius 2) do not reach the far via: two groups",
                ha="center", fontsize=7.5, color=dk.BLUE)
    dk.save(fig, path)


def fig_causes(path):
    """!
    @brief The three causes on the grid.
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 4.4, 1, 3)
    a, b, c = axs
    # (a) centroid on a cell edge and its mirror
    a.set_xlim(-0.5, 9.5)
    a.set_ylim(-1.5, 4)
    a.set_aspect("equal")
    grid(a, 0, 0, 9, 3)
    a.plot([2, 2], [1.5, 1.5], "o", color=dk.HEAT)
    a.plot([7, 7], [1.5, 1.5], "o", color=dk.BLUE)
    a.add_patch(Rectangle((2.5, 1.0), 1, 1, color=dk.HEAT, alpha=0.25))
    a.add_patch(Rectangle((6.5, 1.0), 1, 1, color=dk.BLUE, alpha=0.25))
    a.text(4.5, -0.8, "centroid on a cell edge: floor() reads the cell to the right\nand above (red), the mirror image reads the cell left of its edge (blue)", ha="center", fontsize=7)
    a.text(4.5, 3.4, "Lumped: rise of the other part at the centroid", ha="center", fontsize=8, weight="bold")
    # (b) FDM copper edge between nodes
    b.set_xlim(-0.5, 9.5)
    b.set_ylim(-1.5, 4)
    b.set_aspect("equal")
    for k in range(9):
        b.plot([k + 0.5, k + 0.5], [0.5, 2.5], color="#999", lw=0.5)
    b.add_patch(Rectangle((0.5, 1.4), 3.5, 0.2, color=dk.COPPER))
    b.add_patch(Rectangle((5.5, 1.4), 3.5, 0.2, color=dk.COPPER))
    for k in range(10):
        b.plot(k - 0.0 + 0.0, 1.5, "o", color="k", ms=3)
    b.annotate("", xy=(4.0, 2.4), xytext=(5.5, 2.4), arrowprops=dict(arrowstyle="<->", color=dk.HEAT))
    b.text(4.75, 2.7, "true gap", ha="center", fontsize=7, color=dk.HEAT)
    b.text(4.5, 0.2, "the face between a copper node and an empty node carries the mean of the\ntwo sheets: half of S bridges the gap (arithmetic); the harmonic mean carries 0", ha="center", fontsize=7)
    b.text(4.5, 3.4, "FDM: copper edge between two nodes", ha="center", fontsize=8, weight="bold")
    # (c) via on a line, mirror
    c.set_xlim(-0.5, 9.5)
    c.set_ylim(-1.5, 4)
    c.set_aspect("equal")
    grid(c, 0, 0, 9, 3)
    c.plot([2], [1.5], "o", color=dk.HEAT)
    c.plot([7], [1.5], "o", color=dk.BLUE)
    c.add_patch(Rectangle((2, 1), 1, 1, color=dk.HEAT, alpha=0.25))
    c.add_patch(Rectangle((6, 1), 1, 1, color=dk.BLUE, alpha=0.25))
    c.text(4.5, -0.8, "tuned_footprint puts a via on a line in the cell right/above it:\nthe mirror image of the via (blue) lands in the cell left of its line", ha="center", fontsize=7)
    c.text(4.5, 3.4, "3D solid: via on a grid line", ha="center", fontsize=8, weight="bold")
    dk.save(fig, path)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_grouping(OUT / "fig_01_grouping_rule.png")
    fig_causes(OUT / "fig_04_causes_on_the_grid.png")
