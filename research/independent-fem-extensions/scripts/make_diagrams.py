#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the extension cases (no data, no program): the cross-section with the heat paths of the via cluster under a tab, and the
       hollow barrel against the program's barrel length, the mapping of study 2 onto the program's inputs and the design of the transient reference.
       Run from the repository root; writes figures/fig_01_*.png to fig_04_*.png.
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


def fig_mapping():
    """!
    @brief What each side of study 2 represents: the resolved part of the finite elements (variant B), the same board as the program can take it
           (variant A, also solved by the finite elements), and the program's inputs for it. Not to scale.
    @return None.
    """
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.8))
    titles = ["FEM variant B: the part resolved", "FEM variant A = the program's problem", "program inputs for variant A"]
    for ax, t in zip(axs, titles):
        box(ax, 0, 3.0, 10, 0.4, "#d98c3a", "top copper")
        box(ax, 0, 1.4, 10, 1.6, "#9fd3a8", "laminate")
        box(ax, 0, 1.0, 10, 0.4, "#d98c3a", "bottom copper")
        for x in (3.6, 4.6, 5.4, 6.4):
            box(ax, x - 0.1, 1.0, 0.2, 2.4, "#d98c3a", None)
        ax.set_xlim(-0.2, 10.2)
        ax.set_ylim(-0.9, 5.2)
        ax.axis("off")
        ax.set_title(t, fontsize=8)
    a, b, c = axs
    box(a, 3, 3.8, 4, 0.5, "#d9a35b", "tab + source")
    box(a, 3, 3.4, 4, 0.4, "#b0b0b0", "solder")
    box(a, 0, 0.6, 10, 0.4, "#b0b0b0", "interface slab")
    box(a, 0, -0.4, 10, 1.0, "#cfd8e6", "plate slabs")
    for x in (3.5, 5.0, 6.5):
        arrow(a, (x, 4.3), (x, 3.45))
    box(b, 3, 3.4, 4, 0.3, "#e8a0a0", "uniform source in top copper")
    box(b, 0, 0.6, 10, 0.4, "#b0b0b0", "interface slab")
    box(b, 0, -0.4, 10, 1.0, "#cfd8e6", "plate slabs")
    b.text(5, 4.3, "T_part = T_max(footprint) + P t_s / (k_s A), both sides", ha="center", fontsize=6.5)
    box(c, 3, 3.4, 4, 0.3, "#e8a0a0", "Heater on layer 1")
    c.text(5, 4.1, "role 'source', base_pad_thickness, base_pad_k:\na read-out offset only (no spreading, no capacity)", ha="center", fontsize=6.5)
    box(c, 0, 0.6, 10, 0.4, "#b0b0b0", "pad_thickness / pad_k: R''")
    box(c, 0, -0.4, 10, 1.0, "#cfd8e6", "Heatsink block, layer L: one node layer")
    c.text(5, -0.75, "Via(diameter, fill_k), board via_plating; no input for a tab", ha="center", fontsize=6.5)
    fig.savefig(os.path.join(OUT, "fig_03_program_mapping.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_transient_design():
    """!
    @brief Which transient reference covers which case: the existing references of research/fast-wave-oscillation and the capacity matrix of the
           finite-element tool, and where they are checked against each other.
    @return None.
    """
    fig, ax = plt.subplots(figsize=(9, 3.8))
    box(ax, 0, 3.0, 2.8, 1.0, "#e8eef7", "1D closed forms\nRC exponential, slab series")
    box(ax, 0, 1.5, 2.8, 1.0, "#e8eef7", "axisym_stack (modal)\nfast-wave-oscillation")
    box(ax, 0, 0.0, 2.8, 1.0, "#e8eef7", "review_rect3d (frequency)\nfast-wave-oscillation")
    box(ax, 3.8, 1.5, 2.8, 1.0, "#f6e3c3", "FEM + capacity M\nimplicit steps, K + i w M")
    box(ax, 7.4, 3.0, 2.6, 1.0, "#d8f0dc", "plain and partial copper,\nsquare waves (done there)")
    box(ax, 7.4, 1.5, 2.6, 1.0, "#d8f0dc", "disc board: FEM against\naxisym (cross-check)")
    box(ax, 7.4, 0.0, 2.6, 1.0, "#d8f0dc", "plate + cluster, conforming\nvias: FEM only")
    arrow(ax, (2.8, 3.5), (3.9, 2.4), "#555555")
    arrow(ax, (2.8, 2.0), (3.8, 2.0), "#555555")
    arrow(ax, (2.8, 2.0), (7.4, 3.4), "#555555")
    arrow(ax, (2.8, 0.5), (7.4, 3.2), "#555555")
    arrow(ax, (6.6, 2.0), (7.4, 2.0), "#555555")
    arrow(ax, (6.6, 1.8), (7.4, 0.5), "#555555")
    ax.set_xlim(-0.2, 10.2)
    ax.set_ylim(-0.3, 4.3)
    ax.axis("off")
    ax.set_title("Study 5: the transient reference (left: references; right: what each one checks)", fontsize=9)
    fig.savefig(os.path.join(OUT, "fig_04_transient_design.png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    fig_cluster()
    fig_barrel()
    fig_mapping()
    fig_transient_design()
