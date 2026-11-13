#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file make_diagrams.py
@brief Diagrams of the imported-via-rim investigation: a signal via through a plane with an antipad (section and plan), the drill-circle test and the ray test.
@details No data, no program: shapes from `research/diagram_kit.py`. Writes `figures/fig_01_antipad_and_ray_test.png`.
         Run from the repository root: `.venv/bin/python research/imported-via-rim/scripts/make_diagrams.py`.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(HERE))
import diagram_kit as dk                                                    # noqa: E402
from matplotlib.patches import Circle                                       # noqa: E402

FIG = os.path.join(HERE, "figures")


def antipad():
    """!
    @brief Section of a two-layer board at a signal via (left) and the plan of the bottom layer with the two rim tests (right).
    @return None.
    """
    fig, (a, b) = dk.canvas(11.0, 4.6, 1, 2, ratios=[1.2, 1.0])
    a.set_xlim(0, 10)
    a.set_ylim(0, 6)
    dk.layer(a, 0.3, 4.6, 9.4, 0.35, dk.COPPER, "top plane (joined to the barrel)", 7)
    dk.layer(a, 0.3, 1.25, 9.4, 3.35, dk.FR4, "", 7)
    dk.layer(a, 0.3, 0.9, 3.4, 0.35, dk.COPPER, "bottom plane", 7)
    dk.layer(a, 6.3, 0.9, 3.4, 0.35, dk.COPPER, "bottom plane", 7)
    dk.layer(a, 4.3, 0.9, 1.4, 0.35, dk.COPPER, "pad", 6.5)
    a.text(3.95, 0.55, "clearance", fontsize=6.5, ha="center", color=dk.BLUE)
    a.text(6.05, 0.55, "clearance", fontsize=6.5, ha="center", color=dk.BLUE)
    dk.layer(a, 4.85, 0.9, 0.3, 4.05, "#c47f2c")
    dk.arrow(a, 5.0, 5.4, 5.0, 4.95, color=dk.HEAT)
    a.text(5.0, 5.55, "heat from the part", fontsize=7, ha="center", color=dk.HEAT)
    dk.arrow(a, 5.0, 1.1, 4.0, 1.75, color=dk.HEAT, width=1.0)
    a.text(2.4, 2.1, "the pad island and the laminate\ntake a little (real path)", fontsize=6.5, color=dk.HEAT, ha="center")
    a.text(7.8, 2.4, "program today with imported copper:\na full well to the bottom plane\n(a ghost path through the clearance)", fontsize=6.5, ha="center", color="k")
    a.set_title("Signal via through a plane with an antipad (section, not to scale)", fontsize=9)
    # Plan of the bottom layer: the pad island, the clearance ring, the plane; the drill circle and rays
    b.set_xlim(-3, 3)
    b.set_ylim(-3, 3)
    b.set_aspect("equal")
    b.add_patch(dk.Rectangle((-3, -3), 6, 6, facecolor=dk.COPPER, edgecolor="none"))
    b.add_patch(Circle((0, 0), 1.65, facecolor=dk.FR4, edgecolor="none"))
    b.add_patch(Circle((0, 0), 0.75, facecolor=dk.COPPER, edgecolor="k", linewidth=0.6))
    b.add_patch(Circle((0, 0), 0.45, facecolor="white", edgecolor="#c47f2c", linewidth=2.0))
    for k in range(8):
        t = (k + 0.5) * 2 * math.pi / 8
        b.plot([0.45 * math.cos(t), 2.0 * math.cos(t)], [0.45 * math.sin(t), 2.0 * math.sin(t)], color=dk.BLUE, linewidth=1.0)
        b.plot(0.45 * math.cos(t), 0.45 * math.sin(t), "o", color="k", markersize=3)
    b.text(0, -2.55, "dots: the 48 samples on the drill circle (all on the pad: share 1)\nlines: rays out to the reach (cut by the clearance: share 0)", fontsize=6.8,
           ha="center", va="center", bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85})
    b.text(0, 2.55, "plan of the bottom layer: plane, clearance, pad", fontsize=7, ha="center", bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85})
    b.set_title("Drill-circle test against the ray test", fontsize=9)
    dk.save(fig, os.path.join(FIG, "fig_01_antipad_and_ray_test.png"))


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    antipad()
