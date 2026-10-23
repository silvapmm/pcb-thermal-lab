"""!
@file fin_validation.py
@brief Check of the plate-fin model of the metal block (`blocks.fin_ratio`) against an independent two-dimensional finite-volume solution of one fin.

@details The program replaces the fins by an area gain and an efficiency: per unit of base area, ratio = (1 - t/p) + 2 Hc eta / p with Hc = H + t/2 and
         eta = tanh(m Hc) / (m Hc), m = sqrt(2 h / (k t)) (textbook straight fin with a convecting tip taken as an adiabatic tip at the corrected length, Incropera and DeWitt).
         Here the same fin is solved as a 2D conduction problem (width t, height H, root at a fixed temperature, convection h on both faces and on the tip, uniform h),
         which keeps the transverse temperature drop and the real tip, and the heat of the fin is compared with 2 Hc eta h theta_b.

Usage: python research/block-and-fins/fin_validation.py
"""

import math
import os
import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def fin_heat_2d(k, h, t, height, nx=12, ny=240):
    """!
    @brief Heat leaving one straight fin per unit depth and per kelvin of root excess temperature, from a 2D finite-volume solution.
    @param k Conductivity of the fin in W/mK.
    @param h Heat transfer coefficient on the faces and on the tip in W/m2K.
    @param t Fin thickness in m.
    @param height Fin height in m (from the root to the tip).
    @param nx Cells across the thickness.
    @param ny Cells along the height.
    @return Heat in W/m per K (the root is held at 1 K above the air).
    """
    dx, dy = t / nx, height / ny
    n = nx * ny
    idx = lambda j, i: j * nx + i                                       # noqa: E731  (row j along the height from the root, column i across)
    rows, cols, vals = [], [], []
    rhs = np.zeros(n)
    diag = np.zeros(n)
    for j in range(ny):
        for i in range(nx):
            p = idx(j, i)
            if i + 1 < nx:                                              # Conduction across the thickness
                g = k * dy / dx
                rows += [p, idx(j, i + 1)]; cols += [idx(j, i + 1), p]; vals += [-g, -g]
                diag[p] += g; diag[idx(j, i + 1)] += g
            if j + 1 < ny:                                              # Conduction along the height
                g = k * dx / dy
                rows += [p, idx(j + 1, i)]; cols += [idx(j + 1, i), p]; vals += [-g, -g]
                diag[p] += g; diag[idx(j + 1, i)] += g
            if i == 0 or i == nx - 1:                                   # Convection on the two faces
                diag[p] += h * dy
            if j == ny - 1:                                             # Convection on the tip
                diag[p] += h * dx
            if j == 0:                                                  # Root at 1 K: half a cell of conduction to the fixed temperature
                g = k * dx / (dy / 2.0)
                diag[p] += g
                rhs[p] += g
    A = sp.csr_matrix((vals + list(diag), (rows + list(range(n)), cols + list(range(n)))), shape=(n, n))
    theta = spla.spsolve(A, rhs)
    # Heat leaving by convection (faces and tip), equal to the heat entering at the root
    q = 0.0
    for j in range(ny):
        for i in (0, nx - 1):
            q += h * dy * theta[idx(j, i)]
    for i in range(nx):
        q += h * dx * theta[idx(ny - 1, i)]
    return q


def fin_heat_formula(k, h, t, height):
    """!
    @brief Heat of one fin per unit depth and per kelvin from the model of the program (2 Hc eta h).
    @param k Conductivity in W/mK.
    @param h Heat transfer coefficient in W/m2K.
    @param t Fin thickness in m.
    @param height Fin height in m.
    @return Heat in W/m per K.
    """
    hc = height + 0.5 * t
    m = math.sqrt(2.0 * h / (k * t))
    return 2.0 * hc * math.tanh(m * hc) / (m * hc) * h


def main():
    """!
    @brief Print the comparison for aluminium, copper and steel fins at several coefficients.
    """
    print("| Metal | k (W/mK) | h (W/m²K) | fin (t × H) | efficiency | 2D (W/m/K) | formula (W/m/K) | difference |")
    print("| :-- | --: | --: | :-- | --: | --: | --: | --: |")
    for name, k in (("aluminium", 204.0), ("copper", 386.0), ("carbon steel", 50.0), ("stainless", 14.0)):
        for h in (10.0, 30.0, 100.0):
            for t, height in ((1.5e-3, 15e-3), (1.0e-3, 30e-3)):
                q2, qf = fin_heat_2d(k, h, t, height), fin_heat_formula(k, h, t, height)
                hc = height + 0.5 * t
                eta = math.tanh(math.sqrt(2 * h / (k * t)) * hc) / (math.sqrt(2 * h / (k * t)) * hc)
                print(f"| {name} | {k:g} | {h:g} | {t * 1e3:g} × {height * 1e3:g} mm | {eta:.3f} | {q2:.4f} | {qf:.4f} | {100 * (qf / q2 - 1):+.2f} % |", flush=True)


if __name__ == "__main__":
    main()
