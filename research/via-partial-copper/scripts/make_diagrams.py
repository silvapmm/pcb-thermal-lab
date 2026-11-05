#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation: the section of a via at a copper edge with the heat paths and the fixed footprint weights, the three couplings (program, weighted by the sheet, star), and the plan views of the test cases.
@details Figures 01 to 03 of figures/ (the data figures 04 and later are drawn by make_figures.py). No study is run and no number is computed here; every number on a picture is
         a label of the geometry (drill, pad, antipad) or a statement of the README.
         Files: fig_01_section_copper_edge.png, fig_02_three_couplings.png, fig_03_test_cases_plan.png.
         Usage: python research/via-partial-copper/scripts/make_diagrams.py   (from the repository root).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

import diagram_kit as dk                                                    # noqa: E402
from matplotlib.patches import Circle, Rectangle                            # noqa: E402

OUT = HERE.parent / "figures"


def fig_section(path):
    """!
    @brief Section through a via whose top copper ends at the barrel: where the heat goes, where the program takes it from.
    @param path Output file.
    @return None.
    """
    fig, (a, b) = dk.canvas(13, 5.2, 1, 2, ratios=[1.3, 1])
    a.set_xlim(0, 13)
    a.set_ylim(-1.8, 6.4)
    # laminate and the two copper layers (top copper only on the left of the via)
    dk.layer(a, 0.5, 1.6, 12, 1.8, dk.FR4)
    a.text(2.5, 2.4, "laminate (FR-4)", fontsize=8)
    dk.layer(a, 0.5, 3.4, 6.0, 0.35, dk.COPPER)
    dk.layer(a, 0.5, 1.25, 12, 0.35, dk.COPPER)
    a.text(0.7, 3.95, "top copper ends\nthrough the via centre", fontsize=8)
    a.text(0.7, 0.8, "bottom plane (full copper)", fontsize=8)
    # the barrel
    dk.layer(a, 6.2, 1.25, 0.6, 2.5, "#c98a3b")
    a.text(6.5, 5.5, "barrel", ha="center", fontsize=8)
    # footprint cells (4 cells of 0.25 mm at 0.25 mm cell): half on copper, half on bare laminate
    for k, (x, c) in enumerate([(5.2, "#7fb069"), (5.8, "#7fb069"), (6.4 + 0.2, "#e5989b"), (7.0 + 0.2, "#e5989b")]):
        a.add_patch(Rectangle((x - 0.3, 3.85), 0.6, 0.35, facecolor=c, edgecolor="k", linewidth=0.7))
    a.text(6.5, 4.5, "footprint cells: equal weights w (program)", ha="center", fontsize=7.5)
    # heater
    dk.box(a, 2.6, 5.0, 3.0, 0.9, "heater", "#f8d0d0")
    dk.arrow(a, 4.1, 5.0, 4.1, 3.8, dk.HEAT, label="")
    # heat in the copper to the barrel
    dk.arrow(a, 4.6, 3.58, 6.0, 3.58, dk.HEAT, width=2.2)
    a.text(5.2, 3.0, "heat the copper\ncan bring", fontsize=7.5, color=dk.HEAT, ha="center")
    # demanded flux on bare side
    dk.arrow(a, 7.4, 3.95, 6.9, 3.95, dk.BLUE, width=2.2)
    a.text(10.3, 4.7, "flux the program\ntakes from bare cells\n(weights fixed, bare\nlaminate cannot supply it)", fontsize=7.5, color=dk.BLUE, ha="center")
    # down the barrel and spreading in the bottom plane
    dk.arrow(a, 6.5, 3.0, 6.5, 1.9, dk.HEAT, width=2.2)
    for x0, x1 in [(6.9, 9.8), (6.1, 3.2)]:
        dk.arrow(a, x0, 1.45, x1, 1.45, dk.HEAT)
    a.text(6.5, -1.2, "Result: the bare cells are drained below their neighbours (a cold spot), and\nthe heat that reaches the barrel through the copper is mis-measured.", ha="center", fontsize=8.5)
    a.set_title("Section through a via at a copper edge (not to scale)", fontsize=9)
    # right panel: plan view of the footprint
    b.set_xlim(0, 6)
    b.set_ylim(0, 6)
    b.set_aspect("equal")
    b.add_patch(Rectangle((0.3, 0.6), 2.7, 4.8, facecolor=dk.COPPER, edgecolor="k", linewidth=0.8))
    b.text(1.6, 5.0, "copper", ha="center", fontsize=8)
    b.text(4.5, 5.0, "bare laminate", ha="center", fontsize=8)
    n = 4
    for i in range(2):
        for j in range(2):
            x, y = 2.0 + 1.0 * i, 2.5 + 1.0 * j
            b.add_patch(Rectangle((x, y), 1.0, 1.0, facecolor="none", edgecolor="#333", linewidth=1.0, linestyle="--"))
            b.text(x + 0.5, y + 0.5, "w", ha="center", va="center", fontsize=9, color="#1b4332" if i == 0 else "#9d0208")
    b.add_patch(Circle((3.0, 3.5), 0.38, facecolor="#c98a3b", edgecolor="k"))
    b.plot([3.0, 3.0], [0.6, 5.4], color="k", linewidth=1.6)
    b.axis("off")
    b.set_title("Plan: 2 x 2 footprint cells on a grid, half of them\nwithout copper (weights w are equal)", fontsize=9)
    dk.save(fig, path)


def fig_couplings(path):
    """!
    @brief The three couplings of the footprint cells to the barrel: mean potential (program), mean potential with weights by sheet conductance, and the star (equipotential barrel).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(14, 4.6, 1, 3)
    titles = ["program: prescribed flux shares\nT_mean = sum w_a T_a, one well to the barrel",
              "(a) sheet: the same, but w_a is proportional\nto the sheet conductance of cell a",
              "(c) star: the barrel is one node,\nconductance g_a = c w_a to each cell"]
    for k, ax in enumerate(axs):
        ax.set_xlim(0, 6)
        ax.set_ylim(0, 6)
        ax.set_title(titles[k], fontsize=9)
        xs = [1.0, 2.2, 3.4, 4.6]
        labels = ["copper", "copper", "bare", "bare"]
        for i, x in enumerate(xs):
            ax.add_patch(Circle((x, 4.6), 0.28, facecolor="#e0a458" if labels[i] == "copper" else "#9bbf8a", edgecolor="k"))
            ax.text(x, 5.3, labels[i], ha="center", fontsize=7.5)
        if k < 2:
            ax.add_patch(Circle((2.8, 2.9), 0.28, facecolor="#cfe3f5", edgecolor="k"))
            ax.text(2.8, 2.35, "T_mean", ha="center", fontsize=8)
            for i, x in enumerate(xs):
                wt = [1, 1, 1, 1] if k == 0 else [1.4, 1.4, 0.1, 0.1]
                dk.arrow(ax, x, 4.3, 2.8 + (x - 2.8) * 0.2, 3.2, dk.BLUE, style="-", width=0.6 + 1.2 * wt[i])
            dk.arrow(ax, 2.8, 2.6, 2.8, 1.4, "k", style="-", width=2)
            ax.text(3.1, 2.0, "well G_c", fontsize=8)
            ax.add_patch(Circle((2.8, 1.1), 0.28, facecolor="#c98a3b", edgecolor="k"))
            ax.text(2.8, 0.45, "barrel", ha="center", fontsize=8)
            ax.text(0.2, 0.15, "positive off-diagonal entries inside the footprint" if k == 0 else "weights follow the copper; still positive entries", fontsize=7.5, color=dk.HEAT)
        else:
            ax.add_patch(Circle((2.8, 1.9), 0.28, facecolor="#c98a3b", edgecolor="k"))
            ax.text(2.8, 1.25, "barrel node", ha="center", fontsize=8)
            for i, x in enumerate(xs):
                dk.arrow(ax, x, 4.3, 2.8 + (x - 2.8) * 0.3, 2.2, dk.BLUE, style="-", width=[2.4, 2.4, 0.3, 0.3][i])
            ax.text(0.2, 0.15, "a resistor network: every off-diagonal entry <= 0 (M-matrix)", fontsize=7.5, color="#1b4332")
    dk.save(fig, path)


def fig_cases(path):
    """!
    @brief Plan views of the five families of test cases (copper in orange, via as a circle, heater in red outline).
    @param path Output file.
    @return None.
    """
    fig, axs = dk.canvas(15, 3.4, 1, 5)
    # each tuple: title, copper rectangles (x0,y0,x1,y1) in a 10 x 10 frame, heater rect
    cases = [("edge: copper ends\nthrough the via", [(1, 1, 5, 9)], (3, 4, 5, 6)),
             ("track: 0.4 mm track\nends at the via", [(0.5, 4, 2.5, 6), (2.5, 4.8, 5, 5.2)], (0.5, 4, 2.5, 6)),
             ("island: 1.2 mm pad\naround the via", [(4.4, 4.4, 5.6, 5.6)], (4.4, 4.4, 5.6, 5.6)),
             ("antipad: clearance in the\nbottom plane (shown)", [(0, 0, 10, 4.5), (0, 5.5, 10, 10), (0, 4.5, 4.5, 5.5), (5.5, 4.5, 10, 5.5)], (2, 4, 4, 6)),
             ("bare: heater on bare\nlaminate over half the via", [(0, 0, 5, 10)], (4.5, 4.5, 5.5, 5.5))]
    for ax, (title, cu, hr) in zip(axs, cases):
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.set_aspect("equal")
        ax.add_patch(Rectangle((0, 0), 10, 10, facecolor=dk.FR4, edgecolor="k"))
        for r in cu:
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], facecolor=dk.COPPER, edgecolor="none"))
        ax.add_patch(Rectangle((hr[0], hr[1]), hr[2] - hr[0], hr[3] - hr[1], facecolor="none", edgecolor=dk.HEAT, linewidth=2))
        ax.add_patch(Circle((5, 5), 0.3, facecolor="#7a4b12", edgecolor="k"))
        ax.set_title(title, fontsize=9)
    dk.save(fig, path)


def main():
    """!
    @brief Draw all the diagrams.
    @return None.
    """
    OUT.mkdir(exist_ok=True)
    fig_section(OUT / "fig_01_section_copper_edge.png")
    fig_couplings(OUT / "fig_02_three_couplings.png")
    fig_cases(OUT / "fig_03_test_cases_plan.png")


if __name__ == "__main__":
    main()
