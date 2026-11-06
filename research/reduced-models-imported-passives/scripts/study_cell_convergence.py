#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cell_convergence.py
@brief Does the FVM reference of the small passives converge with the cell? FVM rise on the imported copper (faces), on the arithmetic cell fill and on the uniform layer sheet at several cells.
@details Question: the error of the reduced models is measured against the FVM on the imported copper; if that number moves with the cell, the percentages carry it. One part at a time with 1 W.
         Run: .venv/bin/python research/reduced-models-imported-passives/scripts/study_cell_convergence.py rp2040 C3,C13,R5,C1,U1,U2,Y1 1,0.5,0.25   (board, designators, cells in mm)
         Peak memory about 1.5 GB at 0.25 mm, one solve at a time. Output also in out/convergence_<board>.csv.
"""

import csv
import resource
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import variants as V  # noqa: E402
from pcbthermal import api  # noqa: E402


def main(argv):
    """!
    @brief Print the FVM rise of each part at each cell on three copper treatments.
    @param argv board, designators, cells.
    @return int Exit code.
    """
    board, names, cells = argv[1], argv[2].split(","), [float(c) for c in argv[3].split(",")]
    rows = []
    for cell in cells:
        sx, prob = V.open_board(board, cell, powers=names)
        for n in names:
            q = V.only_heater(prob, n)
            out = {"board": board, "cell": cell, "part": n}
            for kind in ("imported", "fill", "uniform"):
                v = V.variant(q, kind)
                r = api.simulate(v, api.SolverOptions(models=("fvm",), cell_mm=cell))
                out[kind] = r.results["fvm"].t_max - v.board.ambient
            rows.append(out)
            print("cell %-5g %-4s imported %.1f  fill %.1f  uniform %.1f" % (cell, n, out["imported"], out["fill"], out["uniform"]), flush=True)
    path = HERE.parent / "out" / ("convergence_%s.csv" % board)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print("peak RSS %.2f GB" % (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
