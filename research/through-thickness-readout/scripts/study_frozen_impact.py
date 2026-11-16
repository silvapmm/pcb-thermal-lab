#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_frozen_impact.py
@brief How much a surface read-out would move the heater read-outs of the 17 harness boards, and how it compares with the frozen-number tolerance (1e-8 K).

@details For every heater of every board of the regression harness the through-thickness offset of the copper layer (or the metal block) under it is bounded by q'' t / (2 k) with q'' = P / footprint
         area (the warning's bound, an upper bound of the parabolic read-out) and compared with the FVM rise at 2 mm. A read-out that is only ADDED (new arrays) moves no record; a read-out that REPLACES
         the value of the heater rows (`t_max`, `t_mean` under the footprint, Tj) moves every record of a board with a heater by the offset, which is far above 1e-8 K even for 35 um copper.
         Usage: .venv/bin/python research/through-thickness-readout/scripts/study_frozen_impact.py   (about 20 s)
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (ROOT, os.path.join(ROOT, "releases", "regression-harness", "lib")):
    sys.path.insert(0, p)
import regress_boards as RB                                    # noqa: E402
from pcbthermal import fvm                                     # noqa: E402
from pcbthermal.geometry import polygon_area                   # noqa: E402

FROZEN_TOL = 1e-8                                              # K, the tolerance of tests/regression


def main():
    """!
    @brief Print one line per board (largest bound over its heaters) and the totals.
    """
    print("board                 heaters  Cu um   q'' max W/m2   bound max K     rise K   bound % of rise | block")
    worst = 0.0
    data = {}
    n_moved = 0
    rows = 0
    for name in RB.board_names():
        p = RB.build(name)
        if not p.heaters:
            print(f"{name:20s}  (no heater)")
            continue
        r = fvm.solve_steady(p, 2.0)
        rise = r.t_max - p.board.ambient
        k = p.board.materials.k_copper
        best = (0.0, 0.0, 0.0, 0.0)
        for h in p.heaters:
            q = h.power / polygon_area(h.polygon)
            t = float(np.asarray(p.board.copper_thickness)[h.layer])
            b = q * t / (2 * k)
            if b >= best[0]:
                best = (b, q, t, rise)
        blk = ""
        for s in p.heatsinks:
            if s.is_block():
                h = p.heaters[0]
                q = h.power / polygon_area(h.polygon)
                blk = f"| block {1e3 * s.thickness:.1f} mm k {s.k:.0f}: q'' t/2k <= {q * s.thickness / (2 * s.k):.4f} K (the flux into the block is 8 to 21 % of q'')"
        worst = max(worst, best[0])
        data[name] = {"bound_K": best[0], "rise_K": best[3]}
        rows += 1
        n_moved += best[0] > FROZEN_TOL
        print(f"{name:20s} {len(p.heaters):7d} {best[2] * 1e6:6.0f} {best[1]:13.0f} {best[0]:13.6f} {best[3]:10.2f} {100 * best[0] / best[3]:12.5f} % {blk}")
    os.makedirs(os.path.join(HERE, "..", "out"), exist_ok=True)
    with open(os.path.join(HERE, "..", "out", "frozen.json"), "w") as fh:
        json.dump(data, fh, indent=1)
    print(f"\n{n_moved} of {rows} boards with a heater would have a heater read-out moved by more than {FROZEN_TOL} K if the surface replaced the node; largest bound {worst * 1e3:.3f} mK")


if __name__ == "__main__":
    main()
