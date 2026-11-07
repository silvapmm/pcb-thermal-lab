#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the cut cell: the quantities a scheme needs (cover, centroid, apertures, distance to the outline) and the chain of resistances from a node to the air in each scheme.
@details No data and no program: fig_01 is the plan of a 3 x 3 patch of cells cut by a slanted outline with the apertures of the faces, the centres, the centroid of the board part and
         the closest outline point; fig_02 is the section along the normal to the outline (node, link, node, film) for the program, the aperture and the links schemes, and the
         film of Bochkov and Gibou; fig_06 (added by the review) is the plan of an edge column whose board part is a sliver, with the heat path in the program and with the aperture.
         Written to `figures/` (numbers 01, 02 and 06; `make_figures.py` draws 03 to 05 and 07).
Usage: .venv/bin/python research/cut-cell-links/scripts/make_diagrams.py   (from the repository root)
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
import numpy as np                                    # noqa: E402
from matplotlib.patches import Polygon, Rectangle     # noqa: E402

FIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")


def clip_halfplane(poly, a, b, c):
    """!
    @brief Clip a polygon to the half plane a x + b y <= c (Sutherland-Hodgman).
    @param poly List of (x, y).
    @param a Coefficient of x.
    @param b Coefficient of y.
    @param c Right-hand side.
    @return List of (x, y).
    """
    out = []
    n = len(poly)
    for i in range(n):
        p, q = np.array(poly[i]), np.array(poly[(i + 1) % n])
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(tuple(p))
        if fp * fq < 0:
            t = fp / (fp - fq)
            out.append(tuple(p + t * (q - p)))
    return out


def fig_geometry():
    """!
    @brief Figure 1: plan of a 3 x 3 patch cut by a slanted outline, with the quantities of the cut-cell schemes.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(7.4, 6.2))
    # Outline: the line x + 0.55 y = 2.35 (board on the left); cell size 1
    a, b, c = 1.0, 0.55, 2.35
    for i in range(3):
        for j in range(3):
            cell = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            part = clip_halfplane(cell, a, b, c)
            ax.add_patch(Rectangle((i, j), 1, 1, fill=False, ec="0.6", lw=0.8))
            if len(part) >= 3:
                ax.add_patch(Polygon(part, closed=True, fc="#f4b183", ec="none", alpha=0.25 if len(part) == 4 and np.allclose(sorted(part), sorted(cell)) else 0.55))
    ys = np.array([-0.2, 3.2])
    ax.plot((c - b * ys) / a, ys, color="#c00000", lw=2.2, label="outline")
    # The cell (1, 1): its board part, centroid, centre, apertures
    cell = [(1, 1), (2, 1), (2, 2), (1, 2)]
    part = np.array(clip_halfplane(cell, a, b, c))
    x, y = part[:, 0], part[:, 1]
    xn, yn = np.roll(x, -1), np.roll(y, -1)
    cr = x * yn - xn * y
    area = 0.5 * cr.sum()
    cx, cy = ((x + xn) * cr).sum() / (6 * area), ((y + yn) * cr).sum() / (6 * area)
    ax.plot(1.5, 1.5, "o", color="0.15", ms=8, label="cell centre (program, aperture)")
    ax.plot(cx, cy, "s", color="#1f4e79", ms=8, label="centroid of the board part (links)")
    # The closest outline point to the centre and the signed distance d
    n = np.array([a, b]) / np.hypot(a, b)
    d = (c - (a * 1.5 + b * 1.5)) / np.hypot(a, b)
    p = np.array([1.5, 1.5]) + d * n
    ax.annotate("", xy=p, xytext=(1.5, 1.5), arrowprops=dict(arrowstyle="<->", color="#548235", lw=1.6))
    ax.text(*(np.array([1.5, 1.5]) + 0.5 * d * n + np.array([-0.02, 0.1])), "d", color="#548235", fontsize=13)
    # Apertures: the open part of the faces of the cell (1, 1)
    xr = (c - b * 1.0) / a          # right face x = 2: open where y <= (c - 2) / b
    yo = (c - 2.0) / b
    ax.plot([2, 2], [1, min(max(yo, 1), 2)], color="#7030a0", lw=5, solid_capstyle="butt", label="aperture of a face (open length)")
    ax.plot([1, 2], [2, 2], color="#7030a0", lw=5, solid_capstyle="butt")
    ax.plot([1, 1], [1, 2], color="#7030a0", lw=5, solid_capstyle="butt")
    ax.plot([1, min(2, (c - b * 1) / a)], [1, 1], color="#7030a0", lw=5, solid_capstyle="butt")
    ax.annotate("", xy=(cx + 0.55, cy), xytext=(cx, cy), arrowprops=dict(arrowstyle="->", color="#c55a11", lw=1.8))
    ax.annotate("", xy=(2.45, 1.0), xytext=(2.0, 1.0), arrowprops=dict(arrowstyle="->", color="#c55a11", lw=1.4))
    ax.text(cx - 0.05, cy - 0.17, "c = %.2f" % area, fontsize=11, color="#843c0c")
    ax.text(0.05, 2.78, "heat reaches the outline through the film\n(and, along the normal, through the open strip)", fontsize=9, color="#843c0c")
    ax.set_xlim(-0.2, 3.2)
    ax.set_ylim(-0.2, 3.2)
    ax.set_aspect("equal")
    ax.set_title("A cut cell: cover c, centroid, apertures of the faces, distance d to the outline")
    ax.legend(loc="lower left", fontsize=8, framealpha=0.95)
    ax.axis("off")
    fig.savefig(os.path.join(FIG, "fig_01_cut_cell_quantities.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def resistor(ax, x0, x1, y, label, color="k"):
    """!
    @brief Draw a resistor symbol (zigzag) between x0 and x1 at height y.
    @param ax Axes.
    @param x0 Left.
    @param x1 Right.
    @param y Height.
    @param label Text above.
    @param color Line colour.
    @return None.
    """
    xs = np.linspace(x0, x1, 9)
    ys = y + np.array([0, 0.09, -0.09, 0.09, -0.09, 0.09, -0.09, 0.09, 0]) * (1 if x1 - x0 > 0.3 else 0.5)
    ax.plot(xs, ys, color=color, lw=1.4)
    ax.text(0.5 * (x0 + x1), y + 0.17, label, ha="center", fontsize=8)


def fig_chains():
    """!
    @brief Figure 2: the chain of resistances along the normal to the outline for each scheme (the whole neighbour on the left, the cut cell on the right, the air at the far right).
    @return None.
    """
    fig, axes = plt.subplots(4, 1, figsize=(8.2, 7.4), sharex=True)
    rows = [
        ("program: node at the centre, link from the cover-scaled sheets, film on the node", dict(cut_node=0.0, link="2 / (1 + c)  ->  2c / (1 + c) S", film="film  g0", d=None)),
        ("aperture: link a S over one cell width, film on the node", dict(cut_node=0.0, link="a S / dx", film="film  g0", d=None)),
        ("aperture + film: as aperture, the film in series with the conduction d / (S L)", dict(cut_node=0.0, link="a S / dx", film="g0 / (1 + g0 d / (S L))", d=True)),
        ("links: nodes at the centroids, link a S / (d1 + d2), film on the node", dict(cut_node=-0.35, link="a S / (d1 + d2)", film="film  g0", d=None)),
    ]
    for ax, (title, o) in zip(axes, rows):
        ax.set_xlim(-0.2, 6.2)
        ax.set_ylim(-0.6, 0.8)
        ax.axis("off")
        ax.set_title(title, loc="left", fontsize=9)
        ax.add_patch(Rectangle((0, -0.35), 2, 0.7, fc="#dde8f3", ec="0.5"))
        xc = 3.0 + (o["cut_node"] if o["cut_node"] else 0.0) + (0.0 if o["cut_node"] == 0.0 else 0.0)
        ax.add_patch(Rectangle((2, -0.35), 1.6, 0.7, fc="#f4b183", ec="0.5", alpha=0.6))
        ax.plot([1.0], [0], "o", color="k")
        xn = 2.8 if o["cut_node"] == 0.0 else 3.1
        ax.plot([xn], [0], "o", color="#1f4e79" if o["cut_node"] else "k")
        ax.axvline(3.6, color="#c00000", lw=2.2)
        resistor(ax, 1.0, xn, 0.0, o["link"])
        resistor(ax, 3.6, 5.2, 0.0, o["film"] if not o["d"] else "film in series")
        ax.plot([xn, 3.6], [0, 0], color="k", lw=1.0) if not o["d"] else None
        if o["d"]:
            resistor(ax, xn, 3.6, 0.0, "d / (S L)", color="#548235")
        ax.plot([5.2, 5.9], [0, 0], color="k", lw=1.4)
        ax.text(6.0, 0.0, "air", fontsize=9, va="center")
        ax.text(1.0, -0.5, "whole cell", ha="center", fontsize=8)
        ax.text(2.8, -0.5, "cut cell", ha="center", fontsize=8)
        ax.text(3.6, 0.55, "outline", ha="center", fontsize=8, color="#c00000")
    fig.savefig(os.path.join(FIG, "fig_02_scheme_chains.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_sliver_paths():
    """!
    @brief Figure 6 (added by the review): plan of an edge column whose board part is a sliver (cover c = 0.02), with the heat path to the air in the program and with the aperture.
    @details Two panels over the same three cells: the whole cell, the sliver cell (centre off the board) and the outline 0.02 of a cell inside it. Program: the link into the sliver is
             the harmonic mean of S and c S over one cell, 2c/(1+c) S (about 0.04 S), so the film of the whole edge length that sits on the sliver node is nearly cut off and the
             board edge behaves as insulated. Aperture: the face between the two cells is open over its whole height (a = 1), the link is S, and with the film the conduction from
             the sliver node (0.48 of a cell outside the board) to the outline is subtracted (d < 0), so the chain is the real 0.52 cell of sheet plus the film.
    @return None.
    """
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.4))
    c = 0.12                                       # drawn wider than the 0.02 of the study, so that the strip can be seen
    for ax, title, strong in ((axes[0], "program: link 2c/(1+c) S into the sliver", False), (axes[1], "aperture (+ film): link a S, a = 1; film after d < 0", True)):
        ax.set_xlim(-0.4, 3.4)
        ax.set_ylim(-0.95, 1.35)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=9.5)
        for i in range(3):
            ax.add_patch(Rectangle((i, 0), 1, 1, fill=False, ec="0.55", lw=0.9))
        # Board: from x = 1 - c to the right (the sliver is the strip [1 - c, 1] of the left cell)
        ax.add_patch(Rectangle((1 - c, 0), 2 + c, 1, fc="#f4b183", ec="none", alpha=0.55))
        ax.plot([1 - c, 1 - c], [-0.15, 1.15], color="#c00000", lw=2.4)
        ax.text(1 - c - 0.04, 1.2, "outline", color="#c00000", fontsize=8, ha="right")
        ax.text(0.5, -0.12, "sliver cell, c = 0.02\n(drawn wider; node off the board)", ha="center", va="top", fontsize=8)
        ax.text(1.5, -0.12, "whole cell", ha="center", va="top", fontsize=8)
        ax.text(2.5, -0.12, "whole cell", ha="center", va="top", fontsize=8)
        for x in (0.5, 1.5, 2.5):
            ax.plot([x], [0.5], "o", color="k", ms=6)
        # Link into the sliver: thin (program) or full (aperture)
        ax.plot([0.5, 1.5], [0.5, 0.5], color="#7030a0", lw=4.0 if strong else 0.6)
        ax.text(1.2, 0.62, "a S = S" if strong else "0.04 S", ha="center", fontsize=8.5, color="#7030a0")
        ax.plot([1.5, 2.5], [0.5, 0.5], color="#7030a0", lw=4.0)
        # Film on the sliver node to the air (the whole edge length of the cell)
        ax.annotate("", xy=(-0.3, 0.5), xytext=(0.45, 0.5), arrowprops=dict(arrowstyle="-|>", color="#2e7d32", lw=1.6))
        ax.text(-0.05, 0.28, "film g0\n(to air)", ha="center", fontsize=7.5, color="#2e7d32")
        # Heat arriving from the part (to the right)
        ax.annotate("", xy=(2.55, 0.85), xytext=(3.3, 0.85), arrowprops=dict(arrowstyle="-|>", color="#c55a11", lw=1.4))
        ax.text(3.3, 0.95, "heat from the part", ha="right", fontsize=7.5, color="#c55a11")
        if strong:
            ax.annotate("", xy=(0.5, 0.15), xytext=(1 - c, 0.15), arrowprops=dict(arrowstyle="<->", color="#548235", lw=1.0))
            ax.text(0.74, 0.2, "d < 0", fontsize=7.5, color="#548235", ha="center")
            ax.text(1.5, -0.72, "to the air: (1 - |d|) / S + 1 / g0\n= the real 0.52 cell of sheet and the film", ha="center", fontsize=7.8)
        else:
            ax.text(1.5, -0.72, "to the air: 25.5 / S + 1 / g0: the edge acts as insulated\n(+3.5 K at h_side 200, 1 mm, c = 0.02)", ha="center", fontsize=7.8)
    fig.savefig(os.path.join(FIG, "fig_06_sliver_heat_path.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_geometry()
    fig_chains()
    fig_sliver_paths()
