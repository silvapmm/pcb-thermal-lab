"""!
@file make_diagrams.py
@brief Schematic diagrams of the metal block and its fins: the cross-section with the heat path and its thermal-resistance chain, the fin and its efficiency curve, and the three ways the Lumped and Analytic models can represent a block.
@details No data is computed except the closed-form fin efficiency tanh(mL)/(mL); the error figures quoted in the third panel are those of the README of this folder. Writes figures/fig_04_block_and_fins_schematic.png.
         Also writes figures/fig_05_block_section.png (the section of a board on a finned block and one fin).
         Run: .venv/bin/python research/block-and-fins/scripts/make_diagrams.py (from the repository root).
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
    @brief The block under the board: heat path from the part, through the board, the interface sheet and the block, to the fins and the air.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    dk.layer(ax, 1, 5.6, 10, 0.25, dk.COPPER)
    dk.layer(ax, 1, 4.6, 10, 1.0, dk.FR4)
    dk.layer(ax, 1, 4.35, 10, 0.25, dk.COPPER)
    ax.text(1.1, 5.02, "FR-4 laminate (and inner copper)", fontsize=7, va="center")
    ax.text(8.0, 5.72, "top copper", fontsize=6.5, va="center")
    ax.text(8.0, 4.47, "bottom copper", fontsize=6.5, va="center")
    dk.layer(ax, 3, 3.9, 6, 0.3, "#f2e394")
    ax.text(9.1, 4.05, "interface sheet: t / k,\na contact area", fontsize=6.5, va="center")
    dk.layer(ax, 3, 2.7, 6, 1.2, dk.METAL)
    ax.text(7.3, 3.3, "metal block", fontsize=7, va="center")
    for k in range(6):
        dk.layer(ax, 3.1 + k * 1.0, 0.8, 0.3, 1.9, dk.METAL)
    ax.text(6, 0.4, "plate fins: area gain x efficiency", ha="center", fontsize=7)
    dk.layer(ax, 4.6, 5.85, 2.8, 0.8, "#444444", "part (heater)")
    dk.arrow(ax, 6, 5.8, 6, 3.4, color=dk.HEAT, width=2.5)
    ax.text(6.15, 3.55, "heat", color=dk.HEAT, fontsize=8)
    dk.arrow(ax, 1.5, 6.2, 1.5, 7.2, color=dk.BLUE)
    dk.arrow(ax, 10.5, 6.2, 10.5, 7.2, color=dk.BLUE)
    ax.text(6, 7.5, "convection h from the free faces (and radiation)", ha="center", fontsize=7, color=dk.BLUE)
    for k in range(6):
        dk.arrow(ax, 3.25 + k, 1.2, 3.25 + k, 0.2 if k % 2 else 0.05, color=dk.BLUE, width=0.8)
    ax.set_title("1. the block under the board: where the heat goes", fontsize=9)


def resistance_chain(ax):
    """!
    @brief The same path as a chain of thermal resistances with the exposed board face in parallel.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6)
    ax.plot([0.5, 1.5], [3.5, 3.5], color="k")
    ax.text(0.2, 3.9, "part", fontsize=8)
    names = ["spreading\nin the board", "interface\nt / (k A)", "spreading\nin the block", "fins: 1 / (h A eta)"]
    x = 1.5
    for n in names:
        dk.resistor(ax, x, x + 2.6, 3.5, n, size=7)
        x += 2.6
    ax.annotate("", (x + 0.3, 3.5), (x, 3.5), arrowprops={"arrowstyle": "-"})
    ax.plot([x, x + 0.7], [3.5, 3.5], color="k")
    ax.text(x + 0.2, 3.9, "air", fontsize=8)
    ax.plot([1.5, 1.5, 12.0, 12.0], [3.5, 1.5, 1.5, 3.5], color=dk.BLUE)
    dk.resistor(ax, 5.0, 8.6, 1.5, "board faces: 1 / (h A) in parallel", dk.BLUE)
    ax.text(7, 0.4, "the block lowers the temperature of the part by giving the heat a second, large surface;\nthe interface and the contact area decide how much of it is used", ha="center", fontsize=7.5, style="italic")
    ax.set_title("2. the heat path as thermal resistances", fontsize=9)


def fin_efficiency(ax):
    """!
    @brief The efficiency of a straight fin as a function of mL, with the range of the 24 validated cases shaded.
    @param ax Axes.
    @return None.
    """
    x = np.linspace(0.01, 4.5, 300)
    ax.plot(x, np.tanh(x) / x, color="k", linewidth=2)
    lo = float(np.interp(0.27, (np.tanh(x) / x)[::-1], x[::-1]))
    hi = float(np.interp(0.997, (np.tanh(x) / x)[::-1], x[::-1]))
    ax.axvspan(hi, lo, color=dk.BLUE, alpha=0.15, label="efficiencies 0.27 to 0.997 (the 24 cases)")
    ax.set_xlabel("m L = L sqrt(h P / (k A))")
    ax.set_ylabel("efficiency tanh(mL) / (mL)")
    ax.set_title("3. one fin: heat leaves along it, the tip is cooler than the root;\nthe formula matched a 2D solution to 0.08 %", fontsize=9)
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    ax.axis("on")


def approaches(ax):
    """!
    @brief The three ways of representing a block in the Lumped and Analytic models and their mean error against the FVM.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    dk.box(ax, 0.2, 5.6, 9.6, 1.9, "A. an equivalent coefficient with a contact area and an annular fin\nthe block becomes a larger h on the board: 9 to 11 % off on average", "#f7d4d4")
    dk.box(ax, 0.2, 3.1, 9.6, 1.9, "B. Lumped: the block as one more layer of the ring network\\n2.0 % off on average (maximum 4.8 %)".replace("\\n", "\n"), "#d6ecd0", True)
    dk.box(ax, 0.2, 0.6, 9.6, 1.9, "C. Analytic: the block as a Schur complement on the tile graph of the Green-function correction\\n1.1 % off on average (maximum 4.3 %)".replace("\\n", "\n"), "#d6ecd0", True)
    ax.text(5, 7.9, "74 cases against the FVM, which solves the block natively", ha="center", fontsize=8, style="italic")
    ax.set_title("4. a block in the reduced models: three approaches", fontsize=9)


def block_section(path):
    """!
    @brief Draw the section of a board on a finned metal block (heat path from the part to the air) and one plate fin with its temperature falling along it.
    @param path Output file.
    @return None.
    """
    fig, (a1, a2) = dk.canvas(14, 5.4, 1, 2, ratios=[1.6, 1])
    a1.set_xlim(0, 16)
    a1.set_ylim(-1.0, 8.2)
    dk.box(a1, 5.8, 6.2, 2.6, 0.9, "part", "#f4b6b6", size=8)
    dk.layer(a1, 1, 5.4, 14, 0.2, dk.COPPER)
    dk.layer(a1, 1, 4.3, 14, 1.1, dk.FR4)
    a1.text(11.2, 4.85, "board (laminate\nand copper)", ha="center", va="center", fontsize=7)
    dk.layer(a1, 1, 4.1, 14, 0.2, dk.COPPER)
    dk.layer(a1, 4.0, 3.75, 8.0, 0.35, "#e8d98c")
    a1.text(10.6, 3.92, "interface (paste or pad)", ha="center", va="center", fontsize=6.5)
    dk.layer(a1, 2.0, 2.4, 12.0, 1.35, dk.METAL)
    a1.text(12.0, 2.75, "metal block\n(heat spreader)", ha="center", va="center", fontsize=7)
    for k in range(7):
        dk.layer(a1, 2.3 + k * 1.8, 0.3, 0.45, 2.1, dk.METAL)
    dk.arrow(a1, 7.1, 6.1, 7.1, 3.8, color=dk.HEAT, width=2.2)
    for x, dx in ((7.1, -3.6), (7.1, 3.6)):
        dk.arrow(a1, x, 3.1, x + dx, 3.1, color=dk.HEAT, width=1.3)
    for k in range(7):
        dk.arrow(a1, 2.52 + k * 1.8, 1.8, 2.52 + k * 1.8, 0.0, color=dk.BLUE, width=1.0)
    a1.text(8, 7.9, "section: board on a finned block", ha="center", fontsize=9, fontweight="bold")
    a1.text(3.2, 4.85, "air above and\nbelow the board", ha="center", va="center", fontsize=6.5, style="italic")
    a1.text(8, -0.8, "the block touches the board only where the interface is (a patch); the fins give an area gain with an efficiency", ha="center", fontsize=7)
    # one plate fin: base hot, tip cooler
    a2.set_xlim(0, 8)
    a2.set_ylim(-1.0, 8.2)
    grad = np.linspace(1.0, 0.0, 100).reshape(-1, 1)
    a2.imshow(grad ** 1.6, extent=(1.0, 2.2, 0.8, 6.8), cmap="YlOrRd", origin="upper", aspect="auto")
    a2.add_patch(Rectangle((1.0, 0.8), 1.2, 6.0, fill=False, edgecolor="k"))
    a2.add_patch(Rectangle((0.2, 0.3), 3.0, 0.5, facecolor=dk.METAL, edgecolor="k"))
    a2.text(1.7, 0.55, "base", ha="center", va="center", fontsize=7)
    dk.arrow(a2, 0.5, 1.0, 0.5, 6.8, color="k", width=0.8)
    a2.text(0.4, 7.2, "tip: cooler", fontsize=7.5)
    ys = np.linspace(0.8, 6.8, 60)
    th = np.cosh(1.5 * (1 - (ys - 0.8) / 6.0)) / np.cosh(1.5)
    a2.plot([4.0, 4.0], [0.8, 6.8], color="k", linewidth=0.8)
    a2.plot(4.0 + 3.0 * th, ys, color="k")
    a2.text(3.9, 0.8, "base", ha="right", va="center", fontsize=7)
    a2.text(3.9, 6.8, "tip", ha="right", va="center", fontsize=7)
    a2.text(5.5, 7.5, "temperature rise\nalong the fin (illustration)", ha="center", fontsize=7.5)
    a2.text(5.5, -0.4, "efficiency = tanh(mL) / (mL),\n0.27 to 0.997 in the 24 cases;\nformula within 0.08 % of a 2D solution", ha="center", va="top", fontsize=7.5)
    dk.save(fig, path, "The metal block and its fins as they are built, and the fin the formula describes")


def main():
    """!
    @brief Draw the four panels and save the figure.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig, axs = dk.canvas(15, 9, 2, 2)
    cross_section(axs[0, 0])
    resistance_chain(axs[0, 1])
    fin_efficiency(axs[1, 0])
    approaches(axs[1, 1])
    dk.save(fig, OUT / "fig_04_block_and_fins_schematic.png", "The metal block and its fins: schematics")
    block_section(OUT / "fig_05_block_section.png")


if __name__ == "__main__":
    main()
