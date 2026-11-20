#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_flag_rule.py
@brief Which length of a rectangular source governs the thin-sheet limit of the surface term (surface minus column)? Measures elongated parts against the independent 3D solver.

@details Question: the flag 'estimate, upper side' of the surface read-out is raised when t/a > 0.5, where the parabola of thickness.offsets overshoots the true term. For a
         rectangle b x c (b the smaller side) is a the smaller side b, the geometric mean sqrt(b c) (the rule before this fix), or something else? Method: a 50 x 50 mm plate of
         conductivity K, thickness t, bottom film 400 W/m2K, top insulated, heat on a centred rectangle, solved by `tests/helpers/layered3d.py` (imports nothing from pcbthermal,
         8 sub-slabs, 0.5 mm cells). The TRUE term is the surface minus the column mean at the centre of the source (as research/through-thickness-readout/scripts/study_sweep.py);
         the PREDICTION is the parabola with the flux of the program (q = P/A on the top face, the film through the half layer on the bottom face). A case is 'overshooting' when the
         prediction exceeds the true term by more than 7 % (the tolerance quoted for the parabola up to t/a = 0.5). Each rule flags a case when t/a(rule) > 0.5; the table prints
         the three t/a values, the ratio and which rule agrees with the overshoot.
         Usage: .venv/bin/python releases/2.9.0/surface-flag/scripts/study_flag_rule.py   (about 1 min, under 1 GB)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
for p in (ROOT, os.path.join(ROOT, "tests", "helpers")):
    sys.path.insert(0, p)
import layered3d as L                                          # noqa: E402
from pcbthermal import thickness                               # noqa: E402

W = 50e-3                                                      # plate side in m
DX = 0.5e-3                                                    # plan cell in m (a 2 mm side is 4 cells)
H = 400.0                                                      # bottom film in W/m2K
NSUB = 8                                                       # sub-slabs through the plate
TOL = 0.07                                                     # tolerance of the parabola quoted up to t/a 0.5


def one_case(t, k, b, c, power=10.0):
    """!
    @brief One plate under a centred rectangle b x c: true and parabolic term at the source centre.
    @param t Thickness in m.
    @param k Conductivity in W/mK.
    @param b Short side of the source in m.
    @param c Long side of the source in m.
    @param power Source power in W (the ratios do not depend on it).
    @return dict with d3 (true term, K), parabola (K) and their ratio.
    """
    n = int(round(W / DX))
    m = W / 2
    r = L.solve(DX, n, n, [(t, k, NSUB)], (m - c / 2, m - b / 2, m + c / 2, m + b / 2), power, 0.0, H)
    dz = np.array(r["dz"])
    col = np.tensordot(dz / dz.sum(), r["T"], axes=(0, 0))
    j = n // 2
    sl = (slice(j - 1, j + 1), slice(j - 1, j + 1))
    d3 = float(r["surface_top"][sl].mean() - col[sl].mean())
    q = power / (b * c)
    qb = -float(col[sl].mean()) / (1.0 / H + t / (2.0 * k))     # film through the half layer, as the program
    d_par = float(thickness.offsets(t, k, q, qb)[0])
    return {"d3": d3, "parabola": d_par, "ratio": d_par / d3}


def main():
    """!
    @brief Run the cases and print the table of t/a for the three rules against the measured overshoot.
    """
    # (k W/mK, t mm, b mm, c mm): the 2 mm plate of the question, the 1 mm one, a thicker 3 mm one near the threshold, a lower conductivity and a 2 x 40 strip
    cases = [(385, 1, 2, 20), (385, 1, 2, 10), (385, 1, 5, 10), (385, 1, 10, 10),
             (385, 2, 2, 20), (385, 2, 2, 10), (385, 2, 2, 40), (385, 2, 3, 10), (385, 2, 4, 20), (385, 2, 5, 10), (385, 2, 5, 20), (385, 2, 10, 10), (385, 2, 10, 20), (385, 2, 20, 20),
             (385, 3, 5, 10), (385, 3, 4, 20), (150, 2, 2, 20), (150, 2, 5, 10), (150, 2, 10, 10)]
    print("k W/mK | t mm | b x c mm | t/b   t/sqrt(bc) | parab/true | overshoot>7% | flag b | flag sqrt(A)")
    score = {"b": 0, "sqrtA": 0}
    for k, t_mm, b_mm, c_mm in cases:
        r = one_case(t_mm * 1e-3, float(k), b_mm * 1e-3, c_mm * 1e-3)
        tb, tg = t_mm / b_mm, t_mm / np.sqrt(b_mm * c_mm)
        over = r["ratio"] > 1.0 + TOL
        fb, fg = tb > thickness.UPPER_RATIO, tg > thickness.UPPER_RATIO
        score["b"] += int(fb == over)
        score["sqrtA"] += int(fg == over)
        print(f"{k:6d} | {t_mm:4.1f} | {b_mm:2d} x {c_mm:2d} | {tb:5.2f} {tg:8.2f} | {r['ratio']:9.3f} | {str(over):12s} | {str(fb):6s} | {str(fg):6s}")
    n_tot = len(cases)
    print(f"agreement with the measured overshoot: smaller side {score['b']}/{n_tot}, sqrt(A) {score['sqrtA']}/{n_tot}")


if __name__ == "__main__":
    main()
