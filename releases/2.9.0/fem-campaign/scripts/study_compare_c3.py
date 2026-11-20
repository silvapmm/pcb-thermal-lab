#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_compare_c3.py
@brief Row C3 of the FEM campaign (validation 56.3): case 2 of Muzychka, Culham and Yovanovich (2003) in the six models of the program, the column read-out against the independent
       3D solver's column mean and the surface read-out against the paper's printed surface values.
@details The plate is 50 x 50 x 10 mm, k 150 W/mK, h 400 W/m2K on the bottom, adiabatic top, four 10 x 10 mm sources of 10, 25, 20 and 15 W
         (`research/muzychka-case2-analytic/lib/case2.py`, which also holds the independent 3D solver, `tests/helpers/layered3d.py`, and the paper's printed centroid and mean
         temperatures, Table 4, status R of [Muzychka2003]). Two read-outs of each model: the **column** (the layer temperature, centroid of each source) against the column mean of the
         independent solver (0.5 mm cell, 8 sub-slabs), and the **surface** (`arrays['T_surface']`, the face of the part: the 3D solid, the FEM and the estimate of the FVM and FDM)
         against the paper's printed centroid. The Lumped and Analytic give the column only. Differences in K, signed, model minus reference.
         Run from the repository root: `.venv/bin/python -u releases/2.9.0/fem-campaign/scripts/study_compare_c3.py` (about 1 min, under 2 GB).
"""

import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research" / "muzychka-case2-analytic" / "lib"))
LABEL = {"fvm": "FVM", "fdm": "FDM", "lumped": "Lumped", "analytic": "Analytic", "solid3d": "3D solid", "fem": "FEM"}


def fmt(v):
    """!
    @brief Four numbers as a table cell.
    @param v Iterable of floats.
    @return str.
    """
    return " / ".join(f"{x:+.2f}" for x in v)


def surface_readout(sim, model, case2):
    """!
    @brief Centroid of each source on the surface map of a model.
    @param sim Simulation.
    @param model Model key.
    @param case2 The case2 module.
    @return list of 4 floats in degC, or None when the model has no surface map.
    """
    res = sim.results[model]
    arr = getattr(res, "arrays", None) or {}
    if "T_surface" not in arr:
        return None
    s = np.asarray(arr["T_surface"][0], dtype=float)
    if not np.isfinite(s).any():
        return None
    dx = case2.W_MM / s.shape[1]
    return [case2.corner_value(s, dx, *c) for c in case2.CENTRES]


def main():
    """!
    @brief Print the tables of case 2.
    @return None.
    """
    import case2 as C
    tree = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"tree {tree}, program {sys.modules['pcbthermal'].__version__}")
    ref = C.reference3d(0.5, 8)
    print(f"independent 3D solver (0.5 mm, 8 sub-slabs): column mean at the centroids {' / '.join(f'{x:.2f}' for x in ref['lay_c'])}, surface centroid {' / '.join(f'{x:.2f}' for x in ref['surf_c'])} degC")
    print(f"paper (Table 4) centroid {' / '.join(f'{x:.2f}' for x in C.PAPER_CENTROID)}, mean {' / '.join(f'{x:.2f}' for x in C.PAPER_MEAN)} degC\n")
    print("### Column read-out: centroid of each source minus the column mean of the independent 3D solver, K (S1 / S2 / S3 / S4)")
    print("| model | 2 mm | 1 mm | 0.5 mm |\n| :-- | :-- | :-- | :-- |")
    surf = {}
    for m in ("fem", "fvm", "fdm", "solid3d", "analytic", "lumped"):
        row = []
        for cell in (2.0, 1.0, 0.5):
            r, sim = C.run(m, cell)
            if r is None:
                row.append("not run")
                continue
            row.append(fmt(np.array(r["cen"]) - np.array(ref["lay_c"])))
            s = surface_readout(sim, m, C)
            if s is not None:
                surf[(m, cell)] = s
        print(f"| {LABEL[m]} | " + " | ".join(row) + " |")
    print("\n### Surface read-out: centroid of each source on the surface map minus the paper's printed centroid, K (S1 / S2 / S3 / S4); the independent 3D solver's own surface minus the paper is "
          + fmt(np.array(ref["surf_c"]) - np.array(C.PAPER_CENTROID)))
    print("| model | 2 mm | 1 mm | 0.5 mm |\n| :-- | :-- | :-- | :-- |")
    for m in ("fem", "fvm", "fdm", "solid3d"):
        row = [fmt(np.array(surf[(m, c)]) - np.array(C.PAPER_CENTROID)) if (m, c) in surf else "-" for c in (2.0, 1.0, 0.5)]
        print(f"| {LABEL[m]} | " + " | ".join(row) + " |")
    print("\nThe Lumped and Analytic have no surface map. The column minus the paper is not a comparison (the paper prints the surface).")


if __name__ == "__main__":
    main()
