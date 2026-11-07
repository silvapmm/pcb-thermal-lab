#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_scheme_sweep.py
@brief After the exact board cover, how much does the peak of the layered FVM still depend on where the outline cuts the grid, and which cut-cell scheme removes it? (README 2)
@details Boards: a 20 mm square with a 3 mm, 2 W part centred (on a cell centre) or 3.5 mm off centre towards the edge, and a 24 x 8 mm strip; two copper layers; h_side 10, 50,
         200 and 2000 W/m2K; cells 1 and 0.5 mm. Positions: the outline turned 0 to 45 degrees in steps of 5, and shifted along the diagonal by k/8 of a cell (k = 1..7);
         the part stays on a cell centre (`boards.edge_board`). The reference of every position is the same continuum problem in the frame of the board, an aligned
         rectangle solved by the program's FVM at 1/8, 1/16 and 1/32 mm and extrapolated (`boards.frame_reference`): no cut cell, independent of the schemes under test.
         The references are cached in `out/refs.json`. For each (case, h_side, cell, scheme): bias (mean error), spread (max - min) and worst |error| over the positions.
Usage: .venv/bin/python research/cut-cell-links/scripts/study_scheme_sweep.py [--quick]   (from the repository root; about 25 minutes, one process, below 1 GB)
"""

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
sys.path.insert(0, LIB)
OUT = os.path.join(os.path.dirname(HERE), "out")

import cutlinks as cl         # noqa: E402
import boards as bd           # noqa: E402

CASES = [("square", 0.0), ("square", 3.5), ("strip", 0.0)]
HS = (10.0, 50.0, 200.0, 2000.0)
CELLS = (1.0, 0.5)
ANGLES = list(range(0, 50, 5))


def positions(cell):
    """!
    @brief The positions of the outline: turns and diagonal shifts.
    @param cell Cell in mm.
    @return List of (label, dict(angle, sx, sy)).
    """
    pos = [(f"turn {a}", dict(angle=float(a))) for a in ANGLES]
    pos += [(f"shift {k}/8", dict(sx=k / 8 * cell, sy=k / 8 * cell)) for k in range(1, 8)]
    return pos


def get_ref(cache, key, kw):
    """!
    @brief Cached frame reference.
    @param cache dict (file content).
    @param key Cache key.
    @param kw Options of `frame_board`.
    @return float.
    """
    if key not in cache:
        cache[key] = bd.frame_reference(lambda p, c: cl.tmax(p, c), kw)[0]
    return cache[key]


def main():
    """!
    @brief Run the sweep and print one markdown table per cell; write `out/sweep.json`.
    @return None.
    """
    quick = "--quick" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    rp = os.path.join(OUT, "refs.json")
    cache = json.load(open(rp)) if os.path.exists(rp) else {}
    res = {}
    t0 = time.time()
    hlist = (HS[0], HS[2]) if quick else HS
    for shape, off in CASES:
        for hs in hlist:
            for cell in CELLS:
                errs = {s: [] for s in cl.SCHEMES}
                for label, pk in positions(cell):
                    kw = dict(h_side=hs, shape=shape, off=off, pc=cell / 2, **pk)
                    key = f"{shape}|{off}|{hs}|{label}|{cell}"
                    ref = get_ref(cache, key, kw)
                    for s in cl.SCHEMES:
                        errs[s].append(cl.tmax(bd.edge_board(**kw), cell, s) - ref)
                    json.dump(cache, open(rp, "w"))
                for s in cl.SCHEMES:
                    res[f"{shape}|{off}|{hs}|{cell}|{s}"] = errs[s]
                print(f"{shape} off {off} h {hs:g} cell {cell} ({time.time() - t0:.0f} s)", flush=True)
    json.dump(res, open(os.path.join(OUT, "sweep.json"), "w"))
    for cell in CELLS:
        print(f"\n### cell {cell} mm: bias / spread / worst |error| of the peak over the positions (K)\n")
        print("| case | h_side | " + " | ".join(cl.SCHEMES) + " |\n| :-- | --: | " + " | ".join("--:" for _ in cl.SCHEMES) + " |")
        for shape, off in CASES:
            for hs in hlist:
                row = []
                for s in cl.SCHEMES:
                    e = np.array(res[f"{shape}|{off}|{hs}|{cell}|{s}"])
                    row.append(f"{e.mean():+.2f} / {e.max() - e.min():.2f} / {np.abs(e).max():.2f}")
                print(f"| {shape} off {off:g} | {hs:g} | " + " | ".join(row) + " |")


if __name__ == "__main__":
    main()
