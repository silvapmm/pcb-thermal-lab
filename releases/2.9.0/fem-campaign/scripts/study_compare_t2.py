#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_compare_t2.py
@brief Row T2 of the FEM campaign (validation 57.2): square-wave power profiles in the FVM, FDM, FEM, Lumped and Analytic, peak, swing and the curve of the last window against a
       converged reference, for a slow and a fast wave on a plain plate and on the example board with the profile of the examples.
@details The time simulation of a model is `profiles.run_fvm`, `run_fdm`, `run_fem`, `lumped.run_profile` and `analytic.run_profile` with the regime forced to 'resolved' (so that the
         average-or-resolve decision does not hide the wave) and the program's default `SolverOptions().profile` (Crank-Nicolson with the Rannacher start since 2.9.0). The
         reference is the FEM of the same cell with 8 times the steps per period (`plan_run` wrapped, as `releases/2.9.0/fem-transient/scripts/check_unaligned_edges.py`): it
         removes the stepping error, not the model error, so the difference of a model to it is the model difference plus its own stepping error, printed beside the FEM's own
         stepping error. The read-out is the hottest column cell under the heater ('part peak'), the swing is its peak-to-peak over the last window; differences are in K and in
         percent of the swing of the reference (the curve: largest absolute difference over the window divided by the reference swing).
         Run from the repository root, ONE job at a time:
         `.venv/bin/python -u releases/2.9.0/fem-campaign/scripts/study_compare_t2.py [--cases plate_slow,plate_fast,profile_board] [--cell 2]`.
"""

import argparse
import dataclasses
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "regression"))
LABEL = {"fvm": "FVM", "fdm": "FDM", "lumped": "Lumped", "analytic": "Analytic", "fem": "FEM", "fem12": "FEM, 12 elements across a gap"}


def plate(period, duty):
    """!
    @brief The 60 x 40 mm two-layer plate with a 10 x 10 mm part of 10 W on a square wave and its decision forced to 'resolved'.
    @param period Period of the wave in s.
    @param duty Share of the period at full power, between 0 and 1.
    @return tuple (problem, decisions).
    """
    from pcbthermal import Problem, SquareWave, profiles
    p = Problem.new(60.0, 40.0, layers=2)
    p.add_full_copper()
    p.add_heater(1, 3.0, rect=(25.0, 15.0, 35.0, 25.0))
    p.heaters[0].set_profile(SquareWave(p_on=10.0, period=period, duty=duty))
    d = profiles.decide(p, profiles.step_response_fvm(p, 2.0), 0.001)
    return p, [dataclasses.replace(x, regime="resolved") for x in d]


def example_profile():
    """!
    @brief The example board (`example_board`, two parts) with the first part on a slow square wave (4 W, 20 s, 50 %) and the other on its constant power, the decision forced to 'resolved'.
    @details The wave of the shipped `profile_board` (100 Hz) needs 266 668 steps, above the program's own limit of 200 000 (`profiles.plan_run` refuses it), so it is not a case the
             program runs; this one is about 80 steps per model.
    @return tuple (problem, decisions).
    """
    import regress_boards as B
    from pcbthermal import SquareWave, profiles
    p = B.build("example_board")
    p.heaters[0].set_profile(SquareWave(p_on=4.0, period=20.0, duty=0.5))
    d = profiles.decide(p, profiles.step_response_fvm(p, 2.0), 0.001)
    return p, [dataclasses.replace(x, regime="resolved") if x.index == 0 else x for x in d]


def run(problem, decisions, model, cell, cycles, n_per=None):
    """!
    @brief One profile run; the steps per period may be forced (the reference).
    @param problem Problem.
    @param decisions Decisions with the regime forced to 'resolved'.
    @param model Model key.
    @param cell Cell size in mm.
    @param cycles Windows to run, count (the last one is read).
    @param n_per Steps per period to force, count (None: the program's rule).
    @return tuple (times in s of the last window, hottest column under the first part in degC, steps per period used, seconds).
    """
    from pcbthermal import SolverOptions, analytic, lumped, profiles
    base = SolverOptions().profile
    opts = dataclasses.replace(base, duration="cycles", cycles=cycles, max_steps=10 ** 7)
    orig = profiles.plan_run

    def plan(pr, de, op):
        """!
        @brief `plan_run` with the steps per period forced when asked.
        @param pr Problem.
        @param de Decisions.
        @param op ProfileOptions.
        @return dict as `plan_run`.
        """
        r = orig(pr, de, op)
        if n_per is None:
            return r
        return dict(r, n_per=n_per, dt=r["window"] / n_per, steps=op.cycles * n_per)

    profiles.plan_run = plan
    t0 = time.perf_counter()
    try:
        if model == "fvm":
            r = profiles.run_fvm(problem, decisions, opts, cell)
        elif model == "fdm":
            r = profiles.run_fdm(problem, decisions, opts, cell)
        elif model == "fem":
            r = profiles.run_fem(problem, decisions, opts, cell)
        elif model == "fem12":
            r = profiles.run_fem(problem, decisions, opts, cell, gap_elements=12)
        elif model == "lumped":
            r = lumped.run_profile(problem, decisions, opts, 10, lumped.cell_for(problem, cell))
        else:
            r = analytic.run_profile(problem, decisions, opts, min(max(cell, 0.5), 1.0), 300)
    finally:
        profiles.plan_run = orig
    return np.asarray(r.times), np.asarray(r.t_heaters[0]), int(r.steps // max(r.windows, 1)), time.perf_counter() - t0


def case(name, problem, decisions, cell, cycles, models):
    """!
    @brief Print the table of one case.
    @param name Case name.
    @param problem Problem.
    @param decisions Decisions.
    @param cell Cell size in mm.
    @param cycles Windows to run, count.
    @param models Model keys.
    @return None.
    """
    from pcbthermal import profiles
    w = decisions and problem.heaters[[d.index for d in decisions if d.regime == "resolved"][0]].profile
    print(f"\n### {name}: period {w.period:g} s, duty {w.duty:g}, {cycles} windows, cell {cell:g} mm; part peak = hottest column cell under the part, last window")
    tref, yref, nref, sref = run(problem, decisions, "fem", cell, cycles, n_per=8 * max(profiles.plan_run(problem, decisions, dataclasses.replace(__import__('pcbthermal').SolverOptions().profile, duration="cycles", cycles=cycles))["n_per"], 1))
    swing_ref = float(yref.max() - yref.min())
    print(f"reference: FEM, {nref} steps per period (8 times the rule), peak {yref.max():.4f} degC, swing {swing_ref:.4f} K, {sref:.1f} s")
    print("| model | steps per period | peak degC | (K vs ref) | swing K | (% of ref swing) | curve: largest difference, % of ref swing | run s |")
    print("| :-- | --: | --: | --: | --: | --: | --: | --: |")
    for m in models:
        try:
            t, y, n, s = run(problem, decisions, m, cell, cycles)
        except Exception as exc:
            print(f"| {LABEL[m]} | not run: {type(exc).__name__}: {str(exc)[:80]} | | | | | | |")
            continue
        # the reference (8 times the steps) is interpolated onto the model's own sample times of the window, so that the sampling of a coarse run is not counted as an error
        # (periodic: the window of a coarse run may start one step away from the reference's, so the phase inside the window is what is compared)
        win = float(w.period)
        order = np.argsort(tref % win)
        yi = np.interp(t % win, (tref % win)[order], yref[order], period=win)
        sw = float(y.max() - y.min())
        print(f"| {LABEL[m]} | {n} | {y.max():.4f} | {y.max() - yref.max():+.4f} | {sw:.4f} | {100 * (sw / swing_ref - 1):+.1f} | {100 * np.abs(y - yi).max() / swing_ref:.1f} | {s:.1f} |")


def main():
    """!
    @brief Command line of the study.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--cases", default="plate_slow,plate_fast,profile_board")
    ap.add_argument("--cell", type=float, default=2.0)
    a = ap.parse_args()
    import regress_harness as H
    H.use_program(ROOT)
    tree = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    print(f"tree {tree}, program {sys.modules['pcbthermal'].__version__}; default stepping of the program (Crank-Nicolson with the Rannacher start)")
    models = ("fem", "fem12", "fvm", "fdm", "lumped", "analytic")
    for c in a.cases.split(","):
        if c == "plate_slow":
            p, d = plate(100.0, 0.5)
            case("plate, slow wave", p, d, a.cell, 6, models)
        elif c == "plate_fast":
            p, d = plate(0.05, 0.3)
            case("plate, fast wave (20 Hz)", p, d, 1.0 if a.cell > 1.0 else a.cell, 12, models)
            print("independent reference of this wave (axisymmetric stack solver of research/fast-wave-oscillation README 1, quoted, not re-run): swing 6.3 K (the program's closed form of the decision 6.35 K against 6.37 K)")
        elif c == "profile_board":
            p, d = example_profile()
            case("example board, first part on a 20 s wave", p, d, a.cell, 4, ("fem", "fvm", "fdm", "lumped", "analytic"))


if __name__ == "__main__":
    main()
