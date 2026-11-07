#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Diagram of the situation: the real section under a part with the heat path of a fast and of a slow wave, and what one node per copper layer holds (figure 1).

@details No data, no program. Run from the repository root: `.venv/bin/python research/fast-wave-oscillation/scripts/make_diagrams.py`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
import numpy as np                                                   # noqa: E402
from matplotlib.patches import Rectangle, FancyArrowPatch            # noqa: E402

from diagram_kit import COPPER, FR4, HEAT, BLUE, canvas              # noqa: E402

FIG = os.path.join(HERE, "..", "figures")


def section(ax, title, depth_mm, note):
    """!
    @brief One panel: the section (copper, laminate, copper) under a part with the layer of laminate that follows a wave heated to depth_mm.
    @param ax Axes.
    @param title Panel title.
    @param depth_mm Depth reached by the wave in the laminate in mm (drawn to scale of the 1.53 mm gap; the copper is drawn thicker than its 35 um).
    @param note Text under the section.
    @return None.
    """
    ax.set_xlim(0, 10); ax.set_ylim(-4.6, 3.2); ax.axis("off")
    ax.set_title(title, fontsize=10)
    ax.add_patch(Rectangle((3, 1.0), 4, 0.5, color="#555555"))                           # The part
    ax.text(5, 1.75, "part (10 mm)", ha="center", fontsize=8)
    ax.add_patch(Rectangle((0.5, 0.5), 9, 0.25, color=COPPER))                           # Top copper (not to scale)
    ax.add_patch(Rectangle((0.5, -3.0), 9, 3.5, color=FR4, alpha=0.55))                  # Laminate, 1.53 mm drawn as 3.5
    ax.add_patch(Rectangle((0.5, -3.25), 9, 0.25, color=COPPER))                         # Bottom copper
    d = depth_mm / 1.53 * 3.5
    ax.add_patch(Rectangle((2.2, 0.5 - d), 5.6, d, color=HEAT, alpha=0.30))              # Laminate that follows the wave
    for x in (3.6, 5.0, 6.4):
        ax.add_patch(FancyArrowPatch((x, 1.0), (x, 0.55), arrowstyle="-|>", color=HEAT, mutation_scale=9))
    ax.text(9.6, 0.62, "35 um copper", ha="right", fontsize=7, va="bottom")
    ax.text(9.6, -1.4, "FR-4, 1.53 mm", ha="right", fontsize=7)
    ax.text(5, -4.4, note, ha="center", fontsize=8)


def main():
    """!
    @brief Draw figure 1.
    @return None.
    """
    os.makedirs(FIG, exist_ok=True)
    fig, axes = canvas(11.0, 4.6, nrows=1, ncols=3)
    section(axes[0], "Real: 20 Hz wave", 0.06, "heat enters the copper and 0.06 mm of laminate\n(1/12 of the capacity of the node)")
    section(axes[1], "Real: 0.05 Hz wave (20 s)", 1.2, "heat has crossed most of the gap:\nthe node is a fair model")
    ax = axes[2]
    ax.set_xlim(0, 10); ax.set_ylim(-4.6, 3.2); ax.axis("off")
    ax.set_title("Program: one node per copper layer", fontsize=10)
    ax.add_patch(Rectangle((0.5, -3.0), 9, 3.75, color=FR4, alpha=0.25))
    ax.add_patch(Rectangle((0.5, -0.1), 9, 0.85, fill=False, ec=BLUE, lw=2))
    ax.add_patch(Rectangle((0.5, 0.5), 9, 0.25, color=COPPER))
    ax.add_patch(Rectangle((0.5, -3.25), 9, 0.25, color=COPPER))
    ax.text(5, 0.2, "node 1: copper + 0.77 mm of FR-4 at ONE temperature", ha="center", fontsize=7.5, color=BLUE)
    ax.text(5, -1.6, "link k_z A / d (steady state)", ha="center", fontsize=8)
    ax.text(5, -4.4, "capacity 1394 J/m2K against 120 J/m2K of the copper alone:\nthe swing of a fast wave is 12 times too small", ha="center", fontsize=8)
    fig.savefig(os.path.join(FIG, "fig_01_section_fast_wave.png"), dpi=130, bbox_inches="tight")


if __name__ == "__main__":
    main()
