#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_correction.py
@brief Question 3: the column correction (lib/correction.py) against the independent reference over the sweep of study_fast_wave_sweep.py, and the decisions it changes.

@details For every case of the sweep the step response of the program gets dZ = Z_exact column - Z_lumped column added, the program's own wave_response gives the corrected swing, and the
result is compared with the axisymmetric reference. Writes out/correction.json. Run from the repository root with QT_QPA_PLATFORM=offscreen.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import study_fast_wave_sweep as S                                    # noqa: E402,F401  (sets the paths)
import numpy as np                                                   # noqa: E402

import axisym_stack as A                                             # noqa: E402
import correction as Co                                              # noqa: E402
from pcbthermal import profiles                                      # noqa: E402
from pcbthermal.model import SquareWave                              # noqa: E402


def main():
    """!
    @brief Run the correction over the sweep (full copper) and write out/correction.json.
    @return None.
    """
    out = []
    for layers in (1, 2, 4):
        for side in (2.0, 5.0, 10.0):
            for h in (10.0, 30.0):
                prob = S.program_problem(layers, side, h)
                resp = profiles.step_response_fvm(prob, min(1.0, side / 4.0))
                st = A.Stack(layers=layers)
                area = (side * 1e-3) ** 2
                dz = Co.column_difference(st, area, h, h, resp.times)
                phi = Co.spreading_factor(st, area, h, h, resp.times, resp.z[0])
                rc = Co.corrected(resp, 0, dz * phi)
                r1 = Co.corrected(resp, 0, dz)
                ref = A.Reference(st, A.part_radius(side * 1e-3), A.rectangle_radius(S.W * 1e-3, S.H * 1e-3), h, h)
                for f in S.FREQS:
                    for duty in S.DUTIES:
                        w = SquareWave(p_on=1.0, period=1.0 / f, duty=duty)
                        prob.heaters[0].profile = w
                        pk0, vl0 = profiles.wave_response(resp, 0, w)
                        pk1, vl1 = profiles.wave_response(rc, 0, w)
                        pk2, vl2 = profiles.wave_response(r1, 0, w)
                        mx, mn = ref.square_wave(1.0 / f, duty, "center")
                        out.append({"layers": layers, "side": side, "h": h, "f": f, "duty": duty, "prog": pk0 - vl0, "corr": pk1 - vl1, "corr_plain": pk2 - vl2, "ref": mx - mn})
                print("done", layers, side, h, flush=True)
    with open(os.path.join(HERE, "..", "out", "correction.json"), "w") as fh:
        json.dump(out, fh)


if __name__ == "__main__":
    main()
