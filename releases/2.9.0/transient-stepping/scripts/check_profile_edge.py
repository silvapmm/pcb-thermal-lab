#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file check_profile_edge.py
@brief Review check of `fix/transient-default-stepping`: the time-step error of the resolved power-profile run (`profiles.run_fvm`, its own constant step, NOT changed by the
       branch) against the same run with the step divided by 32 and 64, Richardson-extrapolated.
@details `examples/profile_board.pcbt.json` with U2 (6 W, 20 s, duty 0.25) resolved and U1 held at its average power (its 100 Hz wave would be 'average + ripple', whose added wave
         is sampled per step and would hide the stepping error). FVM 2 mm, the decision of `profiles.decide` with the 1 K threshold. Two starts: the steady state of the average power
         until the cycle repeats (the default), and the ambient for four cycles. Prints the peak, the minimum and the swing of the last window, and the error of the first samples
         after the rising and the falling edge, for implicit Euler (the default, `ProfileOptions.theta` = 1) and Crank-Nicolson without a start (0.5).
         Run from the repository root: `.venv/bin/python releases/2.9.0/transient-stepping/scripts/check_profile_edge.py` (about 1 minute).
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
from pcbthermal import profiles  # noqa: E402
from pcbthermal.model import load_problem  # noqa: E402

## Cell of the runs in mm
CELL = 2.0


def run(problem, decisions, theta, div, initial, duration):
    """!
    @brief One resolved run with the step of the plan divided by `div`.
    @param problem pcbthermal.Problem.
    @param decisions Decisions of profiles.decide.
    @param theta 1.0 implicit Euler or 0.5 Crank-Nicolson.
    @param div Divisor of the step, count.
    @param initial "average" or "temperature" (the ambient).
    @param duration "stable" or "cycles" (four).
    @return profiles.ProfileResult.
    """
    original = profiles.plan_run

    def plan(*args, **kwargs):
        """!
        @brief The plan of the program with the step divided.
        @param args Positional arguments of profiles.plan_run.
        @param kwargs Keyword arguments of profiles.plan_run.
        @return dict as profiles.plan_run.
        """
        r = dict(original(*args, **kwargs))
        if r["n_per"]:
            r["n_per"], r["dt"], r["steps"] = r["n_per"] * div, r["dt"] / div, r["steps"] * div
        return r

    profiles.plan_run = plan
    try:
        opts = profiles.ProfileOptions(theta=theta, initial=initial, duration=duration, cycles=4, max_steps=10 ** 7, frames=20)
        return profiles.run_fvm(problem, decisions, opts, cell_mm=CELL)
    finally:
        profiles.plan_run = original


def main():
    """!
    @brief Run the check.
    @return None.
    """
    p = load_problem(os.path.join(ROOT, "examples", "profile_board.pcbt.json"))
    p.heaters[0].profile = None                             # U1 at its average power (see @details)
    dec = profiles.decide(p, profiles.step_response_fvm(p, CELL), 1.0)
    print("decisions:", [(p.heaters[d.index].name, d.regime) for d in dec])
    amb = p.board.ambient
    for initial, duration in (("average", "stable"), ("temperature", "cycles")):
        r32, r64 = run(p, dec, 1.0, 32, initial, duration), run(p, dec, 1.0, 64, initial, duration)
        ref = 2.0 * r64.t_max[63::64] - r32.t_max[31::32]
        print(f"-- start {initial}, {duration}: {r64.windows} windows; reference peak {ref.max():.3f} degC, minimum {ref.min():.3f} degC, swing {ref.max() - ref.min():.3f} K")
        for theta in (1.0, 0.5):
            r = run(p, dec, theta, 1, initial, duration)
            assert r.windows == r64.windows
            err = r.t_max - ref
            wave = p.heaters[1].profile                       # U2 switches on at the start of every window and off after duty x period
            on, off = -1, int(round(wave.duty * wave.period / r.dt)) - 1
            print(f"   theta {theta}: peak {100 * (r.t_max.max() - ref.max()) / (ref.max() - amb):+.3f} % of the rise, minimum {r.t_max.min() - ref.min():+.4f} K, "
                  f"swing {r.t_max.max() - r.t_max.min():.3f} K; after the rising edge {', '.join(f'{e:+.2f}' for e in err[on + 1:on + 5])} K; "
                  f"after the falling edge {', '.join(f'{e:+.2f}' for e in err[off + 1:off + 3])} K (step {r.dt:.3g} s)")


if __name__ == "__main__":
    main()
