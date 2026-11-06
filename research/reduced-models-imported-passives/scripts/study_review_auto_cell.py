#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review_auto_cell.py
@brief Review check: which cell does the program's Auto give for one powered small part of an imported board, and is the movement of the FVM reference with the cell a cell effect or a pixel effect?
@details Two questions of the review (README chapter 7). (1) Auto: for each designator, the session's `auto_cell()` with only that part powered (the rule of `api.suggest_cell_mm`:
         a quarter of the narrow side of the smallest powered part, clipped to [0.25, 2] mm, capped at 1 mm for imported copper, enlarged by the memory guard) and the FVM peak memory
         the guard estimates at that cell. No solve. (2) The FVM rise of C3 and R5 (RP2040, 1 W) at cells 1, 0.5 and 0.25 mm, once with the automatic pixel of the masks (min(w, cell/10):
         0.1, 0.05, 0.025 mm) and once with the pixel fixed at 0.025 mm, so that the change of the masks with the cell is separated from the change of the cell.
         Output: out/review_auto_cell.csv and out/review_pixel_convergence.csv (git-ignored) and a table on the screen; figure 6 of make_figures.py reads them.
         Run from the repository root with the library linked (one solve at a time, peak about 1.4 GB):
         eval "$(pcb-library/scripts/link_env.sh)"; .venv/bin/python research/reduced-models-imported-passives/scripts/study_review_auto_cell.py
"""

import csv
import resource
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import numpy as np  # noqa: E402

import variants as V  # noqa: E402
from pcbthermal import api, memory  # noqa: E402

AUTO_PARTS = (("rp2040", ("C3", "R5", "C13", "C1", "U1", "U3")), ("oswlight", ("C1", "C11", "U2", "J1")), ("co60", ("R1", "C1", "U1")))
CONV_PARTS = ("C3", "R5")
CELLS = (1.0, 0.5, 0.25)
FIXED_PIXEL = 0.025                    # mm, the automatic pixel at the 0.25 mm cell


def auto_rows():
    """!
    @brief Auto cell and the estimated FVM peak for one powered part at a time.
    @return list of dict rows.
    """
    rows = []
    for board, names in AUTO_PARTS:
        for n in names:
            sx, prob = V.open_board(board, 0.5, [n])
            cell = sx.auto_cell()
            q = V.only_heater(prob, n)
            h = q.heaters[0]
            narrow = min(np.ptp(h.polygon[:, 0]), np.ptp(h.polygon[:, 1])) * 1e3
            v = memory.check(q, ("fvm",), cell, refuse="return", quiet=True)[0]
            rows.append({"board": board, "part": n, "narrow_mm": narrow, "auto_cell": cell, "verdict": v.verdict, "estimate_gb": v.estimate / 2 ** 30,
                         "note": sx.auto_note})
            print("%-8s %-4s narrow side %.2f mm  Auto %.3f mm  FVM estimate %.2f GB (%s) %s" % (board, n, narrow, cell, v.estimate / 2 ** 30, v.verdict, sx.auto_note), flush=True)
    return rows


def conv_rows():
    """!
    @brief FVM rise of the small parts at three cells with the automatic and with a fixed pixel.
    @return list of dict rows.
    """
    rows = []
    for pixel in (None, FIXED_PIXEL):
        for cell in CELLS:
            sx, prob = V.open_board("rp2040", cell, list(CONV_PARTS))
            if pixel:
                sx.pixel_mm = pixel
                prob = sx.build_problem()
            for n in CONV_PARTS:
                q = V.only_heater(prob, n)
                r = api.simulate(q, api.SolverOptions(models=("fvm",), cell_mm=cell)).results["fvm"].t_max - q.board.ambient
                rows.append({"part": n, "cell": cell, "pixel_mode": "fixed" if pixel else "auto", "pixel_mm": sx.effective_pixel(), "rise": r})
                print("cell %-5g pixel %.3f (%s) %-3s FVM rise %.1f K" % (cell, sx.effective_pixel(), "fixed" if pixel else "auto", n, r), flush=True)
    return rows


def write(rows, name):
    """!
    @brief Write rows to out/<name>.
    @param rows List of dict.
    @param name File name.
    @return None.
    """
    out = HERE.parent / "out"
    out.mkdir(exist_ok=True)
    with open(out / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


def main(argv):
    """!
    @brief Run both checks.
    @param argv Unused.
    @return int Exit code.
    """
    write(auto_rows(), "review_auto_cell.csv")
    write(conv_rows(), "review_pixel_convergence.csv")
    print("peak RSS %.2f GB" % (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 30))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
