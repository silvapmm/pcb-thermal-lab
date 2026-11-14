#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_shift.py
@brief Study 1 and 2: the position noise of the zoned Lumped footprint on a sweep of sub-cell shifts, and the candidate core rules (copy of the program's rules, `lib/placement.py`) on the same sweep.
@details Four groups (3x3 at 1.5 mm under 6 mm, 5x5 at 1.0 under 8, 8x8 at 0.8 under 10, 5x5 at 2.0 under 8: array = part) on the 100 x 80 mm board of `research/lumped-dense-via-group`. The part and the
         array are translated together by k/8 of the 0.5 mm Lumped cell (k = 0..7) along x, along y and along the diagonal (22 placements per group), the board stays. Each placement is run in the
         FVM at 0.5 mm (peak of the hottest cell under the footprint, coverage-weighted mean), the zoned Lumped as in the program and under each candidate rule, the one-node Lumped, and the same
         board without vias (baseline). Errors are in percent of the FVM rise, peak with peak and mean with mean. Results are stored in out/shift.json (git-ignored).
Usage: python research/lumped-zone-placement/scripts/study_shift.py [--group NAME ...]   (from the repository root; ONE process; light, about 1 GB, a few minutes)
"""

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import placement as pl                                                        # noqa: E402
import viastudy as v                                                          # noqa: E402

CELL = 0.5
GROUPS = {"3x3 @1.5, 6 mm": dict(n=3, pitch=1.5, part=6.0), "5x5 @1.0, 8 mm": dict(n=5, pitch=1.0, part=8.0),
          "8x8 @0.8, 10 mm": dict(n=8, pitch=0.8, part=10.0), "5x5 @2.0, 8 mm (vias on the part edge)": dict(n=5, pitch=2.0, part=8.0),
          "5x5 @2.0, 10 mm": dict(n=5, pitch=2.0, part=10.0)}
CANDIDATES = {"program": dict(), "gate": dict(mask="cell", weighted_gate=True), "centre+tol": dict(mask="centre", member_tol=True),
              "vote+tol": dict(mask="vote", member_tol=True), "vote+tol+gate": dict(mask="vote", member_tol=True, weighted_gate=True),
              "vote+tol+gate+fine": dict(mask="vote", member_tol=True, weighted_gate=True, fine="vote"),
              "rule R1 (vote+tol+gate+fine, MAX_CORE 0.8)": dict(mask="vote", member_tol=True, weighted_gate=True, fine="vote", max_core=0.8),
              "program@0.25": dict(zone_cell=0.25), "vote+tol@0.25": dict(mask="vote", member_tol=True, zone_cell=0.25),
              "program@0.125": dict(zone_cell=0.125), "vote+tol@0.125": dict(mask="vote", member_tol=True, zone_cell=0.125)}


def placements():
    """!
    @brief The sub-cell shifts: k/8 of a cell along x (k = 0..7), along y and along the diagonal (k = 1..7).
    @return list of (label, dx mm, dy mm).
    """
    st = CELL / 8.0
    out = [("x", k * st, 0.0) for k in range(8)]
    out += [("y", 0.0, k * st) for k in range(1, 8)] + [("d", k * st, k * st) for k in range(1, 8)]
    return out


def one(a, dx, dy):
    """!
    @brief Run one placement: FVM, every candidate, one node and the baseline.
    @param a Keyword arguments of `viastudy.board`.
    @param dx Shift along x in mm.
    @param dy Shift along y in mm.
    @return dict of readings.
    """
    p = pl.shifted(v.board(**a), dx, dy)
    p0 = pl.shifted(v.board(**{**a, "n": 0}), dx, dy)
    amb = p.board.ambient
    f, f0 = v.run(p, "fvm", CELL), v.run(p0, "fvm", CELL)
    out = {"fvm_peak": f["parts"][0]["peak"] - amb, "fvm_mean": f["parts"][0]["mean"] - amb, "fvm0_peak": f0["parts"][0]["peak"] - amb}
    o, l0 = v.run(p, "lumped1", CELL), v.run(p0, "lumped1", CELL)
    out["one_peak"] = v.pct(o["parts"][0]["peak"], f["parts"][0]["peak"], amb)
    out["one_mean"] = v.pct(o["parts"][0]["mean"], f["parts"][0]["mean"], amb)
    out["base"] = v.pct(l0["parts"][0]["peak"], f0["parts"][0]["peak"], amb)
    g = pl.geometry(p)
    out["geo"] = {k: g[k] for k in ("n_foot", "n_core", "share_coarse", "share_fine", "share_exact", "zoned")}
    for name, kw in CANDIDATES.items():
        with pl.patched(**kw):
            z = v.run(p, "lumped", CELL)
        out[name] = {"peak": v.pct(z["parts"][0]["peak"], f["parts"][0]["peak"], amb), "mean": v.pct(z["parts"][0]["mean"], f["parts"][0]["mean"], amb), "zoned": bool(z["zoned"][0][0])}
    return out


def main():
    """!
    @brief Run the sweep, print the tables and write out/shift.json.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--group", action="append", help="run only these groups (label prefix)")
    args = ap.parse_args()
    res = {}
    for name, a in GROUPS.items():
        if args.group and not any(name.startswith(g) for g in args.group):
            continue
        t0 = time.time()
        res[name] = [{"axis": ax, "dx": dx, "dy": dy, **one(a, dx, dy)} for ax, dx, dy in placements()]
        print(f"# {name}: {time.time() - t0:.0f} s", flush=True)
    os.makedirs(os.path.join(os.path.dirname(HERE), "out"), exist_ok=True)
    with open(os.path.join(os.path.dirname(HERE), "out", "shift.json"), "w") as fh:
        json.dump(res, fh, indent=1)
    report(res)


def report(res):
    """!
    @brief Print the noise table: per group and rule, mean error, spread (max - min), standard deviation and the number of one-node decisions.
    @param res Dict group -> list of placement rows.
    @return None.
    """
    print("\n| group | rule | zoned at | peak err mean % | peak err range (max-min) points | std | mean err mean % | mean err range |")
    print("| :-- | :-- | --: | --: | --: | --: | --: | --: |")
    for name, rows in res.items():
        fv = [r["fvm_peak"] for r in rows]
        print(f"| {name} | FVM rise K (range over shifts) | - | {np.mean(fv):.2f} | {max(fv) - min(fv):.3f} K | - | - | - |")
        o = [r["one_peak"] for r in rows]
        print(f"| {name} | one node | - | {np.mean(o):+.2f} | {max(o) - min(o):.2f} | {np.std(o):.2f} | {np.mean([r['one_mean'] for r in rows]):+.2f} | {np.ptp([r['one_mean'] for r in rows]):.2f} |")
        b = [r["base"] for r in rows]
        print(f"| {name} | no-via baseline | - | {np.mean(b):+.2f} | {max(b) - min(b):.2f} | {np.std(b):.2f} | - | - |")
        for c in CANDIDATES:
            pk = [r[c]["peak"] for r in rows]
            mn = [r[c]["mean"] for r in rows]
            nz = sum(r[c]["zoned"] for r in rows)
            print(f"| {name} | {c} | {nz}/{len(rows)} | {np.mean(pk):+.2f} | {max(pk) - min(pk):.2f} | {np.std(pk):.2f} | {np.mean(mn):+.2f} | {np.ptp(mn):.2f} |")


if __name__ == "__main__":
    main()
