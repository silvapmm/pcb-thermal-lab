#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_independent.py
@brief Study 8: the zoned Lumped, the one-node Lumped, the FVM (0.5 and 0.25 mm) and the program's 3D solid against the independent 3D solver with the barrels drawn, on 40 x 40 mm boards (quadrant, insulated edges).
@details Same boards as study 2 on a 40 x 40 mm board with h_side = 0 and the part and the array centred (the quadrant symmetry of `lib/ref3d.py`, `tests/helpers/layered3d.py`, cell 0.125 mm, four slabs
         per gap). Peak with peak (hottest cell under the part) and mean with mean (mean of the heated cells), in percent of the 3D rise of the part, and the via effect E (no-via board minus the board
         with vias) of the peak. The 3D reference converges at 0.125 mm to about 0.3 % of the rise (0.25 mm: +0.26 %, printed).
Usage: python research/lumped-dense-via-group/scripts/study_independent.py [--only 2L | --only 4L --dx 0.25]   (from the repository root; ONE process; about 1 GB)
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import viastudy as v                                                          # noqa: E402
import ref3d                                                                  # noqa: E402

CASES = [("2L 8 mm, 5x5 @1.0", dict()), ("2L 6 mm, 3x3 @1.0", dict(part=6.0, n=3)), ("2L 10 mm, 8x8 @1.0", dict(part=10.0, n=8)), ("2L 10 mm, 5x5 @1.5", dict(part=10.0, pitch=1.5)),
         ("2L 8 mm, 5x5 @2.0 (array = part)", dict(pitch=2.0)), ("2L 8 mm, 5x5 @1.0, drill 0.6", dict(drill=0.6)), ("2L 8 mm, 5x5 @1.0, filled", dict(filled=True)),
         ("4L 8 mm, 5x5 @1.0", dict(layers=4)), ("4L 10 mm, 5x5 @1.5", dict(layers=4, part=10.0, pitch=1.5)), ("4L 8 mm, 8x8 @0.8 filled", dict(layers=4, n=8, pitch=0.8, filled=True))]


def main():
    """!
    @brief Print the table.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--only", default="", help="run only the cases whose label starts with this text (4L: the four-layer cases)")
    ap.add_argument("--dx", type=float, default=0.125, help="cell of the 3D reference in mm (four-layer cases: 0.25, a 0.125 mm solve took over 10 minutes and was stopped)")
    args = ap.parse_args()
    print("| case | 3D rise K (peak / mean) | FVM 0.5 peak / mean % | FVM 0.25 peak / mean % | 3D solid 0.5 peak / mean % | Lumped zoned peak / mean % | one-node peak / mean % | zoned? | E (3D) K | E: FVM 0.25 / zoned / one-node % |")
    print("| :-- | --: | --: | --: | --: | --: | --: | :-- | --: | --: |")
    for label, kw in CASES:
        if not label.startswith(args.only):
            continue
        a = {**dict(size=(40.0, 40.0)), **kw}
        p, p0 = v.board(**a), v.board(**{**a, "n": 0})
        for q in (p, p0):
            q.board.h_side = 0.0
        t, t0 = ref3d.solve(p, args.dx), ref3d.solve(p0, args.dx)
        amb = p.board.ambient
        rr = lambda r: f"{v.pct(r['parts'][0]['peak'], t['peak'], amb):+.1f} / {v.pct(r['parts'][0]['mean'], t['mean'], amb):+.1f}"
        f5, f25, s3, z, o = (v.run(p, "fvm", 0.5), v.run(p, "fvm", 0.25), v.run(p, "solid3d", 0.5), v.run(p, "lumped", 0.5), v.run(p, "lumped1", 0.5))
        e3 = t0["peak"] - t["peak"]
        e_of = lambda r0, r: (r0["parts"][0]["peak"] - r["parts"][0]["peak"]) / e3 * 100 - 100
        f0, z0 = v.run(p0, "fvm", 0.25), v.run(p0, "lumped1", 0.5)
        info = v.core_info(p, cell=0.5)
        print(f"| {label} | {t['peak']-amb:.1f} / {t['mean']-amb:.1f} | {rr(f5)} | {rr(f25)} | {rr(s3)} | {rr(z)} | {rr(o)} | {info['zoned']} | {e3:.2f} | "
              f"{e_of(f0, f25):+.0f} / {e_of(z0, z):+.0f} / {e_of(z0, o):+.0f} |", flush=True)


if __name__ == "__main__":
    main()
