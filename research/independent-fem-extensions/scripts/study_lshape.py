#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_lshape.py
@brief Study 4 of the finite-element extensions: the L outline (20 mm arms, 8 mm wide, two layers, copper to the wall and 1.2 mm inside, 200 W/m2K, a 2.4 mm heater of 1 W in the
       lower arm) as a finite-element board against the program's FVM and FDM at 1, 0.5 and 0.25 mm, aligned with the grid. Mirror check: the board mirrored about its diagonal.
@details Run from the repository root, one mode at a time (each under 2 GB):
         `research/independent-fem-edge/.venv-research/bin/python research/independent-fem-extensions/scripts/study_lshape.py fem wall 0.2` (`wall` or `in`, hf in mm; add `mirror`),
         then with the program's interpreter `.venv/bin/python .../study_lshape.py prog` and `... report`. Cache `out/s4.json`. Rises over the ambient, K.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "independent-fem-edge", "lib"))
import numpy as np                                                       # noqa: E402

OUT = os.path.join(HERE, "..", "out", "s4.json")
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


def l_board(kind, hf, mirror=False, n_gap=6, hmax=0.8, h_side=200.0):
    """!
    @brief The L board: tensor plan with the notch [8, 20] x [8, 20] mm removed, fine zones at the walls, the corner and the heater.
    @param kind 'wall' (copper to the wall) or 'in' (copper 1.2 mm inside, on both layers).
    @param hf Fine plan size in mm.
    @param mirror True: the same board mirrored about the diagonal x = y (heater and copper included).
    @param n_gap Elements per gap.
    @param hmax Largest plan size in mm.
    @param h_side Wall film W/m2K.
    @return Board.
    """
    import board
    import cases
    import mesh2d
    rect = cases.rect
    ax = cases.axis(20.0, [1.2, 2.8, 5.2, 6.8, 8.0, 8.8, 11.2, 18.8], [(0, 1.8), (2.4, 5.6), (6.2, 9.4), (18.2, 20)], hf, 1.3, hmax)
    plan = mesh2d.tensor(ax, ax)
    c = plan.centroids() / MM
    plan = plan.remove((c[:, 0] > 8.0) & (c[:, 1] > 8.0))
    heater = rect(8.8, 2.8, 11.2, 5.2)
    cu = None if kind == "wall" else np.array([[1.2, 1.2], [18.8, 1.2], [18.8, 6.8], [6.8, 6.8], [6.8, 18.8], [1.2, 18.8]]) * MM
    if mirror:
        plan = mesh2d.Quad2D(plan.xy[:, ::-1].copy(), plan.quads[:, ::-1].copy(), plan.tag)          # reversing the quad order keeps it counter-clockwise
        heater = heater[:, ::-1].copy()
        cu = None if cu is None else cu[:, ::-1].copy()
    return board.Board(plan, 2, board_t=1.6e-3, k_xy=0.9, k_z=0.3, n_gap=n_gap, h_top=10.0, h_bottom=10.0, h_side=h_side, copper=cu, heaters=[(heater, 1.0)])


def fem(kind, hf, mirror):
    """!
    @brief One finite-element solve (2 GB guard).
    @param kind 'wall' or 'in'.
    @param hf Fine plan size in mm.
    @param mirror True for the mirrored board.
    @return None.
    """
    res = load()
    key = f"{kind}|{hf}{'|mirror' if mirror else ''}"
    if key in res:
        print(key, "cached", res[key])
        return
    b = l_board(kind, hf, mirror)
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
    print(key, {k: (round(v, 6) if isinstance(v, float) else v) for k, v in res[key].items()}, flush=True)
    save(res)


def prog():
    """!
    @brief The program's FVM (heater mean by the network weights) and FDM (heater_stats) on `L_wall` and `L_in`, aligned, 200 W/m2K.
    @return None.
    """
    import logging
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "research", "imported-copper-edge-film", "scripts"))
    import study_drawn_film as sd
    from pcbthermal import SolverOptions, analysis, simulate
    logging.disable(logging.WARNING)
    res = load()
    for name, kind in (("L_wall", "wall"), ("L_in", "in")):
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
    @brief Print the tables.
    @return None.
    """
    import refine
    res = load()
    for kind in ("wall", "in"):
        vals = [(hf, res[f"{kind}|{hf}"]["heater_mean"]) for hf in (0.4, 0.2, 0.1) if f"{kind}|{hf}" in res]
        if not vals:
            continue
        line = f"L {kind}: FEM heater mean " + " / ".join(f"{h}:{v:.4f}" for h, v in vals)
        if len(vals) == 3:
            r = refine.richardson([v for _, v in vals])
            line += f"  order {r['p']:.2f} ext {r['ext']:.4f} gci {100 * r['gci']:.2f}%"
        print(line)
        for hf, v in vals:
            mk = f"{kind}|{hf}|mirror"
            if mk in res:
                print(f"   mirror check hf {hf}: {res[mk]['heater_mean']:.9f} vs {v:.9f} (diff {abs(res[mk]['heater_mean'] - v):.2e})")
        ref = vals[-1][1]
        for model in ("fvm", "fdm"):
            row = []
            for cell in (1.0, 0.5, 0.25):
                o = res.get(f"P|{kind}|{cell}|{model}")
                if o:
                    v = o.get("heater_mean_weights", o["heater_mean"]) if model == "fvm" else o["heater_mean"]
                    row.append(f"@{cell}: {v:.4f} ({100 * (v / ref - 1):+.2f}%)")
            print(f"   program {model}: " + " | ".join(row))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "fem":
        sys.path.insert(0, os.path.join(HERE, "..", "lib"))
        fem(sys.argv[2], float(sys.argv[3]), "mirror" in sys.argv[4:])
    elif mode == "prog":
        prog()
    elif mode == "report":
        sys.path.insert(0, os.path.join(HERE, "..", "..", "independent-fem-edge", "lib"))
        report()
