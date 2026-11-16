#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_independent_shift.py
@brief Study 4: the zoned Lumped over the sub-cell shifts against the INDEPENDENT 3D solver (`research/lumped-dense-via-group/lib/ref3d.py`, `tests/helpers/layered3d.py`), which does not depend on the Lumped raster.
@details The 3D reference needs the part and the array centred on a 40 x 40 mm board with insulated sides (quadrant symmetry), so it is computed ONCE per group at the centred placement; the Lumped is
         then run with the part and the array translated along the diagonal by k/8 of 0.5 mm (k = 0..7), the board staying (the translation of at most 0.44 mm changes the distance to an insulated side by
         about 2 %, a negligible change of the reference, stated). Rules: the program, the candidate (`vote+tol+gate+fine`), the program at 0.25 and 0.125 mm and the candidate at 0.25 mm. Peak with peak and
         mean with mean, percent of the 3D rise.
Usage: python research/lumped-zone-placement/scripts/study_independent_shift.py [--dx 0.25]   (from the repository root; ONE process; about 1 GB; takes the heavy-job lock)
"""

import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import placement as pl                                                        # noqa: E402
import viastudy as v                                                          # noqa: E402
import ref3d                                                                  # noqa: E402

GROUPS = {"3x3 @1.5, 6 mm": dict(n=3, pitch=1.5, part=6.0), "5x5 @1.0, 8 mm": dict(n=5, pitch=1.0, part=8.0), "8x8 @0.8, 10 mm": dict(n=8, pitch=0.8, part=10.0)}
RULES = {"program": dict(), "robust@0.5": dict(mask="vote", member_tol=True, weighted_gate=True, fine="vote"), "program@0.25": dict(zone_cell=0.25),
         "robust@0.25": dict(mask="vote", member_tol=True, weighted_gate=True, fine="vote", zone_cell=0.25), "program@0.125": dict(zone_cell=0.125)}


def main():
    """!
    @brief Run and print the table.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--dx", type=float, default=0.25, help="cell of the 3D reference in mm")
    args = ap.parse_args()
    print("| group | 3D rise K (peak / mean) | rule | peak err mean % | range points | mean err mean % | range |")
    print("| :-- | --: | :-- | --: | --: | --: | --: |")
    for name, kw in GROUPS.items():
        a = {**kw, "size": (40.0, 40.0)}
        p = v.board(**a)
        p.board.h_side = 0.0
        t = ref3d.solve(p, args.dx)
        amb = p.board.ambient
        out = {k: ([], []) for k in RULES}
        one = ([], [])
        for k in range(8):
            q = pl.shifted(v.board(**a), k * 0.0625, k * 0.0625)
            q.board.h_side = 0.0
            for rule, opt in RULES.items():
                with pl.patched(**opt):
                    z = v.run(q, "lumped", 0.5)
                out[rule][0].append(v.pct(z["parts"][0]["peak"], t["peak"], amb))
                out[rule][1].append(v.pct(z["parts"][0]["mean"], t["mean"], amb))
            o = v.run(q, "lumped1", 0.5)
            one[0].append(v.pct(o["parts"][0]["peak"], t["peak"], amb))
            one[1].append(v.pct(o["parts"][0]["mean"], t["mean"], amb))
        print(f"| {name} | {t['peak'] - amb:.2f} / {t['mean'] - amb:.2f} | one node | {np.mean(one[0]):+.2f} | {np.ptp(one[0]):.2f} | {np.mean(one[1]):+.2f} | {np.ptp(one[1]):.2f} |", flush=True)
        for rule, (pk, mn) in out.items():
            print(f"| {name} | | {rule} | {np.mean(pk):+.2f} | {np.ptp(pk):.2f} | {np.mean(mn):+.2f} | {np.ptp(mn):.2f} |", flush=True)


if __name__ == "__main__":
    main()
