#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cost.py
@brief Study 10: the run time of the zoned Lumped network against the program's, on boards with a core under the part, with large footprints, and inside the loops that rebuild the network (top-path split, power coefficient).
@details The earlier folders measured hundredths of a second on a board without a core (no zone work done). Here: (a) one steady solve (`lumped.solve_steady` through `api.simulate`) of a 30 mm board with a 5 x 5
         core under footprints of 10, 20, 30 and 60 mm (the last two are above the 700 cells where the integrals use blocks) at the cell of 0.5 mm; (b) the same part with a junction-to-case path
         and a heatsink (the top-path split of `api._solve_with_tc` re-solves the network, 3 to 7 times); (c) with a power temperature coefficient (the loop re-solves up to 80 times, normally 5 to 10);
         (d) the step response (`step_responses`) and a square-wave profile run. Time: the best of 3 runs (the machine is quiet; the first call of a context builds nothing that is cached). Memory is the peak of the
         process, printed by `/usr/bin/time -l` outside. Success criterion (fixed before running): the zoned solve is within 3 times the program's time in every case and under 1 s per steady solve; a loop case
         under 5 s.
Usage: python research/lumped-zones-adoption/scripts/study_cost.py   (from the repository root, with the program's .venv; a minute)
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import zref                                                                  # noqa: E402
import zoned_lumped as zl                                                    # noqa: E402
from pcbthermal import SolverOptions, simulate, lumped                       # noqa: E402


def best(fn, n=3):
    """!
    @brief Best wall time of n calls.
    @param fn Callable.
    @param n Repeats.
    @return float seconds.
    """
    out = []
    for _ in range(n):
        t0 = time.time()
        fn()
        out.append(time.time() - t0)
    return min(out)


def board(src, n=5, pitch=1.2, side=70.0):
    """!
    @brief A 70 mm board with an n x n array under a square source of the given side (mm).
    @param src Source side in mm.
    @param n Vias per side.
    @param pitch Pitch in mm.
    @param side Board side in mm.
    @return Problem.
    """
    zref.pc.load_libraries()
    return zref.refs.make_problem(dict(layers=4, n=n, pitch=pitch, dia=0.3, fill=385.0, side=side, src=src, power=3.0))


def main():
    """!
    @brief Run the cases and print the table.
    @return None.
    """
    print("| case | program s | zones s | ratio |\n| :-- | --: | --: | --: |")
    rows = []

    def row(label, make, run):
        p = make()
        tp = best(lambda: run(p))
        with zref.VARIANTS["Z_none"]():
            tz = best(lambda: run(p))
            nz = int(zl.LAST.get("nz", 1))
        rows.append((label, tp, tz, nz))
        print(f"| {label} (nz {nz}) | {tp:.3f} | {tz:.3f} | {tz / max(tp, 1e-9):.1f} |", flush=True)

    steady = lambda p: simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5))
    for src in (10.0, 20.0, 30.0, 60.0):
        row(f"steady, 5 x 5 core under {src:g} mm, 0.5 mm cell", lambda s=src: board(s), steady)
    row("steady, 20 x 20 at 1 mm under 30 mm, 0.5 mm cell", lambda: board(30.0, 20, 1.0), steady)

    def with_path():
        p = board(10.0)
        p.heaters[0].theta = 2.0
        p.heaters[0].theta_jc_top = 1.0
        p.heaters[0].theta_sa = 20.0
        return p
    row("steady with a top path (split loop), 10 mm", with_path, steady)

    def with_tc():
        p = board(10.0)
        p.heaters[0].power_tc = 0.004
        return p
    row("steady with a power coefficient, 10 mm", with_tc, steady)
    row("step response, 10 mm, 0.5 mm cell", lambda: board(10.0), lambda p: lumped.step_responses(p, 10, 0.5))
    print("written", zref.save_json("cost.json", rows))


if __name__ == "__main__":
    main()
