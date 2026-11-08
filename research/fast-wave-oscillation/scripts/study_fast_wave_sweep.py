#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fast_wave_sweep.py
@brief Question 1 and 2: how much does the program understate the oscillation of a fast square wave over full copper, and how often is the average-or-resolve decision wrong?

@details For layers 1, 2, 4, a part of 2, 5 and 10 mm, h 10 and 30 W/m2K, frequency 0.1 Hz to 10 kHz and duty 10 to 90 %, the peak-to-peak rise per watt of
on-power of the part is computed (a) by the independent axisymmetric modal reference (lib/axisym_stack.py, copper and laminate resolved through the thickness) and
(b) by the program (profiles.step_response_fvm and profiles.wave_response, the numbers the decision uses). Writes out/sweep.json. Run from the repository root:
`QT_QPA_PLATFORM=offscreen .venv/bin/python research/fast-wave-oscillation/scripts/study_fast_wave_sweep.py`.
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, ROOT)

import numpy as np                                                   # noqa: E402

import axisym_stack as A                                             # noqa: E402
from pcbthermal import profiles                                      # noqa: E402
from pcbthermal.model import Problem, SquareWave                     # noqa: E402

FREQS = [0.1, 0.3, 1, 3, 10, 20, 50, 100, 300, 1000, 3000, 10000]
DUTIES = [0.1, 0.3, 0.5, 0.9]
W, H = 60.0, 40.0                                                    # Board in mm (the disc of the reference has the same area)


def program_problem(layers, side, h, bare=False):
    """!
    @brief The board of the program: one part of side mm in the middle, 1 W of on-power.
    @param layers Copper layers.
    @param side Part side in mm.
    @param h Face coefficient (top and bottom) in W/m2K.
    @param bare True: no copper at all.
    @return Problem.
    """
    p = Problem.new(W, H, layers, 1.6, h_top=h, h_bottom=h, h_side=0.0)
    if not bare:
        p.add_full_copper()
    x0, y0 = 0.5 * (W - side), 0.5 * (H - side)
    p.add_heater(1, 1.0, rect=(x0, y0, x0 + side, y0 + side), name="u", profile=SquareWave(p_on=1.0, period=1.0, duty=0.5))
    return p


def program_swing(problem, resp, f, duty):
    """!
    @brief Peak and valley rise per watt of the program for a unit square wave.
    @param problem Problem with one heater.
    @param resp StepResponse.
    @param f Frequency in Hz.
    @param duty Duty cycle.
    @return Tuple (swing of the node, swing the decision uses) in K/W.
    """
    w = SquareWave(p_on=1.0, period=1.0 / f, duty=duty)
    problem.heaters[0].profile = w
    pk, vl = profiles.wave_response(resp, 0, w)
    d = profiles.decide(problem, resp, 1.0)[0]
    return pk - vl, d.oscillation


def main():
    """!
    @brief Run the sweep and write out/sweep.json.
    @return None.
    """
    out = []
    t0 = time.time()
    for bare in (False, True):
        for layers in ((1, 2, 4) if not bare else (2,)):
            for side in (2.0, 5.0, 10.0):
                for h in (10.0, 30.0):
                    if bare and (h != 10.0 or side != 10.0):
                        continue
                    cell = min(1.0, side / 4.0)
                    prob = program_problem(layers, side, h, bare)
                    resp = profiles.step_response_fvm(prob, cell)
                    st = A.Stack(layers=layers, copper=not bare)
                    ref = A.Reference(st, A.part_radius(side * 1e-3), A.rectangle_radius(W * 1e-3, H * 1e-3), h, h)
                    for f in FREQS:
                        for duty in DUTIES:
                            pn, pd = program_swing(prob, resp, f, duty)
                            rec = {"bare": bare, "layers": layers, "side": side, "h": h, "f": f, "duty": duty, "prog_node": pn, "prog_decision": pd}
                            for ro in ("center", "mean"):
                                mx, mn = ref.square_wave(1.0 / f, duty, ro)
                                rec["ref_" + ro] = mx - mn
                            # The face of a bare part is the top surface; the reference centre cell is the top-surface cell, so the same number is the face swing
                            out.append(rec)
                    print(f"bare={bare} L={layers} side={side} h={h} done ({time.time() - t0:.0f} s)", flush=True)
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    with open(os.path.join(HERE, "..", "out", "sweep.json"), "w") as fh:
        json.dump(out, fh)


if __name__ == "__main__":
    main()
