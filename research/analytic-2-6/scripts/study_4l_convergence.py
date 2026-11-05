#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_4l_convergence.py
@brief Is the remaining transient error of the four-layer board with vias and a heatsink the model or the reference? FVM at 1 and 0.5 mm, local modal system at K 16 to 32.

@details The board is "4L vias+sink under" of study_transient_both.py (heatsink 300 W/m2K). Prints the time to 63 % of the FVM at both cells and of the local modal prototype
         for several K, and the unit-step response at a few times. Run from the repository root:
         .venv/bin/python research/analytic-2-6/scripts/study_4l_convergence.py   (about 3 minutes)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, HERE)

import boards26 as B          # noqa: E402
import local_modal as LM      # noqa: E402
from study_transient_both import boards, curve_err   # noqa: E402


def main():
    """!
    @brief Print the comparison.
    @return None.
    """
    _, p = boards()[8]
    ref = {}
    for cell in (1.0, 0.5):
        t, z, r = B.step(p, "fvm", cell)
        ref[cell] = (t, z, r)
        print(f"FVM {cell} mm: R {r[0]:.3f} K/W, t63 {B.t63(t, z[:1], r[:1])[0]:.2f} s")
    t, z, r = ref[0.5]
    for K in (16, 24, 32):
        ti, zi, ri, s = LM.step_local(p, 1.0, 300, K)
        t63 = B.t63(ti, zi, ri)[0]
        print(f"local K{K}: s {s:.2f}, R {ri[0]:.3f}, t63 {t63:.2f} s ({100 * (t63 / B.t63(t, z[:1], r[:1])[0] - 1):+.1f} % of the FVM at 0.5 mm), "
              f"curve difference to the FVM at 0.5 mm {curve_err(t, z[0], r[0], ti, zi[0], ri[0]):.1f} % of R")
    print("unit-step response (K/W) at t = 1, 2, 5, 10, 20, 50 s: FVM 1 mm / FVM 0.5 mm / local K32")
    for tt in (1, 2, 5, 10, 20, 50):
        print(f"  {tt:3d}: {np.interp(tt, ref[1.0][0], ref[1.0][1][0]):.3f} / {np.interp(tt, t, z[0]):.3f} / {np.interp(tt, ti, zi[0]):.3f}")


if __name__ == "__main__":
    main()
