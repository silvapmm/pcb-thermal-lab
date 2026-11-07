#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file simple.py
@brief Simple uniform boards for the Lumped ring study: builders and a runner for the program's models.
@details A board is a rectangle with one zone per layer at a given copper fill (fill 1 is a full plane, a smaller fill is the layer-average sheet of an imported board),
         one square source on the top layer at the centre, no vias. Nothing here edits the program.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pcbthermal import Problem, SolverOptions, simulate  # noqa: E402


def board(w_mm=52.0, h_mm=51.0, layers=2, fill=1.0, side_mm=1.0, power=1.0, h_top=10.0, h_bot=15.0, h_side=10.0, thickness_mm=1.6, copper_um=35.0, pos=None):
    """!
    @brief A uniform board with a centred square source on the top layer.
    @param w_mm Width in mm.
    @param h_mm Height in mm.
    @param layers Copper layers.
    @param fill Copper fill of every layer (zone over the whole board).
    @param side_mm Side of the square source in mm.
    @param power Power in W.
    @param h_top Top coefficient W/m2K.
    @param h_bot Bottom coefficient W/m2K.
    @param h_side Edge coefficient W/m2K (None: insulated).
    @param thickness_mm Board thickness in mm.
    @param copper_um Copper thickness in um.
    @param pos (x, y) of the centre in mm (None: the board centre).
    @return Problem.
    """
    p = Problem.new(w_mm, h_mm, layers=layers, thickness_mm=thickness_mm, copper_um=copper_um, h_top=h_top, h_bottom=h_bot, h_side=h_side)
    p.add_full_copper(fill=fill)
    cx, cy = pos if pos is not None else (w_mm / 2, h_mm / 2)
    s = side_mm / 2
    p.add_heater(1, power, rect=(cx - s, cy - s, cx + s, cy + s), name="U")
    return p


def rise(p, model, cell_mm, **opts):
    """!
    @brief Rise of the hottest node of one model above the ambient.
    @param p Problem.
    @param model Model key.
    @param cell_mm Cell in mm.
    @param opts Further SolverOptions fields.
    @return float K.
    """
    r = simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm, **opts)).results[model]
    return r.t_max - p.board.ambient
