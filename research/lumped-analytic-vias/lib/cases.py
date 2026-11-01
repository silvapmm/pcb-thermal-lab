#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cases.py
@brief The simple boards of the study, each isolating one effect, and the 4-layer thermal-pad boards used as the step towards real boards.
@details Every board is square, with full 35 um copper on every layer, FR-4 0.3 W/mK, insulated edges, a square source on the top copper, vias of one drill:
         * `unit_cell`   (from research/point-via-convergence): the periodic cell of a via lattice; ONLY the constriction of the heat converging on a barrel is present;
         * `lone_via` / `row`  (same origin): a via, or a row of five, beside a 3 mm source on a 16 mm board; adds the lateral gradient and the position of the via relative to the
                          source (rings of the Lumped model, tiles of the Analytic one);
         * `array`       a n x n array under a square source on a board of 21 mm (the via-fill board, with the number of layers as a parameter); adds the neighbour interaction of
                          the vias inside the footprint, the lattice pitch from 3.5 mm (the example board) down to 1 mm (the usual thermal pad) and the stack-up (2, 4, 6 layers);
         * `pad`         a thermal pad: n x n array under a QFN-like source on a 30 mm board with a heatsink-free bottom, used for the sweep of the dense array.
         The reference of each is `harness.reference_uniform`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "research", "point-via-convergence", "lib"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import program_cases as pc                                                   # noqa: E402
from pcbthermal import Problem                                               # noqa: E402
from pcbthermal.model import Materials                                       # noqa: E402

unit_cell = pc.unit_cell_board
lone_via = pc.lone_via_board
row = pc.row_board


def array(layers=4, n=3, pitch_mm=3.5, diameter_mm=0.3, fill_k=0.0, side_mm=21.0, source_mm=10.0, power=2.0, thickness=1.6, h_top=10.0, h_bottom=200.0, offset_mm=(0.0, 0.0)):
    """!
    @brief An n x n via array under a square source on a board of full copper planes.
    @param layers Copper layers (2, 4, 6, ...).
    @param n Vias per side.
    @param pitch_mm Via pitch in mm.
    @param diameter_mm Drill in mm.
    @param fill_k Fill conductivity in W/mK (0 = open barrel, 385 = copper).
    @param side_mm Board side in mm.
    @param source_mm Side of the source in mm.
    @param power Power of the source in W.
    @param thickness Board thickness in mm.
    @param h_top Top film in W/m2K.
    @param h_bottom Bottom film in W/m2K.
    @param offset_mm Shift of the array from the centre of the board in mm.
    @return Problem.
    """
    c = side_mm / 2
    p = Problem.new(side_mm, side_mm, layers, thickness, 35.0, h_top=h_top, h_bottom=h_bottom, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, side_mm, side_mm))
    p.add_heater(1, power, rect=(c - source_mm / 2 + offset_mm[0], c - source_mm / 2 + offset_mm[1], c + source_mm / 2 + offset_mm[0], c + source_mm / 2 + offset_mm[1]))
    h = (n - 1) / 2
    for i in range(n):
        for j in range(n):
            p.add_via(c + (i - h) * pitch_mm + offset_mm[0], c + (j - h) * pitch_mm + offset_mm[1], diameter_mm, fill_k=fill_k)
    return p


def pad(layers=4, n=5, pitch_mm=1.2, diameter_mm=0.3, fill_k=0.0, side_mm=30.0, source_mm=6.0, power=3.0, h_bottom=200.0):
    """!
    @brief A thermal pad: n x n vias at a dense pitch under a small source, on a larger board (the typical QFN/MOSFET pad).
    @param layers Copper layers.
    @param n Vias per side.
    @param pitch_mm Via pitch in mm.
    @param diameter_mm Drill in mm.
    @param fill_k Fill conductivity.
    @param side_mm Board side in mm.
    @param source_mm Side of the source in mm.
    @param power Power in W.
    @param h_bottom Bottom film in W/m2K.
    @return Problem.
    """
    return array(layers, n, pitch_mm, diameter_mm, fill_k, side_mm, source_mm, power, 1.6, 10.0, h_bottom)
