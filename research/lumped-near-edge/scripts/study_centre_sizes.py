#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_centre_sizes.py
@brief Does the candidate (image potentials and potential links) move the Lumped where there is no edge nearby?
@details Centred source of 2 to 30 mm on 100 x 80 and 60 x 60 mm boards, 2 and 4 layers, copper fill 1 and 0.5, edge film 10 W/m2K; error of the hottest node and of the footprint mean against the
         FVM at 0.5 mm for the program and the candidate. Run from the repository root with PCBT_TREE set as for the other studies.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import boards as B  # noqa: E402
import variants as V  # noqa: E402


def main():
    """!
    @brief Print the table.
    @return None.
    """
    rows = []
    print("| board | layers | fill | side mm | program max / mean % | potlinks max / mean % |")
    print("| :-- | --: | --: | --: | --: | --: |")
    for W, H in ((100.0, 80.0), (60.0, 60.0)):
        for layers in (2, 4):
            for fill in (1.0, 0.5):
                for side in (2.0, 5.0, 10.0, 20.0, 30.0):
                    pos = (W / 2, H / 2)
                    p = B.board(W, H, side, pos, layers=layers, fill=fill)
                    fm, fx = B.fvm(f"centre|{W}|{H}|{layers}|{fill}|{side}", p, 0.5, side, pos)
                    e = {}
                    for v in ("program", "potlinks"):
                        V.install(v)
                        m, x = B.readout(p, "lumped", 0.5, side, pos)
                        e[v] = (100 * (x / fx - 1), 100 * (m / fm - 1))
                    rows.append({"W": W, "H": H, "layers": layers, "fill": fill, "side": side, **e})
                    print(f"| {W:g} x {H:g} | {layers} | {fill:g} | {side:g} | {e['program'][0]:+.1f} / {e['program'][1]:+.1f} | {e['potlinks'][0]:+.1f} / {e['potlinks'][1]:+.1f} |", flush=True)
    for v in ("program", "potlinks"):
        a = np.array([r[v][0] for r in rows])
        print(f"{v}: hottest mean {a.mean():+.1f} %, range {a.min():+.1f} .. {a.max():+.1f}, mean abs {np.abs(a).mean():.1f}")
    B.OUT.mkdir(exist_ok=True)
    (B.OUT / "centre_sizes.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
