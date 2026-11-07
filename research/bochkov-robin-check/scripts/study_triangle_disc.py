#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_triangle_disc.py
@brief Convergence of the symmetric Robin scheme of Bochkov and Gibou (2019) on the thesis' triangle test (section 1.5.2) and on a disc, against the program proposal (aperture + film).
@details Question: does the symmetric scheme reproduce the published orders (second order in the solution, first in the gradient) and how does the one-film-per-cell
         scheme of `research/cut-cell-links` compare? Error = L-infinity over the cell centres inside the domain, maximum over a grid of relative placements
         (nsh x nsh shifts of the grid, as the thesis does with 10 x 10), resolutions n = 17 ... 257 grid points per direction (the thesis: 16 ... 1024).
         Run from the repository root: `.venv/bin/python research/bochkov-robin-check/scripts/study_triangle_disc.py [--nsh 3] [--nmax 257]`.
         Output: `research/bochkov-robin-check/out/convergence.json` (git-ignored) and the table on the screen.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import robin2d as R  # noqa: E402

SCHEMES = ("nofilm", "bg_nokink", "bg", "film")


def sweep(dom, ns, nsh):
    """!
    @brief Maximum errors over the grid placements for every scheme and resolution.
    @param dom Domain.
    @param ns List of grid sizes.
    @param nsh Shifts per direction.
    @return Dict scheme -> list of (n, h, err_u, err_grad).
    """
    shifts = [(-0.5 + (a + 0.5) / nsh, -0.5 + (b + 0.5) / nsh) for a in range(nsh) for b in range(nsh)]
    out = {}
    for sch in SCHEMES:
        rows = []
        for n in ns:
            eu = eg = 0.0
            for s in shifts:
                r = R.solve(dom, n, shift=s, scheme=sch)
                a, b = R.errors(dom, r)
                eu, eg = max(eu, a), max(eg, b)
            rows.append((n, 2.0 / (n - 1), eu, eg))
        out[sch] = rows
    return out


def orders(rows, col):
    """!
    @brief Observed orders between consecutive resolutions and the least-squares slope.
    @param rows List of (n, h, eu, eg).
    @param col Column index (2 solution, 3 gradient).
    @return (list of pairwise orders, fitted slope).
    """
    h = np.array([r[1] for r in rows])
    e = np.array([r[col] for r in rows])
    pw = list(np.log(e[:-1] / e[1:]) / np.log(h[:-1] / h[1:]))
    sl = float(np.polyfit(np.log(h), np.log(e), 1)[0])
    return pw, sl


def main():
    """!
    @brief Run the sweep on the triangle and the disc and print the tables.
    @return None
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--nsh", type=int, default=3)
    ap.add_argument("--nmax", type=int, default=257)
    a = ap.parse_args()
    ns = [n for n in (17, 33, 65, 129, 257, 513) if n <= a.nmax]
    res = {}
    for name, dom in (("triangle", R.thesis_triangle()), ("disc", R.disc_domain())):
        sw = sweep(dom, ns, a.nsh)
        res[name] = sw
        print(f"\n== {name}: max over {a.nsh}x{a.nsh} placements, L-inf error of u / of grad u")
        print("n        " + "".join(f"{s:>26}" for s in SCHEMES))
        for k, n in enumerate(ns):
            print(f"{n:<9}" + "".join(f"{sw[s][k][2]:>13.2e}{sw[s][k][3]:>13.2e}" for s in SCHEMES))
        for col, lab in ((2, "u"), (3, "grad")):
            print(f"fitted order of {lab:<4}" + "".join(f"{orders(sw[s], col)[1]:>26.2f}" for s in SCHEMES))
            print(f"last pair order {lab:<4}" + "".join(f"{orders(sw[s], col)[0][-1]:>26.2f}" for s in SCHEMES))
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    with open(os.path.join(HERE, "..", "out", "convergence.json"), "w") as fh:
        json.dump(res, fh)


if __name__ == "__main__":
    main()
