#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_hollow_barrel.py
@brief Study 1 of the finite-element extensions: is the program's via (barrel length d + 0.5 t_cu, Peaceman well) right for a HOLLOW plated barrel of 25 um (open, resin
       or copper core), single vias at 0.16 and 3 mm from the wall (1a) and a 3 x 3 array (1b), against conforming finite elements with rings across the wall?
@details Run from the repository root, ONE mode at a time (each under 2 GB):
         `research/independent-fem-edge/.venv-research/bin/python research/independent-fem-extensions/scripts/study_hollow_barrel.py fem 1a 0.2` (or `1b 0.1`, ...),
         `.../study_hollow_barrel.py checks`, then with the program's interpreter
         `.venv/bin/python research/independent-fem-extensions/scripts/study_hollow_barrel.py prog 1a` and `... report`.
         The effect E is the hottest top-face rise with the via copper OFF minus ON on the SAME mesh (the mesh effect cancels, as 3(b) of independent-fem-edge).
         Results are cached in `research/independent-fem-extensions/out/s1.json`.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import numpy as np                                                       # noqa: E402

import hollow                                                            # noqa: E402

OUT = os.path.join(HERE, "..", "out", "s1.json")
CORES = {"open": "open", "resin": 0.3, "copper": 385.0}
ARRAY = [(x, y) for x in (6.0, 7.0, 8.0) for y in (4.0, 5.0)]            # 3 x 3 at 1 mm pitch, the middle row on y = 5 (the half domain keeps two rows)


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


def solve(b, label):
    """!
    @brief Solve with the 2 GB rule (direct up to 30 000 unknowns, CG + AMG above) and print the guard line.
    @param b Board.
    @param label Text for the log.
    @return dict of the result (tmax, balance, n, solver, peak_gb).
    """
    m, _ = b.build()
    n = m.nodes.shape[0]
    print(f"  {label}: {n} nodes, {m.elems.shape[0]} elements", flush=True)
    t = time.time()
    r = b.solve(direct_max=30000)
    print(f"  {label}: tmax {r['tmax']:.5f} K balance {r['balance']:.12f} {r['solver']} n {r['n']} peak {r['peak_gb']:.2f} GB {time.time() - t:.0f} s", flush=True)
    return {"tmax": r["tmax"], "balance": r["balance"], "n": r["n"], "solver": r["solver"], "peak": r["peak_gb"]}


def fem_case(kind, hf, res, h_list=(200.0, 1000.0), cores=("open", "resin", "copper"), dists=(0.16, 3.0), **kw):
    """!
    @brief The finite-element runs of one case and mesh size: the baseline (via copper off) and every core.
    @param kind '1a' (single vias) or '1b' (the 3 x 3 array).
    @param hf Fine plan size in mm.
    @param res Cache dict (updated and saved).
    @param h_list Wall films.
    @param cores Core names.
    @param dists Distances from the wall (1a only).
    @param kw Passed to `hollow.strong_board` (n_wall, n_side_via ...).
    @return None.
    """
    tag = "".join(f"{k}{v}" for k, v in kw.items())
    for d in (dists if kind == "1a" else (None,)):
        vias = [(10.0 - d, 5.0)] if kind == "1a" else ARRAY
        for h in h_list:
            base_key = f"{kind}|{d}|{h}|{hf}|base|{tag}"
            if base_key not in res:
                b = hollow.strong_board(h, vias, hf=hf, core=0.3, **kw)          # the mesh of the resin core, via copper off below
                b.vias = []
                res[base_key] = solve(b, base_key)
                save(res)
            for core in cores:
                key = f"{kind}|{d}|{h}|{hf}|{core}|{tag}"
                if key in res:
                    continue
                b = hollow.strong_board(h, vias, hf=hf, core=CORES[core], **kw)
                res[key] = solve(b, key)
                res[key]["E"] = res[base_key]["tmax"] - res[key]["tmax"]
                print(f"  E({core}) = {res[key]['E']:.5f} K", flush=True)
                save(res)


def checks():
    """!
    @brief Checks (i) to (iii) of the plan at hf 0.2 mm: copper core equals the solid cylinder, the barrel area against the closed form (a column solve), wall elements 2 / 3 / 4.
    @return None.
    """
    import fem
    import mesh2d
    res = load()
    # (i) core of copper with r_in set against the solid cylinder of 3(b), the same plan except for the ring levels: both read the copper on the SAME footprint
    for d in (0.16, 3.0):
        a = hollow.strong_board(200.0, [(10.0 - d, 5.0)], hf=0.2, plating=0, core="solid")
        bb = hollow.strong_board(200.0, [(10.0 - d, 5.0)], hf=0.2, core=385.0)
        ra, rb = a.solve(direct_max=30000), bb.solve(direct_max=30000)
        print(f"(i) d {d}: solid cylinder tmax {ra['tmax']:.6f}  copper core + wall rings {rb['tmax']:.6f}  diff {rb['tmax'] - ra['tmax']:+.6f} K", flush=True)
        res[f"chk_i|{d}"] = [ra["tmax"], rb["tmax"]]
    # (ii) the area of the wall elements of the O-grid (an inscribed polygon of 4 n_side sides) against the annulus pi (ro^2 - ri^2), and a column solve
    for n_side in (8, 12):
        plan = hollow.strong_board(200.0, [(5.0, 5.0)], hf=0.2, n_side_via=n_side, half_win=0.5).plan
        c = plan.centroids()
        r = np.hypot(c[:, 0] - 5e-3, c[:, 1] - 5e-3)
        wall = (r >= 0.125e-3) & (r < 0.15e-3)
        area = plan.areas()[wall & (c[:, 1] <= 5e-3)].sum() * 2          # half domain (y <= 5): double it
        ann = np.pi * (0.15e-3 ** 2 - 0.125e-3 ** 2)
        print(f"(ii) n_side {n_side}: wall area {area:.6e} m2 / annulus {ann:.6e} = {area / ann:.5f} (inscribed 4n-gon: area ratio {4 * n_side / (2 * np.pi) * np.sin(2 * np.pi / (4 * n_side)):.5f})", flush=True)
        res[f"chk_ii|{n_side}"] = area / ann
    # column: the wall elements only, extruded through 1.6 mm of copper, flux on top, a stiff film at the bottom
    plan = hollow.strong_board(200.0, [(5.0, 5.0)], hf=0.2, n_side_via=8, half_win=0.5).plan
    c = plan.centroids()
    r = np.hypot(c[:, 0] - 5e-3, c[:, 1] - 5e-3)
    wall = (r >= 0.125e-3) & (r < 0.15e-3) & (c[:, 1] <= 5e-3 + 1e-12)
    ring = plan.remove(~wall)
    L, nz = 1.6e-3, 8
    zn = np.linspace(0.0, L, nz + 1)
    Np = ring.xy.shape[0]
    nodes = np.column_stack([np.tile(ring.xy, (nz + 1, 1)), np.repeat(zn, Np)])
    q = ring.quads
    Q = q.shape[0]
    elems = np.concatenate([np.tile(q, (nz, 1)) + np.repeat(np.arange(nz) * Np, Q)[:, None], np.tile(q, (nz, 1)) + np.repeat((np.arange(nz) + 1) * Np, Q)[:, None]], axis=1)
    m = fem.Model(nodes, elems)
    m.k[:] = 385.0
    m.add_faces(q, flux=1.0)
    m.add_faces(q + nz * Np, h=1e9)
    out = m.solve(direct_max=30000)
    T = out["T"]
    top = T[:Np]
    bot = T[nz * Np:]
    A_fem = m.face_integral(np.ones_like(T), q)[1]
    dT = float(np.nanmean(top) - np.nanmean(bot))
    G_fem = 1.0 * A_fem / dT
    G_cf = 385.0 * A_fem / L
    print(f"(ii) column: wall area {A_fem:.6e} m2, G_fem {G_fem:.6e} W/K, k A / L of the same area {G_cf:.6e} (ratio {G_fem / G_cf:.6f}); closed form of the true annulus (half) "
          f"{385.0 * ann / 2 / L:.6e} (FEM / closed {G_fem / (385.0 * ann / 2 / L):.5f})", flush=True)
    res["chk_ii|column"] = G_fem / (385.0 * ann / 2 / L)
    # (iii) wall elements 2, 3, 4
    for nw in (2, 3, 4):
        e = {}
        for core in ("open",):
            b0 = hollow.strong_board(200.0, [(9.84, 5.0)], hf=0.2, core=0.3, n_wall=nw)
            b0.vias = []
            t0 = b0.solve(direct_max=30000)["tmax"]
            t1 = hollow.strong_board(200.0, [(9.84, 5.0)], hf=0.2, core=CORES[core], n_wall=nw).solve(direct_max=30000)["tmax"]
            e[core] = t0 - t1
        print(f"(iii) n_wall {nw}: E(open, d 0.16, 200) = {e['open']:.5f} K", flush=True)
        res[f"chk_iii|{nw}"] = e["open"]
    save(res)


def prog(kind):
    """!
    @brief The program on the same boards: FVM and FDM at 1, 0.5 and 0.25 mm (default laminate and 8 sub-gaps for the FVM), the 3D solid, the Lumped and the Analytic.
    @param kind '1a' or '1b'.
    @return None.
    """
    import logging
    sys.path.insert(0, os.path.join(ROOT, "research", "strong-edge-laminate", "lib"))
    import prog as sp
    from pcbthermal import SolverOptions, simulate
    logging.disable(logging.WARNING)
    res = load()
    cores = {"open": 0.0, "resin": 0.3, "copper": 385.0}

    def make(h, d, fk):
        """!
        @brief The program's board.
        @param h Wall film.
        @param d Distance from the wall in mm (None: the array).
        @param fk fill_k, None for no via.
        @return Problem.
        """
        p = sp.board(h, None)
        if fk is None:
            return p
        pts = [(10.0 - d, 5.0)] if d is not None else [(x, y) for x in (6.0, 7.0, 8.0) for y in (4.0, 5.0, 6.0)]
        for x, y in pts:
            p.add_via(x, y, 0.3, fill_k=fk)
        return p
    for d in ((0.16, 3.0) if kind == "1a" else (None,)):
        for h in (200.0, 1000.0):
            for cell in (1.0, 0.5, 0.25):
                for model, n in (("fvm", None), ("fvm", 8), ("fdm", None)):
                    base_key = f"P{kind}|{d}|{h}|{cell}|{model}|{n}|base"
                    if base_key not in res:
                        res[base_key] = sp.run(make(h, d, None), cell, n, model=model)
                        save(res)
                    for core, fk in cores.items():
                        key = f"P{kind}|{d}|{h}|{cell}|{model}|{n}|{core}"
                        if key not in res:
                            res[key] = sp.run(make(h, d, fk), cell, n, model=model)
                            print(key, "E", round(res[base_key] - res[key], 5), flush=True)
                            save(res)
            for model, cell in (("lumped", 0.5), ("analytic", 0.5), ("solid3d", 0.5), ("solid3d", 0.25)):
                base_key = f"P{kind}|{d}|{h}|{cell}|{model}|None|base"
                try:
                    if base_key not in res:
                        res[base_key] = float(simulate(make(h, d, None), SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max - 25.0)
                    for core, fk in cores.items():
                        key = f"P{kind}|{d}|{h}|{cell}|{model}|None|{core}"
                        if key not in res:
                            res[key] = float(simulate(make(h, d, fk), SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max - 25.0)
                            print(key, "E", round(res[base_key] - res[key], 5), flush=True)
                    save(res)
                except Exception as exc:                                  # a model that refuses a board is reported, not hidden
                    print(model, cell, "refused:", exc, flush=True)
                    res[f"{base_key}|error"] = str(exc)[:200]


def report():
    """!
    @brief Print the Markdown tables (finite elements by mesh, the program's error against the finest finite-element value).
    @return None.
    """
    import refine
    res = load()
    for kind in ("1a", "1b"):
        for d in ((0.16, 3.0) if kind == "1a" else (None,)):
            for h in (200.0, 1000.0):
                print(f"\n{kind} d={d} h_side={h}")
                for core in ("open", "resin", "copper"):
                    es = [res.get(f"{kind}|{d}|{h}|{hf}|{core}|", {}).get("E") for hf in (0.2, 0.1, 0.05)]
                    got = [e for e in es if e is not None]
                    line = f"  FEM E {core}: " + " / ".join("-" if e is None else f"{e:.4f}" for e in es)
                    if len(got) == 3:
                        rr = refine.richardson(got)
                        line += f"  order {rr['p']:.2f} ext {rr['ext']:.4f}"
                    print(line)
                    ref = got[-1] if got else None
                    if ref is None:
                        continue
                    row = []
                    for cell in (1.0, 0.5, 0.25):
                        for model, n in (("fvm", None), ("fvm", 8), ("fdm", None)):
                            b, v = res.get(f"P{kind}|{d}|{h}|{cell}|{model}|{n}|base"), res.get(f"P{kind}|{d}|{h}|{cell}|{model}|{n}|{core}")
                            if b is not None and v is not None:
                                row.append(f"{model}{'' if n is None else n}@{cell}: {(b - v - ref) / ref * 100:+.1f}%")
                    for model, cell in (("lumped", 0.5), ("analytic", 0.5), ("solid3d", 0.5), ("solid3d", 0.25)):
                        b, v = res.get(f"P{kind}|{d}|{h}|{cell}|{model}|None|base"), res.get(f"P{kind}|{d}|{h}|{cell}|{model}|None|{core}")
                        if b is not None and v is not None:
                            row.append(f"{model}@{cell}: {(b - v - ref) / ref * 100:+.1f}%")
                    print("    program error vs finest FEM: " + "; ".join(row))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "fem":
        r = load()
        fem_case(sys.argv[2], float(sys.argv[3]), r)
    elif mode == "checks":
        checks()
    elif mode == "prog":
        prog(sys.argv[2])
    elif mode == "report":
        report()
