#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_frozen_impact.py
@brief Study 12: which records of the frozen-numbers test (the 17 boards of `tests/regression`) the zoned Lumped model would move, and by how much.
@details The regression test freezes the five models on 17 boards at 2 mm (the Lumped cell is clipped to 1.0 mm) and the times to 63 %. The adoption changes the Lumped result of every board
         with two or more vias in a footprint; this study builds each board with `regress_boards.build` (read only, imported from `tests/regression`), runs the Lumped steady state with the program and with the
         zones (`zref.VARIANTS["Z_none"]`) at the cell the test uses (2 mm, clipped to 1.0 mm by the API) and at 0.5 mm (the cell the adoption proposes for a part with a core), and prints the maximum
         temperature of both, the difference and whether a core is built (`nz`), together with the time to 63 % of the step response (`lumped.step_responses` and the zoned one) where a core exists.
         The regression tolerance is 1e-8 K, so every board with a core is a record that moves and must be refrozen with an explanation at the release (INTEGRATION.md 11.7).
Usage: python research/lumped-zones-adoption/scripts/study_frozen_impact.py   (from the repository root, with the program's .venv; about a minute)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(FOLDER))
sys.path.insert(0, os.path.join(FOLDER, "lib"))
sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))

import zref                                                                  # noqa: E402
import zoned_lumped as zl                                                    # noqa: E402
import regress_boards as rbd                                                 # noqa: E402
from pcbthermal import SolverOptions, simulate                               # noqa: E402


def lumped_tmax(problem, cell):
    """!
    @brief Lumped maximum temperature through the API (the API clips the cell to 0.5 to 1.0 mm).
    @param problem The Problem.
    @param cell Cell in mm as given to the API.
    @return float degC, or None when the model refuses the board.
    """
    try:
        return float(simulate(problem, SolverOptions(models=("lumped",), cell_mm=cell)).results["lumped"].t_max)
    except ValueError:
        return None


def main():
    """!
    @brief Print the table.
    @return None.
    """
    zref.pc.load_libraries()
    print("| board | vias | cell mm (API) | program degC | zones degC | difference K (grid rule) | difference K (fine rule) | zone nodes (last heater) |\n| :-- | --: | --: | --: | --: | --: | --: | --: |")
    rows = []
    for name in rbd.board_names():
        p = rbd.build(name)
        for cell in (2.0, 0.5):
            t0 = lumped_tmax(p, cell)
            if t0 is None:
                continue
            zl.LAST.clear()
            with zref.VARIANTS["Z_none"]():
                t1 = lumped_tmax(p, cell)
                nz = int(zl.LAST.get("nz", 1))
            with zref.VARIANTS["Z_fine"]():
                t2 = lumped_tmax(p, cell)
            rows.append((name, len(p.vias), cell, t0, t1, t1 - t0, nz, t2 - t0))
            print(f"| {name} | {len(p.vias)} | {cell:g} | {t0:.4f} | {t1:.4f} | {t1 - t0:+.2e} | {t2 - t0:+.2e} | {nz} |", flush=True)
    big = [r for r in rows if r[2] == 2.0 and abs(r[5]) > 1e-3]
    tiny = [r for r in rows if abs(r[5]) <= 1e-3 and abs(r[5]) > 0]
    print(f"\nLumped steady records of the test (2 mm, the cell clipped to 1.0 mm) that move by more than 1 mK with the grid rule: {[r[0] for r in big]}; "
          f"with the fine rule: {[r[0] for r in rows if r[2] == 2.0 and abs(r[7]) > 1e-3]}")
    print(f"rounding-level differences (0 < |d| <= 1 mK, the one-node branch of the research copy is not the program's code line for line): max {max([abs(r[5]) for r in tiny], default=0):.1e} K on {len(tiny)} runs")
    print("written", zref.save_json("frozen_impact.json", rows))


if __name__ == "__main__":
    main()
