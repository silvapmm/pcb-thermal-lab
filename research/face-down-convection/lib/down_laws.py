#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file down_laws.py
@brief Candidate laws for the natural convection of the horizontal face turned down (hot side down), and their use in the program on a copy in memory.
@details All laws are Nu(Ra) on L = A/P with Pr = 0.71 (air). The program's law is 0.27 Ra^(1/4) (the McAdams form; from memory in the program). The candidates:
         * `incropera7`  : 0.52 Ra^(1/5), 1e4 <= Ra <= 1e9 (Incropera, later editions; status M: the book was not opened);
         * `gl_mean`     : 0.475 Ra^(1/5), mean of the laminar Goldstein-Lau constants 0.44 to 0.527 (read on p 8 of Yovanovich and Jafarpur 1993);
         * `gl_strip`    : 0.524 Ra^(1/5), the numerical strip of Goldstein and Lau, 40 < Ra < 8e3 (same page);
         * `vdi`         : 0.6 (Ra f1)^(1/5), f1 = [1 + (0.492/Pr)^(9/16)]^(-16/9), L = A/P (VDI Heat Atlas, as quoted by the documentation of the library `ht`: S);
         * `rohsenow`    : Nu_T = 0.527 Ra^(1/5) / [1 + (1.9/Pr)^0.9]^(2/9), Nu = 2.5 / ln(1 + 2.5/Nu_T) (Rohsenow, Hartnett and Cho 1998, as quoted by `ht`: S, not checked);
         * Fujii-Imura, Kadambi-Drake, Jaffer 56: imported from research/horizontal-plate-h/lib/correlations.py (reviewed there).
         `use_down(fn)` replaces `pcbthermal.convection.h_natural_horizontal` in memory by a copy of the program's function whose lower face uses fn; nothing on disk changes.
"""

import contextlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "research", "horizontal-plate-h", "lib"))
sys.path.insert(0, ROOT)

import correlations as C  # noqa: E402
from pcbthermal import convection  # noqa: E402

PR = 0.71


def program_down(ra):
    """!
    @brief The program's lower-face law.
    @param ra Rayleigh number of A/P.
    @return Nu.
    """
    return 0.27 * np.asarray(ra, dtype=float) ** 0.25


def incropera7(ra):
    """!
    @brief Nu = 0.52 Ra^(1/5) (Incropera, later editions, from memory, range 1e4 to 1e9).
    @param ra Rayleigh number of A/P.
    @return Nu.
    """
    return 0.52 * np.asarray(ra, dtype=float) ** 0.2


def gl_mean(ra):
    """!
    @brief Mean laminar Goldstein-Lau constant, Nu = 0.475 Ra^(1/5).
    @param ra Rayleigh number of A/P.
    @return Nu.
    """
    return 0.475 * np.asarray(ra, dtype=float) ** 0.2


def gl_strip(ra):
    """!
    @brief Numerical strip of Goldstein and Lau, Nu = 0.524 Ra^(1/5) (40 < Ra < 8e3).
    @param ra Rayleigh number of A/P.
    @return Nu.
    """
    return 0.524 * np.asarray(ra, dtype=float) ** 0.2


def vdi(ra, pr=PR):
    """!
    @brief VDI lower-surface law as quoted second hand, Nu = 0.6 (Ra f1)^(1/5).
    @param ra Rayleigh number of A/P.
    @param pr Prandtl number.
    @return Nu.
    """
    f1 = (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (-16.0 / 9.0)
    return 0.6 * (np.asarray(ra, dtype=float) * f1) ** 0.2


def rohsenow(ra, pr=PR):
    """!
    @brief Rohsenow-Hartnett-Cho lower-surface form as quoted second hand (thick-layer corrected).
    @param ra Rayleigh number of A/P.
    @param pr Prandtl number.
    @return Nu.
    """
    nt = 0.527 * np.asarray(ra, dtype=float) ** 0.2 / (1.0 + (1.9 / pr) ** 0.9) ** (2.0 / 9.0)
    return 2.5 / np.log1p(2.5 / nt)


def fujii_strip(ra):
    """!
    @brief Fujii-Imura on the width of a long strip (W = 2 A/P).
    @param ra Rayleigh number of A/P.
    @return Nu on A/P.
    """
    return C.fujii_imura_down(ra, 2.0)


def jaffer_square(ra):
    """!
    @brief Jaffer eq. 56 for a square (metric 2).
    @param ra Rayleigh number of A/P.
    @return Nu on A/P.
    """
    return C.jaffer_down_shape(ra, 2.0)


def jaffer_strip(ra):
    """!
    @brief Jaffer eq. 56 for a long strip (metric 1).
    @param ra Rayleigh number of A/P.
    @return Nu on A/P.
    """
    return C.jaffer_down_shape(ra, 1.0)


DOWN = {
    "program 0.27 Ra^1/4": program_down,
    "Incropera 0.52 Ra^1/5 (M)": incropera7,
    "Goldstein-Lau mean 0.475": gl_mean,
    "Goldstein-Lau strip 0.524": gl_strip,
    "VDI 0.6 (Ra f1)^1/5 (S)": vdi,
    "Rohsenow 2.5/ln (S)": rohsenow,
    "Fujii-Imura strip": fujii_strip,
    "Jaffer 56 square": jaffer_square,
    "Jaffer 56 strip": jaffer_strip,
}


@contextlib.contextmanager
def use_down(down_fn):
    """!
    @brief Run the program with another lower-face law on a copy in memory; the program's function is restored on exit.
    @param down_fn Nu(Ra) of the horizontal face turned down (hot) or the face up of a cold board.
    @return Context manager yielding a dict whose "n" counts the calls of the patched function.
    """
    original = convection.h_natural_horizontal
    calls = {"n": 0}

    def patched(t_surface, t_ambient, length, facing_up):
        # Same body as the program's function, except the branch of the face turned down
        calls["n"] += 1
        dt = t_surface - t_ambient
        props = convection.air_properties(0.5 * (t_surface + t_ambient))
        ra = convection.rayleigh(max(abs(dt), 1e-3), length, props)
        up = facing_up if dt >= 0 else not facing_up
        nu = (0.54 * ra ** 0.25 if ra <= 1e7 else 0.15 * ra ** (1.0 / 3.0)) if up else float(down_fn(ra))
        return nu * props["k"] / length, ra

    convection.h_natural_horizontal = patched
    try:
        yield calls
    finally:
        convection.h_natural_horizontal = original
