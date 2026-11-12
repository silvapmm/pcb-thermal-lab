#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_order_program.py
@brief How much the via effect and the hottest rise of the FVM and FDM move when the via well reads the sheet after the laminate rule instead of before it.
@details Sweeps layers (2, 4), copper fill (1, 0.2), edge film (10, 200 W/m2K), via distance from the edge (0.16, 0.5, 1, 3 mm), one via or a 2 x 2 block and the cell (1, 0.5, 0.25 mm).
         Prints one row per case: the rise without vias, the via effect E = T0 - T with today's order and with the sheet after the rule, the shift of T in K, in per cent of the rise
         and of E. Run from the repository root: `.venv/bin/python research/via-well-sheet-order/scripts/study_order_program.py [--model fvm|fdm] [--cells 1 0.5 0.25]`.
"""

import argparse
import itertools
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import cases                                                                # noqa: E402


def main():
    """!
    @brief Run the sweep and print a Markdown table.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="fvm")
    ap.add_argument("--cells", type=float, nargs="+", default=[1.0, 0.5, 0.25])
    ap.add_argument("--layers", type=int, nargs="+", default=[2, 4])
    ap.add_argument("--fills", type=float, nargs="+", default=[1.0, 0.2])
    ap.add_argument("--h", type=float, nargs="+", default=[10.0, 200.0])
    ap.add_argument("--distances", type=float, nargs="+", default=[0.16, 0.5, 1.0, 3.0])
    ap.add_argument("--vias", nargs="+", default=["one", "block"])
    args = ap.parse_args()
    print("| model | layers | fill | h_side | via | d (mm) | cell | T0 (K) | E before (K) | E after (K) | dT (K) | dT % rise | dT % E |")
    print("| :-- | --: | --: | --: | :-- | --: | --: | --: | --: | --: | --: | --: | --: |")
    for ly, fill, hs, v, d, c in itertools.product(args.layers, args.fills, args.h, args.vias, args.distances, args.cells):
        p0 = cases.board(ly, fill, hs, d, v, with_via=False)
        t0 = cases.rise(p0, c, args.model)
        p = cases.board(ly, fill, hs, d, v)
        tb = cases.rise(p, c, args.model, "before")
        ta = cases.rise(p, c, args.model, "after")
        eb, ea = t0 - tb, t0 - ta
        print(f"| {args.model} | {ly} | {fill:g} | {hs:g} | {v} | {d:g} | {c:g} | {t0:.3f} | {eb:.4f} | {ea:.4f} | {ta - tb:+.4f} | {100 * (ta - tb) / t0:+.3f} | {100 * (ta - tb) / eb:+.2f} |", flush=True)


if __name__ == "__main__":
    main()
