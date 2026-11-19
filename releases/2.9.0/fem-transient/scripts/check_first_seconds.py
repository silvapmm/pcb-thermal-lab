#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_first_seconds.py
@brief Tiny check behind the first-seconds statement of DESIGN.md (section 3): a heat flux switched on at the face of a semi-infinite solid, solved by 1D linear finite
       elements on a graded mesh, with the time schemes the FEM transient will offer, against the closed form `T = 2 q sqrt(t / pi) / e`, `e = sqrt(k rho c)`.
@details Not a study of the branch and not a validation: a 1D line of elements, 40 numbers, seconds of run time, written so that the sentence of DESIGN.md about the size of the
         first step has a number behind it. Schemes: implicit Euler (theta 1), Crank-Nicolson with two implicit-Euler half steps at t = 0 (Rannacher, the scheme of
         `research/independent-fem-extensions/lib/transient.py`), and Crank-Nicolson without the start; consistent and lumped mass. Run from the repository root:
         `.venv/bin/python releases/2.9.0/fem-transient/scripts/check_first_seconds.py [--json]`. Material of the laminate of `research/transient-reference-boards` 4.2
         (k 0.3 W/mK, rho c 1.665e6 J/m3K). SI units.
"""
import json
import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

K_LAM, RHO_C = 0.3, 1.665e6                          # laminate of the two-layer board of transient-reference-boards 4.2 (W/mK, J/m3K)
EFF = np.sqrt(K_LAM * RHO_C)                         # thermal effusivity e, W s^0.5 / m2K


def graded_nodes(first=2e-6, ratio=1.15, depth=6e-3):
    """!
    @brief Node positions of a graded 1D mesh from the heated face into the solid.
    @param first Size of the first element in m.
    @param ratio Growth of the element size.
    @param depth Depth to reach in m (the last element ends at or beyond it).
    @return numpy.ndarray Node coordinates in m, starting at 0.
    """
    x, h = [0.0], first
    while x[-1] < depth:
        x.append(x[-1] + h)
        h *= ratio
    return np.array(x)


def matrices(x, consistent):
    """!
    @brief Stiffness K and mass M of linear elements on the line (the far end insulated, which is exact while the heat has not arrived).
    @param x Node coordinates in m.
    @param consistent True for the consistent mass, False for the row-sum (lumped) mass.
    @return tuple (K, M) of scipy sparse matrices, K in W/K per m2 and M in J/K per m2.
    """
    h = np.diff(x)
    n = x.size
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
    return K.tocsc(), M.tocsc()


def run(x, scheme, consistent, steps):
    """!
    @brief March a unit flux from rest through a list of steps and return the face temperature after each.
    @param x Node coordinates in m.
    @param scheme "euler", "cn_rannacher" or "cn".
    @param consistent True for the consistent mass.
    @param steps List of step sizes in s, in order (the half steps of the Rannacher start replace the first step, they do not come on top of it).
    @return tuple (times, face temperatures per unit flux) as numpy arrays.
    """
    K, M = matrices(x, consistent)
    f = np.zeros(x.size)
    f[0] = 1.0                                       # unit flux at the face
    t, T, ts, out = 0.0, np.zeros(x.size), [], []
    cache = {}

    def advance(T, h, theta):
        """!
        @brief One theta step with a cached factorisation.
        @param T Field at the start.
        @param h Step in s.
        @param theta Implicitness.
        @return numpy.ndarray Field at the end.
        """
        key = (round(h, 12), theta)
        if key not in cache:
            cache[key] = spla.splu((M / h + theta * K).tocsc())
        return cache[key].solve(M @ T / h - (1.0 - theta) * (K @ T) + f)

    for i, h in enumerate(steps):
        if i == 0 and scheme == "cn_rannacher":
            T = advance(advance(T, 0.5 * h, 1.0), 0.5 * h, 1.0)
        else:
            T = advance(T, h, 1.0 if scheme == "euler" else 0.5)
        t += h
        ts.append(t)
        out.append(T[0])
    return np.array(ts), np.array(out)


def main():
    """!
    @brief Print the error of the face temperature after 1, 2, 4 and 8 steps of 0.24 s, 0.06 s and 0.015 s for every scheme.
    @return None.
    """
    x = graded_nodes()
    rows = []
    for h0 in (0.24, 0.06, 0.015):                   # 0.24 s: the first step of a doubling grid for t_end 1000 s (arithmetic of DESIGN.md 3.2)
        for consistent in (True, False):
            for scheme in ("euler", "cn_rannacher", "cn"):
                ts, T = run(x, scheme, consistent, [h0] * 8)
                exact = 2.0 * np.sqrt(ts / np.pi) / EFF
                err = 100.0 * (T / exact - 1.0)
                rows.append({"h0_s": h0, "mass": "consistent" if consistent else "lumped", "scheme": scheme,
                             "err_percent_after_steps_1_2_4_8": [round(float(err[k]), 2) for k in (0, 1, 3, 7)]})
    if "--json" in sys.argv:
        print(json.dumps(rows, indent=1))
        return
    print(f"nodes {x.size}, first element {x[1] * 1e6:.1f} um, depth {x[-1] * 1e3:.1f} mm, e = {EFF:.1f}")
    for r in rows:
        print(f"h0 {r['h0_s']:6.3f} s  {r['mass']:10s} {r['scheme']:13s} error after 1, 2, 4, 8 steps (%): {r['err_percent_after_steps_1_2_4_8']}")


if __name__ == "__main__":
    main()
