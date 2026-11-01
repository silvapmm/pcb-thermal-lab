#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_plate_asymptotes_sources.py
@brief The general interpolation function of Yovanovich (1993, AIAA-93-2750, equations 24 to 26) against the program's laminar natural-convection and forced-convection plate laws.
@details The paper (7 pages of a scan, all read as images) blends the small and the large Prandtl asymptotes of a laminar boundary layer on an isothermal plate with the Churchill-Usagi rule:
         theta* = (3/2) Pr^n [1 + (2 / (3 C0 Pr^n))^m]^(1/m), with C0 = sqrt(2/pi), m = 9/4, n = 1/4 for natural convection (equation 25, Nu = Ra^(1/4) Pr^(1/4) / theta*) and C0 = 2/sqrt(pi),
         m = 4, n = 1/6 for forced convection (equation 26, Nu = Re^(1/2) Pr^(1/2) / theta*). The script evaluates both over the Prandtl number and compares them with the laminar form of Churchill and Chu
         (equation 8.2 of the program, whose Ra^(1/4) coefficient is 0.670 / [1 + (0.492/Pr)^(9/16)]^(4/9)) and with the Pohlhausen mean value 0.664 Pr^(1/3) Re^(1/2) that `convection.h_forced` uses.
         The program's functions are called for one board-sized case to show the same numbers through the code. Run: .venv/bin/python research/theory-sources/scripts/study_plate_asymptotes_sources.py
         (from the repository root; under a second).
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from pcbthermal import convection as cv                        # noqa: E402


def coeff_natural_y93(pr):
    """!
    @brief Coefficient c in Nu = c Ra^(1/4) from equation 25 of Yovanovich (1993).
    @param pr Prandtl number.
    @return float c.
    """
    c0, m, n = np.sqrt(2.0 / np.pi), 9.0 / 4.0, 0.25
    theta = 1.5 * pr ** n * (1.0 + (2.0 / (3.0 * c0 * pr ** n)) ** m) ** (1.0 / m)
    return pr ** 0.25 / theta


def coeff_natural_churchill(pr):
    """!
    @brief Coefficient of Ra^(1/4) in the laminar form of Churchill and Chu (without the additive 0.68).
    @param pr Prandtl number.
    @return float c.
    """
    return 0.670 / (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (4.0 / 9.0)


def coeff_forced_y93(pr):
    """!
    @brief Coefficient c in Nu = c Re^(1/2) from equation 26 of Yovanovich (1993).
    @param pr Prandtl number.
    @return float c.
    """
    c0, m, n = 2.0 / np.sqrt(np.pi), 4.0, 1.0 / 6.0
    theta = 1.5 * pr ** n * (1.0 + (2.0 / (3.0 * c0 * pr ** n)) ** m) ** (1.0 / m)
    return pr ** 0.5 / theta


def main():
    """!
    @brief Print the comparisons.
    @return None.
    """
    print("Natural convection, isothermal vertical plate: coefficient of Ra^(1/4)")
    print("   Pr      Yovanovich eq.25   Churchill-Chu laminar (no 0.68)   difference")
    for pr in (0.01, 0.1, 0.5, 0.71, 1.0, 7.0, 100.0):
        a, b = coeff_natural_y93(pr), coeff_natural_churchill(pr)
        print(f"  {pr:6.2f}    {a:.4f}             {b:.4f}                         {100 * (a / b - 1):+.2f} %")
    print("Forced convection, isothermal plate, mean: coefficient of Re^(1/2)")
    print("   Pr      Yovanovich eq.26   Pohlhausen 0.664 Pr^(1/3)   difference")
    for pr in (0.1, 0.71, 1.0, 7.0, 100.0):
        a, b = coeff_forced_y93(pr), 0.664 * pr ** (1.0 / 3.0)
        print(f"  {pr:6.2f}    {a:.4f}             {b:.4f}                   {100 * (a / b - 1):+.2f} %")
    # the program's laminar form through its own function, vertical plate 0.1 m, 20 K above 25 C air
    h, ra = cv.h_natural_vertical(45.0, 25.0, 0.1, form="laminar")
    props = cv.air_properties(35.0)
    nu_prog = h * 0.1 / props["k"]
    nu_y = coeff_natural_y93(props["pr"]) * ra ** 0.25
    print(f"Program, vertical 0.1 m, 20 K: Ra {ra:.3e}, Pr {props['pr']:.4f}, Nu laminar form {nu_prog:.3f}, Yovanovich eq.25 {nu_y:.3f} ({100 * (nu_y / nu_prog - 1):+.2f} %; the program form carries +0.68)")
    hf = cv.h_forced(45.0, 25.0, 1.0, 0.1)
    re = 1.0 * 0.1 / props["nu"]
    nu_f_prog = hf * 0.1 / props["k"]
    nu_f_y = coeff_forced_y93(props["pr"]) * re ** 0.5
    print(f"Program, 1 m/s over 0.1 m: Re {re:.0f}, Nu {nu_f_prog:.3f}, Yovanovich eq.26 {nu_f_y:.3f} ({100 * (nu_f_y / nu_f_prog - 1):+.2f} %)")


def rodero_literal():
    """!
    @brief Equation 21 of Rodero and others (2025) taken literally, against the program and the usual SI form.
    @details The paper prints h_c = 0.52 C [(Ts - Tamb) / L]^0.25 with C = 0.56 (vertical), 0.52 (horizontal up), 0.26 (horizontal down) (Table II). Read literally the coefficient is 0.29, 0.27 and 0.14
             W/(m^1.75 K^1.25); the SI form of Nu = C' Ra^(1/4) with air near 300 K is h = 2.6 C' (dT / L)^(1/4) (1.4 for C' = 0.56), so the printed prefactor 0.52 does not belong with C of Table II.
    @return None.
    """
    dt, length = 20.0, 0.1
    h_prog, _ = cv.h_natural_vertical(25.0 + dt, 25.0, length, form="general")
    literal = 0.52 * 0.56 * (dt / length) ** 0.25
    usual = 1.42 * (dt / length) ** 0.25
    print(f"Rodero eq. 21, vertical plate 0.1 m at 20 K: literal 0.52 x 0.56 {literal:.2f} W/m2K, usual textbook 1.42 (dT/L)^0.25 {usual:.2f}, program (general form) {h_prog:.2f}")
    h_up, _ = cv.h_natural_horizontal(45.0, 25.0, length, True)
    h_dn, _ = cv.h_natural_horizontal(45.0, 25.0, length, False)
    print(f"   horizontal up / down: program {h_up:.2f} / {h_dn:.2f} W/m2K (ratio {h_up / h_dn:.2f}; Table II of the paper 0.52 / 0.26 = 2)")


if __name__ == "__main__":
    main()
    rodero_literal()
