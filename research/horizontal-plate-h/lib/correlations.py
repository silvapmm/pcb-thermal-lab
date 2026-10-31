#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file correlations.py
@brief The correlations of the average Nusselt number of an isothermal HORIZONTAL plate, upper and lower face, with the characteristic length L = A/P, as written in the sources (and the program's own), plus a context that runs the program with another level on a copy in memory.
@details Nu = h L / k, Ra = g beta dT L^3 / (nu alpha), L = A/P (area over perimeter of one face). Levels:

         * `program_up`: Nu = 0.54 Ra^(1/4) up to Ra = 1e7, 0.15 Ra^(1/3) above (Lloyd and Moran 1974 as quoted by textbooks; the program's `convection.h_natural_horizontal`);
         * `program_down`: Nu = 0.27 Ra^(1/4) (the program);
         * `jaffer_up`: Jaffer (2023), equation 30: Nu = [0.642 + 0.370 Ra^(1/6)]^2 (no Prandtl number: the flow goes straight up);
         * `jaffer_down`: Jaffer (2023), equation 46/56 for L = A/P of a strip (half width) or disc (harmonic-mean length): Nu = 0.341 + 0.550 (Ra / Xi_R)^(1/5),
           Xi_R = [1 + (0.477/Pr)^(3/5)]^(5/3) (equation 51); the coefficients 0.341 = Nu0'/4 and 0.550 are the numbers printed in the paper as "approximately";
         * `schulenberg_strip`: Schulenberg (1985, KfK 3713 equation 92 as printed): Nu = 0.571 Pr^(1/5) Ra^(1/5) / [1 + 1.156 Pr^(3/5)]^(1/3), L = half width of the strip;
           `schulenberg_strip_jaffer`: the same with the coefficients Jaffer (2023) gives as "corrected" (0.631, 1.56), equation 4;
         * `schulenberg_disc`: Nu_R = 0.705 Pr^(1/5) Ra_R^(1/5) / [1 + 1.48 Pr^(3/5)]^(1/3) with L = R (equation 94), converted to L = A/P = R/2 by Nu_L = Nu_R / 2 and Ra_L = Ra_R / 8.

         The program is not edited: `use_horizontal` replaces `pcbthermal.convection.h_natural_horizontal` for the duration of a run.
"""

import contextlib
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pcbthermal import convection                              # noqa: E402

PR = 0.71


def program_up(ra):
    """!
    @brief The program's upper-face correlation.
    @param ra Rayleigh number of L = A/P.
    @return Nu.
    """
    ra = np.asarray(ra, dtype=float)
    return np.where(ra <= 1e7, 0.54 * ra ** 0.25, 0.15 * ra ** (1.0 / 3.0))


def program_down(ra):
    """!
    @brief The program's lower-face correlation.
    @param ra Rayleigh number of L = A/P.
    @return Nu.
    """
    return 0.27 * np.asarray(ra, dtype=float) ** 0.25


def jaffer_up(ra):
    """!
    @brief Jaffer's upper-face formula (equation 30), valid for 1 < Ra < 1e12 in the paper's data sets.
    @param ra Rayleigh number of L = A/P.
    @return Nu.
    """
    return (0.642 + 0.370 * np.asarray(ra, dtype=float) ** (1.0 / 6.0)) ** 2


def xi_r(pr=PR):
    """!
    @brief The Prandtl scaling of the downward formulas, Xi_R(Pr) = [1 + (0.477/Pr)^(3/5)]^(5/3) (Jaffer equation 51).
    @param pr Prandtl number.
    @return float.
    """
    return (1.0 + (0.477 / pr) ** 0.6) ** (5.0 / 3.0)


def jaffer_down(ra, pr=PR):
    """!
    @brief Jaffer's lower-face formula (equation 46 with the Prandtl scaling of equation 51), L = A/P of a strip.
    @param ra Rayleigh number of L = A/P.
    @param pr Prandtl number.
    @return Nu.
    """
    return 0.341 + 0.550 * (np.asarray(ra, dtype=float) / xi_r(pr)) ** 0.2


def jaffer_down_shape(ra, q, pr=PR):
    """!
    @brief Jaffer's lower-face formula for a shape whose downward metric L_R (half the shorter side of a rectangle, 2R/pi of a disc) is q times its A/P, returned as Nu of L = A/P.
    @details Equation 56 is written with L_R: Nu_R = 0.341 + 0.550 (Ra_R / Xi_R)^(1/5), Ra_R = q^3 Ra, Nu = h L / k so Nu_AP = Nu_R / q. A long strip has q = 1, a square 2, a disc 4/pi.
    @param ra Rayleigh number of L = A/P.
    @param q Ratio L_R / (A/P) of the shape.
    @param pr Prandtl number.
    @return Nu of L = A/P.
    """
    return jaffer_down(q ** 3 * np.asarray(ra, dtype=float), pr) / q


def schulenberg_strip(ra, pr=PR, jaffer_coefficients=False):
    """!
    @brief Schulenberg's isothermal strip below a hot plate (L = half width = A/P).
    @param ra Rayleigh number of L.
    @param pr Prandtl number.
    @param jaffer_coefficients False: 0.571 and 1.156 as printed in KfK 3713 equation 92; True: 0.631 and 1.56, Jaffer's equation 4 (both have the same large-Pr limit 0.544).
    @return Nu.
    """
    a, b = (0.631, 1.56) if jaffer_coefficients else (0.571, 1.156)
    return a * pr ** 0.2 * np.asarray(ra, dtype=float) ** 0.2 / (1.0 + b * pr ** 0.6) ** (1.0 / 3.0)


def schulenberg_disc(ra_l, pr=PR):
    """!
    @brief Schulenberg's isothermal disc below a hot plate (equation 94, L = R), converted to L = A/P = R/2.
    @param ra_l Rayleigh number of L = A/P = R/2 (Ra_R = 8 Ra_L).
    @param pr Prandtl number.
    @return Nu of L = A/P.
    """
    ra_r = 8.0 * np.asarray(ra_l, dtype=float)
    nu_r = 0.705 * pr ** 0.2 * ra_r ** 0.2 / (1.0 + 1.48 * pr ** 0.6) ** (1.0 / 3.0)
    return 0.5 * nu_r


def lloyd_moran_up_laminar(ra):
    """!
    @brief The laminar branch of Lloyd and Moran as quoted (0.54 Ra^(1/4), 2.2e4 to 8e6), without the turbulent branch.
    @param ra Rayleigh number.
    @return Nu.
    """
    return 0.54 * np.asarray(ra, dtype=float) ** 0.25


def make_horizontal(up_fn, down_fn):
    """!
    @brief A replacement of `convection.h_natural_horizontal` built from two Nusselt functions of Ra (L = A/P).
    @param up_fn Nu(Ra) of the upper face (a hot face looking up; a cold one swaps the faces as in the program).
    @param down_fn Nu(Ra) of the lower face.
    @return Function with the signature of the program's `h_natural_horizontal`.
    """
    def h_horizontal(t_surface, t_ambient, length, facing_up):
        """!
        @brief Natural convection coefficient of a horizontal plate with the chosen levels.
        @param t_surface Mean surface temperature in degC.
        @param t_ambient Air temperature in degC.
        @param length Characteristic length A/P in metres.
        @param facing_up True if the surface faces up.
        @return Tuple (h in W/m2K, Rayleigh number).
        """
        dt = t_surface - t_ambient
        props = convection.air_properties(0.5 * (t_surface + t_ambient))
        ra = convection.rayleigh(max(abs(dt), 1e-3), length, props)
        up = facing_up if dt >= 0 else not facing_up
        nu = float((up_fn if up else down_fn)(ra))
        return nu * props["k"] / length, ra
    return h_horizontal


@contextlib.contextmanager
def use_horizontal(up_fn, down_fn):
    """!
    @brief Run the program with other horizontal levels, on a copy in memory; the function is restored on exit.
    @param up_fn Nu(Ra) of the upper face.
    @param down_fn Nu(Ra) of the lower face.
    @return Context manager.
    """
    original = convection.h_natural_horizontal
    convection.h_natural_horizontal = make_horizontal(up_fn, down_fn)
    try:
        yield
    finally:
        convection.h_natural_horizontal = original
