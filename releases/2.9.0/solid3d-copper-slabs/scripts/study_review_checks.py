#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review_checks.py
@brief Two checks of the review of `feature/solid3d-copper-slabs`: the column of a thick plate converges in the slabs (independent solver), and the program's FEM agrees with the 3D solid on it.
@details Question 1: is the column of the 3D solid with 8 copper slabs converged through the thickness, or does it only agree with a reference cut into the same 8 slabs? The independent
         solver `tests/helpers/layered3d.py` (imports nothing from the program) solves three plates of `research/surface-readout-models/lib/plates.py` (case 2, 10 mm aluminium, 10 mm
         copper; 50 mm square, the 1 um laminate of the program's plate) with 1, 8, 16 and 32 slabs through the metal at a 1 mm cell. Question 2: the program's FEM (copper slabs of its
         own, a flux on the face) and 3D solid on the same plates at 2 and 1 mm. Prints the column maximum and the surface maximum under the source, degC.

             .venv/bin/python releases/2.9.0/solid3d-copper-slabs/scripts/study_review_checks.py [--skip-fem]
"""

import argparse
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
CASES = [("case 2", 10.0, 150.0, 10.0, 25.0, 400.0), ("10 mm Al", 10.0, 200.0, 10.0, 100.0, 1000.0), ("10 mm Cu", 10.0, 385.0, 10.0, 40.0, 400.0)]


def convergence(dx_mm=1.0, w_mm=50.0, amb=25.0):
    """!
    @brief The independent solver with 1, 8, 16 and 32 slabs through the metal of every plate.
    @param dx_mm Plan cell, mm.
    @param w_mm Side of the plate, mm.
    @param amb Ambient, degC.
    @return None (prints one line per plate).
    """
    sys.path.insert(0, str(REPO / "tests" / "helpers"))
    import layered3d as L3
    n = int(round(w_mm / dx_mm))
    c = w_mm / 2.0
    for name, t, k, a, P, h in CASES:
        rect = tuple(v * 1e-3 for v in (c - a / 2, c - a / 2, c + a / 2, c + a / 2))
        out = []
        for ns in (1, 8, 16, 32):
            # The metal in ns slabs, then the 1 um laminate (thickness 1.0001 t of the program's plate) in 4
            r = L3.solve(dx_mm * 1e-3, n, n, [(t * 1e-3, k, ns), (t * 1e-7, 0.3, 4)], rect, P, 0.0, h)
            dz = np.array(r["dz"][:ns])
            col = np.tensordot(dz / dz.sum(), r["T"][:ns], axes=(0, 0))
            m = r["mask_source"]
            out.append(f"n={ns}: column {amb + float(col[m].max()):.3f} surface {amb + float(r['surface_top'][m].max()):.3f}")
        print(f"independent, {name}, {dx_mm} mm: " + "  ".join(out), flush=True)


def fem_and_solid():
    """!
    @brief The program's FEM and 3D solid on the three plates at 2 and 1 mm.
    @return None (prints one line per plate).
    """
    sys.path.insert(0, str(REPO))
    sys.path.insert(0, str(REPO / "research" / "surface-readout-models" / "lib"))
    import plates
    from pcbthermal import fem, solid3d
    names = {"case 2": "case 2", "10 mm Al": "10 mm Al", "10 mm Cu": "10 mm Cu"}
    for spec in plates.PLATES:
        if not any(spec[0].startswith(k) for k in names):
            continue
        p = plates.problem(spec)
        out = []
        for cell in (2.0, 1.0):
            r = fem.solve_steady(p, cell_mm=cell)
            s = solid3d.solve_steady(p, cell_mm=cell)
            out.append(f"{cell} mm: FEM column {r.t_max:.3f} surface {float(np.nanmax(r.arrays['T_surface'][0])):.3f}, 3D solid column {s.t_max:.3f}")
        print(f"{spec[0]}: " + "  |  ".join(out), flush=True)


def main(argv=None):
    """!
    @brief Run both checks.
    @param argv Arguments (default sys.argv[1:]).
    @return int exit code.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--skip-fem", action="store_true", help="only the convergence of the independent solver")
    a = ap.parse_args(argv)
    convergence()
    if not a.skip_fem:
        fem_and_solid()
    return 0


if __name__ == "__main__":
    sys.exit(main())
