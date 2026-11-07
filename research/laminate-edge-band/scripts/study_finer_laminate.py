#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_finer_laminate.py
@brief How much of the remaining error of the band + half-cell rule is the number of sub-gaps (the program's 4 against 8 and 16), and does the model converge to the 3D reference when resolved?
@details Part 1: the band rules with the program's laminate (0.4 mm, 4) and with 0.2 mm / 8 and 0.1 mm / 16, cell 0.5 mm, 30 x 20 mm board, errors against out/refs30.json and unknowns.
         Part 2: nodes everywhere (copper fill 0.9999, no band, no half-cell film) on the 3.2 mm board at h_s 200 and 2000, cell 0.5 and 0.25 mm with 4 and 16 sub-gaps: the resolved model
         against the reference, to show that what is left is discretisation. Run (repository root): .venv/bin/python research/laminate-edge-band/scripts/study_finer_laminate.py
"""

import json

import _bootband

import cases
import edge_rules as ER
from pcbthermal import SolverOptions, fvm, laminate, simulate


def main():
    """!
    @brief Run both parts.
    @return None
    """
    refs = json.loads((_bootband.OUT / "refs30.json").read_text())
    cfgs = [("n4 b1", 0.4, 4, dict(band_width=1.0)), ("n4 b1+hc", 0.4, 4, dict(band_width=1.0, halfcell=True)), ("n8 b1+hc", 0.2, 8, dict(band_width=1.0, halfcell=True)),
            ("n16 b1+hc", 0.1, 16, dict(band_width=1.0, halfcell=True)), ("n4 b0.5+hc", 0.4, 4, dict(band_width=0.5, halfcell=True)), ("n8 b0.5+hc", 0.2, 8, dict(band_width=0.5, halfcell=True))]
    print("part 1: case | " + " | ".join(c[0] for c in cfgs) + "   error % (unknowns)")
    for t in (1.6, 3.2):
        for hs in (50.0, 200.0, 500.0, 2000.0):
            for pos in ("corner", "centre"):
                c = (30, 20, 2, t, hs, pos)
                ref = refs["|".join(str(x) for x in c)]["ref"]
                p, _ = cases.board(*c)
                row = []
                for nm, s, n, kw in cfgs:
                    with ER.rule(**kw):
                        with laminate.using(s * 1e-3, n):
                            u = fvm.unknowns(p, 0.5)[0]
                        r = simulate(p, SolverOptions(cell_mm=0.5, models=("fvm",), laminate_s_max_mm=s, laminate_n_max=n)).results["fvm"].t_max - cases.T0
                    row.append(f"{100 * (r / ref - 1):+5.1f} ({u})")
                print(f"t{t} hs{hs:5.0f} {pos:6s} | " + " | ".join(row), flush=True)
    print("part 2: nodes everywhere (fill 0.9999), t 3.2 mm: h_s | position | cell | sub-gaps | error %")
    for hs in (200.0, 2000.0):
        for pos in ("corner", "centre"):
            c = (30, 20, 2, 3.2, hs, pos)
            ref = refs["|".join(str(x) for x in c)]["ref"]
            p, _ = cases.board(*c)
            for z in p.zones:
                z.fill = 0.9999
            for cell, s, n in ((0.5, 0.4, 4), (0.5, 0.2, 16), (0.25, 0.2, 16)):
                r = simulate(p, SolverOptions(cell_mm=cell, models=("fvm",), laminate_s_max_mm=s, laminate_n_max=n)).results["fvm"].t_max - cases.T0
                print(f"{hs:5.0f} | {pos:6s} | {cell} | {n} | {100 * (r / ref - 1):+5.1f}", flush=True)


if __name__ == "__main__":
    main()
