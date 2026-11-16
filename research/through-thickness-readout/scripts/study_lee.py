#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_lee.py
@brief Seri Lee's plate (100 x 100 x 1.3 mm, k 200, source 25 x 25 mm, h = 1 / (R0 A) with R0 = 1 K cm2... see below) read at the surface: the program on one node and on N sub-layers.

@details Published numbers (Lee, Song, Au and Moran 1995, as used by `research/effective-conductivity`): constriction resistance 0.66 (centre), 1.29 (edge midpoint) and 2.38 K/W (corner)
         for a 1 W source. The plate has the bottom film h = 1 / (R0 side^2) = 100 W/m2K (R0 = 1 K/W), top and sides adiabatic, so the mean wall rise is Q / (h A) = 1 K and
         Rc = (hottest surface of the source) - 1 K per watt. The independent solver gives 0.668 / 1.284 / 2.275 (3 sub-slabs, 0.5 mm; `study_lee_spreading.py`). Here the program (FVM, cell
         0.5 mm) reads the plate as one node and as N sub-layers (N = 1 and 4; N = 8 on the 0.5 mm cell peaks above 3 GB), and the surface read-outs of options A and B are formed. The film term of the half plate acts (`Board.face_film_h`).
         Usage: .venv/bin/python research/through-thickness-readout/scripts/study_lee.py [--with-reference]   (about 20 s; the reference run peaks at 3.8 GB, so it is off by default)
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (ROOT, os.path.join(HERE, "..", "lib"), os.path.join(ROOT, "tests", "helpers")):
    sys.path.insert(0, p)
import layered3d as L                                          # noqa: E402
import sublayers                                               # noqa: E402
import surface_readout as sr                                   # noqa: E402
from pcbthermal import SolverOptions, simulate                 # noqa: E402

SIDE, THICK, K, SRC, H = 100.0, 1.3, 200.0, 25.0, 100.0        # mm, mm, W/mK, mm, W/m2K
PAPER = {"centre": 0.66, "edge midpoint": 1.29, "corner": 2.38}
RECT = {"centre": (37.5, 37.5, 62.5, 62.5), "edge midpoint": (37.5, 0.0, 62.5, 25.0), "corner": (0.0, 0.0, 25.0, 25.0)}
CELL = 0.5
REF_STORED = {"centre": 0.668, "edge midpoint": 1.284, "corner": 2.275}   # printed by research/effective-conductivity/scripts/study_lee_spreading.py (README 4.4)


def program_rc(pos, n):
    """!
    @brief Rc of the program for one position: node read and the surface reads of options A and B.
    @param pos Position name.
    @param n Sub-layers.
    @return dict with the node Rc, the A (parabola) and B (top sub-layer plus half of it) Rc, K/W.
    """
    p = sublayers.stack_problem(n, SIDE, SIDE, THICK, K, H, sources=[(RECT[pos], 1.0)], ambient=0.0)
    r = simulate(p, SolverOptions(models=("fvm",), cell_mm=CELL)).results["fvm"]
    T = np.asarray(r.T)
    x = (np.arange(T.shape[2]) + 0.5) * CELL
    x0, y0, x1, y1 = RECT[pos]
    m = (x[None, :] > x0) & (x[None, :] < x1) & (x[:, None] > y0) & (x[:, None] < y1)
    q = 1.0 / ((x1 - x0) * (y1 - y0) * 1e-6)
    t, k = THICK * 1e-3, K
    node = float(T[0][m].max()) - 1.0
    col = T.mean(axis=0)                                       # equal slabs
    if n == 1:
        d_top, _ = sr.offsets(t, k, q, sr.bottom_flux(col, H, t, k))
        a_par = float((col + d_top)[m].max()) - 1.0
        a_bound = float(col[m].max() + sr.column_bound(t, k, q)) - 1.0
        return {"node": node, "A_parabola": a_par, "A_bound": a_bound}
    b = float((T[0] + (t / n) * q / (2 * k) * m)[m].max()) - 1.0
    return {"node": node, "B": b}


def reference(pos, dx=0.5e-3):
    """!
    @brief Rc of the independent solver (same definition as study_lee_spreading.py).
    @param pos Position name.
    @param dx Cell in m.
    @return float.
    """
    n = int(round(SIDE * 1e-3 / dx))
    r = L.solve(dx, n, n, [(THICK * 1e-3, K, 3)], tuple(v * 1e-3 for v in RECT[pos]), 1.0, 0.0, H)
    return r["max_source"] - r["mean_wall"]


def main(with_reference=False):
    """!
    @brief Print the table and write out/lee.json.
    @param with_reference True: run the independent 3D solver again (peak about 3.8 GB, over the 3 GB limit of this study); False: use the stored numbers of the effective-conductivity folder.
    """
    out = {}
    print("position        paper  3D(3 sub) | FVM node  A parabola  A bound | FVM N=4 node  B(N=4)")
    for pos in RECT:
        ref = reference(pos) if with_reference else REF_STORED[pos]
        a = program_rc(pos, 1)
        b4 = program_rc(pos, 4)
        out[pos] = {"paper": PAPER[pos], "ref": ref, "N1": a, "N4": b4}
        print(f"{pos:14s} {PAPER[pos]:6.2f} {ref:8.3f} | {a['node']:8.3f} {a['A_parabola']:10.3f} {a['A_bound']:8.3f} | {b4['node']:11.3f} {b4['B']:8.3f}")
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    with open(os.path.join(HERE, "..", "out", "lee.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main("--with-reference" in sys.argv)
