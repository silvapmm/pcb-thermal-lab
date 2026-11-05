#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_frozen_impact.py
@brief Which frozen Analytic records the per-layer edge would move: hottest temperature of the 17 boards of the regression harness at 2 mm, program against per-layer.

@details Uses the boards of tests/regression/regress_boards.py (read only) and the patched complete solve of lib/perlayer_local.py. A board with an outline, a metal
         block or no edge coefficient is reported as skipped (outline and blocks go through paths that the copy does not have: simulate() hands the Analytic the rectangle
         of the same area, and a block is a local correction that the copy supports but not in this study); for them the shift is 0 when the layers have the same
         slab / S, and is listed from that ratio.
         Run from the repository root: .venv/bin/python research/analytic-2-6/scripts/study_frozen_impact.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(ROOT))
sys.path.insert(0, os.path.join(ROOT, "lib"))
sys.path.insert(0, os.path.join(REPO, "tests", "regression"))
sys.path.insert(0, REPO)

import perlayer_local as PL            # noqa: E402
import regress_boards as RB            # noqa: E402
from pcbthermal import analytic, blocks   # noqa: E402


def main():
    """!
    @brief Print the shift of the hottest temperature of each board.
    @return None.
    """
    print(f"{'board':24s} {'layers':>6s} {'h_side':>7s} {'slab/S spread':>13s} {'program degC':>13s} {'per-layer degC':>15s} {'shift K':>8s} {'shift %rise':>11s}")
    for name in RB.board_names():
        p = RB.build(name, os.path.join(REPO, "examples"))
        b = p.board
        outline = getattr(b, "outline", None)
        has_outline = outline is not None and len(outline) > 0
        if has_outline or blocks.has_blocks(p) or not b.h_side or not p.heaters:
            print(f"{name:24s} {b.layers:6d} {str(b.h_side):>7s}   skipped ({'outline' if has_outline else 'block' if blocks.has_blocks(p) else 'no edge coefficient or no part'})")
            continue
        sh = analytic._effective_sheet(p, 2.0)
        rat = sh["slab"] / sh["S"]
        prog = analytic.solve_steady(p, 2.0).t_max
        pl = PL.solve(p, 2.0)["t_max"]
        rise = prog - b.ambient
        print(f"{name:24s} {b.layers:6d} {b.h_side:7.1f} {rat.max() / rat.min():13.2f} {prog:13.3f} {pl:15.3f} {pl - prog:+8.3f} {100 * (pl - prog) / rise:+11.2f}", flush=True)


if __name__ == "__main__":
    main()
