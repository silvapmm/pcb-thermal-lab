"""!
@file make_diagrams.py
@brief Schematic diagrams of the stack-up: the simple mode (equal gaps, the thickness shared by the layers) against the advanced mode (copper per layer, material and thickness per gap), the thickness that each node represents and the vertical conductance between nodes as a series of half gaps.
@details Pure drawing, symbolic labels. Writes figures/fig_04_stackup_schematic.png.
         Also writes figures/fig_05_stackup_to_scale.png (the 4-layer stack-up in true proportions) and figures/fig_08_inner_copper_cross_section.png (the same stack-up with 0.5 oz and with 1 oz inner copper, from `pcbthermal.model.stackup_template`).
         Run: .venv/bin/python research/stackup/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np

from matplotlib.patches import Circle, Polygon, Rectangle                 # noqa: E402

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
    dk.box(ax, 0.8, 1.9, 10.4, 3.2, "findings (4 layers, vias): dielectric k ±30 %\nand thickness ±10 % move the rise by about 1 %,\nthe finished copper ±15 % by about 5 %\n(a one-layer pad: k ±30 % moves it 6 to 9 %);\nequal gaps in the advanced mode agree with\nthe simple mode within 0.1 K;\nan exact 1D series-circuit test checks the chain", "#fbe3c2", size=7.5)
    ax.text(6, 0.7, "typical stack-ups by layer count: pcbthermal/data/stackups.json\n(only the 4-layer one is a published fabricator table);\ninner copper 0.5 oz (default) or 1 oz: Board.template_inner_oz (figure 8)", ha="center", fontsize=7, style="italic")
    ax.set_title("3. the vertical chain, and what it was found to matter", fontsize=9)


def stackup_to_scale(path):
    """!
    @brief Draw the 4-layer stack-up of the program (JLCPCB table) to scale and what each of its numbers is worth for the temperature (README 2).
    @param path Output file.
    @return None.
    """
    fig, (a1, a2) = dk.canvas(13, 6.2, 1, 2, ratios=[1, 1.2])
    layers = [("copper", 35, dk.COPPER), ("prepreg 7628", 210.4, "#c9d8a8"), ("copper", 15.2, dk.COPPER), ("core", 1065, dk.FR4), ("copper", 15.2, dk.COPPER), ("prepreg 7628", 210.4, "#c9d8a8"), ("copper", 35, dk.COPPER)]
    total = sum(t for _, t, _ in layers)
    a1.set_xlim(0, 10)
    a1.set_ylim(-0.8, 8.4)
    y = 7.6
    for name, t, c in layers:
        h = 7.0 * t / total
        a1.add_patch(Rectangle((0.4, y - h), 4.0, h, facecolor=c, edgecolor="k", linewidth=0.8))
        a1.text(4.6, y - h / 2, f"{name}  {t:g} um", va="center", fontsize=7.5)
        y -= h
    a1.text(2.4, 8.1, "4 layers, to scale", ha="center", fontsize=9, fontweight="bold")
    a1.text(2.4, 0.4 - 0.5, f"total {total:.1f} um = 1.586 mm\nthe copper is a thin line against the laminate", ha="center", va="top", fontsize=7.5)
    # what matters
    a2.set_xlim(0, 12)
    a2.set_ylim(-0.8, 8.4)
    a2.text(6, 8.1, "what each number is worth (README 2 and 4)", ha="center", fontsize=9, fontweight="bold")
    items = [("finished outer copper 15 % thinner", 5.7, "+5.7 % of the rise"), ("dielectric conductivity and thickness (4 layers, vias)", 1.0, "about 1 % (one-layer pad: 6 to 9 %)"),
             ("another fabricator's dielectric split (upper end)", 1.5, "0.2 to 2.0 % of the rise")]
    for k, (name, v, label) in enumerate(items):
        yy = 6.3 - k * 1.7
        a2.text(0.1, yy + 0.65, name, fontsize=7.5)
        a2.add_patch(Rectangle((0.1, yy - 0.2), v * 1.2, 0.7, facecolor=dk.HEAT if v > 5 else "#c9c9c9", edgecolor="k"))
        a2.text(v * 1.2 + 0.3, yy + 0.15, label, va="center", fontsize=7.5)
    a2.text(0.1, 1.55, "copper weight, heavy against half-ounce", fontsize=7.5)
    a2.text(0.1, 0.95, "70 to 102 K of rise on the same board (ceramic core: 71 K)", fontsize=7.5, color=dk.HEAT)
    a2.text(6, -0.4, "the three bars share one scale (percent of the rise); the copper weight is in kelvin", ha="center", fontsize=7, style="italic")
    dk.save(fig, path, "The 4-layer stack-up in true proportions and what its numbers matter")


def inner_copper_cross_section(path):
    """!
    @brief The 4-layer template in true proportions with the default 0.5 oz (15.2 um) inner copper and with the 1 oz (35 um) option `Board.template_inner_oz` = 1: every dielectric keeps its thickness, only the inner copper changes and the board is thicker.
    @details The layers and totals are read from `pcbthermal.model.stackup_template(4, None, inner_oz)`, so the drawing follows the program. The temperature effect (-6.9 K with the dielectrics unchanged, README 4.5 and docs/validation.md 14.1) is the number printed by `study_inner_copper_1oz.py`, written in the caption of the README, not computed here.
    @param path Output file.
    @return None.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from pcbthermal import model
    fig, axs = dk.canvas(12, 6.2, 1, 3, [1, 1, 0.9])
    scale = 4.6 / 1700.0                                          # drawing units per um (the thicker board is 1.626 mm)
    totals = []
    for ax, oz, title in ((axs[0], 0.5, "0.5 oz inner copper (default, JLCPCB standard)"), (axs[1], 1.0, "1 oz inner copper (option, derived)")):
        t = model.stackup_template(4, None, oz)
        totals.append(t["total_thickness_um"])
        ax.set_xlim(0, 7)
        ax.set_ylim(-1.6, 5.4)
        y = 5.0
        for k, cu in enumerate(t["copper_um"]):
            h = max(cu * scale * 3.0, 0.04)                      # the copper is drawn three times thicker than the scale, or it would be a line
            ax.add_patch(Rectangle((0.6, y - h), 3.6, h, facecolor=dk.COPPER, edgecolor="k", linewidth=0.7))
            ax.text(4.35, y - h / 2, f"copper {cu:g} um", fontsize=7, va="center", color="#a05a00" if k in (1, 2) else "k")
            y -= h
            if k < len(t["dielectrics"]):
                d = t["dielectrics"][k]
                hd = d["thickness_um"] * scale
                ax.add_patch(Rectangle((0.6, y - hd), 3.6, hd, facecolor=dk.FR4 if d["kind"] == "core" else "#c9d8a5", edgecolor="k", linewidth=0.7))
                ax.text(4.35, y - hd / 2, f"{d['kind']} {d['thickness_um']:g} um", fontsize=7, va="center")
                y -= hd
        ax.text(2.4, -0.3, f"board {t['total_thickness_um'] / 1000:.3f} mm", ha="center", fontsize=8, fontweight="bold")
        ax.set_title(title, fontsize=9)
    ax = axs[2]
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 8)
    dk.box(ax, 0.1, 4.8, 5.6, 2.6, "what the option does:\nevery inner copper layer becomes 35 um;\nevery dielectric keeps the thickness\nof the template (no scaling)", "#cfe3f5", size=8)
    dk.box(ax, 0.1, 1.6, 5.6, 2.6, f"cost: the board is thicker by\n(35 - 15.2) um per inner layer:\n{totals[0] / 1000:.3f} -> {totals[1] / 1000:.3f} mm (4 layers);\n0.04 to 0.20 mm for 4 to 12 layers", "#fbe3c2", size=8)
    ax.text(2.9, 0.7, "the copper is drawn three times thicker than the scale", ha="center", fontsize=7, style="italic")
    dk.save(fig, path, "The inner copper of the typical stack-up: 0.5 oz against 1 oz (Board.template_inner_oz)")


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
    stackup_to_scale(OUT / "fig_05_stackup_to_scale.png")
    inner_copper_cross_section(OUT / "fig_08_inner_copper_cross_section.png")


if __name__ == "__main__":
    main()
