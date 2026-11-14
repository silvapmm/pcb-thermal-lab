#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_link_scale.py
@brief Study 7: the factor on the A-C link resistance of the zoned Lumped that would remove the via-related part of the peak error of each case, measured on a copy.
@details For every case of study 2 where the zones apply: the factor s (bisection on a copy, `lib/variants.py`, the potential sum of eq. 5.7 multiplied by s) at which the zoned peak
         error equals the no-via baseline of the same board (so what is left is the via-related error). If one factor served every case the A-C link would be the cause; the
         table shows how s varies with the core share and the geometry.
Usage: python research/lumped-dense-via-group/scripts/study_link_scale.py   (from the repository root; ONE process; reads out/sweep.json from study_sweep.py --grid)
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import viastudy as v                                                          # noqa: E402
import variants as var                                                        # noqa: E402


def resid(r, s):
    """!
    @brief Via-related residual of the zoned peak (error minus the no-via baseline) with the link scaled by s.
    @param r A row of sweep.json.
    @param s Factor on the A-C potential sum.
    @return float percent of the FVM rise.
    """
    kw = {k: (tuple(x) if isinstance(x, list) else x) for k, x in r["kw"].items()}
    with var.patched(ac_scale=s):
        z = v.run(v.board(**kw), "lumped", 0.5)
    return v.pct(z["parts"][0]["peak"], r["ref_peak"][0], r["amb"]) - r["no_via_err"][0]


def main():
    """!
    @brief Bisect the factor for every zoned case and print it.
    @return None.
    """
    rows = [r for r in json.load(open(os.path.join(os.path.dirname(HERE), "out", "sweep.json"))) if r["zoned"][0]]
    print("| case | core share | resid at s=1 % | s that zeroes it |")
    print("| :-- | --: | --: | --: |")
    for r in rows:
        f1 = resid(r, 1.0)
        lo, hi = 0.1, 10.0
        flo, fhi = resid(r, lo), resid(r, hi)
        s = float("nan")
        if flo * fhi < 0:
            for _ in range(14):
                mid = (lo * hi) ** 0.5
                fm = resid(r, mid)
                if fm * flo > 0:
                    lo, flo = mid, fm
                else:
                    hi, fhi = mid, fm
            s = (lo * hi) ** 0.5
        print(f"| {r['case']} | {r['core']['share']:.2f} | {f1:+.1f} | {s:.2f} |", flush=True)


if __name__ == "__main__":
    main()
