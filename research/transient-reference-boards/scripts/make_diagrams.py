#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Figure 1 (the five boards: plan views and the stack) and figure 2 (the comparison chain). No data and no program needed. Run from the repository root:
       `.venv/bin/python research/transient-reference-boards/scripts/make_diagrams.py`.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                          # noqa: E402
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle         # noqa: E402

FIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")


def boards():
    """!
    @brief Figure 1: the five boards drawn to their own scale, with the part, the vias, the plate and the quarter domain of the finite-element model.
    @return None.
    """
    fig, ax = plt.subplots(1, 6, figsize=(17, 3.6), gridspec_kw={"width_ratios": [1.5, 1, 1, 1.3, 1, 1.3]})
    cu, fr = "#c98f3a", "#9bb58a"
    a = ax[0]
    a.add_patch(Rectangle((0, 0), 100, 80, fc=fr, ec="k"))
    a.add_patch(Rectangle((47, 37), 6, 6, fc="r", ec="k"))
    a.add_patch(Rectangle((50, 40), 50, 40, fc="none", ec="b", ls="--"))
    a.set_xlim(-5, 105); a.set_ylim(-5, 85); a.set_aspect("equal"); a.set_title("simple4: 100 x 80 mm, 4 layers\n6 x 6 mm part, copper on all layers", fontsize=8)
    for k, title in ((1, "vias: 20 x 20 mm, 4 layers\n6 x 6 part, 4 x 4 vias"), (2, "plate: vias + 1 mm Al plate\n(FVM and FDM only)")):
        a = ax[k]
        a.add_patch(Rectangle((0, 0), 20, 20, fc=fr, ec="k"))
        a.add_patch(Rectangle((7, 7), 6, 6, fc="r", ec="k"))
        for x in (8.8, 9.6, 10.4, 11.2):
            for y in (8.8, 9.6, 10.4, 11.2):
                a.add_patch(Circle((x, y), 0.15, fc="k"))
        if k == 2:
            a.add_patch(Rectangle((-1, -1), 22, 22, fc="none", ec="gray", lw=3))
        a.add_patch(Rectangle((10, 10), 10, 10, fc="none", ec="b", ls="--"))
        a.set_xlim(-2, 22); a.set_ylim(-2, 22); a.set_aspect("equal"); a.set_title(title, fontsize=8)
    a = ax[3]
    a.add_patch(Rectangle((0, 0), 60, 40, fc=fr, ec="k"))
    a.add_patch(Rectangle((25, 15), 10, 10, fc="r", ec="k"))
    a.add_patch(Rectangle((30, 20), 30, 20, fc="none", ec="b", ls="--"))
    a.set_xlim(-3, 63); a.set_ylim(-3, 43); a.set_aspect("equal"); a.set_title("two2: 60 x 40 mm, 2 layers\n10 x 10 mm part, insulated edges", fontsize=8)
    a = ax[4]
    a.add_patch(Circle((0, 0), 10, fc=fr, ec="k"))
    a.add_patch(Rectangle((-2, -2), 4, 4, fc="r", ec="k"))
    a.set_xlim(-11, 11); a.set_ylim(-11, 11); a.set_aspect("equal"); a.set_title("disc: radius 10 mm, 2 layers\n4 x 4 mm part (outline board)", fontsize=8)
    a = ax[5]
    z = 0
    for i, (kind, t) in enumerate([("cu", .035), ("gap", .5), ("cu", .035), ("gap", .5), ("cu", .035), ("gap", .5), ("cu", .035)]):
        a.add_patch(Rectangle((0, -z - t), 4, t, fc=cu if kind == "cu" else fr, ec="k", lw=.5))
        z += t
    a.add_patch(Rectangle((1, 0), 2, 0.12, fc="r"))
    a.annotate("part (volume source\nin the top copper)", (3, .05), (4.3, .4), fontsize=7, arrowprops=dict(arrowstyle="-"))
    a.text(0, -1.9, "h on both faces and walls\n(copper 35 um, laminate k 0.9 / 0.3)", fontsize=7)
    a.set_xlim(-0.5, 8); a.set_ylim(-2.3, 0.8); a.set_title("stack of the four-layer boards\n(simple stack-up, equal gaps)", fontsize=8)
    for x in ax:
        x.tick_params(labelsize=6)
    ax[5].axis("off")
    fig.text(0.01, 0.01, "dashed blue: the quarter domain of the finite-element model (symmetry planes); red: the part", fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_01_boards.png"), dpi=130)


def chain():
    """!
    @brief Figure 2: the comparison chain, from the board definition to the table.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(12, 3.6))
    ax.axis("off")
    boxes = [(0.02, .55, "Board definition\n(5 boards, 1 W part)"), (0.27, .8, "Program Problem\nFVM, FDM, Lumped, Analytic\nstep_responses (2, 1, 0.5 mm)"),
             (0.27, .3, "FEM model (independent)\nQ1 bricks, 3 mesh levels\ncapacity, Crank-Nicolson + Rannacher"), (0.58, .8, "Z(t) hottest cell / node"),
             (0.58, .3, "Z(t) hottest footprint node\nand footprint mean"), (0.82, .55, "same post-processing:\nt63, early Z(t),\nplateau, wave peak and swing\n(profiles.wave_response)")]
    for x, y, t in boxes:
        ax.add_patch(FancyBboxPatch((x, y - .12), .19, .24, boxstyle="round,pad=0.01", fc="#eef3fa", ec="k"))
        ax.text(x + .095, y, t, ha="center", va="center", fontsize=7.5)
    for (x0, y0, x1, y1) in [(.21, .55, .27, .8), (.21, .55, .27, .3), (.46, .8, .58, .8), (.46, .3, .58, .3), (.77, .8, .82, .6), (.77, .3, .82, .5)]:
        ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="->"))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    fig.savefig(os.path.join(FIG, "fig_02_chain.png"), dpi=130)


if __name__ == "__main__":
    boards()
    chain()
