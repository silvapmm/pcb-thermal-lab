"""!
@file make_diagrams.py
@brief Schematic diagrams of a part with its top path: the cross-section (die, pad, board, paste, heatsink), the junction-node network with the program's fixed-point loop, and the two branches of resistances from the junction.
@details No numbers are computed; the shares quoted (a bare mould about 1 % of the heat, a clip-on heatsink with paste 41 to 51 %) are those of the README of this folder. Writes figures/fig_05_part_and_top_path_schematic.png.
         Also writes figures/fig_06_package_sections.png (a part with and without a heatsink, sections).
         Run: .venv/bin/python research/component-heatsink/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

from matplotlib.patches import Circle, Polygon, Rectangle                 # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def cross_section(ax):
    """!
    @brief A package on the board with a heatsink on top: the two paths from the junction.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 10)
    dk.layer(ax, 1, 2.0, 10, 0.25, dk.COPPER)
    dk.layer(ax, 1, 1.2, 10, 0.8, dk.FR4)
    dk.layer(ax, 1, 0.95, 10, 0.25, dk.COPPER)
    ax.text(1.2, 1.6, "board: copper layers and laminate", fontsize=7, va="center")
    dk.layer(ax, 4.5, 2.25, 3.0, 0.35, dk.COPPER)
    ax.text(6.0, 2.42, "exposed pad", ha="center", fontsize=6.5, va="center")
    dk.layer(ax, 4.0, 2.6, 4.0, 1.6, "#555555")
    ax.text(6.0, 3.8, "package (mould)", ha="center", va="center", fontsize=7, color="w")
    dk.layer(ax, 5.2, 2.65, 1.6, 0.4, "#d62728")
    ax.text(6.0, 2.85, "die: junction Tj", ha="center", va="center", fontsize=6.5, color="w")
    dk.layer(ax, 4.0, 4.2, 4.0, 0.3, "#f2e394")
    ax.text(8.2, 4.35, "paste / pad: interface", fontsize=6.5, va="center")
    dk.layer(ax, 3.5, 4.5, 5.0, 0.8, dk.METAL)
    for k in range(6):
        dk.layer(ax, 3.6 + k * 0.85, 5.3, 0.3, 2.0, dk.METAL)
    ax.text(6.0, 7.6, "heatsink: theta_SA to the air\n(typed, or one of the typical heatsinks of the library with its flow)", ha="center", fontsize=7)
    dk.arrow(ax, 6.0, 2.75, 6.0, 0.5, color=dk.HEAT, width=2.2, label="")
    # The program's theta is the junction-to-pad number (theta_JC(bot), RthJC of a MOSFET), not theta_JB (README 4.1 B: theta_JB counts the board twice)
    ax.text(6.2, 0.55, "theta = theta_JC(bot): junction to pad,\nthen the board (the main path)", fontsize=6.5, color=dk.HEAT)
    dk.arrow(ax, 7.2, 3.9, 7.2, 6.8, color=dk.BLUE, width=2.2)
    ax.text(8.7, 6.3, "theta_JC(top): top path,\nonly worth it with a heatsink", fontsize=6.5, color=dk.BLUE)
    ax.set_title("1. a part on the board with a heatsink on top: two paths from the junction", fontsize=9)


def network(ax):
    """!
    @brief The junction-node network and the fixed-point loop that the program uses instead of a node.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8)
    dk.box(ax, 0.1, 3.2, 2.4, 1.6, "junction\nTj = T_max\n+ P_board theta", "#f7d4d4", True)
    dk.arrow(ax, 2.5, 4.4, 4.0, 5.8, color=dk.HEAT)
    dk.arrow(ax, 2.5, 3.6, 4.0, 2.2, color=dk.BLUE)
    dk.box(ax, 4.0, 5.2, 3.6, 1.3, "pad / board\n(the board model)", "#d6ecd0")
    dk.box(ax, 4.0, 1.6, 3.6, 1.3, "case, paste,\nheatsink theta_SA", "#cfe3f5")
    dk.arrow(ax, 7.6, 5.85, 9.2, 4.5, color=dk.HEAT)
    dk.arrow(ax, 7.6, 2.25, 9.2, 3.5, color=dk.BLUE)
    dk.box(ax, 9.2, 3.2, 1.6, 1.6, "ambient", "#ffffff")
    dk.box(ax, 11.0, 1.4, 3.6, 5.2, "the program's way:\nno junction node;\nthe top path takes\nP_top from the heat,\nthe board gets P - P_top,\niterate until it holds\n(steady state)", "#fbe3c2", True, size=7)
    ax.text(7.0, 7.6, "bare mould: about 1 % of the heat goes up;  clip-on heatsink with paste: 41 to 51 %", ha="center", fontsize=8, style="italic")
    ax.text(7.0, 0.5, "within 0.4 to 0.8 K of a junction-node prototype on the four real parts", ha="center", fontsize=8, style="italic")
    ax.set_title("2. the network behind it and the fixed-point loop of the program", fontsize=9)


def chain(ax):
    """!
    @brief The two branches of resistances from the junction to the ambient studied in chain_study.py: down through the board (and a metal block), up through the package top.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 22)
    ax.set_ylim(0, 5)
    dk.box(ax, 0.2, 1.9, 2.4, 1.4, "junction\nTj", "#f7d4d4", True)
    down = (["theta to\nthe pad", "pad, board\n(and its faces\nto the air)", "interface\n(under)", "metal\nblock"], ["#f7d4d4", "#d6ecd0", "#fbe3c2", "#fbe3c2"])
    up = (["package top\ntheta_JC(top)", "interface\n(paste)", "heatsink\ntheta_SA"], ["#f7d4d4", "#fbe3c2", "#cfe3f5"])
    # Two parallel branches leave the junction: they are not one series chain
    for (names, cols), y, colr in ((down, 3.2, dk.HEAT), (up, 0.6, dk.BLUE)):
        for k, (n, c) in enumerate(zip(names, cols)):
            x = 3.6 + 3.1 * k
            dk.box(ax, x, y, 2.4, 1.1, n, c)
            if k:
                dk.arrow(ax, x - 0.7, y + 0.55, x, y + 0.55, color=colr)
        dk.arrow(ax, 2.6, 2.6, 3.6, y + 0.55, color=colr)
        dk.arrow(ax, 3.6 + 3.1 * (len(names) - 1) + 2.4, y + 0.55, 18.6, 2.6, color=colr)
    dk.box(ax, 18.6, 1.9, 2.4, 1.4, "ambient", "#ffffff")
    ax.text(11, 4.75, "the two paths studied (chain_study.py): down through pad, board, interface and metal block; up through the package top, paste and heatsink", ha="center", fontsize=8)
    ax.text(11, 0.1, "under the board the interface moves Tj by about 2 K and the metal by about 1 K; on top of a small package the interface and the base spreading matter more", ha="center", fontsize=7.5, style="italic")
    ax.set_title("3. all the levels: two parallel branches from the junction", fontsize=9)


def package(ax, x, heatsink, title, share):
    """!
    @brief Draw the section of a package on the board (die, mould, pad, vias) with or without a heatsink on top and the two paths of the heat.
    @param ax Axes.
    @param x Left of the drawing.
    @param heatsink True to put a heatsink with paste on the package.
    @param title Title of the drawing.
    @param share Text with the share of the heat going up.
    @return None.
    """
    dk.layer(ax, x, 1.0, 6.0, 1.3, dk.FR4)
    ax.text(x + 0.7, 1.65, "board", ha="center", va="center", fontsize=7)
    dk.layer(ax, x, 2.3, 6.0, 0.2, dk.COPPER)
    dk.layer(ax, x, 0.8, 6.0, 0.2, dk.COPPER)
    for vx in (x + 2.3, x + 3.0, x + 3.7):
        ax.add_patch(Rectangle((vx - 0.1, 0.8), 0.2, 1.7, facecolor=dk.COPPER, edgecolor="k"))
    dk.layer(ax, x + 1.4, 2.5, 3.2, 0.15, "#bbbbbb")
    dk.layer(ax, x + 1.5, 2.65, 3.0, 1.4, "#555555", "mould")
    ax.text(x + 3.0, 2.0, "", fontsize=6)
    ax.add_patch(Rectangle((x + 2.4, 2.75), 1.2, 0.35, facecolor="#f4b6b6", edgecolor="k"))
    ax.text(x + 3.0, 2.92, "die: Tj", ha="center", va="center", fontsize=6.5)
    if heatsink:
        dk.layer(ax, x + 1.5, 4.05, 3.0, 0.12, "#e8d98c")
        dk.layer(ax, x + 1.2, 4.17, 3.6, 0.4, dk.METAL)
        for k in range(5):
            dk.layer(ax, x + 1.3 + k * 0.7, 4.57, 0.25, 1.2, dk.METAL)
    dk.arrow(ax, x + 3.0, 2.7, x + 3.0, 0.5, color=dk.HEAT, width=3.0 if not heatsink else 1.8)
    dk.arrow(ax, x + 3.0, 3.6 if not heatsink else 4.0, x + 3.0, 4.6 if not heatsink else 6.0, color=dk.HEAT, width=0.8 if not heatsink else 2.4)
    ax.text(x + 3.0, 6.6, title, ha="center", fontsize=9, fontweight="bold")
    ax.text(x + 5.05, 1.65, "theta to the pad\n(theta_JC(bot)),\nthen the vias", ha="center", fontsize=6.5, va="center")
    ax.text(x + 3.0, 0.05, share, ha="center", va="top", fontsize=7.5, color=dk.HEAT)


def package_sections(path):
    """!
    @brief Draw a part on the board without and with a heatsink: where the junction is and how much of the heat each path takes (README 2).
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(13, 5.4)
    ax.set_xlim(-0.5, 14)
    ax.set_ylim(-1.0, 7.1)
    package(ax, 0.0, False, "bare mould", "up through the mould: about 1 % (0.6 to 1.4 %), Tj lower by 0.4 to 0.8 K\nthe rest goes down into the board")
    package(ax, 7.0, True, "clip-on heatsink with paste (12 K/W)", "up through paste and heatsink: 41 to 51 %\nTj lower by 14 to 38 K")
    dk.save(fig, path, "The junction and its two paths: a part with and without a heatsink on top")


def main():
    """!
    @brief Draw the three panels and save the figure.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig = dk.plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.35, 0.8])
    axes = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])]
    for ax in axes:
        ax.axis("off")
    cross_section(axes[0])
    network(axes[1])
    chain(axes[2])
    dk.save(fig, OUT / "fig_05_part_and_top_path_schematic.png", "The part, its top path and its heatsink: schematics")
    package_sections(OUT / "fig_06_package_sections.png")


if __name__ == "__main__":
    main()
