#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fem_profile_limit.py
@brief The rule of the FEM profile note (`checks.fem_profile_limit`, 2 (first gap element)^2 / alpha) tested on two boards: the peak of a single power pulse in the FEM at
       6, 12 and 24 elements across a gap, for stretches from 0.15 to 3 times the limit, on the two-layer and on a four-layer 60 x 40 mm plate.
@details The pulse is a one-shot table (0 W for s, 10 W for s, 0 W for s; the program always steps a one-shot profile in time), the part 10 x 10 mm on full copper, cell
         2 mm, 400 time steps over the table (Crank-Nicolson with the Rannacher start, the program's default; the step count is forced, as in `study_compare_t2.py`, so that the
         time step is the same for the three meshes and the difference between them is the gap mesh). The read-out is the hottest column cell under the part, its largest rise
         above the ambient over the run ('pulse peak'); the reference is the same FEM with 24 elements across a gap (a convergence reference of the same model, not an
         independent one: the independent checks of the rule are the closed forms of validation 57.3 and the axisymmetric solver of validation 57.2).
         Run from the repository root, ONE job at a time (about 3 minutes):
         `.venv/bin/python -u releases/2.9.0/fem-campaign/scripts/study_fem_profile_limit.py`.
"""

import dataclasses
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))


def plate(layers, stretch):
    """!
    @brief The 60 x 40 mm plate with full copper and a 10 x 10 mm part carrying one pulse.
    @param layers Copper layers (2 or 4; 1.6 mm board, 35 um copper, the defaults of Problem.new).
    @param stretch Length of each stretch of the table in s (0 W, 10 W, 0 W).
    @return Problem.
    """
    from pcbthermal import Problem, TableProfile
    p = Problem.new(60.0, 40.0, layers=layers)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(25.0, 15.0, 35.0, 25.0), name="U")
    p.heaters[0].set_profile(TableProfile(times=[0.0, stretch, 2 * stretch, 3 * stretch], powers=[0.0, 10.0, 0.0], repeat=False))
    return p


def pulse_peak(problem, gap_elements, steps=400):
    """!
    @brief Largest rise of the hottest column cell under the part over the run of the FEM.
    @param problem Problem with the pulse.
    @param gap_elements Elements across every gap, count.
    @param steps Time steps over the table, count (forced).
    @return Rise in K.
    """
    from pcbthermal import SolverOptions, profiles
    opts = dataclasses.replace(SolverOptions().profile, max_steps=10 ** 7)
    decisions = profiles.decide(problem, profiles.step_response_fvm(problem, 2.0), opts.threshold_c)
    orig = profiles.plan_run

    def plan(pr, de, op):
        """!
        @brief `plan_run` with the step count forced.
        @param pr Problem.
        @param de Decisions.
        @param op ProfileOptions.
        @return dict as `plan_run`.
        """
        r = orig(pr, de, op)
        return dict(r, n_per=steps, dt=r["window"] / steps, steps=steps)

    profiles.plan_run = plan
    try:
        r = profiles.run_fem(problem, decisions, opts, 2.0, gap_elements=gap_elements)
    finally:
        profiles.plan_run = orig
    return float(np.max(np.asarray(r.t_heaters[0])) - problem.board.ambient)


def main():
    """!
    @brief Print the table of the study.
    @return None.
    """
    from pcbthermal import checks
    tree = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"tree {tree}, program {sys.modules['pcbthermal'].__version__}; one-shot pulse, cell 2 mm, 400 steps; pulse peak = largest rise of the hottest column cell under the part")
    print("| layers | stretch s | limit s (6 elements) | stretch / limit | 6 elements K (% vs 24) | 12 elements K (% vs 24) | 24 elements K |")
    print("| --: | --: | --: | --: | --: | --: | --: |")
    for layers, stretches in ((2, (0.05, 0.15, 0.35, 1.0)), (4, (0.01, 0.035, 0.1))):
        for s in stretches:
            p = plate(layers, s)
            limit = checks.fem_profile_limit(p)[0]
            v6, v12, v24 = (pulse_peak(p, g) for g in (6, 12, 24))
            print(f"| {layers} | {s:g} | {limit:.3f} | {s / limit:.2f} | {v6:.3f} ({100 * (v6 / v24 - 1):+.2f}) | {v12:.3f} ({100 * (v12 / v24 - 1):+.2f}) | {v24:.3f} |", flush=True)


if __name__ == "__main__":
    main()
