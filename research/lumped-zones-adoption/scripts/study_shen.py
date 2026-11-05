#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_shen.py
@brief Study 8: the published case of Shen and others (2020), a 5.6 mm four-layer PCB with a 12 x 12 array of open 0.25 mm vias under a uniform 1 W top flux: the paper's equations, an independent axisymmetric
       unit-cell solver, and the five models of the program (and the zoned Lumped variant) on the same board.
@details Question: does the independent solver reproduce the published numbers (the no-via resistance 120.3 K/W and the via resistance 1.86 K/W of the Icepak CFD of Fig. 17, and the curve of Fig. 18(a) read
         from the plot), and how far are the program's models from the independent solver on a board where the via array is the whole footprint (the case the zones fall back on)?
         Tables: (1) the paper's equations (2) to (5) at the Fig. 17 geometry and the one-dimensional no-via resistance; (2) the Fig. 18(a) plot against equation (4) for a pad of 5.6 mm and 5.0 mm (the pad of
         Fig. 18 is not stated in the text read: the 5.0 mm is inferred from the fit and is marked so); (3) the unit-cell solver on three grids and the plating sensitivity; (4) the models of the program at several cells;
         (5) a sweep of the via diameter, the program against the unit-cell solver; (6) `P245` against `Z_none` (the fallback: a core above 92 % of the footprint, so the two must be identical).
         Success criterion (fixed before running): the unit-cell solver within 5 % of equation (4) (the equation has no lateral spreading in the planes and should be the higher), the program's FVM within 5 % of the
         unit-cell solver on the 12 x 12 board and on the diameter sweep, and `Z_none` equal to `P245` to 1e-9. The published CFD number (1.86 K/W) is NOT expected to be reproduced to 5 %: it is a third-party
         CFD whose model (layer positions, plating, FR-4 values) is not known in full; the gap is reported, not adjusted away.
         Not verified: the experimental part of the paper (section IV-B), the top-case and junction resistances (Theta_jc = 2.47, Theta_jt = 44.12 oC/W, from CFD), the pad models of section III.
Usage: python research/lumped-zones-adoption/scripts/study_shen.py   (from the repository root, with the program's .venv; about a minute)
"""

import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import shen_case as sc                                                       # noqa: E402
import zref                                                                  # noqa: E402
from pcbthermal import SolverOptions, simulate                               # noqa: E402

FINE = dict(nr_out=96, nz_gap=28, nz_cu=8, nr_barrel=10, nr_hole=10)
PLOT_18A = {0.1: 2.35, 0.16: 1.93, 0.25: 1.85, 0.33: 1.89, 0.55: 2.23, 0.8: 2.70}   # Fig. 18(a), air filler, Pattern I, CFD markers, READ FROM THE PLOT


def run(problem, model, cell):
    """!
    @brief Resistance (maximum rise per watt) of one model of the program on a Problem.
    @param problem The Problem (1 W).
    @param model Model key.
    @param cell Cell in mm.
    @return float K/W.
    """
    r = simulate(problem, SolverOptions(models=(model,), cell_mm=cell)).results[model]
    return float(r.t_max - problem.board.ambient)


def main():
    """!
    @brief Print the tables.
    @return dict of the numbers (also written to out/shen.json).
    """
    zref.pc.load_libraries()
    out = {}
    print("## 1. The paper's equations at the Fig. 17 geometry (5.6 mm, 12 x 12 vias, phi 0.25 mm, s 0.2 mm, t_PTH 25 um, air filler)")
    eq = sc.shen_array_resistance()
    nov = sc.shen_no_via_resistance()
    print(f"equation (4), 12 x 12 units: {eq:.3f} K/W ; one-dimensional no-via board: {nov:.2f} K/W (k_FR4 through 0.29); CFD in the paper: 1.86 and 120.3 K/W")
    print(f"the through-plane FR-4 conductivity that would give 120.3 K/W in one dimension: {(sc.T_BOARD - sc.N_CU * sc.T_CU) / (sc.SIDE ** 2 * (120.3 - sc.N_CU * sc.T_CU / sc.K_CU / sc.SIDE ** 2)):.3f} W/mK (Table I says 0.29)")
    out["eq4"], out["no_via_1d"] = eq, nov

    print("\n## 2. Fig. 18(a), air filler, Pattern I: CFD markers (read from the plot) against equation (4)")
    print("| phi mm | CFD plot K/W | eq. (4), pad 5.6 mm, floor count | eq. (4), pad 5.0 mm, l w / (phi + s)^2 |\n| --: | --: | --: | --: |")
    rows2 = []
    for phi_mm, cfd in PLOT_18A.items():
        phi = phi_mm * 1e-3
        e56 = sc.shen_unit_resistance(phi=phi) / math.floor(5.6e-3 / (phi + 0.2e-3)) ** 2
        e50 = sc.shen_unit_resistance(phi=phi) / (5.0e-3 ** 2 / (phi + 0.2e-3) ** 2)
        rows2.append((phi_mm, cfd, e56, e50))
        print(f"| {phi_mm:g} | {cfd:.2f} | {e56:.3f} ({100 * (e56 / cfd - 1):+.0f} %) | {e50:.3f} ({100 * (e50 / cfd - 1):+.0f} %) |")
    out["fig18a"] = rows2

    print("\n## 3. The unit-cell solver (axisymmetric finite volumes, nothing of the program)")
    grids = {"coarse": dict(nr_out=24, nz_gap=7, nz_cu=2, nr_barrel=3, nr_hole=3), "medium": {}, "fine": FINE}
    cells = {}
    for name, kw in grids.items():
        cells[name] = sc.unit_cell(**kw)
        print(f"{name}: R_cell {cells[name]:.2f} K/W, array of 144: {cells[name] / 144:.4f} K/W")
    ref = cells["fine"] / 144
    print(f"fine grid {ref:.3f} K/W: {100 * (ref / eq - 1):+.1f} % against equation (4), {100 * (ref / 1.86 - 1):+.1f} % against the CFD 1.86 K/W")
    print("plating sensitivity (fine grid, array of 144; the CFD value 1.86 K/W would be met by about 19 um: a sensitivity, not an explanation): ", end="")
    for tp in (25e-6, 20e-6, 15e-6):
        print(f"t_PTH {tp * 1e6:.0f} um: solver {sc.unit_cell(t_pth=tp, **FINE) / 144:.3f}, eq. (4) {sc.shen_array_resistance(t_pth=tp):.3f}; ", end="")
    print()
    out["solver"] = {"grids": cells, "ref": ref}

    print("\n## 4. The models of the program on the 12 x 12 board (maximum rise for 1 W, K/W; no-via board)")
    print("| model | cell mm | no vias | with vias | against the unit-cell solver | against eq. (4) | seconds |\n| :-- | --: | --: | --: | --: | --: | --: |")
    rows4 = []
    for model, cell in (("fvm", 0.4), ("fvm", 0.2), ("fvm", 0.1), ("fvm", 0.05), ("fdm", 0.2), ("fdm", 0.1), ("solid3d", 0.2), ("solid3d", 0.1), ("lumped", 1.0), ("analytic", 1.0)):
        t0 = time.time()
        try:
            r0 = run(sc.program_problem(with_vias=False), model, cell)
            r1 = run(sc.program_problem(), model, cell)
        except ValueError as exc:
            print(f"| {model} | {cell} | refused: {str(exc)[:60]} | | | | |")
            continue
        rows4.append((model, cell, r0, r1))
        print(f"| {model} | {cell:g} | {r0:.3f} | {r1:.3f} | {100 * (r1 / ref - 1):+.1f} % | {100 * (r1 / eq - 1):+.1f} % | {time.time() - t0:.1f} |", flush=True)
    out["models"] = rows4

    print("\n## 5. Sweep of the via diameter (pitch phi + 0.2 mm, as many as fit in 5.6 mm), the program against the unit-cell solver")
    print("| phi mm | n | unit-cell solver | eq. (4) | FVM 0.1 mm | FDM 0.1 mm | Lumped | Analytic | FVM vs solver |\n| --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    rows5 = []
    for phi_mm in (0.16, 0.25, 0.33, 0.55):
        phi = phi_mm * 1e-3
        pitch = phi + 0.2e-3
        n = int(math.floor(5.6e-3 / pitch))
        s = sc.unit_cell(pitch=pitch, phi=phi, **FINE) / n ** 2
        e = sc.shen_unit_resistance(phi=phi) / n ** 2
        p = sc.program_problem(n=n, pitch=pitch, phi=phi)
        v = {m: run(p, m, c) for m, c in (("fvm", 0.1), ("fdm", 0.1), ("lumped", 1.0), ("analytic", 1.0))}
        rows5.append((phi_mm, n, s, e, v))
        print(f"| {phi_mm:g} | {n} | {s:.3f} | {e:.3f} | {v['fvm']:.3f} | {v['fdm']:.3f} | {v['lumped']:.3f} | {v['analytic']:.3f} | {100 * (v['fvm'] / s - 1):+.1f} % |", flush=True)
    out["sweep"] = rows5

    print("\n## 6. The zoned Lumped model on this board (the via array is the whole footprint: a core above 92 %, the program's network)")
    p = sc.program_problem()
    t_p = zref.lumped_tmax(p, "P245", 1.0)
    t_z = zref.lumped_tmax(p, "Z_none", 1.0)
    print(f"P245 {t_p:.9f} K, Z_none {t_z:.9f} K, difference {abs(t_p - t_z):.2e} K")
    out["fallback"] = (t_p, t_z)
    print("written", zref.save_json("shen.json", out))
    return out


if __name__ == "__main__":
    main()
