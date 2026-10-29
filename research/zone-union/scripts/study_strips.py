#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_strips.py
@brief Q4 (where the zone edges fall): the error of the old rule against the width of abutting strips and the offset of their joints with respect to the cell grid.
@details Question answered: how much copper does the old rule lose, as a function of the strip width in cells and of the phase of the joints? The 20 x 20 mm board (the board of lib/cases.py) is covered by abutting
         vertical strips of width w; their joints sit at multiples of w plus a shift. The peak rise of the FVM and of the FDM (cells of 1.0 mm) under the old rule (the program as it is: ZONE_RULE=max_cell for
         the FVM; the unmodified program for the FDM) and under the per-point union is compared with the one-zone board (which has the same copper). The copper area of the cell field is printed too.
         Run from the repository root: .venv/bin/python research/zone-union/scripts/study_strips.py [develop|variant|report]; out/strips_*.json, out/study_strips.txt.
"""

import _bootstrap  # noqa: F401  (import paths)

import json
import sys

import numpy as np

import variant
from paths import OUT

WIDTHS = (0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.25, 1.5, 2.0, 3.0)
SHIFTS = (0.0, 0.25, 0.5)                              # fraction of a strip width
CELL = 1.0


def strip_problem(cases, w, shift):
    """!
    @brief The board covered by abutting vertical strips of width w whose joints are shifted.
    @param cases The cases module.
    @param w Strip width (mm).
    @param shift Shift of the first joint as a fraction of the width.
    @return Problem.
    """
    p = cases.new_problem()
    x = -(1 - shift) * w if shift else 0.0
    while x < 20.0 - 1e-9:
        lo, hi = max(x, 0.0), min(x + w, 20.0)
        if hi - lo > 1e-9:
            p.add_zone(1, rect=(lo, 0, hi, 20))
        x += w
    return p


def run(mode):
    """!
    @brief Run the sweep for the program as it is (develop) or the variant (every rule).
    @param mode develop or variant.
    @return None (writes out/strips_<mode>.json).
    """
    variant.use(mode == "variant")
    import cases
    from pcbthermal import SolverOptions, simulate
    one = cases.new_problem()
    one.add_zone(1, rect=(0, 0, 20, 20))
    base = {m: simulate(one, SolverOptions(models=(m,), cell_mm=CELL)).results[m].t_max - 25.0 for m in ("fvm", "fdm")}
    res = {"base": base}
    for w in WIDTHS:
        for sh in SHIFTS:
            p = strip_problem(cases, w, sh)
            key = f"{w}/{sh}"
            if mode == "variant":
                res[key] = {}
                for rule in ("max_cell", "max_point"):
                    variant.set_rule(rule)
                    res[key][rule] = {m: simulate(p, SolverOptions(models=(m,), cell_mm=CELL)).results[m].t_max - 25.0 for m in ("fvm", "fdm")}
            else:
                res[key] = {"develop": {m: simulate(p, SolverOptions(models=(m,), cell_mm=CELL)).results[m].t_max - 25.0 for m in ("fvm", "fdm")}}
            print(mode, key, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"strips_{mode}.json").write_text(json.dumps(res, indent=1))


def table():
    """!
    @brief Rows (width, shift, old FVM error %, prototype FVM error %, old FDM error %, prototype FDM error %) against the one-zone board.
    @return list of tuples.
    """
    dev = json.loads((OUT / "strips_develop.json").read_text())
    var = json.loads((OUT / "strips_variant.json").read_text())
    b = dev["base"]
    rows = []
    for w in WIDTHS:
        for sh in SHIFTS:
            k = f"{w}/{sh}"
            rows.append((w, sh, 100 * (dev[k]["develop"]["fvm"] / b["fvm"] - 1), 100 * (var[k]["max_point"]["fvm"] / b["fvm"] - 1),
                         100 * (dev[k]["develop"]["fdm"] / b["fdm"] - 1), 100 * (var[k]["max_point"]["fdm"] / b["fdm"] - 1)))
    return rows


def report():
    """!
    @brief Print the table and save it.
    @return None.
    """
    lines = [f"Abutting strips of width w (cells of {CELL} mm): peak-rise error (%) against one zone of the same copper",
             f"{'w mm':>6s}{'joint shift':>12s}{'old FVM':>10s}{'proto FVM':>11s}{'old FDM':>10s}{'proto FDM':>11s}"]
    for r in table():
        lines.append(f"{r[0]:6.2f}{r[1]:12.2f}{r[2]:10.2f}{r[3]:11.2f}{r[4]:10.2f}{r[5]:11.2f}")
    print("\n".join(lines))
    (OUT / "study_strips.txt").write_text("\n".join(lines))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if mode in ("develop", "variant"):
        run(mode)
    else:
        report()
