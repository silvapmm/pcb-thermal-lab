#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_harness_boards.py
@brief The surface read-out rules on the boards of the release regression harness (35 um copper, patterned copper, vias, outlines, a block): the Lumped upper bound and the Analytic rule F against the finite-element surface.
@details For every part of every harness board that has a heater (releases/regression-harness/lib/regress_boards.py, `build`), at the cell given, the models run are the FVM, the FEM, the Lumped and the Analytic.
         Per part (layer 1 or the last layer only, which have an outer face): the column read-out of each model (the part row), the FEM surface (analysis.surface_stats), the FVM surface (the program's
         thickness.attach), the Lumped upper bound (its column peak plus q'' t / (2 k), q'' the part power over its footprint) and the Analytic rule F. The numbers that decide the Lumped wording are
         `ub - FEM surface` (the bound is hot-side when positive) and the same with the Lumped column alone.
         Boards a model refuses (the FEM with a slanted outline, for example) print `-`. Usage: .venv/bin/python research/surface-readout-models/scripts/study_harness_boards.py [cell_mm] (the
         real-board environment is not needed; about 3 min at 2 mm, under 2 GB).
"""

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (ROOT, os.path.join(HERE, "..", "lib"), os.path.join(ROOT, "releases", "regression-harness", "lib")):
    if p not in sys.path:
        sys.path.insert(0, p)
import regress_boards as RB  # noqa: E402
import rules  # noqa: E402
from pcbthermal import SolverOptions, analysis, simulate  # noqa: E402
from pcbthermal.geometry import coverage_fraction, polygon_area  # noqa: E402


def run_board(name, cell):
    """!
    @brief The four models and the rules on one board.
    @param name Harness board name.
    @param cell Cell in mm.
    @return list of dicts, one per powered part on an outer layer (empty if none), with the numbers in degC and the errors.
    """
    prob = RB.build(name, os.path.join(ROOT, "examples"))
    b = prob.board
    L = b.layers
    res, fail = {}, {}
    for m in ("fvm", "fem", "lumped", "analytic"):
        try:
            res[m] = simulate(prob, SolverOptions(models=(m,), cell_mm=cell)).results[m]
        except Exception as exc:                                  # a refusal is a result, printed
            fail[m] = f"{type(exc).__name__}: {str(exc)[:60]}"
    rows = []
    fr = {m: rules.field_rule(prob, np.asarray(res[m].T), cell) for m in ("lumped", "analytic") if m in res}
    for j, h in enumerate(prob.heaters):
        if h.power <= 0 or h.layer not in (0, L - 1):
            continue
        face = 0 if h.layer == 0 else 1
        row = {"board": name, "part": h.name or f"H{j + 1}", "layer": h.layer + 1, "power": h.power, "cell": cell, "fail": fail}
        for m, r in res.items():
            hs = analysis.heater_stats(r, prob)[j]
            row[f"col_{m}"] = hs["t_max"]
            s = analysis.surface_stats(r, h.polygon, h.layer, b.outline)
            if s is not None:
                row[f"surf_{m}"] = s[0]
        q = h.power / polygon_area(h.polygon)
        t = float(b.copper_thickness[h.layer])
        row["bound_k"] = q * t / (2.0 * b.materials.k_copper)
        # The cells of THIS part only: q_src > 0 is the footprint of every part of the layer, which read the
        # hottest offset of the layer for each part (a defect found in review, the U1 / U2 rows were equal)
        # (per model: the Analytic may solve on a finer grid than the Lumped, plate_vias)
        for m in fr:
            my, mx = fr[m]["q_src"].shape[1:]
            own = coverage_fraction(h.polygon, mx, my, b.width / mx, b.height / my, 4) > 0
            mask = (fr[m]["q_src"][h.layer] > 0) & own
            d = fr[m]["d_top"] if face == 0 else fr[m]["d_bottom"]
            row[f"d_{m}"] = float(d[mask].max()) if mask.any() else float("nan")
        rows.append(row)
    return rows


def fmt(x, w=8, p=3):
    """!
    @brief Format a number or a dash.
    @param x float or None.
    @param w Width.
    @param p Decimals.
    @return str.
    """
    return f"{x:{w}.{p}f}" if x is not None and np.isfinite(x) else f"{'-':>{w}s}"


def main(cell=2.0):
    """!
    @brief Run every harness board, print the table, write out/harness_<cell>.json.
    @param cell Cell in mm.
    """
    allrows = []
    print(f"cell {cell} mm. Offsets are surface minus column in mK; 'bound' = q'' t / 2k in mK; the other columns in K. margin = (Lumped column + bound) - FEM surface (+ = the bound is above the FEM surface)")
    print(f"{'board':20s} {'part':8s} {'rise':>7s} | {'off FEM':>8s} {'off FVM':>8s} {'F Lump':>7s} {'F Anal':>7s} {'bound':>7s} {'bound>=FEM':>10s} | {'colL-FEM':>8s} {'margin':>8s} {'colA-FEM':>8s}")
    for name in RB.board_names():
        t0 = time.time()
        try:
            rows = run_board(name, cell)
        except Exception as exc:
            print(f"{name:20s} ERROR {type(exc).__name__}: {str(exc)[:80]}")
            continue
        for r in rows:
            amb = 25.0
            fem_s, fem_c = r.get("surf_fem"), r.get("col_fem")
            mk = lambda v: None if v is None else 1e3 * v  # noqa: E731
            off_fem = None if fem_s is None else fem_s - fem_c
            off_fvm = r["surf_fvm"] - r["col_fvm"] if "surf_fvm" in r else None
            ub = r["col_lumped"] + r["bound_k"] if "col_lumped" in r else None
            r["margin_ub"], r["ub"] = (ub - fem_s if (ub is not None and fem_s is not None) else None), ub
            r["off_fem"], r["off_fvm"] = off_fem, off_fvm
            ok = None if off_fem is None else ("yes" if r["bound_k"] >= off_fem - 1e-9 else "NO")
            print(f"{r['board']:20s} {r['part'][:8]:8s} {fmt(fem_s - amb if fem_s else None, 7, 2)} | {fmt(mk(off_fem), 8, 2)} {fmt(mk(off_fvm), 8, 2)} {fmt(mk(r.get('d_lumped')), 7, 2)} {fmt(mk(r.get('d_analytic')), 7, 2)} "
                  f"{fmt(mk(r['bound_k']), 7, 2)} {str(ok):>10s} | {fmt(r['col_lumped'] - fem_c if ('col_lumped' in r and fem_c) else None, 8, 2)} {fmt(r['margin_ub'], 8, 2)} "
                  f"{fmt(r['col_analytic'] - fem_c if ('col_analytic' in r and fem_c) else None, 8, 2)}" + (f"   refused: {r['fail']}" if r["fail"] else ""), flush=True)
        allrows += rows
        print(f"   ({name}: {time.time() - t0:.1f} s)", file=sys.stderr, flush=True)
    # Summary: how often the Lumped upper bound is below each reference surface, and how often the bound on the offset holds
    with_fem = [r for r in allrows if r.get("margin_ub") is not None]
    with_fvm = [r for r in allrows if "col_lumped" in r and "surf_fvm" in r]
    below_fem = [r for r in with_fem if r["margin_ub"] < 0]
    below_fvm = [r for r in with_fvm if r["col_lumped"] + r["bound_k"] - r["surf_fvm"] < 0]
    held = [r for r in allrows if r.get("off_fem") is not None and r["bound_k"] >= r["off_fem"] - 1e-9]
    print(f"\nparts with a FEM surface: {len(with_fem)}; the Lumped bound is BELOW the FEM surface on {len(below_fem)} (worst {min((r['margin_ub'] for r in with_fem), default=float('nan')):.2f} K); "
          f"below the FVM surface on {len(below_fvm)} of {len(with_fvm)} (worst {min((r['col_lumped'] + r['bound_k'] - r['surf_fvm'] for r in with_fvm), default=float('nan')):.2f} K); "
          f"the bound on the offset q'' t / 2k holds against the FEM offset on {len(held)} of {sum(1 for r in allrows if r.get('off_fem') is not None)}")
    # The counts quoted in README 4.4 and 4.6 (added in review, so that every quoted count is printed by a script)
    dA = [r for r in allrows if np.isfinite(r.get("d_analytic", np.nan))]
    dL = [r for r in allrows if np.isfinite(r.get("d_lumped", np.nan))]
    if dA and dL:
        print(f"rule F: {1e3 * min(r['d_analytic'] for r in dA):.2f} to {1e3 * max(r['d_analytic'] for r in dA):.2f} mK on the Analytic field, "
              f"{1e3 * min(r['d_lumped'] for r in dL):.2f} to {1e3 * max(r['d_lumped'] for r in dL):.2f} mK on the Lumped's (parts with a FEM surface: "
              f"{sum(1 for r in dA if r.get('off_fem') is not None)})")
        both = [r for r in dA if r.get("off_fem") is not None and np.isfinite(r.get("d_lumped", np.nan))]
        print(f"  Analytic and Lumped rule F within 0.02 mK of each other on {sum(1 for r in both if abs(r['d_analytic'] - r['d_lumped']) <= 2e-5)} of {len(both)}")
        near = [r for r in dA if r.get("off_fem") is not None and r.get("off_fvm") is not None]
        print(f"  Analytic rule F within 1 mK of the FVM offset on {sum(1 for r in near if abs(r['d_analytic'] - r['off_fvm']) <= 1e-3)} of {len(near)}; "
              f"exceptions: {[(r['board'], r['part']) for r in near if abs(r['d_analytic'] - r['off_fvm']) > 1e-3]}")
    pairs = [r for r in allrows if r.get("off_fem") is not None and r.get("off_fvm") is not None and r["off_fvm"] > 1e-4 and r["board"] != "drawn_ell"]
    if pairs:
        ratio = [r["off_fvm"] / max(r["off_fem"], 1e-12) for r in pairs]
        print(f"FEM offset smaller than the FVM offset on {sum(1 for r in pairs if r['off_fem'] < r['off_fvm'])} of {len(pairs)} parts (FVM offset > 0.1 mK, drawn_ell out), "
              f"FVM / FEM {min(ratio):.1f} to {max(ratio):.1f}; FEM offset / bound {min(r['off_fem'] / r['bound_k'] for r in pairs):.2f} to {max(r['off_fem'] / r['bound_k'] for r in pairs):.2f}, "
              f"FVM offset / bound {min(r['off_fvm'] / r['bound_k'] for r in pairs):.2f} to {max(r['off_fvm'] / r['bound_k'] for r in pairs):.2f}")
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    with open(os.path.join(HERE, "..", "out", f"harness_{cell}.json"), "w") as f:
        json.dump(allrows, f, indent=1, default=float)


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 2.0)
