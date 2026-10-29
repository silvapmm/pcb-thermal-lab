#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Schematic diagrams of the power calculator: the board model run backwards (two runs, an affine relation, the watts), and the band of the answer from the one-at-a-time effects.
@details Pure drawing; the line in the second panel is the affine relation T(P) = T0 + c P that the calculator uses, with illustrative numbers. Writes figures/fig_04_calculator_schematic.png.
         Also writes figures/fig_05_reading_points_and_copper.png (the temperature reading points and the copper drawn against the real one).
         And figures/fig_07_design_sources.png: the four board-description (design) sources of the band, what each moves, the amplitude at the level Estimated and the four levels (numbers of docs/calculators.md 1.1c).
         Run: .venv/bin/python research/power-calculator/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

from matplotlib.patches import Circle, Polygon, Rectangle                 # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def flow(ax):
    """!
    @brief The calculator as a flow of boxes.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    dk.box(ax, 0.2, 5.6, 3.6, 1.8, "inputs\nthe measured temperature\nand where it was read\n(board, case top, junction)", "#cfe3f5", size=7)
    dk.box(ax, 0.2, 2.9, 3.6, 1.8, "the drawn board\n(copper, heat transfer,\nthe part's theta, psi_JT)", "#cfe3f5", size=7)
    dk.box(ax, 5.2, 4.2, 3.8, 1.8, "the board model\nrun twice:\nP = 0 and P = P1", "#d6ecd0", True, size=7.5)
    dk.box(ax, 10.2, 4.2, 3.6, 1.8, "T(P) = T0 + c P\nso  P = (T_meas - T0) / c", "#fbe3c2", True, size=7.5)
    dk.arrow(ax, 3.8, 6.4, 5.2, 5.4)
    dk.arrow(ax, 3.8, 3.8, 5.2, 4.8)
    dk.arrow(ax, 9.0, 5.1, 10.2, 5.1)
    dk.box(ax, 10.2, 1.4, 3.6, 1.8, "outputs\nthe watts, the temperatures\nat that power, the board\nresistance", "#f7d4d4", size=7)
    dk.arrow(ax, 12.0, 4.2, 12.0, 3.2)
    ax.text(7, 0.25, "the board model run backwards: because the model is linear in the power,\ntwo runs give the whole line (the heat transfer coefficient is held fixed)", ha="center", fontsize=8, style="italic")
    ax.set_title("1. how the watts are found", fontsize=9)


def affine(ax):
    """!
    @brief The affine relation between the power and the temperature, and the reading that gives the answer.
    @param ax Axes.
    @return None.
    """
    ax.axis("on")
    P = np.linspace(0, 4, 50)
    ax.plot(P, 25 + 22 * P, color="k", linewidth=2)
    ax.plot([0, 2.0], [25, 25 + 44], "o", color=dk.BLUE, markersize=8)
    ax.text(0.45, 27, "run 1: P = 0 (ambient)", fontsize=7, color=dk.BLUE)
    ax.text(1.85, 74, "run 2: P = P1", fontsize=7, color=dk.BLUE, ha="right")
    ax.axhline(80, color=dk.HEAT, linestyle="--")
    ax.text(0.05, 82, "measured temperature", color=dk.HEAT, fontsize=8)
    ax.axvline((80 - 25) / 22, color=dk.HEAT, linestyle="--")
    ax.text((80 - 25) / 22 + 0.05, 30, "the watts", color=dk.HEAT, fontsize=8)
    ax.set_xlabel("power (W, illustrative)")
    ax.set_ylabel("temperature at the reading point (C)")
    ax.set_title("2. the line from two runs and the reading on it", fontsize=9)
    ax.grid(alpha=0.3)


def band(ax):
    """!
    @brief The band: best, nominal and worst power from the effects of the uncertain inputs combined by root-sum-square.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    names = ["copper", "heat transfer", "theta", "psi_JT", "the reading", "board description:\n4 design terms (fig. 7)"]
    for k, n in enumerate(names):
        dk.box(ax, 0.2, 7.0 - 1.1 * k, 3.0, 0.85, n, "#cfe3f5" if k < 5 else "#fbe3c2", size=7)
        dk.arrow(ax, 3.2, 7.4 - 1.1 * k, 4.6, 3.8)
    dk.box(ax, 4.6, 3.0, 2.2, 1.6, "root sum\nof squares\nof the effects\n(one at a time)", "#d6ecd0", True, size=7)
    dk.arrow(ax, 6.8, 3.8, 7.5, 3.8)
    dk.box(ax, 7.5, 2.4, 2.3, 2.8, "best\nnominal\nworst\npower", "#fbe3c2", True)
    ax.text(5, 0.6, "the selector decides which of the three is written into the part", ha="center", fontsize=7.5, style="italic")
    ax.set_title("3. the band of the answer", fontsize=9)


def reading_points(path):
    """!
    @brief Draw where the temperature of a part can be read (junction, case top, board) on the section of a package, and the drawn copper against the real copper that dominates the error (README 2).
    @param path Output file.
    @return None.
    """
    fig, (a1, a2) = dk.canvas(14, 5.2, 1, 2, ratios=[1.1, 1])
    a1.set_xlim(0, 10)
    a1.set_ylim(-0.8, 7.2)
    dk.layer(a1, 0.5, 1.0, 9.0, 1.3, dk.FR4)
    a1.text(1.8, 1.65, "board", ha="center", va="center", fontsize=7.5)
    dk.layer(a1, 0.5, 2.3, 9.0, 0.2, dk.COPPER)
    dk.layer(a1, 0.5, 0.8, 9.0, 0.2, dk.COPPER)
    dk.layer(a1, 2.6, 2.5, 4.8, 0.15, "#bbbbbb")
    dk.layer(a1, 2.7, 2.65, 4.6, 2.0, "#555555")
    a1.add_patch(Rectangle((3.9, 2.8), 2.2, 0.5, facecolor="#f4b6b6", edgecolor="k"))
    for (x, y, t, c) in ((5.0, 3.05, "Tj (die)", "k"), (5.0, 4.9, "T case top", dk.BLUE), (1.6, 2.75, "T board", dk.BLUE)):
        a1.plot([x], [y if y != 3.05 else 3.05], "o", color=c, markersize=6)
    a1.text(5.0, 3.55, "junction Tj", ha="center", fontsize=7, color="white")
    a1.text(5.0, 5.25, "case top (thermocouple): psi_JT", ha="center", fontsize=7.5, color=dk.BLUE)
    a1.text(1.6, 3.25, "board next\nto the pad", ha="center", fontsize=7.5, color=dk.BLUE)
    dk.arrow(a1, 5.0, 2.8, 5.0, 0.6, color=dk.HEAT, width=1.8)
    a1.text(7.9, 1.65, "theta: junction\nto the board", fontsize=7, ha="center", va="center")
    a1.text(5, 6.9, "which temperature was read", ha="center", fontsize=9, fontweight="bold")
    a1.text(5, -0.6, "the calculator runs the board model twice and reads the line T(P) at the point you measured", ha="center", fontsize=7, style="italic")
    # drawn board against real board
    a2.set_xlim(0, 12)
    a2.set_ylim(-1.6, 7.6)
    a2.set_aspect("equal")
    a2.text(6, 7.1, "the copper is what dominates the error", ha="center", fontsize=9, fontweight="bold")
    for x0, copper, label in ((0.2, (0.8, 0.8, 4.2, 4.2), "real board:\nlarge copper plane"), (6.3, (2.2, 2.2, 1.8, 1.8), "drawn board:\nonly the pad")):
        a2.add_patch(Rectangle((x0, 0.2), 5.4, 5.4, facecolor=dk.FR4, edgecolor="k"))
        a2.add_patch(Rectangle((x0 + copper[0] - 0.5, copper[1] - 0.5 + 0.2), copper[2], copper[3], facecolor=dk.COPPER, edgecolor="k"))
        a2.add_patch(Rectangle((x0 + 2.0, 2.0), 1.4, 1.4, facecolor="#c0392b", edgecolor="k"))
        a2.text(x0 + 2.7, 5.9, label, ha="center", va="bottom", fontsize=7.5)
    a2.text(6, -0.3, "drawn copper not the real one: -11 to -45 % in the power found\nheat transfer, theta, psi_JT and a 3 K reading error: 5 to 9 % each", ha="center", va="top", fontsize=7.5, color=dk.HEAT)
    dk.save(fig, path, "The power calculator: what is measured, and what the drawing must get right")


def design_sources(path):
    """!
    @brief The four design sources of the power band: what each one moves on the drawn board, its amplitude at the level Estimated, the four levels and how they are combined with the numbers (docs/calculators.md 1.1c).
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(14, 6.6)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6.6)
    srcs = [("copper coverage", "fill of every outer-layer zone\nx (1 -/+ a), limited to 1", "40 %", "top pad half filled:\n-13 % of power"),
            ("copper weight", "thickness of every layer\nx (1 -/+ a), on top of the 25 %", "50 %", "17.5 instead of 35 um:\n-24 %"),
            ("inner planes", "down: fill x (1 - a); up: a plane\nat fill a where there is none", "50 %", "no inner planes:\n-34 %"),
            ("vias", "plating of the barrel\nx (1 -/+ a); none drawn: not run", "50 %", "no vias under the part:\n-11 %")]
    ax.text(0.2, 5.9, "source", fontsize=8, fontweight="bold")
    ax.text(2.7, 5.9, "what is moved on the drawn board", fontsize=8, fontweight="bold")
    ax.text(6.6, 5.9, "amplitude a at\nthe level Estimated\n(assumed)", fontsize=8, fontweight="bold", va="top")
    ax.text(8.6, 5.9, "measured sensitivity\n(the four wrong boards)", fontsize=8, fontweight="bold", va="top")
    for k, (name, what, amp, sens) in enumerate(srcs):
        y = 4.4 - 1.05 * k
        dk.box(ax, 0.2, y, 2.2, 0.85, name, "#cfe3f5", size=8)
        dk.box(ax, 2.7, y, 3.6, 0.85, what, "#ffffff", size=7.5)
        dk.box(ax, 6.6, y, 1.6, 0.85, amp, "#fbe3c2", size=9)
        dk.box(ax, 8.6, y, 2.3, 0.85, sens, "#ffffff", size=7.5)
        dk.arrow(ax, 10.9, y + 0.42, 11.5, 3.1)
    dk.box(ax, 11.5, 2.4, 2.3, 1.4, "root sum of squares\nwith the five numeric\nsources (copper,\nh, theta, psi_JT, reading)", "#d6ecd0", True, size=7.5)
    dk.arrow(ax, 12.65, 2.4, 12.65, 1.9)
    dk.box(ax, 11.5, 0.7, 2.3, 1.1, "best / nominal / worst\n(nominal never moves)", "#f7d4d4", size=7.5)
    # The four levels: the multiplier of the amplitude
    ax.text(0.2, 0.55, "level (multiplier of a):", fontsize=8, fontweight="bold")
    for k, (lab, mult) in enumerate((("None", "0"), ("From fabrication files", "0.2"), ("By hand (default)", "0.5"), ("Estimated", "1"))):
        dk.box(ax, 3.0 + 1.9 * k, 0.15, 1.8, 0.9, f"{lab}\nx {mult}", "#e8e8e8" if mult != "0.5" else "#fbe3c2", bold=(mult == "0.5"), size=7)
    ax.text(0.2, 6.4, "the amplitudes and the level multipliers are assumed judgements, not fitted to data; the sensitivities are measured", fontsize=7.5, style="italic")
    dk.save(fig, path, "The four board-description (design) sources of the power band and the four levels")


def main():
    """!
    @brief Draw the three panels and save the figure.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig, axs = dk.canvas(16, 5.2, 1, 3, [1.3, 1, 1])
    flow(axs[0])
    affine(axs[1])
    band(axs[2])
    dk.save(fig, OUT / "fig_04_calculator_schematic.png", "The power calculator: schematics")
    reading_points(OUT / "fig_05_reading_points_and_copper.png")
    design_sources(OUT / "fig_07_design_sources.png")


if __name__ == "__main__":
    main()
