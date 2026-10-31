#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file print_tables.py
@brief Print the markdown tables of the README (the numerical plates and the effect on the boards) from the JSON files of out/, so that the README quotes what the scripts wrote.
@details Reads out/plate_h2d.json (study_plate_h2d.py) and out/board_effect.json (study_board_effect.py) and prints: (A) the numerical Nusselt numbers of both faces for every case with the ratios to the
         levels; (B) the isolated-face and both-faces values and their ratio; (C) the rise of every board with the program's levels and the change with each other level.

Usage: .venv/bin/python research/horizontal-plate-h/scripts/print_tables.py   (instant)
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import correlations as C                                  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")


def load(name):
    """!
    @brief Read a JSON file of out/.
    @param name File name.
    @return Parsed JSON, or an empty list when missing.
    """
    p = os.path.join(OUT, name)
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return json.load(f)


def main():
    """!
    @brief Print the tables.
    @return None.
    """
    res = load("plate_h2d.json")
    print("A. numerical plates: Nu of L = A/P (steps, convergence flag, energy balance) and the ratio to the levels")
    print("| geometry | Ra | faces | grid | Nu up | Nu down | balance | converged | up / program | up / Jaffer | down / program | down / Jaffer (strip or disc) | down / Schulenberg |")
    print("| :-- | --: | :-- | :-- | --: | --: | --: | :-- | --: | --: | --: | --: | --: |")
    for r in sorted(res, key=lambda q: (q["geometry"], q["ra_l"], q["faces"], q["grid"])):
        ra = r["ra_l"]
        q = 1.0 if r["geometry"] == "strip" else 4 / np.pi
        sch = float(C.schulenberg_strip(ra)) if r["geometry"] == "strip" else float(C.schulenberg_disc(ra))
        up = r["nu_up"] if r["faces"] != "down" else None
        dn = r["nu_down"] if r["faces"] != "up" else None
        f = lambda v, ref: "" if v is None else f"{v / float(ref):.2f}"
        print(f"| {r['geometry']} | {ra:.0e} | {r['faces']} | {r['grid']} | {r['nu_up']:.3f} | {r['nu_down']:.3f} | {r['balance']:.3f} | {r['converged']} | {f(up, C.program_up(ra))} | {f(up, C.jaffer_up(ra))} | "
              f"{f(dn, C.program_down(ra))} | {f(dn, C.jaffer_down_shape(ra, q))} | {f(dn, sch)} |")
    print("\nB. the other face: Nu(both faces hot) / Nu(face alone)")
    print("| geometry | Ra | upper face: both / alone | lower face: both / alone |")
    print("| :-- | --: | --: | --: |")
    for geom in ("strip", "disc"):
        for ra in sorted({r["ra_l"] for r in res if r["geometry"] == geom}):
            get = lambda faces: [r for r in res if r["geometry"] == geom and r["ra_l"] == ra and r["faces"] == faces and r["grid"] == "base"]
            b, u, d = get("both"), get("up"), get("down")
            if b and u and d and u[0]["nu_up"] > 0 and d[0]["nu_down"] > 0:
                print(f"| {geom} | {ra:.0e} | {b[0]['nu_up'] / u[0]['nu_up']:.2f} | {b[0]['nu_down'] / d[0]['nu_down']:.2f} |")
    be = load("board_effect.json")
    if be:
        keys = ["jaffer", "up x0.6", "down x1.3", "up x0.6 down x1.3", "up x1.2", "down x0.7"]
        print("\nC. rise of the hottest point (K) with the program's levels and the change with each other level (convection and radiation)")
        print("| case | program (K) | " + " | ".join(keys) + " |")
        print("| :-- | --: | " + " | ".join("--:" for _ in keys) + " |")
        for r in be:
            print(f"| {r['case']} | {r['program']['rise']:.2f} | " + " | ".join(f"{100 * (r[k]['rise'] / r['program']['rise'] - 1):+.1f} %" for k in keys) + " |")
        print("\nD. the same with the emissivity at zero (convection only)")
        print("| case | program (K) | " + " | ".join(keys) + " |")
        print("| :-- | --: | " + " | ".join("--:" for _ in keys) + " |")
        for r in be:
            if "conv_program" in r:
                print(f"| {r['case']} | {r['conv_program']['rise']:.2f} | " + " | ".join(f"{100 * (r['conv_' + k]['rise'] / r['conv_program']['rise'] - 1):+.1f} %" for k in keys) + " |")


if __name__ == "__main__":
    main()
