"""!
@file make_diagrams.py
@brief Schematic diagrams of the power calculator: the board model run backwards (two runs, an affine relation, the watts), and the band of the answer from the one-at-a-time effects.
@details Pure drawing; the line in the second panel is the affine relation T(P) = T0 + c P that the calculator uses, with illustrative numbers. Writes figures/fig_04_calculator_schematic.png.
         Run: .venv/bin/python research/power-calculator/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

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
    dk.box(ax, 0.2, 5.6, 3.6, 1.8, "inputs\nthe measured temperature\nand where it was read\n(board, case top, junction)", "#cfe3f5")
    dk.box(ax, 0.2, 2.9, 3.6, 1.8, "the drawn board\n(copper, heat transfer,\nthe part's theta, psi_JT)", "#cfe3f5")
    dk.box(ax, 5.2, 4.2, 3.8, 1.8, "the board model\nrun twice: P = 0 and P = P1", "#d6ecd0", True)
    dk.box(ax, 10.2, 4.2, 3.6, 1.8, "T(P) = T0 + c P\nso  P = (T_meas - T0) / c", "#fbe3c2", True)
    dk.arrow(ax, 3.8, 6.4, 5.2, 5.4)
    dk.arrow(ax, 3.8, 3.8, 5.2, 4.8)
    dk.arrow(ax, 9.0, 5.1, 10.2, 5.1)
    dk.box(ax, 10.2, 1.4, 3.6, 1.8, "outputs\nthe watts, the temperatures\nat that power, the board\nresistance", "#f7d4d4")
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
    ax.text(0.05, 27, "run 1: P = 0 (ambient)", fontsize=7, color=dk.BLUE)
    ax.text(2.05, 66, "run 2: P = P1", fontsize=7, color=dk.BLUE)
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
    names = ["copper", "heat transfer", "theta", "psi_JT", "the reading"]
    for k, n in enumerate(names):
        dk.box(ax, 0.2, 6.4 - 1.15 * k, 3.0, 0.9, n, "#cfe3f5", size=7.5)
        dk.arrow(ax, 3.2, 6.85 - 1.15 * k, 4.6, 3.8)
    dk.box(ax, 4.6, 3.0, 2.2, 1.6, "root sum\nof squares\nof the effects\n(one at a time)", "#d6ecd0", True, size=7)
    dk.arrow(ax, 6.8, 3.8, 7.5, 3.8)
    dk.box(ax, 7.5, 2.4, 2.3, 2.8, "best\nnominal\nworst\npower", "#fbe3c2", True)
    ax.text(5, 0.6, "the selector decides which of the three is written into the part", ha="center", fontsize=7.5, style="italic")
    ax.set_title("3. the band of the answer", fontsize=9)


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


if __name__ == "__main__":
    main()
