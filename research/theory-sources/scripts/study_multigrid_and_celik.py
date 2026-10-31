#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_multigrid_and_celik.py
@brief F6 (topic 16) and F7: prints the numbers of README 3.9 (multigrid) and 3.10 (Celik Table 1) that no other script printed.
@details Questions answered: (1) does a V(2,1) cycle written from Algorithm 3 of McCormick and Tamstorf (arXiv:2605.17828) reduce the residual by a factor independent of the
mesh (15 to 255 points per side), and is its converged solution second order on -Laplace(u) = 2 pi^2 sin(pi x) sin(pi y); (2) does `lib/gci.py` reproduce the three columns of
Table 1 of Celik, Ghia, Roache and Freitas (2008). Added by the review: the README quoted these numbers without a script that prints them.
Run from the repository root: .venv/bin/python research/theory-sources/scripts/study_multigrid_and_celik.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import gci  # noqa: E402
import mg2d  # noqa: E402

# Celik et al. (2008), Table 1: (phi1, phi2, phi3, r21, r32) and the printed p, extrapolated value and fine-grid GCI
CELIK_TABLE_1 = [((6.063, 5.972, 5.863, 1.5, 1.333), 1.53, 6.1685, 0.022), ((10.7880, 10.7250, 10.6050, 2.0, 2.143), 0.75, 10.8801, 0.011),
                 ((6.0042, 5.9624, 6.0909, 2.0, 2.143), 1.51, 6.0269, 0.005)]


def sine_error(n, cycles=12):
    """!
    @brief Largest error of the multigrid solution of the five-point problem with the exact solution sin(pi x) sin(pi y).
    @param n Interior points per side (2^k - 1).
    @param cycles V(2,1) cycles from a zero start (enough to bring the algebraic error far below the discretisation error).
    @return float Maximum absolute error at the grid points.
    """
    h = 1.0 / (n + 1)
    x = np.arange(1, n + 1) * h
    exact = np.sin(np.pi * x)[:, None] * np.sin(np.pi * x)[None, :]
    f = 2.0 * np.pi ** 2 * exact
    u = np.zeros((n, n))
    for _ in range(cycles):
        u = mg2d.vcycle(u, f, h)
    return float(np.abs(u - exact).max())


def main():
    """!
    @brief Print the multigrid factors and errors and the Celik Table 1 comparison.
    @return None.
    """
    print("1. V(2,1) cycle, red-black Gauss-Seidel, random right-hand side: points per side | mean residual reduction of the last three of 8 cycles")
    for n in (15, 31, 63, 127, 255):
        print("   %4d | %.3f" % (n, float(np.mean(mg2d.convergence_factors(n, 8)[-3:]))))
    print("   exact solution sin(pi x) sin(pi y): points per side | largest error (second order: a quarter per halving)")
    for n in (15, 31, 63):
        print("   %4d | %.2e" % (n, sine_error(n)))
    print("2. Celik et al. (2008) Table 1: p, extrapolated value, GCI fine (printed | lib/gci.py)")
    for args, p, ext, g in CELIK_TABLE_1:
        out = gci.gci(*args)
        print("   p %.2f | %.2f   ext %.4f | %.4f   GCI %.1f %% | %.1f %%" % (p, out["p"], ext, out["phi_ext21"], 100 * g, 100 * out["gci_fine21"]))


if __name__ == "__main__":
    main()
