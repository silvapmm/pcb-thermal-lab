#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge_complications.py
@brief What changes when the board is not a stack of identical full-copper layers: unequal copper in the layers (the edge parameter differs per layer), vias, heatsinks, the example board, and the time response.

@details Three parts (--part A, B, C; default all):

         A. Unequal layers. 60 x 40 mm, 4 layers of 1.6 mm, a 10 mm, 2 W part at the centre or a corner, h_side 50 and 200; the copper fill of the layers (1, 2, 3, 4) is
            (1,1,1,1), (0.5,1,1,0.5), (0.3,1,1,1) and (0.2,0.2,1,1) (uniform fill, so the FVM resolves the same board). Treatments: faces (the program), robin (one common edge
            parameter), robin_res (common parameter plus the mismatch of each layer moved to the faces), against the FVM at 0.5 mm.
         B. Vias and heatsinks. 60 x 40 mm, 2 layers of 1.6 mm, a 3 x 3 via array (3.5 mm pitch, 0.3 mm) under the part, and a 20 x 20 mm heatsink (30 W/m2K extra on the bottom
            layer) under it, the part at the centre and in a corner, h_side 50 and 200; and the example board (100 x 80 mm, 4 layers, partial top copper, vias, heatsink) with the
            edge coefficient set to 50 and 200. The hottest rise and the via effect (rise without vias minus with) against the FVM at 0.5 mm.
         C. Time. The time to 63 % of the unit step of the first part (FVM 2 mm cell, the program's Analytic, and the copy with faces / none / Robin) and the largest
            difference of the Robin step response from the FVM step response, in percent of the steady resistance, on uniform boards.

         Run from the repository root: .venv/bin/python research/analytic-edge-spatial/scripts/study_edge_complications.py [--part A|B|C]  (about 10 minutes)
"""

import argparse
import copy
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import analytic_edge as ae   # noqa: E402
import cases                 # noqa: E402
from pcbthermal import Problem, SolverOptions, analytic   # noqa: E402
from pcbthermal.api import step_response                 # noqa: E402
from pcbthermal.examples import example_board            # noqa: E402

T0 = cases.T0


def part_a():
    """!
    @brief Unequal copper in the layers.
    @return None.
    """
    print("A. unequal layers, 60 x 40 mm, 4 x 1.6 mm, error of the hottest rise against the FVM at 0.5 mm (percent)")
    allv = []
    for fills in ((1, 1, 1, 1), (0.5, 1, 1, 0.5), (0.3, 1, 1, 1), (0.2, 0.2, 1, 1)):
        for hs in (50.0, 200.0):
            for pos in ("centre", "corner"):
                p, _ = cases.board(60, 40, 4, 1.6, hs, pos)
                for z, f in zip(p.zones, fills):
                    z.fill = float(f)
                f05 = cases.rise(p, "fvm", 0.5)
                out = {k: ae.solve(p, 1.0, edge=k)["t_max"] - T0 for k in ("faces", "robin", "robin_res")}
                sh = analytic._effective_sheet(p, 1.0)
                spread = (sh["slab"] / sh["S"]).max() / (sh["slab"] / sh["S"]).min()
                allv.append([out[k] / f05 - 1 for k in ("faces", "robin", "robin_res")])
                print(f"fill {fills} hs {hs:3.0f} {pos:6s} FVM {f05:7.2f} | beta ratio max/min {spread:4.2f} | faces {100 * allv[-1][0]:+6.1f} robin {100 * allv[-1][1]:+6.2f} robin_res {100 * allv[-1][2]:+6.2f}", flush=True)
    r = np.abs(np.array(allv))
    print(f"A summary ({len(r)} boards): max |err| faces {100 * r[:, 0].max():.1f} %, robin {100 * r[:, 1].max():.2f} %, robin_res {100 * r[:, 2].max():.2f} %\n")


def with_elements(p, pos, vias, heatsink):
    """!
    @brief Add a via array and/or a heatsink under the part of a `cases.board` board.
    @param p Problem.
    @param pos "centre" or "corner".
    @param vias True for the 3 x 3 array.
    @param heatsink True for the 20 x 20 mm heatsink on the bottom layer.
    @return Problem (same object).
    """
    cx, cy = (30.0, 20.0) if pos == "centre" else (5.0, 5.0)
    if vias:
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                p.add_via(cx + 3.5 * i, cy + 3.5 * j, diameter=0.3)
    if heatsink:
        p.add_heatsink(p.board.layers, 30.0, rect=(max(cx - 10, 0), max(cy - 10, 0), cx + 10, cy + 10))
    return p


def part_b():
    """!
    @brief Vias and heatsinks.
    @return None.
    """
    print("B. vias and heatsinks, 60 x 40 mm, 2 x 1.6 mm: error of the hottest rise and of the via effect against the FVM at 0.5 mm (percent)")
    rows = []
    for hs in (50.0, 200.0):
        for pos in ("centre", "corner"):
            for vias, sink in ((True, False), (False, True), (True, True)):
                p, _ = cases.board(60, 40, 2, 1.6, hs, pos)
                with_elements(p, pos, vias, sink)
                q, _ = cases.board(60, 40, 2, 1.6, hs, pos)                    # the same without the vias and heatsink
                f05, f05_0 = cases.rise(p, "fvm", 0.5), cases.rise(q, "fvm", 0.5)
                prog = analytic.solve_steady(p, 1.0).t_max - T0
                out = {k: ae.solve(p, 1.0, edge=k)["t_max"] - T0 for k in ("faces", "robin")}
                out0 = {k: ae.solve(q, 1.0, edge=k)["t_max"] - T0 for k in ("faces", "robin")}
                eff = f05_0 - f05
                row = [out[k] / f05 - 1 for k in ("faces", "robin")] + [(out0[k] - out[k]) / eff - 1 for k in ("faces", "robin")]
                rows.append(row)
                print(f"hs {hs:3.0f} {pos:6s} vias {int(vias)} sink {int(sink)} FVM {f05:6.2f} (effect {eff:5.2f} K) | program == copy: {abs(prog - out['faces']):.1e} | rise: faces "
                      f"{100 * row[0]:+6.1f} robin {100 * row[1]:+6.2f} | effect: faces {100 * row[2]:+6.1f} robin {100 * row[3]:+6.1f}", flush=True)
    r = np.abs(np.array(rows))
    print(f"B summary: max |rise err| faces {100 * r[:, 0].max():.1f} %, robin {100 * r[:, 1].max():.2f} %; max |effect err| faces {100 * r[:, 2].max():.1f} %, robin {100 * r[:, 3].max():.1f} %")
    print("example board (100 x 80 mm, 4 layers, partial top copper, 9 vias, heatsink), the hottest rise:")
    for hs in (10.0, 50.0, 200.0):
        p = example_board()
        p.board.h_side = hs
        f05 = cases.rise(p, "fvm", 0.5)
        out = {k: ae.solve(p, 1.0, edge=k)["t_max"] - T0 for k in ("none", "faces", "robin")}
        print(f"  h_side {hs:3.0f}: FVM {f05:6.2f} | none {100 * (out['none'] / f05 - 1):+6.1f} faces {100 * (out['faces'] / f05 - 1):+6.1f} robin {100 * (out['robin'] / f05 - 1):+6.2f} %", flush=True)
    print()


def time_to_63(p, model):
    """!
    @brief Time to 63.2 % of the steady resistance of the unit step of the first part, from the program's step_response.
    @param p Problem.
    @param model Model key.
    @return Tuple (t63 in s, times, z, rth).
    """
    import math
    sr = step_response(p, model, SolverOptions(models=(model,), cell_mm=2.0))
    t, z = np.asarray(sr.times, dtype=float), np.asarray(sr.z[0], dtype=float)
    rth = float(sr.rth[0])
    target = (1.0 - math.exp(-1.0)) * rth
    k = int(np.argmax(z >= target))
    f = (target - z[k - 1]) / (z[k] - z[k - 1])
    return math.exp(math.log(t[k - 1]) + f * (math.log(t[k]) - math.log(t[k - 1]))), t, z, rth


def part_c():
    """!
    @brief Time response.
    @return None.
    """
    print("C. time response, uniform boards 2 x 1.6 mm, part at the centre / corner, 2 mm cell for the FVM and the program")
    for (w, h) in ((30, 20), (60, 40), (100, 80)):
        for hs in (50.0, 200.0):
            for pos in ("centre", "corner"):
                p, _ = cases.board(w, h, 2, 1.6, hs, pos)
                t_fvm, tt, zz, r_fvm = time_to_63(p, "fvm")
                t_prog = time_to_63(p, "analytic")[0]
                out = {}
                for k in ("none", "faces", "robin"):
                    times, z, rth, t63 = ae.step_response(p, k)
                    out[k] = (t63, rth)
                    if k == "robin":
                        zi = np.interp(np.log(tt[tt > 0]), np.log(times), z)
                        dmax = np.abs(zi - zz[tt > 0]).max() / r_fvm
                p0 = copy.deepcopy(p)
                p0.board.h_side = None
                t_none = time_to_63(p0, "analytic")[0]
                print(f"{w}x{h} hs {hs:3.0f} {pos:6s}: t63 FVM {t_fvm:7.1f} s | program {t_prog:7.1f} ({100 * (t_prog / t_fvm - 1):+5.1f} %) copy faces {out['faces'][0]:7.1f} "
                      f"none {out['none'][0]:7.1f} ({100 * (t_none / t_fvm - 1):+5.1f} % before the transfer) robin {out['robin'][0]:7.1f} ({100 * (out['robin'][0] / t_fvm - 1):+5.1f} %) | "
                      f"Rth FVM {r_fvm:6.2f} faces {out['faces'][1]:6.2f} robin {out['robin'][1]:6.2f} | max |z_robin - z_FVM| {100 * dmax:4.1f} % of Rth", flush=True)


def main(argv=None):
    """!
    @brief Run the chosen parts.
    @param argv Arguments.
    @return int 0.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--part", choices=("A", "B", "C"), default=None)
    a = ap.parse_args(argv)
    for name, fn in (("A", part_a), ("B", part_b), ("C", part_c)):
        if a.part in (None, name):
            fn()
    return 0


if __name__ == "__main__":
    sys.exit(main())
