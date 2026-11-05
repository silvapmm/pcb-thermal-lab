#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cases.py
@brief The boards of the study and the references that judge them (FVM, 3D with side convection).

@details Uniform boards with full copper on every layer (35 um), a 10 mm square part of 2 W at the centre, in a corner or at the middle of an edge, faces 10 W/m2K
         unless said otherwise, the edge coefficient swept. The references are the FVM of the program at 0.5 mm (the layered model resolved, section 4 of
         docs/validation.md shows it converged to 1/24 mm within 0.4 %) and the independent 3D solver layered3d_side.py (the real stack, the side film on every slab).
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pcbthermal import Problem, SolverOptions, simulate   # noqa: E402
import layered3d_side                                      # noqa: E402

T0 = 25.0


def board(w, h, layers, t, h_side, pos="centre", hf=10.0, size=10.0, power=2.0):
    """!
    @brief A uniform board of the study.
    @param w Width in mm.
    @param h Height in mm.
    @param layers Copper layers (35 um each, full copper).
    @param t Thickness in mm.
    @param h_side Edge coefficient in W/m2K (None = insulated).
    @param pos "centre", "corner" or "edge" (middle of the bottom edge) for the part.
    @param hf Coefficient of both faces in W/m2K.
    @param size Side of the square part in mm.
    @param power Power in W.
    @return Tuple (Problem, (x0, y0) corner of the part in mm).
    """
    p = Problem.new(width_mm=w, height_mm=h, layers=layers, thickness_mm=t, copper_um=35.0, ambient=T0, h_top=hf, h_bottom=hf, h_side=h_side)
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, w, h))
    if pos == "centre":
        x0, y0 = (w - size) / 2, (h - size) / 2
    elif pos == "corner":
        x0, y0 = 0.0, 0.0
    else:
        x0, y0 = (w - size) / 2, 0.0
    p.add_heater(1, power, rect=(x0, y0, x0 + size, y0 + size))
    return p, (x0, y0)


def rise(p, model, cell):
    """!
    @brief Hottest rise of one program model.
    @param p Problem.
    @param model Model key.
    @param cell Cell in mm.
    @return float Rise in K.
    """
    return simulate(p, SolverOptions(cell_mm=cell, models=(model,))).results[model].t_max - T0


def ref3d(p, pos, dx_mm=1.0, size=10.0, sub=4):
    """!
    @brief Hottest rise of the independent 3D solver for a board made by `board`.
    @param p Problem made by `board`.
    @param pos Corner (x0, y0) of the part in mm.
    @param dx_mm Cell in the plane in mm.
    @param size Side of the part in mm.
    @param sub Sub-slabs per dielectric gap.
    @return float Rise in K.
    """
    b = p.board
    w, h, layers = int(round(b.width * 1000 / dx_mm)), int(round(b.height * 1000 / dx_mm)), b.layers
    gaps = b.gap_thicknesses()
    slabs = []
    for k in range(layers):
        slabs.append((35e-6, 385.0, 385.0, 1))
        if k < layers - 1:
            slabs.append((float(gaps[k]), 0.9, 0.3, sub))
    x0, y0 = pos
    top, _ = layered3d_side.solve_3d(dx_mm * 1e-3, w, h, slabs, (x0 * 1e-3, y0 * 1e-3, (x0 + size) * 1e-3, (y0 + size) * 1e-3), p.total_power(), b.h_top, b.h_side or 0.0)
    return float(top.max())
