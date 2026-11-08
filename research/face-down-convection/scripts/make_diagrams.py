#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the thing itself for the face-down study: the section of a hot horizontal board with the air paths under it, and what the characteristic length is.
@details No data, no program. Writes figures/fig_01_air_under_a_hot_board.png. Usage: .venv/bin/python research/face-down-convection/scripts/make_diagrams.py
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle  # noqa: E402

FIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")


def arrow(ax, p, q, color="tab:blue", rad=0.0, lw=1.6):
    """!
    @brief Draw one arrow of the air path.
    @param ax Axes.
    @param p Start (x, y).
    @param q End (x, y).
    @param color Colour.
    @param rad Curvature.
    @param lw Line width.
    @return None.
    """
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=12, color=color, lw=lw, connectionstyle=f"arc3,rad={rad}"))


def main():
    """!
    @brief Draw figure 1.
    @return None.
    """
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.35, 1]})
    ax = axs[0]
    ax.add_patch(Rectangle((-5, 0), 10, 0.25, color="#b87333"))            # the board (copper side drawn as one slab)
    ax.text(0, 0.45, "hot board, face up above, face down below", ha="center", fontsize=9)
    # Stable layer under the board: air meets the face, flows out to the edges, then goes round and up
    for x in (-3.5, -1.5, 0.0, 1.5, 3.5):
        arrow(ax, (x, -2.2), (x, -0.15), "tab:blue", 0.0)
    arrow(ax, (-0.3, -0.1), (-4.6, -0.55), "tab:red", -0.15)
    arrow(ax, (0.3, -0.1), (4.6, -0.55), "tab:red", 0.15)
    arrow(ax, (-4.8, -0.6), (-6.2, 0.8), "tab:red", -0.3)
    arrow(ax, (4.8, -0.6), (6.2, 0.8), "tab:red", 0.3)
    ax.text(0, -2.45, "cold air drawn up to the face (stagnation at the centre)", ha="center", fontsize=8, color="tab:blue")
    ax.text(-5.0, -1.5, "thin hot layer\nflows out to the edges", fontsize=8, color="tab:red", ha="center")
    ax.annotate("layer thickens toward the edge:\nh falls from the centre outward", xy=(3.0, -0.35), xytext=(1.8, -1.4), fontsize=8, arrowprops={"arrowstyle": "-", "color": "k"})
    ax.set_xlim(-7, 7)
    ax.set_ylim(-2.9, 1.5)
    ax.axis("off")
    ax.set_title("Section: the face turned down is a stable layer (flow starts at the centre)", fontsize=10)
    ax2 = axs[1]
    ax2.add_patch(Rectangle((0, 0), 6, 4, fill=False, lw=2))
    ax2.annotate("", xy=(0, -0.5), xytext=(6, -0.5), arrowprops={"arrowstyle": "<->"})
    ax2.text(3, -0.9, "a = 100 mm", ha="center", fontsize=8)
    ax2.annotate("", xy=(6.5, 0), xytext=(6.5, 4), arrowprops={"arrowstyle": "<->"})
    ax2.text(6.9, 2, "b = 80 mm", rotation=90, va="center", fontsize=8)
    ax2.text(3, 2, "L = A/P = a b / (2 (a + b))\n= 22.2 mm", ha="center", va="center", fontsize=10)
    ax2.text(3, -2.0, "Ra = g beta dT L^3 / (nu alpha),  Nu = h L / k\nprogram: Nu = 0.27 Ra^(1/4)   candidates: Nu = C Ra^(1/5)", ha="center", fontsize=8)
    ax2.set_xlim(-1, 8)
    ax2.set_ylim(-2.8, 4.6)
    ax2.axis("off")
    ax2.set_title("The characteristic length (the same board, seen from below)", fontsize=10)
    fig.tight_layout()
    os.makedirs(FIG, exist_ok=True)
    fig.savefig(os.path.join(FIG, "fig_01_air_under_a_hot_board.png"), dpi=130)


if __name__ == "__main__":
    main()
