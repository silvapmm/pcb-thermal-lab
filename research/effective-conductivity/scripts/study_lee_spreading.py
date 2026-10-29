#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_lee_spreading.py
@brief The spreading resistance of a small square source on a base plate (Seri Lee, Electronics Cooling, January 1998): centre, edge-midpoint and corner positions with the independent 3D solver.
@details The article gives, for an aluminium base of 100 x 100 x 1.3 mm (k = 200 W/mK), a 25 x 25 mm source and a catalogue resistance R0 = 1.0 K/W of the fin side, the maximum constriction resistance Rc
         and the total R0 + Rc: centre 0.66 (1.66 K/W), edge midpoint 1.29 (2.29) and corner 2.38 (3.38). Here the plate is solved in 3D (three slabs through the thickness, 0.5 mm cells), the fin side as a
         film coefficient h = 1/(R0 A) on the bottom face, the top face insulated outside the source and the sides insulated; Rc is the maximum source temperature minus the mean temperature of the
         film face, per watt. The thin-plate (2D, conductance k t) version of the program's plate model is solved too, for the same three positions.
         Run: .venv/bin/python research/effective-conductivity/scripts/study_lee_spreading.py (from the repository root; about 1 minute).
"""

import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
import layered3d as L                                          # noqa: E402

SIDE, THICK, K, R0, SRC = 0.1, 1.3e-3, 200.0, 1.0, 25e-3
PAPER = {"centre": 0.66, "edge midpoint": 1.29, "corner": 2.38}


def source_rect(position, dx):
    """!
    @brief The source rectangle for a position on the plate.
    @param position "centre", "edge midpoint" or "corner".
    @param dx Cell size in m (the rectangle edges are multiples of dx / 2).
    @return tuple (x0, y0, x1, y1) in m.
    """
    c = (SIDE - SRC) / 2
    return {"centre": (c, c, c + SRC, c + SRC), "edge midpoint": (c, 0.0, c + SRC, SRC), "corner": (0.0, 0.0, SRC, SRC)}[position]


def rc_3d(position, dx=0.5e-3):
    """!
    @brief Maximum constriction resistance by the 3D solver.
    @param position Position name.
    @param dx Cell size in m.
    @return float Rc in K/W.
    """
    n = int(round(SIDE / dx))
    h = 1.0 / (R0 * SIDE ** 2)
    res = L.solve(dx, n, n, [(THICK, K, 3)], source_rect(position, dx), 1.0, 0.0, h)
    return res["max_source"] - res["mean_wall"]


def rc_2d(position, n=200):
    """!
    @brief Maximum constriction resistance of the thin plate (lateral conductance k t, film on the whole face), the model of block_contact_study.py generalised to a position.
    @param position Position name.
    @param n Cells per side.
    @return float Rc in K/W.
    """
    d = SIDE / n
    h = 1.0 / (R0 * SIDE ** 2)
    g = K * THICK
    idx = np.arange(n * n).reshape(n, n)
    rows = np.concatenate([idx[:, :-1].ravel(), idx[:-1].ravel()])
    cols = np.concatenate([idx[:, 1:].ravel(), idx[1:].ravel()])
    off = sp.coo_matrix((np.full(rows.size, g), (rows, cols)), shape=(n * n, n * n))
    off = off + off.T
    Kmat = sp.diags(np.asarray(off.sum(axis=1)).ravel() + h * d * d) - off
    x0, y0, x1, y1 = source_rect(position, d)
    q = np.zeros((n, n))
    # round halves up (round() rounds them to even and can shrink the source by a cell); the 1e-9 absorbs the round-off of v / d (37.5 mm / 1.19 mm gave 31.4999...)
    i0, j0, i1, j1 = (int(np.floor(v / d + 0.5 + 1e-9)) for v in (x0, y0, x1, y1))
    q[j0:j1, i0:i1] = 1.0
    q /= q.sum()
    theta = spla.spsolve(Kmat.tocsc(), q.ravel()).reshape(n, n)
    return float(theta[q > 0].max() - (theta * h * d * d).sum())


def main():
    """!
    @brief Print the table and write out/lee_spreading.json for the figures.
    @return None.
    """
    out = {}
    print("| source position | paper Rc (K/W) | 3D solver | difference | thin plate (2D) | difference |")
    print("| :-- | --: | --: | --: | --: | --: |")
    for pos, ref in PAPER.items():
        a, b = rc_3d(pos), rc_2d(pos)
        out[pos] = {"paper": ref, "3d": a, "2d": b}
        print(f"| {pos} | {ref} | {a:.3f} | {100 * (a / ref - 1):+.1f} % | {b:.3f} | {100 * (b / ref - 1):+.1f} % |", flush=True)
    (HERE.parent / "out").mkdir(exist_ok=True)
    (HERE.parent / "out" / "lee_spreading.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
