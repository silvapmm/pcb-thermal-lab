#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_outline_and_vias.py
@brief What is left of the Lumped deficit on a uniform sheet after the first ring: the outline (equivalent rectangle) and the vias, on parts of oswlight and RP2040.
@details For a part the uniform variant of reduced-models-imported-passives (one zone per layer at the layer-average fill) is run in three versions: as it is (outline and vias kept), without
         vias, and without vias and without outline (the board becomes its bounding rectangle). FVM, Analytic and Lumped (program and proposal) at 0.5 mm; error = model / FVM - 1 on the
         hottest node. Output: a table. Usage from the repository root (peak under 1 GB):
         eval "$(pcb-library/scripts/link_env.sh)"; QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_outline_and_vias.py
"""

import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE.parents[1] / "reduced-models-imported-passives" / "lib"))

import runner as R  # noqa: E402
import variants as V  # noqa: E402
from pcbthermal import SolverOptions, simulate  # noqa: E402

CASES = [("oswlight", ["SW2", "U5", "J1"]), ("rp2040", ["C3", "U1"])]


def rise(p, model):
    """!
    @brief Rise of the hottest node at 0.5 mm.
    @param p Problem.
    @param model Model key.
    @return float K.
    """
    return simulate(p, SolverOptions(models=(model,), cell_mm=0.5)).results[model].t_max - p.board.ambient


def main():
    """!
    @brief Print the table.
    @return None.
    """
    print("| board | part | variant | FVM (K) | Analytic | Lumped, program | Lumped, proposal |")
    print("| :-- | :-- | :-- | --: | --: | --: | --: |")
    for board, names in CASES:
        _, prob = V.open_board(board, 0.5)
        for n in names:
            u = V.variant(V.only_heater(prob, n), "uniform")
            nv = copy.deepcopy(u)
            nv.vias = []
            vs = {"outline and vias kept": u, "no vias": nv}
            if nv.board.has_outline():
                no = copy.deepcopy(nv)
                no.board.outline = None
                vs["no vias, no outline"] = no
            for k, pp in vs.items():
                f = rise(pp, "fvm")
                a = rise(pp, "analytic")
                cells = []
                for c in ("program", R.PROPOSAL):
                    R.LL.configure(*R.CANDIDATES[c])
                    cells.append(rise(pp, "lumped"))
                print(f"| {board} | {n} | {k} | {f:.1f} | {100 * (a / f - 1):+.1f} % | {100 * (cells[0] / f - 1):+.1f} % | {100 * (cells[1] / f - 1):+.1f} % |", flush=True)


if __name__ == "__main__":
    main()
