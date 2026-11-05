#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation: a via next to a board edge on the grid, the true image and the image the lattice has, and the heat paths in a section (figure 01).
@details No data and no program: the distances are those of the test board of the README (cell 1 mm, via 0.16 mm from the insulated edge, drill 0.3 mm).
         Run from the repository root: `.venv/bin/python research/via-edge-image/scripts/make_diagrams.py`.
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle  # noqa: E402

FIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")


def fig_01():
    """!
    @brief Figure 01: plan with the cells, the footprint, the true image and the lattice image; section with the heat paths.
    @return None.
    """
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.15, 1]})
    # Plan: the wall at x = 0, board to the left (x < 0), cells of 1 mm; coordinates in mm measured from the wall, positive towards the board interior reversed for clarity
    for k in range(-5, 3):
        a.axvline(k, color="#cccccc", lw=0.8, zorder=0)
    for k in range(-3, 4):
        a.axhline(k, color="#cccccc", lw=0.8, zorder=0)
    a.add_patch(Rectangle((-5, -3), 5, 6, fc="#f3e9d0", ec="none", zorder=-1))
    a.axvline(0, color="k", lw=2.5)
    a.text(0.08, 2.55, "edge (insulated or\nweakly cooled)", fontsize=8, va="top")
    via = (-0.16, 0.0)
    a.add_patch(Circle(via, 0.15, fc="#c0392b", ec="k", zorder=3))
    a.text(-1.0, -0.05, "via", ha="center", fontsize=8, color="#c0392b")
    for yc in (-0.5, 0.5):                                              # footprint cells: centres 0.5 mm from the wall
        a.plot(-0.5, yc, "s", color="#2471a3", ms=9, zorder=3)
    a.text(-1.9, 0.5, "footprint\n(cell centres)", ha="center", va="center", fontsize=8, color="#2471a3")
    a.plot(0.32 - 0.16, 0.0, "o", mfc="none", mec="#c0392b", ms=11, mew=2, zorder=3)      # the true image: 0.16 mm beyond the wall
    a.plot(0.5, 0.5, "s", mfc="none", mec="#2471a3", ms=9, zorder=3)                          # the lattice image of a cell centre: 0.5 mm beyond the wall
    a.plot(0.5, -0.5, "s", mfc="none", mec="#2471a3", ms=9, zorder=3)
    a.text(0.75, 1.25, "true image\n(0.16 mm beyond)", fontsize=8, color="#c0392b", va="center")
    a.annotate("", xy=(0.16, 0.08), xytext=(0.7, 1.05), arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.8))
    a.text(0.75, -0.95, "lattice image\n(0.5 mm beyond)", fontsize=8, color="#2471a3", va="center")
    a.annotate("", xy=(0.16, -1.9), xytext=(-0.16, -1.9), arrowprops=dict(arrowstyle="<->", color="#c0392b"))
    a.annotate("", xy=(0.5, -2.4), xytext=(-0.5, -2.4), arrowprops=dict(arrowstyle="<->", color="#2471a3"))
    a.text(0.0, -1.78, "D_true = 0.32 mm", ha="center", fontsize=8, color="#c0392b")
    a.text(0.0, -2.28, "D_lat about 1.0 mm", ha="center", fontsize=8, color="#2471a3")
    a.set_xlim(-3, 2.2)
    a.set_ylim(-3, 3)
    a.set_aspect("equal")
    a.set_title("Plan: the mean potential of the footprint sees the lattice image,\nthe via sees the true one", fontsize=9)
    a.set_xlabel("mm (edge at 0)", fontsize=8)
    a.tick_params(labelsize=7)
    # Section: planes, the barrel, heat paths and the image sink
    for k, y in enumerate((3.0, 2.2, 1.4, 0.6)):
        b.add_patch(Rectangle((-5, y), 5, 0.12, fc="#b87333", ec="none"))
        b.text(-5.1, y + 0.05, f"L{k + 1}", ha="right", fontsize=7)
    b.add_patch(Rectangle((-5, 0.6), 5, 2.52, fc="#f6edd6", ec="none", zorder=-1, alpha=0.7))
    b.add_patch(Rectangle((-0.2, 0.6), 0.08, 2.52, fc="#b87333", ec="k", lw=0.5))
    b.axvline(0, color="k", lw=2.5)
    b.add_patch(Rectangle((-4.0, 3.15), 1.6, 0.22, fc="#444444"))
    b.text(-3.2, 3.5, "source", ha="center", fontsize=8)
    for y in (3.06, 2.26, 1.46, 0.66):
        b.add_patch(FancyArrowPatch((-3.2, 3.05), (-0.25, y), arrowstyle="->", color="#c0392b", lw=1.0, mutation_scale=8, connectionstyle="arc3,rad=0.15"))
    b.add_patch(FancyArrowPatch((-0.1, 3.0), (-0.1, 0.7), arrowstyle="->", color="#c0392b", lw=2.0, mutation_scale=10))
    b.text(0.25, 1.8, "barrel", fontsize=8, color="#c0392b")
    b.text(-2.5, 0.15, "the wall turns the lateral flux back: the mirror\nimage doubles the constriction near the edge", fontsize=8, ha="center")
    b.set_xlim(-5.6, 1.2)
    b.set_ylim(-0.3, 3.9)
    b.set_aspect("equal")
    b.axis("off")
    b.set_title("Section: heat paths from the source down the barrel; at the wall they reflect", fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_01_via_near_edge.png"), dpi=140)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_01()
