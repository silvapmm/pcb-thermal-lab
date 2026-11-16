#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_case2_h_sweep.py
@brief Case 2 of Muzychka, Culham and Yovanovich (2003) swept over the bottom coefficient h: does the shortfall of the models grow for a lower h?
@details For h from 10 to 2000 W/m2K (paper: 400) the independent 3D solver (dx 0.5 mm, 8 sub-slabs) gives the surface centroid temperature of every source (the paper's quantity) and the
         through-thickness mean of the column (the quantity one node per layer stands for); the FVM, FDM, Analytic, Lumped (0.5 mm) and 3D solid (1 mm) are run on the same plate and the
         error in K and in % of the rise is printed, against both references. The through-thickness term and the film term do not depend on h (they are set by the flux and by t/k), so the
         error in K should be flat and the error in % should fall with the rise. Writes out/h_sweep.json for make_figures.py.
         Run from the repository root: .venv/bin/python -u research/muzychka-case2-analytic/scripts/study_case2_h_sweep.py
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import case2 as C  # noqa: E402

OUT = os.path.join(HERE, "..", "out")
HS = (10.0, 25.0, 50.0, 100.0, 200.0, 400.0, 1000.0, 2000.0)
MODELS = (("fvm", 0.5), ("fdm", 0.5), ("analytic", 0.5), ("lumped", 0.5), ("solid3d", 1.0))


def main():
    """!
    @brief Run the sweep and print the table.
    @return None.
    """
    os.makedirs(OUT, exist_ok=True)
    data = {}
    print("error of the layer temperature at the source centroid: K against the 3D surface | K against the 3D layer mean   (source 2, 25 W; and the mean over the four sources)")
    for h in HS:
        ref = C.reference3d(0.5, 8, h=h)
        rise = np.array(ref["surf_c"]) - C.AMB
        row = {"surf_c": ref["surf_c"], "lay_c": ref["lay_c"], "models": {}}
        print(f"\nh = {h:6.0f}: 3D surface centroid {np.round(ref['surf_c'], 2).tolist()} (rise of source 2: {rise[1]:.1f} K), layer mean {np.round(ref['lay_c'], 2).tolist()}")
        for m, cell in MODELS:
            r, sim = C.run(m, cell, h=h)
            if r is None:
                continue
            cen = np.array(r["cen"])
            e_surf, e_lay = cen - ref["surf_c"], cen - ref["lay_c"]
            row["models"][m] = {"cen": r["cen"], "e_surf": e_surf.tolist(), "e_lay": e_lay.tolist(), "e_surf_pct": (100 * e_surf / rise).tolist()}
            print(f"  {m:8s} err vs surface: S2 {e_surf[1]:6.2f} K ({100 * e_surf[1] / rise[1]:5.1f} %), mean {e_surf.mean():6.2f} K ({100 * (e_surf / rise).mean():5.1f} %), range [{e_surf.min():.2f}, {e_surf.max():.2f}]"
                  f"   | vs layer mean: S2 {e_lay[1]:6.2f} mean {e_lay.mean():6.2f} K", flush=True)
        data[str(h)] = row
    with open(os.path.join(OUT, "h_sweep.json"), "w") as fh:
        json.dump(data, fh, indent=1, default=float)


if __name__ == "__main__":
    main()
