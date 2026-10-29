#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file calculator_calibration_study.py
@brief How to reduce the error of the power calculator when the drawn board is not exactly the real one: a known-power reference, two measurement points, an uncertainty band.

@details The real board is the example board with U1 at 2 W (theta 6 K/W, psi_JT 2 K/W); the "measurements" are made on it. The calculator then works on a drawn board that
         has the wrong copper (as in power_from_top_study.py). Three ways to cope are tried:
         A. **Known-power reference**: the same thermocouple is read with the part at a known power (a dummy load, or the part in a known state), and the model is scaled so that it
            reproduces that reading before the unknown power is looked for. It does not need the copper at all, only the linearity of the board.
         B. **Two measurement points**: two board temperatures at different distances from the part give the power and a copper multiplier at the same time (two equations, two
            unknowns): how fast the temperature falls with distance tells how well the board spreads heat, and the level tells the power.
         C. **An uncertainty band**: the calculator is run with the copper and the heat transfer at the ends of their uncertainty and the range of powers is reported
            (the band of the program, inverse.power_band, with theta, psi_JT and the reading too, is printed by study_power_band.py).
         The plain calculator here inverts a board point 1 mm from the part by bisection, because inverse.power_from_temperature has no point at a given distance.
         Error = recovered power / 2 W - 1.

Usage: python research/power-calculator/scripts/calculator_calibration_study.py
"""

import copy
import os
import sys

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pcbthermal import SolverOptions                                        # noqa: E402
from pcbthermal.api import _run_model                                       # noqa: E402
from pcbthermal.examples import example_board                               # noqa: E402

P_TRUE, THETA = 2.0, 6.0
OPTIONS = SolverOptions(models=("fvm",), cell_mm=1.0)


def true_board():
    """!
    @brief The real board: the example with U1 at 2 W and U2 off.
    @return Problem.
    """
    p = example_board()
    p.heaters[0].power, p.heaters[0].theta = P_TRUE, THETA
    p.heaters[1].power, p.heaters[1].theta = 0.0, 0.0
    return p


def with_copper(problem, factor):
    """!
    @brief A copy whose copper (thickness of every layer) is multiplied by a factor.
    @param problem Problem.
    @param factor Multiplier of the copper thickness.
    @return Problem.
    """
    q = copy.deepcopy(problem)
    q.board.copper_thickness = [t * factor for t in q.board.copper_thickness]
    return q


def board_temps(problem, power, offsets_mm=(1.0, 10.0)):
    """!
    @brief Temperature of the top layer at given distances to the right of the footprint edge of U1, with U1 at a given power.
    @param problem Problem.
    @param power U1 power in W.
    @param offsets_mm Distances from the right edge of the footprint in mm.
    @return Array of temperatures in degC.
    """
    q = copy.deepcopy(problem)
    q.heaters[0].power = power
    res = _run_model(q, "fvm", OPTIONS)
    x_edge = q.heaters[0].polygon[:, 0].max()
    y_mid = q.heaters[0].polygon[:, 1].mean()
    iy = int(y_mid // res.dy)
    return np.array([res.T[0, iy, int((x_edge + d * 1e-3) // res.dx)] for d in offsets_mm])


def main():
    """!
    @brief Print the three mitigation tables.
    """
    real = true_board()
    t_ring_real = board_temps(real, P_TRUE)                       # Two thermocouples, 1 mm and 10 mm from the part
    ref_power = 1.0
    t_ref_real = board_temps(real, ref_power)                      # The same two thermocouples with a known 1 W reference
    wrong = {"correct board": 1.0, "copper 0.5 x": 0.5, "copper 0.25 x": 0.25}
    print("A and B: error of the recovered power for a drawn board whose copper is a factor of the real one\n")
    print("| Drawn board | plain calculator (1 mm point) | A. known-power reference (1 W) | B. two points (1 and 10 mm) fit P and copper |")
    print("| :-- | --: | --: | --: |")
    for label, f in wrong.items():
        drawn = with_copper(real, f)
        # Plain: invert the 1 mm board point on the drawn board by bisection on the power (inverse.py has no point at a given distance)
        lo, hi = 0.05, 20.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if board_temps(drawn, mid)[0] < t_ring_real[0] else (lo, mid)
        plain = 0.5 * (lo + hi)
        # A: scale the model so that it reads the reference as measured, then invert
        k_ref = (t_ref_real[0] - real.board.ambient) / (board_temps(drawn, ref_power)[0] - real.board.ambient)
        lo, hi = 0.05, 20.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            model_rise = (board_temps(drawn, mid)[0] - real.board.ambient) * k_ref
            lo, hi = (mid, hi) if model_rise < t_ring_real[0] - real.board.ambient else (lo, mid)
        pa = 0.5 * (lo + hi)

        # B: unknowns (P, copper multiplier m) from the two readings
        def residual(x):
            p, m = x
            return (board_temps(with_copper(drawn, m), p) - t_ring_real) / 5.0
        sol = least_squares(residual, x0=[1.0, 1.0], bounds=([0.05, 0.1], [20.0, 10.0]), diff_step=0.02)
        pb = sol.x[0]
        print(f"| {label} | {100 * (plain / P_TRUE - 1):+.1f} % | {100 * (pa / P_TRUE - 1):+.1f} % | {100 * (pb / P_TRUE - 1):+.1f} % (copper x{sol.x[1]:.2f} of the drawn) |", flush=True)
    print("\nA and B with +/-1 K of error on each thermocouple (worst combination of signs), drawn board with half the copper")
    print("| Error on the readings | plain calculator | A. known-power reference | B. two points |")
    print("| :-- | --: | --: | --: |")
    drawn = with_copper(real, 0.5)
    amb = real.board.ambient
    for sign in ((0, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        e = np.array(sign, dtype=float)                                      # Error of the 1 mm and the 10 mm reading, K
        t_meas = t_ring_real + e
        t_ref = t_ref_real + e                                               # The reference readings carry the same error (same thermocouples)
        lo, hi = 0.05, 20.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if board_temps(drawn, mid)[0] < t_meas[0] else (lo, mid)
        plain = 0.5 * (lo + hi)
        k_ref = (t_ref[0] - amb) / (board_temps(drawn, ref_power)[0] - amb)
        lo, hi = 0.05, 20.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if (board_temps(drawn, mid)[0] - amb) * k_ref < t_meas[0] - amb else (lo, mid)
        pa = 0.5 * (lo + hi)
        sol = least_squares(lambda x: (board_temps(with_copper(drawn, x[1]), x[0]) - t_meas) / 5.0, x0=[1.0, 1.0], bounds=([0.05, 0.1], [20.0, 10.0]), diff_step=0.02)
        print(f"| {'none' if sign == (0, 0) else f'{sign[0]:+d} K at 1 mm, {sign[1]:+d} K at 10 mm'} | {100 * (plain / P_TRUE - 1):+.1f} % | {100 * (pa / P_TRUE - 1):+.1f} % | "
              f"{100 * (sol.x[0] / P_TRUE - 1):+.1f} % (copper x{sol.x[1]:.2f}) |", flush=True)
    print("\nC: uncertainty band for the drawn board = real board, power from the 1 mm reading")
    drawn = real
    rows = []
    for label, mod in (("copper 0.75 x / 1.25 x", lambda m: with_copper(drawn, 0.75 if m == 0 else 1.25)),
                       ("heat transfer -30 % / +30 %", lambda m: _scaled_h(drawn, 0.7 if m == 0 else 1.3))):
        ps = []
        for m in (0, 1):
            d = mod(m)
            lo, hi = 0.05, 20.0
            for _ in range(40):
                mid = 0.5 * (lo + hi)
                lo, hi = (mid, hi) if board_temps(d, mid)[0] < t_ring_real[0] else (lo, mid)
            ps.append(0.5 * (lo + hi))
        rows.append((label, ps))
        print(f"  {label}: {ps[0]:.2f} W / {ps[1]:.2f} W  ({100 * (ps[0] / P_TRUE - 1):+.1f} % / {100 * (ps[1] / P_TRUE - 1):+.1f} %)")


def _scaled_h(problem, f):
    """!
    @brief A copy with both face heat transfer coefficients multiplied by a factor.
    @param problem Problem.
    @param f Factor.
    @return Problem.
    """
    q = copy.deepcopy(problem)
    q.board.h_top *= f
    q.board.h_bottom *= f
    return q


if __name__ == "__main__":
    main()
