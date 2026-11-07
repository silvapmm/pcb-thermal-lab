#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_frozen_impact.py
@brief Which Lumped records of the frozen-numbers test (the 17 boards of tests/regression) the proposed first ring would move, and by how much; the FVM at 0.5 mm as a check where they move.
@details The proposal (INTEGRATION.md) is a first ring of at most 1.5 cells (the candidate "first 1.5 cells" of lib/runner.py, or the one named in the environment variable LRU_PROPOSAL; the program uses max(1.5 cells, 0.04 rho_max)). It changes a board
         only when 0.04 rho_max exceeds 1.5 cells. This script builds each board with tests/regression/regress_boards.py (read only), runs the Lumped at the cells of the test (2, 1 and
         0.5 mm; the API clips the Lumped cell to 0.5..1 mm) with the program and with the candidate, and prints the maximum temperature of both and the difference. For the boards that move,
         the FVM at 0.5 mm (cached) shows which of the two is nearer. Run from the repository root:
         QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_frozen_impact.py (a few minutes).
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(ROOT / "tests" / "regression"))

import runner as R  # noqa: E402
import regress_boards as rb  # noqa: E402
from pcbthermal import SolverOptions, simulate  # noqa: E402

CELLS = (2.0, 1.0, 0.5)


def tmax(p, cand, cell, model="lumped"):
    """!
    @brief Maximum temperature of the Lumped with a candidate construction.
    @param p Problem.
    @param cand Key of runner.CANDIDATES.
    @param cell Cell of the test in mm.
    @param model Model key.
    @return float degC.
    """
    R.LL.configure(*R.CANDIDATES[cand])
    return simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max


def main():
    """!
    @brief Print the table and write out/frozen_impact.json.
    @return None.
    """
    rows = []
    print("| board | cell | program (degC) | first 1.5 cells | difference (K) | FVM 0.5 mm | rise error: program / candidate (%) |")
    print("| :-- | --: | --: | --: | --: | --: | :-- |")
    for name in rb.board_names():
        p = rb.build(name)
        for cell in CELLS:
            try:
                a = tmax(p, "program", cell)
                b = tmax(p, R.PROPOSAL, cell)
            except Exception as exc:                                        # a board the Lumped refuses is reported, not hidden
                print(f"| {name} | {cell:g} | {type(exc).__name__} | | | | |")
                continue
            d = b - a
            fv, e1, e2 = "", "", ""
            if abs(d) > 1e-6 and cell in (1.0, 0.5):
                key = f"frozen|{name}"
                cache = R._load()
                if f"{key}|0.5" not in cache:
                    cache[f"{key}|0.5"] = [0.0, simulate(p, SolverOptions(models=("fvm",), cell_mm=0.5)).results["fvm"].t_max]
                    R.CACHE.write_text(json.dumps(cache))
                f = cache[f"{key}|0.5"][1]
                amb = p.board.ambient
                fv = f"{f:.2f}"
                e1, e2 = f"{100 * ((a - amb) / (f - amb) - 1):+.1f}", f"{100 * ((b - amb) / (f - amb) - 1):+.1f}"
            rows.append({"board": name, "cell": cell, "program": a, "candidate": b, "diff": d})
            print(f"| {name} | {cell:g} | {a:.4f} | {b:.4f} | {d:+.4f} | {fv} | {e1} / {e2} |", flush=True)
    R.OUT.mkdir(exist_ok=True)
    (R.OUT / "frozen_impact.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
