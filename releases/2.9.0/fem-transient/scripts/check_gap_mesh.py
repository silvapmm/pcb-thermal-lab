#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_gap_mesh.py
@brief Tiny check of the review of DESIGN.md (section 3): how many elements through the dielectric gap the first seconds need, with the program's own gap grading.
@details A 1D line: a heat flux switched on at the top copper of a two-layer board (the copper sheet carried as a nodal capacity of 35 um x 3.45e6 J/m3K), a laminate gap of
         1.53 mm (k 0.3 W/mK, rho c 1.665e6 J/m3K: the board `two2` of `research/transient-reference-boards`), insulated below (the same on every mesh, so the comparison is of the
         mesh alone). The gap is cut as the program cuts it (`pcbthermal.femmesh.graded_gap`, ratio 1.4, finest at both faces) into 2 to 24 linear elements; the reference is
         the same line with 3000 uniform elements. Time: Crank-Nicolson with the two Euler half steps at t = 0, 400 steps per output interval (converged in the step; the
         error printed is the mesh's). A second line checks the reference itself against the closed form `2 q sqrt(t / pi) / e` without the copper capacity while the heat
         has not reached the bottom. Not a study of the branch and not a validation of the 3D model: the plan mesh, the spreading and the films are not in it.
         Run from the repository root: `.venv/bin/python releases/2.9.0/fem-transient/scripts/check_gap_mesh.py`. SI units.
"""
import os
import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
from pcbthermal.femmesh import graded_gap                          # noqa: E402  the program's grading of a gap

K_LAM, RHO_C = 0.3, 1.665e6                                          # laminate of two2 (W/mK, J/m3K)
GAP = 1.53e-3                                                        # gap of two2 (m): 0.765 mm per half
CU_SHEET = 3.45e6 * 35e-6                                            # capacity of the top copper per area (J/m2K)
TIMES = (0.1, 0.3, 1.0, 3.0, 10.0)                                   # output times (s)


def matrices(h, consistent, sheet):
    """!
    @brief Stiffness and mass of linear elements through the gap, the copper sheet as a capacity on the top node.
    @param h Element thicknesses in m, from the top.
    @param consistent True for the consistent mass, False for the row sums.
    @param sheet Capacity of the copper sheet in J/m2K added on the top node.
    @return tuple (K, M) of scipy sparse matrices (per m2 of board).
    """
    n = len(h) + 1
    K = sp.lil_matrix((n, n))
    M = sp.lil_matrix((n, n))
    for e, he in enumerate(h):
        k = K_LAM / he * np.array([[1.0, -1.0], [-1.0, 1.0]])
        m = RHO_C * he / 6.0 * np.array([[2.0, 1.0], [1.0, 2.0]])
        if not consistent:
            m = np.diag(m.sum(axis=1))
        for a in range(2):
            for b in range(2):
                K[e + a, e + b] += k[a, b]
                M[e + a, e + b] += m[a, b]
    M[0, 0] += sheet
    return K.tocsc(), M.tocsc()


def top_rise(h, consistent=True, sheet=CU_SHEET, nsub=400):
    """!
    @brief Rise of the top node per unit flux at the output times (Crank-Nicolson, two Euler half steps at t = 0).
    @param h Element thicknesses in m.
    @param consistent True for the consistent mass.
    @param sheet Capacity of the copper sheet in J/m2K.
    @param nsub Steps per output interval.
    @return numpy.ndarray Rise in K per W/m2 at TIMES.
    """
    K, M = matrices(h, consistent, sheet)
    f = np.zeros(K.shape[0])
    f[0] = 1.0
    T, t, out = np.zeros_like(f), 0.0, []
    for tt in TIMES:
        dt = (tt - t) / nsub
        cn = spla.splu((M / dt + 0.5 * K).tocsc())
        half = spla.splu((M / (0.5 * dt) + K).tocsc())
        for i in range(nsub):
            if t == 0.0 and i == 0:
                T = half.solve(M @ T / (0.5 * dt) + f)               # Rannacher: two Euler half steps open the run
                T = half.solve(M @ T / (0.5 * dt) + f)
            else:
                T = cn.solve(M @ T / dt - 0.5 * (K @ T) + f)
        t = tt
        out.append(T[0])
    return np.array(out)


def main():
    """!
    @brief Print the error of the top rise of every graded gap against the 3000-element line, and the check of that line against the closed form.
    @return None.
    """
    fine = np.full(3000, GAP / 3000)
    ref = top_rise(fine)
    bare = top_rise(fine, sheet=0.0)
    exact = 2.0 * np.sqrt(np.array(TIMES) / np.pi) / np.sqrt(K_LAM * RHO_C)
    print("times (s):", TIMES)
    print("reference check, no copper, 3000 elements against 2 q sqrt(t/pi)/e (%):", np.round(100 * (bare / exact - 1), 2).tolist(),
          "(the last times feel the insulated bottom)")
    for n in (2, 4, 6, 12, 24):
        h = graded_gap(GAP, n)
        cons = 100 * (top_rise(h) / ref - 1)
        lump = 100 * (top_rise(h, consistent=False) / ref - 1)
        print(f"gap elements {n:2d} (first {h[0] * 1e6:5.0f} um, (first)^2/alpha {h[0] ** 2 * RHO_C / K_LAM:7.4f} s): consistent {np.round(cons, 2).tolist()}  "
              f"lumped {np.round(lump, 2).tolist()}")


if __name__ == "__main__":
    main()
