#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_near_edge.py
@brief Item 5: a source near an edge or a corner of a finite plate. The published case (Seri Lee, Electronics Cooling, January 1998: aluminium base 100 x 100 x 1.3 mm, 25 x 25 mm source, 1.0 K/W fin side, Rc 0.66 /
       1.29 / 2.38 K/W for the centre, the edge midpoint and the corner), the exact thin-plate cosine series (`lib/plate_series.py`, the method of images in eigenfunction form), the independent 3D solver, and the
       program's five models, at the three published positions and along a sweep of the distance to the edge and to the corner.
@details Metric: Rc = maximum temperature of the source minus the mean temperature of the film face, per watt (the paper's definition). The program runs the plate as a two-layer board of aluminium (k = 200 W/mK,
         two layers of 0.65 mm joined by a 1 um laminate gap whose drop, 6.5e-4 K at 100 W/m2, is 0.1 % of Rc), the film h = 1 / (R0 A) on the bottom face, the top and the edges insulated, a heater over the source.
         The thin-plate series is the continuum limit of the layered models (one node through the thickness); the difference between a program model and the series is the model, the difference between
         the series and the 3D solver is the through-thickness gradient of the real 1.3 mm plate, the difference from the printed Rc is the correlation of the article (accurate to about 5 %).
         Run from the repository root: .venv/bin/python research/published-cases-followup/scripts/study_near_edge.py (about 1 minute, under 1 GB). Section 4 (review): a PCB-like board with a 5 mm part at the centre, an edge and a corner.
"""

import json

import _bootstrap
import numpy as np

import layered3d as L3
import plate_series as PS

OUT = _bootstrap.OUT
SIDE, THICK, K, R0, SRC = 0.1, 1.3e-3, 200.0, 1.0, 25e-3
PAPER = {"centre": 0.66, "edge midpoint": 1.29, "corner": 2.38}
MODELS = ("fvm", "fdm", "solid3d", "lumped", "analytic")
H = 1.0 / (R0 * SIDE ** 2)


def rect_mm(gx, gy):
    """!
    @brief The source rectangle for gaps to the left and bottom edges.
    @param gx Gap between the source and the left edge in mm (37.5 = centred).
    @param gy Gap to the bottom edge in mm.
    @return tuple (x0, y0, x1, y1) in mm.
    """
    return (gx, gy, gx + 25.0, gy + 25.0)


def series_rc(gx, gy):
    """!
    @brief The exact thin-plate Rc of a source position.
    @param gx Gap to the left edge in mm.
    @param gy Gap to the bottom edge in mm.
    @return tuple (Rc on the maximum of the source, Rc on the mean of the source) in K/W.
    """
    r = tuple(v * 1e-3 for v in rect_mm(gx, gy))
    o = PS.source_rise(SIDE, K * THICK, H, r, 1.0)
    return o["rc"], o["rc_mean"]


def solver_rc(gx, gy, dx=0.5e-3):
    """!
    @brief Rc by the independent 3D solver (three slabs through the thickness).
    @param gx Gap to the left edge in mm.
    @param gy Gap to the bottom edge in mm.
    @param dx Cell in m.
    @return tuple (Rc on the maximum, Rc on the mean of the source) in K/W.
    """
    n = int(round(SIDE / dx))
    res = L3.solve(dx, n, n, [(THICK, K, 3)], tuple(v * 1e-3 for v in rect_mm(gx, gy)), 1.0, 0.0, H)
    return res["max_source"] - res["mean_wall"], res["mean_source"] - res["mean_wall"]


def program_rc(gx, gy, model, cell_mm=1.0):
    """!
    @brief Rc of one model of the program.
    @param gx Gap to the left edge in mm.
    @param gy Gap to the bottom edge in mm.
    @param model Model key.
    @param cell_mm Cell in mm.
    @return tuple (Rc on the hottest point of the footprint, Rc on the footprint mean) in K/W (NaN when the model refuses the board).
    """
    import sys
    from pcbthermal import Problem, SolverOptions, analysis, simulate
    from pcbthermal.model import Materials
    p = Problem.new(100.0, 100.0, layers=2, thickness_mm=1.301, copper_um=650.0, ambient=0.0, h_top=0.0, h_bottom=H, h_side=0.0,
                    materials=Materials(k_copper=K, k_fr4_through=0.3, k_fr4_inplane=0.9))
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=rect_mm(gx, gy), name="U")
    try:
        res = simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm)).results[model]
        st = analysis.heater_stats(res, p)[0]
        film = float(np.asarray(res.T)[-1].mean()) - p.board.ambient
        return float(st["t_max"] - p.board.ambient - film), float(st["t_mean"] - p.board.ambient - film)
    except Exception as exc:
        print(f"  [{model}] {type(exc).__name__}: {str(exc)[:100]}", file=sys.stderr)
        return float("nan"), float("nan")


def row_text(series, vals):
    """!
    @brief One table row: for each model the error against the series on the maximum and on the mean of the source.
    @param series Tuple (max, mean) of the series.
    @param vals dict model -> (max, mean).
    @return str.
    """
    return "  ".join(f"{100 * (v[0] / series[0] - 1):+6.1f}/{100 * (v[1] / series[1] - 1):+6.1f}" for v in vals.values())


def main():
    """!
    @brief Run the study and write out/near_edge.json.
    @return None.
    """
    res = {"published": [], "sweep_edge": [], "sweep_corner": []}
    hdr = "   " + "  ".join(f"{m:>13s}" for m in MODELS)
    print("\n1. The published plate (Seri Lee 1998): Rc in K/W on the hottest point of the source (and on its mean)")
    print("   position        printed |  series max (vs printed)  mean |  3D solver max (vs printed)  mean")
    for name, (gx, gy) in (("centre", (37.5, 37.5)), ("edge midpoint", (37.5, 0.0)), ("corner", (0.0, 0.0))):
        s, d3 = series_rc(gx, gy), solver_rc(gx, gy)
        vals = {m: program_rc(gx, gy, m) for m in MODELS}
        v05 = program_rc(gx, gy, "fvm", 0.5)
        res["published"].append({"name": name, "printed": PAPER[name], "series": s, "solver3d": d3, "models": vals, "fvm_0.5": v05})
        print(f"   {name:14s}  {PAPER[name]:6.2f} | {s[0]:9.4f} ({100 * (s[0] / PAPER[name] - 1):+5.1f} %) {s[1]:8.4f} | {d3[0]:9.4f} ({100 * (d3[0] / PAPER[name] - 1):+5.1f} %) {d3[1]:8.4f}")
    print("   the program, error against the thin-plate series in % (on the hottest point / on the footprint mean), 1 mm cells:")
    print("   position       " + "  ".join(f"{m:>13s}" for m in MODELS) + "      fvm@0.5")
    for r in res["published"]:
        print(f"   {r['name']:14s} " + row_text(r["series"], r["models"]) + "   " + row_text(r["series"], {"x": r["fvm_0.5"]}))
    print("\n2. Sweep of the gap g between the source and one edge (25 mm source, centred along the edge): Rc of the series (max, mean) and the error of each model (max/mean), %")
    print("   gap mm  series max  mean |" + hdr)
    for g in (0.0, 2.0, 6.0, 12.0, 24.0, 37.5):
        s = series_rc(g, 37.5)
        vals = {m: program_rc(g, 37.5, m) for m in MODELS}
        res["sweep_edge"].append({"gap_mm": g, "series": s, "models": vals})
        print(f"   {g:6.1f}  {s[0]:8.4f} {s[1]:7.4f} | " + row_text(s, vals))
    print("\n3. Sweep of the diagonal gap g to the corner (source at (g, g)): same quantities")
    print("   gap mm  series max  mean |" + hdr)
    for g in (0.0, 2.0, 6.0, 12.0, 24.0):
        s = series_rc(g, g)
        vals = {m: program_rc(g, g, m) for m in MODELS}
        res["sweep_corner"].append({"gap_mm": g, "series": s, "models": vals})
        print(f"   {g:6.1f}  {s[0]:8.4f} {s[1]:7.4f} | " + row_text(s, vals))
    res["pcb"] = pcb_board()
    (OUT / "near_edge.json").write_text(json.dumps(res, indent=1, default=float))


def pcb_board():
    """!
    @brief Review: the same question on a PCB-like board (100 x 100 mm, two layers of 35 um full copper, 1.6 mm, h = 10 W/m2K on both faces, insulated edges,
           a 5 x 5 mm part of 1 W on layer 1) at the centre, at an edge and at a corner, the Lumped and the Analytic against the fvm at 0.25 mm (footprint mean and hottest point).
           Run with PYTHONPATH set to another checkout to measure another version of the program on the same board.
    @return list of dicts (position, fvm mean and max, analytic and lumped errors in %).
    """
    from pcbthermal import Problem, SolverOptions, analysis, simulate
    print("\n4. (review) A PCB-like board: 100 x 100 mm, 2 x 35 um full copper, 1.6 mm, h 10 W/m2K, 5 x 5 mm part of 1 W; error against the fvm at 0.25 mm, %")
    print("   position        fvm mean  max K | analytic mean | lumped mean  max")
    rows = []
    for name, (x, y) in (("centre", (47.5, 47.5)), ("edge, gap 0", (0.0, 47.5)), ("edge, gap 5", (5.0, 47.5)), ("corner, gap 0", (0.0, 0.0)), ("corner, gap 5", (5.0, 5.0))):
        p = Problem.new(100.0, 100.0, layers=2, thickness_mm=1.6, copper_um=35.0, ambient=0.0, h_top=10.0, h_bottom=10.0, h_side=0.0)
        p.add_full_copper()
        p.add_heater(1, 1.0, rect=(x, y, x + 5.0, y + 5.0), name="U")
        st = {}
        for m, c in (("fvm", 0.25), ("analytic", 0.5), ("lumped", 0.5)):
            r = simulate(p, SolverOptions(models=(m,), cell_mm=c)).results[m]
            s = analysis.heater_stats(r, p)[0]
            st[m] = (s["t_mean"] - p.board.ambient, s["t_max"] - p.board.ambient)
        f = st["fvm"]
        row = {"position": name, "fvm": f, "analytic_mean": 100 * (st["analytic"][0] / f[0] - 1),
               "lumped_mean": 100 * (st["lumped"][0] / f[0] - 1), "lumped_max": 100 * (st["lumped"][1] / f[1] - 1)}
        rows.append(row)
        print(f"   {name:14s} {f[0]:8.2f} {f[1]:6.2f} | {row['analytic_mean']:+12.2f} | {row['lumped_mean']:+10.1f} {row['lumped_max']:+5.1f}")
    return rows


if __name__ == "__main__":
    main()
