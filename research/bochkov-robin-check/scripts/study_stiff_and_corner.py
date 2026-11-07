#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_stiff_and_corner.py
@brief Two questions the thesis leaves open for our use: (1) the stiff Robin coefficient (the denominator mu - alpha d of eq. 1.14 and the floor of the program proposal), (2) where the error sits at the corners of the triangle.
@details (1) A disc with alpha = s (2 + sin(x + y)), s from 1 to 1e4, coarse grids; schemes `bg` (no floor, eq. 1.14), `film` (denominator floored at 0.25 mu) and `nofilm`; the error
         is the L-infinity error over the cell centres inside the domain, max over 3 x 3 placements; also how many cells have a denominator below zero or below the floor.
         (2) The triangle of the thesis: the error inside a window of 3 cells around the three vertices against the rest of the domain, for `bg`, `bg_nokink`, `film`, `nofilm`.
         Run from the repository root: `.venv/bin/python research/bochkov-robin-check/scripts/study_stiff_and_corner.py`.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import robin2d as R  # noqa: E402


def shifts(nsh):
    """!
    @brief Grid placements.
    @param nsh Shifts per direction.
    @return List of (sx, sy).
    """
    return [(-0.5 + (a + 0.5) / nsh, -0.5 + (b + 0.5) / nsh) for a in range(nsh) for b in range(nsh)]


def stiff():
    """!
    @brief Disc with a stiff Robin coefficient: errors of the schemes and the counts of bad denominators.
    @return None
    """
    print("\n== 1. stiff Robin coefficient on the disc (alpha = s (2 + sin(x + y)), mu = 1), L-inf error, 3 x 3 placements")
    cfgs = [("nofilm", dict(scheme="nofilm")), ("bg(1.14)", dict(scheme="bg")), ("film.25", dict(scheme="film", floor=0.25)),
            ("film.5", dict(scheme="film", floor=0.5)), ("film.rat", dict(scheme="film", floor=-9.0, rational=True))]
    print(f"{'s':>7}{'n':>5}{'h a_max':>9}" + "".join(f"{c[0]:>11}" for c in cfgs) + f"{'neg.den':>9}{'hits':>6}")
    for s in (1.0, 10.0, 100.0, 1e3, 1e4):
        dom = R.disc_domain(s)
        for n in (17, 33, 65):
            h = 2.0 / (n - 1)
            errs = []
            neg = hits = 0
            for name, kw in cfgs:
                e = 0.0
                for sh in shifts(3):
                    r = R.solve(dom, n, shift=sh, **kw)
                    e = max(e, R.errors(dom, r)[0])
                    if name == "bg(1.14)":
                        neg = max(neg, r["stats"]["negative_denominator"])
                    if name == "film.25":
                        hits = max(hits, r["stats"]["floor_hits"])
                errs.append(e)
            print(f"{s:>7g}{n:>5}{h * 3 * s:>9.2f}" + "".join(f"{e:>11.2e}" for e in errs) + f"{neg:>9}{hits:>6}")


def corners():
    """!
    @brief Error near the vertices of the triangle against the rest.
    @return None
    """
    print("\n== 2. triangle: L-inf error of u within 3 cells of a vertex / elsewhere (max over 3 x 3 placements)")
    dom = R.thesis_triangle()
    print(f"{'n':>5}" + "".join(f"{k:>26}" for k in ("nofilm", "bg_nokink", "bg", "film")))
    for n in (33, 65, 129, 257):
        cells = {}
        for sch in ("nofilm", "bg_nokink", "bg", "film"):
            ec = eo = 0.0
            for sh in shifts(3):
                r = R.solve(dom, n, shift=sh, scheme=sch)
                X, Y, h = r["X"], r["Y"], r["h"]
                e = np.abs(r["u"] - dom.u(X, Y))
                ins = dom.inside(X, Y) & r["active"]
                near = np.zeros_like(ins)
                for v in dom.v:
                    near |= np.hypot(X - v[0], Y - v[1]) < 3.5 * h
                ec = max(ec, np.where(ins & near, e, 0).max())
                eo = max(eo, np.where(ins & ~near, e, 0).max())
            cells[sch] = (ec, eo)
        print(f"{n:>5}" + "".join(f"{cells[k][0]:>13.2e}{cells[k][1]:>13.2e}" for k in cells))


if __name__ == "__main__":
    stiff()
    corners()
