#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file correlations.py
@brief Natural convection correlations written from the sources that were opened, independent of `pcbthermal/convection.py`.
@details Sources (see README.md): Lienhard, A Heat Transfer Textbook v6.00 (open): equations 8.13a, 8.13b, 8.35, 8.37a, 8.37b, 8.38;
ASHRAE 2005 preprint OR-05-4-3: equations 9 to 14 (ISO 15099 / Rohsenow 1985 and Hollands et al. 1976); the `ht` package source for the 1984 form.
"""

import math


def churchill_chu_laminar(ra, pr):
    """!
    @brief Churchill and Chu laminar form, Lienhard equation 8.13a (Ra up to 1e9).
    @param ra Rayleigh number.
    @param pr Prandtl number.
    @return Nusselt number.
    """
    return 0.68 + 0.670 * ra ** 0.25 / (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (4.0 / 9.0)


def churchill_chu_general(ra, pr):
    """!
    @brief Churchill and Chu all-range form, Lienhard equation 8.13b.
    @param ra Rayleigh number.
    @param pr Prandtl number.
    @return Nusselt number.
    """
    return (0.825 + 0.387 * ra ** (1.0 / 6.0) / (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (8.0 / 27.0)) ** 2


def _pos(x):
    """!
    @brief Positive part, the bracket with a star of the sources.
    @param x Number.
    @return max(x, 0).
    """
    return x if x > 0.0 else 0.0


def hollands_1976(ra):
    """!
    @brief Hollands, Unny, Raithby and Konicek (1976) horizontal air layer, ASHRAE preprint equation 14.
    @param ra Rayleigh number.
    @return Nusselt number.
    """
    return 1.0 + 1.44 * _pos(1.0 - 1708.0 / ra) + _pos((ra / 5830.0) ** (1.0 / 3.0) - 1.0)


def hollands_iso15099(ra):
    """!
    @brief ISO 15099 / Rohsenow (1985) form, ASHRAE preprint equations 9 to 12 with k1 = 1.40 and k2 = Ra^(1/3)/450.5.
    @param ra Rayleigh number.
    @return Nusselt number (the critical number of equation 13 is replaced by the plane-layer value 1708, which is its limit for a wide layer).
    """
    k1 = 1.40
    k2 = ra ** (1.0 / 3.0) / 450.5
    t2 = k1 + 2.0 * k2 ** (1.0 - math.log(k2))
    return 1.0 + _pos(1.0 - 1708.0 / ra) * _pos(t2) + _pos((ra / 5830.0) ** (1.0 / 3.0) - 1.0)


def hollands_ht(pr, ra, root=3.0, ra_c_third=5803.0):
    """!
    @brief Hollands (1984) multi-Prandtl equation as coded in `ht` 1.2.0 (Rac 1708), with the root inside the logarithm selectable (3 as coded, 5 as documented).
    @details The term is `2 (Ra^(1/3)/k2)^(1 - ln(Ra^(1/root)/k2))`: the base always carries the cube root, and only the root inside the logarithm changes, which is
             exactly the difference between the `ht` code and its docstring (read in `ht` 1.2.0, `Nu_Nusselt_Rayleigh_Hollands`). The first version of this function applied
             the fifth root to the base as well, a variant that neither the code nor the documentation prints (review, README 6).
    @param pr Prandtl number.
    @param ra Rayleigh number.
    @param root Denominator of the exponent of Ra inside the logarithm (3 as coded, 5 as documented).
    @param ra_c_third Constant of the last bracket (5803 in `ht`, 5830 in the 1976 equation).
    @return Nusselt number.
    """
    if ra < 1708.0:
        return 1.0
    k1 = 1.44 / (1.0 + 0.018 / pr + 0.00136 / (pr * pr))
    k2 = 75.0 * math.exp(1.5 * pr ** -0.5)
    base = ra ** (1.0 / 3.0) / k2                               # the base of the power: cube root in the code and in the documentation
    inner = ra ** (1.0 / root) / k2                             # inside the logarithm: cube root in the code, fifth root in the documentation
    t2 = k1 + 2.0 * base ** (1.0 - math.log(inner))
    return 1.0 + _pos(1.0 - 1708.0 / ra) * _pos(t2) + _pos((ra / ra_c_third) ** (1.0 / 3.0) - 1.0)


def raithby_hollands_low(ra, pr):
    """!
    @brief Lienhard 8.37a with the thick-boundary-layer correction 8.37b (Nu_corrected = 1.4 / ln(1 + 1.4/Nu), applied when Nu <= 10).
    @param ra Rayleigh number on L* = A/P.
    @param pr Prandtl number.
    @return Nusselt number.
    """
    nu = 0.560 * ra ** 0.25 / (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (4.0 / 9.0)
    if nu <= 10.0:
        nu = 1.4 / math.log(1.0 + 1.4 / nu)
    return nu


def raithby_hollands_up(ra, pr):
    """!
    @brief Upward-facing hot plate, Raithby and Hollands: Lienhard 8.35 above Ra 1e7, 8.37a with the correction 8.37b below.
    @param ra Rayleigh number on L = A/P.
    @param pr Prandtl number.
    @return Nusselt number.
    """
    if ra >= 1e7:
        return 0.14 * ra ** (1.0 / 3.0) * (1.0 + 0.0107 * pr) / (1.0 + 0.01 * pr)
    return raithby_hollands_low(ra, pr)


def fujii_imura_down(ra):
    """!
    @brief Fujii and Imura downward-facing hot plate, Lienhard 8.38 (valid 1e6 to 1e9 for a two-dimensional, nearly horizontal plate).
    @note The length of Ra and Nu is the **width L of the plate** (Lienhard, book page 437: "plates of width L"), not the A/P of 8.37a; for a strip of width W, A/P = W/2.
    @param ra Rayleigh number on the plate width.
    @return Nusselt number.
    """
    return 0.58 * ra ** 0.2
