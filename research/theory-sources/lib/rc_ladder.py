#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file rc_ladder.py
@brief Cauer ladder and its Foster equivalent (topic 12, planned): step response, pole decomposition and the response to a piecewise-constant power profile.
@details The ladder is that of the Nexperia application note AN11261 Rev. 5.0 (Fig. 2 Foster, Fig. 4 Cauer, equations 2 and 3): capacitors C_i from node i to the ambient, resistors R_i from
node i to node i + 1, the last resistor to the ambient, the power into node 1 (the junction). The Foster form is Zth(t) = sum R_i (1 - exp(-t / tau_i)), tau_i = R_i C_i (equations 2 and 3 of the note).
"""

import numpy as np


def matrices(r, c):
    """!
    @brief Conductance and capacity matrices of a Cauer ladder.
    @param r Resistances R_1..R_n in K/W (R_n connects node n to the ambient).
    @param c Capacitances C_1..C_n in J/K.
    @return Tuple (G, C) as arrays with G tridiagonal.
    """
    n = len(r)
    g = np.zeros((n, n))
    for i in range(n):
        gi = 1.0 / r[i]
        g[i, i] += gi
        if i + 1 < n:
            g[i + 1, i + 1] += gi
            g[i, i + 1] -= gi
            g[i + 1, i] -= gi
    return g, np.diag(np.asarray(c, dtype=float))


def foster(r, c):
    """!
    @brief Foster equivalent of a Cauer ladder, seen from node 1.
    @param r Cauer resistances (K/W).
    @param c Cauer capacitances (J/K).
    @return Tuple (R_f, tau) arrays: Zth(t) = sum R_f (1 - exp(-t / tau)).
    """
    g, cm = matrices(r, c)
    s = np.diag(1.0 / np.sqrt(np.diag(cm)))
    lam, vec = np.linalg.eigh(s @ g @ s)                         # symmetric problem: C^(-1/2) G C^(-1/2)
    # With T = C^(-1/2) y the junction response is Zth(s) = sum_k (e1' C^(-1/2) v_k)^2 / (s + lam_k)
    res = (vec[0, :] / np.sqrt(cm[0, 0])) ** 2
    order = np.argsort(lam)
    lam, res = lam[order], res[order]
    return res / lam, 1.0 / lam


def zth_foster(t, r_f, tau):
    """!
    @brief Step response of a Foster network (equation 2 of AN11261).
    @param t Times in s (array).
    @param r_f Foster resistances.
    @param tau Foster time constants.
    @return Zth(t) array in K/W.
    """
    t = np.asarray(t, dtype=float)[:, None]
    return (r_f[None, :] * (1.0 - np.exp(-t / tau[None, :]))).sum(axis=1)


def zth_cauer(t, r, c):
    """!
    @brief Step response of the Cauer ladder by the matrix exponential (independent of the Foster formula).
    @param t Times in s (array).
    @param r Cauer resistances.
    @param c Cauer capacitances.
    @return Junction temperature rise for 1 W in K, array.
    """
    g, cm = matrices(r, c)
    a = np.linalg.solve(cm, g)
    lam, vec = np.linalg.eig(a)
    vinv = np.linalg.inv(vec)
    ss = np.linalg.solve(g, np.eye(len(r))[:, 0])               # steady state for 1 W
    out = []
    for ti in np.asarray(t, dtype=float):
        # T(t) = T_ss - exp(-A t) T_ss for a step from zero
        out.append(float((ss - (vec @ np.diag(np.exp(-lam * ti)) @ vinv) @ ss)[0].real))
    return np.array(out)
