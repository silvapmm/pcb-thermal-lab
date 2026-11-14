#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Cross-section of a metal block joined to the board through several pads, with the heat paths (figures/fig_01_block_several_pads.png).
@details Schematic, no data. Run: .venv/bin/python research/block-warning-remeasure/scripts/make_diagrams.py (from the repository root).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import diagram_kit as dk                                           # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "figures"


def main():
    """!
    @brief Draw the section: parts on the top copper, laminate, bottom pads, interface sheets, the plate and its free face.
    @return None.
    """
    fig, ax = dk.canvas(9, 4.6)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    dk.layer(ax, 0.5, 5.2, 11, 0.2, dk.COPPER)
    dk.layer(ax, 0.5, 4.2, 11, 1.0, dk.FR4)
    ax.text(0.7, 4.7, "FR-4 laminate", fontsize=7, va="center")
    dk.layer(ax, 0.5, 4.0, 11, 0.2, dk.COPPER)
    for x, w in ((2.0, 1.4), (5.3, 1.4), (8.6, 1.4)):
        dk.layer(ax, x - 0.3, 5.4, w + 0.6, 0.7, "#444444", "part")
        dk.layer(ax, x - 0.3, 3.5, w + 0.6, 0.5, dk.COPPER)            # bottom pad (copper), the only place heat can enter the plate
        dk.layer(ax, x - 0.3, 3.2, w + 0.6, 0.3, "#f2e394")            # interface sheet R'' over the pad
        dk.arrow(ax, x + w / 2, 5.3, x + w / 2, 2.9, color=dk.HEAT, width=2.2)
    dk.layer(ax, 1.0, 2.2, 10, 1.0 - 0.0, dk.METAL)
    ax.text(6, 2.7, "plate (metal block), spreads the heat between the pads", ha="center", fontsize=7.5)
    ax.text(0.7, 3.6, "bare laminate between pads: no entry", fontsize=6.5, color="#555555")
    for x in (1.5, 3.2, 5.0, 6.8, 8.6, 10.4):
        dk.arrow(ax, x, 2.2, x, 1.2, color=dk.BLUE, width=1.0)
    ax.text(6, 0.8, "free face of the plate: h (+ h_extra)", ha="center", fontsize=7, color=dk.BLUE)
    for x in (3.3, 6.6):
        dk.arrow(ax, x, 3.0, x + 0.9 if x < 5 else x - 0.9, 2.9, color=dk.HEAT, width=1.0)
    ax.text(6, 7.4, "one block, several pads: heat enters through each pad and is shared inside the plate", ha="center", fontsize=8)
    dk.save(fig, OUT / "fig_01_block_several_pads.png")


if __name__ == "__main__":
    main()
