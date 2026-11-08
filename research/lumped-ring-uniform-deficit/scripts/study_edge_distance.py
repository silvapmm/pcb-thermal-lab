#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge_distance.py
@brief The second, smaller cause: a source near a board edge or corner, program against the proposed first ring.
@details Two-layer full-copper 100 x 80 mm board, edge film 10 W/m2K (nearly insulated: 1.6 mm of edge), source of 3 and 10 mm at a distance d from the left edge (centred vertically) and in the
         corner (distance d from both edges). Error = Lumped / FVM - 1 on the hottest node, FVM at 0.5 mm (cached). The ring network lets a ring that an edge clips keep its mean temperature
         as one number, so the hot side of the ring next to the source cannot be shown. Output: a table. Run from the repository root:
         QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_edge_distance.py (about 2 minutes)
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))

import runner as R  # noqa: E402
import simple as S  # noqa: E402


def main():
    """!
    @brief Print the table and write out/edge_distance.json.
    @return None.
    """
    W, H = 100.0, 80.0
    rows = []
    print("| source (mm) | place | distance of the source edge to the board edge (mm) | FVM (K) | program | proposal | Analytic |")
    print("| --: | :-- | --: | --: | --: | --: | --: |")
    for side in (3.0, 10.0):
        for place in ("edge", "corner"):
            for d in (2.0, 5.0, 10.0, 20.0, 40.0):
                cx = d + side / 2
                cy = H / 2 if place == "edge" else d + side / 2
                pos = (cx, cy)
                p = S.board(w_mm=W, h_mm=H, layers=2, fill=1.0, side_mm=side, pos=pos)
                key = f"edge|{side}|{place}|{d}"
                fh = R.fvm_reference(key, p, 0.5, side, pos)[1]
                e = {}
                for c in ("program", R.PROPOSAL):
                    e[c] = 100 * (R.lumped(p, c, 0.5, side, pos)[1] / fh - 1)
                an = 100 * (R.readout(p, "analytic", 0.5, side, pos)[1] / fh - 1)
                rows.append({"side": side, "place": place, "d": d, "fvm": fh, **e, "analytic": an})
                print(f"| {side:g} | {place} | {d:g} | {fh:.2f} | {e['program']:+.1f} | {e[R.PROPOSAL]:+.1f} | {an:+.1f} |", flush=True)
    R.OUT.mkdir(exist_ok=True)
    (R.OUT / "edge_distance.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
