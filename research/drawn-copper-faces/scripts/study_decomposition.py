#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_decomposition.py
@brief Question (a): where does the gap between drawn and imported copper come from, and how far is each variant from an independent finite-element solution?
@details The same board is run in the program's FVM and FDM as (1) drawn zones (4 x 4 samples for the cell fill, the fill-weighted harmonic mean for the faces), and as the same
         copper handed to the program as an import with (2) mapping `fill` (exact coverage fill, the same harmonic faces: isolates the fill), (3) `lambda` and (4) `faces`
         (flow-based faces on the reduced sheet: the imported default). The laminate rule is the program's default (sub-gaps of at most 0.4 mm, at most 4); `--n8` gives 8.
         Reference: `out/fem.json` (`study_fem_reference.py`), the heater mean of the resolved finite-element board at 0.4 and 0.2 mm, extrapolated to zero plan size assuming second order (0.4 and 0.2 mm; 0.4 and 0.3 mm for the 4-layer board);
         the extrapolation is a ESTIMATE, the move from 0.2 mm to it is printed. Run: `.venv/bin/python research/drawn-copper-faces/scripts/study_decomposition.py [--n8] [--fdm]`.
         Cache `out/dec.json`.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import dc_cases as D                                                      # noqa: E402
from pcbthermal import laminate                                           # noqa: E402

OUT = os.path.join(HERE, "..", "out")
CELLS = (1.0, 0.5, 0.25)
LIST = [("plain_inset", 10, 2), ("plain_inset", 50, 2), ("plain_inset", 200, 2), ("plain_inset", 1000, 2), ("plain_wall", 200, 2), ("plain_wall", 1000, 2),
        ("stripes", 200, 2), ("stripes", 1000, 2), ("ell", 200, 2), ("plain_inset", 200, 4), ("hatch", 200, 2)]
VARIANTS = ("drawn", "fill", "lambda", "faces")


def fem_ref(name, hs, layers):
    """!
    @brief The finite-element reference of a case: the 0.2 mm value and the extrapolation.
    @param name Case name.
    @param hs Edge film.
    @param layers Layers.
    @return Tuple (v02, v_extrapolated) or None without a cached solution.
    """
    p = os.path.join(OUT, "fem.json")
    if not os.path.exists(p):
        return None
    res = json.load(open(p))
    k4 = f"{name}|{hs:g}|{layers}|0.4"
    for fine in ("0.2", "0.3"):                                       # the 4-layer board is refused at 0.2 mm (above 2 GB): 0.4 and 0.3 mm
        k2 = f"{name}|{hs:g}|{layers}|{fine}"
        if k4 in res and k2 in res:
            h1, h2 = 0.4, float(fine)
            v1, v2 = res[k4]["heater_mean"], res[k2]["heater_mean"]
            return v2, v2 + (v2 - v1) * h2 ** 2 / (h1 ** 2 - h2 ** 2)   # second order in the plan size
    return None


def run_case(name, hs, layers, model, n8):
    """!
    @brief Heater mean rise of the four variants at the three cells.
    @param name Case.
    @param hs Edge film.
    @param layers Layers.
    @param model 'fvm' or 'fdm'.
    @param n8 True: eight laminate sub-gaps.
    @return dict variant -> list of rises per cell.
    """
    p = D.problem(D.case(name, hs, layers))
    run = D.heater_mean_fvm if model == "fvm" else D.heater_mean_fdm
    out = {}
    for var in VARIANTS:
        vals = []
        for cell in CELLS:
            q = p if var == "drawn" else D.zones_to_imported(p, cell, var)
            if n8:
                with laminate.using(0.2e-3, 8):
                    vals.append(run(q, cell)[0])
            else:
                vals.append(run(q, cell)[0])
        out[var] = vals
    return out


def main():
    """!
    @brief Run every case and print the error table.
    @return None.
    """
    n8 = "--n8" in sys.argv
    models = ["fvm"] + (["fdm"] if "--fdm" in sys.argv else [])
    path = os.path.join(OUT, "dec.json")
    res = json.load(open(path)) if os.path.exists(path) else {}
    os.makedirs(OUT, exist_ok=True)
    for model in models:
        for name, hs, layers in LIST:
            key = f"{model}|{name}|{hs}|{layers}|{'n8' if n8 else 'n4'}"
            if key not in res:
                res[key] = run_case(name, hs, layers, model, n8)
                json.dump(res, open(path, "w"), indent=1)
            ref = fem_ref(name, hs, layers)
            r = ref[1] if ref else res[key]["faces"][-1]
            tag = "FEM" if ref else "faces@0.25 (no FEM)"
            line = f"{model} {name:12s} h_side {hs:5d} L{layers} ref {r:8.3f} K [{tag}]"
            print(line)
            for var in VARIANTS:
                v = res[key][var]
                print(f"    {var:7s} " + "  ".join(f"{c:g}mm {100 * (x / r - 1):+6.2f}%" for c, x in zip(CELLS, v)), flush=True)


if __name__ == "__main__":
    main()
