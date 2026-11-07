#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_disc_tee.py
@brief The round board against the axisymmetric reduction and the small T with the neck edge moved over a cell, for every scheme after the exact cover (README 3).
@details disc: 40 mm round two-layer board, 3 mm round part, h_side 10, 200, 1000, 5000; the peak read at the centre of the hot cell and the heat leaving by the rim, against
         `layered_disc.solve` (rings times the same slabs: no square grid); cells 1, 0.5, 0.25 mm.
         tee: the 30 x 24 mm T board whose 2 W part crosses the neck edge; the neck edge at x = 10 + k/12 mm (on the grid lines of a cell of 1/12 mm); the reference is the program's
         FVM at 1/12 and 1/24 mm extrapolated to second order; error of the hottest point at 1 and 0.5 mm and its spread over the twelve positions; h_side 10 and 200.
Usage: .venv/bin/python research/cut-cell-links/scripts/study_disc_tee.py [disc|tee|all]   (from the repository root; about 6 minutes, below 1 GB)
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
sys.path.insert(0, LIB)
OUT = os.path.join(os.path.dirname(HERE), "out")

import cutlinks as cl         # noqa: E402
import boards as bd           # noqa: E402
import layered_disc           # noqa: E402

SCHEMES = cl.SCHEMES


def study_disc():
    """!
    @brief Peak and rim loss against the axisymmetric reduction.
    @return dict of the numbers.
    """
    d, a = 40.0, 3.0
    out = {}
    print("\n### disc: peak at the centre of the hot cell / heat through the rim, per cent against the axisymmetric reduction\n")
    print("| h_side | rise there (K) | cell (mm) | " + " | ".join(SCHEMES) + " |\n| --: | --: | --: | " + " | ".join("--:" for _ in SCHEMES) + " |")
    for hs in (10.0, 200.0, 1000.0, 5000.0):
        p = bd.disc_board(d, a, hs)
        amb = p.board.ambient
        sol = layered_disc.solve(p, d / 2000.0, a / 1000.0)
        for c in (1.0, 0.5, 0.25):
            ref = float(np.interp(c / 1000.0 * 0.5 * np.sqrt(2.0), sol["r"], sol["top"]))
            row, rec = [], []
            for s in SCHEMES:
                r = cl.solve(p, c, s)
                peak = 100.0 * (r.t_max - amb - ref) / ref
                rim = 100.0 * (r.power_out["sides"] / sol["heat_rim"] - 1.0)
                row.append(f"{peak:+.2f} / {rim:+.2f}")
                rec.append([peak, rim])
            out[f"{hs:g}|{c:g}"] = rec
            print(f"| {hs:g} | {ref:.3f} | {c:g} | " + " | ".join(row) + " |", flush=True)
    return out


def study_tee():
    """!
    @brief Small T: error of the hottest point over the neck positions.
    @return dict of the numbers.
    """
    out = {}
    for hs in (10.0, 200.0):
        print(f"\n### tee, h_side {hs:g}: error of the hottest point against the extrapolated 1/12-1/24 mm value (K)\n")
        print("| a (mm) | cell | " + " | ".join(SCHEMES) + " |\n| --: | --: | " + " | ".join("--:" for _ in SCHEMES) + " |")
        table = {1.0: [], 0.5: []}
        for k in range(12):
            a = 10.0 + k / 12.0
            t1 = cl.tmax(bd.small_t(a, hs), 1 / 12)
            t2 = cl.tmax(bd.small_t(a, hs), 1 / 24)
            ref = t2 + (t2 - t1) / 3.0
            for c in (1.0, 0.5):
                row = [cl.tmax(bd.small_t(a, hs), c, s) - ref for s in SCHEMES]
                table[c].append(row)
                out[f"{hs:g}|{a:.4f}|{c:g}"] = row
                if k % 3 == 0:
                    print(f"| {a:.3f} | {c:g} | " + " | ".join(f"{v:+.3f}" for v in row) + " |", flush=True)
        print(f"\nBias and spread over the 12 positions, h_side {hs:g} (K):\n")
        print("| cell | " + " | ".join(SCHEMES) + " |\n| --: | " + " | ".join("--:" for _ in SCHEMES) + " |")
        for c, rows in table.items():
            arr = np.array(rows)
            print(f"| {c:g} | " + " | ".join(f"{m:+.2f} / {sp:.2f}" for m, sp in zip(arr.mean(axis=0), arr.max(axis=0) - arr.min(axis=0))) + " |")
    return out


def main():
    """!
    @brief Run the studies named on the command line and save the numbers.
    @return None.
    """
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("disc", study_disc), ("tee", study_tee)):
        if which in (name, "all"):
            res = fn()
            with open(os.path.join(OUT, f"{name}.json"), "w") as f:
                json.dump(res, f)


if __name__ == "__main__":
    main()
