#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fem_thin_copper.py
@brief The surface minus column term of the FVM and the FEM on thin-copper plates against the independent 3D solver, and the column and energy balance of the FEM (for the fix of the part's source on thin copper).
@details Question: after the part on an outer copper layer of any thickness enters the FEM through its face (femmesh.build), does the FEM read the surface term like the independent solver,
         and does the column move by no more than milli-kelvin? Plates: a 50 x 50 mm two-layer board (lib/plates.py of research/surface-readout-models: top copper of 18, 35, 70 and 105 um,
         1 mm laminate of 0.3 W/mK, 35 um bottom copper, a film below), a square part of 2, 4 or 8 mm centred on the top copper. The reference is tests/helpers/layered3d.py (8 sub-slabs
         through the copper, 4 through the laminate, the cell of the study in the plane), which imports nothing from the program. Printed per case: the column under the part and the
         term (surface minus column, K) of the independent solver, the FVM and the FEM, the FEM balance error, and the term in units of q t / (2 k). With `--json` the numbers are
         also written to the file given (the before/after comparison of the fix runs the study on the tree before it and on the tree after it: `--tree <root of the tree>`).
         Usage: .venv/bin/python releases/2.9.0/fem-thin-copper/scripts/study_fem_thin_copper.py [--cell 1.0] [--tree <root>] [--json out.json] (about 1 min at 1 mm).
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))


def parse():
    """!
    @brief Read the command line and put the chosen tree and the helpers on the import path.
    @return argparse.Namespace.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cell", type=float, default=1.0, help="plan cell in mm")
    ap.add_argument("--tree", default=ROOT, help="root of the tree whose pcbthermal is measured")
    ap.add_argument("--json", default=None, help="file to write the numbers to")
    a = ap.parse_args()
    for p in (a.tree, os.path.join(ROOT, "research", "surface-readout-models", "lib"), os.path.join(ROOT, "tests", "helpers")):
        sys.path.insert(0, p)
    return a


def case_problem(t_um, a_mm, power, h):
    """!
    @brief The plate as a Problem (a two-layer board, the part on the top copper).
    @param t_um Top copper thickness in um.
    @param a_mm Side of the square part in mm.
    @param power Part power in W.
    @param h Film coefficient below in W/m2K.
    @return tuple (Problem, spec in the layout of plates.PLATES).
    """
    import plates
    spec = (f"{t_um:g} um Cu, a {a_mm:g}", "two", t_um * 1e-3, plates.K_CU, a_mm, power, h, False)
    return plates.problem(spec), spec


def main():
    """!
    @brief Run every case and print the table.
    """
    args = parse()
    # The program first, from the tree asked for: lib/plates.py of the other study puts its own tree on the path, and a module already imported wins
    from pcbthermal import SolverOptions, analysis, simulate
    import pcbthermal
    import plates
    assert os.path.dirname(os.path.dirname(os.path.abspath(pcbthermal.__file__))) == os.path.abspath(args.tree), "the program of another tree was imported"
    rows = []
    print(f"tree {args.tree} (pcbthermal {pcbthermal.__version__}); cell {args.cell} mm; term = surface minus column under the part (mK); bound = q t / (2 k)")
    for t_um in (18.0, 35.0, 70.0, 105.0):
        for a_mm in (2.0, 4.0, 8.0):
            power = 1.0
            p, spec = case_problem(t_um, a_mm, power, 10.0)
            ref = plates.reference(spec, dx_mm=args.cell, n_sub=8)
            bound = power / (a_mm * 1e-3) ** 2 * t_um * 1e-6 / (2.0 * plates.K_CU)
            o = {"t_um": t_um, "a_mm": a_mm, "bound_K": bound, "ref_col": ref["col"], "ref_term": ref["surf"] - ref["col"]}
            for m in ("fvm", "fem"):
                r = simulate(p, SolverOptions(models=(m,), cell_mm=args.cell)).results[m]
                col = analysis.heater_stats(r, p)[0]["t_max"]
                surf = analysis.surface_stats(r, p.heaters[0].polygon, 0, p.board.outline)[0]
                o[f"{m}_col"], o[f"{m}_term"] = col, surf - col
                if m == "fem":
                    o["fem_balance"] = float(r.balance_error)
            rows.append(o)
            print(f"t {t_um:5.0f} um a {a_mm:3.0f} mm bound {1e3 * bound:7.3f} mK | ref col {o['ref_col']:8.4f} term {1e3 * o['ref_term']:7.3f} ({o['ref_term'] / bound:4.2f}) | "
                  f"FVM col {o['fvm_col'] - o['ref_col']:+7.4f} term {1e3 * o['fvm_term']:7.3f} ({o['fvm_term'] / bound:4.2f}) | "
                  f"FEM col {o['fem_col'] - o['ref_col']:+7.4f} term {1e3 * o['fem_term']:7.3f} ({o['fem_term'] / bound:4.2f}) bal {o['fem_balance']:+.1e}", flush=True)
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    main()
