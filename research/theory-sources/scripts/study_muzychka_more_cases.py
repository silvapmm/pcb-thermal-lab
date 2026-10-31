#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_muzychka_more_cases.py
@brief F2: the two cases of Muzychka, Culham and Yovanovich (2003) that the earlier study did not run, with the independent 3D solver and the models of the program.
@details Case 1 (b), Table 2: the plate of case 1 (a) (300 x 300 x 10 mm, k 10, h = 10 W/m2K on the bottom, 25 C) with a 2 mm layer of k = 350 W/mK on top, sources 10 W at (90, 90) and
15 W at (210, 210), 25 x 25 mm; paper centroids 56.55 and 59.94 C, means 56.05 and 59.19 C, base mean 53.06 C (Culham and Yovanovich Fourier series: 56.63 and 60.08, means 56.03 and 59.16).
Case 2, Tables 3 and 4: the baseplate of a heat sink, 50 x 50 x 10 mm, k 150 W/mK, h = 400 W/m2K on the bottom, four 10 x 10 mm sources (10 W at (12.5, 12.5), 25 W at (37.5, 12.5), 20 W at
(12.5, 37.5), 15 W at (37.5, 37.5) mm; the ambient is not printed in the extracted text, 25 C is assumed as in the other cases); paper centroids 97.40, 103.82, 101.28, 99.94 C and means 96.85, 102.33,
100.10, 99.07 C. The model of the program is one layer of the plate (case 2), or a top layer of the spreader on a dielectric gap of 10 mm with k 10 W/mK both ways (case 1 (b)).
Run from the repository root: .venv/bin/python research/theory-sources/scripts/study_muzychka_more_cases.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research", "effective-conductivity", "lib"))
import layered3d as L  # noqa: E402
from pcbthermal import Problem, SolverOptions, simulate  # noqa: E402
from pcbthermal.model import Materials  # noqa: E402

AMB = 25.0
MODELS = ("fvm", "fdm", "solid3d", "analytic", "lumped")


def sq(xc, yc, c):
    """!
    @brief Square of side c centred at a point.
    @param xc X of the centre in mm.
    @param yc Y of the centre in mm.
    @param c Side in mm.
    @return Tuple (x0, y0, x1, y1) in mm.
    """
    return (xc - c / 2, yc - c / 2, xc + c / 2, yc + c / 2)


CASES = {
    "1b": {"w": 300.0, "dx": 2.5, "h": 10.0, "slabs": [(2.0, 350.0, 4), (10.0, 10.0, 6)],
           "sources": [(sq(90, 90, 25), 10.0), (sq(210, 210, 25), 15.0)],
           "paper": {"centroid": [56.55, 59.94], "mean": [56.05, 59.19], "base": 53.06}, "fourier": {"centroid": [56.63, 60.08], "mean": [56.03, 59.16]}},
    "2": {"w": 50.0, "dx": 0.5, "h": 400.0, "slabs": [(10.0, 150.0, 8)],
          "sources": [(sq(12.5, 12.5, 10), 10.0), (sq(37.5, 12.5, 10), 25.0), (sq(12.5, 37.5, 10), 20.0), (sq(37.5, 37.5, 10), 15.0)],
          "paper": {"centroid": [97.40, 103.82, 101.28, 99.94], "mean": [96.85, 102.33, 100.10, 99.07]}},
}


def centroid_value(field, dx, cx, cy):
    """!
    @brief Mean of the four cells around a point (the centroids of the sources fall on cell corners).
    @param field Array (ny, nx).
    @param dx Cell size in mm.
    @param cx X in mm.
    @param cy Y in mm.
    @return float The value.
    """
    i, j = int(round(cx / dx)), int(round(cy / dx))
    return float(field[j - 1:j + 1, i - 1:i + 1].mean())


def independent(case):
    """!
    @brief Centroid and mean source temperatures by the independent 3D solver.
    @param case Case dictionary.
    @return Dict with centroid, mean (lists in C) and base (mean of the bottom face in C).
    """
    n = int(round(case["w"] / case["dx"]))
    rects = [tuple(v * 1e-3 for v in r) for r, _ in case["sources"]]
    res = L.solve(case["dx"] * 1e-3, n, n, [(t * 1e-3, k, s) for t, k, s in case["slabs"]], rects, [p for _, p in case["sources"]], 0.0, case["h"])
    return {"centroid": [AMB + centroid_value(res["surface_top"], case["dx"], (r[0] + r[2]) / 2e-3, (r[1] + r[3]) / 2e-3) for r in rects],
            "mean": [AMB + d["mean"] for d in res["per_source"]], "base": AMB + res["mean_wall"]}


def program(case, model, cell_mm):
    """!
    @brief The same board in one model of the program.
    @param case Case dictionary.
    @param model Model key.
    @param cell_mm Cell size in mm.
    @return Dict with centroid and mean lists in C, or None when the model refuses the board.
    """
    slabs = case["slabs"]
    if len(slabs) == 1:                                           # a plate: one copper layer with the plate conductivity on a laminate of 0.01 % of it
        t, k, _ = slabs[0]
        p = Problem.new(case["w"], case["w"], layers=1, thickness_mm=1.0001 * t, copper_um=t * 1e3, ambient=AMB, h_top=1e-6, h_bottom=case["h"], h_side=None,
                        materials=Materials(k_copper=k))
    else:                                                          # a spreader (copper layer 1) over a dielectric gap of the substrate; a 1 um copper layer carries the bottom face
        (t1, k1, _), (t2, k2, _) = slabs
        mat = Materials(k_copper=k1, k_fr4_through=k2, k_fr4_inplane=k2)
        p = Problem.new(case["w"], case["w"], layers=2, thickness_mm=t1 + t2 + 0.001, copper_um=t1 * 1e3, ambient=AMB, h_top=1e-6, h_bottom=case["h"], h_side=None, materials=mat)
        p.board.copper_thickness = [t1 * 1e-3, 1e-6]
    p.add_full_copper(layers=[1] if len(slabs) > 1 else None)
    if len(slabs) > 1:
        p.add_full_copper(layers=[2], fill=1.0)
    for i, (r, pw) in enumerate(case["sources"]):
        p.add_heater(1, pw, rect=r, name=f"S{i}")
    try:
        res = simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm)).results[model]
    except Exception as exc:                                       # reported, not hidden
        print(f"  {model}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None
    t_map = np.asarray(res.T)[0]
    ny, nx = t_map.shape
    dxm = case["w"] / nx
    xs, ys = (np.arange(nx) + 0.5) * dxm, (np.arange(ny) + 0.5) * dxm
    means, cens = [], []
    for r, _ in case["sources"]:
        m = (xs[None, :] > r[0]) & (xs[None, :] < r[2]) & (ys[:, None] > r[1]) & (ys[:, None] < r[3])
        means.append(float(t_map[m].mean()))
        cens.append(centroid_value(t_map, dxm, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2))
    return {"centroid": cens, "mean": means}


def main():
    """!
    @brief Print both cases: the paper, the independent solver and the models of the program.
    @return None.
    """
    for name, case in CASES.items():
        print(f"\nCase {name}: paper {case['paper']}" + (f", Fourier series {case['fourier']}" if "fourier" in case else ""))
        ind = independent(case)
        print("  independent 3D solver: centroid %s, mean %s, bottom mean %.2f" % (np.round(ind["centroid"], 2).tolist(), np.round(ind["mean"], 2).tolist(), ind["base"]))
        for m in MODELS:
            r = program(case, m, 2.5 if name == "1b" else 1.0)
            if r:
                print("  %s: centroid %s, mean %s" % (m, np.round(r["centroid"], 2).tolist(), np.round(r["mean"], 2).tolist()), flush=True)


if __name__ == "__main__":
    main()
