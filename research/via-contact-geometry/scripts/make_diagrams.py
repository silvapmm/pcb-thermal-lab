#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Drawings of the situation (no data, no program): the real section of a via through the copper layers with the heat paths and the length rule, and the plan views of the copper cases.
@details Writes figures/fig_01_barrel_section.png and figures/fig_02_contact_plans.png. Run from the repository root: `.venv/bin/python research/via-contact-geometry/scripts/make_diagrams.py`.
"""

import sys

import _bootstrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

CU, FR4, AIR = "#c9803a", "#cfd8c0", "#ffffff"


def section(ax):
    """!
    @brief Section through a via in a four-layer board: copper nodes, gaps, the barrel, and the length rule.
    @param ax Matplotlib axes.
    @return None.
    """
    t, d, w, r = 0.35, 1.3, 9.0, 0.45               # drawn copper thickness, gap, width, barrel half-width (not to scale)
    ys = [0.0]
    for _ in range(3):
        ys.append(ys[-1] - (t + d))
    for k, y in enumerate(ys):
        ax.add_patch(Rectangle((-w / 2, y - t), w, t, fc=CU, ec="k", lw=0.6))
        ax.text(-w / 2 - 0.2, y - t / 2, f"layer {k + 1}", ha="right", va="center", fontsize=8)
        if k < 3:
            ax.add_patch(Rectangle((-w / 2, y - t - d), w, d, fc=FR4, ec="k", lw=0.6))
    top, bot = ys[0], ys[-1] - t
    ax.add_patch(Rectangle((-r, bot), 2 * r, top - bot, fc="#e8e8e8", ec="none", zorder=2))
    for sgn in (-1, 1):
        ax.add_patch(Rectangle((sgn * r - 0.07 if sgn < 0 else r - 0.07, bot), 0.14, top - bot, fc=CU, ec="k", lw=0.5, zorder=3))
    ax.text(0, top + 0.35, "plated barrel (air in the hole)", ha="center", fontsize=8)
    # heat paths: spreading in the plane, down the barrel, into the next plane
    for k, y in enumerate(ys):
        yc = y - t / 2
        ax.annotate("", xy=(r + 0.15, yc), xytext=(3.2, yc), arrowprops=dict(arrowstyle="->", color="crimson", lw=1.2), zorder=5)
    for k in range(3):
        ax.annotate("", xy=(0.0, ys[k + 1] - t / 2), xytext=(0.0, ys[k] - t / 2), arrowprops=dict(arrowstyle="->", color="navy", lw=1.2), zorder=5)
    # the length rule on the first gap
    y0, y1 = ys[0] - t / 2, ys[1] - t / 2
    ax.annotate("", xy=(w / 2 - 0.5, ys[0] - t), xytext=(w / 2 - 0.5, ys[1]), arrowprops=dict(arrowstyle="<->", lw=1))
    ax.text(w / 2 - 0.35, (ys[0] - t + ys[1]) / 2, "d (the program)", fontsize=8, va="center")
    ax.annotate("", xy=(w / 2 + 2.6, y0), xytext=(w / 2 + 2.6, y1), arrowprops=dict(arrowstyle="<->", lw=1))
    ax.text(w / 2 + 2.75, (y0 + y1) / 2, "d + t_cu\n(node to node)", fontsize=8, va="center")
    ax.text(w / 2 + 2.75, y1 - 1.0, "measured:\nd + 0.5 t_cu", fontsize=8, color="darkgreen", va="center")
    ax.text(-w / 2, bot - 0.8, "red: heat spreading in a copper layer to the barrel; blue: heat down the barrel.\nA copper layer is one node at its mid-plane; the program counts the barrel over d only.",
            fontsize=8)
    ax.set_xlim(-w / 2 - 2.2, w / 2 + 6.2)
    ax.set_ylim(bot - 1.6, top + 1.0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Section through a via: where the barrel length is counted", fontsize=10)


def plans(axs):
    """!
    @brief Plan views of the copper cases of the reference set: the drill rim, the copper, the footprint cells.
    @param axs Sequence of four Matplotlib axes.
    @return None.
    """
    cases = [
        ("copper edge through the via", [(-1.6, -1.6), (0, -1.6), (0, 1.6), (-1.6, 1.6)], "rim share f about 0.5"),
        ("corner of a copper quadrant", [(-1.6, -1.6), (0, -1.6), (0, 0), (-1.6, 0)], "f = 0.25"),
        ("track ending on the via", [(-1.6, -0.12), (0, -0.12), (0, 0.12), (-1.6, 0.12)], "f about 0.3"),
        ("via outside a copper edge", [(-1.6, -1.6), (-0.3, -1.6), (-0.3, 1.6), (-1.6, 1.6)], "f = 0 (no contact)"),
    ]
    for ax, (title, poly, note) in zip(axs, cases):
        ax.add_patch(Rectangle((-1.6, -1.6), 3.2, 3.2, fc=FR4, ec="k", lw=0.6))
        ax.add_patch(Polygon(poly, fc=CU, ec="k", lw=0.6, alpha=0.9))
        for i in range(-3, 3):
            for j in range(-3, 3):
                ax.add_patch(Rectangle((i * 0.5, j * 0.5), 0.5, 0.5, fc="none", ec="#555", lw=0.3))
        ax.add_patch(Rectangle((-0.5, -0.5), 1.0, 1.0, fc="none", ec="blue", lw=1.4, ls="--"))
        ax.add_patch(Circle((0, 0), 0.15, fc="white", ec="k", lw=1.2, zorder=5))
        ax.set_xlim(-1.6, 1.6)
        ax.set_ylim(-1.6, 1.6)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(title, fontsize=8)
        ax.text(0, -1.9, note, ha="center", fontsize=8)


def main():
    """!
    @brief Draw both figures.
    @return None.
    """
    _bootstrap.FIGURES.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 4.6))
    section(ax)
    fig.savefig(_bootstrap.FIGURES / "fig_01_barrel_section.png", dpi=130, bbox_inches="tight")
    fig, axs = plt.subplots(1, 4, figsize=(12, 3.6))
    plans(axs)
    fig.suptitle("Plan views (not to scale): copper (orange), the grid (grey), the footprint of cells (blue dashed), the drill (white circle)", fontsize=9)
    fig.savefig(_bootstrap.FIGURES / "fig_02_contact_plans.png", dpi=130, bbox_inches="tight")


if __name__ == "__main__":
    sys.exit(main())
