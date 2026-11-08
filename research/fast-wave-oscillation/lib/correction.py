#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file correction.py
@brief Prototype of the column correction of the step response of the program (research/fast-wave-oscillation README 5): Z_corrected(t) = Z_program(t) + [Z_exact column(t) - Z_lumped column(t)].

@details Works on a copy of the program's StepResponse (pcbthermal.profiles); nothing of the program is changed. The difference of two one-dimensional columns of the same footprint
area is zero at t = 0 and decays to zero when both columns have reached their (equal) steady state, so the steady resistance and the long-time response are the program's.
"""

import dataclasses

import numpy as np

import axisym_stack as A
import columns as Cn


def column_difference(stack: A.Stack, area: float, h_top: float, h_bottom: float, times: np.ndarray, **kw) -> np.ndarray:
    """!
    @brief dZ(t) = Z_exact(t) - Z_lumped(t) of the two columns.
    @param stack Stack.
    @param area Footprint area in m2.
    @param h_top Top coefficient.
    @param h_bottom Bottom coefficient.
    @param times Times in s.
    @param kw Options of Cn.exact_column (n_cu, n_gap, first).
    @return Array like times in K/W.
    """
    ex = Cn.exact_column(stack, area, h_top, h_bottom, **kw)
    lu = Cn.lumped_column(stack, area, h_top, h_bottom)
    return ex.step(times, "top") - lu.step(times, "top")


def corrected(resp, i: int, dz: np.ndarray):
    """!
    @brief A copy of a profiles.StepResponse whose heater i carries the correction.
    @param resp StepResponse of the program.
    @param i Heater index.
    @param dz Correction on resp.times in K/W.
    @return New StepResponse (the steady resistance is unchanged).
    """
    z = resp.z.copy()
    z[i] = z[i] + dz
    return dataclasses.replace(resp, z=z)


def spreading_factor(stack: A.Stack, area: float, h_top: float, h_bottom: float, times: np.ndarray, z_prog: np.ndarray) -> np.ndarray:
    """!
    @brief Share of the one-dimensional temperature that the board keeps after the lateral spreading, phi(t) = Z_program(t) / Z_lumped column(t), limited to [0, 1].
    @details The program's own step response already contains the spreading; dividing it by the response of its column without spreading gives how much of the column's
             rise survives at each time. The exact-minus-lumped difference of the column is scaled by it (the lateral flow carries away the same share of the extra heat that goes
             into the laminate).
    @param stack Stack.
    @param area Footprint area in m2.
    @param h_top Top coefficient.
    @param h_bottom Bottom coefficient.
    @param times Times in s.
    @param z_prog Step response of the program at those times in K/W.
    @return Array like times in [0, 1].
    """
    lu = Cn.lumped_column(stack, area, h_top, h_bottom)
    return np.clip(z_prog / lu.step(times, "top"), 0.0, 1.0)
