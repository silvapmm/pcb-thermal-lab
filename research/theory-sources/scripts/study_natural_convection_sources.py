#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_natural_convection_sources.py
@brief F3: the natural and mixed convection correlations of `pcbthermal/convection.py` against the open sources that were read.
@details Questions answered: (1) does the program's Churchill and Chu vertical-plate form reproduce the worked value of Lienhard's open textbook
(Example 8.1, Nu 47.33, h 4.22 W/m2K); (2) which exponent inside the logarithm of the Hollands (1984) horizontal-layer equation is the right one
(the `ht` documentation writes Ra^(1/5) inside the logarithm, its code Ra^(1/3)): the ISO 15099 / Rohsenow (1985) form printed in an open ASHRAE preprint (equation 9, Pr near 0.71)
and the Hollands et al. (1976) air form (its equation 14) decide; (3) how far the horizontal-plate correlations of the program (McAdams) are from those of
Raithby and Hollands in Lienhard (equations 8.35, 8.37a, 8.37b) and of Fujii and Imura (8.38, on the plate width, not A/P) on board-size plates; (4) what the cube-root blend of natural and
forced convection costs against the exponents that Jaffer and Jaffer give for a level forced flow (p = 2 over an upward-facing plate, p = 5 under a downward-facing one).
Run from the repository root: .venv/bin/python research/theory-sources/scripts/study_natural_convection_sources.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(HERE, "..", "lib"))

from pcbthermal import convection as cv  # noqa: E402
from correlations import (churchill_chu_laminar, hollands_ht, hollands_iso15099, hollands_1976,  # noqa: E402
                          raithby_hollands_up, raithby_hollands_low, fujii_imura_down)


def part1():
    """!
    @brief Lienhard Example 8.1 (Pr 0.71, Ra 6.78e7, k 0.02672, L 0.30 m): Nu 47.33, h 4.22 W/m2K, and the program's form at its own Ra.
    @return Dict with the numbers (book, standalone formula, program).
    """
    ra, pr = 6.78e7, 0.710
    nu = churchill_chu_laminar(ra, pr)
    h_prog, ra_prog = cv.h_natural_vertical(60.0, 20.0, 0.30, "laminar")
    props = cv.air_properties(40.0)
    nu_prog = h_prog * 0.30 / props["k"]
    return {"nu_book": 47.33, "nu_formula": nu, "h_book": 4.22, "h_formula": nu * 0.02672 / 0.30, "nu_program": nu_prog,
            "nu_formula_same_ra": churchill_chu_laminar(ra_prog, props["pr"]), "ra_program": ra_prog}


def part2():
    """!
    @brief Hollands horizontal layer, Pr 0.71: the `ht` form with Ra^(1/3) (code) and Ra^(1/5) inside the logarithm (documentation), against ISO 15099 (equation 9) and Hollands 1976 (equation 14).
    @return List of rows (Ra, Nu 1976, Nu ISO, ht code, ht documentation, ht with 5830).
    """
    return [(ra, hollands_1976(ra), hollands_iso15099(ra), hollands_ht(0.71, ra), hollands_ht(0.71, ra, root=5.0),
             hollands_ht(0.71, ra, ra_c_third=5830.0)) for ra in (2e3, 3e3, 5e3, 1e4, 3e4, 1e5, 3e5, 1e6, 1e7)]


def part3():
    """!
    @brief Horizontal plates: the program (McAdams) against Raithby and Hollands (Lienhard 8.35, 8.37a with 8.37b) and Fujii and Imura (8.38).
    @details Fujii and Imura's correlation is written for a two-dimensional plate of width L (Lienhard, book page 437); a rectangle has no single width, so it is evaluated on two lengths
             that bracket the plausible choice: 2 A/P (the width of a strip with the same A/P) and the shorter side. The first version of this study used A/P, which is not the
             correlation's length and inflated its h by about (2)^(2/5) to (b/(A/P))^(2/5) (review, README 6).
    @return List of rows (a mm, b mm, dT, Ra on A/P, h up program, h up source, change of the total h in percent with eps 0.9, h down program,
            h down Fujii-Imura on 2 A/P, h down Fujii-Imura on the shorter side, Ra on the shorter side).
    """
    rows = []
    for a, b in ((0.04, 0.03), (0.1, 0.08), (0.16, 0.1), (0.3, 0.2)):
        length = a * b / (2 * (a + b))
        for dt in (5.0, 20.0, 60.0):
            ts, ta = 20.0 + dt, 20.0
            props = cv.air_properties(0.5 * (ts + ta))
            ra = cv.rayleigh(dt, length, props)
            hp_up, _ = cv.h_natural_horizontal(ts, ta, length, True)
            hp_dn, _ = cv.h_natural_horizontal(ts, ta, length, False)
            k = props["k"]
            hs_up = raithby_hollands_up(ra, props["pr"]) * k / length
            hr = cv.h_radiation(ts, ta, 0.9)                 # radiation of the program, added to both to see the effect on the total
            w_strip, w_short = 2.0 * length, min(a, b)
            fi_strip = fujii_imura_down(cv.rayleigh(dt, w_strip, props)) * k / w_strip
            ra_short = cv.rayleigh(dt, w_short, props)
            fi_short = fujii_imura_down(ra_short) * k / w_short
            rows.append((a * 1e3, b * 1e3, dt, ra, hp_up, hs_up, 100.0 * (hs_up - hp_up) / (hp_up + hr),
                         hp_dn, fi_strip, fi_short, ra_short))
    return rows


def part4():
    """!
    @brief Mixed convection of a hot horizontal 100 x 100 mm board (A/P = 25 mm) in a level flow: cube-root blend (program) against the exponents of Jaffer and Jaffer, Table 4
           (p = 2 for the face looking up, p = 5 for the face looking down).
    @details The first version used A/P = 28.6 mm, which is not the A/P of a 100 mm square (review, README 6).
    @return List of rows (air speed, h_n up, h_f, h up p=3, h up p=2, ratio up, h_n down, h down p=3, h down p=5, ratio down).
    """
    rows = []
    for speed in (0.2, 0.5, 1.0, 2.0):
        hn, _ = cv.h_natural_horizontal(60.0, 20.0, 0.025, True)
        hd, _ = cv.h_natural_horizontal(60.0, 20.0, 0.025, False)
        hf = cv.h_forced(60.0, 20.0, speed, 0.10)
        h3 = (hn ** 3 + hf ** 3) ** (1 / 3)
        h2 = (hn ** 2 + hf ** 2) ** 0.5
        d3 = (hd ** 3 + hf ** 3) ** (1 / 3)
        d5 = (hd ** 5 + hf ** 5) ** 0.2
        rows.append((speed, hn, hf, h3, h2, h3 / h2, hd, d3, d5, d3 / d5))
    return rows


def main():
    """!
    @brief Print every check of this study.
    @return None.
    """
    r1 = part1()
    print("1. Churchill-Chu laminar form, Lienhard Example 8.1: book Nu %.2f h %.2f | formula Nu %.2f h %.2f | program Nu %.4f vs formula at the same Ra %.4f (Ra %.3e)"
          % (r1["nu_book"], r1["h_book"], r1["nu_formula"], r1["h_formula"], r1["nu_program"], r1["nu_formula_same_ra"], r1["ra_program"]))
    print("2. Hollands horizontal layer, Pr 0.71: Ra | Nu 1976 (eq 14) | ISO 15099 (eq 9) | ht code (1/3) | ht doc (1/5 in the log) | ht with 5830")
    for row in part2():
        print("   %9.3g | %7.4f | %7.4f | %7.4f | %7.4f | %7.4f" % row)
    print("3. Horizontal plates (L = A/P): a x b mm, dT, Ra | h up program, R&H, change of total h in % | h down program, Fujii-Imura 8.38 on 2 A/P and on the shorter side (Ra)")
    for row in part3():
        print("   %4.0f x %3.0f dT %4.0f Ra %9.3g | up %6.3f %6.3f (%+5.1f %%) | down %6.3f %6.3f %6.3f (Ra %8.2g)" % row)
    print("4. Mixed convection, horizontal board 100 x 100 mm, 60 degC in 20 degC air: v | up: h_n h_f h(p=3) h(p=2) ratio | down: h_n h(p=3) h(p=5) ratio")
    for row in part4():
        print("   %4.1f | %6.3f %6.3f %6.3f %6.3f %.3f | %6.3f %6.3f %6.3f %.3f" % row)


if __name__ == "__main__":
    main()
