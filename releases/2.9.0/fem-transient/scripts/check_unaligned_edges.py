#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_unaligned_edges.py
@brief Hypothesis H3 of DESIGN.md (review): the error of the swing of a 30 % square wave in the profile runner when the edge of the wave falls inside a step (`duty x n_per` not an
       integer, the program's `plan_run` rule gives n_per = 34 for duty 0.3, edge at 10.2 steps), against aligned steps and a converged Crank-Nicolson reference.
@details Light (seconds): a 60 x 40 mm two-layer plate with full copper, a 10 x 10 mm heater at the centre on a 20 Hz, 30 % wave of 10 W, the regime forced to 'resolved', 12 windows
         from the average state, a 4 mm cell, the FEM on the direct path (`--model fvm` for the FVM). `plan_run` is wrapped to set `n_per`; the swing is the peak-to-peak hottest
         column under the heater in the last window. Usage from the repository root:

         .venv/bin/python releases/2.9.0/fem-transient/scripts/check_unaligned_edges.py [--model fem|fvm]
"""

import dataclasses
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

from pcbthermal import Problem, SquareWave, profiles          # noqa: E402
from pcbthermal.profiles import ProfileOptions                # noqa: E402


def plate():
    """!
    @brief The plate of the check and its decision forced to 'resolved'.
    @return Tuple (problem, decisions).
    """
    p = Problem.new(60.0, 40.0, layers=2)
    p.add_full_copper()
    p.add_heater(1, 3.0, rect=(25.0, 15.0, 35.0, 25.0))
    p.heaters[0].set_profile(SquareWave(p_on=10.0, period=0.05, duty=0.3))
    d = profiles.decide(p, profiles.step_response_fvm(p, 2.0), 0.001)
    return p, [dataclasses.replace(d[0], regime="resolved")]


def swing(p, d, model, n_per, theta, cycles=12):
    """!
    @brief Swing and peak of the last window with `n_per` steps per period.
    @param p Problem.
    @param d Decisions.
    @param model 'fem' or 'fvm'.
    @param n_per Steps per period, count.
    @param theta 1.0 or 0.5.
    @param cycles Windows, count.
    @return Tuple (swing in K, peak in degC).
    """
    orig = profiles.plan_run

    def plan(problem, decisions, options):
        """!
        @brief `plan_run` with the steps per period of the check.
        @param problem Problem.
        @param decisions Decisions.
        @param options ProfileOptions.
        @return dict as `plan_run`.
        """
        r = orig(problem, decisions, options)
        return dict(r, n_per=n_per, dt=r["window"] / n_per, steps=options.cycles * n_per)
    profiles.plan_run = plan
    try:
        opts = ProfileOptions(duration="cycles", cycles=cycles, theta=theta, max_steps=10 ** 7)
        r = profiles.run_fem(p, d, opts, cell_mm=4.0, force_solver="direct") if model == "fem" else profiles.run_fvm(p, d, opts, 4.0)
    finally:
        profiles.plan_run = orig
    th = r.t_heaters[0]
    return float(th.max() - th.min()), float(th.max())


def main():
    """!
    @brief Print the swing error of aligned and unaligned steps for Euler and Crank-Nicolson.
    @return None.
    """
    model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "fem"
    p, d = plate()
    print(f"model {model}; program n_per {profiles.plan_run(p, d, ProfileOptions(duration='cycles', cycles=12))['n_per']}")
    ref_sw, ref_pk = swing(p, d, model, 1000, 0.5)
    print(f"reference (Crank-Nicolson, n_per 1000): swing {ref_sw:.5f} K, peak {ref_pk:.4f} degC")
    for theta in (1.0, 0.5):
        for n in (30, 33, 34, 35, 40, 50, 60):
            sw, pk = swing(p, d, model, n, theta)
            edge = 0.3 * n
            tag = "aligned" if abs(edge - round(edge)) < 1e-9 else f"edge at {edge:.1f} steps"
            print(f"theta {theta} n_per {n:3d} ({tag:17s}): swing {100 * (sw / ref_sw - 1):+6.2f} % of the reference, peak {pk - ref_pk:+.4f} K")


if __name__ == "__main__":
    main()
