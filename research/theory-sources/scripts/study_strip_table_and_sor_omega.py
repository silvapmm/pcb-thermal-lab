#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_strip_table_and_sor_omega.py
@brief Do the strip series of Yovanovich, Muzychka and Culham (1999) reproduce their Table 2, and is the SOR factor of the program Young's optimum of Saad's eq 4.47?

Question (README 9.2 and 9.5, plan study S0):
(1) Table 2 of Yovanovich, Muzychka and Culham (1999, p 5), kRs of a strip on a semi-infinite flux channel, from the sums of eq 24 (iso-flux strip, mu = 0),
    kRs = 1/(pi^3 eps^2) sum_n sin^2(n pi eps)/n^3, and of eq 27 (true isothermal strip), kRs = (1/pi) ln(1/sin(pi eps/2)); the ln is lost in the text layer of the copy
    and is restored here from the printed values (the two agree to four digits).  Printed: eq 24 at eps 0.02, 0.2, 0.6, 0.8 = 1.1377, 0.4083, 0.0882, 0.0255;
    eq 27 = 1.1015, 0.3738, 0.0675, 0.0160 at the same four (the README quotes eq 27 at 0.02, 0.2 and 0.8); all nine columns are checked.
(2) `fvm.Network.sor_omega` on the five-point Dirichlet Laplacian of n x n unknowns, against Saad (2003) eq 4.47, omega = 2 / (1 + sqrt(1 - rho^2)): the program's
    Rayleigh-quotient estimate of rho is a lower bound of the Jacobi spectral radius cos(pi/(n+1)), so its omega must not exceed the optimum; the spectral radius of the SOR
    iteration matrix is computed densely (n = 8) to show where the true minimum lies.

Run (from the repository root):  .venv/bin/python research/theory-sources/scripts/study_strip_table_and_sor_omega.py   (about 1 s)
"""
import math
import os
import sys
from types import SimpleNamespace

import numpy as np
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)

from pcbthermal import fvm  # noqa: E402

# The nine columns of Table 2 (p 5) and the printed rows mu = 0 (eq 24) and T = const (eq 27)
ALL_EPS = (0.02, 0.04, 0.06, 0.08, 0.10, 0.20, 0.40, 0.60, 0.80)
FULL_EQ24 = (1.1377, 0.9172, 0.7883, 0.6970, 0.6263, 0.4083, 0.1984, 0.0882, 0.0255)
FULL_EQ27 = (1.1015, 0.8811, 0.7523, 0.6611, 0.5905, 0.3738, 0.1691, 0.0675, 0.0160)


def eq24(eps, terms=200000):
    """!
    @brief Dimensionless spreading resistance of an iso-flux strip on a semi-infinite flux channel, eq 24.
    @param eps    Relative strip size a/c (dimensionless, 0 < eps < 1).
    @param terms  Number of terms of the series (the tail is O(1/terms^2)).
    @return float k Rs (dimensionless).
    """
    n = np.arange(1, terms + 1, dtype=float)
    return float(np.sum(np.sin(n * math.pi * eps) ** 2 / n ** 3) / (math.pi ** 3 * eps ** 2))


def eq27(eps):
    """!
    @brief Dimensionless spreading resistance of the true isothermal strip, eq 27.
    @param eps Relative strip size (dimensionless).
    @return float k Rs.
    """
    return -math.log(math.sin(math.pi * eps / 2.0)) / math.pi


def table2(eps_list=ALL_EPS):
    """!
    @brief Eq 24 and eq 27 at the columns of Table 2.
    @param eps_list Relative sizes.
    @return list of tuple (eps, eq24, eq27).
    """
    return [(e, eq24(e), eq27(e)) for e in eps_list]


def laplacian(n):
    """!
    @brief Five-point Dirichlet Laplacian of an n x n grid (K = 4 I - N).
    @param n Unknowns per side.
    @return scipy.sparse.csr_matrix of size n^2.
    """
    t = sp.diags([-1.0, 2.0, -1.0], [-1, 0, 1], shape=(n, n))
    return (sp.kron(sp.identity(n), t) + sp.kron(t, sp.identity(n))).tocsr()


def sor_spectral_radius(k, omega):
    """!
    @brief Spectral radius of the SOR iteration matrix of a dense symmetric matrix.
    @param k     Matrix (dense or sparse).
    @param omega Relaxation factor.
    @return float spectral radius.
    """
    a = np.asarray(k.todense() if sp.issparse(k) else k, float)
    d, lo = np.diag(np.diag(a)), np.tril(a, -1)
    m = np.linalg.solve(d + omega * lo, (1 - omega) * d - omega * np.triu(a, 1))
    return float(np.max(np.abs(np.linalg.eigvals(m))))


def sor_check(n=8):
    """!
    @brief The program's omega against Saad's eq 4.47 with the exact Jacobi radius, and the best omega found by a scan.
    @param n  Unknowns per side of the test Laplacian.
    @return dict: omega_prog, omega_saad (rho = cos(pi/(n+1))), omega_scan (argmin of the SOR radius over a fine scan), rho_prog, rho_exact, rad_prog, rad_saad.
    """
    k = laplacian(n)
    omega_prog = float(fvm.Network.sor_omega(SimpleNamespace(K=k)))
    rho_exact = math.cos(math.pi / (n + 1))
    omega_saad = 2.0 / (1.0 + math.sqrt(1.0 - rho_exact ** 2))
    grid = np.linspace(1.0, 1.99, 99)
    rads = [sor_spectral_radius(k, w) for w in grid]
    # Rayleigh quotient of the trial vector of ones, as in the program (all nodes have a link)
    ones = np.ones(k.shape[0])
    rho_prog = 1.0 - float(ones @ (k @ ones)) / float(ones @ k.diagonal())
    return dict(omega_prog=omega_prog, omega_saad=omega_saad, omega_scan=float(grid[int(np.argmin(rads))]), rho_prog=rho_prog, rho_exact=rho_exact,
                rad_prog=sor_spectral_radius(k, omega_prog), rad_saad=sor_spectral_radius(k, omega_saad))


def main():
    """!
    @brief Print Table 2 and the SOR check.
    @return None.
    """
    print("1. Table 2 (kRs): eps | eq 24 computed (printed) | eq 27 computed (printed)")
    for (e, a, b), pa, pb in zip(table2(), FULL_EQ24, FULL_EQ27):
        print(f"  {e:.2f}: {a:.4f} ({pa:.4f}) | {b:.4f} ({pb:.4f})")
    s = sor_check()
    print(f"2. SOR omega on the 8 x 8 Laplacian: program {s['omega_prog']:.4f} (rho {s['rho_prog']:.4f}), Saad 4.47 with the exact rho {s['omega_saad']:.4f} (rho {s['rho_exact']:.4f}), "
          f"best of a scan {s['omega_scan']:.2f}; SOR radius at the program's omega {s['rad_prog']:.4f}, at Saad's {s['rad_saad']:.4f}")


if __name__ == "__main__":
    main()
