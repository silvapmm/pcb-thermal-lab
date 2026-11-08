#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_independent_3d.py
@brief The simple boards against the independent 3D layered solver: is the FVM a fair reference for the Lumped deficit, and does the proposed first ring move the Lumped to the 3D answer?
@details Board 70 x 70 mm (large enough for the program's first ring to be wide), two copper layers of 35 um (400 W/mK), one FR-4 gap of 1.5 mm with the same conductivity (0.4 W/mK) in every direction (the solver is isotropic per cell), film
         coefficients 10 W/m2K on both faces, insulated edges (the solver has no edge film), a square source of 1 W on the top layer, centred or at (20, 17) mm. The solver is
         research/effective-conductivity/lib/layered3d.py (imports nothing of the program; checked there against Seri Lee's plate, Culham and Yovanovich's coupon and a series circuit). It runs at 0.5 mm with 8 sub-slabs in the gap (a 1 mm source is two cells across: its answer is a cell mean, not converged). The metric is the mean rise over the cells of the source ("mean") because the 3D answer of a source smaller than a few cells is its cell mean; the FVM, the
         Analytic and the Lumped (program and candidate) are read the same way. Output: a table and out/independent_3d.json. Run from the repository root:
         QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_independent_3d.py (a few minutes, peak about 2 GB).
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE.parents[1] / "effective-conductivity" / "lib"))

import layered3d as L3  # noqa: E402
import runner as R  # noqa: E402
from pcbthermal import Problem  # noqa: E402
from pcbthermal.model import Materials  # noqa: E402

W = 70.0
CU_T, GAP, K_CU, K_FR4, H = 35e-6, 1.5e-3, 400.0, 0.4, 10.0
CASES = [(s, p) for p in ((35.0, 35.0), (20.0, 17.0)) for s in (1.0, 3.0, 10.0)]


def reference(side, pos):
    """!
    @brief Mean rise over the source cells in the independent 3D solver.
    @param side Side of the source in mm.
    @param pos Centre in mm.
    @return float K.
    """
    store = R.OUT / "ref3d_store.json"
    kept = json.loads(store.read_text()) if store.exists() else {}
    key = f"{side}|{pos[0]}|{pos[1]}"
    if key in kept:                                            # the 3D solve peaks at 6 GB: it is run once and kept
        return kept[key]
    dx = 0.5e-3
    n = int(round(W * 1e-3 / dx))
    x0, y0 = (pos[0] - side / 2) * 1e-3, (pos[1] - side / 2) * 1e-3
    res = L3.solve(dx, n, n, [(CU_T, K_CU, 1), (GAP, K_FR4, 8), (CU_T, K_CU, 1)], (x0, y0, x0 + side * 1e-3, y0 + side * 1e-3), 1.0, H, H, film_under_source=True)
    kept[key] = res["cell_mean_source"]
    R.OUT.mkdir(exist_ok=True)
    store.write_text(json.dumps(kept))
    return kept[key]


def program(side, pos):
    """!
    @brief The Problem of the same board in the program's builder.
    @param side Side of the source in mm.
    @param pos Centre in mm.
    @return Problem.
    """
    mat = Materials(k_copper=K_CU, k_fr4_through=K_FR4, k_fr4_inplane=K_FR4)
    p = Problem.new(W, W, layers=2, thickness_mm=(2 * CU_T + GAP) * 1e3, copper_um=CU_T * 1e6, ambient=0.0, h_top=H, h_bottom=H, h_side=None, materials=mat)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(pos[0] - side / 2, pos[1] - side / 2, pos[0] + side / 2, pos[1] + side / 2), name="U")
    return p


def main():
    """!
    @brief Print the table and write out/independent_3d.json.
    @return None.
    """
    rows = []
    print("| source (mm) | centre | 3D mean (K) | FVM 0.5 | Analytic | Lumped, program | Lumped, proposal (LRU_PROPOSAL) |")
    print("| --: | :-- | --: | --: | --: | --: | --: |")
    for side, pos in CASES:
        ref = reference(side, pos)
        p = program(side, pos)
        fv = R.readout(p, "fvm", 0.5, side, pos)[0]
        an = R.readout(p, "analytic", 0.5, side, pos)[0]
        lp = R.lumped(p, "program", 0.5, side, pos)[0]
        lc = R.lumped(p, R.PROPOSAL, 0.5, side, pos)[0]
        rows.append({"side": side, "pos": pos, "3d": ref, "fvm": fv, "analytic": an, "program": lp, "candidate": lc})
        e = lambda v: f"{v:.2f} ({100 * (v / ref - 1):+.1f} %)"
        print(f"| {side:g} | {pos} | {ref:.2f} | {e(fv)} | {e(an)} | {e(lp)} | {e(lc)} |", flush=True)
    R.OUT.mkdir(exist_ok=True)
    (R.OUT / "independent_3d.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
