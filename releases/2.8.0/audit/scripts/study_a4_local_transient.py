#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_a4_local_transient.py
@brief Audit A4 R5: the ten boards of validation 4.1 (local transient) on the program of 2.7.1, through the program's own step responses (study_transient_both.py cannot be
       imported: its lib/calib_variants.py reads analytic._calibrated_dynamics, removed in 2.6.0). Time to 63 % (log-time interpolation of z/r = 0.632) and steady resistance of the
       FVM at 0.5 mm and of the Analytic (1 mm) and the Lumped (its cell rule); the 4 L board also at 0.25 mm.
@details Run from the repository root: .venv/bin/python releases/2.8.0/audit/scripts/study_a4_local_transient.py $PWD (releases/2.8.0/audit/REVIEW_A4.md).
"""
import sys, numpy as np
root = sys.argv[1]; sys.path.insert(0, root); sys.path.insert(0, root + "/research/analytic-edge-and-transient/lib")
import boards26 as B
from pcbthermal import fvm, analytic, lumped
def t63(t, z, r):
    """!
    @brief Time to 63 % of a step response by log-time interpolation.
    @param t Times in s.
    @param z Response in K/W.
    @param r Steady resistance in K/W.
    @return float Time in s.
    """
    f = z / r; i = int(np.argmax(f >= 0.632)); return float(np.exp(np.interp(0.632, f[i-1:i+1], np.log(t[i-1:i+1]))))
pl, wv, ws = B.plain, B.with_vias, B.with_sink
bl = [("plain 2L", pl()), ("1 via", wv(pl(), 1)), ("vias 4x4", wv(pl())), ("sink under", ws(pl())), ("sink beside", ws(pl(), 100.0, "side")),
      ("vias+sink under", ws(wv(pl()))), ("vias+sink beside", ws(wv(pl()), 100.0, "side")), ("plain 4L", pl(4)),
      ("4L vias+sink under", ws(wv(pl(4)), 300.0)), ("2L h_side 50 vias+sink", ws(wv(pl(h_side=50.0))))]
for name, p in bl:
    tf, zf, rf = fvm.step_responses(p, cell_mm=0.5); ta, za, ra = analytic.step_responses(p, cell_mm=1.0)
    tl, zl, rl = lumped.step_responses(p, cell_mm=lumped.cell_for(p, 1.0))
    f63, a63, l63 = t63(tf, zf[0], rf[0]), t63(ta, za[0], ra[0]), t63(tl, zl[0], rl[0])
    extra = ""
    if name.startswith("4L"):
        tq, zq, rq = fvm.step_responses(p, cell_mm=0.25); extra = f" | FVM 0.25 mm t63 {t63(tq, zq[0], rq[0]):.2f} s R {rq[0]:.3f}"
    print(f"{name:24s} FVM t63 {f63:7.2f} s R {rf[0]:7.3f} | Analytic t63 {100*(a63/f63-1):+6.1f} % R {ra[0]:7.3f} | Lumped t63 {100*(l63/f63-1):+6.1f} % R {rl[0]:7.3f}{extra}", flush=True)
