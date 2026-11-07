#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_reference_cell.py
@brief Does the FVM cell (0.5 against 0.25 mm) change the near-edge errors of the sweep?
@details 16 cases of study_edge_sweep.py (100 x 80 mm; source 5 and 10 mm; edge and corner at gaps 0 and 5 mm; edge film 10 and 200 W/m2K): the Lumped at 0.5 mm (program and potlinks)
         against the FVM at 0.5 and at 0.25 mm (hottest node and footprint mean). Run from the repository root with PCBT_TREE set as for the other studies.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import boards as B  # noqa: E402
import variants as V  # noqa: E402


def main():
    """!
    @brief Print the comparison.
    @return None.
    """
    print("| side | place | gap | h_side | FVM 0.5 -> 0.25 hottest (K) | program % vs 0.5 / vs 0.25 | potlinks % vs 0.5 / vs 0.25 |")
    print("| --: | :-- | --: | --: | --: | --: | --: |")
    rows = []
    for side in (5.0, 10.0):
        for place in ("edge", "corner"):
            for d in (0.0, 5.0):
                for hs in (10.0, 200.0):
                    pos = (d + side / 2, 40.0 if place == "edge" else d + side / 2)
                    p = B.board(100.0, 80.0, side, pos, h_side=hs)
                    key = f"sweep|100.0|80.0|{side}|{place}|{d}|{hs}"
                    a = B.fvm(key, p, 0.5, side, pos)
                    b = B.fvm(key, p, 0.25, side, pos)
                    e = {}
                    for v in ("program", "potlinks"):
                        V.install(v)
                        m, x = B.readout(p, "lumped", 0.5, side, pos)
                        e[v] = (100 * (x / a[1] - 1), 100 * (x / b[1] - 1), 100 * (m / a[0] - 1), 100 * (m / b[0] - 1))
                    rows.append({"side": side, "place": place, "d": d, "hs": hs, "fvm05": a, "fvm025": b, **e})
                    print(f"| {side:g} | {place} | {d:g} | {hs:g} | {a[1]:.2f} -> {b[1]:.2f} | {e['program'][0]:+.1f} / {e['program'][1]:+.1f} | {e['potlinks'][0]:+.1f} / {e['potlinks'][1]:+.1f} |", flush=True)
    B.OUT.mkdir(exist_ok=True)
    (B.OUT / "reference_cell.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
