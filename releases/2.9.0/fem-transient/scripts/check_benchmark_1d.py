#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_benchmark_1d.py
@brief Check of the review of DESIGN.md (section 14.6): the 1D linear transient benchmark proposed as the published case, solved by an independent 1D finite-element line.
@details The case as the reviewer remembers it (status M: the NAFEMS publication was not opened): a bar of 0.1 m, k 35 W/mK, rho 7200 kg/m3, c 440.5 J/kgK, from 0 degC,
         x = 0 held at 0 degC, x = 0.1 m held at 100 sin(pi t / 40) degC; the quoted reference is 36.60 degC at x = 0.08 m, t = 32 s. Linear elements, consistent mass,
         Crank-Nicolson, the held values eliminated (their mass and stiffness couplings moved to the right-hand side). Not a test of the program: it only says whether the
         remembered value is consistent with the remembered data. Run from the repository root: `.venv/bin/python releases/2.9.0/fem-transient/scripts/check_benchmark_1d.py`.
"""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

K, RHO_C, LENGTH = 35.0, 7200.0 * 440.5, 0.1          # W/mK, J/m3K, m


def held(t):
    """!
    @brief Temperature held at x = L.
    @param t Time in s.
    @return float degC.
    """
    return 100.0 * np.sin(np.pi * t / 40.0)


def solve(ne, nsteps, t_end=32.0, x_read=0.08):
    """!
    @brief March the bar to t_end and read the temperature at x_read.
    @param ne Number of elements.
    @param nsteps Number of Crank-Nicolson steps.
    @param t_end End time in s.
    @param x_read Position of the read-out in m.
    @return float Temperature in degC.
    """
    h, n = LENGTH / ne, ne + 1
    Kf = (sp.diags([np.r_[1, 2 * np.ones(n - 2), 1], -np.ones(n - 1), -np.ones(n - 1)], [0, 1, -1]) * K / h).tocsr()
    Mf = (sp.diags([np.r_[2, 4 * np.ones(n - 2), 2], np.ones(n - 1), np.ones(n - 1)], [0, 1, -1]) * RHO_C * h / 6).tocsr()
    inner = np.arange(1, n - 1)
    Kii, Mii = Kf[inner][:, inner], Mf[inner][:, inner]
    kib, mib = Kf[inner][:, [n - 1]].toarray().ravel(), Mf[inner][:, [n - 1]].toarray().ravel()
    dt = t_end / nsteps
    lu = spla.splu((Mii / dt + 0.5 * Kii).tocsc())
    T = np.zeros(n - 2)
    for i in range(nsteps):
        g0, g1 = held(i * dt), held((i + 1) * dt)
        T = lu.solve(Mii @ T / dt - 0.5 * (Kii @ T) - mib * (g1 - g0) / dt - kib * 0.5 * (g1 + g0))
    return float(np.interp(x_read, np.linspace(0, LENGTH, n)[1:-1], T))


def main():
    """!
    @brief Print the read-out at two refinements.
    @return None.
    """
    for ne, ns in ((50, 3200), (200, 12800)):
        print(f"{ne} elements, {ns} steps: T(0.08 m, 32 s) = {solve(ne, ns):.3f} degC (remembered reference 36.60)")


if __name__ == "__main__":
    main()
