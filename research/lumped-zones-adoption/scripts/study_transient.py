#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_transient.py
@brief Study 2: the step response of the hottest point of a part with a via core under it, in the zoned Lumped network (capacities of the zones as sums of cells), the program's Lumped network and the FVM.
@details The zoned network has two footprint nodes per layer whose capacities are the sums of the capacities of their cells (`zoned_lumped.heater_network` returns `C` per node). Question:
         does that reproduce the time behaviour of the FVM as well as the steady state, in particular the time to reach 63 % of the steady rise, the response at 10 ms, 0.1 s, 1 s and 10 s, and
         the steady value? Boards (`refs.make_problem` specs): 5 x 5 vias at 1.2 mm in a 10 mm source (core covers about half of the footprint), 3 x 3 at 3.0 mm in a 12 mm source (sparse core),
         and 5 x 5 at 1.2 mm in a 14 x 7 mm source (elongated), all copper-filled. Models: `lumped.step_responses` (the program, 2.4.5), `zoned_lumped.step_responses_zoned` in the options `Z_none` and
         `Z_cap`, and `fvm.step_responses` at 0.5 mm (the reference of the time behaviour; it is the layered model with the mean-potential via).
         Success criterion (fixed before running): at every time the zoned response is within 10 % of the FVM response or closer to it than the program's, and the 63 % time within 20 %.
         Not verified: a profile (square wave) run, which also needs the source vector of the adapter (INTEGRATION.md 4); the transient of a block under the part.
Usage: python research/lumped-zones-adoption/scripts/study_transient.py   (from the repository root; a few minutes)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import zref                                                                  # noqa: E402
import zoned_lumped as zl                                                    # noqa: E402
from pcbthermal import fvm, lumped                                           # noqa: E402

BOARDS = [("5x5 @ 1.2 in 10 mm", dict(n=5, pitch=1.2, src=10.0, fill=385.0)),
          ("3x3 @ 3.0 in 12 mm", dict(n=3, pitch=3.0, src=12.0, fill=385.0)),
          ("5x5 @ 1.2 in 14 x 7 mm", dict(n=5, pitch=1.2, src=10.0, src_wh=(14.0, 7.0), fill=385.0))]
TIMES = (0.01, 0.1, 1.0, 10.0)


def sample(times, z, t):
    """!
    @brief Value of a step response at a time by interpolation in log time.
    @param times Array of times in s.
    @param z Response of one heater (degC/W).
    @param t Time in s.
    @return float.
    """
    return float(np.interp(np.log(t), np.log(times), z))


def t63(times, z, rth):
    """!
    @brief Time at which the response reaches 63.2 % of the steady value.
    @param times Array of times in s.
    @param z Response (degC/W).
    @param rth Steady value (degC/W).
    @return float Time in s (nan if never reached within the run).
    """
    above = np.nonzero(np.asarray(z) >= 0.632 * rth)[0]
    return float(times[above[0]]) if len(above) else float("nan")


def main():
    """!
    @brief Compare the step responses on the boards and print the table.
    @return None.
    """
    import program_cases as pc
    pc.load_libraries()
    for label, spec in BOARDS:
        p = zref.refs.make_problem(spec)
        t_f, z_f, r_f = fvm.step_responses(p, cell_mm=0.5)
        t_p, z_p, r_p = lumped.step_responses(p, cell_mm=0.5)
        out = {"FVM": (t_f, z_f[0], r_f[0]), "P245": (t_p, z_p[0], r_p[0])}
        for name in ("Z_none", "Z_cap"):
            with zref.VARIANTS[name]():
                t_z, z_z, r_z = zl.step_responses_zoned(p, cell_mm=0.5)
            out[name] = (t_z, z_z[0], r_z[0])
        print(f"\n{label}: steady rise K/W and response (K/W) at the times; error against the FVM in percent\n")
        print("| model | steady | " + " | ".join(f"{t:g} s" for t in TIMES) + " | t63 s |\n| :-- | --: |" + " --: |" * (len(TIMES) + 1))
        ref = out["FVM"]
        for name, (t, z, r) in out.items():
            cells = []
            for tt in TIMES:
                v, v_ref = sample(t, z, tt), sample(ref[0], ref[1], tt)
                cells.append(f"{v:.3f} ({100 * (v / v_ref - 1):+.1f}%)" if name != "FVM" else f"{v:.3f}")
            steady = f"{r:.3f} ({100 * (r / ref[2] - 1):+.1f}%)" if name != "FVM" else f"{r:.3f}"
            print(f"| {name} | {steady} | " + " | ".join(cells) + f" | {t63(t, z, r):.3g} |")


if __name__ == "__main__":
    main()
