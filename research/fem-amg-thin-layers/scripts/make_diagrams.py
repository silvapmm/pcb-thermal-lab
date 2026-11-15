#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawing of the question (no data, no program): a section through the stack of the FEM mesh with the thin copper and gap slabs, the strong (through-thickness) and weak (in-plane) couplings,
       and the two coarsening choices (aggregates ignoring the anisotropy against semi-coarsening along the plane / line relaxation through the thickness).
@details Writes figures/fig_01_thin_layer_coarsening.png. Illustrative sketch, not to scale: the element aspect ratio drawn (about 1:6) is far milder than the real one (35 um copper under a 1 mm cell is about 1:30).
         Run (repository root): .venv/bin/python research/fem-amg-thin-layers/scripts/make_diagrams.py
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
from matplotlib.patches import Rectangle                            # noqa: E402

FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def fig_01():
    """!
    @brief Two sections of a stack of thin slabs: the aggregates of an anisotropy-blind coarsening (squares) and of the aggregation the thin layers need (columns, then plan blocks).
    @return None.
    """
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6))
    nx, nz = 12, 6
    dz = [0.35, 0.35, 1.2, 0.35, 0.35, 1.2]                         # copper, copper, gap, ... (sketch)
    for ax, title in zip(axes, ("(a) aggregates of 3 x 3 nodes: blind to the thin layers", "(b) columns first (line relaxation through the thickness), then in-plane blocks")):
        z = 0.0
        for k in range(nz):
            for i in range(nx):
                ax.add_patch(Rectangle((i, z), 1, dz[k], fc="#d8a15f" if dz[k] < 0.5 else "#9fc5a0", ec="#555555", lw=0.4))
            z += dz[k]
        ax.set_xlim(-0.3, nx + 0.3)
        ax.set_ylim(-0.3, z + 0.3)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=8)
        axes_z = z
    for i in range(0, nx, 3):                                       # (a) square aggregates
        axes[0].add_patch(Rectangle((i, 0), 3, 3.0, fc="none", ec="#c0392b", lw=1.6))
    for i in range(nx):                                             # (b) one column per plan node, then blocks of 4 columns
        axes[1].add_patch(Rectangle((i + 0.05, 0.02), 0.9, axes_z - 0.04, fc="none", ec="#1f4e79", lw=0.8))
    for i in range(0, nx, 4):
        axes[1].add_patch(Rectangle((i, -0.2), 4, axes_z + 0.4, fc="none", ec="#c0392b", lw=1.6, ls="--"))
    fig.text(0.5, -0.04, "strong coupling: through the thin slab (large conductance k A / dz); weak coupling: in plane (k dz / dx). Sketch, not to scale.", fontsize=8, ha="center")
    os.makedirs(os.path.join(FOLDER, "figures"), exist_ok=True)
    fig.savefig(os.path.join(FOLDER, "figures", "fig_01_thin_layer_coarsening.png"), dpi=140, bbox_inches="tight")


def fig_02():
    """!
    @brief Flow chart of the two column-solve preconditioners measured in README section 7.4: 'colblock' (exact solve of every vertical column) and 'colblock_amg' (that plus the program's V cycle, added).
    @return None.
    """
    fig, ax = plt.subplots(figsize=(10, 3.4))
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.4)

    def box(x, y, w, h, text, fc):
        ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec="#333333", lw=1.0))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8)

    def arrow(x0, y0, x1, y1):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="->", lw=1.2))

    box(0.1, 1.3, 1.4, 0.8, "residual r\n(CG step)", "#eeeeee")
    box(3.0, 2.2, 2.6, 0.8, "colblock: solve K_col z1 = r\n(K_col = couplings inside each\nvertical column, sparse LU once)", "#cfe3f5")
    box(3.0, 0.3, 2.6, 0.8, "program default: one V cycle z2\n(smoothed aggregation, theta 0)", "#f5dcb5")
    box(6.6, 1.3, 1.5, 0.8, "z = z1 + z2\n(sum of two SPD\noperators: SPD)", "#d6ecd0")
    box(8.5, 1.3, 1.3, 0.8, "CG update", "#eeeeee")
    arrow(1.5, 1.7, 3.0, 2.6)
    arrow(1.5, 1.7, 3.0, 0.7)
    arrow(5.6, 2.6, 6.6, 1.9)
    arrow(5.6, 0.7, 6.6, 1.5)
    arrow(8.1, 1.7, 8.5, 1.7)
    ax.text(4.3, 1.55, "'colblock' uses only the upper path;\n'colblock_amg' uses both", fontsize=7.5, ha="center")
    ax.set_title("Fig. 2: the two column-solve preconditioners (flow chart, no data)", fontsize=9)
    fig.savefig(os.path.join(FOLDER, "figures", "fig_02_column_preconditioner.png"), dpi=140, bbox_inches="tight")


if __name__ == "__main__":
    fig_01()
    fig_02()
