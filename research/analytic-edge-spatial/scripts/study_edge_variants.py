#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge_variants.py
@brief How good are the four treatments of a convective board edge in the steady Analytic model (edge left out, moved to the faces, Robin eigenfunctions, edge cells as heatsinks) on uniform boards?

@details Uniform boards, full 35 um copper on every layer, a 10 mm square part of 2 W at the centre, in a corner or at the middle of the bottom edge, faces 10 W/m2K:
         30 x 20, 60 x 40 and 100 x 80 mm; (layers, thickness) = (2, 0.8), (2, 1.6), (2, 3.2), (4, 1.6), (6, 1.6); edge coefficient 10, 50 and 200 W/m2K: 135 boards.
         For each it prints the error of the hottest rise of "faces" (the program), "robin", "strips" at 1 mm (reviewer's prototype), "none" against the FVM of the program at
         0.5 mm (the layered model resolved) and, on the boards where it fits in 2 GB (up to 60 x 40 mm, and the 2-layer 100 x 80), against the independent 3D solver with the
         side film (what the real stack does, which the layered idealisation itself misses by up to 17 % at a thick board and a large edge coefficient), the energy balance of the
         Robin series and the run time of each. The last lines summarise per treatment.

         Run from the repository root: .venv/bin/python research/analytic-edge-spatial/scripts/study_edge_variants.py [--quick]  (about 15 minutes; --quick: the 30 x 20 and 60 x 40 boards)
"""

import argparse
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import analytic_edge as ae   # noqa: E402
import cases                 # noqa: E402


def main(argv=None):
    """!
    @brief Run the boards and print one line each and the summary.
    @param argv Arguments.
    @return int 0.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--quick", action="store_true", help="only the 30 x 20 and 60 x 40 mm boards")
    a = ap.parse_args(argv)
    sizes = ((30, 20), (60, 40)) if a.quick else ((30, 20), (60, 40), (100, 80))
    rows = []
    for w, h in sizes:
        for layers, t in ((2, 0.8), (2, 1.6), (2, 3.2), (4, 1.6), (6, 1.6)):
            for hs in (10.0, 50.0, 200.0):
                for pos in ("centre", "corner", "edge"):
                    p, xy = cases.board(w, h, layers, t, hs, pos)
                    f05 = cases.rise(p, "fvm", 0.5)
                    r3 = float("nan")
                    if w <= 60 or layers <= 2:
                        r3 = cases.ref3d(p, xy, 1.0)
                    res, tm = {}, {}
                    for name, kw in (("none", dict(edge="none")), ("faces", dict(edge="faces")), ("robin", dict(edge="robin")),
                                     ("strips", dict(edge="strips", strip_mm=1.0))):
                        t0 = time.time()
                        r = ae.solve(p, 1.0, **kw)
                        tm[name] = time.time() - t0
                        res[name] = r["t_max"] - cases.T0
                        if name == "robin":
                            bal = (r["p_faces"] + r["p_edge"]) / r["power"]
                    rows.append([res[k] / f05 - 1 for k in ("none", "faces", "robin", "strips")] + [f05 / r3 - 1, res["robin"] / r3 - 1, bal, tm["faces"], tm["robin"], tm["strips"],
                                                                                                        w, h, layers, t, hs, ("centre", "corner", "edge").index(pos)])
                    print(f"{w}x{h} L{layers} t{t} hs{hs:4.0f} {pos:6s} FVM {f05:7.2f} | none {100 * rows[-1][0]:+6.1f} faces {100 * rows[-1][1]:+6.1f} robin {100 * rows[-1][2]:+6.2f} "
                          f"strips {100 * rows[-1][3]:+6.2f} % of FVM | FVM/3D {100 * rows[-1][4]:+6.1f} robin/3D {100 * rows[-1][5]:+6.1f} % | balance {bal:.4f} | "
                          f"time faces {tm['faces']:.2f} robin {tm['robin']:.2f} strips {tm['strips']:.1f} s", flush=True)
    r = np.array(rows)
    print(f"\nboards {len(r)}")
    for i, name in enumerate(("none", "faces", "robin", "strips 1 mm")):
        e = np.abs(r[:, i])
        print(f"{name:12s} vs FVM 0.5 mm: mean |err| {100 * e.mean():5.2f} %, max {100 * e.max():5.2f} %, signed range {100 * r[:, i].min():+.1f} to {100 * r[:, i].max():+.1f} %")
    ok = ~np.isnan(r[:, 4])
    print(f"FVM 0.5 mm vs 3D ({ok.sum()} boards): mean |err| {100 * np.abs(r[ok, 4]).mean():.2f} %, signed range {100 * r[ok, 4].min():+.1f} to {100 * r[ok, 4].max():+.1f} %; "
          f"robin vs 3D: mean |err| {100 * np.abs(r[ok, 5]).mean():.2f} %, signed range {100 * r[ok, 5].min():+.1f} to {100 * r[ok, 5].max():+.1f} %")
    print(f"Robin energy balance (faces + edge)/P: {r[:, 6].min():.4f} to {r[:, 6].max():.4f}")
    print(f"time (s): faces mean {r[:, 7].mean():.2f}, robin mean {r[:, 8].mean():.2f}, strips mean {r[:, 9].mean():.1f}, max {r[:, 9].max():.1f}")
    for hs in (10.0, 50.0, 200.0):
        s = r[:, 14] == hs
        print(f"h_side {hs:4.0f}: faces |err| max {100 * np.abs(r[s, 1]).max():5.1f} %, robin max {100 * np.abs(r[s, 2]).max():5.2f} %, strips max {100 * np.abs(r[s, 3]).max():5.2f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
