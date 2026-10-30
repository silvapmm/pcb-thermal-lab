#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_window_sweep.py
@brief Q1 to Q3: the error of FVM, FDM, 3D solid, Lumped and Analytic against the resolved 3D reference as a function of the size of a copper-free window under a 6 mm part, for four stack-ups, two cells, windows in the top layer or in every layer, and a half-bare footprint; and the same board with the proposed treatments.
@details Question answered: how large is the error when the hottest cell under the part has no copper, how does it depend on the window, the laminate thickness, the cell and the model, and which treatment (n laminate nodes in the gaps next to the bare cells, with a margin; or a thinner lateral path) removes it?
         Board 30 x 30 mm, part 6 x 6 mm, 1 W, h_top = h_bottom = 10 W/m2K, laminate 0.9 / 0.3 W/mK, copper 35 um (inner 15.2 um in the typical stack-ups). Reference: lib/resolved3d.py on a quadrant,
         0.25 mm cells, 8 sub-slabs per gap (converged to about 0.5 %, study_reference.py).
         Run from the repository root: .venv/bin/python research/bare-spot-under-source/scripts/study_window_sweep.py [models|treat|extra|all]; results in out/sweep_*.json and out/sweep_*.txt.
"""

import _bootstrap  # noqa: F401  (import paths)

import json
import sys

import sweep as SW
from _bootstrap import OUT

TREATMENTS = ([{"kind": "none"}, {"kind": "vert"}] + [{"kind": "nodes", "n": n} for n in (2, 3, 4, 6)] + [{"kind": "nodes", "n": n, "vert": True} for n in (2, 3, 4)]
              + [{"kind": "skin", "alpha": a} for a in (0.125, 0.25)])


def pct(v, ref):
    """!
    @brief Error in percent against the reference.
    @param v Value.
    @param ref Reference.
    @return float.
    """
    return 100.0 * (v / ref - 1.0)


def models():
    """!
    @brief Q1/Q2: the five models of the program, unchanged, on every stack-up and window.
    @return None (writes out/sweep_models.json and .txt).
    """
    res, lines = [], []
    for stack in SW.STACKS:
        for w in SW.WINDOWS:
            r = SW.run_case(SW.make_case(stack, w))
            res.append(r)
            ref = r["ref"]["max"]
            for cell, m in r["models"].items():
                lines.append(f"{r['name']:<18} ref {ref:7.2f} cell {cell:>4} " + " ".join(f"{k} {v:7.2f} ({pct(v, ref):+6.1f}%)" for k, v in m.items()))
            print(lines[-1], flush=True)
    json.dump(res, open(OUT / "sweep_models.json", "w"), indent=1)
    (OUT / "sweep_models.txt").write_text("\n".join(lines))


def treat():
    """!
    @brief Q3/Q4: the treatments on the FVM for every stack-up and window.
    @return None (writes out/sweep_treat.json and .txt).
    """
    res, lines = [], []
    for stack in SW.STACKS:
        for w in SW.WINDOWS[1:]:
            r = SW.run_case(SW.make_case(stack, w), models=("fvm",), treatments=TREATMENTS)
            res.append(r)
            ref = r["ref"]["max"]
            for cell, t in r["treat"].items():
                lines.append(f"{r['name']:<18} ref {ref:7.2f} cell {cell:>4} " + " ".join(f"{k} {pct(v['peak'], ref):+6.1f}% ({v['unknowns']})" for k, v in t.items()))
                print(lines[-1], flush=True)
    json.dump(res, open(OUT / "sweep_treat.json", "w"), indent=1)
    (OUT / "sweep_treat.txt").write_text("\n".join(lines))


def extra():
    """!
    @brief Windows through every copper layer and the half-bare footprint, program and treatments.
    @return None (writes out/sweep_extra.json and .txt).
    """
    cases = []
    for stack, layers in (("2L 1.6 mm", (0, 1)), ("4L typical", (0, 1, 2, 3))):
        for w in (6, 12):
            cases.append(SW.make_case(stack, w, window_layers=layers))
    for stack in SW.STACKS:
        cases.append(SW.make_case(stack, 0, half=True))
    res, lines = [], []
    for c in cases:
        r = SW.run_case(c, treatments=TREATMENTS)
        res.append(r)
        ref = r["ref"]["max"]
        for cell in r["models"]:
            lines.append(f"{r['name']:<28} ref {ref:7.2f} cell {cell:>4} " + " ".join(f"{k} {pct(v, ref):+6.1f}%" for k, v in r["models"][cell].items())
                         + " | " + " ".join(f"{k} {pct(v['peak'], ref):+6.1f}%" for k, v in r["treat"][cell].items()))
            print(lines[-1], flush=True)
    json.dump(res, open(OUT / "sweep_extra.json", "w"), indent=1)
    (OUT / "sweep_extra.txt").write_text("\n".join(lines))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in (("models", models), ("treat", treat), ("extra", extra)):
        if what in (name, "all"):
            fn()
