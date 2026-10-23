"""!
@file study_rect_convergence.py
@brief How the five models of the program converge with the cell size on the rectangle board, to separate the error of the grid from the difference of the physics.
@details Same board and heater as study_models_rect_board.py, with two copper layers (copper on the top one), using the program's own zones (the rectangles are disjoint, so the program's maximum rule is exact and the original program is used).
         Cells of 2, 1, 0.5, 0.25 and 0.1 mm (the 3D solid from 0.25 mm: memory). Reports the mean rise over the heater, the change from the finest run, and for the FVM the observed order of convergence from the three finest runs.
         A model that converges to a value is right about its own equations; the spread between the converged values of different models is the physics (README 4.37).
         Run: .venv/bin/python research/gerbers/scripts/study_rect_convergence.py (from the repository root; a few minutes).
"""

import _bootstrap  # noqa: F401  (puts research/gerbers/lib on the import path)

import math

from pcbthermal import SolverOptions, simulate
from pcbthermal.analysis import heater_stats

import rect_board as rb
import study_models_rect_board as sm

CELLS = (2.0, 1.0, 0.5, 0.25, 0.1)
MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")


def problem(shift):
    """!
    @brief The rectangle board as the program's own zones, two copper layers.
    @param shift Offset of the features (mm).
    @return Problem.
    """
    sm.LAYERS = 2
    p = sm.make_problem(shift)
    for r in rb.rects(shift):
        p.add_zone(1, rect=r, fill=1.0)
    return p


def main():
    """!
    @brief Print the convergence table for both shifts.
    @return None.
    """
    for shift in (0.0, 0.4):
        p = problem(shift)
        res = {}
        for m in MODELS:
            for c in CELLS:
                if m == "solid3d" and c < 0.25:
                    continue
                try:
                    sim = simulate(p, SolverOptions(models=(m,), cell_mm=c))
                    res[(m, c)] = heater_stats(sim.results[m], p)[0]["t_mean"] - p.board.ambient
                except Exception as e:                                         # reported, not hidden
                    print(f"  {m} {c}: failed ({type(e).__name__}: {str(e)[:60]})")
        print(f"\nshift {shift} mm, two layers: mean rise over the heater (K) by cell size")
        print(f"{'cell (mm)':>10s}" + "".join(f"{m:>12s}" for m in MODELS))
        for c in CELLS:
            print(f"{c:10.2f}" + "".join(f"{res[(m, c)]:12.2f}" if (m, c) in res else f"{'-':>12s}" for m in MODELS))
        fin = {m: res.get((m, 0.1), res.get((m, 0.25))) for m in MODELS}
        print(f"{'finest':>10s}" + "".join(f"{fin[m]:12.2f}" for m in MODELS))
        print("change of the 1 mm run from the finest (%): " + ", ".join(f"{m} {100 * (res[(m, 1.0)] / fin[m] - 1):+.1f}" for m in MODELS if (m, 1.0) in res))
        a, b_, c_ = res[("fvm", 0.5)], res[("fvm", 0.25)], res[("fvm", 0.1)]
        if abs(b_ - a) > 1e-9 and (c_ - b_) / (b_ - a) > 0:
            print(f"FVM from 0.5, 0.25, 0.1 mm: step ratio {(c_ - b_) / (b_ - a):.2f} (not an order estimate: the ratio of the cell sizes is not constant)")
        print("converged values against the FVM (%): " + ", ".join(f"{m} {100 * (fin[m] / fin['fvm'] - 1):+.1f}" for m in MODELS))


if __name__ == "__main__":
    main()
