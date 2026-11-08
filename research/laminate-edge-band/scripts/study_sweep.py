#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_sweep.py
@brief Error of the hottest rise of the FVM (and FDM) against the independent 3D reference, for the program as it is and for the edge rules of lib/edge_rules.py, over thickness, edge coefficient,
       position of the part and cell; with the unknowns each rule costs.
@details Cases and references: study_reference.py (out/refs.json). Rules: default; ring (nodes in the border cells only); band of 0.5, 1 and 2 gap thicknesses; the program's own margin
         (ceil(d / dx) + 1 cells); eta (closed-form efficiency of the laminate, no unknowns); hc = the edge film of the laminate nodes in series with half a cell of conduction, also on the laminate of the copper nodes (suffix +hc, first prototype); hci = on the interior laminate nodes only (suffix +hci, the reviewed rule); margin = the band alone. Output: out/sweep.json and a table on the screen.
         Run (repository root): .venv/bin/python research/laminate-edge-band/scripts/study_sweep.py [--cells 1,0.5] [--model fvm|fdm] [--four] [--rules a,b] [--refs refs|refs30] [--out name]
"""

import json
import sys
import time

import _bootband

import cases
import edge_rules as ER
from pcbthermal import SolverOptions, fdm, fvm, simulate

RULES = {"default": {}, "ring": dict(band_width=0.0), "band0.5": dict(band_width=0.5), "band1": dict(band_width=1.0), "band2": dict(band_width=2.0), "eta": dict(eta_mode="exact"),
         "hc": dict(halfcell=True), "ring+hc": dict(band_width=0.0, halfcell=True), "b0.5+hc": dict(band_width=0.5, halfcell=True), "b1+hc": dict(band_width=1.0, halfcell=True),
         "b1.5+hc": dict(band_width=1.5, halfcell=True), "b2+hc": dict(band_width=2.0, halfcell=True), "margin+hc": dict(band_width="margin", halfcell=True),
         "margin+hci": dict(band_width="margin", halfcell="interior"), "margin": dict(band_width="margin")}


def run_case(c, ref, cell, model, rules):
    """!
    @brief Errors and unknowns of the rules on one case.
    @param c Case tuple (w, h, layers, t, h_side, pos).
    @param ref Reference rise in K.
    @param cell Cell in mm.
    @param model "fvm" or "fdm".
    @param rules Names of RULES.
    @return Dict name -> (error in percent, unknowns).
    """
    p, _ = cases.board(*c)
    out = {}
    mod = fvm if model == "fvm" else fdm
    for name in rules:
        with ER.rule(**RULES[name]):
            u = mod.unknowns(p, cell)[0]
            out[name] = (100.0 * (cases.rise(p, model, cell) / ref - 1.0), int(u))
    return out


def main(argv=None):
    """!
    @brief Run the sweep.
    @param argv Command line.
    @return None
    """
    argv = sys.argv[1:] if argv is None else argv
    cells = [float(x) for x in (argv[argv.index("--cells") + 1] if "--cells" in argv else "1,0.5").split(",")]
    model = argv[argv.index("--model") + 1] if "--model" in argv else "fvm"
    name = argv[argv.index("--out") + 1] if "--out" in argv else f"sweep_{model}"
    refname = argv[argv.index("--refs") + 1] if "--refs" in argv else "refs"
    refs = json.loads((_bootband.OUT / f"{refname}.json").read_text())
    path = _bootband.OUT / f"{name}.json"
    res = json.loads(path.read_text()) if path.exists() else {}
    rules = argv[argv.index("--rules") + 1].split(",") if "--rules" in argv else list(RULES)
    print("case | cell | " + " | ".join(rules) + "   (error %, then unknowns of default / b1+hc)")
    for k, r in refs.items():
        c = k.split("|")
        c = (int(c[0]), int(c[1]), int(c[2]), float(c[3]), float(c[4]), c[5])
        if ("--four" in argv) != (c[2] == 4):
            continue
        for cell in cells:
            kk = f"{k}|{cell}"
            if kk not in res:
                t0 = time.time()
                res[kk] = run_case(c, r["ref"], cell, model, rules)
                path.write_text(json.dumps(res, indent=1))
            row = res[kk]
            print(f"L{c[2]} t{c[3]} hs{c[4]:.0f} {c[5]:6s} | {cell} | " + " | ".join(f"{row[n][0]:+6.1f}" for n in rules) + f"   {row['default'][1]} / {row.get('b1+hc', row['default'])[1]}", flush=True)


if __name__ == "__main__":
    main()
