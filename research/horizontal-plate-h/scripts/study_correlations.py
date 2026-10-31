#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_correlations.py
@brief The correlations of the horizontal plate against each other and the Rayleigh numbers of the boards: where the program's 0.54 / 0.15 (up) and 0.27 (down) lie against Jaffer's fits and Schulenberg's theory over Ra = 1e1 ... 1e8 of L = A/P.

@details No solver, no program run except `pcbthermal.convection` for the properties of air and the program's own `h_natural_horizontal` (checked against the formula of `lib/correlations.py`).
         Parts: (1) the Rayleigh numbers of L = A/P for squares of 40 to 200 mm and strips at 10, 30 and 60 K above 20 degC; (2) the levels in Nu and their ratio to the program;
         (3) the large-Prandtl and small-Prandtl limits of Schulenberg's strip formula as printed (0.544 and 0.571) against Jaffer's "corrected" coefficients; (4) the coefficient h in W/m2K
         of a 100 mm square at 30 K (convection only) with each level. Results go to out/correlations.json for make_figures.py.

Usage: .venv/bin/python research/horizontal-plate-h/scripts/study_correlations.py   (a few seconds)
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import correlations as C                                  # noqa: E402
from pcbthermal import convection                         # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")


def ra_of(side_mm, dt, kind="square"):
    """!
    @brief Rayleigh number of L = A/P of a face at dt above 20 degC (air at the film temperature).
    @param side_mm Side of the square, or width of the strip, in mm.
    @param dt Excess temperature in K.
    @param kind "square" (L = s/4) or "strip" (L = w/2).
    @return float.
    """
    length = side_mm / 1000.0 / (4.0 if kind == "square" else 2.0)
    props = convection.air_properties(20.0 + dt / 2.0)
    return float(convection.rayleigh(dt, length, props))


def main():
    """!
    @brief Print the tables and write out/correlations.json.
    @return None.
    """
    out = {}
    print("1. Rayleigh number of L = A/P (air at the film temperature, ambient 20 degC)")
    print("| face | 10 K | 30 K | 60 K |")
    print("| :-- | --: | --: | --: |")
    rows = []
    for kind, sizes in (("square", (40, 60, 100, 150, 200)), ("strip", (40, 100))):
        for s in sizes:
            r = [ra_of(s, dt, kind) for dt in (10, 30, 60)]
            rows.append({"kind": kind, "size_mm": s, "ra": r})
            print(f"| {kind} {s} mm | {r[0]:.2e} | {r[1]:.2e} | {r[2]:.2e} |")
    out["ra_boards"] = rows
    ras = np.array([1e1, 3e1, 1e2, 3e2, 1e3, 3e3, 1e4, 3e4, 1e5, 3e5, 1e6, 3e6, 1e7, 3e7, 1e8])
    levels = {"program up": C.program_up(ras), "Jaffer up (30)": C.jaffer_up(ras), "program down": C.program_down(ras), "Jaffer down (46,51)": C.jaffer_down(ras),
              "Jaffer down, square (q = 2)": C.jaffer_down_shape(ras, 2.0), "Jaffer down, disc (q = 4/pi)": C.jaffer_down_shape(ras, 4.0 / np.pi),
              "Schulenberg strip (92)": C.schulenberg_strip(ras), "Schulenberg strip, Jaffer coef.": C.schulenberg_strip(ras, jaffer_coefficients=True), "Schulenberg disc (94), L = R/2": C.schulenberg_disc(ras)}
    print("\n2. Nu of every level (L = A/P) and the ratio to the program")
    print("| Ra | program up | Jaffer up | Jaffer / program | program down | Jaffer down, strip | strip / program | Jaffer down, square | square / program | Jaffer down, disc | disc / program | Schulenberg strip | / program | Schulenberg disc | / program |")
    print("| --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    for i, ra in enumerate(ras):
        pu, ju = levels["program up"][i], levels["Jaffer up (30)"][i]
        pd, jd = levels["program down"][i], levels["Jaffer down (46,51)"][i]
        jq, jc = levels["Jaffer down, square (q = 2)"][i], levels["Jaffer down, disc (q = 4/pi)"][i]
        ss, sd = levels["Schulenberg strip (92)"][i], levels["Schulenberg disc (94), L = R/2"][i]
        print(f"| {ra:.0e} | {pu:.2f} | {ju:.2f} | {ju / pu:.2f} | {pd:.2f} | {jd:.2f} | {jd / pd:.2f} | {jq:.2f} | {jq / pd:.2f} | {jc:.2f} | {jc / pd:.2f} | {ss:.2f} | {ss / pd:.2f} | {sd:.2f} | {sd / pd:.2f} |")
    out["ra"] = ras.tolist()
    out["levels"] = {k: v.tolist() for k, v in levels.items()}
    print("\n3. Schulenberg's strip formula: limits (the two sets of coefficients)")
    for label, jf in (("as printed (0.571, 1.156)", False), ("Jaffer (0.631, 1.56)", True)):
        a, b = (0.631, 1.56) if jf else (0.571, 1.156)
        print(f"   {label}: Pr -> infinity {a / b ** (1 / 3):.4f} (paper: 0.544), Pr -> 0: {a:.3f} Pr^(1/5) Ra^(1/5); at Pr 0.71: {C.schulenberg_strip(1.0, jaffer_coefficients=jf):.4f} Ra^(1/5)")
    print(f"   Schulenberg disc at Pr 0.71, L = R: {C.schulenberg_disc(1.0 / 8.0) * 2.0:.4f} Ra_R^(1/5) (Pr -> infinity: 0.619)")
    print(f"   Jaffer 46 constants: Nu0'/4 = 0.341, 0.550; Xi_R(0.71) = {C.xi_r():.3f}; the downward formula is {C.jaffer_down(0.0):.3f} + {0.550 / C.xi_r() ** 0.2:.4f} Ra^(1/5)")
    print("\n4. The program's function against the formula of lib/correlations.py (100 mm square, 30 K, 20 degC ambient)")
    length = 0.1 / 4
    for up in (True, False):
        h, ra = convection.h_natural_horizontal(50.0, 20.0, length, up)
        nu_prog = (C.program_up if up else C.program_down)(ra)
        props = convection.air_properties(35.0)
        print(f"   {'up' if up else 'down':4s}: program h {h:.4f}, from the formula {float(nu_prog) * props['k'] / length:.4f} W/m2K (Ra {ra:.3e})")
    hs = {}
    for name, (fu, fd) in {"program": (C.program_up, C.program_down), "Jaffer (down with q = 2)": (C.jaffer_up, lambda r: C.jaffer_down_shape(r, 2.0))}.items():
        _, ra = convection.h_natural_horizontal(50.0, 20.0, length, True)
        k = convection.air_properties(35.0)["k"]
        hs[name] = (float(fu(ra)) * k / length, float(fd(ra)) * k / length)
        print(f"   {name:8s}: up {hs[name][0]:.2f}, down {hs[name][1]:.2f} W/m2K (convection only; Ra {ra:.3e})")
    out["h_100mm_30K"] = hs
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "correlations.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
