#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file warnrule.py
@brief Prototype of the live warning for a via whose footprint covers a plane with copper over only part of it.
@details The rule reads the footprint the FVM would use for the via (`viawell.footprint`, the disc enlarged to the target radius, on the cells of the run), and for every copper layer
         the sheet conductance per unit of board of the cells that carry at least `MIN_SHARE` of the footprint weight. The footprint is "partial" in a layer when the smallest of those
         values is below `RATIO` times the largest (a copper edge, a track end, a clearance, a hatch crossing the footprint). The message is about the via effect being misread (either
         way: the research found the program 30 to 60 % too small on a copper edge or a track and several times too large for a via just off a copper edge), not about the cold spot,
         because at a coarse cell there is no cold spot and the via effect is still wrong.
@note A prototype in the research folder: it is the proposal of INTEGRATION.md, to be written into `pcbthermal/checks.py` on a `fix/` branch; it imports the program and edits nothing.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np                                                            # noqa: E402

from pcbthermal import fvm                                                    # noqa: E402
from pcbthermal import viawell as vw                                          # noqa: E402

MIN_SHARE = 0.05          # a cell takes part when it holds at least this share of the largest footprint weight
RATIO = 0.5               # partial when a participating cell has less than this share of the sheet conductance of the best one


def partial_vias(problem, cell_mm):
    """!
    @brief Indices of the vias whose footprint is partial in some layer, at a cell size.
    @param problem Problem.
    @param cell_mm Cell size in mm.
    @return List of (via index, layer index, ratio of the smallest to the largest sheet conductance in the footprint).
    """
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    net = fvm.Network(problem, nx, ny, assemble=False)
    out = []
    cover = net.cover
    rel = [np.where(cover > 0, net.S[l] / np.where(cover > 0, cover, 1.0), 0.0) for l in range(b.layers)]
    for k, (v, share) in enumerate(zip(problem.vias, problem.via_board_shares())):
        if share <= 0:
            continue
        w, _, _ = vw.footprint(v.x, v.y, v.diameter / 2.0, net.dx, 0.0, cover, net.dy, 0.0)
        if not w:
            continue
        wmax = max(w.values())
        cells = [c for c, x in w.items() if x >= MIN_SHARE * wmax]
        for l in range(b.layers):
            vals = [rel[l][c] for c in cells]
            if min(vals) < RATIO * max(vals):
                out.append((k, l, min(vals) / max(vals)))
    return out
