#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file boards.py
@brief The test boards of the study: the 20 mm square of the finite-element comparison with or without an explicit outline, the 10 mm strong-edge plate, and the readers.
@details All boards are built through the program's public API. The square is the `sq_in` / `sq_wall` board of `research/imported-copper-edge-film` (2 layers, 35 um copper,
         h_top = h_bottom = 10 W/m2K, a 4 mm heater of 1 W at the centre, copper `inset` mm inside the wall) but kept aligned with the grid (no turn, no shift), so that the
         plain edge and the cut-cell treatment of an outline can be told apart: `outline=False` leaves the board a plain rectangle (no outline polygon), `outline=True` gives
         the same rectangle as an explicit outline (exact cover, cut-cell links of the FVM). The finite-element limits of an independent finite-element comparison are quoted in `FEM_*`.
"""

import logging
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(1, os.path.join(ROOT, "research", "strong-edge-laminate", "lib"))

from pcbthermal import Problem, analysis                       # noqa: E402

logging.disable(logging.WARNING)

# Finite-element limits of an independent finite-element comparison (Richardson extrapolation of conforming meshes; quoted, not re-run here)
FEM_SQUARE_INSET = {10.0: 124.551, 200.0: 57.201, 1000.0: 38.972}        # 20 mm square, copper 1.2 mm in, heater mean rise (K)
FEM_SQUARE_WALL = {200.0: 50.635, 1000.0: 30.114}                        # copper to the wall
FEM_PLATE_WALL = {10.0: 51.687, 200.0: 36.981, 1000.0: 24.332}           # 10 mm plate hottest rise (K)
FEM_PLATE_INSET = {10.0: 53.406, 200.0: 41.826, 1000.0: 33.906}          # copper 0.5 mm in


def square(h_side, inset=1.2, outline=False, side=20.0, heater=4.0):
    """!
    @brief The aligned 20 mm two-layer square.
    @param h_side Edge coefficient W/m2K.
    @param inset Copper inset from the wall in mm (0: copper to the wall).
    @param outline True to give the board an explicit rectangular outline polygon.
    @param side Side in mm.
    @param heater Heater side in mm.
    @return Problem.
    """
    p = Problem.new(side, side, 2, h_side=h_side)
    p.board.h_top = p.board.h_bottom = 10.0
    c, hh = side / 2, heater / 2
    p.add_heater(1, 1.0, rect=(c - hh, c - hh, c + hh, c + hh), name="U")
    if outline:
        p.set_outline([[0, 0], [side, 0], [side, side], [0, side]])
    for k in (1, 2):
        p.add_zone(k, rect=(inset, inset, side - inset, side - inset))
    return p


def plate(h_side, inset=0.0, via_dist=None):
    """!
    @brief The 10 mm four-layer strong-edge plate of `research/strong-edge-laminate`.
    @param h_side Edge coefficient W/m2K.
    @param inset Copper inset in mm.
    @param via_dist Distance of the via from the right edge in mm (None: no via).
    @return Problem.
    """
    import prog
    return prog.board(h_side, via_dist, inset_mm=inset)


def read(model, problem, cell, kind="max", **kw):
    """!
    @brief Run a model module's `solve_steady` and read the hottest or the heater-mean rise.
    @param model Module with `solve_steady(problem, cell_mm, **kw)` (pcbthermal.fdm, pcbthermal.fvm or a variant).
    @param problem Problem.
    @param cell Cell in mm.
    @param kind "max" (hottest) or "mean" (mean of the first heater, face value).
    @param kw Extra arguments of `solve_steady`.
    @return float rise in K.
    """
    r = model.solve_steady(problem, cell, **kw)
    if kind == "max":
        return float(r.t_max - problem.board.ambient)
    return float(analysis.heater_stats(r, problem)[0]["t_mean"] - problem.board.ambient)


def err(a, ref):
    """!
    @brief Percent error.
    @param a Value.
    @param ref Reference.
    @return float.
    """
    return float((a / ref - 1.0) * 100.0)


__all__ = ["square", "plate", "read", "err", "np"]
