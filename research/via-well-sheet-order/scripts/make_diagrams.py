#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Diagrams of the via-well-sheet-order investigation: the section of a two-layer board at a via near a cooled edge, the nodes of the laminate rule and the sheet each order hands to the well.
@details No data, no program: the shapes come from `research/diagram_kit.py`. Writes `figures/fig_01_section_and_order.png`.
         Run from the repository root: `.venv/bin/python research/via-well-sheet-order/scripts/make_diagrams.py`.
"""

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(HERE))
import diagram_kit as dk                                                    # noqa: E402

FIG = os.path.join(HERE, "figures")


def section():
    """!
    @brief Draw the section (left) and the bookkeeping of the two orders (right).
    @return None.
    """
    fig, (a, b) = dk.canvas(11.0, 4.6, 1, 2, ratios=[1.25, 1.0])
    a.set_xlim(0, 10.5)
    a.set_ylim(-0.6, 5.6)
    b.set_xlim(0, 10)
    b.set_ylim(0, 6)
    # Section: top copper, laminate cut into sub-gaps (interior nodes), bottom copper; a barrel at x 6.5 near the right edge at x 9.5
    dk.layer(a, 0.3, 4.4, 9.2, 0.3, dk.COPPER, "top copper node (S_cu + its laminate share)", 7)
    for k in range(4):
        dk.layer(a, 0.3, 1.0 + 0.85 * k, 9.2, 0.85, dk.FR4, "", 7)
    a.text(1.8, 2.7, "laminate sub-gap nodes\n(interior nodes of the rule:\nthey take dS out of the copper)", fontsize=7, ha="center")
    dk.layer(a, 0.3, 0.7, 9.2, 0.3, dk.COPPER, "bottom copper node", 7)
    dk.layer(a, 6.35, 0.7, 0.3, 4.0, "#c47f2c")
    a.text(6.5, 5.0, "plated barrel", ha="center", fontsize=7)
    # Edge band of the rule (cells near the cooled edge) shaded
    a.add_patch(dk.Rectangle((5.2, 0.6), 4.3, 4.2, facecolor="none", edgecolor=dk.BLUE, linestyle="--", linewidth=1.2))
    a.text(7.35, 0.2, "edge band: cells flagged by the rule even under full copper", color=dk.BLUE, fontsize=7, ha="center")
    for y in (1.4, 2.25, 3.1, 3.95):
        dk.arrow(a, 5.3, y, 6.3, y, color=dk.HEAT, width=1.0)
    a.text(4.3, 4.0, "laminate heat\ntowards the wall", color=dk.HEAT, fontsize=6.5, ha="center")
    for y in (1.2, 2.4, 3.6):
        dk.arrow(a, 9.5, y, 10.3, y, color=dk.BLUE, width=1.0)
    a.text(10.0, 4.1, "h_side", color=dk.BLUE, fontsize=7, ha="center")
    a.set_title("Section at a via near a cooled edge (not to scale)", fontsize=9)
    # Bookkeeping: the two orders
    dk.box(b, 0.3, 4.2, 9.4, 1.3, "BEFORE (program): well reads S = S_cu + dS of the laminate\n"
           "G_c = 2 pi S / ln(r_eff / r_t)\nthe copper node keeps S_cu (dS moved to the interior nodes)", "#d8efd0", bold=True, size=7.5)
    dk.box(b, 0.3, 2.4, 9.4, 1.3, "AFTER (tested in memory, lib/order_patch.py): well reads S_cu only\n"
           "the well is softer by dS / S: 0.5 to 1.3 % (full copper), 2.7 to 6.2 % (fill 0.2)", "#f5e0cf", size=7.5)
    dk.box(b, 0.3, 0.4, 9.4, 1.5, "Effect: hottest rise +0.002 to +0.036 K (after - before, FVM);\n"
           "against a resolved 3D barrel: before equal or closer by at most 0.005 K\n-> keep the order, pin it with a test", "#e8e8e8", size=7.5)
    b.set_title("Which sheet the well reads", fontsize=9)
    dk.save(fig, os.path.join(FIG, "fig_01_section_and_order.png"))


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    section()
