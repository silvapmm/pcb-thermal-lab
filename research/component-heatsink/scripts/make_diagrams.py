"""!
@file make_diagrams.py
@brief Schematic diagrams of a part with its top path: the cross-section (die, pad, board, paste, heatsink), the junction-node network with the program's fixed-point loop, and the heatsink chain.
@details No numbers are computed; the shares quoted (a bare mould about 1 % of the heat, a clip-on heatsink with paste 41 to 51 %) are those of the README of this folder. Writes figures/fig_05_part_and_top_path_schematic.png.
         Run: .venv/bin/python research/component-heatsink/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

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
    ax.text(6.0, 7.6, "heatsink: theta_SA to the air", ha="center", fontsize=7.5)
    dk.arrow(ax, 6.0, 2.75, 6.0, 0.5, color=dk.HEAT, width=2.2, label="")
    ax.text(6.2, 1.0, "theta_JB: junction to pad,\nthen the board (the main path)", fontsize=6.5, color=dk.HEAT)
    dk.arrow(ax, 7.2, 3.9, 7.2, 6.8, color=dk.BLUE, width=2.2)
    ax.text(7.45, 5.9, "theta_JC(top): top path,\nonly worth it with a heatsink", fontsize=6.5, color=dk.BLUE)
    ax.set_title("1. a part on the board with a heatsink on top: two paths from the junction", fontsize=9)


def network(ax):
    """!
    @brief The junction-node network and the fixed-point loop that the program uses instead of a node.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8)
    dk.box(ax, 0.1, 3.2, 2.4, 1.6, "junction\nTj = T + P theta", "#f7d4d4", True)
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
    @brief The chain of resistances from junction to ambient with the optional elements.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 22)
    ax.set_ylim(0, 4)
    names = ["junction\nto pad", "pad,\nboard", "interface\n(under)", "metal\nblock", "package\ntop", "interface\n(paste)", "heatsink\ntheta_SA"]
    cols = ["#f7d4d4", "#d6ecd0", "#fbe3c2", "#fbe3c2", "#f7d4d4", "#fbe3c2", "#cfe3f5"]
    for k, (n, c) in enumerate(zip(names, cols)):
        dk.box(ax, 0.2 + 3.1 * k, 1.4, 2.4, 1.4, n, c)
        if k:
            dk.arrow(ax, 0.2 + 3.1 * k - 0.7, 2.1, 0.2 + 3.1 * k, 2.1)
    ax.text(11, 3.6, "the chain studied (chain_study.py): junction, pad, board, interface, metal block, package top, interface, heatsink", ha="center", fontsize=8)
    ax.text(11, 0.6, "under the board the interface moves Tj by about 2 K and the metal by about 1 K; on top of a small package the interface and the base spreading matter more", ha="center", fontsize=7.5, style="italic")
    ax.set_title("3. all the levels in one chain", fontsize=9)


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


if __name__ == "__main__":
    main()
