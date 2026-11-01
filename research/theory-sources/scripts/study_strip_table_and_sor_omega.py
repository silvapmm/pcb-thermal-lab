#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_strip_table_and_sor_omega.py
@brief Do the strip series of Yovanovich, Muzychka and Culham (1999) reproduce their Table 2, and is the SOR factor of the program Young's optimum of Saad's eq 4.47?

Question (README 9.2 and 9.5, plan study S0):
(1) Table 2 of Yovanovich, Muzychka and Culham (1999, p 5), kRs of a strip on a semi-infinite flux channel, from the sums of eq 24 (iso-flux strip, mu = 0),
    kRs = 1/(pi^3 eps^2) sum_n sin^2(n pi eps)/n^3, and of eq 27 (true isothermal strip), kRs = (1/pi) ln(1/sin(pi eps/2)); the ln is lost in the text layer of the copy
    but printed on the page (checked on the page image by the review), so the formula is the paper's, not one fitted to the table.  Printed: eq 24 at eps 0.02, 0.2, 0.6, 0.8 = 1.1377, 0.4083, 0.0882, 0.0255;
    eq 27 = 1.1015, 0.3738, 0.0675, 0.0160 at the same four (the README quotes eq 27 at 0.02, 0.2 and 0.8); all nine columns are checked.
(2) `fvm.Network.sor_omega` on the five-point Dirichlet Laplacian of n x n unknowns, against Saad (2003) eq 4.47, omega = 2 / (1 + sqrt(1 - rho^2)): the program's
    Rayleigh-quotient estimate of rho is a lower bound of the Jacobi spectral radius cos(pi/(n+1)), so its omega must not exceed the optimum; the spectral radius of the SOR
    iteration matrix is computed densely (n = 8) to show where the true minimum lies.
(3) Added by the review: the cost of the safe side on boards, the program's SOR at its own omega against the best omega of a scan (three 60 x 40 mm boards, 1 mm).

Run (from the repository root):  .venv/bin/python research/theory-sources/scripts/study_strip_table_and_sor_omega.py   (about 25 s, part 3; < 0.2 GB)
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
    rad_prog, rad_saad = sor_spectral_radius(k, omega_prog), sor_spectral_radius(k, omega_saad)
    # Asymptotic cost: sweeps to reduce the error by a fixed factor scale as 1 / -ln(radius)
    return dict(omega_prog=omega_prog, omega_saad=omega_saad, omega_scan=float(grid[int(np.argmin(rads))]), rho_prog=rho_prog, rho_exact=rho_exact,
                rad_prog=rad_prog, rad_saad=rad_saad, sweep_ratio=math.log(rad_saad) / math.log(rad_prog))


def sor_on_boards(cell_mm=1.0, scan=tuple(np.round(np.arange(1.80, 1.995, 0.01), 2))):
    """!
    @brief Sweeps of the program's SOR at its own omega against the best omega of a scan, on three small boards (added by the review).
    @details The 8 x 8 Dirichlet Laplacian is the worst case of the trial vector of ones (its first eigenvector is a product of sines, far from flat); a board with
             face films is close to the Neumann case, where the vector of ones is near the first eigenvector, so the gap should be smaller there.
    @param cell_mm  FVM cell in mm.
    @param scan     Values of omega tried.
    @return list of dict: board, omega_prog, sweeps_prog, omega_best, sweeps_best.
    """
    from pcbthermal.model import Problem   # local import: part 2 needs only fvm

    def board(name, full, h):
        """!
        @brief One 60 x 40 mm two-layer board with a 10 x 10 mm, 2 W part.
        @param name  Label.
        @param full  True for copper over both layers, False for a 20 x 20 mm pad on layer 1 only.
        @param h     Film coefficient of both faces in W/m2K.
        @return tuple (name, Problem).
        """
        p = Problem.new(60, 40, layers=2, h_top=h, h_bottom=h)
        if full:
            p.add_zone(1, rect=(0, 0, 60, 40), fill=1.0)
            p.add_zone(2, rect=(0, 0, 60, 40), fill=1.0)
        else:
            p.add_zone(1, rect=(20, 10, 40, 30), fill=1.0)
        p.add_heater(1, 2.0, rect=(25, 15, 35, 25))
        return name, p

    out = []
    for name, p in (board("full copper, h 10", True, 10.0), board("pad only, h 10", False, 10.0), board("full copper, h 200", True, 200.0)):
        r = fvm.solve_steady(p, cell_mm=cell_mm, method="sor")
        best = (r.extras["iterations"], r.extras["omega"])
        for w in scan:
            rr = fvm.solve_steady(p, cell_mm=cell_mm, method="sor", sor_omega=float(w))
            if rr.extras["converged"] and rr.extras["iterations"] < best[0]:
                best = (rr.extras["iterations"], float(w))
        out.append(dict(board=name, omega_prog=r.extras["omega"], sweeps_prog=r.extras["iterations"], omega_best=best[1], sweeps_best=best[0]))
    return out


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
          f"best of a scan {s['omega_scan']:.2f}; SOR radius at the program's omega {s['rad_prog']:.4f}, at Saad's {s['rad_saad']:.4f} "
          f"(asymptotic sweeps {s['sweep_ratio']:.2f} times the optimum's)")
    print("3. program's SOR on 60 x 40 mm two-layer boards at 1 mm, residual 1e-9: own omega against the best of a scan 1.80 to 1.99 (review)")
    for b in sor_on_boards():
        print(f"  {b['board']}: omega {b['omega_prog']:.3f} {b['sweeps_prog']:.0f} sweeps; best {b['omega_best']:.2f} {b['sweeps_best']:.0f} sweeps; "
              f"ratio {b['sweeps_prog'] / b['sweeps_best']:.2f}")


if __name__ == "__main__":
    main()
