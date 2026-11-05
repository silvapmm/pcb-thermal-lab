#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_variants.py
@brief The partial-copper boards against the candidate via treatments: via effect against the converged 3D solid, cold spot, minimum rise, positive off-diagonal entries of K.
@details For every case of lib/cases.py, every variant of lib/viavariants.py (current, sheet, plane, star), the FVM and the FDM and the cells 1, 0.5, 0.25 and 0.125 mm:
         the maximum rise with the via, the via effect (rise without the via minus rise with it), the local cold spot, the minimum rise over the board and the number of positive
         off-diagonal entries of K. The reference is the 3D solid at 0.0625 and 0.05 mm (the pair shows whether it has converged). Writes `out/variants.json`.
         Run from the repository root: `.venv/bin/python research/via-partial-copper/scripts/study_variants.py [--quick]`.
         Light: 10 x 10 mm boards, at most 0.2 M unknowns per solve.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import numpy as np                                                            # noqa: E402

import cases                                                                  # noqa: E402
import viavariants as vv                                                      # noqa: E402

PLAN = [("edge", dict(delta=0.0)), ("edge", dict(delta=0.3)), ("edge", dict(delta=-0.3)), ("track", dict(width=0.4)), ("track", dict(width=1.0)),
        ("island", dict(side=1.2)), ("antipad", dict(hole=1.0)), ("antipad", dict(hole=1.0, land=0.6)), ("antipad", dict(hole=2.0)), ("bare", dict()), ("bare", dict(h=2000.0, power=2.0))]
VARIANTS = ("current", "sheet", "plane", "star")


def label(name, kw):
    """!
    @brief Text label of a case.
    @param name Case name.
    @param kw Its parameters.
    @return str.
    """
    return name + "".join(f" {k}={v}" for k, v in kw.items())


def positive_entries(net):
    """!
    @brief Number of positive off-diagonal entries of K.
    @param net Network.
    @return int.
    """
    coo = net.K.tocoo()
    return int(((coo.row != coo.col) & (coo.data > 1e-12 * np.abs(net.K.diagonal()).max())).sum())


def solve(problem, model, cell):
    """!
    @brief One layered solve with the numbers of the study.
    @param problem Problem.
    @param model "fvm" or "fdm".
    @param cell Cell size in mm.
    @return dict tmax, tmin, cold, pos.
    """
    net = cases.network(problem, model, cell)
    theta, _ = net.solve_steady()
    keep = np.ones(theta.shape, dtype=bool) if net.drop is None else ~net.drop
    return dict(tmax=float(theta[:problem.board.layers].max()), tmin=float(theta[keep].min()),
                cold=cases.local_cold_spot(problem, theta, "node" if model == "fdm" else "cell"), pos=positive_entries(net))


def main():
    """!
    @brief Run the sweep and print the table.
    @return None.
    """
    quick = "--quick" in sys.argv
    cells = [1.0, 0.5, 0.25] if quick else [1.0, 0.5, 0.25, 0.125]
    out = {}
    print(f"{'case':26s} {'model':5s} {'variant':8s} {'cell':>6s} {'effect':>8s} {'ref(1/16,1/20)':>15s} {'err%':>7s} {'cold':>8s} {'min':>8s} {'pos':>6s}")
    for name, kw in PLAN:
        f = cases.CASES[name]
        ref = []
        for c in (0.0625, 0.05):
            a, b = cases.run(f(**kw), "solid3d", c), cases.run(f(with_via=False, **kw), "solid3d", c)
            ref.append(b["tmax"] - a["tmax"])
        for model in ("fvm", "fdm"):
            for cell in cells:
                base = solve(f(with_via=False, **kw), model, cell)
                for variant in VARIANTS:
                    with vv.patched(variant):
                        r = solve(f(**kw), model, cell)
                    eff = base["tmax"] - r["tmax"]
                    err = 100.0 * (eff - ref[1]) / ref[1]
                    out[f"{label(name, kw)}|{model}|{variant}|{cell}"] = dict(effect=eff, ref=ref, err_pct=err, **r)
                    print(f"{label(name, kw):26s} {model:5s} {variant:8s} {cell:6.3f} {eff:8.2f} {ref[0]:7.2f},{ref[1]:7.2f} {err:7.1f} {r['cold']:8.2f} {r['tmin']:8.2f} {r['pos']:6d}", flush=True)
    os.makedirs(os.path.join(os.path.dirname(HERE), "out"), exist_ok=True)
    with open(os.path.join(os.path.dirname(HERE), "out", "variants.json"), "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
