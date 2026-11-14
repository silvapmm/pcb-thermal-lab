#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_stripes.py
@brief Study 3 of the finite-element extensions, the aligned case: the 20 mm board of `study_drawn_film.py` (`sq_stripes`: top layer stripes of 1.2 mm every 2.4 mm plus a 7.2 mm
       pad, bottom layer copper, 1.2 mm inset, 200 W/m2K, a 4 mm heater of 1 W) with the copper RESOLVED (every stripe edge a mesh line, elements of 0.4 to 0.2 mm; the centroid
       decides) against the program's FVM and FDM at 1, 0.5 and 0.25 mm; the plain board (copper 1.2 mm inside on both layers) as the control; the checkerboard sheet against sqrt(S1 S2).
@details Run from the repository root, one mode at a time (each under 2 GB):
         `research/independent-fem-edge/.venv-research/bin/python research/independent-fem-extensions/scripts/study_stripes.py fem stripes 0.4` (or `plain`, hf 0.2),
         `... checker`, then with the program's interpreter `.venv/bin/python .../study_stripes.py prog` and `... report`. Cache `out/s3.json`.
         The copper is NOT mixed by area fraction in an element: the truth must not share the cell-fill assumption under test (README 7.1, finding 2).
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "independent-fem-edge", "lib"))
import numpy as np                                                       # noqa: E402

OUT = os.path.join(HERE, "..", "out", "s3.json")
MM = 1e-3


def load():
    """!
    @brief Read the cache.
    @return dict.
    """
    return json.load(open(OUT)) if os.path.exists(OUT) else {}


def save(res):
    """!
    @brief Write the cache.
    @param res dict.
    @return None.
    """
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=1)


def stripe_board(kind, hf, n_gap=12, h_side=200.0):
    """!
    @brief The finite-element board of `sq_stripes` ('stripes') or the plain control ('plain': copper 1.2 mm inside on both layers).
    @param kind 'stripes' or 'plain'.
    @param hf Plan size in mm (uniform over the whole board: the copper is resolved everywhere).
    @param n_gap Elements across the laminate gap.
    @param h_side Edge film W/m2K.
    @return Board.
    """
    import board
    import cases
    import mesh2d
    sys.path.insert(0, os.path.join(ROOT, "research", "imported-copper-edge-film", "scripts"))
    rect = cases.rect
    if kind == "stripes":
        polys, y = [], 1.2
        while y < 18.8 - 1e-9:
            polys.append(rect(1.2, y, 18.8, min(y + 1.2, 18.8)))
            y += 2.4
        polys.append(rect(6.4, 6.4, 13.6, 13.6))
        top = polys
        brk = sorted({1.2 + 1.2 * i for i in range(0, 15)} | {18.8, 6.4, 13.6, 8.0, 12.0})
    else:
        top = rect(1.2, 1.2, 18.8, 18.8)
        brk = [1.2, 8.0, 12.0, 18.8]
    xn = cases.axis(20.0, brk, [(0.0, 20.0)], hf, 1.3, hf)
    plan = mesh2d.tensor(xn, xn)
    return board.Board(plan, 2, board_t=1.6e-3, k_xy=0.9, k_z=0.3, n_gap=n_gap, h_top=10.0, h_bottom=10.0, h_side=h_side, copper=[top, rect(1.2, 1.2, 18.8, 18.8)],
                       heaters=[(rect(8, 8, 12, 12), 1.0)])


def fem(kind, hf):
    """!
    @brief One finite-element solve (2 GB guard) of the stripes or the control board.
    @param kind 'stripes' or 'plain'.
    @param hf Plan size in mm.
    @return None.
    """
    res = load()
    key = f"{kind}|{hf}"
    if key in res:
        print(key, "cached", res[key])
        return
    b = stripe_board(kind, hf)
    m, _ = b.build()
    n = m.nodes.shape[0]
    est = n * (46000.0 if n <= 30000 else 8500.0) / 1e9
    print(f"{key}: {n} nodes, {m.elems.shape[0]} elements, estimate {est:.2f} GB", flush=True)
    if est > 2.0:
        print("refused: above 2 GB")
        return
    t0 = time.time()
    r = b.solve(direct_max=30000)
    res[key] = {"heater_mean": r["heater_mean"], "tmax": r["tmax"], "balance": r["balance"], "n": r["n"], "solver": r["solver"], "peak_gb": r["peak_gb"], "seconds": time.time() - t0}
    print(key, {k: (round(v, 5) if isinstance(v, float) else v) for k, v in res[key].items()}, flush=True)
    save(res)


def checker():
    """!
    @brief A checkerboard sheet (copper and laminate squares, N x N, 4 elements per square) between two stiff faces and insulated sides against sqrt(S1 S2) of the
           infinite array (Dykhne's result, quoted from memory, status M: it is NOT used as a reference until its source is opened; the number is a plausibility check).
    @return None.
    """
    import sheets
    k1, k2, t = 385.0, 0.9, 35e-6
    res = load()
    for N in (4, 8, 16):
        a = 1e-3
        xn = np.linspace(0, N * a, 4 * N + 1)
        g = sheets.conductance(xn, xn, lambda c: ((np.floor(c[:, 0] / a).astype(int) + np.floor(c[:, 1] / a).astype(int)) % 2 == 0), k1, k2, t)
        s_eff = g                                                       # square sheet: S = G (width = length)
        print(f"checkerboard N={N}: S_eff {s_eff:.6e} W/K, sqrt(S1 S2) {np.sqrt(k1 * k2) * t:.6e}, ratio {s_eff / (np.sqrt(k1 * k2) * t):.4f}", flush=True)
        res[f"checker|{N}"] = s_eff / (np.sqrt(k1 * k2) * t)
    save(res)


def prog():
    """!
    @brief The program's FVM and FDM on `sq_stripes` and the plain `sq_in` at 200 W/m2K, aligned (no turn, no shift), cells 1, 0.5 and 0.25 mm: heater mean rise.
    @return None.
    """
    import logging
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "research", "imported-copper-edge-film", "scripts"))
    import study_drawn_film as sd
    from pcbthermal import SolverOptions, analysis, simulate
    logging.disable(logging.WARNING)
    res = load()
    for name, kind in (("sq_stripes", "stripes"), ("sq_in", "plain")):
        spec = sd.CASES[name]
        for cell in (1.0, 0.5, 0.25):
            for model in ("fvm", "fdm"):
                key = f"P|{kind}|{cell}|{model}"
                if key in res:
                    continue
                p = sd.build(spec, 200.0, 0.0, 0.0)
                r = simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model]
                res[key] = {"heater_mean": float(analysis.heater_stats(r, p)[0]["t_mean"] - p.board.ambient), "tmax": float(r.t_max - p.board.ambient)}
                if model == "fvm":
                    res[key]["heater_mean_weights"] = sd.heater_rise(p, cell)[0]
                print(key, res[key], flush=True)
                save(res)


def report():
    """!
    @brief Print the tables: finite elements by mesh and the program's error against the finest.
    @return None.
    """
    import refine
    res = load()
    for kind in ("plain", "stripes"):
        vals = [(hf, res[f"{kind}|{hf}"]["heater_mean"]) for hf in (0.4, 0.2, 0.1) if f"{kind}|{hf}" in res]
        if not vals:
            continue
        line = f"{kind}: FEM heater mean " + " / ".join(f"{h}:{v:.4f}" for h, v in vals)
        if len(vals) == 3:
            r = refine.richardson([v for _, v in vals])
            line += f"  order {r['p']:.2f} ext {r['ext']:.4f} gci {100 * r['gci']:.2f}%"
        print(line)
        ref = vals[-1][1]
        for model in ("fvm", "fdm"):
            row = []
            for cell in (1.0, 0.5, 0.25):
                o = res.get(f"P|{kind}|{cell}|{model}")
                if o:
                    v = o.get("heater_mean_weights", o["heater_mean"]) if model == "fvm" else o["heater_mean"]
                    row.append(f"@{cell}: {v:.4f} ({100 * (v / ref - 1):+.2f}%)")
            print(f"   program {model}: " + " | ".join(row))
    for N in (4, 8, 16):
        if f"checker|{N}" in res:
            print(f"checkerboard N={N}: S_eff / sqrt(S1 S2) = {res[f'checker|{N}']:.4f}")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "fem":
        fem(sys.argv[2], float(sys.argv[3]))
    elif mode == "checker":
        checker()
    elif mode == "prog":
        prog()
    elif mode == "report":
        report()
