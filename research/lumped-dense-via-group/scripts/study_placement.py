#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_placement.py
@brief Study 9 (review): do the errors of the zoned Lumped depend on where the part and the via array fall on the 0.5 mm raster, and does the MAX_CORE 0.75 candidate survive a shift?
@details The 66 cases of study 2 are re-run with the part and the array translated together by s = 0, 0.125, 0.25 and 0.375 mm in x and in y (s = 0 is the placement of study 2:
         the array centre on a raster corner, the part edges on cell lines). Each placement is compared with the FVM at 0.5 mm of the same translated board. Per placement the script
         prints the zoned and one-node part-peak errors (mean, mean of the absolute value, largest absolute value, percent of the FVM rise), then the effect of MAX_CORE 0.75
         (a copy, `lib/variants.py`) on the same placement, then the per-case spread of the zoned error over the four placements. With `--cell` it also prints four cases against
         the FVM at 0.5 and 0.25 mm (is the reference converged on the regimes?); with `--edge` only the two regimes of study 6 at the four placements.
Usage: python research/lumped-dense-via-group/scripts/study_placement.py [--cell | --edge]   (from the repository root; ONE process; about 1.7 GB; 6 minutes)
"""

import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, HERE)
import viastudy as v                                                          # noqa: E402
import variants                                                               # noqa: E402
import study_sweep as s                                                       # noqa: E402

SHIFTS = (0.0, 0.125, 0.25, 0.375)


def shifted(p, d_mm):
    """!
    @brief Translate every part and every via of a problem by the same amount in x and in y.
    @param p Problem (changed in place).
    @param d_mm Translation in mm.
    @return Problem p.
    """
    d = d_mm * 1e-3
    for h in p.heaters:
        h.polygon = h.polygon + d
    for x in p.vias:
        x.x += d
        x.y += d
    return p


def stats(xs):
    """!
    @brief Mean, mean of the absolute value and largest absolute value of a list of errors.
    @param xs Errors in percent.
    @return str.
    """
    a = np.asarray(xs)
    return f"{a.mean():+.2f} / {np.abs(a).mean():.2f} / {np.abs(a).max():.1f}"


def cell_check():
    """!
    @brief Four cases (both regimes, the densest worst case, the base) against the FVM at 0.5 and 0.25 mm.
    @return None.
    """
    print("| case | FVM cell | zoned peak % | zoned mean % | one-node peak % | no-via baseline % | zoned minus baseline |")
    print("| :-- | --: | --: | --: | --: | --: | --: |")
    for lab, kw in (("pitch 2.0, part 8", dict(pitch=2.0)), ("pitch 1.5, part 8.5", dict(pitch=1.5, part=8.5)), ("8 x 8 at 1.0, part 10", dict(part=10.0, n=8)), ("base", dict())):
        a = {**s.BASE, **kw}
        p, p0 = v.board(**a), v.board(**{**a, "n": 0})
        z, o, l0 = v.run(p, "lumped", 0.5), v.run(p, "lumped1", 0.5), v.run(p0, "lumped1", 0.5)
        amb = p.board.ambient
        for c in (0.5, 0.25):
            f, f0 = v.run(p, "fvm", c), v.run(p0, "fvm", c)
            zp = v.pct(z["parts"][0]["peak"], f["parts"][0]["peak"], amb)
            b = v.pct(l0["parts"][0]["peak"], f0["parts"][0]["peak"], amb)
            print(f"| {lab} | {c} | {zp:+.2f} | {v.pct(z['parts'][0]['mean'], f['parts'][0]['mean'], amb):+.2f} | "
                  f"{v.pct(o['parts'][0]['peak'], f['parts'][0]['peak'], amb):+.2f} | {b:+.2f} | {zp - b:+.2f} |", flush=True)


def edge_check():
    """!
    @brief The two regimes of study 6 (pitch 2.0 under 7.5 to 8.1 mm, pitch 1.5 under 8.5 to 11 mm) at the four placements.
    @return None.
    """
    print("| pitch | part | zoned peak % at shift 0 / 0.125 / 0.25 / 0.375 (* = one node) | one-node peak % at the same shifts |")
    print("| --: | --: | :-- | :-- |")
    for pitch, parts in ((2.0, (7.5, 8.0, 8.1)), (1.5, (8.5, 10.0, 11.0))):
        for part in parts:
            zs, os_ = [], []
            for sh in SHIFTS:
                p = shifted(v.board(2, 5, pitch, 0.3, part), sh)
                f, z, o = v.run(p, "fvm", 0.5), v.run(p, "lumped", 0.5), v.run(p, "lumped1", 0.5)
                amb, pk = f["amb"], f["parts"][0]["peak"]
                zs.append(f"{v.pct(z['parts'][0]['peak'], pk, amb):+.1f}{'' if z['zoned'][0][0] else '*'}")
                os_.append(f"{v.pct(o['parts'][0]['peak'], pk, amb):+.1f}")
            print(f"| {pitch} | {part} | {' / '.join(zs)} | {' / '.join(os_)} |", flush=True)


def main():
    """!
    @brief Run the placements and print the tables.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--cell", action="store_true", help="also print four cases against the FVM at 0.5 and 0.25 mm")
    ap.add_argument("--edge", action="store_true", help="print only the two regimes of study 6 at the four placements")
    args = ap.parse_args()
    if args.edge:
        edge_check()
        return
    if args.cell:
        cell_check()
    cases = s.cases(True)
    table = {}
    print("| shift mm | zoned cases | zoned peak: mean / mean abs / max abs % | one-node peak (same cases) | baseline mean % | MAX_CORE 0.75: zoned cases | MAX_CORE 0.75 all 66: max abs % | cases moved by 0.75 (before -> after %) |")
    print("| --: | --: | --: | --: | --: | --: | --: | :-- |")
    for sh in SHIFTS:
        rows = []
        for lab, kw in cases:
            a = {**s.BASE, **kw}
            p, p0 = shifted(v.board(**a), sh), shifted(v.board(**{**a, "n": 0}), sh)
            f, z, o = v.run(p, "fvm", 0.5), v.run(p, "lumped", 0.5), v.run(p, "lumped1", 0.5)
            f0, l0 = v.run(p0, "fvm", 0.5), v.run(p0, "lumped1", 0.5)
            with variants.patched(max_core=0.75):
                z75 = v.run(p, "lumped", 0.5)
            amb = f["amb"]
            pk = f["parts"][0]["peak"]
            rows.append(dict(case=lab, zoned=bool(z["zoned"][0][0]), zp=v.pct(z["parts"][0]["peak"], pk, amb), op=v.pct(o["parts"][0]["peak"], pk, amb),
                             base=v.pct(l0["parts"][0]["peak"], f0["parts"][0]["peak"], amb), z75=v.pct(z75["parts"][0]["peak"], pk, amb), zoned75=bool(z75["zoned"][0][0]),
                             share=v.core_info(p)["share"]))
        table[sh] = rows
        zz = [r for r in rows if r["zoned"]]
        moved = [f"{r['case']} {r['zp']:+.1f} -> {r['z75']:+.1f}" for r in rows if abs(r["z75"] - r["zp"]) > 1e-9]
        print(f"| {sh} | {len(zz)} | {stats([r['zp'] for r in zz])} | {stats([r['op'] for r in zz])} | {np.mean([r['base'] for r in zz]):+.2f} | "
              f"{sum(r['zoned75'] for r in rows)} | {np.abs([r['z75'] for r in rows]).max():.1f} | {'; '.join(moved)} |", flush=True)
    print()
    print("| case | zoned peak % at shift 0 / 0.125 / 0.25 / 0.375 (* = one node by the rule) | core share on the 0.5 mm raster | spread (points) |")
    print("| :-- | :-- | :-- | --: |")
    spread = []
    for i, (lab, _) in enumerate(cases):
        rs = [table[sh][i] for sh in SHIFTS]
        zp = [r["zp"] for r in rs]
        spread.append((max(zp) - min(zp), lab, " / ".join(f"{r['zp']:+.1f}{'' if r['zoned'] else '*'}" for r in rs), " / ".join(f"{r['share']:.2f}" for r in rs)))
    for sp, lab, txt, sha in sorted(spread, reverse=True)[:12]:
        print(f"| {lab} | {txt} | {sha} | {sp:.1f} |")


if __name__ == "__main__":
    main()
