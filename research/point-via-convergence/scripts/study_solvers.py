#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_solvers.py
@brief Do the three linear solvers of the FVM (direct, CG, SOR) agree with the mean-potential via couplings? (INTEGRATION.md 1, "What must not change".)
@details The copper-filled 3 x 3 via-array board with the treatment `mw_disc@eta` installed on a copy of the program (`program_patch`), solved at 0.5 and 0.25 mm by the
         direct solver, the conjugate gradients and the red-black SOR; prints the maximum temperature of each, the differences to the direct one and the warnings.
         Written by the review: the SOR and CG figures of INTEGRATION.md were printed by no script of the folder.
         Run from the repository root: `.venv/bin/python research/point-via-convergence/scripts/study_solvers.py` (about two minutes: SOR runs its 200 000 sweeps).
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import program_cases as pc                                                  # noqa: E402
import program_patch as pp                                                  # noqa: E402
from pcbthermal import SolverOptions, simulate                              # noqa: E402


def main():
    """!
    @brief Run the three solvers and print the table.
    @return None.
    """
    pc.load_libraries()
    board = pc.array_board(385.0)
    print("| cell (mm) | direct T_max (degC) | CG - direct (K) | SOR - direct (K) | SOR warning |")
    print("| --: | --: | --: | --: | :-- |")
    for cell in (0.5, 0.25):
        out = {}
        with pp.patched("mw_disc", eta=math.exp(-0.25)):
            for solver in ("direct", "cg", "sor"):
                sim = simulate(board, SolverOptions(models=("fvm",), cell_mm=cell, linear_solver=solver))
                out[solver] = (sim.results["fvm"].t_max, [w for w in sim.warnings if "SOR" in w])
        print(f"| {cell} | {out['direct'][0]:.3f} | {out['cg'][0] - out['direct'][0]:.1e} | {out['sor'][0] - out['direct'][0]:+.2f} | "
              f"{'; '.join(out['sor'][1]) or 'none'} |", flush=True)


if __name__ == "__main__":
    main()
