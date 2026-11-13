#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fdm_gap.py
@brief Item 2 (FDM): the FDM is below the FVM when the copper is cut by a gap across the board; cause and candidate (the harmonic mean of the nodal sheets, an option the FDM has).
@details Part A: boards of 50 x 24 mm, 4 layers, copper cut by a gap g on every layer, a 6 mm 2 W part at distance d from the gap edge; hottest rise of the FVM (the reference
         at the same cell and the converged one at 0.25 mm), of the FDM with the arithmetic and with the harmonic mean, at 1, 0.5 and 0.25 mm.
         Part B: the harmonic mean on the 17 boards of the regression harness (FDM, 2 and 1 mm): which records move and by how much, so that the frozen numbers touched are listed.
         Usage: python research/small-model-defects/scripts/study_fdm_gap.py [--part A|B]   (from the repository root; part A about 4 minutes, part B about 2).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "releases" / "regression-harness" / "lib"))

from pcbthermal import fdm                                                  # noqa: E402
from pcbthermal.api import SolverOptions, simulate                          # noqa: E402
from pcbthermal.model import Problem                                        # noqa: E402


def gap_board(gap, dist, W=50.0, H=24.0, side=6.0, layers=4):
    """!
    @brief Board whose copper is cut by a gap on every layer; a part on the left half, the right half empty.
    @param gap Gap width in mm (0 = no gap).
    @param dist Distance from the part's edge to the gap edge in mm.
    @param W Width in mm.
    @param H Height in mm.
    @param side Part side in mm.
    @param layers Copper layers.
    @return Problem.
    """
    p = Problem.new(W, H, layers=layers, h_top=10.0, h_bottom=15.0, h_side=10.0)
    x0, x1 = W / 2 - gap / 2, W / 2 + gap / 2
    for l in range(1, layers + 1):
        p.add_zone(l, rect=(0, 0, x0, H))
        p.add_zone(l, rect=(x1, 0, W, H))
    cx = x0 - dist - side / 2
    p.add_heater(1, 2.0, rect=(cx - side / 2, H / 2 - side / 2, cx + side / 2, H / 2 + side / 2))
    return p


def part_a():
    """!
    @brief Gap sweep.
    @return None.
    """
    print("== A. FDM against the FVM on a board cut by a gap (rise over the ambient in K; error of the FDM against the FVM at 0.25 mm, the converged value) ==")
    print("gap mm | dist mm | cell | FVM | FDM arithmetic | FDM harmonic | arithmetic vs FVM(0.25) % | harmonic vs FVM(0.25) %")
    for gap in (0.0, 3.0, 6.0):
        for dist in (1.0, 4.0):
            rows = []
            for cell in (1.0, 0.5, 0.25):
                p = gap_board(gap, dist)
                ref = float(simulate(p, SolverOptions(models=("fvm",), cell_mm=cell)).results["fvm"].t_max) - 25.0
                a = float(fdm.solve_steady(p, cell, "arithmetic").t_max) - 25.0
                h = float(fdm.solve_steady(p, cell, "harmonic").t_max) - 25.0
                rows.append((cell, ref, a, h))
            conv = rows[-1][1]
            for cell, ref, a, h in rows:
                print(f"{gap} | {dist} | {cell} | {ref:.2f} | {a:.2f} | {h:.2f} | {100 * (a - conv) / conv:+.1f} | {100 * (h - conv) / conv:+.1f}", flush=True)


def part_b():
    """!
    @brief Harness boards.
    @return None.
    """
    import regress_boards as rb
    print("\n== B. Harmonic mean on the regression-harness boards (FDM hottest temperature, K; only the records that move) ==")
    moved = 0
    total = 0
    for name in rb.board_names():
        for cell in (2.0, 1.0):
            try:
                a = float(fdm.solve_steady(rb.build(name), cell, "arithmetic").t_max)
                h = float(fdm.solve_steady(rb.build(name), cell, "harmonic").t_max)
            except Exception as exc:                                         # a board the FDM refuses (a metal block with faces, say)
                print(name, cell, "skipped:", str(exc)[:50])
                continue
            total += 1
            if abs(h - a) > 1e-9:
                moved += 1
                print(f"{name} | cell {cell} | arithmetic {a:.4f} | harmonic {h:.4f} | {h - a:+.4f} K")
    print(f"{moved} of {total} (board, cell) records move")


if __name__ == "__main__":
    part = sys.argv[sys.argv.index("--part") + 1] if "--part" in sys.argv else "AB"
    if "A" in part:
        part_a()
    if "B" in part:
        part_b()
