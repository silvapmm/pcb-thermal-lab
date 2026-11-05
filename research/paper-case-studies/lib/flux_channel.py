#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file flux_channel.py
@brief The thermal spreading resistance of a rectangular source on an orthotropic rectangular flux channel with a cooled base: equations 48 to 51 of Muzychka, Yovanovich and Culham (2004),
       J. Thermophysics and Heat Transfer 18 (1) 45-51, evaluated by a direct double series. Imports nothing from pcbthermal.
@details Geometry (Fig. 8, page 49; a, b, c, d are HALF sizes: the channel is 2c x 2d, the source 2a x 2b at its centre; the quarter 0..c, 0..d with the source at the corner 0..a, 0..b carries a
         quarter of the heat at the same temperatures): thickness t, in-plane conductivity k_xy (x and y), through-plane k_z; a uniform flux over the source, the rest of the top face adiabatic,
         the sides adiabatic, the bottom face cooled with a film h to a fluid at T_f.
         R_s is per watt of the WHOLE source (heat 4 a b q). Checked against the half-space value of a square source under a uniform flux, R_s k (2a) = I / (2 pi) = 0.4732 with I the mean
         reciprocal distance of a unit square, computed independently in the tests by a double integral; the series approach it from below as the channel and the depth grow (0.461 for
         c = 50 a, t = 100 a). A first reading that took R_s per watt of the quarter was 4 times too small and was found by that test.
         Orthotropic transformation (equations 48, 49, 57, 58): xi = z / gamma, gamma = sqrt(k_z / k_xy), the system becomes isotropic with k_eff = sqrt(k_xy k_z) and t_eff = t / gamma.
         Equation 50 (page 50, read from the page image): R_s = 1 / (2 a^2 c d k_eff) sum_m sin^2(a delta_m) / delta_m^3 phi(delta_m) + 1 / (2 b^2 c d k_eff) sum_n sin^2(b lambda_n) /
         lambda_n^3 phi(lambda_n) + 1 / (a^2 b^2 c d k_eff) sum_m sum_n sin^2(a delta_m) sin^2(b lambda_n) / (delta_m^2 lambda_n^2 beta_mn) phi(beta_mn), delta_m = m pi / c, lambda_n = n pi / d,
         beta_mn = sqrt(delta_m^2 + lambda_n^2); equation 51: phi(zeta) = [(e^(2 zeta t_eff) + 1) zeta t_eff - (1 - e^(2 zeta t_eff)) h t_eff / k_eff] / [(e^(2 zeta t_eff) - 1) zeta t_eff +
         (1 + e^(2 zeta t_eff)) h t_eff / k_eff], which is (x + Bi tanh x) / (Bi + x tanh x) with x = zeta t_eff and Bi = h t_eff / k_eff.
         The printed equation 51 reads "zeta t_eff" in the exponent and in the first term (the image); the text printed by the OCR lost it. It was read from the image of page 50.
         R_s is the part of the resistance beyond the one-dimensional one: R_total = R_s + t / (4 k_z c d) + 1 / (4 h c d) per watt of the whole source, for its mean temperature (the one-dimensional part
         t_eff / (k_eff 4 c d) is t / (4 k_z c d)); R_s vanishes for a = c and b = d (checked by the tests).
         The series converge like 1 / m^3 and 1 / m^2: the double sum is evaluated by numpy outer products up to n_max terms in each direction and the tail is NOT extrapolated; the tests
         and the study print the dependence on n_max.
"""

import numpy as np


def phi(zeta, t_eff, k_eff, h):
    """!
    @brief Equation 51: the film-and-thickness factor of one eigenvalue, in the numerically stable tanh form.
    @param zeta Eigenvalue(s) in 1/m (array or float).
    @param t_eff Effective thickness t / gamma in m.
    @param k_eff Effective conductivity sqrt(k_xy k_z) in W/mK.
    @param h Film coefficient of the base in W/m2K (np.inf for an isothermal base).
    @return numpy.ndarray phi, between tanh(zeta t_eff) (h = inf) and 1 (h = 0).
    """
    x = np.asarray(zeta, float) * t_eff
    th = np.tanh(x)
    if np.isinf(h):
        return th
    bi = h * t_eff / k_eff
    return (x + bi * th) / (bi + x * th)


def spreading_resistance(a, b, c, d, t, k_xy, k_z, h, n_max=2000):
    """!
    @brief Equation 50: the spreading resistance of an a x b source at the corner of a c x d orthotropic channel.
    @param a Source size in x in m (0 < a <= c).
    @param b Source size in y in m (0 < b <= d).
    @param c Channel size in x in m.
    @param d Channel size in y in m.
    @param t Thickness in m.
    @param k_xy In-plane conductivity in W/mK.
    @param k_z Through-plane conductivity in W/mK.
    @param h Film coefficient of the base in W/m2K (np.inf for isothermal).
    @param n_max Terms of each series (the double sum has n_max^2 terms).
    @return float R_s in K/W per watt of the whole source (2a x 2b in the channel 2c x 2d).
    @throws ValueError If the source is larger than the channel.
    """
    if a > c * (1 + 1e-12) or b > d * (1 + 1e-12):
        raise ValueError("the source must not be larger than the channel")
    gamma = np.sqrt(k_z / k_xy)
    k_eff, t_eff = np.sqrt(k_xy * k_z), t / gamma
    m = np.arange(1, n_max + 1)
    dm, ln = m * np.pi / c, m * np.pi / d
    s1 = np.sum(np.sin(a * dm) ** 2 / dm ** 3 * phi(dm, t_eff, k_eff, h)) / (2.0 * a * a * c * d * k_eff)
    s2 = np.sum(np.sin(b * ln) ** 2 / ln ** 3 * phi(ln, t_eff, k_eff, h)) / (2.0 * b * b * c * d * k_eff)
    # the double sum by blocks of rows so that the memory stays small
    s3 = 0.0
    sa, sb = np.sin(a * dm) ** 2 / dm ** 2, np.sin(b * ln) ** 2 / ln ** 2
    for i0 in range(0, n_max, 500):
        beta = np.sqrt(dm[i0:i0 + 500, None] ** 2 + ln[None, :] ** 2)
        s3 += np.sum(sa[i0:i0 + 500, None] * sb[None, :] / beta * phi(beta, t_eff, k_eff, h))
    s3 /= a * a * b * b * c * d * k_eff
    return float(s1 + s2 + s3)


def total_resistance(a, b, c, d, t, k_xy, k_z, h, n_max=2000):
    """!
    @brief The mean source temperature rise per watt: spreading plus the one-dimensional resistance of the channel.
    @param a Source size in x in m.
    @param b Source size in y in m.
    @param c Channel size in x in m.
    @param d Channel size in y in m.
    @param t Thickness in m.
    @param k_xy In-plane conductivity in W/mK.
    @param k_z Through-plane conductivity in W/mK.
    @param h Film coefficient of the base in W/m2K.
    @param n_max Terms of each series.
    @return float R_total in K/W per watt of the whole source: R_s + t / (4 k_z c d) + 1 / (4 h c d).
    """
    one_d = t / (4.0 * k_z * c * d) + (0.0 if np.isinf(h) else 1.0 / (4.0 * h * c * d))
    return spreading_resistance(a, b, c, d, t, k_xy, k_z, h, n_max) + one_d
