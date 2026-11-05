#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file boards26.py
@brief The boards of the analytic-2-6 studies and the time to 63 % of a step response of any model.

@details Simple boards first: a 60 x 40 mm board with one 10 x 10 mm, 2 W part on layer 1, optionally with a via array under the part and a heatsink (extra
         coefficient on the top face), 2 or 4 layers. The transient reference is the FVM of the program at 1 mm (fvm.step_responses; the API uses at least 2 mm).
"""

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pcbthermal import Problem, fvm, lumped, analytic   # noqa: E402

T0 = 25.0


def plain(layers=2, h_side=None, w=60, h=40, t=1.6, hf=10.0, pos="centre", power=2.0, size=10.0):
    """!
    @brief A full-copper board with one square part on layer 1.
    @param layers Copper layers (35 um).
    @param h_side Edge coefficient in W/m2K (None: insulated).
    @param w Width in mm.
    @param h Height in mm.
    @param t Thickness in mm.
    @param hf Coefficient of both faces in W/m2K.
    @param pos "centre" or "corner".
    @param power Power in W.
    @param size Side of the part in mm.
    @return Problem.
    """
    p = Problem.new(width_mm=w, height_mm=h, layers=layers, thickness_mm=t, copper_um=35.0, ambient=T0, h_top=hf, h_bottom=hf, h_side=h_side)
    for l in range(1, layers + 1):
        p.add_zone(l, rect=(0, 0, w, h))
    x0, y0 = ((w - size) / 2, (h - size) / 2) if pos == "centre" else (0.0, 0.0)
    p.add_heater(1, power, rect=(x0, y0, x0 + size, y0 + size))
    return p


def with_vias(p, n=4, pitch=2.0, d=0.3):
    """!
    @brief Add an n x n via array centred under the part (mm).
    @param p Problem made by plain.
    @param n Vias per side.
    @param pitch Pitch in mm.
    @param d Drill diameter in mm.
    @return The same Problem.
    """
    cx, cy = p.board.width * 500.0, p.board.height * 500.0
    half = pitch * (n - 1) / 2.0
    p.add_via_array((cx - half, cy - half, cx + half, cy + half), n, n, diameter=d)
    return p


def with_sink(p, h_extra=100.0, where="under", size=20.0):
    """!
    @brief Add a heatsink (extra coefficient on layer 1) under the part or at the far end of the board.
    @param p Problem made by plain.
    @param h_extra Added coefficient in W/m2K.
    @param where "under" (centred, size mm square) or "side" (the right-hand quarter of the board).
    @param size Side of the square in mm.
    @return The same Problem.
    """
    w, h = p.board.width * 1000.0, p.board.height * 1000.0
    if where == "under":
        p.add_heatsink(1, h_extra, rect=((w - size) / 2, (h - size) / 2, (w + size) / 2, (h + size) / 2))
    else:
        p.add_heatsink(1, h_extra, rect=(0.7 * w, 0.0, w, h))
    return p


def t63(times, z, rth):
    """!
    @brief Time to 63.2 % of the steady resistance (log-time interpolation) for every heater.
    @param times Array (nt,) in seconds.
    @param z Array (nh, nt) of the unit-step responses in K/W.
    @param rth Array (nh,) of the steady resistances in K/W.
    @return Array (nh,) in seconds (nan if not reached).
    """
    out = []
    for zi, r in zip(np.atleast_2d(z), np.atleast_1d(rth)):
        target = (1.0 - math.exp(-1.0)) * float(r)
        if not (zi >= target).any():
            out.append(float("nan"))
            continue
        k = int(np.argmax(zi >= target))
        if k == 0:
            out.append(float(times[0] * target / zi[0]))
            continue
        f = (target - zi[k - 1]) / (zi[k] - zi[k - 1])
        out.append(float(math.exp(math.log(times[k - 1]) + f * (math.log(times[k]) - math.log(times[k - 1])))))
    return np.array(out)


def step(p, model, cell=1.0):
    """!
    @brief Step response of a model.
    @param p Problem.
    @param model "fvm", "lumped" or "analytic".
    @param cell Cell in mm.
    @return Tuple (times, z, rth).
    """
    if model == "fvm":
        return fvm.step_responses(p, cell_mm=cell)
    if model == "lumped":
        return lumped.step_responses(p, cell_mm=max(cell, 0.5))
    return analytic.step_responses(p, cell_mm=max(cell, 0.5))
