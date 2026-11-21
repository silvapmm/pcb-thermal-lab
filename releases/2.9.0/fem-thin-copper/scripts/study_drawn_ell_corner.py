#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_drawn_ell_corner.py
@brief The part of `drawn_ell` over the corner without top copper: the FEM column and surface term against an independent 3D solver with the copper patterned per cell, and the frozen board in the FVM, the 3D solid and the FEM.
@details Question: the face load of a part on an outer layer moves the FEM column of `drawn_ell` by 0.1 to 1.5 K (2 to 0.5 mm). Is the move toward a reference that does not share
         the program's assumptions? Part A (independent check): the board of `drawn_ell` (20 x 20 mm, two layers of 35 um, 1.6 mm, an L of top copper without the corner
         x, y > 10.8 mm, bottom copper 1.2 mm inside the wall, a 4 x 4 mm 1 W part at the centre, 10 W/m2K on both faces) with two changes that the independent solver needs:
         no edge film (its sides are insulated) and a laminate of 0.3 W/mK in every direction. The reference is `tests/helpers/layered3d.py` (it imports nothing from the
         program): 8 sub-slabs through the top copper, 6 through the laminate, 2 through the bottom copper, every cell of a copper slab copper or laminate by the drawn
         polygons (the edges 1.2, 8, 10.8, 12, 18.8 mm lie on the cell edges of 0.4 and 0.2 mm), the film also under the part (as the program). Printed per cell: the hottest
         column under the part (the mean through the top copper slab) and the hottest surface, and their difference, for the reference, the FVM and the FEM. Part B (the frozen
         board as it is, edge film and default materials): the column t_max and the surface term under the part at 2, 1 and 0.5 mm for the FVM, the 3D solid and the FEM.
         Run it on the tree before the fix and on the tree after it (`--tree`) to see the move.
         Usage: .venv/bin/python releases/2.9.0/fem-thin-copper/scripts/study_drawn_ell_corner.py [--tree <root>] [--cells 0.4,0.2] [--frozen-cells 2,1,0.5] [--json out.json]
         (about 30 s).
"""

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
K_LAM = 0.3                                   # laminate of part A, W/mK in every direction (the independent solver is isotropic per cell)
TOP = [(1.2, 1.2, 18.8, 10.8), (1.2, 10.8, 10.8, 18.8)]   # the L of top copper, mm
BOTTOM = [(1.2, 1.2, 18.8, 18.8)]                          # the bottom copper, mm
PART = (8.0, 8.0, 12.0, 12.0)                               # the 4 mm part, mm


def parse():
    """!
    @brief Read the command line and put the chosen tree and the helpers on the import path.
    @return argparse.Namespace.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tree", default=ROOT, help="root of the tree whose pcbthermal is measured")
    ap.add_argument("--cells", default="0.4,0.2", help="cells of part A in mm (each must divide 0.4 mm)")
    ap.add_argument("--frozen-cells", default="2,1,0.5", help="cells of part B in mm (empty: skip part B)")
    ap.add_argument("--json", default=None, help="file to write the numbers to")
    a = ap.parse_args()
    for p in (a.tree, os.path.join(ROOT, "tests", "helpers"), os.path.join(ROOT, "tests", "regression")):
        sys.path.insert(0, p)
    return a


def board_a():
    """!
    @brief The board of part A: `drawn_ell` without the edge film and with an isotropic laminate of K_LAM.
    @return Problem.
    """
    from pcbthermal import Problem
    from pcbthermal.model import Dielectric, Materials
    p = Problem.new(20.0, 20.0, layers=2, thickness_mm=1.6, copper_um=35.0, ambient=25.0, h_top=10.0, h_bottom=10.0, h_side=None,
                    materials=Materials(k_fr4_through=K_LAM, k_fr4_inplane=K_LAM))
    p.board.dielectrics = [Dielectric(thickness=1.6e-3 - 2 * 35e-6, name="FR-4", k_through=K_LAM, k_inplane=K_LAM, rho=1850.0, cp=1100.0)]
    for r in TOP:
        p.add_zone(1, rect=r)
    for r in BOTTOM:
        p.add_zone(2, rect=r)
    p.add_heater(1, 1.0, rect=PART, name="U")
    return p


def raster(rects, n, dx_mm, k_cu):
    """!
    @brief The conductivity of every cell of a copper slab: copper where the cell centre is inside a polygon, laminate elsewhere.
    @param rects Copper rectangles in mm.
    @param n Cells per side.
    @param dx_mm Cell in mm.
    @param k_cu Copper conductivity in W/mK.
    @return numpy.ndarray (n, n) in W/mK.
    """
    c = (np.arange(n) + 0.5) * dx_mm
    k = np.full((n, n), K_LAM)
    for x0, y0, x1, y1 in rects:
        k[(c[:, None] > y0) & (c[:, None] < y1) & (c[None, :] > x0) & (c[None, :] < x1)] = k_cu
    return k


def reference(p, dx_mm):
    """!
    @brief The independent 3D solution of the board of part A.
    @param p Problem (only its copper conductivity, thicknesses and films are read).
    @param dx_mm Cell in mm.
    @return dict col (hottest column under the part, degC), surf (hottest surface under the part, degC), balance (relative).
    """
    import layered3d as L3
    k_cu = p.board.materials.k_copper
    n = int(round(20.0 / dx_mm))
    t = 35e-6
    slabs = [(t, raster(TOP, n, dx_mm, k_cu), 8), (1.6e-3 - 2 * t, K_LAM, 6), (t, raster(BOTTOM, n, dx_mm, k_cu), 2)]
    r = L3.solve(dx_mm * 1e-3, n, n, slabs, tuple(v * 1e-3 for v in PART), 1.0, p.board.h_top, p.board.h_bottom, film_under_source=True)
    dz = np.array(r["dz"])
    col = np.tensordot(dz[:8] / dz[:8].sum(), r["T"][:8], axes=(0, 0))
    m = r["mask_source"]
    return {"col": 25.0 + float(col[m].max()), "surf": 25.0 + float(r["surface_top"][m].max()), "balance": float(r["heat_out"] - 1.0)}


def program(p, model, cell):
    """!
    @brief One model of the program on a board: the hottest column under the part and the hottest surface under it.
    @param p Problem.
    @param model Model key.
    @param cell Cell in mm.
    @return dict col, surf (degC, NaN when the model has no surface read-out) and balance (the model's energy balance error, relative, or None).
    """
    from pcbthermal import SolverOptions, analysis, simulate
    r = simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model]
    col = analysis.heater_stats(r, p)[0]["t_max"]
    s = analysis.surface_stats(r, p.heaters[0].polygon, 0, p.board.outline)
    surf = float(s[0]) if s is not None else float("nan")             # the 3D solid has no surface read-out yet
    return {"col": float(col), "surf": surf, "balance": getattr(r, "balance_error", None)}


def main():
    """!
    @brief Run part A and part B and print the tables.
    @return None.
    """
    args = parse()
    import pcbthermal
    assert os.path.dirname(os.path.dirname(os.path.abspath(pcbthermal.__file__))) == os.path.abspath(args.tree), "the program of another tree was imported"
    out = {"tree": args.tree, "a": [], "b": []}
    print(f"tree {args.tree} (pcbthermal {pcbthermal.__version__})")
    print("A: drawn_ell, no edge film, laminate 0.3 W/mK isotropic; hottest column and surface under the part (degC), term = surface - column (K)")
    p = board_a()
    for cell in [float(c) for c in args.cells.split(",") if c]:
        row = {"cell": cell, "ref": reference(p, cell)}
        for m in ("fvm", "fem"):
            row[m] = program(p, m, cell)
        out["a"].append(row)
        txt = " | ".join(f"{k} col {row[k]['col']:9.4f} term {row[k]['surf'] - row[k]['col']:6.3f}" for k in ("ref", "fvm", "fem"))
        print(f"  cell {cell:4.2f} mm | {txt}", flush=True)
    if args.frozen_cells:
        import regress_boards
        print("B: drawn_ell as frozen (edge film 200 W/m2K, default materials); column t_max under the part (degC), term (K)")
        pb = regress_boards.build("drawn_ell")
        for cell in [float(c) for c in args.frozen_cells.split(",") if c]:
            row = {"cell": cell}
            for m in ("fvm", "solid3d", "fem"):
                row[m] = program(pb, m, cell)
            out["b"].append(row)
            txt = " | ".join(f"{k} col {row[k]['col']:9.4f} term {row[k]['surf'] - row[k]['col']:6.3f}" for k in ("fvm", "solid3d", "fem"))
            print(f"  cell {cell:4.2f} mm | {txt}", flush=True)
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
