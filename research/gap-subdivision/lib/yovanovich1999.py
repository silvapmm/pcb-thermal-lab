#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file yovanovich1999.py
@brief Eqs. 14 and 15 of Yovanovich, Muzychka and Culham (1999): spreading resistance of an isoflux rectangle on a two-layer rectangular flux channel with a film on the bottom.
@details M. M. Yovanovich, Y. S. Muzychka, J. R. Culham, "Spreading Resistance of Isoflux Rectangles and Strips on Compound Flux Channels", J. Thermophysics and Heat Transfer
         13 (4) (1999) 495-500 (read in full, open copy of the Waterloo microelectronics heat transfer laboratory). Source 2a x 2b centred on a channel 2c x 2d, layers t1 (k1) on top of
         t2 (k2), film h on the bottom, adiabatic sides and adiabatic top outside the source. Rs = (mean source - mean contact plane) / Q, Eq. 14 with phi of Eq. 15; the exponentials of
         Eq. 15 are divided through by exp(2 zeta (2 t1 + t2)) so that nothing overflows (the same function). Isotropic layers only.
"""

import numpy as np


def phi(zeta, t1, t2, k1, k2, h):
    """!
    @brief The function phi(zeta) of Eq. 15, rewritten with decaying exponentials.
    @param zeta Eigenvalue (delta_m, lambda_n or beta_mn) in 1/m (array).
    @param t1 Thickness of the layer under the source in m.
    @param t2 Thickness of the second layer in m.
    @param k1 Conductivity of the first layer in W/mK.
    @param k2 Conductivity of the second layer in W/mK.
    @param h Film coefficient of the bottom face in W/m2K.
    @return numpy.ndarray phi.
    """
    kap = k2 / k1
    alpha = (1 - kap) / (1 + kap)
    gam = (zeta + h / k2) / (zeta - h / k2)         # gamma = (zeta + Bi / (kappa L)) / (zeta - Bi / (kappa L)) with Bi / (kappa L) = h / k2
    e1, e2, e12 = np.exp(-2 * zeta * t1), np.exp(-2 * zeta * t2), np.exp(-2 * zeta * (t1 + t2))
    # Eq. 15 (page image, p. 496): the factor varphi multiplies both exp(2 zeta (2 t1 + t2)) and alpha exp(2 zeta (t1 + t2)); the text layer of the PDF misplaces the bracket
    num = alpha * e2 + e12 + gam * (1 + alpha * e1)
    den = alpha * e2 - e12 + gam * (1 - alpha * e1)
    return num / den


def spreading_resistance(a, b, c, d, t1, t2, k1, k2, h, terms=1500):
    """!
    @brief Rs of Eq. 14 for a source of half sides a, b on a channel of half sides c, d.
    @param a Half side of the source along x in m.
    @param b Half side of the source along y in m.
    @param c Half side of the channel along x in m.
    @param d Half side of the channel along y in m.
    @param t1 Thickness of the top layer in m.
    @param t2 Thickness of the second layer in m.
    @param k1 Conductivity of the top layer in W/mK.
    @param k2 Conductivity of the second layer in W/mK.
    @param h Film coefficient of the bottom in W/m2K.
    @param terms Number of terms of each series.
    @return Rs in K/W.
    """
    m = np.arange(1, terms + 1)
    dm, ln = m * np.pi / c, m * np.pi / d
    s1 = np.sum(np.sin(a * dm) ** 2 / dm ** 3 * phi(dm, t1, t2, k1, k2, h)) / (2 * a ** 2 * c * d * k1)
    s2 = np.sum(np.sin(b * ln) ** 2 / ln ** 3 * phi(ln, t1, t2, k1, k2, h)) / (2 * b ** 2 * c * d * k1)
    dd, ll = np.meshgrid(dm, ln, indexing="ij")
    beta = np.sqrt(dd ** 2 + ll ** 2)
    s3 = np.sum(np.sin(a * dd) ** 2 * np.sin(b * ll) ** 2 / (dd ** 2 * ll ** 2 * beta) * phi(beta, t1, t2, k1, k2, h)) / (a ** 2 * b ** 2 * c * d * k1)
    return float(s1 + s2 + s3)
