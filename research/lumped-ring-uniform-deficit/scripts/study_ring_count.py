#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_ring_count.py
@brief Do more rings, without the merge of thin rings, cure the deficit? (they do not: they make the Lumped hot and unstable.)
@details Centred sources of 1, 3 and 10 mm on 60 x 40, 100 x 80 and 200 x 150 mm uniform two-layer boards and five places near an edge or a corner of the 100 x 80 board; Lumped hottest node against
         the FVM (cached by lib/runner.py) with the first ring at 1.5 cells and 10 rings with the merge (the proposal's reference), and with 20, 40 and 80 rings and the merge switched off
         (`min_width` 0). Output: a table. Run from the repository root: QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_ring_count.py (about a minute from the cache)
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import runner as R  # noqa: E402
import simple as S  # noqa: E402

CONFIGS = [("10 rings, merge", ("strip", 0.0, 1.5, None), 10), ("20 rings, no merge", ("strip", 0.0, 1.5, None, True, True, 0.0), 20),
           ("40 rings, no merge", ("strip", 0.0, 1.5, None, True, True, 0.0), 40), ("80 rings, no merge", ("strip", 0.0, 1.5, None, True, True, 0.0), 80)]


def main():
    """!
    @brief Print the table.
    @return None.
    """
    cases = []
    for (w, h) in ((60, 40), (100, 80), (200, 150)):
        for side in (1.0, 3.0, 10.0):
            cases.append((w, h, side, (w / 2, h / 2), f"b{w}x{h}|s{side}|L2|f1|h10"))
    for side, place, d in ((3.0, "corner", 5.0), (3.0, "edge", 5.0), (10.0, "corner", 5.0), (3.0, "corner", 20.0), (10.0, "edge", 10.0)):
        cases.append((100, 80, side, (d + side / 2, 40.0 if place == "edge" else d + side / 2), f"edge|{side}|{place}|{d}"))
    print("| case | FVM (K) | " + " | ".join(c[0] for c in CONFIGS) + " |")
    print("| :-- | --: | " + " | ".join("--:" for _ in CONFIGS) + " |")
    for (w, h, side, pos, key) in cases:
        p = S.board(w_mm=w, h_mm=h, layers=2, fill=1.0, side_mm=side, pos=pos)
        ref_cell = 0.25 if (key.startswith("b") and side <= 3 and w * h <= 8000) else 0.5
        fh = R.fvm_reference(key, p, ref_cell, side, pos)[1]
        vals = []
        for _, args, rings in CONFIGS:
            R.LL.configure(*args)
            vals.append(100 * (R.readout(p, "lumped", 0.5, side, pos, lumped_rings=rings)[1] / fh - 1))
        print(f"| {key} | {fh:.1f} | " + " | ".join(f"{v:+.1f}" for v in vals) + " |", flush=True)


if __name__ == "__main__":
    main()
