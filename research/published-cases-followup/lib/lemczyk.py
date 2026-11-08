#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file lemczyk.py
@brief The four trace cells (a) to (d) of Lemczyk, Mack, Culham and Yovanovich (1992), solved with the independent 2D solver, and the printed Tables 1 to 4 as data.
@details The cell is a homogeneous slab of conductivity k, thickness t and half-width L1 with a trace (strip) of width w held at the temperature T_c on one face, the ends insulated (page 3, Fig. 3,
         equations 25 to 36): (a) the trace on the top face z = t, films h1 = h2 on both faces (the film also cools the trace face, equation 27); (b) the trace mid-way, solved as the half cell of
         thickness t/2 (insulated outside the trace, film h1 at the far face) and doubled (equation 32); (c) as (a) with h1 = 0; (d) the trace on the face z = 0 with h1 = 0 and the film h2 on the far face
         (equation 34). Psi = k L2 R with R = T_c / Q (equation 36). Journal pages 413 to 419 (printed pages of the scan are not numbered in the text layer: the Tables are on scan pages 4 and 5).
"""

import numpy as np

import strip2d as F

# Table 2 (Bi2 <= 0.1) and Table 3 (Bi2 >= 1): (Bi2, t/L1, w/L1, Psi_a, Psi_b, Psi_c, Psi_d) as printed (mantissas; the power of ten of each block is inferred, see study_lemczyk.py)
TABLE23 = [
    (0.001, .01, 0.1, .5284, .5332, .5284, 1.032), (0.001, .01, 1.0, .5000, .5000, .5000, 1.000), (0.001, 1., 0.1, .5018, .5012, .5018, 1.003),
    (0.001, 1., 1.0, .5002, .5002, .5002, 1.001), (0.001, 10., 0.1, .5040, .5034, .5040, 1.012), (0.001, 10., 1.0, .5025, .5025, .5025, 1.010),
    (0.01, .01, 0.1, .7210, .7226, 1.147, 1.240), (0.01, .01, 1.0, .5000, .5000, .9091, 1.000), (0.01, 1., 0.1, .5150, .5092, .9219, 1.023),
    (0.01, 1., 1.0, .5025, .5025, .9092, 1.010), (0.01, 10., 0.1, .5363, .5314, .9226, 1.113), (0.01, 10., 1.0, .5238, .5250, .9099, 1.100),
    (0.1, .01, 0.1, 1.604, 1.594, 2.470, 2.488), (0.1, .01, 1.0, .5002, .5002, .9901, 1.001), (0.1, 1., 0.1, .6441, .5891, 1.111, 1.223),
    (0.1, 1., 1.0, .5238, .5250, .9901, 1.100), (0.1, 10., 0.1, .7868, .8116, 1.111, 2.123), (0.1, 10., 1.0, .6667, .7500, .9902, 2.000),
    (1.0, .01, 0.1, .3155, .3112, .5296, .5355), (1.0, .01, 1.0, .0503, .0503, .1000, 1.010), (1.0, 1., 0.1, .1686, .1377, .2018, .3227),
    (1.0, 1., 1.0, .6667, .7500, .9990, .2000), (1.0, 10., 0.1, .1935, .3614, .2017, 1.223), (1.0, 10., 1.0, .0917, .3000, .1000, 1.100),
    (10.0, .01, 0.1, .0461, .0465, .0813, .0913), (10.0, .01, 1.0, .0052, .0053, .0100, .0110), (10.0, 1., 0.1, .0538, .0900, .0546, .2325),
    (10.0, 1., 1.0, .0092, .0300, .0100, .1100), (10.0, 10., 0.1, .0545, .3163, .0546, 1.133), (10.0, 10., 1.0, .0099, .2550, .0100, 1.010),
    (100.0, .01, 0.1, .6550, .7809, .9567, 2.014), (100.0, .01, 1.0, .0667, .0750, .1000, .2000), (100.0, 1., 0.1, .8882, 8.444, .8892, 22.34),
    (100.0, 1., 1.0, .0990, 2.550, .1000, 10.10), (100.0, 10., 0.1, .8891, 31.18, .8892, 112.4), (100.0, 10., 1.0, .0999, 25.05, .1000, 100.1),
]

# Table 1 (T_c = 90 C, h1 = h2 = 10 W/m2K, L2 = 1 m): (material k, w, t, L1 in micrometres, Q_a, Q_b, Q_c, Q_d in W)
TABLE1 = [
    (0.2, 10, 10, 20, .036, .036, .036, .018), (0.2, 10, 50, 20, .036, .036, .036, .018), (0.2, 10, 10, 50, .089, .090, .063, .045), (0.2, 10, 50, 50, .090, .090, .063, .045),
    (0.2, 50, 50, 100, .179, .179, .108, .090), (0.2, 50, 100, 100, .179, .179, .108, .090), (0.2, 50, 50, 250, .436, .438, .239, .221), (0.2, 50, 100, 250, .439, .442, .240, .221),
    (0.4, 50, 1000, 100, .178, .178, .126, .088), (0.4, 50, 2000, 100, .176, .175, .125, .086), (0.4, 50, 1000, 250, .440, .442, .259, .218), (0.4, 50, 2000, 250, .435, .435, .259, .213),
    (0.4, 250, 1000, 500, .884, .886, .484, .438), (0.4, 250, 2000, 500, .884, .886, .484, .438), (0.4, 250, 1000, 1250, 2.12, 2.16, 1.13, 1.07), (0.4, 250, 2000, 1250, 2.10, 2.14, 1.13, 1.05),
]

# Table 4 (3-layer PCB, w/L1: R printed, R_S, R_P, R_H in K/W)
TABLE4 = [(0.1, 134.3, 139.0, 130.7, 135.1), (0.25, 147.4, 156.7, 142.9, 150.1), (0.5, 172.3, 183.5, 166.8, 175.6), (0.75, 205.6, 212.2, 199.2, 206.0), (0.9, 230.4, 233.5, 224.0, 228.8),
          (1.0, 259.7, 259.7, 250.4, 255.1)]


def q_case(case, k, t, l1, w, h, tc=1.0, hmins=(0.04, 0.02, 0.01), bi1=0.0):
    """!
    @brief Heat flow per unit depth of one trace cell by the independent solver, with a Richardson step (first-order convergence at the trace edge).
    @param case "a", "b", "c" or "d".
    @param k Conductivity in W/mK.
    @param t Thickness of the slab in m.
    @param l1 Half-width of the cell in m.
    @param w Trace width in m.
    @param h Film coefficient of both faces in W/m2K (case c: only the top, case d: only the far face).
    @param tc Trace temperature above the ambient in K.
    @param hmins Smallest cell as a fraction of the smaller of w, t and l1 - w, finest last.
    @param bi1 Case (c) only: Biot number h1 L1 / k of the bottom face, 0 for the case as written in the text; the printed numbers correspond to 0.001 (see study_lemczyk.py).
    @return float Total heat flow Q of the cell in W/m (the quantity of equations 27, 32, 34, per unit depth).
    """
    th = t / 2.0 if case == "b" else t
    vals = []
    for hm in hmins:
        s = hm * min(w, th, max(l1 - w, w))
        xe = F.graded_edges(l1, s, w, 1.12, h_max=l1 / 25.0)
        ze = F.graded_edges(th, s, 0.0, 1.12, h_max=th / 25.0)
        if case == "a":
            r = F.solve(xe, ze, k, w, "temp", tc, h, h, film_under_strip=True)
            vals.append(r["q_total"])
        elif case == "c":
            r = F.solve(xe, ze, k, w, "temp", tc, h, bi1 * k / l1, film_under_strip=True)
            vals.append(r["q_total"])
        elif case == "b":
            r = F.solve(xe, ze, k, w, "temp", tc, 0.0, h, film_under_strip=False)
            vals.append(2.0 * r["q_strip"])
        else:
            r = F.solve(xe, ze, k, w, "temp", tc, 0.0, h, film_under_strip=False)
            vals.append(r["q_strip"])
    return vals[-1] + (vals[-1] - vals[-2])             # first order: the Richardson value of the two finest meshes (ratio 2 between them)


def psi_case(case, bi, tau, wl, bi1=0.0):
    """!
    @brief Psi = k L2 R of one case in the dimensionless form of Tables 2 and 3.
    @param case "a", "b", "c" or "d".
    @param bi Bi2 = h L1 / k.
    @param tau t / L1.
    @param wl w / L1.
    @param bi1 Case (c) only: Biot number of the bottom face (see q_case).
    @return float Psi (dimensionless).
    """
    q = q_case(case, 1.0, tau, 1.0, wl, bi, 1.0, bi1=bi1)
    return float(1.0 / q)
