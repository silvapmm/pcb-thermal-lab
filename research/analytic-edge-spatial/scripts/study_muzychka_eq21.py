#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_muzychka_eq21.py
@brief Does equation 21 of Muzychka, Culham and Yovanovich (2003, Part II), the edge-cooled rectangular flux channel, agree with an independent 3D solver, and when does the thin-sheet series of the Analytic model equal it?

@details A 50 x 50 mm channel of conductivity k, thickness t, a 10 x 10 mm source at the centre (adiabatic top outside it), a film h = 100 W/m2K on the bottom and
         the edge coefficient h_e on the four edges. For k in {50, 385} W/mK, t in {0.2, 1, 3} mm and h_e in {0, 50, 200, 1000} W/m2K it prints the resistance
         (mean source rise over the power) of equation 21, of the independent 3D finite-volume solver (0.5 mm cells, 8 sub-slabs) and of the thin-sheet series of
         robin_basis (what the Analytic model solves), with the edge Biot number Bi_e = h_e c / k and tau = t / sqrt(A_s).

         Run from the repository root: .venv/bin/python research/analytic-edge-spatial/scripts/study_muzychka_eq21.py  (about 1 minute)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import layered3d_side as l3   # noqa: E402
import muzychka as mz         # noqa: E402


def main():
    """!
    @brief Print the table.
    @return int 0.
    """
    a = b = 5e-3
    c = d = 25e-3
    h = 100.0
    n = 100
    dx = 0.5e-3
    xs = (np.arange(n) + 0.5) * dx
    m = (xs[None, :] > 20e-3) & (xs[None, :] < 30e-3) & (xs[:, None] > 20e-3) & (xs[:, None] < 30e-3)
    print(f"{'k':>5s} {'t mm':>5s} {'h_e':>6s} {'Bi_e':>8s} {'tau':>6s} | {'eq.21':>9s} {'3D FV':>9s} {'eq/3D':>7s} | {'thin sheet':>10s} {'sheet/eq':>8s}   (K/W)")
    for k in (50.0, 385.0):
        for t in (0.2e-3, 1e-3, 3e-3):
            for he in (0.0, 50.0, 200.0, 1000.0):
                # h_e = 0 is the adiabatic channel: the series needs a tiny edge to build the eigenvalues, 1e-3 W/m2K is the same to 4 digits
                hee = max(he, 1e-3)
                r21 = mz.eq21(a, b, c, d, t, k, h, hee, hee)
                top, _ = l3.solve_3d(dx, n, n, [(t, k, k, 8)], (20e-3, 20e-3, 30e-3, 30e-3), 1.0, h, he, h_top=0.0)
                r3 = float(top[m].mean())
                rf = mz.fin_limit(a, b, c, d, t, k, h, hee, hee)
                print(f"{k:5.0f} {t * 1e3:5.1f} {he:6.0f} {he * c / k:8.3f} {t / 0.01:6.3f} | {r21:9.4f} {r3:9.4f} {100 * (r21 / r3 - 1):+6.2f}% | {rf:10.4f} {100 * (rf / r21 - 1):+7.2f}%", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
