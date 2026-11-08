#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_barrel_length.py
@brief What length should the barrel of a via have between two copper nodes: the dielectric gap d only (the program), d + a t_cu, and which a?
@details One via unit cell (square board of one pitch, 1 W over the whole top, isothermal bottom, insulated sides, h_top 0) in the FVM and FDM of the program, against the
         independent axisymmetric cell of lib/axicell.py, over a sweep of copper thickness (18 to 105 um), gap (0.1 to 1.5 mm), drill (0.2 to 0.5 mm), filler (air, solder),
         number of layers (2, 4, 6) and pitch. For each rule a (lib/barrel.py, a = 0 is the program) it prints the error of R and the worst and mean over the sweep.
         Run from the repository root: `.venv/bin/python research/via-contact-geometry/scripts/study_barrel_length.py [--quick]`; writes out/barrel.json.
"""

import argparse
import itertools
import json
import logging
import sys

import _bootstrap  # noqa: F401  (paths)
import numpy as np

import axicell as AX
import barrel as BA

logging.disable(logging.WARNING)
K_CU, K_Z, K_R, T_PTH = 393.0, 0.29, 0.81, 25e-6
K_FILL = {"air": 0.026, "solder": 57.3}


def program_r(n_layers, t_board, t_cu, phi, pitch, kf, model, cell_div):
    """!
    @brief R = mean top temperature / 1 W of the unit-cell board in one layered model of the program.
    @param n_layers Copper layers.
    @param t_board Board thickness in m.
    @param t_cu Copper thickness in m.
    @param phi Drill in m.
    @param pitch Cell side in m.
    @param kf Filler conductivity in W/mK.
    @param model "fvm" or "fdm".
    @param cell_div Cells across the pitch.
    @return float K/W.
    """
    from pcbthermal import Problem, SolverOptions, analysis, simulate
    from pcbthermal.model import Materials
    side = pitch * 1e3
    p = Problem.new(side, side, n_layers, t_board * 1e3, t_cu * 1e6, ambient=0.0, h_top=0.0, h_bottom=1.0e7, h_side=0.0, via_plating=T_PTH,
                    materials=Materials(k_copper=K_CU, k_fr4_through=K_Z, k_fr4_inplane=K_R))
    for layer in range(1, n_layers + 1):
        p.add_zone(layer, rect=(0.0, 0.0, side, side))
    p.add_heater(1, 1.0, rect=(0.0, 0.0, side, side))
    if phi > 0:
        p.add_via(side / 2, side / 2, phi * 1e3, fill_k=kf)
    res = simulate(p, SolverOptions(models=(model,), cell_mm=side / cell_div)).results[model]
    return float(analysis.heater_stats(res, p)[0]["t_mean"])


def main():
    """!
    @brief Run the sweep and print the table.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    t_cus = (35e-6, 70e-6) if a.quick else (18e-6, 35e-6, 70e-6, 105e-6)
    gaps = (0.2e-3, 0.44e-3) if a.quick else (0.1e-3, 0.2e-3, 0.44e-3, 1.0e-3, 1.5e-3)
    phis = (0.3e-3,) if a.quick else (0.2e-3, 0.3e-3, 0.5e-3)
    fills = ("air",) if a.quick else ("air", "solder")
    layers = (2, 4) if a.quick else (2, 4, 6)
    rules = (0.0, 0.25, 0.5, 0.75, 1.0)
    rows = []
    # no-via check first: the program and the reference on the plain board
    st = AX.equal_gap_stack(4, 1.6e-3, 70e-6)
    r0 = AX.unit_cell(0.45e-3, 0.25e-3, 0.026, st, no_via=True)
    print(f"no via, 4 x 70 um, 1.6 mm: reference {r0:.4f} K/W, FVM {program_r(4, 1.6e-3, 70e-6, 0.0, 0.45e-3, 0.0, 'fvm', 3):.4f}, FDM {program_r(4, 1.6e-3, 70e-6, 0.0, 0.45e-3, 0.0, 'fdm', 3):.4f}")
    for nl, tcu, gap, phi, fk in itertools.product(layers, t_cus, gaps, phis, fills):
        t_board = nl * tcu + (nl - 1) * gap
        for pitch in (phi + 0.2e-3, 1.0e-3):
            stack = AX.equal_gap_stack(nl, t_board, tcu)
            ref = AX.unit_cell(pitch, phi, K_FILL[fk], stack)
            row = dict(layers=nl, t_cu=tcu, gap=gap, phi=phi, fill=fk, pitch=pitch, ref=ref, err={})
            for model in ("fvm", "fdm"):
                for rule in rules:
                    with BA.patched(rule):
                        v = program_r(nl, t_board, tcu, phi, pitch, K_FILL[fk], model, max(int(round(pitch * 1e3 / 0.0625)), 3))   # 0.0625 mm cells: converged (README 2.2)
                    row["err"][f"{model}|{rule}"] = 100.0 * (v / ref - 1.0)
            rows.append(row)
            print(f"{nl}L tcu {tcu * 1e6:4.0f} gap {gap * 1e3:4.2f} phi {phi * 1e3:3.1f} {fk:6s} p {pitch * 1e3:4.2f} ref {ref:8.3f}  fvm " + " ".join(f"{row['err'][f'fvm|{r}']:+6.1f}" for r in rules), flush=True)
    summary = {}
    print("\nerror of R against the axisymmetric cell, per cent (negative: the program reads the via too conductive)")
    print("model rule(a)   mean    min    max   mean|e|")
    for model in ("fvm", "fdm"):
        for rule in rules:
            e = np.array([r["err"][f"{model}|{rule}"] for r in rows])
            summary[f"{model}|{rule}"] = dict(mean=e.mean(), min=e.min(), max=e.max(), mae=np.abs(e).mean())
            print(f"{model:5s} {rule:5.2f} {e.mean():+7.2f} {e.min():+7.2f} {e.max():+7.2f} {np.abs(e).mean():7.2f}")
    # the best a per model, and its dependence on t_cu / gap
    print("\nbest a for each case (FVM), by the ratio t_cu / gap: the a that makes the error zero by interpolation")
    from scipy.interpolate import interp1d
    for model in ("fvm", "fdm"):
        pairs = []
        for r in rows:
            e = np.array([r["err"][f"{model}|{k}"] for k in rules])
            if e.min() <= 0 <= e.max():
                pairs.append((r["t_cu"] / r["gap"], float(interp1d(e[::-1] if e[0] > e[-1] else e, np.array(rules)[::-1] if e[0] > e[-1] else np.array(rules))(0.0)), r["layers"]))
        if pairs:
            arr = np.array(pairs)
            print(f"{model}: cases bracketed {len(pairs)} of {len(rows)}; a0 mean {arr[:, 1].mean():.2f} min {arr[:, 1].min():.2f} max {arr[:, 1].max():.2f}; corr(a0, t/gap) {np.corrcoef(arr[:, 0], arr[:, 1])[0, 1]:+.2f}")
    with open(_bootstrap.OUT / "barrel.json", "w") as fh:
        json.dump(dict(rows=rows, summary=summary), fh, indent=1)


if __name__ == "__main__":
    sys.exit(main())
