#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_real_board.py
@brief Q7: what the rule that combines zones does on a real board drawn as a crowd of solid polygons (the Stormduino from its KiCad file: tracks, pads, zone fills).
@details Question answered: on copper that is a union of hundreds of overlapping and abutting polygons, how far is each rule from the resolved copper (the geometric union, the independent solver),
         and how much does the old rule lose? Windows of 24 x 24 mm of the two-layer board (1.6 mm, 35 um copper, laminate 0.3 W/mK isotropic as in the reference), a 6 x 6 mm part of 1 W on the top
         layer, cells of 0.5 and 1.0 mm, rules max_cell (the program as it is: taken from the unmodified program in a separate process), max_point (prototype), prob, sum_clip, priority; the copper
         area of the cell field is printed too. The reference is the independent solver at 0.25 mm on the same polygons. Needs the fetched Stormduino (see lib/real_board.py).
         Run from the repository root: .venv/bin/python research/zone-union/scripts/study_real_board.py [develop|variant|reference|fills|decompose|report]; out/real_board_*.json, out/study_real_board.txt.
"""

import _bootstrap  # noqa: F401  (import paths)

import json
import sys

import numpy as np

import variant
from paths import OUT

MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")
CELLS = (1.0, 0.5)
SIZE = 24.0
## Windows (x0, y0 of the lower left corner in board mm) and the part position inside the window; chosen by the copper they hold (script, see pick_windows)
PART = (9.0, 9.0, 15.0, 15.0)
RULES = ("max_cell", "max_point", "prob", "sum_clip", "priority")


def pick_windows(objs, bbox, n=3):
    """!
    @brief Three windows of the board: the densest copper, a middle one and a sparse one, by the copper area fraction of the top layer in the window.
    @param objs Objects by layer.
    @param bbox Bounding box (xmin, ymin, xmax, ymax) of the objects.
    @param n Number of windows.
    @return list of (x0, y0) snapped to 1 mm.
    """
    import real_board
    import reference
    cands = []
    for x0 in np.arange(np.floor(bbox[0]), bbox[2] - SIZE, 8.0):
        for y0 in np.arange(np.floor(bbox[1]), bbox[3] - SIZE, 8.0):
            w = real_board.window(objs, x0, y0, SIZE)
            f = reference.raster([q * 1e-3 for q in w[0]], 24, 24, 1e-3, 2).mean()
            cands.append((f, float(x0), float(y0), len(w[0])))
    cands.sort()
    # Keep windows that hold at least some copper and several objects, spread over the density range
    cands = [c for c in cands if c[3] > 20]
    pick = [cands[-1], cands[len(cands) // 2], cands[max(len(cands) // 6, 0)]][:n]
    return [(c[1], c[2], c[0]) for c in pick]


def build(w, layers_polys):
    """!
    @brief The Problem of a window: zones for every polygon (solid), a 6 x 6 mm part of 1 W on the top layer.
    @param w Window polygons by layer (mm).
    @param layers_polys unused placeholder kept for symmetry (None).
    @return Problem.
    """
    from pcbthermal import Problem
    from pcbthermal.model import Materials
    p = Problem.new(width_mm=SIZE, height_mm=SIZE, layers=2, thickness_mm=1.6, copper_um=35.0, h_top=10.0, h_bottom=10.0, h_side=None,
                    materials=Materials(k_fr4_through=0.3, k_fr4_inplane=0.3))
    for k, polys in w.items():
        for q in polys:
            p.add_zone(k + 1, polygon=q.tolist())
    p.add_heater(1, 1.0, rect=PART)
    return p


def peaks(p, cell, rule=None):
    """!
    @brief Peak rise of every model.
    @param p Problem.
    @param cell Cell (mm).
    @param rule Zone rule to set (variant) or None.
    @return dict.
    """
    from pcbthermal import SolverOptions, simulate
    if rule:
        variant.set_rule(rule)
    out = {}
    for m in MODELS:
        try:
            out[m] = round(simulate(p, SolverOptions(models=(m,), cell_mm=cell)).results[m].t_max - p.board.ambient, 4)
        except Exception as e:                                   # reported, not hidden
            out[m] = type(e).__name__
    return out


def windows():
    """!
    @brief The windows of the study (computed once from the board).
    @return tuple (objs, list of (x0, y0, fraction)).
    """
    import real_board
    objs, bbox = real_board.objects(real_board.read())
    return objs, pick_windows(objs, bbox)


def run(mode):
    """!
    @brief Run the models (develop = the program as it is; variant = every rule) or the reference.
    @param mode develop, variant or reference.
    @return None (writes out/real_board_<mode>.json).
    """
    variant.use(mode == "variant")
    import real_board
    import reference
    objs, wins = windows()
    res = {}
    for x0, y0, frac in wins:
        key = f"window x={x0:.0f} y={y0:.0f}"
        w = real_board.window(objs, x0, y0, SIZE)
        p = build(w, None)
        res[key] = {"copper fraction (top, 1 mm raster)": frac, "objects": [len(w[0]), len(w[1])]}
        if mode == "reference":
            r = reference.reference_rise(p, {k: [q * 1e-3 for q in v] for k, v in w.items()}, 0.25, n_lam=4)
            res[key]["reference"] = {"max": float(r["max"]), "mean": float(r["mean"]), "fill": [float(r["fill"][k].mean()) for k in (0, 1)]}
        else:
            for cell in CELLS:
                if mode == "variant":
                    res[key][str(cell)] = {r: peaks(p, cell, r) for r in RULES}
                else:
                    res[key][str(cell)] = {"develop": peaks(p, cell)}
        print("done", key, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"real_board_{mode}.json").write_text(json.dumps(res, indent=1))


def fills():
    """!
    @brief Mean copper fill of the two layers of every window under each rule (1 mm and 0.5 mm cells) against the resolved copper.
    @return dict.
    """
    variant.use(True)
    import real_board
    import reference
    import zone_rules as zr
    objs, wins = windows()
    out = {}
    for x0, y0, _ in wins:
        w = real_board.window(objs, x0, y0, SIZE)
        p = build(w, None)
        key = f"window x={x0:.0f} y={y0:.0f}"
        out[key] = {}
        for cell in CELLS:
            n = int(round(SIZE / cell))
            dx = SIZE * 1e-3 / n
            row = {}
            for r in RULES:
                f = zr.combine(p.zones, 2, n, n, dx, dx, 4, r)
                row[r] = [float(f[0].mean()), float(f[1].mean())]
            fine = [reference.raster([q * 1e-3 for q in w[k]], 96, 96, 0.25e-3, 4).mean() for k in (0, 1)]
            row["resolved"] = [float(v) for v in fine]
            out[key][str(cell)] = row
    (OUT / "real_board_fills.json").write_text(json.dumps(out, indent=1))
    return out


def decompose():
    """!
    @brief Where the error of the models on the real board comes from (review): the independent solver run on the program's own cell fill (the cells of 1 and 0.5 mm, old rule and union,
           laminate resolved in 4 slabs) against the resolved reference, and the FVM against that same coarse solver; the peak and the mean over the part; the fill of the cell
           where the coarse solver is hottest; and the convergence of the reference itself (0.25 mm and 0.125 mm, 2 slabs per dielectric gap).
    @details Added by the review of the folder. The coarse solver shares the cell fill of the program but not its layered idealisation (one node per copper layer holding half
             of the laminate), so: reference -> coarse solver = the scalar fill at the size of the cell (the mapping); coarse solver -> FVM = the layered idealisation;
             old -> union = the rule. Memory about 1.5 GB (the 0.125 mm reference).
    @return None (prints, writes out/real_board_decompose.json).
    """
    variant.use(True)
    import layered3d as L3
    import real_board
    import reference
    import zone_rules as zr
    from pcbthermal import SolverOptions, simulate
    objs, wins = windows()
    out = {}
    for x0, y0, _ in wins:
        w = real_board.window(objs, x0, y0, SIZE)
        p = build(w, None)
        key = f"window x={x0:.0f} y={y0:.0f}"
        polys = {k: [q * 1e-3 for q in v] for k, v in w.items()}
        row = {"reference": {}}
        for dx in (0.25, 0.125):
            r = reference.reference_rise(p, polys, dx, n_gap=2)
            row["reference"][f"{dx}/2"] = {"max": float(r["max"]), "mean": float(r["mean"])}
        kc, kl = p.board.materials.k_copper, 0.3
        part = tuple(np.array(PART) * 1e-3)
        for cell in CELLS:
            n = int(round(SIZE / cell))
            d = SIZE * 1e-3 / n
            xs = (np.arange(n) + 0.5) * cell
            under = (xs[None, :] > PART[0]) & (xs[None, :] < PART[2]) & (xs[:, None] > PART[1]) & (xs[:, None] < PART[3])
            for rule in ("max_cell", "max_point"):
                f = zr.combine(p.zones, 2, n, n, d, d, 4, rule)
                slabs = [(35e-6, kl + f[0] * (kc - kl), 1), (1.6e-3 - 70e-6, kl, 4), (35e-6, kl + f[1] * (kc - kl), 1)]
                c = L3.solve(d, n, n, slabs, part, 1.0, p.board.h_top, p.board.h_bottom, film_under_source=True)
                hot = np.unravel_index(np.where(c["mask_source"], c["T"][0], -np.inf).argmax(), (n, n))
                variant.set_rule(rule)
                T = np.asarray(simulate(p, SolverOptions(models=("fvm",), cell_mm=cell)).results["fvm"].T)[0] - p.board.ambient
                row[f"{cell}/{rule}"] = {"coarse max": float(c["cell_max_source"]), "coarse mean": float(c["cell_mean_source"]),
                                         "fill at the coarse hot cell": float(f[0][hot]), "fvm max": float(T.max()), "fvm mean": float(T[under].mean())}
        out[key] = row
        print(key, json.dumps(row), flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "real_board_decompose.json").write_text(json.dumps(out, indent=1))


def report():
    """!
    @brief Print the tables from the saved files.
    @return None.
    """
    dev = json.loads((OUT / "real_board_develop.json").read_text())
    var = json.loads((OUT / "real_board_variant.json").read_text())
    ref = json.loads((OUT / "real_board_reference.json").read_text())
    fl = json.loads((OUT / "real_board_fills.json").read_text())
    lines = []

    def out(s=""):
        """!
        @brief Print and keep a line.
        @param s Text.
        @return None.
        """
        print(s)
        lines.append(s)

    for key in var:
        rf = ref[key]["reference"]
        out(f"\n{key}: objects top/bottom {var[key]['objects']}, resolved copper fraction top/bottom {rf['fill'][0]:.3f}/{rf['fill'][1]:.3f}, independent solver {rf['max']:.2f} K (mean over the part {rf['mean']:.2f} K)")
        for cell in CELLS:
            c = str(cell)
            out(f"  cells {cell} mm: copper fraction top/bottom  " + "  ".join(f"{r}: {fl[key][c][r][0]:.3f}/{fl[key][c][r][1]:.3f}" for r in RULES))
            out(f"    error of the peak rise against the independent solver (%), old rule = unmodified program")
            out(f"    {'rule':10s}" + "".join(f"{m:>10s}" for m in MODELS))
            out(f"    {'old':10s}" + "".join(f"{100 * (dev[key][c]['develop'][m] / rf['max'] - 1):+10.2f}" for m in MODELS))
            for r in RULES[1:]:
                out(f"    {r:10s}" + "".join(f"{100 * (var[key][c][r][m] / rf['max'] - 1):+10.2f}" if isinstance(var[key][c][r][m], float) else f"{'-':>10s}" for m in MODELS))
    (OUT / "study_real_board.txt").write_text("\n".join(lines))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if mode in ("develop", "variant", "reference"):
        run(mode)
    elif mode == "fills":
        fills()
    elif mode == "decompose":
        decompose()
    else:
        sys.path.insert(0, str(variant.build()))
        report()
