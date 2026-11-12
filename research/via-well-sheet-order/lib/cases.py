#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cases.py
@brief The boards of the via-well-order study and the runs of the program with the sheet read before (today) and after the laminate rule.
@details Board: 10 x 10 mm, `layers` copper planes of 35 um, 1.6 mm, FR-4 0.3 / 0.3 W/mK (the boards of via-edge-image), a 0.5 W source of 3 x 2 mm at (1..4, 4..6) mm on the top
         layer, h 10 W/m2K on top and 200 below, edge film `h_side`, copper fill `fill` on every layer (1 = full copper, below 1 = a hatched zone), vias at `distance` mm from the right
         edge (one via, or a 2 x 2 block at a 0.8 mm pitch). The program is imported, never edited; `order_patch.after()` makes the wells read the reduced sheet.
"""

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESEARCH = os.path.dirname(HERE)
for extra in (os.path.join(HERE, "lib"), os.path.join(RESEARCH, "point-via-convergence", "lib")):
    if extra not in sys.path:
        sys.path.insert(0, extra)
REPO = os.path.dirname(RESEARCH)
if REPO not in sys.path:
    sys.path.append(REPO)

import order_patch                                                          # noqa: E402
import program_cases as pc                                                  # noqa: E402
from pcbthermal import Problem                                              # noqa: E402
from pcbthermal.model import Materials                                      # noqa: E402

W_MM = 10.0


def board(layers=4, fill=1.0, h_side=10.0, distance=1.0, vias="one", fill_k=385.0, with_via=True, power=0.5):
    """!
    @brief One test board.
    @param layers Copper layers (2 or 4).
    @param fill Copper fill of every layer (1 = whole zone).
    @param h_side Edge film in W/m2K (None: insulated).
    @param distance Distance of the via (the nearest via of a block) from the right edge in mm.
    @param vias "one" or "block" (2 x 2 at 0.8 mm pitch, the nearest column at `distance`).
    @param fill_k Via fill conductivity in W/mK (385 copper-filled, 0 open barrel).
    @param with_via False: the board without vias.
    @param power Source power in W.
    @return Problem.
    """
    w = W_MM
    p = Problem.new(w, w, layers, 1.6, 35.0, h_top=10.0, h_bottom=200.0, h_side=h_side or None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, w, w), fill=fill)
    p.add_heater(1, power, rect=(1, 4, 4, 6))
    if with_via:
        x = w - distance
        if vias == "one":
            p.add_via(x, 5.0, 0.3, fill_k=fill_k)
        else:
            for dx in (0.0, -0.8):
                for y in (4.6, 5.4):
                    p.add_via(x + dx, y, 0.3, fill_k=fill_k)
    return p


def rise(p, cell, model="fvm", order="before"):
    """!
    @brief Maximum rise of a model with the via wells reading the sheet before or after the laminate rule.
    @param p Problem.
    @param cell Cell in mm.
    @param model Model key (fvm or fdm).
    @param order "before" (today's program) or "after".
    @return float rise over the ambient in K.
    """
    if order == "after":
        with order_patch.after():
            return pc.max_rise(p, model, cell)
    return pc.max_rise(p, model, cell)
