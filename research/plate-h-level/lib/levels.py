#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file levels.py
@brief The natural-convection "levels" of a vertical isothermal plate (average Nusselt number against Rayleigh and Prandtl) and a context that runs the program with one of them, on a copy in memory.
@details Levels (Nu is the plate-average Nusselt number, Ra the Rayleigh number of the plate height):

         * "general": Churchill and Chu (1975) all-Ra form, the program's default;
         * "laminar": Churchill and Chu laminar form 0.68 + 0.670 Ra^(1/4)/[1 + (0.492/Pr)^(9/16)]^(4/9), the program's `Board.natural_form = "laminar"`;
         * "bl": the exact laminar boundary-layer (similarity) solution, Nu = C(Pr) Ra^(1/4) with C(Pr) from `similarity.coefficient` (0.5157 at Pr 0.71): no leading-edge term, so it fails at low Ra;
         * "bl_le": the exact boundary-layer term plus the 0.68 of Churchill and Chu (the laminar form with the exact coefficient instead of its fit);
         * "mcadams": Nu = 0.59 Ra^(1/4), the plate limit of the Bar-Cohen and Rohsenow composite (and the empirical correlation quoted by textbooks for 1e4 < Ra < 1e9);
         * "squire": the integral-method coefficient of Squire, (4/3) 0.508 [Pr/(0.952 + Pr)]^(1/4) Ra^(1/4) (a historical approximation, 6 % above the exact one at Pr 0.71).

         `use_level` replaces `pcbthermal.convection.h_natural_vertical` for the duration of a run; the program is not edited.
"""

import contextlib
import os
import sys
from functools import lru_cache

import numpy as np
from scipy.interpolate import CubicSpline

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import similarity as sim                                       # noqa: E402
from pcbthermal import convection                              # noqa: E402

LEVELS = ("general", "laminar", "bl", "bl_le", "mcadams", "squire")
LABELS = {"general": "Churchill-Chu general", "laminar": "Churchill-Chu laminar", "bl": "exact boundary layer", "bl_le": "exact BL + 0.68",
          "mcadams": "0.59 Ra^(1/4)", "squire": "Squire integral"}


@lru_cache(maxsize=1)
def _c_spline():
    """!
    @brief Spline of the exact coefficient C(Pr) over the Prandtl numbers of air (0.6 to 0.8).
    @return scipy CubicSpline.
    """
    prs = np.linspace(0.6, 0.8, 9)
    return CubicSpline(prs, [sim.coefficient(p, "bvp") for p in prs])


def c_exact(pr):
    """!
    @brief The exact coefficient C(Pr) of Nu = C Ra^(1/4) for Pr in 0.6 to 0.8.
    @param pr Prandtl number.
    @return float.
    """
    return float(_c_spline()(pr))


def nu_level(level, ra, pr):
    """!
    @brief Average Nusselt number of a vertical isothermal plate for a level.
    @param level One of LEVELS.
    @param ra Rayleigh number (plate height).
    @param pr Prandtl number.
    @return float or array Nu.
    @throws ValueError For an unknown level.
    """
    ra = np.asarray(ra, float)
    den = (1.0 + (0.492 / pr) ** (9.0 / 16.0))
    if level == "general":
        return (0.825 + 0.387 * ra ** (1.0 / 6.0) / den ** (8.0 / 27.0)) ** 2
    if level == "laminar":
        return 0.68 + 0.670 * ra ** 0.25 / den ** (4.0 / 9.0)
    if level == "bl":
        return c_exact(pr) * ra ** 0.25
    if level == "bl_le":
        return 0.68 + c_exact(pr) * ra ** 0.25
    if level == "mcadams":
        return 0.59 * ra ** 0.25
    if level == "squire":
        return (4.0 / 3.0) * 0.508 * (pr / (0.952 + pr)) ** 0.25 * ra ** 0.25
    raise ValueError(f"unknown level '{level}'")


def h_vertical(level, t_surface, t_ambient, height):
    """!
    @brief Convection coefficient of a vertical plate for a level, with the air properties of the program.
    @param level One of LEVELS.
    @param t_surface Mean surface temperature in degC.
    @param t_ambient Air temperature in degC.
    @param height Plate height in m.
    @return tuple (h in W/m2K, Rayleigh number).
    """
    props = convection.air_properties(0.5 * (t_surface + t_ambient))
    ra = convection.rayleigh(max(abs(t_surface - t_ambient), 1e-3), height, props)
    return float(nu_level(level, ra, props["pr"])) * props["k"] / height, ra


@contextlib.contextmanager
def use_level(level):
    """!
    @brief Run the program with the natural convection of a vertical face given by a level (the function `convection.h_natural_vertical` is replaced for the duration).
    @param level One of LEVELS.
    @return Context manager.
    """
    original = convection.h_natural_vertical

    def patched(t_surface, t_ambient, height, form="general"):
        """!
        @brief Replacement of `convection.h_natural_vertical`.
        @param t_surface Mean surface temperature in degC.
        @param t_ambient Air temperature in degC.
        @param height Plate height in m.
        @param form Ignored (the level decides).
        @return tuple (h, Ra).
        """
        return h_vertical(level, t_surface, t_ambient, height)

    convection.h_natural_vertical = patched
    try:
        yield
    finally:
        convection.h_natural_vertical = original
