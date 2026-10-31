#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_foster_cauer.py
@brief F6, topic 12: the Cauer model of the BUK7S1R0-40H of Nexperia AN11261 Rev. 5.0, its Foster equivalent and the published numbers (Rth 0.4 K/W, Zth 0.26 K/W for the 4 ms pulse of example 2).
@details The Cauer values are the netlist of Fig. 6 (page 6) and the schematic of Fig. 8 (page 8). Published numbers: Table 1 (page 2) Rth(j-mb) typical 0.35 and maximum 0.4 K/W; Fig. 11 and Fig. 12
(pages 10 and 11): Rth = 0.4 K/W and Zth = 0.26 K/W for the first pulse (120 W for 4 ms) of Table 3; example 2 sets the mounting base at 125 C. The Foster network is obtained from the ladder by the pole
decomposition (lib/rc_ladder.py); the step response of the ladder is computed with the matrix exponential, which does not use the Foster formula, so the two agree only if the transformation is right.
Run from the repository root: .venv/bin/python research/theory-sources/scripts/study_foster_cauer.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import rc_ladder as rl  # noqa: E402

R = np.array([0.00272144, 0.0220255, 0.00713124, 0.185679, 0.182443])
C = np.array([9.29451e-05, 0.000514739, 0.00195047, 0.00305028, 0.0279554])


def main():
    """!
    @brief Print the checks.
    @return None.
    """
    print("Sum of the Cauer resistances: %.4f K/W (datasheet Rth(j-mb): typical 0.35, maximum 0.4; Fig. 11 and 12: Rth = 0.4)" % R.sum())
    t = np.array([1e-6, 1e-5, 1e-4, 1e-3, 4e-3, 1e-2, 1e-1, 1.0])
    zc = rl.zth_cauer(t, R, C)
    rf, tau = rl.foster(R, C)
    zf = rl.zth_foster(t, rf, tau)
    print("Foster equivalent: R_i %s K/W, tau_i %s s; sum %.4f K/W" % (np.round(rf, 5).tolist(), ["%.3g" % x for x in tau], rf.sum()))
    print("Zth(t) of the ladder (matrix exponential) against the Foster form, largest difference %.2e K/W" % np.abs(zc - zf).max())
    for ti, z in zip(t, zc):
        print("   t = %8.1e s  Zth = %.4f K/W" % (ti, z))
    print("First pulse of example 2: 120 W for 4 ms -> Zth(4 ms) = %.4f K/W (paper 0.26), rise %.1f K, junction %.1f C on the 125 C base"
          % (rl.zth_cauer([4e-3], R, C)[0], 120 * rl.zth_cauer([4e-3], R, C)[0], 125 + 120 * rl.zth_cauer([4e-3], R, C)[0]))
    print("Total capacity %.4f J/K; the single time constant of the dominant pole %.3g s" % (C.sum(), tau.max()))


if __name__ == "__main__":
    main()
