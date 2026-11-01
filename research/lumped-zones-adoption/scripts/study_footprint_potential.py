#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_footprint_potential.py
@brief Study 5: the decimation of the footprint potentials of the program (`lumped._footprint_potentials`, every step-th cell above 900 cells) against blocks of cells and against every cell.
@details The program's link from the footprint to ring 1 uses `phi_boundary - phi_mean` of the logarithmic potential of the uniformly heated footprint, and its peak uses `phi_mean - phi_min`.
         Above 900 footprint cells it keeps every step-th cell in row order. The earlier folder found the mean-to-boundary term 4 % short on a 20 mm square, 11 % on a 30 mm square and 5 % on a
         20 mm disc (read-only, against every cell) and the peak term within 0.4 %. This study measures it on squares of 6, 10, 14, 20 and 30 mm and discs of 10, 20 and 30 mm diameter at
         cells of 0.25 (where the footprint holds the most cells), 0.5 and 1.0 mm, in three ways: the program's stride, `zoned_lumped.footprint_potentials(mode="block")` and the exact value with
         every cell (`footprint_potentials_exact`, chunked), and for the discs also against the closed form (`phi_boundary - phi_mean = 1/4`, `phi_mean - phi_min = 1/4` for a disc). It also prints the
         change of the resistance of the footprint to ring 1 (`R_01` of a copper sheet, in units of `1/(2 pi S)`), which is what the answer of the program depends on, and the change of the
         maximum temperature of a 4-layer board with a 20 or 30 mm source in the Lumped model between the two decimations (`footprint="stride"` and `"block"`).
         Success criterion (fixed before running): the block decimation is within 1 % of the exact value for both terms on every case, and the stride is outside 1 % on at least the cases the earlier
         folder named (20 and 30 mm squares at 0.5 mm); the change of the maximum temperature of the board is reported, and a change above 0.5 K on a plausible board is a finding.
Usage: python research/lumped-zones-adoption/scripts/study_footprint_potential.py [--quick]   (from the repository root; the exact value at 0.25 mm of a 30 mm square has 14 400 cells: about 1.6 GB of distance blocks in chunks, minutes)
"""

import argparse
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import zref                                                                  # noqa: E402
import zoned_lumped as zl                                                    # noqa: E402
from pcbthermal import lumped                                                # noqa: E402
from pcbthermal.geometry import coverage_fraction                            # noqa: E402


def footprint(kind, size_mm, cell_mm):
    """!
    @brief Coverage array of a square or disc footprint at the centre of a board 1.5 times its size.
    @param kind "square" or "disc".
    @param size_mm Side or diameter in mm.
    @param cell_mm Cell in mm.
    @return Tuple (cov (ny, nx), dx in m, dy in m).
    """
    side = 1.5 * size_mm * 1e-3
    n = int(round(side * 1e3 / cell_mm))
    dx = side / n
    c, h = side / 2, size_mm * 1e-3 / 2
    if kind == "square":
        poly = np.array([(c - h, c - h), (c + h, c - h), (c + h, c + h), (c - h, c + h)])
    else:
        poly = zref.disc_polygon(c, c, h)
    return coverage_fraction(poly, n, n, dx, dx, 4), dx, dx


def main():
    """!
    @brief Print the potentials of the three ways and the effect on the board.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    cases = [("square", s) for s in (6, 10, 14, 20, 30)] + [("disc", s) for s in (10, 20, 30)]
    cells = (1.0, 0.5) if args.quick else (1.0, 0.5, 0.25)
    print("\n| footprint | cell mm | cells | link term: stride / block vs exact | peak term: stride / block vs exact | disc closed form (link, peak) |\n| :-- | --: | --: | --: | --: | :-- |")
    rows = []
    for kind, size in cases:
        for cell in cells:
            if kind == "square" and size == 30 and cell < 0.5 and args.quick:
                continue
            cov, dx, dy = footprint(kind, size, cell)
            n = int((cov > 0).sum())
            ex = zl.footprint_potentials_exact(cov, dx, dy)
            st = lumped._footprint_potentials(cov, dx, dy)
            bl = zl.footprint_potentials(cov, dx, dy, "block")
            link = lambda t: t[1] - t[0]                                     # noqa: E731  phi_boundary - phi_mean
            peak = lambda t: t[0] - t[2]                                     # noqa: E731  phi_mean - phi_min
            cf = f"{link(ex):.3f}, {peak(ex):.3f}" if kind == "disc" else ""
            print(f"| {kind} {size} | {cell:g} | {n} | {100 * (link(st) / link(ex) - 1):+.1f} % / {100 * (link(bl) / link(ex) - 1):+.1f} % | {100 * (peak(st) / peak(ex) - 1):+.1f} % / {100 * (peak(bl) / peak(ex) - 1):+.1f} % | {cf} (exact 0.250, 0.250) |", flush=True)
            rows.append({"kind": kind, "size": size, "cell": cell, "cells": n, "exact": ex, "stride": st, "block": bl})
    # the effect on a board: 4 layers, full copper, a large source, with and without the block decimation
    print("\nMaximum temperature rise of a 4-layer copper board with a square source (Lumped), K\n")
    print("| source mm | cell mm | stride (program) | block | change |\n| --: | --: | --: | --: | --: |")
    for src, cell_b in ((20.0, 1.0), (30.0, 1.0), (20.0, 0.5), (30.0, 0.5)):
        spec = dict(layers=4, n=0, pitch=1.0, dia=0.3, fill=0.0, side=2.0 * src, src=src, power=10.0)
        prob = zref.refs.make_problem(spec)
        prob.vias = []
        res = {}
        for mode in ("stride", "block"):
            with zl.patched(zones=False, footprint=mode):
                res[mode] = zref.pc.max_rise(prob, "lumped", cell_b)
        print(f"| {src:g} | {cell_b:g} | {res['stride']:.2f} | {res['block']:.2f} | {res['block'] - res['stride']:+.2f} |")
    print("\nwritten", zref.save_json("footprint_potential.json", rows))


if __name__ == "__main__":
    main()
