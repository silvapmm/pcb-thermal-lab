#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cell_and_outline.py
@brief Two side questions: do the Lumped and Analytic readings of an imported board change with the cell (0.5 against 1 mm), and how much of their gap on a uniform sheet is the equivalent rectangle of the outline?
@details (1) Lumped and Analytic rises on the imported RP2040 at cells 0.5 and 1 mm, for the parts given (the FVM reference at the same cell is printed beside them). (2) The uniform-sheet variant
         of the same parts with and without the board outline (the outline removed leaves the 52 x 51 mm box): FVM, Lumped and Analytic, and the ratios model / FVM. One solve at a time.
         Run: .venv/bin/python research/reduced-models-imported-passives/scripts/study_cell_and_outline.py rp2040 C3,C13,R5,C1,U1,U3,Y1
"""

import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import variants as V  # noqa: E402
from pcbthermal import api  # noqa: E402


def rise(problem, model, cell):
    """!
    @brief Rise of the hottest node of one model.
    @param problem Problem.
    @param model Model key.
    @param cell Cell in mm.
    @return float K.
    """
    r = api.simulate(problem, api.SolverOptions(models=(model,), cell_mm=cell))
    return r.results[model].t_max - problem.board.ambient


def main(argv):
    """!
    @brief Print the two tables.
    @param argv board, designators.
    @return int Exit code.
    """
    board, names = argv[1], argv[2].split(",")
    print("(1) imported copper, Lumped and Analytic against the FVM at the same cell")
    for cell in (0.5, 1.0):
        sx, prob = V.open_board(board, cell, powers=names)
        for n in names:
            q = V.only_heater(prob, n)
            f, l, a = (rise(q, m, cell) for m in ("fvm", "lumped", "analytic"))
            print("  cell %.1f %-4s FVM %.1f K  Lumped %.1f K (%+.0f %%)  Analytic %.1f K (%+.0f %%)" % (cell, n, f, l, 100 * (l / f - 1), a, 100 * (a / f - 1)), flush=True)
    print("(2) uniform sheet with and without the outline (cell 0.5)")
    sx, prob = V.open_board(board, 0.5, powers=names)
    for n in names:
        u = V.variant(V.only_heater(prob, n), "uniform")
        w = copy.deepcopy(u)
        w.board.outline = None
        out = []
        for lab, pr in (("outline", u), ("box", w)):
            f, l, a = (rise(pr, m, 0.5) for m in ("fvm", "lumped", "analytic"))
            out.append("%s: FVM %.1f Lumped %+.0f %% Analytic %+.0f %%" % (lab, f, 100 * (l / f - 1), 100 * (a / f - 1)))
        print("  %-4s %s" % (n, " | ".join(out)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
