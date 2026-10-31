#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fish_case.py
@brief Reproduction of the published via unit cell of Fish (2017, chapter 6): effective vertical conductivity and microspreading resistance of a 60 um copper via at 100 um pitch in glass.
@details Published numbers read from the dissertation (University of Maryland, pp. 95 to 99): copper via diameter 60 um, pitch 100 um (square, aligned), glass k = 1 W/mK, copper
         k = 400 W/mK, fill 28.3 %; isothermal limit k_eff,z = 114.5 W/mK for every thickness (the rule of mixtures, eq. 43); the thick-substrate microspreading resistance with a uniform
         flux on the top face R_msp,max = 1240 K/W; the correlation R_msp = R_msp,max / (1 + (h P / (k_s H0))^beta), H0 = 15.5, beta = 0.96 (eq. 49, fitted to finite elements).
         The independent axisymmetric solver `lib/axisym_cell.py` (equal-area disc of the square cell, cell-centred finite volumes) gives the same quantities. The cell is the same family of
         problem as a via under a plane of finite sheet conductance: the top condition decides how much lateral spreading the substrate must do to reach the via.
Usage: python research/lumped-via-groups/scripts/study_fish_case.py   (from the repository root; about a minute)
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import axisym_cell as ax                                                     # noqa: E402

P = 100e-6
A = P * P
A_VIA = 30e-6
K_V, K_S = 400.0, 1.0


def r_1d(length):
    """!
    @brief One-dimensional resistance of the cell by the rule of mixtures (eq. 48 of Fish).
    @param length Thickness in m.
    @return float K/W.
    """
    phi = math.pi * A_VIA ** 2 / A
    return length / (A * (phi * K_V + (1.0 - phi) * K_S))


def main():
    """!
    @brief Print the comparison tables.
    @return None.
    """
    phi = math.pi * A_VIA ** 2 / A
    print(f"fill {100 * phi:.1f} %, rule of mixtures k_eff = {phi * K_V + (1 - phi) * K_S:.2f} W/mK (Fish: 114.5)\n")
    print("## Isothermal top and bottom: effective conductivity of the cell\n")
    print("| thickness um | R_total K/W | k_eff,z W/mK |\n| --: | --: | --: |")
    for length in (25e-6, 100e-6, 250e-6, 500e-6):
        r = ax.unit_cell_resistance(A_VIA, P, length, K_V, K_S, h_top=1e13)
        print(f"| {length * 1e6:.0f} | {r:.3f} | {length / (A * r):.2f} |")
    print("\n## Microspreading resistance of the thick substrate (500 um) against the top condition\n")
    print("| h W/m2K | R_msp K/W (this solver) | Fish correlation, eq. 49 | ratio |\n| --: | --: | --: | --: |")
    length = 500e-6
    for h in (1e0, 1e2, 1e4, 1e5, 5e5, 1e6, 1e7):
        r = ax.unit_cell_resistance(A_VIA, P, length, K_V, K_S, h_top=h)
        # the 1D term of the cell includes the film 1 / (h A) of the convection condition: it is not part of the resistance between the faces
        rmsp = r - r_1d(length)
        corr = 1240.0 / (1.0 + (h * P / (K_S * 15.5)) ** 0.96)
        print(f"| {h:.0e} | {rmsp:.1f} | {corr:.1f} | {rmsp / corr:.3f} |")
    r = ax.unit_cell_resistance(A_VIA, P, length, K_V, K_S, h_top=None)
    print(f"\nUniform flux on the top face: R_msp = {r - r_1d(length):.1f} K/W (Fish: 1240 K/W for the thick substrate)")
    print("\n## Thin substrates (uniform flux): the microspreading resistance grows as the cell gets thinner (Fish figure 43)\n")
    print("| thickness um | R_total K/W | R_1D K/W | R_msp K/W |\n| --: | --: | --: | --: |")
    for length in (25e-6, 50e-6, 100e-6, 200e-6, 350e-6, 500e-6):
        r = ax.unit_cell_resistance(A_VIA, P, length, K_V, K_S, h_top=None)
        print(f"| {length * 1e6:.0f} | {r:.1f} | {r_1d(length):.1f} | {r - r_1d(length):.1f} |")


if __name__ == "__main__":
    main()
