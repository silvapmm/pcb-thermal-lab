#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_a4_warnings.py
@brief Audit A4 R7: which warnings of the Analytic fire on the 45 uniform boards of R1 (the edge warning of analytic.py and checks.check_reduced_edge_laminate).
@details Run from the repository root: .venv/bin/python releases/2.8.0/audit/scripts/study_a4_warnings.py $PWD (releases/2.8.0/audit/REVIEW_A4.md).
"""
import sys
root = sys.argv[1]; sys.path.insert(0, root); sys.path.insert(0, root + "/research/analytic-edge-spatial/lib")
import cases
from pcbthermal.api import simulate, SolverOptions
sets = [(30, 20, 2, 1.6), (60, 40, 2, 1.6), (60, 40, 2, 3.2), (60, 40, 4, 1.6), (100, 80, 2, 1.6)]
for w, h, L, t in sets:
    for pos in ("centre", "edge", "corner"):
        for hs in (10.0, 50.0, 200.0):
            p, xy = cases.board(w, h, L, t, hs, pos=pos)
            res = simulate(p, SolverOptions(cell_mm=1.0, models=("analytic", "lumped")))
            ws = " || ".join(w_[:70] for w_ in (res.warnings if hasattr(res, "warnings") else []))
            wa = " || ".join(x[:60] for x in res.results["analytic"].warnings)
            print(f"{w}x{h} L{L} t{t} {pos} {hs:.0f} | run: {ws} | analytic: {wa}", flush=True)
