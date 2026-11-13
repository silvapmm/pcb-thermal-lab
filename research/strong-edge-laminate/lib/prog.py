#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file prog.py
@brief The 10 x 10 mm, four-layer test board of the edge study built in the program, and its run with chosen laminate options.
@details Same board as `lib/ref3d.py` (full or inset copper on the four layers, 35 um, FR-4 0.3 W/mK in plane and through, h_top 10, h_bottom 200 W/m2K, a 0.5 W source of 3 x 2 mm
         on the top layer at (1..4, 4..6) mm, one copper-filled via of 0.3 mm at a given distance from the right edge on the line y = 5 mm). Only the program's public API is used.
"""

import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if REPO not in sys.path:
    sys.path.append(REPO)

from pcbthermal import Problem, SolverOptions, simulate          # noqa: E402
from pcbthermal import model as pmodel                           # noqa: E402
from pcbthermal.model import Materials                           # noqa: E402

logging.disable(logging.WARNING)
W_MM = 10.0


def board(h_side, via_dist_mm=None, inset_mm=0.0, diameter_mm=0.3, power=0.5):
    """!
    @brief Build the test board.
    @param h_side Edge film coefficient in W/m2K.
    @param via_dist_mm Distance of the via centre from the right edge in mm (None: no via).
    @param inset_mm Copper inset from all four edges in mm (0: the copper reaches the edge).
    @param diameter_mm Drill diameter in mm.
    @param power Source power in W.
    @return Problem.
    """
    pmodel.reload_libraries()
    w = W_MM
    p = Problem.new(w, w, 4, 1.6, 35.0, h_top=10.0, h_bottom=200.0, h_side=h_side, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, 5):
        p.add_zone(layer, rect=(inset_mm, inset_mm, w - inset_mm, w - inset_mm))
    p.add_heater(1, power, rect=(1, 4, 4, 6))
    if via_dist_mm is not None:
        p.add_via(w - via_dist_mm, 5.0, diameter_mm, fill_k=385.0)
    return p


GAP_MM = (1.6 - 4 * 0.035) / 3                                  # dielectric gap of the board in mm


def run(problem, cell_mm, n_sub=None, model="fvm"):
    """!
    @brief Hottest rise of one model with a chosen number of laminate sub-gaps.
    @details `n_sub=None` runs the shipped defaults (s_max 0.4 mm, n_max 4: the 0.487 mm gaps of this board get 2 sub-gaps). A number sets `laminate.using` to give exactly that many
             sub-gaps in every gap, also beyond the public range of the options (s_max >= 0.05 mm, n_max <= 16), by overriding `laminate_params` of the options instance.
    @param problem The Problem.
    @param cell_mm Cell size in mm.
    @param n_sub Sub-gaps per gap (None: the defaults).
    @param model Model key.
    @return float maximum rise over the ambient in K.
    """
    opts = SolverOptions(models=(model,), cell_mm=cell_mm)
    if n_sub is not None:
        s = GAP_MM / n_sub * 1.001 * 1e-3                      # ceil(d / s) = n_sub
        opts.laminate_params = lambda: (s, int(n_sub))
    res = simulate(problem, opts).results[model]
    return float(res.t_max - problem.board.ambient)
