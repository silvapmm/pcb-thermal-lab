#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_a4_uniform.py
@brief Audit A4 R1: the 45 uniform boards of validation 4.1 (sample of the 135): Lumped (0.5 and 1 mm) and Analytic (1 mm) against the shipped FVM at 0.5 mm
       and against the independent 3D solver with side films (research/analytic-edge-spatial/lib, 4 sub-slabs per gap) at 1 mm and, for the 30 x 20 boards, 0.5 mm.
@details Run from the repository root: .venv/bin/python releases/2.8.0/audit/scripts/study_a4_uniform.py $PWD (releases/2.8.0/audit/REVIEW_A4.md).
"""
import sys, numpy as np
root = sys.argv[1]
sys.path.insert(0, root); sys.path.insert(0, root + "/research/analytic-edge-spatial/lib")
import cases
sets = [(30, 20, 2, 1.6), (60, 40, 2, 1.6), (60, 40, 2, 3.2), (60, 40, 4, 1.6), (100, 80, 2, 1.6)]
e = lambda a, b: 100 * (a / b - 1)
for w, h, L, t in sets:
    for pos in ("centre", "edge", "corner"):
        for hs in (10.0, 50.0, 200.0):
            p, xy = cases.board(w, h, L, t, hs, pos=pos)
            an = cases.rise(p, "analytic", 1.0)
            l5 = cases.rise(p, "lumped", 0.5)
            l1 = cases.rise(p, "lumped", 1.0)
            fv = cases.rise(p, "fvm", 0.5)
            r3 = cases.ref3d(p, xy) if w <= 60 else float("nan")
            r3h = cases.ref3d(p, xy, dx_mm=0.5) if w <= 30 else float("nan")
            print(f"{w}x{h} L{L} t{t} {pos:6s} hs {hs:5.0f} | FVM {fv:8.3f} 3D1 {r3:8.3f} 3D.5 {r3h:8.3f} | AN vsFVM {e(an,fv):+6.2f} vs3D {e(an,r3):+6.2f} | LU.5 vsFVM {e(l5,fv):+6.2f} vs3D {e(l5,r3):+6.2f} | LU1 vsFVM {e(l1,fv):+6.2f} vs3D {e(l1,r3):+6.2f} | FVM vs3D {e(fv,r3):+6.2f}", flush=True)
