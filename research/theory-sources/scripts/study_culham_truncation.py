#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_culham_truncation.py
@brief F1: does truncating the Fourier series explain the 2 to 6 % excess of the paper's effective conductivities and the plateau of its Figure 5?
@details The paper (Culham and Yovanovich, ITherm 1998, pp. 460-467) solves the coupon with a three-dimensional Fourier series and defines the effective conductivity as that of a
single layer of the same thickness with the same solid-body resistance (its equations 8 to 11). This script solves the base-case coupon (FR4 / Cu / FR4 / Cu / FR4, 50 x 50 mm,
25 x 25 mm source of 2.5 W) with an independent cosine-series solver for 3 to 200 modes per direction (lib/cosine_stack.py, film on the whole top face), finds the single layer
of the same thickness and the same number of modes by bisection and prints the effective conductivity for film coefficients 5 W/m2K (the base case, paper 8.28) and 1e4 (Bi 625,
paper plateau about 4.8, read from its Figure 5).
Run from the repository root: .venv/bin/python research/theory-sources/scripts/study_culham_truncation.py
"""

import os
import sys

from scipy.optimize import brentq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import cosine_stack as cs  # noqa: E402

LAYERS = [(0.5263e-3, 0.4), (0.0356e-3, 400.0), (0.5263e-3, 0.4), (0.0356e-3, 400.0), (0.5263e-3, 0.4)]


def effective_conductivity(h, modes, layers=LAYERS):
    """!
    @brief Effective conductivity of the laminate by the paper's definition (same R_solid, same thickness, same number of modes).
    @param h Film coefficient on the top and bottom faces (W/m2K).
    @param modes Modes per direction.
    @param layers Laminate as (thickness, conductivity) from the top down.
    @return Tuple (R_solid in K/W, effective conductivity in W/mK).
    """
    r = cs.solve(0.05, 0.05, 0.025, layers, h, h, 2.5, modes)[2]
    t = sum(x for x, _ in layers)
    ke = brentq(lambda k: cs.solve(0.05, 0.05, 0.025, [(t, k)], h, h, 2.5, modes)[2] - r, 0.02, 1e5)
    return r, ke


def main():
    """!
    @brief Print the effective conductivity against the number of modes for the two film coefficients.
    @return None.
    """
    print("modes per direction | h = 5 W/m2K: R_solid, k_e (paper 8.28) | h = 1e4 W/m2K: R_solid, k_e (paper plot about 4.8)")
    for m in (3, 5, 7, 9, 11, 21, 41, 101, 201):
        r1, k1 = effective_conductivity(5.0, m)
        r2, k2 = effective_conductivity(1e4, m)
        print("%4d | %7.4f %7.3f | %7.4f %7.3f" % (m, r1, k1, r2, k2))


if __name__ == "__main__":
    main()
