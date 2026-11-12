#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_order_reference.py
@brief Is the via well closer to a resolved 3D reference when it reads the sheet before or after the laminate rule? FVM (or FDM) against lib/ref3d_via.py.
@details For every case prints the 3D rise without and with the via (1/16 mm, 8 laminate sub-slabs per gap), its via effect E, and for each cell the FVM with the well sheet before (today)
         and after the rule: the error of the hottest rise in K and in per cent of the rise, and of E in per cent of E_ref. A fill below 1 is a stripe pattern in the 3D (0.5 mm pitch)
         and a smeared zone fill in the program, so those rows also carry the idealisation error, which is larger than the order effect; they are marked.
         Run: `.venv/bin/python research/via-well-sheet-order/scripts/study_order_reference.py [--dx 16] [--model fvm]`.
"""

import argparse
import itertools
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import cases                                                                # noqa: E402
import ref3d_via as r3                                                      # noqa: E402


def main():
    """!
    @brief Run the comparison and print a Markdown table.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--dx", type=int, default=16, help="3D cells per mm")
    ap.add_argument("--model", default="fvm")
    ap.add_argument("--cells", type=float, nargs="+", default=[0.5, 0.25])
    ap.add_argument("--layers", type=int, nargs="+", default=[2, 4])
    ap.add_argument("--fills", type=float, nargs="+", default=[1.0, 0.25])
    ap.add_argument("--h", type=float, nargs="+", default=[10.0, 200.0])
    ap.add_argument("--distances", type=float, nargs="+", default=[0.16, 0.5, 1.0, 3.0])
    ap.add_argument("--vias", nargs="+", default=["one"])
    args = ap.parse_args()
    dx = 1.0 / args.dx
    print("| layers | fill | h_side | via | d | T0 ref | E ref | cell | err T before (K / % rise) | err T after | err E before (% E) | err E after (% E) |")
    print("| --: | --: | --: | :-- | --: | --: | --: | --: | :-- | :-- | --: | --: |")
    for ly, fill, hs, v, d in itertools.product(args.layers, args.fills, args.h, args.vias, args.distances):
        t0 = r3.edge_board_reference(ly, fill, hs, d, v, dx_mm=dx, with_via=False)
        t1 = r3.edge_board_reference(ly, fill, hs, d, v, dx_mm=dx, with_via=True)
        e_ref = t0 - t1
        p0, p = cases.board(ly, fill, hs, d, v, with_via=False), cases.board(ly, fill, hs, d, v)
        for c in args.cells:
            p_t0 = cases.rise(p0, c, args.model)
            tb, ta = cases.rise(p, c, args.model, "before"), cases.rise(p, c, args.model, "after")
            eb, ea = p_t0 - tb, p_t0 - ta
            print(f"| {ly} | {fill:g} | {hs:g} | {v} | {d:g} | {t0:.3f} | {e_ref:.3f} | {c:g} | {tb - t1:+.3f} / {100 * (tb - t1) / t0:+.2f} | {ta - t1:+.3f} / {100 * (ta - t1) / t0:+.2f} | "
                  f"{100 * (eb - e_ref) / e_ref:+.2f} | {100 * (ea - e_ref) / e_ref:+.2f} |", flush=True)


if __name__ == "__main__":
    main()
