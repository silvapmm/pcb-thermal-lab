#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file sublayers.py
@brief Option B prototype without editing the program: a thick metal plate as a stack of N copper layers joined by vertical links of the plate's own conductivity.
@details The layered models (FVM, FDM, Lumped, Analytic) accept an advanced stack-up: N copper layers and N-1 dielectric gaps. A gap whose conductivity through the thickness is that
         of the metal and whose thickness is the sub-layer thickness t/N is a vertical link of resistance (t/N)/(k A), which is exactly the link between two sub-layer nodes
         spaced t/N apart (the program joins two layer nodes by the gap alone; the half copper layers are the thin-copper approximation it makes, and here the half sub-layers
         are carried by the gap, so the chain is exact). The in-plane conductivity of the gap is set to a negligible value (the sub-layers carry the lateral heat), and the
         face films see half a sub-layer (Board.face_film_h with the sub-layer thickness). N = 1 is the plate as the program holds it today (one layer, a laminate of 1 micrometre).
         The cost in the program would be the same as this emulation: N times the unknowns of the plate.
"""

import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from pcbthermal import Problem  # noqa: E402
from pcbthermal.model import Dielectric, Materials  # noqa: E402


def stack_problem(n, width_mm, height_mm, t_mm, k, h_bottom, h_top=1e-6, sources=(), ambient=25.0):
    """!
    @brief A plate of thickness t and conductivity k cut into n sub-layers, as a Problem of the program.
    @param n Number of sub-layers through the thickness (1 is the plate as one layer).
    @param width_mm Plate width in mm.
    @param height_mm Plate height in mm.
    @param t_mm Plate thickness in mm.
    @param k Conductivity of the metal in W/mK.
    @param h_bottom Film coefficient of the bottom face in W/m2K.
    @param h_top Film coefficient of the top face outside the sources in W/m2K (1e-6: adiabatic).
    @param sources Iterable of (rect (x0, y0, x1, y1) in mm, power in W) on the top face (sub-layer 1).
    @param ambient Ambient temperature in degC.
    @return Problem.
    """
    ts = t_mm / n
    if n == 1:
        p = Problem.new(width_mm, height_mm, layers=1, thickness_mm=1.0001 * t_mm, copper_um=t_mm * 1e3, ambient=ambient, h_top=h_top, h_bottom=h_bottom, h_side=None,
                        materials=Materials(k_copper=k))
    else:
        p = Problem.new(width_mm, height_mm, layers=n, thickness_mm=(2 * n - 1) * ts, copper_um=ts * 1e3, ambient=ambient, h_top=h_top, h_bottom=h_bottom, h_side=None,
                        materials=Materials(k_copper=k))
        p.board.dielectrics = [Dielectric(thickness=ts * 1e-3, name="metal link", k_through=k, k_inplane=1e-9, rho=8900.0, cp=385.0) for _ in range(n - 1)]
    p.add_full_copper(layers=None)
    for i, (rect, pw) in enumerate(sources):
        p.add_heater(1, pw, rect=rect, name=f"S{i}")
    return p
