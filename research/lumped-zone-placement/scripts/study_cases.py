#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cases.py
@brief Study 3: the 66 cases of `research/lumped-dense-via-group` at four placements, with the exact (raster-free) core share, the zoned reading FORCED on every case and the one-node reading, so that any threshold rule can be evaluated afterwards.
@details Per case and placement (the part and the array translated by 0, 0.125, 0.25, 0.375 mm along the diagonal, FVM at 0.5 mm of the translated board as reference, peak with peak, mean with mean,
         percent of the FVM rise) the script stores: the exact share of the footprint within CORE_R d_nn of a via position (`placement.exact_share`), the reading of the program as it is, the zoned reading forced
         on by MAX_CORE = 0.9999 under the program's mask and under the candidate rule (`vote+tol+gate+fine`) at 0.5 and 0.25 mm, and the one-node reading. `report` evaluates a rule "zoned when the
         exact share is at most T, one node otherwise" for T = 0.60 ... 0.95 from these numbers. Output out/cases.json (git-ignored).
Usage: python research/lumped-zone-placement/scripts/study_cases.py   (from the repository root; ONE process; 4-layer cases at 0.5 mm take a few GB; about 10 minutes; takes the heavy-job lock)
"""

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "lumped-dense-via-group", "scripts"))
import placement as pl                                                        # noqa: E402
import viastudy as v                                                          # noqa: E402
import study_sweep as sw                                                      # noqa: E402

SHIFTS = (0.0, 0.125, 0.25, 0.375)
ROB = dict(mask="vote", member_tol=True, weighted_gate=True, fine="vote")


def main():
    """!
    @brief Run the cases and the placements, write out/cases.json and print the report.
    @return None.
    """
    rows = []
    for lab, kw in sw.cases(True):
        a = {**sw.BASE, **kw}
        t0 = time.time()
        for sh in SHIFTS:
            p = pl.shifted(v.board(**a), sh, sh)
            amb = p.board.ambient
            f = v.run(p, "fvm", 0.5)
            pk, mn = f["parts"][0]["peak"], f["parts"][0]["mean"]
            e = lambda r: [v.pct(r["parts"][0]["peak"], pk, amb), v.pct(r["parts"][0]["mean"], mn, amb)]
            row = {"case": lab, "shift": sh, "rise": pk - amb}
            z = v.run(p, "lumped", 0.5)
            row["prog"], row["prog_zoned"] = e(z), bool(z["zoned"][0][0])
            row["one"] = e(v.run(p, "lumped1", 0.5))
            g = pl.geometry(p)
            row["share_prog_coarse"], row["share_prog_fine"] = g["share_coarse"], g["share_fine"]
            with pl.patched(**ROB):
                row["share_exact"] = pl.geometry(p)["share_exact"]
            with pl.patched(max_core=0.9999):
                row["prog_forced"] = e(v.run(p, "lumped", 0.5))
            with pl.patched(**ROB, max_core=0.9999):
                row["rob_forced"] = e(v.run(p, "lumped", 0.5))
            with pl.patched(**ROB, max_core=0.9999, zone_cell=0.25):
                row["rob_forced_025"] = e(v.run(p, "lumped", 0.5))
            rows.append(row)
        print(f"# {lab}: {time.time() - t0:.0f} s", flush=True)
    os.makedirs(os.path.join(os.path.dirname(HERE), "out"), exist_ok=True)
    with open(os.path.join(os.path.dirname(HERE), "out", "cases.json"), "w") as fh:
        json.dump(rows, fh, indent=1)
    report(rows)


def rule_errors(rows, forced_key, thr, idx=0):
    """!
    @brief Errors of the rule "zoned (forced reading) when the exact share is at most thr, one node otherwise" over the rows that have a core.
    @param rows List of case rows.
    @param forced_key Key of the forced zoned reading ('rob_forced' or 'rob_forced_025').
    @param thr Threshold on the exact share.
    @param idx 0 for the peak, 1 for the mean.
    @return list of percent errors.
    """
    out = []
    for r in rows:
        if r["share_exact"] <= 0:
            out.append(r["one"][idx])
        else:
            out.append(r[forced_key][idx] if r["share_exact"] <= thr else r["one"][idx])
    return out


def report(rows):
    """!
    @brief Print the tables: the program per placement, then every threshold rule per placement.
    @param rows Case rows.
    @return None.
    """
    st = lambda xs: f"{np.mean(xs):+.2f} / {np.mean(np.abs(xs)):.2f} / {np.max(np.abs(xs)):.1f}"
    print("\nProgram as it is, per placement (all 66 cases): peak error mean / mean abs / max abs %, zoned cases, mean-with-mean")
    print("| shift | zoned cases | peak | mean |\n| --: | --: | --: | --: |")
    for sh in SHIFTS:
        rs = [r for r in rows if r["shift"] == sh]
        print(f"| {sh} | {sum(r['prog_zoned'] for r in rs)} | {st([r['prog'][0] for r in rs])} | {st([r['prog'][1] for r in rs])} |")
    print("\nRule 'zoned when the exact share <= T': all 66 cases, peak mean / mean abs / max abs % at each placement; spread of one case over the placements (mean, max, points)")
    print("| rule | T | shift 0 | 0.125 | 0.25 | 0.375 | case spread mean / max | zoned (placement 0) |\n| :-- | --: | :-- | :-- | :-- | :-- | --: | --: |")
    labels = sorted({r["case"] for r in rows}, key=lambda c: [r["case"] for r in rows].index(c))
    for key in ("rob_forced", "rob_forced_025"):
        for thr in (0.60, 0.70, 0.75, 0.80, 0.85, 0.92, 0.95):
            cells, spread = [], []
            for sh in SHIFTS:
                rs = [r for r in rows if r["shift"] == sh]
                cells.append(st(rule_errors(rs, key, thr)))
            for lab in labels:
                rs = [r for r in rows if r["case"] == lab]
                ee = rule_errors(rs, key, thr)
                spread.append(max(ee) - min(ee))
            nz = sum(1 for r in rows if r["shift"] == 0.0 and 0 < r["share_exact"] <= thr)
            print(f"| {key} | {thr} | " + " | ".join(cells) + f" | {np.mean(spread):.2f} / {np.max(spread):.1f} | {nz} |")
    spread = []
    for lab in labels:
        rs = [r for r in rows if r["case"] == lab]
        for k in ("prog", "one"):
            spread.append((k, max(r[k][0] for r in rs) - min(r[k][0] for r in rs)))
    for k in ("prog", "one"):
        s = [x for kk, x in spread if kk == k]
        print(f"case spread over the placements, {k}: mean {np.mean(s):.2f}, max {np.max(s):.1f} points")


if __name__ == "__main__":
    main()
