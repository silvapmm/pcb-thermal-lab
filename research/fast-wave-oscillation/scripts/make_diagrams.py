#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Diagrams of the situation: the real section under a part with the heat path of a fast and of a slow wave, and what one node per copper layer holds (figure 1);
       the sections of the cases of the review where the estimator E3 was tested beyond the author's family (figure 5).

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
    @brief Draw figures 1 and 5.
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
    review_cases()


def review_cases():
    """!
    @brief Figure 5: four sections (heater on an inner layer, part on bare laminate, vias under the part, a 2 mm part on the 2 mm cell of the decision) with the heat path of a fast wave.
    @return None.
    """
    fig, axes = canvas(13.0, 4.0, nrows=1, ncols=4)
    titles = ("heater on an inner layer", "part on bare laminate", "vias under the part", "2 mm part, 2 mm decision cell")
    notes = ("heat enters laminate on BOTH sides:\nE3 (one side) overstates 1.07 to 1.57 x",
             "no copper sheet: E3 (copper sheet)\nunderstates; the face term carries it",
             "barrels carry heat down: E3 high\nbelow 10 Hz (up to 1.56 x, safe side)",
             "one cell holds the part: the decision's\nswing reads 0.67 x even at 0.1 Hz")
    for k, ax in enumerate(axes):
        ax.set_xlim(0, 10); ax.set_ylim(-4.6, 3.2); ax.axis("off")
        ax.set_title(titles[k], fontsize=9.5)
        ax.add_patch(Rectangle((0.5, -3.0), 9, 3.5, color=FR4, alpha=0.55))
        if k != 1:
            ax.add_patch(Rectangle((0.5, 0.5), 9, 0.25, color=COPPER))
        else:
            ax.add_patch(Rectangle((0.5, 0.5), 2.0, 0.25, color=COPPER))
            ax.add_patch(Rectangle((7.5, 0.5), 2.0, 0.25, color=COPPER))
        ax.add_patch(Rectangle((0.5, -3.25), 9, 0.25, color=COPPER))
        if k == 0:
            ax.add_patch(Rectangle((0.5, -1.35), 9, 0.25, color=COPPER))
            ax.add_patch(Rectangle((3, -1.35), 4, 0.25, color=HEAT, alpha=0.6))
            ax.add_patch(Rectangle((3, -1.1), 4, 0.25, color=HEAT, alpha=0.25))
            ax.add_patch(Rectangle((3, -1.6), 4, 0.25, color=HEAT, alpha=0.25))
        else:
            ax.add_patch(Rectangle((3, 1.0), 4, 0.5, color="#555555"))
            ax.add_patch(Rectangle((3, 0.3), 4, 0.2 if k != 1 else 0.45, color=HEAT, alpha=0.3))
        if k == 2:
            for x in (3.6, 5.0, 6.4):
                ax.add_patch(Rectangle((x - 0.12, -3.0), 0.24, 3.5, color=COPPER))
                ax.add_patch(FancyArrowPatch((x + 0.4, 0.2), (x + 0.4, -2.6), arrowstyle="-|>", color=BLUE, mutation_scale=8))
        if k == 3:
            for x in np.arange(0.5, 9.6, 2.0):
                ax.plot([x, x], [-3.25, 0.75], color=BLUE, lw=0.8, ls="--")
            ax.add_patch(Rectangle((4.5, 1.0), 2.0, 0.5, color="#555555"))
        ax.text(5, -4.4, notes[k], ha="center", fontsize=7.5)
    fig.savefig(os.path.join(FIG, "fig_05_review_cases.png"), dpi=130, bbox_inches="tight")


if __name__ == "__main__":
    main()
