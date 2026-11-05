#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file laws.py
@brief The candidate natural-convection laws of a board face as functions of Ra (L = A/P for horizontal plates, the height for vertical ones), the board sizes, and the program's laws; for the S4 study.
@details The horizontal laws already coded and reviewed in research/horizontal-plate-h/lib/correlations.py are imported, not copied (that folder is in `develop`); this module adds
         the 1/5 downward laws used as candidates, the vertical Churchill-Chu forms (copied from the formulas printed by Lienhard 2024, eq. 8.13a/b) and the helpers that turn a
         board size and a temperature rise into Ra. Sources and reading status: README section 2 and research/theory/BIBLIOGRAPHY.md.

         Candidate pairs (face up, face down), all with L = A/P:
         * `program`: 0.54 Ra^(1/4) [0.15 Ra^(1/3) above 1e7] and 0.27 Ra^(1/4);
         * `RH+program-down`: Raithby-Hollands 8.37a/b with the thick-layer correction (Lienhard pp 435-436) above, the program's lower face;
         * `RH+GL`: Raithby-Hollands above and 0.475 Ra^(1/5) below (Goldstein-Lau mean laminar law as quoted in Yovanovich and Jafarpur 1993, p 8: second hand);
         * `RH+FI`: Raithby-Hollands above and Fujii-Imura 0.58 Ra_W^(1/5) with W = 2 A/P (a long strip) below (Lienhard eq. 8.38, water data, 2D plate, 1e6 to 1e11: outside its range here);
         * `Jaffer`: Jaffer (2023) eq. 30 above and eq. 56 below with the square metric.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "research", "horizontal-plate-h", "lib"))
sys.path.insert(0, ROOT)

import correlations as C  # noqa: E402

PR = 0.71


def goldstein_lau_down(ra):
    """!
    @brief The mean laminar lower-face law of Goldstein and Lau as quoted second hand (Nu = 0.475 Ra^(1/5), L = A/P).
    @param ra Rayleigh number of L = A/P.
    @return Nu.
    """
    return 0.475 * np.asarray(ra, dtype=float) ** 0.2


def churchill_chu_general(ra, pr=PR):
    """!
    @brief Churchill and Chu, all Ra (Lienhard eq. 8.13b): Nu = {0.825 + 0.387 Ra^(1/6) / [1 + (0.492/Pr)^(9/16)]^(8/27)}^2.
    @param ra Rayleigh number of the plate height.
    @param pr Prandtl number.
    @return Nu.
    """
    ra = np.asarray(ra, dtype=float)
    return (0.825 + 0.387 * ra ** (1.0 / 6.0) / (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (8.0 / 27.0)) ** 2


def churchill_chu_laminar(ra, pr=PR):
    """!
    @brief Churchill and Chu, laminar (Lienhard eq. 8.13a, Ra < 1e9): Nu = 0.68 + 0.670 Ra^(1/4) / [1 + (0.492/Pr)^(9/16)]^(4/9).
    @param ra Rayleigh number of the plate height.
    @param pr Prandtl number.
    @return Nu.
    """
    return 0.68 + 0.670 * np.asarray(ra, dtype=float) ** 0.25 / (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (4.0 / 9.0)


PAIRS = {
    "program": (C.program_up, C.program_down),
    "RH+program-down": (C.raithby_hollands_up, C.program_down),
    "RH+GL": (C.raithby_hollands_up, goldstein_lau_down),
    "RH+FI": (C.raithby_hollands_up, lambda ra: C.fujii_imura_down(ra, 2.0)),
    "Jaffer": (C.jaffer_up, lambda ra: C.jaffer_down_shape(ra, 2.0)),
}


def air_ra(dt, length, t_amb=25.0):
    """!
    @brief Rayleigh number of a surface dt kelvin above the air, with the program's air properties at the film temperature.
    @param dt Surface excess in kelvin.
    @param length Characteristic length in metres.
    @param t_amb Ambient in degC.
    @return Ra.
    """
    from pcbthermal import convection
    props = convection.air_properties(t_amb + 0.5 * dt)
    return convection.rayleigh(dt, length, props)


def a_over_p(w_mm, h_mm):
    """!
    @brief Characteristic length A/P of a rectangular face.
    @param w_mm Width in mm.
    @param h_mm Height in mm.
    @return Length in metres.
    """
    return (w_mm * 1e-3) * (h_mm * 1e-3) / (2.0 * ((w_mm + h_mm) * 1e-3))
