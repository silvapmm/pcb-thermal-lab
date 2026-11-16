#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_options.py
@brief Muzychka, Culham and Yovanovich (2003) case 2 (10 mm plate, four sources) read at the surface: option A (read-out from the node and the face fluxes), option B (N sub-layers
       through the plate in the FVM, FDM, Lumped and Analytic) and option C (N slabs through the copper of the 3D solid), against the independent 3D solver.

@details Answers: how far is each read-out from the paper's surface temperature (97.40 / 103.82 / 101.28 / 99.94 C, Table 4 of the paper, page 184), from the independent solver's
         surface and from its column mean, and what does it cost in unknowns and time. Nothing of the program is edited: option B is the program run on a stack of N copper layers joined by
         links of the plate's own conductivity (`lib/sublayers.py`), option C the program's `solid3d.py` read as text with one line replaced (`lib/solid3d_sublayers.py`).
         Prints the tables and writes `out/options.json` (git-ignored). Cell 0.5 mm. Peak memory under 1 GB.
         Usage: .venv/bin/python research/through-thickness-readout/scripts/study_options.py [--quick]   (about 1 minute; --quick: N up to 4)
"""

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (ROOT, os.path.join(HERE, "..", "lib"), os.path.join(ROOT, "research", "muzychka-case2-analytic", "lib")):
    sys.path.insert(0, p)
import case2                                                   # noqa: E402
import sublayers                                               # noqa: E402
import solid3d_sublayers                                       # noqa: E402
import surface_readout as sr                                   # noqa: E402
from pcbthermal import SolverOptions, simulate                 # noqa: E402

CELL = 0.5                                                     # plan cell in mm: sources and centroids lie on cell lines
REF_SUB = 8                                                    # sub-slabs of the reference (16 reads 0.02 K lower on the surface but peaks above 5 GB)
T_M, K, H = case2.T_MM * 1e-3, case2.K_PLATE, case2.H_PAPER
SRC = [(case2.rect(c), p) for c, p in zip(case2.CENTRES, case2.POWERS)]
Q = [p / (0.01 * 0.01) for p in case2.POWERS]                  # W/m2 of every source (10 x 10 mm)


def centroids(T):
    """!
    @brief Centroid value of every source from a layer map.
    @param T Array (ny, nx) in degC.
    @return list of float.
    """
    dx = case2.W_MM / T.shape[1]
    return [case2.corner_value(T, dx, *c) for c in case2.CENTRES]


def run_layered(model, n):
    """!
    @brief One layered model on the plate cut into n sub-layers.
    @param model Model key.
    @param n Sub-layers.
    @return dict with the centroids of the top node, of the column mean, the unknown count and the time, or None when the model refuses.
    """
    p = sublayers.stack_problem(n, case2.W_MM, case2.W_MM, case2.T_MM, K, H, sources=SRC)
    t0 = time.time()
    try:
        s = simulate(p, SolverOptions(models=(model,), cell_mm=CELL))
    except Exception as exc:                                   # reported, never hidden
        print(f"  {model} n={n}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None
    el = time.time() - t0
    T = np.asarray(s.results[model].T)
    tops = centroids(T[0])
    mean = np.mean([centroids(T[i]) for i in range(n)], axis=0)    # equal slabs: the plain mean is the column mean
    return {"top": tops, "mean": list(mean), "unknowns": int(T.size), "seconds": el}


def run_solid(n_cu):
    """!
    @brief The 3D solid with n_cu slabs through the copper.
    @param n_cu Slabs.
    @return dict as run_layered (top = first slab).
    """
    mod = solid3d_sublayers.load(n_cu)
    p = sublayers.stack_problem(1, case2.W_MM, case2.W_MM, case2.T_MM, K, H, sources=SRC)
    t0 = time.time()
    net = mod.Solid(p, CELL)
    theta, _ = net.solve()
    el = time.time() - t0
    b0 = net.board_slab[0]
    amb = p.board.ambient
    top = centroids(theta[b0] + amb)
    mean = np.mean([centroids(theta[b0 + i] + amb) for i in range(n_cu)], axis=0)
    return {"top": top, "mean": list(mean), "unknowns": int(net.n), "seconds": el}


def fmt(v):
    """!
    @brief Format a list of four temperatures.
    @param v List of floats.
    @return str.
    """
    return " ".join(f"{x:7.2f}" for x in v)


def main(quick=False):
    """!
    @brief Run the whole study and print the tables.
    @param quick True: sub-layer counts up to 4.
    """
    ns = (1, 2, 4) if quick else (1, 2, 4, 8)
    ref = case2.reference3d(CELL, REF_SUB)
    paper = np.array(case2.PAPER_CENTROID)
    surf, col = np.array(ref["surf_c"]), np.array(ref["lay_c"])
    print("Reference (independent 3D, 0.5 mm, %d sub-slabs)" % REF_SUB)
    print(f"  paper Table 4 centroid   {fmt(paper)}")
    print(f"  3D surface centroid      {fmt(surf)}   (minus paper {fmt(surf - paper)})")
    print(f"  3D column-mean centroid  {fmt(col)}   (surface minus mean {fmt(surf - col)}; bound q t/2k {fmt([q * T_M / 2 / K for q in Q])})")
    out = {"paper": list(paper), "surf": list(surf), "col": list(col), "layered": {}, "solid": {}}
    qq = np.array(Q)
    print("\nLayered models, plate cut into N sub-layers (cell 0.5 mm)")
    print("model     N  unknowns  time_s | top node (error to 3D surface)  | column mean (error to 3D mean) | surface = top node + q (t/N)/(2k) (error to 3D surface)")
    for m in ("fvm", "fdm", "analytic", "lumped"):
        for n in ns:
            r = run_layered(m, n)
            if r is None:
                continue
            top, mean = np.array(r["top"]), np.array(r["mean"])
            surf_b = top + qq * (T_M / n) / (2 * K)
            r["surface_B"] = list(surf_b)
            out["layered"][f"{m}|{n}"] = r
            print(f"{m:8s} {n:2d} {r['unknowns']:9d} {r['seconds']:6.1f} | {fmt(top - surf)} | {fmt(mean - col)} | {fmt(surf_b - surf)}")
            if n == 1:
                # Option A on the one-node plate: the node is the column mean; offsets from the face fluxes
                qb = sr.bottom_flux(mean - 25.0, H, T_M, K)
                d_top, _ = sr.offsets(T_M, K, qq, qb)
                bound = sr.column_bound(T_M, K, qq)
                r["surface_A_parabola"], r["surface_A_bound"] = list(mean + d_top), list(mean + bound)
                print(f"{'':8s}  A parabola t(2q-qb)/6k: {fmt(mean + d_top - surf)} | A bound q t/2k: {fmt(mean + bound - surf)}   (errors to the 3D surface)")
    print("\n3D solid, N_CU slabs through the copper (cell 0.5 mm; N=1 is the program's rule)")
    for n in ns:
        r = run_solid(n)
        top, mean = np.array(r["top"]), np.array(r["mean"])
        r["surface_C"] = list(top + qq * (T_M / n) / (2 * K))
        out["solid"][str(n)] = r
        print(f"solid3d  {n:2d} {r['unknowns']:9d} {r['seconds']:6.1f} | {fmt(top - surf)} | {fmt(mean - col)} | {fmt(np.array(r['surface_C']) - surf)}")
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    with open(os.path.join(HERE, "..", "out", "options.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main("--quick" in sys.argv)
