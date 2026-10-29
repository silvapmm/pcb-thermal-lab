#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_muzychka_2003.py
@brief The numerical examples of Muzychka, Culham and Yovanovich (J. Electronic Packaging 125, 2003, 178-185) with the independent 3D solver and with the five models of the program.
@details Case 1 (a): a 300 x 300 x 10 mm plate, k = 10 W/mK, film h = 10 W/m2K on the bottom face (top insulated), ambient 25 C, two 25 x 25 mm sources, 10 W centred at (90, 90) mm and 15 W at (210, 210) mm;
         the paper gives the centroid and mean temperature of each source and the mean temperature of the bottom face (84.97, 80.56, 108.43, 101.81, 53.06 C by its solution, the last being the mean of the whole top face: 52.78 C of the bottom face plus Q t / (k A) = 0.28 K; 85.95, 80.20, 109.92, 101.26, 53.06 by the
         Fourier series of Culham and Yovanovich). Case 3: five 20 x 20 mm sources of 5 W in a cross at the centre of a 100 x 100 x 10 mm plate, k = 50 W/mK, h = 50 W/m2K, ambient 25 C: maximum temperature at the centre
         80.61 C and area-weighted mean source temperature 78.87 C. The layered models of the program represent such a plate as one copper layer of 10 mm with the conductivity of the plate on a laminate of 0.01 % of it (thin-plate approximation,
         Biot number h t / k = 0.01 to 0.1); the thickness of the case-3 plate is then varied from 0.1 to 10 mm to show where one temperature node through the thickness stops being a good idea. Run: .venv/bin/python research/effective-conductivity/scripts/study_muzychka_2003.py [--mesh-check] (from the repository root; about 2 minutes; --mesh-check adds 30 to 50 minutes).
"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "lib"))
import layered3d as L                                          # noqa: E402
from pcbthermal import Problem, SolverOptions, simulate        # noqa: E402
from pcbthermal.model import Materials                         # noqa: E402

AMB = 25.0
MODELS = ("fvm", "fdm", "solid3d", "lumped", "analytic")
CASES = {
    "1a": {"w": 300.0, "t": 10.0, "k": 10.0, "h": 10.0, "dx": 2.5, "sources": [((77.5, 77.5, 102.5, 102.5), 10.0), ((197.5, 197.5, 222.5, 222.5), 15.0)],
           "paper": {"centroid": [84.97, 108.43], "mean": [80.56, 101.81], "base": 53.06}, "paper_fourier": {"centroid": [85.95, 109.92], "mean": [80.20, 101.26]}},
    "3": {"w": 100.0, "t": 10.0, "k": 50.0, "h": 50.0, "dx": 1.0, "sources": [((40, 40, 60, 60), 5.0), ((20, 40, 40, 60), 5.0), ((60, 40, 80, 60), 5.0), ((40, 20, 60, 40), 5.0), ((40, 60, 60, 80), 5.0)],
          "paper": {"max_centre": 80.61, "mean_area": 78.87}},
}


def centroid_value(field, dx, cx, cy):
    """!
    @brief Value of a cell field at a point, the mean of the four cells around it (the centroids of the sources fall on cell corners).
    @param field Array (ny, nx).
    @param dx Cell size in mm.
    @param cx X of the point in mm.
    @param cy Y of the point in mm.
    @return float The value.
    """
    i, j = int(round(cx / dx)), int(round(cy / dx))
    return float(field[j - 1:j + 1, i - 1:i + 1].mean())


def independent(case, n_sub=6):
    """!
    @brief Source temperatures and base mean by the independent 3D solver.
    @param case Case dictionary.
    @param n_sub Sub-slabs through the plate.
    @return dict with centroid, mean (lists, C), area_mean (C, the area-weighted mean source temperature), base (C, the mean of the bottom face, equal to the ambient plus Q / (h A)), top_mean (C, the mean of the whole top face), the maximum surface temperature,
            thick_mean (list, C: the mean over each source of the temperature averaged through the thickness, the quantity one node per layer represents) and gradient (list, K: mean surface
            temperature of each source minus thick_mean) with bound (list, K: q'' t / (2 k), the gradient if all the heat of the source crossed the plate under it).
    """
    n = int(round(case["w"] / case["dx"]))
    rects = [tuple(v * 1e-3 for v in r) for r, _ in case["sources"]]
    pw = [p for _, p in case["sources"]]
    res = L.solve(case["dx"] * 1e-3, n, n, [(case["t"] * 1e-3, case["k"], n_sub)], rects, pw, 0.0, case["h"])
    cen = [AMB + centroid_value(res["surface_top"], case["dx"], (r[0] + r[2]) / 2 * 1e3, (r[1] + r[3]) / 2 * 1e3) for r in rects]
    dz = np.asarray(res["dz"])
    tbar = (res["T"] * dz[:, None, None]).sum(axis=0) / dz.sum()          # temperature averaged through the thickness
    xs = (np.arange(n) + 0.5) * case["dx"] * 1e-3
    masks = [(xs[None, :] > r[0]) & (xs[None, :] < r[2]) & (xs[:, None] > r[1]) & (xs[:, None] < r[3]) for r in rects]
    thick = [float(tbar[m].mean()) for m in masks]
    grad = [d["mean"] - t for d, t in zip(res["per_source"], thick)]
    bound = [p / ((r[2] - r[0]) * (r[3] - r[1])) * case["t"] * 1e-3 / (2 * case["k"]) for r, p in zip(rects, pw)]
    areas = [(r[2] - r[0]) * (r[3] - r[1]) for r in rects]
    area_mean = AMB + sum(a * d["mean"] for a, d in zip(areas, res["per_source"])) / sum(areas)   # the area-weighted mean source temperature of the paper's case 3
    return {"centroid": cen, "mean": [AMB + d["mean"] for d in res["per_source"]], "area_mean": area_mean, "base": AMB + res["mean_wall"], "top_mean": AMB + res["top_surface_mean"], "max": AMB + float(res["surface_top"].max()),
            "thick_mean": [AMB + t for t in thick], "gradient": grad, "bound": bound}


def program(case, model, cell_mm):
    """!
    @brief The same plate in one model of the program (one copper layer of the plate thickness and conductivity).
    @param case Case dictionary.
    @param model Model key.
    @param cell_mm Cell size in mm.
    @return dict with centroid, mean (lists, C) and max, or None when the model refuses the board.
    """
    # The board is the plate plus 0.01 % of laminate (1 um for 10 mm): a one-layer board of thickness 2 t, as in the first version of this study, adds t of
    # FR4 to the plate, a lateral path the real plate does not have (+9 % of conductance for k = 10) and, since the 3D solid builds the laminate of a
    # one-layer board, 10 mm of FR4 between the plate and the bottom film; 1 um of FR4 changes neither (0.02 % of the film resistance at h = 50)
    mat = Materials(k_copper=case["k"])
    p = Problem.new(case["w"], case["w"], layers=1, thickness_mm=1.0001 * case["t"], copper_um=case["t"] * 1e3, ambient=AMB, h_top=1e-6, h_bottom=case["h"], h_side=None, materials=mat)
    p.add_full_copper()
    for k, (r, pw) in enumerate(case["sources"]):
        p.add_heater(1, pw, rect=r, name=f"S{k}")
    try:
        res = simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm)).results[model]
    except Exception as exc:                                    # reported, not hidden
        print(f"  {model}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None
    T = np.asarray(res.T)[0]
    ny, nx = T.shape
    dxm = case["w"] / nx
    xs, ys = (np.arange(nx) + 0.5) * dxm, (np.arange(ny) + 0.5) * dxm
    means, cens = [], []
    for r, _ in case["sources"]:
        m = (xs[None, :] > r[0]) & (xs[None, :] < r[2]) & (ys[:, None] > r[1]) & (ys[:, None] < r[3])
        means.append(float(T[m].mean()))
        cens.append(centroid_value(T, dxm, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2))
    return {"centroid": cens, "mean": means, "max": float(T.max())}


def thickness_sweep(thicknesses=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0), models=("fvm", "fdm", "solid3d", "analytic")):
    """!
    @brief The plate of case 3 with growing thickness: rise of the centre of the cross in the models of the program against the independent 3D solver.
    @param thicknesses Plate thicknesses in mm.
    @param models Model keys.
    @return dict thickness -> {"independent": rise in K, model: rise in K}.
    """
    out = {}
    base = CASES["3"]
    for t in thicknesses:
        case = dict(base, t=t)
        ind = independent(case)
        ref = ind["centroid"][0] - AMB
        row = {"independent": ref, "gradient": ind["gradient"][0], "bound": ind["bound"][0]}
        for m in models:
            r = program(case, m, 1.0)
            row[m] = (r["centroid"][0] - AMB) if r else float("nan")
        out[t] = row
        print(f"  t = {t:g} mm: independent {ref:.2f} K (gradient under the centre source {row['gradient']:.2f} K = {100 * row['gradient'] / ref:.2f} %, bound q'' t / (2 k) {100 * row['bound'] / ref:.2f} %); "
              + ", ".join(f"{m} {row[m]:.2f} ({100 * (row[m] / ref - 1):+.2f} %)" for m in models), flush=True)
    return out


def mesh_check():
    """!
    @brief The independent solver on both cases with the cells halved and twice the sub-slabs, and the film test of the node: the FVM with the film in series with half the plate, 1 / (1/h + t / (2 k)).
    @details Case 1a on 1.25 mm cells with 12 sub-slabs takes most of the 30 to 50 minutes; run with --mesh-check.
    @return dict case -> {"fine": independent() on the fine mesh, "fvm_half_plate": program() with the film in series with half the plate}.
    """
    out = {}
    for name, (dx, cell) in (("1a", (1.25, 2.5)), ("3", (0.5, 1.0))):
        case = CASES[name]
        fine = independent(dict(case, dx=dx), n_sub=12)
        h_half = 1.0 / (1.0 / case["h"] + case["t"] * 1e-3 / (2.0 * case["k"]))
        half = program(dict(case, h=h_half), "fvm", cell)
        out[name] = {"fine": fine, "fvm_half_plate": half}
        print(f"  case {name}, cells {dx:g} mm and 12 sub-slabs: centroid {np.round(fine['centroid'], 2).tolist()[:2]}, mean {np.round(fine['mean'], 2).tolist()[:2]}, "
              f"max {fine['max']:.2f}, area-weighted mean {fine['area_mean']:.2f}; FVM with the film in series with half the plate: mean {np.round(half['mean'], 2).tolist()[:2]} "
              f"against the 3D thickness mean {np.round(fine['thick_mean'], 2).tolist()[:2]}", flush=True)
    return out


def main():
    """!
    @brief Print both cases and write out/muzychka_2003.json for the figures (with --mesh-check, also the mesh check and the film test of the node).
    @return None.
    """
    out = {}
    for name, case in CASES.items():
        ind = independent(case)
        out[name] = {"paper": case["paper"], "independent": ind, "program": {}}
        print(f"\nCase {name}: paper {case['paper']}")
        print(f"  independent 3D solver: centroid {np.round(ind['centroid'], 2).tolist()}, mean {np.round(ind['mean'], 2).tolist()}, bottom mean {ind['base']:.2f}, top-face mean {ind['top_mean']:.2f}, max {ind['max']:.2f}, area-weighted mean source temperature {ind['area_mean']:.2f}")
        print(f"  through-thickness mean over each source {np.round(ind['thick_mean'], 2).tolist()}; surface minus that mean {np.round(ind['gradient'], 2).tolist()} K against q'' t / (2 k) {np.round(ind['bound'], 2).tolist()} K")
        for m in MODELS:
            r = program(case, m, 2.5 if name == "1a" else 1.0)
            out[name]["program"][m] = r
            if r:
                print(f"  {m}: centroid {np.round(r['centroid'], 2).tolist()}, mean {np.round(r['mean'], 2).tolist()}, max {r['max']:.2f}", flush=True)
    print("\nCase 3 plate, growing thickness (rise of the centre of the cross):")
    out["thickness"] = thickness_sweep()
    if "--mesh-check" in sys.argv:
        print("\nMesh check of the independent solver, and the film of the node in series with half the plate:")
        out["mesh_check"] = mesh_check()
    (HERE.parent / "out").mkdir(exist_ok=True)
    (HERE.parent / "out" / "muzychka_2003.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
