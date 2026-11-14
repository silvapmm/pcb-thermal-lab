#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the extension cases (no data, no program): the cross-section with the heat paths of the via cluster under a tab, and the
       hollow barrel against the program's barrel length. Run from the repository root; writes figures/fig_01_*.png and fig_02_*.png.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                     # noqa: E402
from matplotlib.patches import Rectangle, FancyArrowPatch            # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")


def box(ax, x, y, w, h, fc, label=None, ec="k"):
    """!
    @brief Draw a labelled rectangle.
    @param ax Axes.
    @param x Left.
    @param y Bottom.
    @param w Width.
    @param h Height.
    @param fc Face colour.
    @param label Text or None.
    @param ec Edge colour.
    @return None.
    """
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=0.6))
    if label:
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=7)


def arrow(ax, p, q, c="#c0392b"):
    """!
    @brief Draw a heat-path arrow.
    @param ax Axes.
    @param p Start (x, y).
    @param q End (x, y).
    @param c Colour.
    @return None.
    """
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=9, color=c, lw=1.3))


def fig_cluster():
    """!
    @brief Cross-section of case 2: part, tab, solder, top copper, laminate, via barrels, bottom copper, plate. Not to scale.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(8, 4.2))
    box(ax, 3, 6.4, 4, 0.5, "#e8a0a0", "heat source on the tab (surface or volume)")
    box(ax, 3, 5.8, 4, 0.6, "#d9a35b", "copper tab (block)")
    box(ax, 3, 5.4, 4, 0.4, "#b0b0b0", "solder layer")
    box(ax, 0, 5.0, 10, 0.4, "#d98c3a", "top copper (sheet)")
    box(ax, 0, 3.0, 10, 2.0, "#9fd3a8", "laminate (k_xy 0.9, k_z 0.3)")
    box(ax, 0, 2.6, 10, 0.4, "#d98c3a", "bottom copper")
    box(ax, 0, 2.2, 10, 0.4, "#b0b0b0", "interface")
    box(ax, 0, 1.0, 10, 1.2, "#cfd8e6", "plate underneath (aluminium)")
    for x in (3.6, 4.6, 5.4, 6.4):
        box(ax, x - 0.12, 2.6, 0.24, 2.8, "#d98c3a", None)
        box(ax, x - 0.05, 2.6, 0.10, 2.8, "white", None, ec="none")        # hollow barrel: copper wall, resin core
    for x in (3.5, 5.0, 6.5):
        arrow(ax, (x, 6.3), (x, 5.6))
    arrow(ax, (7.2, 5.3), (9.4, 5.2))
    for x in (3.6, 6.4):
        arrow(ax, (x + 0.3, 4.9), (x + 0.3, 3.0))
    arrow(ax, (5.0, 2.3), (5.0, 1.0))
    ax.text(9.5, 5.5, "spreading", fontsize=7, ha="right")
    ax.text(5.0, 0.6, "film h to ambient on the free faces and walls", ha="center", fontsize=7)
    ax.set_xlim(-0.2, 10.2)
    ax.set_ylim(0.3, 7.2)
    ax.axis("off")
    ax.set_title("Case 2: part on a tab over a via cluster (cross-section, not to scale; arrows = heat paths)", fontsize=9)
    fig.savefig(os.path.join(OUT, "fig_01_cluster_cross_section.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_barrel():
    """!
    @brief Plan and section of a hollow barrel: copper wall, resin core, the rim, and the two lengths compared (d + 0.5 t_cu against the real wall).
    @return None.
    """
    fig, (a, b) = plt.subplots(1, 2, figsize=(8, 3.6))
    a.add_patch(plt.Circle((0, 0), 0.30, fc="#d98c3a", ec="k"))
    a.add_patch(plt.Circle((0, 0), 0.27, fc="#f3e6c8", ec="k", lw=0.5))
    a.text(0, 0, "resin\nk_fill", ha="center", va="center", fontsize=7)
    a.annotate("wall 25 um", (0.29, 0.05), (0.5, 0.35), fontsize=7, arrowprops=dict(arrowstyle="-"))
    a.set_aspect("equal")
    a.set_xlim(-0.6, 0.9)
    a.set_ylim(-0.6, 0.6)
    a.axis("off")
    a.set_title("plan: hollow plated barrel", fontsize=8)
    box(b, 0, 0, 3, 0.35, "#d98c3a", "layer 1 copper")
    box(b, 0, 1.6, 3, 0.35, "#d98c3a", "layer 2 copper")
    box(b, 0, 0.35, 3, 1.25, "#9fd3a8", "gap d")
    box(b, 1.4, 0, 0.15, 1.95, "#d98c3a", None)
    b.annotate("", (3.3, 0.18), (3.3, 1.78), arrowprops=dict(arrowstyle="<->"))
    b.text(3.35, 0.95, "program:\nd + 0.5 t_cu", fontsize=7, va="center")
    b.set_xlim(-0.2, 4.4)
    b.set_ylim(-0.2, 2.2)
    b.axis("off")
    b.set_title("section: the barrel length of the program", fontsize=8)
    fig.savefig(os.path.join(OUT, "fig_02_hollow_barrel.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig_cluster()
    fig_barrel()
