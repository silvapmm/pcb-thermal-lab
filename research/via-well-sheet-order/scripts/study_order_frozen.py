#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_order_frozen.py
@brief Which boards of the 17 of the frozen-number harness (and the examples) move when the via wells read the sheet after the laminate rule, FVM and FDM at 2 and 1 mm.
@details Prints the hottest-temperature shift in K per board and model, and the boards that do not move (bit-identical or below 1e-8 K, the tolerance of tests/regression).
         Run: `.venv/bin/python research/via-well-sheet-order/scripts/study_order_frozen.py`.
"""

import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "lib"))
import cases                                                                # noqa: E402
import order_patch                                                          # noqa: E402
from pcbthermal import SolverOptions, simulate                              # noqa: E402


def tmax(problem, model, cell):
    """!
    @brief Hottest temperature of one model.
    @param problem Problem.
    @param model Model key.
    @param cell Cell in mm.
    @return float temperature in degC.
    """
    return float(simulate(problem, SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max)


def main():
    """!
    @brief Run every board of the harness and the examples and print the shifts.
    @return None.
    """
    sys.path.insert(0, os.path.join(cases.REPO, "releases", "regression-harness", "lib"))
    import regress_boards as rb
    items = [(n, rb.build(n, os.path.join(cases.REPO, "examples"))) for n in rb.board_names()]
    print("| board | vias | model | cell | T before | shift after (K) |")
    print("| :-- | --: | :-- | --: | --: | --: |")
    for name, p in items:
        for model in ("fvm", "fdm"):
            for c in (2.0, 1.0):
                try:
                    b = tmax(p, model, c)
                    with order_patch.after():
                        a = tmax(p, model, c)
                except Exception as e:                                      # noqa: BLE001
                    print(f"| {name} | {len(p.vias)} | {model} | {c:g} | error {type(e).__name__} | |")
                    continue
                print(f"| {name} | {len(p.vias)} | {model} | {c:g} | {b:.4f} | {a - b:+.5f} |", flush=True)


if __name__ == "__main__":
    main()
