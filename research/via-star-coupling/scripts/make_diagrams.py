#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Draws the picture of the star coupling of a via (no data, no program): the footprint at the end of a copper edge and the section with the barrel nodes.
@details Writes `research/via-star-coupling/figures/fig_01_star_coupling.png`. The numbers quoted in the panel titles are those of docs/validation.md 31.1 and 31.2 (board of
         docs/theory.md 2.2, FVM at 0.25 mm). Run from the repository root: `.venv/bin/python research/via-star-coupling/scripts/make_diagrams.py [--copy-to-docs]`
         (the option also writes `docs/images/via_star_coupling.png`).
"""

import os
import shutil
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                              # noqa: E402
from matplotlib.patches import Circle, Rectangle                              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(FOLDER))


def plan(ax):
    """!
    @brief Plan view: a 5 x 4 patch of cells, copper on the left three columns, the via disc on the copper edge, the weights of the footprint cells.
    @param ax Matplotlib axes.
    @return None.
    """
    copper, bare = "#c9a24a", "#e9e4d6"
    for i in range(4):
        for j in range(5):
            on = j < 3
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=copper if on else bare, edgecolor="#555555", linewidth=0.8))
    cx, cy = 3.0, 2.0
    ax.add_patch(Circle((cx, cy), 0.35, facecolor="none", edgecolor="#1f3a5f", linewidth=2.0))
    ax.plot([cx], [cy], "o", color="#1f3a5f", markersize=4)
    # Weights by sheet conductance: the copper cells next to the via take almost all of it
    for (j, i, txt) in ((2, 1, "0.49"), (2, 2, "0.49"), (3, 1, "0.01"), (3, 2, "0.01")):
        ax.text(j + 0.5, i + 0.5, txt, ha="center", va="center", fontsize=10)
    ax.set_xlim(0, 5)
    ax.set_ylim(0, 4)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Plan: weights of the footprint of one layer\n(sheet conductance times the disc share; copper ends at the via)", fontsize=10)


def section(ax):
    """!
    @brief Section: a barrel node per layer, a conductance from every footprint cell to it (line width ~ g_a), the barrel between the layers.
    @param ax Matplotlib axes.
    @return None.
    """
    xs = [0.8, 1.6, 2.4, 3.2]
    widths = [3.0, 3.0, 0.4, 0.4]                      # g_a of the top layer: two copper cells, two bare cells
    for k, (y0, name) in enumerate(((3.6, "top layer: copper ends at the via"), (0.6, "bottom layer: whole plane"))):
        for j, x in enumerate(xs):
            on = (j < 2) if k == 0 else True
            ax.add_patch(Rectangle((x - 0.35, y0), 0.7, 0.35, facecolor="#c9a24a" if on else "#e9e4d6", edgecolor="#555555"))
        bx = 2.0
        ax.plot([bx], [y0 - 0.9], "s", color="#1f3a5f", markersize=9)
        for j, x in enumerate(xs):
            lw = widths[j] if k == 0 else 1.6
            ax.plot([x, bx], [y0, y0 - 0.9], color="#1f3a5f", linewidth=lw, alpha=0.75, solid_capstyle="butt")
        ax.text(0.0, y0 + 0.55, name, fontsize=10)
    ax.plot([2.0, 2.0], [2.7, 1.5], color="#1f3a5f", linewidth=4)
    ax.text(2.15, 2.1, "barrel", fontsize=10)
    ax.text(4.15, 3.0, "g_a = c S w_a", fontsize=10)
    ax.text(0.0, -0.95, "barrel nodes eliminated: off-diagonal entries of K all negative", fontsize=10)
    ax.set_xlim(-0.1, 5.2)
    ax.set_ylim(-1.2, 4.6)
    ax.axis("off")
    ax.set_title("Section: a barrel node per layer, a star of conductances\n(documented board, 0.25 mm: cold spot -14.4 K -> none, via effect 7.7 -> 12.6 K)", fontsize=10)


def main():
    """!
    @brief Draw and save the figure.
    @return None.
    """
    fig, (a, b) = plt.subplots(1, 2, figsize=(12.0, 4.6))
    plan(a)
    section(b)
    os.makedirs(os.path.join(FOLDER, "figures"), exist_ok=True)
    path = os.path.join(FOLDER, "figures", "fig_01_star_coupling.png")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    print(path)
    if "--copy-to-docs" in sys.argv:
        dest = os.path.join(REPO, "docs", "images", "via_star_coupling.png")
        shutil.copyfile(path, dest)
        print(dest)


if __name__ == "__main__":
    main()
