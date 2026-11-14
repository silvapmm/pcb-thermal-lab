#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge.py
@brief Study 6: the zoned Lumped part with a via group near a board side (the situation of A27, the first link near an edge) over four sub-cell placements, program against the candidate rules and the one-node reading.
@details Two groups (5x5 at 1.0 mm under 8 mm; 8x8 at 0.8 mm under 10 mm) on the 100 x 80 mm board with the edge coefficient of a new project (10 W/m2K), the part and the array moved toward the left side so that
         the gap from the part to the side is 3, 6, 12 and 25 mm, and translated by 0, 0.125, 0.25 and 0.375 mm along the diagonal. Reference: the FVM at 0.5 mm of the same board. Per gap: mean error and
         spread (max - min) of the part peak over the four placements, for the program, the candidate (`vote+tol+gate+fine` at 0.5 and 0.25 mm) and one node. The point is whether the placement noise and the near-edge
         deficit add or are separate, so that a later single Lumped branch can take both.
Usage: python research/lumped-zone-placement/scripts/study_edge.py   (from the repository root; ONE process; about 1.5 GB; takes the heavy-job lock)
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import placement as pl                                                        # noqa: E402
import viastudy as v                                                          # noqa: E402

GROUPS = {"5x5 @1.0, 8 mm": dict(n=5, pitch=1.0, part=8.0), "8x8 @0.8, 10 mm": dict(n=8, pitch=0.8, part=10.0)}
GAPS = (3.0, 6.0, 12.0, 25.0)
SUB = (0.0, 0.125, 0.25, 0.375)
RULES = {"program": dict(), "robust@0.5": dict(mask="vote", member_tol=True, weighted_gate=True, fine="vote"),
         "robust@0.25": dict(mask="vote", member_tol=True, weighted_gate=True, fine="vote", zone_cell=0.25)}


def main():
    """!
    @brief Run and print the table.
    @return None.
    """
    print("| group | gap to the side mm | reading | peak err mean % | range points | mean-with-mean err mean % |")
    print("| :-- | --: | :-- | --: | --: | --: |")
    for name, a in GROUPS.items():
        for gap in GAPS:
            move = gap + a["part"] / 2.0 - 50.0
            acc = {k: ([], []) for k in list(RULES) + ["one node"]}
            for sub in SUB:
                p = pl.shifted(v.board(**a), move + sub, sub)
                amb = p.board.ambient
                f = v.run(p, "fvm", 0.5)
                pk, mn = f["parts"][0]["peak"], f["parts"][0]["mean"]
                for rule, opt in RULES.items():
                    with pl.patched(**opt):
                        z = v.run(p, "lumped", 0.5)
                    acc[rule][0].append(v.pct(z["parts"][0]["peak"], pk, amb))
                    acc[rule][1].append(v.pct(z["parts"][0]["mean"], mn, amb))
                o = v.run(p, "lumped1", 0.5)
                acc["one node"][0].append(v.pct(o["parts"][0]["peak"], pk, amb))
                acc["one node"][1].append(v.pct(o["parts"][0]["mean"], mn, amb))
            for k, (pks, mns) in acc.items():
                print(f"| {name} | {gap:g} | {k} | {np.mean(pks):+.2f} | {np.ptp(pks):.2f} | {np.mean(mns):+.2f} |", flush=True)


if __name__ == "__main__":
    main()
