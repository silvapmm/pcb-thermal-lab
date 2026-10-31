#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_solver_checks.py
@brief Review checks of the solver `lib/plate_h2d.py`: is the heat of the plate what the wall gradient says, is the isolated upper face grid- and domain-converged, and does the coupling of the two faces survive when the heat is measured on closed boxes instead of the wall?

@details Added by the review of the folder. Three parts, all on the solver of `study_plate_h2d.py` (Pr 0.71, Nu of L = A/P):

         1. the heat crossing three closed boxes around the plate (x to 1.5, 2 and 3; y from -0.5 to 1, -1 to 2, -2 to 4) over the heat of the wall gradient, for every strip and disc case
            at the base grid (`HorizontalStrip.heat_through_box`): if the boxes agree with each other but not with the wall, the wall gradient (the singular flux at the edge of a
            zero-thickness plate) is the error; if they drift from box to box, the field is not conservative;
         2. the isolated upper face (lower face insulated) on the finer grid and the larger domain of the README (strip Ra 1e3 and 1e4, disc Ra 1e3): the first version checked
            only the both-faces and lower-face cases;
         3. the coupling of the two faces measured on totals: Nu(both faces hot) over Nu(upper alone) + Nu(lower alone), from the wall and from the middle box.

         Prints the tables and writes out/solver_checks.json.

Usage: .venv/bin/python research/horizontal-plate-h/scripts/study_solver_checks.py   (22 solver runs; run it in the background)
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, HERE)

import plate_h2d as ph                                    # noqa: E402
from study_plate_h2d import BASE, FINE, WIDE, FACES, PR, dt_for      # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
BOXES = ((1.5, 1.0, -0.5), (2.0, 2.0, -1.0), (3.0, 4.0, -2.0))


def one(geometry, ra_l, faces, grid, name):
    """!
    @brief Run one case of the solver as `study_plate_h2d.py` does and measure the heat on the wall and on the three boxes.
    @param geometry "strip" or "disc".
    @param ra_l Rayleigh number of L = A/P.
    @param faces Key of FACES.
    @param grid Keyword arguments of the grid.
    @param name Label of the grid.
    @return dict with Nu of the two faces (wall gradient), the box ratios and the convergence flag.
    """
    disc = geometry == "disc"
    ra = 8.0 * ra_l if disc else ra_l
    m = ph.HorizontalStrip(ra, PR, axisym=disc, **grid, **FACES[faces])
    m.relax = 0.15
    r = m.run(max_steps=400000, check=2500, tol=2e-5, dt=dt_for(max(ra, 1e-6)) if ra >= 1.0 else 5e-4)
    s = 0.5 if disc else 1.0                                 # Nu_L = Nu_R / 2 for the disc
    boxes = [m.heat_through_box(*b) for b in BOXES]
    out = {"geometry": geometry, "ra_l": ra_l, "faces": faces, "grid": name, "nu_up": s * r["nu_up"], "nu_down": s * r["nu_down"], "converged": bool(r["converged"]), "boxes": boxes}
    print(f"{geometry:5s} Ra_L {ra_l:8.0e} {faces:5s} {name:5s} Nu up {out['nu_up']:6.3f} down {out['nu_down']:6.3f} conv {out['converged']} boxes " + " ".join(f"{b:.3f}" for b in boxes), flush=True)
    return out


def main():
    """!
    @brief Run the three parts, print the tables and write out/solver_checks.json.
    @return None.
    """
    res = []
    for geometry in ("strip", "disc"):
        res.append(one(geometry, 1e-3, "both", BASE, "base"))                 # conduction: no convection, only the wall gradient can be off
    for geometry, ras in (("strip", (1e3, 1e4)), ("disc", (1e2, 1e3, 1e4))):
        for ra in ras:
            for faces in ("both", "up", "down"):
                res.append(one(geometry, ra, faces, BASE, "base"))
    for geometry, ra in (("strip", 1e3), ("strip", 1e4), ("disc", 1e3)):
        for name, grid in (("fine", FINE), ("wide", WIDE)):
            res.append(one(geometry, ra, "up", grid, name))
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "solver_checks.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("\n1. heat through the boxes over the heat of the wall gradient (base grid)")
    print("| geometry | Ra | faces | Nu (wall) | box 1.5 | box 2 | box 3 |")
    print("| :-- | --: | :-- | --: | --: | --: | --: |")
    for r in res:
        if r["grid"] == "base":
            print(f"| {r['geometry']} | {r['ra_l']:.0e} | {r['faces']} | {r['nu_up'] + r['nu_down']:.3f} | " + " | ".join(f"{b:.3f}" for b in r["boxes"]) + " |")
    print("\n2. the isolated upper face on three grids (Nu of the wall; in brackets Nu of the middle box)")
    print("| geometry | Ra | base | fine | wide |")
    print("| :-- | --: | --: | --: | --: |")
    for geometry, ra in (("strip", 1e3), ("strip", 1e4), ("disc", 1e3)):
        cells = []
        for name in ("base", "fine", "wide"):
            q = [r for r in res if r["geometry"] == geometry and r["ra_l"] == ra and r["faces"] == "up" and r["grid"] == name][0]
            cells.append(f"{q['nu_up']:.3f} ({q['nu_up'] * q['boxes'][1]:.3f})")
        print(f"| {geometry} | {ra:.0e} | " + " | ".join(cells) + " |")
    print("\n3. the coupling on totals: Nu(both) / [Nu(up alone) + Nu(down alone)], from the wall and from the middle box")
    print("| geometry | Ra | wall | box 2 |")
    print("| :-- | --: | --: | --: |")
    for geometry, ras in (("strip", (1e3, 1e4)), ("disc", (1e2, 1e3, 1e4))):
        for ra in ras:
            get = lambda fc: [r for r in res if r["geometry"] == geometry and r["ra_l"] == ra and r["faces"] == fc and r["grid"] == "base"][0]
            b, u, d = get("both"), get("up"), get("down")
            wall = (b["nu_up"] + b["nu_down"]) / (u["nu_up"] + d["nu_down"])
            box = (b["nu_up"] + b["nu_down"]) * b["boxes"][1] / (u["nu_up"] * u["boxes"][1] + d["nu_down"] * d["boxes"][1])
            print(f"| {geometry} | {ra:.0e} | {wall:.2f} | {box:.2f} |")


if __name__ == "__main__":
    main()
