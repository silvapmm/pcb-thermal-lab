#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_switches.py
@brief Which piece of the 2.6.0 edge treatment limits the plate at h_side 1000: the band width, the cut-cell edge film, the half-cell conduction? (monkeypatches in the script; the program is untouched)
@details Question: is the converged -6 % of the plate at a strongly cooled edge a missing band width (a candidate fix) or the layered idealisation itself. Runs the no-via board at
         h_side 1000 and 200, cell 0.25 mm, 16 sub-gaps, with the variants `asis`, `wide` (the band margin x3 and x6) and `nofilm`, and prints the error against the reference
         (24.7338 K, dx 1/8; 24.5377 K at dx 1/16 for h 1000). Run: `.venv/bin/python research/strong-edge-laminate/scripts/study_switches.py`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import prog                                                         # noqa: E402
from pcbthermal import fvm, laminate                                # noqa: E402

REF = {1000: 24.5377, 200: 37.08}                                   # no-via reference (3D, 8 sub-slabs; 1/16 mm for 1000, 1/8 for 200)
orig_margin = laminate.margin_cells
orig_film = fvm.Network._cut_edge_film

for h in (1000, 200):
    for variant in ("asis", "wide3", "wide6", "nofilm"):
        laminate.margin_cells = orig_margin
        fvm.Network._cut_edge_film = orig_film
        if variant.startswith("wide"):
            mult = int(variant[4:])
            laminate.margin_cells = lambda d, dx, m=mult: orig_margin(d, dx) * m
        if variant == "nofilm":
            fvm.Network._cut_edge_film = lambda self, g0: g0
        for cell in (0.5, 0.25):
            a = prog.run(prog.board(h), cell, 16)
            print(f"h {h} {variant:7s} cell {cell}: {a:.3f} K  error {100 * (a / REF[h] - 1):+.1f} %", flush=True)
