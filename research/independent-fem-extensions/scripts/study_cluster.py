#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cluster.py
@brief Study 2 of the finite-element extensions: a part (6 x 6 or 4 x 4 mm, 1 W) over a 4 x 4 cluster of hollow resin vias on a 20 x 20 mm four-layer board with a 1 mm
       aluminium plate under it through a 0.1 mm interface; variant A (the program's problem), variant B (copper tab and solder resolved) and the partial-edge variant
       (layer 2 copper ends on a line through one column of vias), against the program's FVM, FDM, 3D solid, Lumped and Analytic.
@details Run from the repository root, one job at a time (each under 2 GB; the plan guard prints the unknowns first):
         `research/independent-fem-edge/.venv-research/bin/python research/independent-fem-extensions/scripts/study_cluster.py fem A 6 0.2` (variant A|B, tab 6|4, hf in mm,
         add `rim` as a fifth argument for the partial edge), `.../study_cluster.py report`, and with the program's interpreter
         `.venv/bin/python research/independent-fem-extensions/scripts/study_cluster.py prog`. Results: `research/independent-fem-extensions/out/s2.json`.
         Every value is a rise over the ambient in K. Compared quantities: the mean over the footprint of the top surface of the board copper (the program's `heater_stats`
         `t_mean`), the hottest node/cell of the top copper (`t_max`) and the mean temperature of the plate.
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

OUT = os.path.join(HERE, "..", "out", "s2.json")


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


def fem(variant, tab, hf, rim, no_via=False):
    """!
    @brief One finite-element solve of study 2 with the 2 GB guard (refuses above 30 000 unknowns direct, estimate 8.5 kB per unknown above).
    @param variant 'A' or 'B'.
    @param tab Part side in mm.
    @param hf Fine plan size in mm.
    @param rim True for the partial edge.
    @param no_via True: the baseline without the via copper (same mesh).
    @return None.
    """
    import cluster
    res = load()
    key = f"{variant}|{tab}|{hf}|{'rim' if rim else 'full'}{'|novia' if no_via else ''}"
    if key in res:
        print(key, "cached", res[key])
        return
    st, hd = cluster.build(variant, tab, hf, rim, no_via=no_via)
    m, info = st.build()
    n = m.nodes.shape[0]
    est = n * (46000.0 if n <= 30000 else 8500.0) / 1e9
    print(f"{key}: {n} nodes, {m.elems.shape[0]} elements, estimate {est:.2f} GB", flush=True)
    if est > 2.0:
        print("refused: above the 2 GB budget", flush=True)
        return
    t = time.time()
    r = st.solve(direct_max=30000)
    o = cluster.readout(st, r, hd, tab)
    o["seconds"] = time.time() - t
    print(key, {k: (round(v, 5) if isinstance(v, float) else v) for k, v in o.items()}, flush=True)
    res[key] = o
    save(res)


def program_problem(tab, rim, no_via=False):
    """!
    @brief The program's problem: variant A.
    @param tab Part side in mm.
    @param rim True: the copper of layer 2 is two zones that leave the strip |x - 10| < 1.2 mm bare.
    @param no_via True: no vias.
    @return Problem.
    """
    from pcbthermal import Problem
    p = Problem.new(20, 20, 4, 1.6, 35.0, h_top=10.0, h_bottom=10.0, h_side=10.0)
    for lay in range(1, 5):
        if rim and lay == 2:
            p.add_zone(lay, rect=(0, 0, 8.8, 20))
            p.add_zone(lay, rect=(11.2, 0, 20, 20))
        else:
            p.add_zone(lay, rect=(0, 0, 20, 20))
    a, b = 10 - tab / 2, 10 + tab / 2
    p.add_heater(1, 1.0, rect=(a, a, b, b), role="source", pad_thickness_mm=0.1, pad_k=50.0)
    for x in (8.8, 9.6, 10.4, 11.2):
        for y in (8.8, 9.6, 10.4, 11.2):
            if not no_via:
                p.add_via(x, y, 0.3, fill_k=0.3)
    p.add_heatsink(4, 0.0, rect=(0, 0, 20, 20), thickness_mm=1.0, k=204.0, rho_cp=2.44e6, pad_thickness_mm=0.1, pad_k=3.0)
    return p


def prog():
    """!
    @brief The program's models on variant A (steady): FVM and FDM at 1, 0.5 and 0.25 mm, the 3D solid at 0.5 and 0.25, the Lumped and Analytic at 0.5 and 0.25 mm.
    @return None.
    """
    import logging
    sys.path.insert(0, ROOT)
    from pcbthermal import SolverOptions, analysis, simulate
    logging.disable(logging.WARNING)
    res = load()
    for tab in (6, 4):
        for rim in (False, True):
            if tab == 4 and rim:
                continue
            for nov in ((False, True) if not rim else (False,)):
                for model, cells in (("fvm", (1.0, 0.5, 0.25)), ("fdm", (1.0, 0.5, 0.25)), ("solid3d", (0.5, 0.25)), ("lumped", (0.5, 0.25)), ("analytic", (0.5, 0.25))):
                    for cell in cells:
                        key = f"P|{tab}|{'rim' if rim else 'full'}|{model}|{cell}{'|novia' if nov else ''}"
                        if key in res:
                            continue
                        t = time.time()
                        try:
                            p = program_problem(tab, rim, nov)
                            r = simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model]
                            st = analysis.heater_stats(r, p)[0]
                            o = {"part_mean": float(st["t_mean"] - 25.0), "part_max": float(st["t_max"] - 25.0), "t_max_board": float(r.t_max - 25.0)}
                            bt = r.arrays.get("block_T") if hasattr(r, "arrays") else None
                            if bt is not None:
                                cov = r.arrays.get("block_cov")
                                o["plate_mean"] = float(np.nansum(bt * cov) / np.nansum(cov) - 25.0) if cov is not None and np.shape(cov) == np.shape(bt) else float(np.nanmean(bt) - 25.0)
                            o["seconds"] = time.time() - t
                            res[key] = o
                            print(key, {k: round(v, 4) for k, v in o.items()}, flush=True)
                        except Exception as exc:                          # a refusal of a model is reported
                            res[key] = {"error": str(exc)[:200]}
                            print(key, "ERROR", exc, flush=True)
                        save(res)


def report():
    """!
    @brief Print the tables: finite elements by mesh (observed order for three), B minus A, the program's error against the finest finite-element value.
    @return None.
    """
    import refine
    res = load()
    for tab, rim in ((6, False), (6, True), (4, False)):
        tag = "rim" if rim else "full"
        print(f"\n== part {tab} x {tab} mm, {tag} copper")
        fe = {}
        for variant in ("A", "B"):
            for q in ("part_mean", "part_max", "plate_mean"):
                vals = [(hf, res[f"{variant}|{float(tab)}|{hf}|{tag}"][q]) for hf in (0.4, 0.2, 0.1) if f"{variant}|{float(tab)}|{hf}|{tag}" in res]
                if vals:
                    line = f"  FEM {variant} {q}: " + " / ".join(f"{h}:{v:.4f}" for h, v in vals)
                    if len(vals) == 3:
                        r = refine.richardson([v for _, v in vals])
                        line += f"  order {r['p']:.2f} ext {r['ext']:.4f} gci {100 * r['gci']:.2f}%"
                    print(line)
                    fe[(variant, q)] = vals[-1][1]
        for q in ("part_mean", "part_max", "plate_mean"):
            if ("A", q) in fe and ("B", q) in fe:
                print(f"  B - A {q}: {fe[('B', q)] - fe[('A', q)]:+.4f} K ({100 * (fe[('B', q)] - fe[('A', q)]) / fe[('A', q)]:+.2f} % of A)")
        if not rim:
            for q in ("part_mean", "part_max"):
                vals = [(hf, res[f"A|{float(tab)}|{hf}|full|novia"][q] - res[f"A|{float(tab)}|{hf}|full"][q]) for hf in (0.2, 0.1) if f"A|{float(tab)}|{hf}|full|novia" in res]
                if vals:
                    print(f"  via effect E (no via minus via) {q}: " + " / ".join(f"{h}:{v:.4f}" for h, v in vals))
                    fe[("E", q)] = vals[-1][1]
            for model in ("fvm", "fdm", "solid3d", "lumped", "analytic"):
                row = []
                for cell in (1.0, 0.5, 0.25):
                    a, b = res.get(f"P|{tab}|full|{model}|{cell}"), res.get(f"P|{tab}|full|{model}|{cell}|novia")
                    if a and b and "error" not in a and ("E", "part_mean") in fe:
                        row.append(f"@{cell}: E {b['part_mean'] - a['part_mean']:.4f} K ({100 * ((b['part_mean'] - a['part_mean']) / fe[('E', 'part_mean')] - 1):+.1f}% of the FEM E)")
                if row:
                    print(f"  program {model} via effect (part mean): " + " | ".join(row))
        for model in ("fvm", "fdm", "solid3d", "lumped", "analytic"):
            row = []
            for cell in (1.0, 0.5, 0.25):
                o = res.get(f"P|{tab}|{tag}|{model}|{cell}")
                if not o or "error" in o:
                    continue
                parts = []
                for q in ("part_mean", "part_max", "plate_mean"):
                    if q in o and ("A", q) in fe:
                        parts.append(f"{q.split('_')[0]}{q.split('_')[1][:3]} {100 * (o[q] - fe[('A', q)]) / fe[('A', q)]:+.2f}%")
                row.append(f"@{cell}: " + ", ".join(parts))
            if row:
                print(f"  program {model} vs FEM A (finest mesh): " + " | ".join(row))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "fem":
        fem(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), "rim" in sys.argv[5:], no_via="novia" in sys.argv[5:])
    elif mode == "prog":
        prog()
    elif mode == "report":
        report()
