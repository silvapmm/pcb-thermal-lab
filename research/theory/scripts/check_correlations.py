#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_correlations.py
@brief Numerical checks of the correlations and formulas that the reference compilation of the maintainer quotes, so that what was transcribed or written from memory is at least internally consistent: the 2D Hashin-Shtrikman bounds and the Keller-Dykhne product, the Bar-Cohen and Rohsenow composite and its limits, the Elenbaas correlation, the two Churchill-Chu vertical-plate forms, the Hollands (1984) equation and the Churchill-Chu all-range form against the worked values in the source of the Python `ht` library (read from the package, MIT licence; its examples are given with the Grashof number, not the Rayleigh number), and the series and parallel conductivities of the printed board example.
@details Prints each check with the value found and the value expected; nothing is tuned. Run: .venv/bin/python research/theory/scripts/check_correlations.py (from the repository root).
"""

import numpy as np


def hs_2d(phi1, s1, s2):
    """!
    @brief The 2D Hashin-Shtrikman bounds of an isotropic two-phase medium.
    @param phi1 Volume fraction of phase 1.
    @param s1 Conductivity of the poorer phase.
    @param s2 Conductivity of the better phase.
    @return Tuple (lower, upper).
    """
    phi2 = 1.0 - phi1
    lower = s1 + phi2 / (1.0 / (s2 - s1) + phi1 / (2.0 * s1))
    upper = s2 + phi1 / (1.0 / (s1 - s2) + phi2 / (2.0 * s2))
    return lower, upper


def churchill_chu_all(ra, pr):
    """!
    @brief Churchill and Chu vertical isothermal plate, valid for all Rayleigh numbers.
    @param ra Rayleigh number.
    @param pr Prandtl number.
    @return Nusselt number.
    """
    return (0.825 + 0.387 * ra ** (1 / 6) / (1 + (0.492 / pr) ** (9 / 16)) ** (8 / 27)) ** 2


def churchill_chu_laminar(ra, pr):
    """!
    @brief Churchill and Chu vertical plate, laminar form (Rayleigh number up to about 1e9).
    @param ra Rayleigh number.
    @param pr Prandtl number.
    @return Nusselt number.
    """
    return 0.68 + 0.670 * ra ** 0.25 / (1 + (0.492 / pr) ** (9 / 16)) ** (4 / 9)


def hollands_1984(pr, ra):
    """!
    @brief Hollands (1984) multi-Prandtl correlation for a horizontal layer heated from below, as **implemented** in the `ht` library (its documentation writes Ra^(1/5) inside the logarithm; the code uses Ra^(1/3), and only the code reproduces the library's own worked example).
    @param pr Prandtl number.
    @param ra Rayleigh number of the layer.
    @return Nusselt number.
    """
    k1 = 1.44 / (1 + 0.018 / pr + 0.00136 / pr ** 2)
    k2 = 75 * np.exp(1.5 * pr ** -0.5)
    pos = lambda x: max(x, 0.0)                                  # the bracket with a star keeps only its positive part
    return 1 + pos(1 - 1708 / ra) * pos(k1 + 2 * (ra ** (1 / 3) / k2) ** (1 - np.log(ra ** (1 / 3) / k2))) + pos((ra / 5803) ** (1 / 3) - 1)


def main():
    """!
    @brief Run the checks and print them.
    @return None.
    """
    lo, up = hs_2d(0.5, 1.0, 4.0)
    print(f"HS 2D, s1 = 1, s2 = 4, phi = 1/2: lower {lo:.4f} (13/7 = {13 / 7:.4f}), upper {up:.4f} (28/13 = {28 / 13:.4f}), product {lo * up:.4f} (s1 s2 = 4)")
    f = np.linspace(0.05, 0.95, 19)
    dev = max(abs(hs_2d(x, 1, 4)[0] * hs_2d(1 - x, 1, 4)[1] - 4) for x in f)
    print(f"Keller-Dykhne type product, lower(phi) x upper(1 - phi) against s1 s2: largest deviation {dev:.2e}")
    ras = np.logspace(-2, 4, 400)
    ras_s = 1e-6
    for ras_ in (1e-3, 1e5):
        nu = (576 / ras_ ** 2 + 2.873 / ras_ ** 0.5) ** -0.5
        print(f"Bar-Cohen and Rohsenow composite at Ra* = {ras_:g}: Nu {nu:.4g}; fully developed Ra*/24 = {ras_ / 24:.4g}; isolated plate 0.590 Ra*^(1/4) = {0.590 * ras_ ** 0.25:.4g}")
    print(f"Optimum spacing: 2.714^4 = {2.714 ** 4:.1f} (the optimum channel Rayleigh number; Simons quotes about 50 for Elenbaas)")
    for r in (1e-1, 1e2, 1e5):
        nu_e = r / 24 * (1 - np.exp(-35 / r)) ** 0.75
        print(f"Elenbaas at Ra* = {r:g}: Nu {nu_e:.4g} (Ra*/24 = {r / 24:.4g}, 0.62 Ra*^(1/4) = {0.62 * r ** 0.25:.4g})")
    for ra in (1e5, 1e7, 1e9):
        a, b = churchill_chu_all(ra, 0.71), churchill_chu_laminar(ra, 0.71)
        print(f"Churchill-Chu vertical plate, Pr 0.71, Ra {ra:g}: all-range {a:.2f}, laminar form {b:.2f} (difference {100 * (b / a - 1):+.1f} %)")
    ra_h = 5.54 * 3.21e8                                          # the `ht` example gives the Grashof number 3.21e8; Ra = Gr Pr
    print(f"Hollands 1984, Pr 5.54, Gr 3.21e8 (Ra = {ra_h:.4g}): {hollands_1984(5.54, ra_h):.2f} (the `ht` documentation example gives 69.0267)")
    print(f"Churchill-Chu vertical plate, Pr 0.69, Gr 2.63e9: {churchill_chu_all(0.69 * 2.63e9, 0.69):.2f} (the `ht` example, from Bergman and others, Example 9.2, gives 147.16)")
    k_par = (0.07 * 390 + 1.52 * 0.25) / 1.59
    k_ser = 1.59 / (0.07 / 390 + 1.52 / 0.25)
    print(f"Printed board of the 1998 article: in-plane {k_par:.2f} W/mK (article about 17.4), through-plane {k_ser:.4f} W/mK (article about 0.26)")


if __name__ == "__main__":
    main()
