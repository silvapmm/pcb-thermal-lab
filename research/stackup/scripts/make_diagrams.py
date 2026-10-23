"""!
@file make_diagrams.py
@brief Schematic diagrams of the stack-up: the simple mode (equal gaps, the thickness shared by the layers) against the advanced mode (copper per layer, material and thickness per gap), the thickness that each node represents and the vertical conductance between nodes as a series of half gaps.
@details Pure drawing, symbolic labels. Writes figures/fig_04_stackup_schematic.png.
         Run: .venv/bin/python research/stackup/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def simple(ax):
    """!
    @brief The simple mode: layers of the same copper, equal gaps, the total thickness shared equally.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    y = 7.4
    for k in range(4):
        dk.layer(ax, 1.5, y, 8, 0.3, dk.COPPER)
        ax.text(9.7, y + 0.1, f"copper {k + 1}", fontsize=7)
        if k < 3:
            dk.layer(ax, 1.5, y - 1.8, 8, 1.8, dk.FR4)
            if k == 0:
                ax.text(5.5, y - 0.9, "equal gaps: same material", ha="center", fontsize=7)
        y -= 2.1
    ax.annotate("", (0.9, 1.4), (0.9, 7.7), arrowprops={"arrowstyle": "<->"})
    ax.text(0.2, 4.5, "total\nthickness", fontsize=7, rotation=90, va="center")
    ax.text(6, 0.3, "slab per layer = total thickness / layers", ha="center", fontsize=7.5, style="italic")
    ax.set_title("1. simple mode", fontsize=9)


def advanced(ax):
    """!
    @brief The advanced mode: per-layer copper, per-gap material and thickness; each node is the copper plus half of each adjacent gap.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    cu = [0.5, 0.25, 0.25, 0.5]
    gap = [1.5, 2.2, 1.2]
    colors = ["#9bbf8a", "#c4d99a", "#9bbf8a"]
    y = 8.0
    ys = []
    for k in range(4):
        dk.layer(ax, 1.5, y - cu[k], 8, cu[k], dk.COPPER)
        ys.append(y - cu[k] / 2)
        ax.text(9.7, y - cu[k] / 2, f"t_cu{k + 1}", fontsize=7, va="center")
        y -= cu[k]
        if k < 3:
            dk.layer(ax, 1.5, y - gap[k], 8, gap[k], colors[k])
            ax.text(5.5, y - gap[k] / 2, f"gap {k + 1}: d{k + 1}, k_through, k_inplane", ha="center", fontsize=6.5, va="center")
            y -= gap[k]
    for k in range(4):
        ax.plot(2.0, ys[k], "ko", markersize=5)
    ax.text(9.7, ys[1] - 1.4, "node = copper +\nhalf of each\nadjacent gap", fontsize=6.5)
    ax.text(6, 0.5, "different materials and thicknesses per gap;\nthe slabs of the nodes add up to the total thickness", ha="center", fontsize=7.5, style="italic")
    ax.set_title("2. advanced mode", fontsize=9)


def series(ax):
    """!
    @brief The vertical conductance between two nodes as a series circuit of two half gaps, and the findings.
    @param ax Axes.
    @return None.
    """
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.plot([0.5, 1.2], [6, 6], color="k")
    ax.text(0.3, 6.5, "node i", fontsize=8)
    dk.resistor(ax, 1.2, 4.2, 6, "d_i / (2 k_i)")
    dk.resistor(ax, 4.2, 7.2, 6, "d_(i+1) / (2 k_(i+1))")
    ax.plot([7.2, 8.0], [6, 6], color="k")
    ax.text(7.8, 6.5, "node i+1", fontsize=8)
    dk.box(ax, 0.8, 1.9, 10.4, 3.2, "findings: the dielectric conductivity and\nthickness move the temperature by about 1 %,\nthe copper weight by about 5 %;\nequal gaps in the advanced mode agree with\nthe simple mode within 0.1 K;\nan exact 1D series-circuit test checks the chain", "#fbe3c2", size=7.5)
    ax.text(6, 0.7, "typical stack-ups by layer count: pcbthermal/data/stackups.json\n(only the 4-layer one is a published fabricator table)", ha="center", fontsize=7, style="italic")
    ax.set_title("3. the vertical chain, and what it was found to matter", fontsize=9)


def main():
    """!
    @brief Draw the three panels and save the figure.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    fig, axs = dk.canvas(16, 5.8, 1, 3, [1, 1.1, 1.1])
    simple(axs[0])
    advanced(axs[1])
    series(axs[2])
    dk.save(fig, OUT / "fig_04_stackup_schematic.png", "The stack-up: schematics")


if __name__ == "__main__":
    main()
