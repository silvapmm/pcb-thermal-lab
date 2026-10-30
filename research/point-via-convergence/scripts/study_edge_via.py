#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge_via.py
@brief Does the recommended treatment behave next to a board edge or an outline, and what does a footprint cost? (README 8, review.)
@details A 10 x 10 mm four-plane board (full copper, FR-4 0.3 W/mK, h 10 / 200 W/m2K, 0.5 W in a 3 x 2 mm source), one 0.3 mm copper-filled via 0.16 mm from the right
         edge: either the edge of the box (x = 10 mm) or an outline that cuts the box at x = 7.03 mm (an edge between grid lines). Via effect E = T_max(no via) - T_max(via)
         for the program and for `mw_disc@eta` at 1 to 0.0625 mm. Then the time to build the footprint of one via (`viakernel.disc_target_weights`) at each cell.
         Written by the review. Run from the repository root: `.venv/bin/python research/point-via-convergence/scripts/study_edge_via.py` (about one minute).
"""

import logging
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import program_cases as pc                                                  # noqa: E402
import program_patch as pp                                                  # noqa: E402
import viakernel as vk                                                      # noqa: E402
from pcbthermal import Problem                                              # noqa: E402
from pcbthermal.model import Materials                                      # noqa: E402

ETA = math.exp(-0.25)
CELLS = (1.0, 0.5, 0.25, 0.125, 0.0625)


def board(outline, with_via=True, distance=0.16):
    """!
    @brief The test board.
    @param outline True: the outline cuts the box at x = 7.03 mm; False: the edge of the box at 10 mm.
    @param with_via False: the board without the via.
    @param distance Distance of the via centre from the edge in mm.
    @return Problem.
    """
    w = 10.0
    p = Problem.new(w, w, 4, 1.6, 35.0, h_top=10.0, h_bottom=200.0, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, 5):
        p.add_zone(layer, rect=(0, 0, w, w))
    edge = w
    if outline:
        p.set_outline([(0, 0), (7.03, 0), (7.03, w), (0, w)])
        edge = 7.03
    p.add_heater(1, 0.5, rect=(1, 4, 4, 6))
    if with_via:
        p.add_via(edge - distance, 5.0, 0.3, fill_k=385.0)
    return p


def main():
    """!
    @brief Print the via effect against the cell and the cost of a footprint.
    @return None.
    """
    logging.disable(logging.WARNING)
    pc.load_libraries()
    print("| edge | treatment | " + " | ".join(f"{c} mm" for c in CELLS) + " |")
    print("| :-- | :-- | " + " | ".join("--:" for _ in CELLS) + " |")
    for outline in (False, True):
        prog, mw = [], []
        for c in CELLS:
            t_no = pc.max_rise(board(outline, False), "fvm", c)
            prog.append(t_no - pc.max_rise(board(outline), "fvm", c))
            with pp.patched("mw_disc", eta=ETA):
                mw.append(t_no - pc.max_rise(board(outline), "fvm", c))
        name = "outline at 7.03 mm" if outline else "box edge"
        print(f"| {name} | program | " + " | ".join(f"{e:.2f}" for e in prog) + " |")
        print(f"| {name} | mw_disc@eta | " + " | ".join(f"{e:.2f}" for e in mw) + " |", flush=True)
    print()
    for c in CELLS:
        dx = c * 1e-3
        t0 = time.perf_counter()
        for k in range(20):
            w = vk.disc_target_weights(10e-3 + k * 0.037e-3, 10e-3 + k * 0.011e-3, 0.15e-3, ETA * 0.15e-3, dx)
        print(f"footprint at {c} mm: {len(w)} cells, {(time.perf_counter() - t0) / 20 * 1e3:.2f} ms per via")


if __name__ == "__main__":
    main()
