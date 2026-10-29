#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_program_vs_coupon.py
@brief The five models of the program against the independent 3D solver on the Cu / FR4 / Cu version of the coupon of Culham and Yovanovich (1998), for several source sizes.
@details The coupon of the paper has an outer dielectric layer above the top copper in most of its five cases, which the layered models of the program cannot represent (they have a node per copper layer
         and the outer faces belong to copper). Its case 2 (copper, three FR4 layers merged into one gap of 1.5789 mm, copper; isotropic FR4 of 0.4 W/mK, copper 400 W/mK, layers of 35.6 um) is representable,
         so the program is run on that board: 50 x 50 mm, insulated sides, film coefficient 5 W/m2K on both faces (the program applies it under the source too, so the independent solver does the same), a
         centred square source of 2.5 W whose side is varied (epsilon = source area / board area). The metric is the mean temperature rise of the top copper under the source. Run:
         .venv/bin/python research/effective-conductivity/scripts/study_program_vs_coupon.py (from the repository root; about 3 minutes).
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

CU_T, GAP, K_CU, K_FR4, POWER, H = 35.6e-6, 1.5789e-3, 400.0, 0.4, 2.5, 5.0
WIDTH = 50e-3
SIDES_MM = [5.0, 16.0, 25.0, 35.0, 50.0]                       # edges on the 0.5 mm cells (35 mm for epsilon 0.5: 35.5 would put the edges between cells)
MODELS = ("fvm", "fdm", "solid3d", "lumped", "analytic")


def independent(side_mm, dx=0.5e-3):
    """!
    @brief Mean rise of the top copper under the source by the independent 3D solver.
    @param side_mm Side of the centred source in mm.
    @param dx Cell size in m.
    @return float Rise in K.
    """
    n = int(round(WIDTH / dx))
    c, s = WIDTH / 2, side_mm * 1e-3
    res = L.solve(dx, n, n, [(CU_T, K_CU, 1), (GAP, K_FR4, 8), (CU_T, K_CU, 1)], (c - s / 2, c - s / 2, c + s / 2, c + s / 2), POWER, H, H, film_under_source=True)
    return res["cell_mean_source"]


def program(side_mm, cell_mm=0.5):
    """!
    @brief Mean rise of the top copper under the source in each model of the program.
    @param side_mm Side of the centred source in mm.
    @param cell_mm Cell size in mm.
    @return dict model -> rise in K (NaN where the model did not run).
    """
    mat = Materials(k_copper=K_CU, k_fr4_through=K_FR4, k_fr4_inplane=K_FR4)
    p = Problem.new(50.0, 50.0, layers=2, thickness_mm=(2 * CU_T + GAP) * 1e3, copper_um=CU_T * 1e6, ambient=0.0, h_top=H, h_bottom=H, h_side=None, materials=mat)
    p.add_full_copper()
    c = 25.0
    p.add_heater(1, POWER, rect=(c - side_mm / 2, c - side_mm / 2, c + side_mm / 2, c + side_mm / 2), name="U")
    out = {}
    for m in MODELS:
        try:
            r = simulate(p, SolverOptions(models=(m,), cell_mm=cell_mm)).results[m]
            T = np.asarray(r.T)[0]
            ny, nx = T.shape
            xs, ys = (np.arange(nx) + 0.5) * (WIDTH / nx), (np.arange(ny) + 0.5) * (WIDTH / ny)
            h = side_mm * 1e-3 / 2
            mask = (np.abs(xs[None, :] - WIDTH / 2) < h) & (np.abs(ys[:, None] - WIDTH / 2) < h)
            out[m] = float(T[mask].mean())
        except Exception as exc:                                # a model that refuses the board is reported, not hidden
            print(f"  {m}: {type(exc).__name__}: {exc}", file=sys.stderr)
            out[m] = float("nan")
    return out


def main():
    """!
    @brief Print the table and write out/program_vs_coupon.json for the figures.
    @return None.
    """
    rows = {}
    print("| side (mm) | epsilon | independent 3D (K) | " + " | ".join(MODELS) + " |")
    print("| --: | --: | --: | " + " | ".join("--:" for _ in MODELS) + " |")
    for side in SIDES_MM:
        ref = independent(side)
        pr = program(side)
        rows[side] = {"independent": ref, **pr}
        cells = " | ".join(f"{pr[m]:.2f} ({100 * (pr[m] / ref - 1):+.1f} %)" for m in MODELS)
        print(f"| {side:g} | {(side / 50) ** 2:.3f} | {ref:.2f} | {cells} |", flush=True)
    (HERE.parent / "out").mkdir(exist_ok=True)
    (HERE.parent / "out" / "program_vs_coupon.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
