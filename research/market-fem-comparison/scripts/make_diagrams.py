#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of research/market-fem-comparison: the comparison workflow (one case description, several solvers, the same read-out points) and the section of the via-cluster case with the read-out points.
@details No data and no program. Writes figures/fig_01_workflow.png and figures/fig_02_case_section.png. Run (repository root): .venv/bin/python research/market-fem-comparison/scripts/make_diagrams.py
"""

import os
import sys

import matplotlib

matplotlib.use("Agg")
from matplotlib.patches import Circle, Rectangle          # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FOLDER, ".."))
import diagram_kit as K                                    # noqa: E402

FIG = os.path.join(FOLDER, "figures")


def fig_01():
    """!
    @brief The workflow: one JSON case description feeds the program's models and the external solvers; every solver writes the same read-out points to one table.
    @return None.
    """
    fig, ax = K.canvas(11, 5.2)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 5.2)
    K.box(ax, 0.2, 2.2, 2.0, 1.0, "case.json\n(geometry, layers,\nvias, h, power)", "#fdebd0", bold=True)
    names = [("pcbthermal\n5 models", "#cfe3f5", 4.2), ("scikit-fem\n(Q1 bricks, ours)", "#d5f5e3", 3.4),
             ("Gmsh + Elmer / CalculiX\n(P2 tetrahedra)", "#e8daef", 2.6), ("FEniCSx / MFEM\n(P1/P2, Python)", "#e8daef", 1.8),
             ("OpenFOAM chtMultiRegion\n(finite volumes)", "#fadbd8", 1.0)]
    for text, col, y in names:
        K.box(ax, 4.2, y - 0.3, 3.0, 0.7, text, col, size=7)
        K.arrow(ax, 2.2, 2.7, 4.2, y + 0.05)
        K.arrow(ax, 7.2, y + 0.05, 8.4, 2.7)
    K.box(ax, 8.4, 2.1, 2.4, 1.2, "read-out table\nT at the part, at the via,\nT_min, edge heat, balance", "#fcf3cf", bold=True)
    ax.text(0.2, 4.6, "Adapters (one per solver) read case.json; none edits the program.", fontsize=8)
    ax.text(4.2, 0.2, "Dashed idea: commercial tools only by hand, numbers kept private unless the licence allows publishing.", fontsize=7, style="italic")
    K.save(fig, os.path.join(FIG, "fig_01_workflow.png"), "Comparison workflow: same case, several solvers, same read-out points")


def fig_02():
    """!
    @brief Section of the via-cluster case with the plate: board layers, the barrels, the part, the plate and the read-out points A (part centre), B (barrel foot), C (board edge).
    @return None.
    """
    fig, ax = K.canvas(9, 4.2)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    for i, y in enumerate([3.0, 2.4, 1.8, 1.2]):
        K.layer(ax, 0.5, y, 9, 0.12, K.COPPER, "")
    ax.add_patch(Rectangle((0.5, 1.2), 9, 1.92, fc="#e8e0c8", ec="k", alpha=0.35))
    for x in (4.2, 4.8, 5.4):
        ax.add_patch(Rectangle((x - 0.08, 1.2), 0.16, 1.92, fc=K.COPPER, ec="k"))
    ax.add_patch(Rectangle((3.8, 3.12), 2.0, 0.45, fc=K.HEAT, ec="k"))
    ax.text(4.8, 3.3, "part", ha="center", fontsize=8)
    ax.add_patch(Rectangle((3.5, 0.5), 2.6, 0.6, fc="#bdc3c7", ec="k"))
    ax.text(4.8, 0.72, "plate", ha="center", fontsize=8)
    for (x, y, t) in [(4.8, 3.6, "A"), (4.8, 1.15, "B"), (9.5, 2.6, "C")]:
        ax.add_patch(Circle((x, y), 0.1, fc="r"))
        ax.text(x + 0.15, y + 0.12, t, color="r", fontsize=9)
    K.arrow(ax, 4.8, 3.7, 4.8, 4.5, label="film h_top")
    ax.text(0.6, 4.5, "A part centre   B barrel foot   C board edge: the same three points in every solver", fontsize=8)
    K.save(fig, os.path.join(FIG, "fig_02_case_section.png"), "Via cluster under a part, with a plate (section, not to scale)")


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    fig_01()
    fig_02()
