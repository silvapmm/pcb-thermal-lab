#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Schematic figures of the investigation: the air paths round a horizontal board with the law of each face, the numerical domain and the staggered grid of lib/mac2d.py, and the test set-up of docs/measurement-plan.md.
@details No data is computed. Writes figures/fig_01_air_paths_and_laws_of_a_horizontal_board.png, fig_02_numerical_domain_and_staggered_grid.png and
         fig_03_test_boards_and_set_up.png (the numbers 04 and above belong to `make_figures.py`, one numbering for both).
Usage: .venv/bin/python research/convection-laws/scripts/make_diagrams.py   (from the repository root)
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

from matplotlib.patches import Circle, Rectangle                   # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"
HOT = "#e07b6a"


def stream(ax, xs, ys, color, width=1.3):
    """!
    @brief A streamline with an arrow head.
    @param ax Axes.
    @param xs x coordinates.
    @param ys y coordinates.
    @param color Colour.
    @param width Line width.
    @return None.
    """
    ax.plot(xs, ys, color=color, linewidth=width)
    ax.annotate("", (xs[-1], ys[-1]), (xs[-2], ys[-2]), arrowprops={"arrowstyle": "-|>", "color": color, "linewidth": width})


def fig_air_paths():
    """!
    @brief Section of a horizontal board: air paths above and below, and the laws that the program, the textbook and the candidates give to each face.
    @return None.
    """
    fig, (a, b) = dk.canvas(11.5, 4.6, 1, 2, ratios=[1.25, 1])
    a.set_xlim(0, 12)
    a.set_ylim(-4.2, 4.6)
    a.add_patch(Rectangle((2, -0.12), 8, 0.24, facecolor=dk.FR4, edgecolor="k"))
    a.add_patch(Rectangle((2, 0.12), 8, 0.06, facecolor=dk.COPPER))
    a.add_patch(Rectangle((2, -0.18), 8, 0.06, facecolor=dk.COPPER))
    a.add_patch(Rectangle((5.2, 0.18), 1.6, 0.35, facecolor="#444", edgecolor="k"))
    a.text(6, 0.7, "part (heat source)", ha="center", fontsize=8)
    # above: air drawn in along the board towards the centre, plume rising
    for x0 in (2.0, 10.0):
        s = 1 if x0 < 6 else -1
        stream(a, [x0 - s * 1.2, x0 + s * 0.8, x0 + s * 2.4, 6 + s * 0.3, 6 + s * 0.15], [1.4, 0.5, 0.45, 0.7, 1.9], "#c0392b", 1.2)
    stream(a, [6, 6, 6.0], [1.0, 2.6, 4.0], "#c0392b", 2.0)
    a.text(9.0, 3.3, "FACE UP: hot layer under colder air;\nthe air runs in along the board and leaves\nin a plume above the centre (unsteady above Ra ~ 1e4)", fontsize=7, ha="center")
    # below: the hot air is trapped under the board, flows outwards along the face
    for x0 in (2.0, 10.0):
        s = 1 if x0 < 6 else -1
        stream(a, [6 + s * 0.2, 6 + s * 1.8, x0 + s * 0.2, x0 + s * 1.6], [-0.5, -0.55, -0.6, -1.4], dk.BLUE, 1.2)
    stream(a, [0.3, 1.2, 1.9], [-2.4, -1.6, -0.9], dk.BLUE, 1.0)
    stream(a, [11.7, 10.8, 10.1], [-2.4, -1.6, -0.9], dk.BLUE, 1.0)
    a.text(6, -2.7, "FACE DOWN: stable layer against the board;\nflow to the edges, cold air enters at the sides", fontsize=8, ha="center", color=dk.BLUE)
    a.annotate("", (2, -3.9), (10, -3.9), arrowprops={"arrowstyle": "<->"})
    a.text(6, -4.15, "A/P = W H / 2(W + H)  (characteristic length)", fontsize=8, ha="center")
    a.set_title("Horizontal board, section", fontsize=9)
    # right: the table of laws
    b.set_xlim(0, 10)
    b.set_ylim(0, 10)
    rows = [("", "program", "candidate", "range as published"),
            ("face up", "0.54 Ra^1/4\n(Lloyd-Moran, M)", "Raithby-Hollands\n0.560 Ra^1/4 /\n[1+(0.492/Pr)^(9/16)]^(4/9)\n+ 1.4/ln(1+1.4/Nu)", "1 < Ra < 1e7\n(Lienhard 8.37)\nLM: 2.2e4 .. 8e6"),
            ("face down", "0.27 Ra^1/4", "0.475 Ra^1/5 (Goldstein-Lau, S)\n0.58 Ra_W^1/5 (Fujii-Imura,\nwater, 2D)\n0.82 Ra_D^1/5 Pr^.034 (disc)", "1e6 .. 1e11 (FI)\nboards: 3e2 .. 2e4"),
            ("vertical", "Churchill-Chu\n8.13b (general)", "8.13a laminar\n(default of new projects)", "Ra < 1e9 laminar")]
    ys = [9.0, 7.6, 4.4, 1.8]
    xs = [0.0, 1.3, 3.5, 7.6]
    for r, y in zip(rows, ys):
        for c, x in enumerate(xs):
            b.text(x, y, r[c], fontsize=7 if c else 8, va="top", fontweight="bold" if (r is rows[0] or c == 0) else "normal")
    b.plot([0, 10], [9.3, 9.3], color="k", lw=0.5)
    b.plot([0, 10], [8.6, 8.6], color="k", lw=0.5)
    b.set_title("Laws compared in this folder", fontsize=9)
    dk.save(fig, OUT / "fig_01_air_paths_and_laws_of_a_horizontal_board.png")


def fig_domain():
    """!
    @brief The numerical domain of the strip in a cold box, and the staggered (MAC) arrangement of the unknowns.
    @return None.
    """
    fig, (a, b) = dk.canvas(11, 4.6, 1, 2, ratios=[1.2, 1])
    a.set_xlim(-0.6, 8)
    a.set_ylim(-4, 7.2)
    a.add_patch(Rectangle((0, -3), 4, 9, facecolor="#f4f8fc", edgecolor="k"))
    a.plot([0, 1], [0, 0], color=HOT, lw=4)
    a.text(0.5, 0.25, "plate  T = 1", color=HOT, ha="center", fontsize=8)
    a.plot([0, 0], [-3, 6], color="k", ls="--", lw=1)
    a.text(-0.1, 1.5, "symmetry line\n(x = 0)", ha="right", fontsize=7)
    for (x, y, t, ha) in ((2, 6.15, "cold lid  T = 0, no slip", "center"), (2, -3.45, "cold floor  T = 0, no slip", "center"), (4.1, 1.5, "cold wall\nT = 0", "left")):
        a.text(x, y, t, ha=ha, fontsize=7)
    stream(a, [3.2, 2.6, 1.7], [-1.5, -0.6, -0.15], dk.BLUE, 1.0)
    stream(a, [3.2, 2.4, 1.3, 0.3], [2.5, 1.0, 0.45, 0.35], "#c0392b", 1.0)
    stream(a, [0.15, 0.15, 0.2], [0.4, 2.2, 4.2], "#c0392b", 1.4)
    a.annotate("", (1, -3.6), (0, -3.6), arrowprops={"arrowstyle": "<->"})
    a.text(0.5, -3.85, "half width = 1 = A/P", fontsize=7, ha="center")
    a.text(6, 5.2, "sizes of the box: s x (W 4, up 6,\ndown 3) plate half widths;\ns = 1 and 2", fontsize=8)
    a.text(6, 3.0, "unknowns: u, v, p, T\nPr = 0.71, Ra on the half width\nBoussinesq, steady, 2D,\nsymmetric about x = 0", fontsize=8)
    a.set_title("Domain of study_plate_mac.py", fontsize=9)
    # staggered grid
    b.set_xlim(0, 6)
    b.set_ylim(0, 6)
    for i in range(3):
        for j in range(3):
            b.add_patch(Rectangle((1 + 1.5 * i, 1 + 1.5 * j), 1.5, 1.5, fill=False, edgecolor="#888"))
            b.plot([1.75 + 1.5 * i], [1.75 + 1.5 * j], "o", color="k", ms=4)
            if i < 3:
                b.plot([1 + 1.5 * i], [1.75 + 1.5 * j], ">", color=dk.BLUE, ms=6)
            b.plot([1.75 + 1.5 * i], [1 + 1.5 * j], "^", color="#c0392b", ms=6)
    b.text(3.6, 0.35, "o  T and p in the cell centre\n>  u on the vertical faces       ^  v on the horizontal faces", fontsize=8, ha="center")
    b.text(3.0, 5.65, "central fluxes, implicit diffusion,\nprojection for div u = 0", fontsize=8, ha="center")
    b.set_title("Staggered (MAC) arrangement", fontsize=9)
    dk.save(fig, OUT / "fig_02_numerical_domain_and_staggered_grid.png")


def fig_setup():
    """!
    @brief The three test boards (top views with thermocouple positions) and the set-up (side view).
    @return None.
    """
    fig, axs = dk.canvas(12, 6.2, 2, 3)
    names = ["A: full copper", "B: 20 mm pad", "C: pad + 3 x 3 vias"]
    for k, ax in enumerate(axs[0]):
        ax.set_xlim(-6, 106)
        ax.set_ylim(-6, 86)
        ax.set_aspect("equal")
        ax.add_patch(Rectangle((0, 0), 100, 80, facecolor=dk.FR4, edgecolor="k"))
        if k == 0:
            ax.add_patch(Rectangle((1, 1), 98, 78, facecolor=dk.COPPER, alpha=0.8))
        else:
            ax.add_patch(Rectangle((40, 30), 20, 20, facecolor=dk.COPPER, alpha=0.9))
        ax.add_patch(Rectangle((46, 36), 8, 8, facecolor="#333"))
        if k == 2:
            for i in range(3):
                for j in range(3):
                    ax.add_patch(Circle((47.4 + 2.6 * i, 37.4 + 2.6 * j), 0.5, facecolor="white", edgecolor="k", lw=0.4))
        pts = [(50, 40), (50, 54), (50, 66), (74, 40), (92, 40)] if k == 0 else [(50, 40), (50, 54), (50, 66), (74, 40), (92, 40)]
        for n, (x, y) in enumerate(pts):
            ax.plot(x, y, "x", color="#c0392b", ms=7, mew=2)
            ax.text(x + 2, y + (4.5 if n == 0 else 2.5), f"T{n + 1}", fontsize=7, color="#c0392b")
        ax.set_title(names[k] + " (top view, layer 1)", fontsize=9)
        ax.text(50, -5, "100 x 80 mm, 1.6 mm FR-4, 35 um copper both sides", fontsize=6, ha="center")
    # side view
    ax = axs[1][0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.add_patch(Rectangle((2, 3), 6, 0.15, facecolor=dk.FR4, edgecolor="k"))
    ax.add_patch(Rectangle((4.4, 3.15), 1.2, 0.3, facecolor="#333"))
    for x in (2.3, 7.7):
        ax.plot([x, x], [2.2, 3], color="k", lw=1)
    ax.add_patch(Rectangle((0.3, 0.2), 9.4, 5.2, fill=False, edgecolor="#777", ls="--"))
    ax.text(5, 5.0, "draught shield: a box without lid,\nsides at least 0.3 m away", ha="center", fontsize=7)
    ax.text(5, 1.5, "board on 4 needle supports, 20 mm\nabove a table; air-temperature TC\n(shielded) 0.15 m from the board", ha="center", fontsize=7)
    ax.set_title("Set-up, horizontal (the board is turned over for 'face down')", fontsize=8)
    ax = axs[1][1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.add_patch(Rectangle((0.5, 0.5), 2.2, 4.4, facecolor="#e8e8e8", edgecolor="k"))
    ax.text(1.6, 2.7, "bench supply\n+ 4-wire V and I\n(or 2 DMMs)", ha="center", fontsize=7)
    ax.add_patch(Rectangle((4, 0.5), 2.4, 4.4, facecolor="#e8e8e8", edgecolor="k"))
    ax.text(5.2, 2.7, "logger,\ntype K TCs\n(5 + 1 air)", ha="center", fontsize=7)
    ax.annotate("", (4, 4.0), (2.7, 4.0), arrowprops={"arrowstyle": "->"})
    ax.annotate("", (7.6, 2.7), (6.4, 2.7), arrowprops={"arrowstyle": "->"})
    ax.add_patch(Rectangle((7.6, 1.5), 2.0, 2.4, facecolor=dk.FR4, edgecolor="k"))
    ax.text(8.6, 2.7, "board", ha="center", fontsize=7)
    ax.set_title("Instruments", fontsize=9)
    ax = axs[1][2]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.text(0.2, 5.4, "Runs (each at 3 powers, steady state,\nrise at 35 K +- 15 K)", fontsize=8, va="top")
    ax.text(0.2, 3.8, "1  horizontal, layer 1 up\n2  horizontal, turned over (layer 1 down)\n3  vertical, long side vertical\nrepeat 1 on board A with emissivity changed\n(matt black paint on one face only)", fontsize=8, va="top")
    ax.set_title("Run list", fontsize=9)
    dk.save(fig, OUT / "fig_03_test_boards_and_set_up.png")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_air_paths()
    fig_domain()
    fig_setup()
