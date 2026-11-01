#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file closed_forms.py
@brief Closed forms used to check the resolved solver: the 1D series column and the mean source temperature of a rectangular source on an isotropic plate (Muzychka, Culham and Yovanovich 2003).
@details `plate_mean_rise` implements Eqs. (18), (20), (22), (24), (27) and (28) of Muzychka, Culham, Yovanovich, "Thermal Spreading Resistance of Eccentric Heat Sources on
         Rectangular Flux Channels", J. Electronic Packaging 125 (2003) 178-185 (read in full, open copy of the Waterloo group): a plate a x b x t of conductivity k, adiabatic sides,
         adiabatic top outside the source, uniform flux Q/(c d) on a c x d rectangle centred at (Xc, Yc), a film h on the bottom face. It returns the mean temperature rise of the source.
"""

import numpy as np


def plate_mean_rise(a, b, c, d, xc, yc, t, k, h, q, terms=400):
    """!
    @brief Mean temperature rise of a rectangular source on the top of an isotropic plate cooled on the bottom by a film (Eq. 27 of the paper).
    @param a Plate size along x in m.
    @param b Plate size along y in m.
    @param c Source size along x in m.
    @param d Source size along y in m.
    @param xc Source centre x in m.
    @param yc Source centre y in m.
    @param t Plate thickness in m.
    @param k Conductivity in W/mK.
    @param h Film coefficient of the bottom face in W/m2K.
    @param q Heat in W.
    @param terms Number of terms in each series.
    @return Mean rise of the source in K.
    """
    def f(z):
        # Eq. (18); written with tanh to avoid overflow
        th = np.tanh(z * t)
        return (z * th + h / k) / (z + (h / k) * th)

    u1 = q / (a * b) * (t / k + 1.0 / h)                                            # Eq. (28)
    m = np.arange(1, terms + 1)
    lam, dl = m * np.pi / a, m * np.pi / b
    # Eq. (20) and the matching term of Eq. (27)
    am = 2 * q * (np.sin((2 * xc + c) / 2 * lam) - np.sin((2 * xc - c) / 2 * lam)) / (a * b * c * k * lam ** 2 * f(lam))
    an = 2 * q * (np.sin((2 * yc + d) / 2 * dl) - np.sin((2 * yc - d) / 2 * dl)) / (a * b * d * k * dl ** 2 * f(dl))
    s1 = 2 * np.sum(am * np.cos(lam * xc) * np.sin(0.5 * lam * c) / (lam * c))
    s2 = 2 * np.sum(an * np.cos(dl * yc) * np.sin(0.5 * dl * d) / (dl * d))
    L, D = np.meshgrid(lam, dl, indexing="ij")
    beta = np.sqrt(L ** 2 + D ** 2)
    amn = 16 * q * np.cos(L * xc) * np.sin(0.5 * L * c) * np.cos(D * yc) * np.sin(0.5 * D * d) / (a * b * c * d * k * beta * L * D * f(beta))     # Eq. (24)
    s3 = 4 * np.sum(amn * np.cos(D * yc) * np.sin(0.5 * D * d) * np.cos(L * xc) * np.sin(0.5 * L * c) / (L * c * D * d))
    return float(u1 + s1 + s2 + s3)


def column_rise(power, area, layers, h_top, h_bottom):
    """!
    @brief Exact rise of the top face of a 1D column heated over its whole top face, with films on both faces.
    @param power Heat in W entering the top face.
    @param area Area in m2.
    @param layers List of (thickness m, conductivity W/mK) from the top down.
    @param h_top Top film in W/m2K.
    @param h_bottom Bottom film in W/m2K.
    @return Rise of the top face in K (parallel of the top film and the series path to the bottom film).
    """
    r_path = sum(t / k for t, k in layers) / area + 1.0 / (h_bottom * area)
    r_top = 1.0 / (h_top * area) if h_top > 0 else np.inf
    return float(power / (1.0 / r_path + 1.0 / r_top))
