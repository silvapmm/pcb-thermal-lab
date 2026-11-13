#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of research/independent-fem-edge: the four canonical boards (plan views with the wall, the source and the via), and the section of a cooled wall in the two methods (the finite-element bricks with the film integrated on the face, the cell-centred cell with the half-cell conduction in series).
@details No data and no program. Writes figures/fig_05_cases.png and figures/fig_06_methods_at_the_wall.png. Run (repository root): .venv/bin/python research/independent-fem-edge/scripts/make_diagrams.py
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FOLDER, "..", ".."))
sys.path.insert(0, os.path.join(FOLDER, ".."))
import diagram_kit as K                                            # noqa: E402

FIG = os.path.join(FOLDER, "figures")
WALL = "#c0392b"


def fig_01():
    """!
    @brief Plan views of the four canonical boards: strong-edge plate (a), via near the wall (b), 20 mm square (c), T outline (d); the wall in red, the symmetry planes dashed.
    @return None.
    """
    fig, ax = K.canvas(11, 3.6, 1, 4)
    a = ax[0]
    a.add_patch(Rectangle((0, 0), 10, 5, fc=K.COPPER, ec="k", alpha=0.5))
    a.add_patch(Rectangle((1, 4), 3, 1, fc=K.HEAT, ec="k"))
    a.plot([0, 10, 10, 0, 0], [5, 5, 0, 0, 5], color=WALL, lw=2.5)
    a.plot([0, 10], [5, 5], "k--", lw=1)
    a.set_xlim(-1, 11)
    a.set_ylim(-1, 6.5)
    a.set_title("(a) plate: 10 x 10 mm, 4 layers,\nhalf domain, film on 3 walls", fontsize=8)
    b = ax[1]
    b.add_patch(Rectangle((0, 0), 10, 5, fc=K.COPPER, ec="k", alpha=0.5))
    b.add_patch(Rectangle((1, 4), 3, 1, fc=K.HEAT, ec="k"))
    b.add_patch(Circle((9.84, 5), 0.3, fc="k"))
    b.add_patch(Circle((7.0, 5), 0.3, fc="k"))
    b.plot([0, 10, 10, 0, 0], [5, 5, 0, 0, 5], color=WALL, lw=2.5)
    b.plot([0, 10], [5, 5], "k--", lw=1)
    b.text(9.84, 5.7, "0.16 mm", fontsize=7, ha="center")
    b.text(7.0, 5.7, "3 mm", fontsize=7, ha="center")
    b.set_xlim(-1, 11)
    b.set_ylim(-1, 6.5)
    b.set_title("(b) via, drill 0.3 mm, at 0.16 mm\nor 3 mm from the wall", fontsize=8)
    c = ax[2]
    c.add_patch(Rectangle((0, 0), 10, 10, fc="white", ec=WALL, lw=2.5))
    c.add_patch(Rectangle((0, 0), 8.8, 8.8, fc=K.COPPER, ec="k", alpha=0.5))
    c.add_patch(Rectangle((0, 0), 2, 2, fc=K.HEAT, ec="k"))
    c.plot([0, 10], [0, 0], "k--", lw=1)
    c.plot([0, 0], [0, 10], "k--", lw=1)
    c.set_xlim(-1, 11)
    c.set_ylim(-1, 11)
    c.set_title("(c) 20 mm square, quarter,\ncopper 1.2 mm in or to the wall;\nthe program turns it by 0..45 deg", fontsize=8)
    d = ax[3]
    pts = [(10, 20), (20, 20), (20, 14), (13.2, 14), (13.2, 0), (10, 0)]
    d.add_patch(Polygon(pts, fc=K.COPPER, ec=WALL, lw=2.5, alpha=0.6))
    d.add_patch(Rectangle((10, 16), 1.2, 2.4, fc=K.HEAT, ec="k"))
    d.plot([10, 10], [0, 20], "k--", lw=1)
    d.set_xlim(8, 22)
    d.set_ylim(-1, 21)
    d.set_title("(d) T outline, half domain,\ncopper to the wall, h 200", fontsize=8)
    for x in ax:
        x.set_aspect("equal")
        x.set_xticks([])
        x.set_yticks([])
    K.save(fig, os.path.join(FIG, "fig_05_cases.png"), "Four canonical cooled-wall boards (red: wall with the film; dashed: symmetry plane; orange: source)")


def fig_02():
    """!
    @brief The wall of a copper layer over laminate in the two methods.
    @return None.
    """
    fig, ax = K.canvas(10, 3.8, 1, 2)
    for i, (a, title) in enumerate(zip(ax, ("finite element: continuous trilinear T, film on the face by the face mass matrix", "cell-centred finite volume: one value per cell, half-cell conduction in series with h"))):
        a.add_patch(Rectangle((0, 2.6), 6, 0.35, fc=K.COPPER, ec="k"))
        a.add_patch(Rectangle((0, 0), 6, 2.6, fc=K.FR4, ec="k", alpha=0.6))
        a.plot([6, 6], [0, 2.95], color=WALL, lw=3)
        a.set_xlim(-0.5, 8)
        a.set_ylim(-0.5, 3.6)
        a.set_xticks([])
        a.set_yticks([])
        a.set_title(title, fontsize=7)
        if i == 0:
            for x in (0, 1.5, 3, 4.5, 6):
                a.plot([x, x], [0, 2.95], color="grey", lw=0.6)
            for y in (0, 0.6, 1.3, 2.0, 2.6, 2.95):
                a.plot([0, 6], [y, y], color="grey", lw=0.6)
                a.plot([6], [y], "ko", ms=3)
            a.annotate("h T on the face,\nintegrated exactly", (6, 1.3), (6.4, 1.3), fontsize=7, arrowprops=dict(arrowstyle="->"))
        else:
            for x in (0.75, 2.25, 3.75, 5.25):
                for y in (0.3, 0.9, 1.6, 2.3, 2.78):
                    a.plot([x], [y], "ko", ms=3)
            a.plot([5.25, 6], [1.6, 1.6], "k-", lw=2)
            a.annotate("k/(dx/2) and h\nin series", (5.6, 1.6), (6.4, 1.0), fontsize=7, arrowprops=dict(arrowstyle="->"))
    K.save(fig, os.path.join(FIG, "fig_06_methods_at_the_wall.png"), "Section at a cooled wall: copper over laminate, the node placement and the wall film in the two methods")


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_01()
    fig_02()
