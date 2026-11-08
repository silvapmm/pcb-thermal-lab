#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_board_size_sweep.py
@brief Does the Lumped deficit on a uniform sheet depend on the size of the board? Sweep of board size, source size and candidates of the ring construction.
@details Question: on a uniform sheet the Lumped reads below the FVM by an amount that the earlier study (reduced-models-imported-passives 3.1) could not explain. Here the sheet
         is simple: a rectangle, layers of uniform copper (fill 1 or 0.6), one square source at the centre, 1 W, edge coefficient 10 W/m2K. The board is varied from 30 x 20 to
         200 x 150 mm and the source from 1 to 20 mm; the Lumped is run as the program runs it and with the candidates of lib/runner.py. The reference is the FVM at 0.5 mm (and at
         0.25 mm for the 1 mm source on the boards up to 100 x 80 mm). Output: a table on the screen and out/sweep_board.json (git-ignored). Run from the repository root:
         QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_board_size_sweep.py (a few minutes, peak under 1.5 GB).
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import runner as R  # noqa: E402
import simple as S  # noqa: E402

BOARDS = [(30, 20), (60, 40), (100, 80), (200, 150)]
SIDES = [1.0, 3.0, 6.0, 10.0, 20.0]


def main():
    """!
    @brief Run the sweep and print the tables.
    @return None.
    """
    rows = []
    cands = list(R.CANDIDATES)
    print("| board | side | FVM hottest (K) | " + " | ".join(cands) + " | Analytic |")
    print("| :-- | --: | --: | " + " | ".join("--:" for _ in cands) + " | --: |")
    for (w, h) in BOARDS:
        for side in SIDES:
            if side > 0.5 * min(w, h):
                continue
            pos = (w / 2.0, h / 2.0)
            p = S.board(w_mm=w, h_mm=h, layers=2, fill=1.0, side_mm=side, pos=pos)
            key = f"b{w}x{h}|s{side}|L2|f1|h10"
            ref_cell = 0.25 if (side <= 3.0 and w * h <= 100 * 80) else 0.5
            fm, fh = R.fvm_reference(key, p, ref_cell, side, pos)
            rec = {"board": [w, h], "side": side, "ref_cell": ref_cell, "fvm_mean": fm, "fvm_hot": fh}
            cells = []
            for c in cands:
                lm, lh = R.lumped(p, c, 0.5, side, pos)
                rec[c] = {"mean": lm, "hot": lh}
                cells.append(f"{100 * (lh / fh - 1):+.1f}")
            am, ah = R.readout(p, "analytic", 0.5, side, pos)
            rec["analytic"] = {"mean": am, "hot": ah}
            rows.append(rec)
            print(f"| {w}x{h} | {side:g} | {fh:.2f} | " + " | ".join(cells) + f" | {100 * (ah / fh - 1):+.1f} |", flush=True)
    R.OUT.mkdir(exist_ok=True)
    (R.OUT / "sweep_board.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
