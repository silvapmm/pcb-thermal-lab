#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cutcell_capacity.py
@brief Do the capacities of the cut cells (volume fraction = cover) need the cut-cell treatment? Slowest time constant and total capacity of a 20 mm disc for the program, the exact cover and the cut-cell links.
@details The slowest mode of the network (the generalised eigenproblem K x = lambda C x, smallest lambda, `scipy.sparse.linalg.eigsh` in shift-invert mode on the nodes with a capacity)
         is the time constant that a transient would show last. The capacity is `sum(C)` of the active nodes. Both are printed for `program`, `program@exact`, `links` and `links@exact` at
         1, 0.5 and 0.25 mm, with the capacity relative to the exact-cover value at 0.25 mm. Light (a few seconds, below 0.1 GB).
Usage: .venv/bin/python research/rotated-square-3d/scripts/study_cutcell_capacity.py   (from the repository root)
"""

import os
import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)

import fvm_cutcell as fc          # noqa: E402
import cutcell_exact              # noqa: E402
import rotsq                      # noqa: E402
from pcbthermal import fvm        # noqa: E402


def slowest(problem, cell, scheme):
    """!
    @brief Slowest time constant and total capacity of the network of a scheme.
    @param problem Problem.
    @param cell Cell in mm.
    @param scheme "program", "program@exact", "links" or "links@exact".
    @return (time constant in s, total capacity in J/K).
    """
    n = int(round(problem.board.width * 1000 / cell))
    base, _, flag = scheme.partition("@")
    exact = flag == "exact"
    if base == "program":
        if exact:
            with cutcell_exact.using_exact_cover():
                net = fvm.Network(problem, n, n)
        else:
            net = fvm.Network(problem, n, n)
    else:
        with fc.using_cutcell(base, exact=exact):
            net = fvm.Network(problem, n, n)
    cap = net.C.ravel()
    keep = cap > 0                                   # the cells off the board carry no capacity (and a pin to the ambient)
    K = net.K.tocsr()[keep][:, keep]
    lam = spla.eigsh(K, k=1, M=sp.diags(cap[keep]), sigma=0.0, which="LM", return_eigenvectors=False)[0]
    return 1.0 / lam, float(cap[keep].sum())


def main():
    """!
    @brief Print the table.
    @return None.
    """
    print("| cell (mm) | scheme | slowest time constant (s) | capacity / exact-cover capacity at 0.25 mm - 1 |\n| --: | :-- | --: | --: |")
    res = {}
    for cell in (1.0, 0.5, 0.25):
        for s in ("program", "program@exact", "links", "links@exact"):
            res[(cell, s)] = slowest(rotsq.disc_board(20.0, 1.5, 10.0, box_mm=30.0), cell, s)
    ref = res[(0.25, "program@exact")][1]
    for (cell, s), (t, c) in res.items():
        print(f"| {cell:g} | {s} | {t:.3f} | {c / ref - 1:+.2e} |")
    ts = np.array([v[0] for v in res.values()])
    print(f"\nspread of the time constant over every case: {(ts.max() - ts.min()) / ts.mean():.1e} (relative)")


if __name__ == "__main__":
    main()
