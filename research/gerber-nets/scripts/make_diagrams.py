"""!
@file make_diagrams.py
@brief Schematic diagrams of the nets phase: from the mask of a net to its Joule heat (README 4.20) and the proposed order of work up to the electro-thermal loop (CONCLUSIONS 4).
@details Pure drawing, no data and no program; the numbers are those of README 4.20 and 4.23 and the loop is a proposal, not built. Writes figures/fig_06_joule_chain_schematic.png and figures/fig_07_electro_thermal_loop_schematic.png.
         Run: .venv/bin/python research/gerber-nets/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

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


def main():
    """!
    @brief Draw and save the diagrams of this folder.
    @return None.
    """
    OUT.mkdir(parents=True, exist_ok=True)
    joule_chain(OUT / "fig_06_joule_chain_schematic.png")
    loop(OUT / "fig_07_electro_thermal_loop_schematic.png")


if __name__ == "__main__":
    main()
