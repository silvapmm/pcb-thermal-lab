#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_case2_models.py
@brief Case 2 of Muzychka, Culham and Yovanovich (2003), the published four-source plate: the surface read-out of every model at the four source centroids against the paper's Table 4 and the independent 3D surface.
@details The independent solver (tests/helpers/layered3d.py through research/muzychka-case2-analytic/lib/case2.py) reproduces the paper's centroid temperatures (97.40 / 103.82 / 101.28 / 99.94 degC) to
         0.03 K; every model is read at the same four points: the FVM and FEM surfaces (the program's own arrays), the Lumped upper bound (column + q'' t / 2k) and its parabola, the Analytic rule F, and the 3D solid with
         1, 4 and 8 slabs through the copper. The column read-out is printed beside. Usage: .venv/bin/python research/surface-readout-models/scripts/study_case2_models.py (about 1 min, under 1.5 GB).
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (ROOT, os.path.join(HERE, "..", "lib"), os.path.join(ROOT, "research", "muzychka-case2-analytic", "lib"), os.path.join(ROOT, "research", "through-thickness-readout", "lib")):
    if p not in sys.path:
        sys.path.insert(0, p)
import case2  # noqa: E402
import rules  # noqa: E402
import solid3d_sublayers  # noqa: E402
from pcbthermal import SolverOptions, simulate  # noqa: E402

CELL = 0.5


def centroids(field):
    """!
    @brief Value of a map at the four source centroids (mean of the four cells around each).
    @param field Array (ny, nx).
    @return numpy array of four values.
    """
    dx = case2.W_MM / field.shape[1]
    return np.array([case2.corner_value(field, dx, *c) for c in case2.CENTRES])


def main():
    """!
    @brief Print the table of errors against the independent 3D surface.
    """
    ref = case2.reference3d(CELL, 8)
    surf, col = np.array(ref["surf_c"]), np.array(ref["lay_c"])
    paper = np.array(case2.PAPER_CENTROID)
    prob = case2.problem()
    fmt = lambda v: " ".join(f"{x:+7.2f}" for x in v)  # noqa: E731
    print(f"paper Table 4 {fmt(paper)} | independent 3D surface {fmt(surf)} (minus paper {fmt(surf - paper)}) | 3D column mean {fmt(col)} | term {fmt(surf - col)}")
    print("errors against the independent 3D surface at the four centroids (K, + hot)")
    res = {m: simulate(prob, SolverOptions(models=(m,), cell_mm=CELL)).results[m] for m in ("fvm", "fem", "lumped", "analytic")}
    for m in ("fvm", "fem"):
        print(f"  {m:8s} surface   {fmt(centroids(res[m].arrays['T_surface'][0]) - surf)}   (column {fmt(centroids(res[m].T[0]) - col)})")
    for m in ("lumped", "analytic"):
        f = rules.field_rule(prob, np.asarray(res[m].T), CELL)
        cen = centroids(res[m].T[0])
        print(f"  {m:8s} column    {fmt(cen - col)}")
        print(f"  {m:8s} parabola  {fmt(centroids(f['top']) - surf)}   (rule F)")
        if m == "lumped":
            print(f"  {m:8s} UPPER BOUND {fmt(cen + centroids(f['bound_top']) - surf)}   (column + q'' t / 2k; never below the surface when positive)")
    for n in (1, 4, 8):
        mod = solid3d_sublayers.load(n)
        net = mod.Solid(prob, CELL)
        theta, _ = net.solve()
        r = rules.solid_rule(net, theta, n)
        print(f"  solid3d {n} slab{'s' if n > 1 else ' '} surface {fmt(centroids(r['top']) - surf)}   (column {fmt(centroids(r['col']) - col)})")


if __name__ == "__main__":
    main()
