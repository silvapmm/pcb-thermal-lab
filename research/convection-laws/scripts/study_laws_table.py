#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_laws_table.py
@brief Tabulate the candidate natural-convection laws (face up, face down, vertical) over Ra = 1e2 .. 1e8 and for the sizes of the boards, as ratios to the program's law.
@details Part 1: Nu(Ra) of each law at Pr 0.71 and the ratio to the program (up and down); L = A/P for the horizontal faces, the height for the vertical ones.
         Part 2: the Rayleigh number of the faces of boards of the usual sizes (square 40 to 200 mm, 100 x 80 mm, 160 x 100 mm) at excesses of 5 to 80 K over a 25 degC ambient
         (program air properties at the film temperature), with the coefficient h in W/m2K of the program and of the Raithby-Hollands / Goldstein-Lau pair, and which range of every law that Ra
         falls in. Part 3: the ratio of the vertical Churchill-Chu forms to the program's choice at the same Ra. Output: out/laws_table.json. No program run, no solver.
Usage: .venv/bin/python research/convection-laws/scripts/study_laws_table.py
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import laws  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
RAS = [1e2, 3e2, 1e3, 3e3, 1e4, 3e4, 1e5, 3e5, 1e6, 1e7, 1e8]
# published validity ranges of the up and down laws (A/P based) as printed by the sources
RANGES = {"RH up": (1.0, 1e7), "Lloyd-Moran up": (2.2e4, 8e6), "Fujii-Imura down (water, 2D)": (1e6, 1e11)}


def part1():
    """!
    @brief Nu of every law at the Ra list and the ratio to the program.
    @return dict of arrays.
    """
    ra = np.array(RAS)
    out = {"ra": ra.tolist()}
    names_up = {"program": laws.C.program_up, "RH": laws.C.raithby_hollands_up, "Jaffer": laws.C.jaffer_up}
    names_dn = {"program": laws.C.program_down, "GL 0.475 Ra^1/5": laws.goldstein_lau_down, "FI strip (w=2)": lambda r: laws.C.fujii_imura_down(r, 2.0),
                "FI square (w=4)": lambda r: laws.C.fujii_imura_down(r, 4.0), "KD disc": laws.C.kadambi_drake_down, "Jaffer square": lambda r: laws.C.jaffer_down_shape(r, 2.0),
                "Jaffer strip": lambda r: laws.C.jaffer_down_shape(r, 1.0)}
    print("FACE UP, Nu (L = A/P), ratio to the program in brackets")
    print("Ra       " + "  ".join(f"{k:>16s}" for k in names_up))
    for i, r in enumerate(ra):
        print(f"{r:7.0e}  " + "  ".join(f"{float(f(r)):8.3f} ({float(f(r)) / float(names_up['program'](r)):5.2f})" for f in names_up.values()))
    for k, f in names_up.items():
        out["up|" + k] = [float(f(r)) for r in ra]
    print("\nFACE DOWN, Nu (L = A/P), ratio to the program in brackets")
    print("Ra       " + "  ".join(f"{k:>15s}" for k in names_dn))
    for i, r in enumerate(ra):
        print(f"{r:7.0e}  " + "  ".join(f"{float(f(r)):7.3f} ({float(f(r)) / float(names_dn['program'](r)):4.2f})" for f in names_dn.values()))
    for k, f in names_dn.items():
        out["down|" + k] = [float(f(r)) for r in ra]
    return out


def part2():
    """!
    @brief Ra of the faces of boards and the h of the program and of the RH + GL pair.
    @return list of rows.
    """
    from pcbthermal import convection
    rows = []
    print("\nBOARDS: Ra of A/P and h (convection only, W/m2K) of the program and of Raithby-Hollands up + Goldstein-Lau down; 25 degC ambient")
    print("board          dT   A/P mm    Ra     h_up prog  h_up RH   h_dn prog  h_dn GL   ratio_up  ratio_dn")
    for (w, h) in ((40, 40), (60, 60), (100, 80), (100, 100), (160, 100), (200, 200)):
        L = laws.a_over_p(w, h)
        for dt in (5, 10, 20, 40, 80):
            props = convection.air_properties(25 + dt / 2)
            ra = convection.rayleigh(dt, L, props)
            k = props["k"]
            hu_p, hu_r = float(laws.C.program_up(ra)) * k / L, float(laws.C.raithby_hollands_up(ra, props["pr"])) * k / L
            hd_p, hd_g = float(laws.C.program_down(ra)) * k / L, float(laws.goldstein_lau_down(ra)) * k / L
            rows.append({"w": w, "h": h, "dt": dt, "L_mm": L * 1e3, "ra": ra, "h_up_program": hu_p, "h_up_rh": hu_r, "h_down_program": hd_p, "h_down_gl": hd_g})
            print(f"{w:3d}x{h:<3d} mm  {dt:4d}  {L * 1e3:6.2f}  {ra:8.2e}  {hu_p:7.2f}  {hu_r:7.2f}   {hd_p:7.2f}  {hd_g:7.2f}    {hu_r / hu_p:5.2f}    {hd_g / hd_p:5.2f}")
    return rows


def part3():
    """!
    @brief The two Churchill-Chu forms against each other and the program's horizontal laws at the same Ra (a vertical board of the height given).
    @return list of rows.
    """
    rows = []
    print("\nVERTICAL: Churchill-Chu general / laminar (Nu of the height), Ra 1e2 .. 1e8")
    for r in RAS:
        g, l = float(laws.churchill_chu_general(r)), float(laws.churchill_chu_laminar(r))
        rows.append({"ra": r, "general": g, "laminar": l, "ratio": l / g})
        print(f"{r:7.0e}  general {g:7.3f}  laminar {l:7.3f}  laminar/general {l / g:5.3f}")
    return rows


def main():
    """!
    @brief Print the three parts and save them.
    @return None.
    """
    res = {"laws": part1(), "boards": part2(), "vertical": part3()}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "laws_table.json"), "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main()
