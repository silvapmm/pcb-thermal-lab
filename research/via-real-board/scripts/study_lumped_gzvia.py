#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_lumped_gzvia.py
@brief The Lumped model after the via change: does keeping `gz_via` (the point conductance, as today) leave its results bit-identical, and where does the Lumped model stand against the FVM on boards with 100 or more vias?
@details Part 1 (identity): the Lumped steady state of the example board, the 3 x 3 array board and the own via field, computed on the program as it is and inside the patch with
         `edge_patch.lumped_sees_gz_via()`; the difference of T_max must be 0.0 (the rings see the same `gz`). Also the ring sums of `gz` are compared directly.
         Part 2 (without the fix): the same run inside the patch WITHOUT `lumped_sees_gz_via` (the vias disappear from the rings) to show why the array is needed: T_max rises by the
         via effect of the Lumped model.
         Part 3 (context): Lumped and Analytic against the FVM with the recommended treatment on the own via fields (the overstatement of A6 is not corrected by this work: the numbers
         are printed so that the validation rows can quote them).
         Run from the repository root: `.venv/bin/python research/via-real-board/scripts/study_lumped_gzvia.py`.
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import logging

import numpy as np

import edge_patch as ep
import program_cases as pc
import real_board as rbd
import runs
from pcbthermal import fvm, lumped
from pcbthermal.examples import example_board


def ring_sums_equal(problem, cell_mm=1.0):
    """!
    @brief Largest difference of `gz` and of `gz_via` between the program and the patched network (the Lumped model sums both) (the sums over any region are then equal).
    @param problem A Problem.
    @param cell_mm Cell in mm.
    @return float largest absolute difference of the arrays in W/K.
    """
    nx = max(int(round(problem.board.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(problem.board.height * 1000.0 / cell_mm)), 2)
    old = fvm.Network(problem, nx, ny, assemble=False)
    with ep.patched_edge(**runs.MW_BOARD):
        new = fvm.Network(problem, nx, ny, assemble=False)
    return float(max(np.abs(old.gz - new.gz).max(), np.abs(old.gz_via - new.gz_via).max()))


def main():
    """!
    @brief Print the three parts.
    @return None.
    """
    logging.disable(logging.WARNING)
    pc.load_libraries()
    holes, w, h = rbd.own_via_field(10)
    boards = (("example board", example_board()), ("3 x 3 array board", pc.array_board()), ("own 100 vias", rbd.problem_from_holes(holes, w, h, layers=4)))
    print("| board | Lumped T_max rise: program | patched with gz_via | difference | patched without gz_via | max |gz - (gz + gz_via)| (W/K) |")
    print("| :-- | --: | --: | --: | --: | --: |")
    for name, p in boards:
        t0 = lumped.solve_steady(p).t_max
        with ep.patched_edge(**runs.MW_BOARD):
            with ep.lumped_sees_gz_via():
                t1 = lumped.solve_steady(p).t_max
            t2 = lumped.solve_steady(p).t_max
        print(f"| {name} | {t0:.4f} | {t1:.4f} | {t1 - t0:+.2e} | {t2:.4f} | {ring_sums_equal(p):.1e} |", flush=True)
    print("\n| board | cell (mm) | FVM program | FVM recommended | Lumped | Analytic | Lumped vs FVM rec. (%) | Analytic vs FVM rec. (%) |")
    print("| :-- | --: | --: | --: | --: | --: | --: | --: |")
    for n in (10, 30):
        holes, w, h = rbd.own_via_field(n)
        p = rbd.problem_from_holes(holes, w, h, layers=4)
        for c in (1.0, 0.5):
            f0, f1 = runs.rise(p, "fvm", c), runs.rise(p, "fvm", c, runs.MW_BOARD)
            lu, an = runs.rise(p, "lumped", c, runs.MW_BOARD), runs.rise(p, "analytic", c)
            print(f"| own {n * n} | {c:g} | {f0:.2f} | {f1:.2f} | {lu:.2f} | {an:.2f} | {100 * (lu / f1 - 1):+.1f} | {100 * (an / f1 - 1):+.1f} |", flush=True)


if __name__ == "__main__":
    main()
