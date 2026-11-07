#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file series.py
@brief The closed forms of Yovanovich, Muzychka and Culham (1999) for the strip source (equations 23 to 28), as printed, and the strip-on-a-cell relation used to compare them with a numerical solve.
@details All of them give the dimensionless spreading resistance psi = k R_s of an isoflux (or other) strip of half-width a = eps c on a channel of half-width c (equation numbers of the paper, journal pages 495 to 500;
         the numbers of Table 2 are on page 499). Nothing here imports the program.
"""

import numpy as np
from scipy import special


def psi_finite(eps, tau, bi, n_max=20000):
    """!
    @brief Equation 23: isoflux strip on a finite isotropic channel with a film at the base.
    @param eps Relative strip size a / c.
    @param tau Relative thickness t / c.
    @param bi Biot number h c / k (use a very large number for an isothermal base).
    @param n_max Terms of the series.
    @return float psi = k R_s (dimensionless).
    """
    n = np.arange(1, n_max + 1)
    th = np.tanh(n * np.pi * tau)
    bracket = (n * np.pi + bi * th) / (n * np.pi * th + bi)
    return float((np.sin(n * np.pi * eps) ** 2 / n ** 3 * bracket).sum() / (np.pi ** 3 * eps ** 2))


def psi_isoflux(eps, n_max=200000):
    """!
    @brief Equation 24: isoflux strip on a semi-infinite isotropic channel.
    @param eps Relative strip size.
    @param n_max Terms of the series.
    @return float psi.
    """
    n = np.arange(1, n_max + 1)
    return float((np.sin(n * np.pi * eps) ** 2 / n ** 3).sum() / (np.pi ** 3 * eps ** 2))


def psi_equivalent_isothermal(eps, n_max=200000):
    """!
    @brief Equation 26: the equivalent isothermal flux distribution (mu = -1/2).
    @param eps Relative strip size.
    @param n_max Terms.
    @return float psi.
    """
    n = np.arange(1, n_max + 1)
    return float((np.sin(n * np.pi * eps) * special.j0(n * np.pi * eps) / n ** 2).sum() / (np.pi ** 2 * eps))


def psi_parabolic(eps, n_max=200000):
    """!
    @brief Equation 28: parabolic flux distribution (mu = +1/2).
    @param eps Relative strip size.
    @param n_max Terms.
    @return float psi.
    """
    n = np.arange(1, n_max + 1)
    return float(2.0 * (np.sin(n * np.pi * eps) * special.j1(n * np.pi * eps) / n ** 3).sum() / (np.pi ** 3 * eps ** 2))


def psi_true_isothermal(eps):
    """!
    @brief Equation 27: the true isothermal strip, kR_s = (1/pi) ln(1 / sin(pi eps / 2)).
    @param eps Relative strip size.
    @return float psi.
    """
    return float(np.log(1.0 / np.sin(0.5 * np.pi * eps)) / np.pi)


def psi_step(eps):
    """!
    @brief Equation 29: the abrupt change of channel width from 2a to 2b (eps = a / b < 1), closed form of Smythe (ref. 4) as printed on page 500.
    @param eps Ratio of the widths, a / b.
    @return float psi.
    @note Printed (page 500, image): kR_s = (1/2 pi) [ (eps + 1/eps) ln((1+eps)/(1-eps)) + 2 ln((1-eps^2)/(4 eps)) ]; it reproduces the Eq. (29) row of Table 3.
    """
    return float(((eps + 1.0 / eps) * np.log((1.0 + eps) / (1.0 - eps)) + 2.0 * np.log((1.0 - eps ** 2) / (4.0 * eps))) / (2.0 * np.pi))
