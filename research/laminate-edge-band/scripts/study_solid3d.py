#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_solid3d.py
@brief Does the program's 3D solid (a second reference, slabs per gap of its own rule) read the edge film like the independent 3D solver? Error of its hottest rise against the reference of out/refs30.json.
@details Cases of the 30 x 20 mm board, 2 layers, thickness 1.6 and 3.2 mm, h_s 50, 200, 500, 2000, corner and centre, cell 1 and 0.5 mm; the solid at its default slabs. Output: table and
         out/solid3d.json. Run (repository root): .venv/bin/python research/laminate-edge-band/scripts/study_solid3d.py
"""

import json

import _bootband

import cases
from pcbthermal import SolverOptions, simulate


def main():
    """!
    @brief Run and print.
    @return None
    """
    refs = json.loads((_bootband.OUT / "refs30.json").read_text())
    out = {}
    print("case | cell | solid3d error % | solid3d rise, reference rise")
    for t in (1.6, 3.2):
        for hs in (50.0, 200.0, 500.0, 2000.0):
            for pos in ("corner", "centre"):
                c = (30, 20, 2, t, hs, pos)
                ref = refs["|".join(str(x) for x in c)]["ref"]
                p, _ = cases.board(*c)
                for cell in (1.0, 0.5):
                    r = simulate(p, SolverOptions(cell_mm=cell, models=("solid3d",))).results["solid3d"].t_max - cases.T0
                    out[f"{c}|{cell}"] = 100 * (r / ref - 1)
                    print(f"t{t} hs{hs:5.0f} {pos:6s} | {cell} | {100 * (r / ref - 1):+6.1f} | {r:7.2f} {ref:7.2f}", flush=True)
    (_bootband.OUT / "solid3d.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
