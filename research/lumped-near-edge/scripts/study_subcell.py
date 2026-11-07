#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_subcell.py
@brief The Lumped model for a part smaller than its raster cell (sub-cell footprint spread).
@details 24 x 24 mm, two layers of 35 um full copper, a square source of 0.1 to 2 mm of 1 W on layer 1 at the board centre shifted by 0 / 0.125 / 0.25 mm inside the cell. Reference: the FVM at
         0.0625 mm (hottest node). Compared: the FVM at 0.5 mm (same grid as the Lumped), the Lumped as the program has it and with the spreading term inside the cell ("subcell":
         the hottest rise gets lat ln(sqrt(A_cells / A_part)) / (2 pi S) when the part covers less than the cells it touches). Output: a table and out/subcell.json. Run from the repository root:
         PCBT_TREE=<checkout of feature/integration-260> QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-near-edge/scripts/study_subcell.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import boards as B  # noqa: E402
import variants as V  # noqa: E402


def main():
    """!
    @brief Print the sub-cell table.
    @return None.
    """
    rows = []
    print("| side mm | shift mm | FVM 0.0625 (K) | FVM 0.5 % | Lumped program % | Lumped subcell % |")
    print("| --: | --: | --: | --: | --: | --: |")
    for side in (0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 2.0):
        for sh in (0.0, 0.125, 0.25):
            pos = (12.0 + sh, 12.0 + sh)
            p = B.board(24.0, 24.0, side, pos, h_side=10.0)
            ref = B.fvm(f"sub|{side}|{sh}", p, 0.0625, side, pos)[1]
            half = B.fvm(f"sub|{side}|{sh}", p, 0.5, side, pos)[1]
            e = {}
            for v in ("program", "subcell"):
                V.install(v)
                e[v] = 100 * (B.readout(p, "lumped", 0.5, side, pos)[1] / ref - 1)
            rows.append({"side": side, "shift": sh, "ref": ref, "fvm05": 100 * (half / ref - 1), **e})
            print(f"| {side:g} | {sh:g} | {ref:.2f} | {100 * (half / ref - 1):+.1f} | {e['program']:+.1f} | {e['subcell']:+.1f} |", flush=True)
    B.OUT.mkdir(exist_ok=True)
    (B.OUT / "subcell.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
