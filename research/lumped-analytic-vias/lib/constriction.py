#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file constriction.py
@brief The constriction resistance of a via in a conducting sheet: closed forms, the exact references they are checked against, and the Kron reduction of a barrel.
@details A via of radius a draws heat from a sheet of conductance S (W/K, thickness times conductivity). The sheet temperature that the lumped models carry is an AREA
         MEAN (a ring of the thermal network, a tile of the Green-function mosaic), the temperature the barrel sees is the one at its wall, and the difference is a
         thermal resistance that the models leave out. Closed forms (all per sheet, in K/W):
         * `krogh`: sink at the centre of a circular cell of radius R with a uniform source of the same total heat and an insulated rim (the lattice of vias, Wigner-Seitz
           cell). Area mean of the cell minus wall temperature, per watt: (1 / (2 pi S)) [b^4 ln b / (b^2 - 1)^2 - b^2 / (2 (b^2 - 1)) - 1/4], b = R / a, which tends to
           (ln b - 3/4) / (2 pi S) for b >> 1.
         * `tile_self`: a point sink read at radius a against the response of a disc-shaped tile to its own uniform injection, the quantity the Green-function mosaic
           of the Analytic model gets wrong: (ln(R / a) - 1/4) / (2 pi S) for R >> a (mean of ln r over a disc is ln R - 1/2, mean of ln |x - y| over two points ln R - 1/4).
         `sheet_with_loss` is the exact solution of a via in an infinite sheet with a uniform loss (K0, K1) and `cell_with_loss` the same in a circular cell of radius R
         with an insulated rim (I0, I1, K0, K1), from which the constriction of a cell in which the sheet also loses heat vertically is computed without approximation.
         `kron_barrel` is the reduction of the star barrel + wells to couplings between the sheets (same algebra as research/point-via-convergence/lib/viakernel.py, written
         again here so that this folder's library depends on numpy and scipy only).
"""

import math

import numpy as np
from scipy.special import i0e, i1e, k0e, k1e

# Target radius of a via in the layered idealisation: exp(-1/4) of the drill radius (uniform sink density over the disc; research/point-via-convergence)
ETA = math.exp(-0.25)


def krogh(S, R, a):
    """!
    @brief Mean-to-wall resistance of a circular cell with a uniform source and a sink disc at the centre (insulated rim).
    @param S Sheet conductance in W/K.
    @param R Cell radius in m.
    @param a Radius of the sink disc (an equipotential circle) in m.
    @return float Resistance in K/W: (area mean of the annulus a < r < R) minus (wall temperature), per watt taken by the via; 0 if R <= a.
    """
    if R <= a:
        return 0.0
    b = R / a
    b2 = b * b
    return (b2 * b2 * math.log(b) / (b2 - 1.0) ** 2 - b2 / (2.0 * (b2 - 1.0)) - 0.25) / (2.0 * math.pi * S)


def tile_self(S, R, a):
    """!
    @brief Point sink read at radius a against the response of a disc-shaped tile to its own uniform injection (Analytic mosaic self-term correction).
    @param S Sheet conductance in W/K.
    @param R Tile radius in m (the radius of the disc of the tile area).
    @param a Radius of the via in m.
    @return float (ln(R / a) - 1/4) / (2 pi S) in K/W (zero if R <= a).
    """
    if R <= a:
        return 0.0
    return (math.log(R / a) - 0.25) / (2.0 * math.pi * S)


def sheet_with_loss(S, h, a, q):
    """!
    @brief Equipotential via of radius a in an infinite sheet with a uniform loss h and a uniform source q (closed form).
    @param S Sheet conductance in W/K.
    @param h Loss per area in W/m2K.
    @param a Via radius in m.
    @param q Uniform source in W/m2.
    @return dict with lam (m) and I (heat taken by the via in W): I = 2 pi S (a / lam) (q / h) K1(a / lam) / K0(a / lam).
    """
    lam = math.sqrt(S / h)
    x = a / lam
    # Ratio of scaled functions: K1/K0 = k1e/k0e (the exponentials cancel)
    return {"lam": lam, "I": 2.0 * math.pi * S * x * (q / h) * k1e(x) / k0e(x)}


def cell_with_loss(S, h, a, R, q):
    """!
    @brief Equipotential via of radius a at the centre of a circular cell of radius R with insulated rim, uniform loss h and uniform source q (closed form).
    @param S Sheet conductance in W/K.
    @param h Loss per area in W/m2K.
    @param a Via radius in m.
    @param R Cell radius in m.
    @param q Uniform source in W/m2.
    @return dict with I (heat taken by the via, W), T_mean (area mean rise of the annulus above the via temperature, K) and R_c = T_mean / I (K/W).
    @note T(r) = q/h + A K0(r/lam) + B I0(r/lam), T(a) = 0 (rise measured from the via), T'(R) = 0, lam = sqrt(S/h).
    """
    lam = math.sqrt(S / h)
    xa, xR = a / lam, R / lam
    # K1(xR)/I1(xR) from the scaled functions: K1 = k1e e^-x, I1 = i1e e^x
    ratio = (k1e(xR) / i1e(xR)) * math.exp(-2.0 * xR)
    # Rim condition T'(R) = 0 gives B = A K1(xR) / I1(xR); T(a) = 0 gives A
    d = k0e(xa) * math.exp(-xa) + ratio * i0e(xa) * math.exp(xa)
    A = -(q / h) / d
    B = A * ratio
    tp = (-A * k1e(xa) * math.exp(-xa) + B * i1e(xa) * math.exp(xa)) / lam
    i_via = 2.0 * math.pi * a * S * tp

    # Primitives of x K0(x) = -x K1(x) and x I0(x) = x I1(x)
    def prim_k(x):
        return -x * k1e(x) * math.exp(-x)

    def prim_i(x):
        return x * i1e(x) * math.exp(x)
    area_int = (q / h) * (xR ** 2 - xa ** 2) / 2.0 + A * (prim_k(xR) - prim_k(xa)) + B * (prim_i(xR) - prim_i(xa))
    t_mean = area_int / ((xR ** 2 - xa ** 2) / 2.0)
    return {"I": i_via, "T_mean": t_mean, "R_c": t_mean / i_via if i_via != 0 else float("nan")}


def kron_barrel(g_gap, g_well):
    """!
    @brief Couplings between the sheets of a barrel with a well (constriction resistance) in each sheet, the barrel nodes eliminated.
    @param g_gap (L-1,) conductance of the barrel across each gap in W/K per via (inf allowed).
    @param g_well (L,) conductance of the well of each sheet in W/K per via (inf = no constriction, 0 = the sheet does not touch the barrel).
    @return numpy.ndarray (L, L) symmetric conductances G[l, m] between the sheets, zero diagonal.
    """
    g_gap = np.asarray(g_gap, float)
    g_well = np.asarray(g_well, float)
    n = len(g_well)
    fin = np.concatenate([g_well[np.isfinite(g_well)], g_gap[np.isfinite(g_gap)], [1e-30]])
    big = 1e15 * float(fin.max())
    gw = np.where(np.isfinite(g_well), g_well, big)
    gg = np.where(np.isfinite(g_gap), g_gap, big)
    Y = np.zeros((2 * n, 2 * n))

    def link(a, b, g):
        Y[a, a] += g
        Y[b, b] += g
        Y[a, b] -= g
        Y[b, a] -= g

    for l in range(n):
        link(l, n + l, gw[l])
    for k in range(n - 1):
        link(n + k, n + k + 1, gg[k])
    Yss, Ysb, Ybb = Y[:n, :n], Y[:n, n:], Y[n:, n:]
    # A sheet with no contact (well 0) leaves its barrel node tied only by the gaps: regularise the barrel block
    Yred = Yss - Ysb @ np.linalg.solve(Ybb + 1e-300 * np.eye(n), Ysb.T)
    G = -Yred
    np.fill_diagonal(G, 0.0)
    return G
