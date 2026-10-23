"""!
@file make_diagrams.py
@brief Schematic diagrams of the nets phase: from the mask of a net to its Joule heat (README 4.20) and the proposed order of work up to the electro-thermal loop (CONCLUSIONS 4).
@details Pure drawing, no data and no program; the numbers are those of README 4.20 and 4.23 and the loop is a proposal, not built. Writes figures/fig_06_joule_chain_schematic.png figures/fig_07_electro_thermal_loop_schematic.png, figures/fig_08_track_in_squares.png and figures/fig_09_where_the_power_goes.png.
         Run: .venv/bin/python research/gerber-nets/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

import numpy as np
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def joule_chain(path):
    """!
    @brief Draw the steps from the mask of a net to the heat in the cells of the thermal grid.
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(15, 3.8)
    ax.set_xlim(0, 15)
    ax.set_ylim(0, 4.0)
    steps = [("mask of one net\n(X2 attribute or\nconnectivity)", dk.COPPER), ("sheet resistance\nRs = rho / t\n(+0.393 %/K)", "#e8e8e8"),
             ("Laplace problem\ndiv(grad V / Rs) = 0\nwith two terminals", "#cfe3f5"), ("potential and current\nin every pixel,\nresistance R", "#cfe3f5"),
             ("Joule heat per pixel,\nsum exactly I^2 R", "#fbe3c2"), ("summed into the\ncells of the grid:\nheat sources", "#f4b6b6")]
    for i, (text, color) in enumerate(steps):
        x = 0.1 + i * 2.45
        dk.box(ax, x, 1.4, 2.1, 1.4, text, color, size=7.5)
        if i:
            dk.arrow(ax, x - 0.35, 2.1, x, 2.1)
    ax.text(7.5, 0.6, "given from outside: the current of the net and which pads source and sink it (not inferred from voltages)", ha="center", fontsize=8, style="italic")
    ax.text(7.5, 3.5, "example (README 4.20, net VIN, 1 A, 35 um copper): R = 32 mOhm, 32 mW", ha="center", fontsize=8)
    dk.save(fig, path, "From a net to its heat: the Joule chain (README 4.20)")


def loop(path):
    """!
    @brief Draw the proposed order of work and the loop between temperature, resistance and heat.
    @param path Output file.
    @return None.
    """
    fig, ax = dk.canvas(13, 4.6)
    ax.set_xlim(0, 13)
    ax.set_ylim(-0.6, 5.0)
    names = ["1  Joule heat of a net\nwith given terminals\n(one layer)", "2  pieces joined\nby links (0 ohm, bead,\nshunt, fuse)", "3  vias between\nlayers", "4  coupling with the\ntemperature of the\nthermal run"]
    for i, t in enumerate(names):
        dk.box(ax, 0.1 + i * 3.2, 3.2, 2.9, 1.4, t, "#cfe3f5" if i < 3 else "#fbe3c2", size=8)
        if i:
            dk.arrow(ax, 0.1 + i * 3.2 - 0.3, 3.9, 0.1 + i * 3.2, 3.9)
    dk.box(ax, 1.5, 0.5, 3.0, 1.2, "temperature T\n(thermal model)", "#f4b6b6", size=8)
    dk.box(ax, 5.2, 0.5, 3.0, 1.2, "resistance rises\nwith T (+0.393 %/K)", "#e8e8e8", size=8)
    dk.box(ax, 8.9, 0.5, 3.0, 1.2, "Joule heat\nI^2 R changes", "#e8e8e8", size=8)
    dk.arrow(ax, 4.5, 1.1, 5.2, 1.1)
    dk.arrow(ax, 8.2, 1.1, 8.9, 1.1)
    # the return path drawn by hand: down from the heat box, left under the boxes, up into the temperature box
    ax.plot([10.4, 10.4, 3.0], [0.5, 0.0, 0.0], color=dk.HEAT, linewidth=1.4)
    dk.arrow(ax, 3.0, 0.0, 3.0, 0.5, color=dk.HEAT)
    ax.text(6.7, -0.3, "the heat sources go back into the thermal run", ha="center", fontsize=8, color=dk.HEAT, style="italic")
    ax.text(6.5, 2.4, "step 4 closes this loop below (a proposal, not built)", ha="center", fontsize=8, style="italic")
    dk.save(fig, path, "Order of work of the electrical side and the electro-thermal loop")


def track_in_squares(path):
    """!
    @brief Draw a track as a row of squares of sheet resistance (R = Rs x squares) with its section, the current in the copper and where the heat goes, and the arithmetic for a 0.2 mm track.
    @param path Output file.
    @return None.
    """
    rho, t = 1.68e-8, 35e-6                        # copper resistivity (ohm m) and finished 1 oz thickness (m), as in README 4.20
    rs = rho / t                                   # sheet resistance, ohm per square
    fig, (a1, a2) = dk.canvas(14, 5.4, 2, 1, ratios=None)
    a1.set_xlim(0, 14)
    a1.set_ylim(-1.2, 4.0)
    for k in range(10):
        a1.add_patch(Rectangle((1.0 + k * 1.1, 1.4), 1.1, 1.1, facecolor=dk.COPPER, edgecolor="k"))
        a1.text(1.55 + k * 1.1, 1.95, "1", ha="center", va="center", fontsize=8)
    dk.arrow(a1, 0.2, 1.95, 0.9, 1.95, color=dk.HEAT, width=2.0)
    dk.arrow(a1, 12.1, 1.95, 12.9, 1.95, color=dk.HEAT, width=2.0)
    a1.text(0.55, 2.4, "I", color=dk.HEAT, fontsize=9, ha="center")
    a1.text(6.0, 3.3, "plan view: a track is a row of squares, each one the sheet resistance Rs = rho / t", ha="center", fontsize=9, fontweight="bold")
    a1.text(6.0, 0.6, f"copper 1.68e-8 ohm m, 35 um: Rs = {rs * 1e3:.2f} mohm per square; a track 0.2 mm wide and 20 mm long is 100 squares: R = {100 * rs * 1e3:.0f} mohm\n(a bend, a pad, a neck change the number of squares: the solver counts them on the pixels)", ha="center", va="top", fontsize=8)
    a2.set_xlim(0, 14)
    a2.set_ylim(-1.2, 5.0)
    dk.layer(a2, 1.0, 1.0, 5.0, 1.6, dk.FR4)
    a2.text(1.9, 1.8, "laminate", ha="center", fontsize=8)
    dk.layer(a2, 2.4, 2.6, 2.2, 0.35, dk.COPPER)
    a2.text(3.5, 3.15, "copper track, section", ha="center", fontsize=8)
    dk.arrow(a2, 3.5, 2.6, 3.5, 1.2, color=dk.HEAT, width=1.3)
    for x in (2.6, 4.4):
        dk.arrow(a2, x, 2.95, x, 4.0, color=dk.BLUE, width=1.0)
    a2.text(3.5, 0.5, "I squared R is made in the copper\nand leaves through the board and the air", ha="center", va="top", fontsize=8)
    a2.text(9.5, 4.0, "what the electrical side must be given", ha="center", fontsize=9, fontweight="bold")
    a2.text(9.5, 3.0, "the current of the net and which pads source and sink it\n(a voltage is the same on a whole net and carries no current)\nthe resistance of any link: 0 ohm, bead, shunt, fuse", ha="center", va="top", fontsize=8)
    a2.text(9.5, 0.9, "what it then gives the thermal model:\nheat in the cells of the grid, exactly I squared R", ha="center", va="top", fontsize=8, color=dk.HEAT)
    dk.save(fig, path, "A track as squares of copper: where its resistance and its heat come from (README 4.20)")


def where_the_power_goes(path):
    """!
    @brief Draw the plan of the source, the link and the load of the scenario of README 4.40 and the split of the 7.5 W between the copper, the link and the load.
    @param path Output file.
    @return None.
    """
    fig, (a1, a2) = dk.canvas(14, 4.8, 1, 2, ratios=[1.3, 1])
    a1.set_xlim(0, 14)
    a1.set_ylim(-0.8, 6.0)
    a1.add_patch(Rectangle((0.3, 1.8), 4.2, 2.6, facecolor=dk.COPPER, edgecolor="k"))
    a1.add_patch(Rectangle((4.5, 2.8), 2.2, 0.5, facecolor=dk.COPPER, edgecolor="k"))
    a1.add_patch(Rectangle((8.3, 2.0), 3.4, 2.2, facecolor=dk.COPPER, edgecolor="k"))
    a1.add_patch(Rectangle((6.7, 2.7), 1.6, 0.7, facecolor="#cfe3f5", edgecolor="k"))
    a1.text(7.5, 3.05, "link\n0.1 ohm", ha="center", va="center", fontsize=7)
    a1.text(2.4, 3.1, "piece A\n5 V source", ha="center", va="center", fontsize=8)
    a1.text(10.0, 3.1, "piece B\n1.5 A sink (the IC)", ha="center", va="center", fontsize=8)
    dk.arrow(a1, 6.7, 3.05, 8.4, 3.05, color=dk.HEAT, width=2.0)
    a1.add_patch(Rectangle((12.2, 4.6), 1.5, 0.9, facecolor="#e8e8e8", edgecolor="k", linestyle="--"))
    a1.text(12.95, 5.05, "floating\npiece: no\ncurrent, no heat", ha="center", va="center", fontsize=6.5)
    a1.text(7, 5.6, "two pieces of one net joined by a part", ha="center", fontsize=9, fontweight="bold")
    a1.text(7, 0.9, "the current of piece B must cross the link: the link, not the copper,\nis the part that carries the whole current", ha="center", va="top", fontsize=8, style="italic")
    a2.set_xlim(0, 10)
    a2.set_ylim(-0.8, 6.0)
    a2.text(5, 5.6, "where the source's power goes", ha="center", fontsize=9, fontweight="bold")
    for k, (name, mw, color) in enumerate((("load (the IC)", 7262.7, "#9bbf8a"), ("link", 225.0, "#f4b6b6"), ("copper", 12.3, dk.COPPER))):
        y = 4.2 - k * 1.5
        a2.add_patch(Rectangle((0.2, y), 8.5 * (mw / 7500.0) if mw > 100 else 0.05, 0.8, facecolor=color, edgecolor="k"))
        a2.text(0.3, y + 1.0, f"{name}: {mw:g} mW", fontsize=8)
    a2.text(5, -0.1, "source 7500.001 mW: balance closes to 0.002 mW;\nthe link makes 18 times the heat of all the copper", ha="center", va="top", fontsize=8, color=dk.HEAT)
    dk.save(fig, path, "A source, a link and a load: what carries the current and what heats (README 4.40)")


def main():
    """!
    @brief Draw and save the diagrams of this folder.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    joule_chain(OUT / "fig_06_joule_chain_schematic.png")
    loop(OUT / "fig_07_electro_thermal_loop_schematic.png")
    track_in_squares(OUT / "fig_08_track_in_squares.png")
    where_the_power_goes(OUT / "fig_09_where_the_power_goes.png")


if __name__ == "__main__":
    main()
