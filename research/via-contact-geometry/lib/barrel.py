#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file barrel.py
@brief The barrel length rule as a patch in memory: the conductance of the barrel over each gap becomes k A / (d + a t_cu), a the "extra length" in units of the copper thickness.
@details The program counts the barrel over the dielectric gap d only (viawell.build: gv = k_cu A / d) and crosses the copper nodes with no resistance. `patched(a)` wraps
         viawell.build so that the barrel conductances handed to the Kron reduction are scaled by d / (d + a * t), t the mean of the thicknesses of the two copper layers on either
         side of the gap. a = 0 is the program. Nothing of the program is edited; the wrapper is removed on exit.
"""

import contextlib

import numpy as np

from pcbthermal import viawell as vw

_ORIG_BUILD = vw.build
_ORIG_KRON = vw.kron_barrel


@contextlib.contextmanager
def patched(a):
    """!
    @brief Install the barrel rule with extra length a * t_cu per gap for the duration of a with-block.
    @param a Extra length per gap in units of the copper thickness (0: the program).
    @return context manager.
    """
    if a == 0.0:
        yield
        return
    state = {"scale": None}

    def kron(g_gap, g_well):
        """!
        @brief kron_barrel with the barrel conductances scaled.
        @param g_gap Barrel conductance of every gap in W/K.
        @param g_well Well conductances in W/K.
        @return numpy.ndarray.
        """
        return _ORIG_KRON(np.asarray(g_gap) * state["scale"], g_well)

    def build(problem, d, S, cover, dx, dy, nx, ny, origin, active):
        """!
        @brief viawell.build with the scale set from the problem.
        @param problem The Problem.
        @param d Gap thicknesses in m.
        @param S Sheet conductances.
        @param cover Board share of every cell.
        @param dx Cell size x in m.
        @param dy Cell size y in m.
        @param nx Cells along x.
        @param ny Cells along y.
        @param origin Lower x edge in m.
        @param active Cells on the board.
        @return the program's tuple.
        """
        t = np.asarray(problem.board.copper_thickness, dtype=float)
        t_gap = 0.5 * (t[:-1] + t[1:])
        state["scale"] = np.asarray(d) / (np.asarray(d) + a * t_gap)
        return _ORIG_BUILD(problem, d, S, cover, dx, dy, nx, ny, origin, active)

    vw.build, vw.kron_barrel = build, kron
    try:
        yield
    finally:
        vw.build, vw.kron_barrel = _ORIG_BUILD, _ORIG_KRON
