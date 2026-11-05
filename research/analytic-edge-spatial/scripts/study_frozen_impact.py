#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_frozen_impact.py
@brief How many of the frozen-number boards would move if the Analytic edge treatment were the Robin basis, and by how much against the FVM?

@details The 17 boards of the regression harness (research/release-regression-245/lib/regress_boards.py) at the 2 mm cell of the frozen numbers: for every board that has an edge
         coefficient, no metal block (the copy in lib does not have it) and no top path (the copy does not run the split) it prints the hottest rise of the program's Analytic (edge moved to the faces), of the copy
         with the Robin basis, the FVM and the percent change the Robin basis brings to the Analytic and to its error against the FVM. A board with an outline is solved on its equivalent rectangle, as the program does.

         Run from the repository root: .venv/bin/python research/analytic-edge-spatial/scripts/study_frozen_impact.py  (about 1 minute)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(REPO, "research", "release-regression-245", "lib"))

import analytic_edge as ae   # noqa: E402
import regress_boards        # noqa: E402
from pcbthermal import SolverOptions, analytic, blocks, simulate   # noqa: E402


def main():
    """!
    @brief Print the table.
    @return int 0.
    """
    print(f"{'board':24s} {'h_side':>6s} | {'FVM':>8s} {'program':>8s} {'Robin':>8s} | {'program err':>11s} {'Robin err':>9s} | Robin vs program")
    for name in regress_boards.board_names():
        p = regress_boards.build(name, os.path.join(REPO, "examples"))
        hs = p.board.h_side
        if blocks.has_blocks(p) or not hs or any(h.theta_sa > 0 for h in p.heaters):
            why = "block" if blocks.has_blocks(p) else ("top path" if hs else "no edge coefficient")
            print(f"{name:24s} {hs if hs else 0:6.0f} | not covered ({why})")
            continue
        t0 = p.board.ambient
        f = simulate(p, SolverOptions(cell_mm=2.0, models=("fvm",))).results["fvm"].t_max - t0
        q = p.equivalent_rectangle()[0]                 # the board with an outline is solved on the rectangle of the same area, as simulate() does
        a = analytic.solve_steady(q, cell_mm=1.0).t_max - t0
        r = ae.solve(q, 1.0, edge="robin")["t_max"] - t0
        print(f"{name:24s} {hs:6.0f} | {f:8.3f} {a:8.3f} {r:8.3f} | {100 * (a / f - 1):+10.2f}% {100 * (r / f - 1):+8.2f}% | {100 * (r / a - 1):+6.2f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
