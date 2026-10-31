#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_gci_references.py
@brief F7: grid convergence index (Celik et al. 2008, equations 3 to 7, three grids, safety factor 1.25) of the independent 3D solver and of the program's FVM and FDM on the Muzychka cases.
@details Case 2 (50 mm baseplate, k 150, four 10 mm sources; cells 0.125, 0.25 and 0.5 mm for the 3D solver, 0.5, 1 and 2 mm for the models of the program) and case 3 (100 mm plate, k 50, cross of five
20 mm sources; cells 0.5, 1 and 2 mm for both). The quantity is the mean temperature of the hottest source (case 2, source 2) and of the centre source (case 3).
Run from the repository root: .venv/bin/python research/theory-sources/scripts/study_gci_references.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import study_muzychka_more_cases as M  # noqa: E402
import gci  # noqa: E402

CASE2 = M.CASES["2"]
CASE3 = {"w": 100.0, "dx": 1.0, "h": 50.0, "slabs": [(10.0, 50.0, 6)],
         "sources": [(M.sq(50, 50, 20), 5.0), (M.sq(30, 50, 20), 5.0), (M.sq(70, 50, 20), 5.0), (M.sq(50, 30, 20), 5.0), (M.sq(50, 70, 20), 5.0)]}


def run(case, index, dx_independent, dx_models):
    """!
    @brief Mean temperature of one source on three grids by the independent solver and the two finite models.
    @param case Case dictionary.
    @param index Index of the source.
    @param dx_independent Three cell sizes in mm (finest first) for the independent solver.
    @param dx_models Three cell sizes in mm (finest first) for the models of the program.
    @return Dict name -> list of three values (finest first).
    """
    out = {"independent": [M.independent(dict(case, dx=d))["mean"][index] for d in dx_independent]}
    for m in ("fvm", "fdm"):
        out[m] = [M.program(case, m, d)["mean"][index] for d in dx_models]
    return out


def report(name, values, dxs_i, dxs_m):
    """!
    @brief Print the values and the GCI of every series.
    @param name Case name.
    @param values Dict from run().
    @param dxs_i Cell sizes of the independent solver.
    @param dxs_m Cell sizes of the models.
    @return None.
    """
    print(f"\n{name}")
    for key, v in values.items():
        dxs = dxs_i if key == "independent" else dxs_m
        g = gci.gci(v[0], v[1], v[2], dxs[1] / dxs[0], dxs[2] / dxs[1])
        print("  %-11s cells %s mm: %s K | p %.2f, extrapolated %.3f K, GCI fine %.2f %% (%.3f K)"
              % (key, dxs, ", ".join("%.3f" % x for x in v), g["p"], g["phi_ext21"], 100 * g["gci_fine21"], g["gci_fine21"] * v[0]))


def main():
    """!
    @brief Run both cases.
    @return None.
    """
    # The source edges of case 2 lie at 7.5 mm, so the independent solver (edges on cell edges) needs cells that divide 2.5 mm: 0.125, 0.25 and 0.5
    case2 = dict(CASE2, slabs=[(10.0, 150.0, 4)])
    di, dm = (0.125, 0.25, 0.5), (0.5, 1.0, 2.0)
    report("Case 2, mean temperature of the hottest source (25 W), 4 sub-slabs", run(case2, 1, di, dm), di, dm)
    # The number of sub-slabs through the thickness is a second refinement direction: case 2 at 0.5 mm cells with 16, 8 and 4 sub-slabs (the 0.5 mm run above has 4)
    zs = [M.independent(dict(CASE2, dx=0.5, slabs=[(10.0, 150.0, n)]))["mean"][1] for n in (16, 8, 4)]
    g = gci.gci(zs[0], zs[1], zs[2], 2.0, 2.0)
    print("  independent, 0.5 mm cells, 16/8/4 sub-slabs through the thickness: %s K | p %.2f, extrapolated %.3f K, GCI fine %.2f %%"
          % (", ".join("%.3f" % x for x in zs), g["p"], g["phi_ext21"], 100 * g["gci_fine21"]))
    di, dm = (0.5, 1.0, 2.0), (0.5, 1.0, 2.0)
    report("Case 3, mean temperature of the centre source", run(CASE3, 0, di, dm), di, dm)


if __name__ == "__main__":
    main()
