#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_similarity.py
@brief The exact laminar boundary-layer coefficient of an isothermal vertical plate (Ostrach's table reproduced), the coefficients of the correlations against it, and the levels against Rayleigh number.

@details Questions answered:

         1. Does the independent similarity solver (`lib/similarity.py`, own RK4 shooting and scipy collocation) reproduce the values of Ostrach (NACA Report 1111, Table I, pages 77 and 78)?
            -H'(0) = 0.0812 / 0.5046 / 0.5080 / 0.5671 / 0.7165 / 1.1694 / 2.191 at Pr = 0.01 / 0.72 / 0.733 / 1 / 2 / 10 / 100 (read from the page images).
         2. What is the exact coefficient C(Pr) of the plate-average Nu = C Ra^(1/4), and how far are Churchill and Chu's 0.670/[...]^(4/9), LeFevre's 0.503 (average 4/3 of it),
            Squire's 0.508 and the 0.59 of the composite from it, at Pr 0.71?
         3. How do the levels compare over 1e2 < Ra < 1e12 (ratios to the program's general form)?

         Run: .venv/bin/python research/plate-h-level/scripts/study_similarity.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import levels as L                                        # noqa: E402
import similarity as sim                                  # noqa: E402

# Table I of Ostrach (NACA Report 1111, pages 77 and 78): Prandtl number -> (F''(0), -H'(0)), read from the page images
OSTRACH = {0.01: (0.9862, 0.0812), 0.72: (0.6760, 0.5046), 0.733: (0.6741, 0.5080), 1.0: (0.6421, 0.5671), 2.0: (0.5713, 0.7165), 10.0: (0.4192, 1.1694), 100.0: (0.2517, 2.191)}


def main():
    """!
    @brief Print the tables.
    @return None.
    """
    print("1. Similarity solution against Ostrach's Table I")
    print("| Pr | F''(0) own (collocation) | F''(0) Ostrach | -H'(0) own collocation | -H'(0) own shooting | -H'(0) Ostrach | difference (%) |")
    print("| --: | --: | --: | --: | --: | --: | --: |")
    for pr, (fpp_o, thp_o) in OSTRACH.items():
        fpp, thp = sim.bvp(pr, 100.0 if pr < 0.05 else 50.0)
        try:
            thp_s = -sim.shoot(pr)[1] if 0.5 <= pr <= 2 else float("nan")
        except Exception:
            thp_s = float("nan")
        print(f"| {pr:g} | {fpp:.4f} | {fpp_o:.4f} | {-thp:.4f} | {thp_s:.4f} | {thp_o:.4f} | {100 * (-thp / thp_o - 1):+.2f} |")

    print("\n2. The plate-average coefficient C(Pr) of Nu = C Ra^(1/4)")
    print("| Pr | exact (collocation) | Churchill-Chu 0.670/[..]^(4/9) | LeFevre 0.503 x 4/3 /[..]^(4/9) | Squire (4/3) 0.508 [Pr/(0.952+Pr)]^(1/4) | exact local c_x |")
    print("| --: | --: | --: | --: | --: | --: |")
    for pr in (0.1, 0.5, 0.7, 0.71, 0.72, 1.0, 10.0, 100.0):
        c = sim.coefficient(pr, "bvp")
        cs = (4.0 / 3.0) * 0.508 * (pr / (0.952 + pr)) ** 0.25
        print(f"| {pr:g} | {c:.4f} | {sim.churchill_usagi(pr):.4f} ({100 * (sim.churchill_usagi(pr) / c - 1):+.2f} %) | {sim.lefevre_local(pr) * 4 / 3:.4f} ({100 * (sim.lefevre_local(pr) * 4 / 3 / c - 1):+.2f} %) | {cs:.4f} ({100 * (cs / c - 1):+.1f} %) | {3 / 4 * c:.4f} |")
    c = sim.coefficient(0.71, "bvp")
    print(f"\nPr 0.71: exact {c:.4f}; 0.59 is {100 * (0.59 / c - 1):+.1f} % above it; Churchill-Chu laminar term {100 * (sim.churchill_usagi(0.71) / c - 1):+.2f} %; "
          f"the plate limit of the Churchill (1977) channel formula 0.75/[..]^(4/9) = {0.75 / (1 + (0.492 / 0.71) ** (9 / 16)) ** (4 / 9):.4f} ({100 * (0.75 / (1 + (0.492 / 0.71) ** (9 / 16)) ** (4 / 9) / c - 1):+.1f} %), Raithby-Hollands 0.62 ({100 * (0.62 / c - 1):+.1f} %)")

    print("\n3. Average Nusselt number of the levels at Pr 0.71, and the ratio to the program's general form")
    ras = [1e2, 1e3, 1e4, 3e4, 1e5, 3e5, 1e6, 3e6, 1e7, 3e7, 1e8, 1e9, 1e10, 1e12]
    lv = ("general", "laminar", "bl", "bl_le", "mcadams", "squire")
    print("| Ra | " + " | ".join(L.LABELS[k] for k in lv) + " |")
    print("| --: | " + " | ".join("--:" for _ in lv) + " |")
    for ra in ras:
        g = L.nu_level("general", ra, 0.71)
        print(f"| {ra:.0e} | " + " | ".join(f"{L.nu_level(k, ra, 0.71):.3f} ({100 * (L.nu_level(k, ra, 0.71) / g - 1):+.1f} %)" for k in lv) + " |")

    print("\n   Ra at which the laminar form and the general form agree, and the ratio 0.59 / laminar form, laminar form / exact BL:")
    grid = np.logspace(1, 10, 2000)
    d = L.nu_level("laminar", grid, 0.71) - L.nu_level("general", grid, 0.71)
    cross = grid[np.where(np.diff(np.sign(d)))[0]]
    print("   laminar = general at Ra =", ", ".join(f"{x:.3g}" for x in cross))
    for ra in (1e4, 1e5, 1e6, 1e7, 1e8):
        print(f"   Ra {ra:.0e}: 0.59/laminar = {L.nu_level('mcadams', ra, 0.71) / L.nu_level('laminar', ra, 0.71):.3f}; laminar/exact BL = {L.nu_level('laminar', ra, 0.71) / L.nu_level('bl', ra, 0.71):.3f}; "
              f"general/exact BL = {L.nu_level('general', ra, 0.71) / L.nu_level('bl', ra, 0.71):.3f}")

    print("\n4. PCB conditions: Rayleigh number of a vertical face (air at the film temperature)")
    from pcbthermal import convection
    for h in (0.04, 0.1, 0.2):
        row = []
        for dt in (10, 30, 60):
            props = convection.air_properties(20.0 + dt / 2)
            row.append(convection.rayleigh(dt, h, props))
        print(f"   height {h * 1000:.0f} mm, 10 / 30 / 60 K above 20 degC: Ra = " + " / ".join(f"{x:.2e}" for x in row))


if __name__ == "__main__":
    main()
