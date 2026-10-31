#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_lemczyk_1992.py
@brief F2: the trace cells of Lemczyk, Mack, Culham and Yovanovich (J. Electronic Packaging 114, 1992, 413-419) reproduced with an independent 2D finite-volume solver and, for the thin cases, with the program.
@details The paper's Table 1 (dimensional heat flows Q_a of polyamide and FR4 traces, h1 = h2 = 10 W/m2K, contact temperature 90 C above a fluid at 20 C, L2 = 1 m) and Tables 2 and 3 (dimensionless
resistance factors Psi = k L2 R for the cases a to d, Bi1 = Bi2) were read from the scan (pages 416, 4-digit numbers; the page is an image, so a misread digit is possible). Cases: (a) trace on the top face with
the film over the whole top face, (b) mid-buried trace (half cell, twice the flow), (c) as (a) with h1 = 0, (d) trace on the bottom face with h1 = 0, solved as the mirror cell. The 2D solver is lib/strip2d.py.
The program is run on the FR4 rows of Table 1 that a one-layer board can represent (one copper layer of the thickness t and conductivity k carrying a strip heater of the Q_a of the paper over a
board of the cell width): it returns the mean temperature of the trace, to be compared with the 90 K contact temperature.
Run from the repository root: .venv/bin/python research/theory-sources/scripts/study_lemczyk_1992.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import strip2d as s2  # noqa: E402

TABLE1 = [  # (w um, t um, L1 um, k, Q_a W, R_a C/W) read from Table 1 of the paper (polyamide k 0.2, FR4 k 0.4)
    (10, 10, 20, 0.2, 0.036, 2500.0), (10, 50, 20, 0.2, 0.036, 2500.0), (10, 10, 50, 0.2, 0.089, 1010.0), (10, 50, 50, 0.2, 0.090, 1000.0),
    (50, 50, 100, 0.2, 0.179, 502.0), (50, 100, 100, 0.2, 0.179, 502.0), (50, 50, 250, 0.2, 0.436, 206.0), (50, 100, 250, 0.2, 0.439, 205.0),
    (50, 1000, 100, 0.4, 0.178, 507.0), (50, 2000, 100, 0.4, 0.176, 513.0), (50, 1000, 250, 0.4, 0.440, 204.0), (50, 2000, 250, 0.4, 0.435, 207.0),
    (250, 1000, 500, 0.4, 0.884, 102.0), (250, 2000, 500, 0.4, 0.884, 102.0), (250, 1000, 1250, 0.4, 2.12, 42.4), (250, 2000, 1250, 0.4, 2.10, 42.9),
]
# Tables 2 and 3: (Bi2, t/L1, w/L1, Psi_a, Psi_b, Psi_c, Psi_d), numbers as printed times the block factor
TABLE23 = [
    (0.01, 0.01, 0.1, 72.10, 72.26, 114.7, 124.0), (0.01, 0.01, 1.0, 50.00, 50.00, 90.91, 100.0), (0.01, 1.0, 0.1, 51.50, 50.92, 92.19, 102.3),
    (0.01, 10.0, 0.1, 53.63, 53.14, 92.26, 111.3), (0.1, 0.01, 0.1, 16.04, 15.94, 24.70, 24.88), (0.1, 1.0, 0.1, 6.441, 5.891, 11.11, 12.23),
    (0.1, 10.0, 0.1, 7.868, 8.116, 11.11, 21.23), (1.0, 0.01, 0.1, 3.155, 3.112, 5.296, 5.355), (1.0, 1.0, 0.1, 1.686, 1.377, 2.018, 3.227),
    (1.0, 10.0, 0.1, 1.935, 3.614, 2.017, 12.23), (10.0, 0.01, 0.1, 0.461, 0.465, 0.813, 0.913), (10.0, 1.0, 0.1, 0.538, 0.900, 0.546, 2.325),
    (100.0, 0.01, 0.1, 0.0655, 0.0781, 0.0957, 0.2014), (100.0, 1.0, 0.1, 0.0888, 0.8444, 0.0889, 2.234),
]


def psi(bi, t, w, case, n=300):
    """!
    @brief Dimensionless resistance factor of one case (L1 = 1, k = 1, L2 = 1, contact temperature 1).
    @param bi Biot number h L1 / k (the same h on both faces).
    @param t Thickness over cell width.
    @param w Trace width over cell width.
    @param case One of "a", "b", "c", "d".
    @param n Cells per direction of the finest mesh.
    @return float Psi = k L2 T_c / Q.
    """
    tiny = 1e-12
    if case == "a":
        q = s2.trace_heat_flow(w, t, 1.0, 1.0, bi, bi, tc=1.0, nx=n, nz=n)
    elif case == "c":
        q = s2.trace_heat_flow(w, t, 1.0, 1.0, tiny, bi, tc=1.0, nx=n, nz=n)
    elif case == "b":                                           # half cell with the trace at its top, twice the flow
        q = 2.0 * s2.trace_heat_flow(w, t / 2.0, 1.0, 1.0, bi, tiny, tc=1.0, nx=n, nz=n)
    else:                                                       # d: trace on the bottom face with h1 = 0: the trace plane of a cell of thickness t with the film on the far face only
        q = s2.trace_heat_flow(w, t, 1.0, 1.0, bi, tiny, tc=1.0, nx=n, nz=n)
    return 1.0 / q


def main():
    """!
    @brief Print Table 1 and the Tables 2 and 3 comparisons.
    @return None.
    """
    print("Table 1: w t L1 (um), k | Q_a paper, solver (W) | difference")
    for w, t, l1, k, qa, ra in TABLE1:
        q = s2.trace_heat_flow(w * 1e-6, t * 1e-6, l1 * 1e-6, k, 10.0, 10.0, nx=300, nz=300)
        print("  %4d %5d %5d %.1f | %.3f %.4f | %+.2f %%   R_a %.1f paper %.1f" % (w, t, l1, k, qa, q, 100 * (q / qa - 1), 90.0 / q, ra))
    print("Tables 2 and 3: Bi2 t/L1 w/L1 | Psi a b c d (paper) | Psi a b c d (solver) | worst relative difference")
    worst = np.zeros(4)
    for bi, t, w, pa, pb, pc, pd in TABLE23:
        mine = [psi(bi, t, w, c) for c in "abcd"]
        difs = np.array([abs(m / p - 1) for m, p in zip(mine, (pa, pb, pc, pd))])
        if w < 1.0:                                              # the w/L1 = 1 row is the 1D limit, listed apart
            worst = np.maximum(worst, difs)
        print("  %6.3g %5.2f %4.2f | %8.4g %8.4g %8.4g %8.4g | %8.4g %8.4g %8.4g %8.4g | %s %%"
              % ((bi, t, w, pa, pb, pc, pd) + tuple(mine) + (" ".join("%5.1f" % (100 * d) for d in difs),)))
    print("  worst difference per column a b c d over the w/L1 = 0.1 rows: %s %%" % " ".join("%.1f" % (100 * d) for d in worst))
    # The one-dimensional limit w = L1 of case c is exact: Q = h2 L1 Tc, Psi = 1 / Bi2
    print("  case c with w = L1 (exact 1/Bi2): Bi 0.01 -> solver %.3f, 1/Bi %.3f, paper 90.91; Bi 0.1 -> solver %.4f, 1/Bi %.3f, paper 9.901"
          % (psi(0.01, 0.01, 1.0, "c"), 100.0, psi(0.1, 0.01, 1.0, "c"), 10.0))


if __name__ == "__main__":
    main()
