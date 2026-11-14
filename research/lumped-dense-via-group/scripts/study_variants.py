#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_variants.py
@brief Study 5: which rule of the zoned Lumped moves the error against the FVM, measured on a copy (`lib/variants.py`): the cases and the FVM references of study 2, the Lumped re-run under variants.
@details Reads out/sweep.json (run study_sweep.py --grid first: it stores the absolute FVM readings), rebuilds every board, runs the Lumped under each variant and prints, over the
         cases where the program's zoned model applies (and over all cases), the mean, the mean of the absolute values, the largest absolute value and the worst case of the error of the part peak and of the part mean in percent of the FVM rise, and how many cases change zoned or one node.
         The variants: the program as it is; the core mask from the via positions; the core radius CORE_R 0.5 to 1.0; MAX_CORE 0.75 and 0.6; the raster 0.25 mm; the A-C link resistance
         scaled 0.5 to 2.
Usage: python research/lumped-dense-via-group/scripts/study_variants.py   (from the repository root; ONE process)
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import viastudy as v                                                          # noqa: E402
import variants as var                                                        # noqa: E402

VARIANTS = [("program", {}), ("true core mask", dict(true_core=True)), ("CORE_R 0.5", dict(core_r=0.5)), ("CORE_R 0.6", dict(core_r=0.6)), ("CORE_R 0.85", dict(core_r=0.85)),
            ("CORE_R 1.0", dict(core_r=1.0)), ("true mask, CORE_R 0.6", dict(true_core=True, core_r=0.6)), ("true mask, CORE_R 0.85", dict(true_core=True, core_r=0.85)),
            ("MAX_CORE 0.75", dict(max_core=0.75)), ("MAX_CORE 0.6", dict(max_core=0.6)), ("raster 0.25 mm", dict(zone_cell=0.25)), ("raster 0.25 + true mask", dict(zone_cell=0.25, true_core=True)),
            ("A-C link x0.5", dict(ac_scale=0.5)), ("A-C link x1.5", dict(ac_scale=1.5)), ("A-C link x2", dict(ac_scale=2.0))]


def main():
    """!
    @brief Run the variants over the stored cases and print the summary table.
    @return None.
    """
    path = os.path.join(os.path.dirname(HERE), "out", "sweep.json")
    rows = json.load(open(path))
    print("| variant | zoned cases: mean peak % | mean abs | max abs (case) | mean of part mean % | max abs mean % | all cases: mean abs peak | max abs peak | cases zoned / changed |")
    print("| :-- | --: | --: | --: | --: | --: | --: | --: | --: |")
    base_zoned = [bool(r["zoned"][0]) for r in rows]
    for name, opts in VARIANTS:
        e_pk, e_mn, lab, zflags = [], [], [], []
        with var.patched(**opts):
            for r in rows:
                kw = {k: (tuple(x) if isinstance(x, list) else x) for k, x in r["kw"].items()}
                p = v.board(**kw)
                z = v.run(p, "lumped", 0.5)
                amb = r["amb"]
                pk = [v.pct(a["peak"], b, amb) for a, b in zip(z["parts"], r["ref_peak"])]
                mn = [v.pct(a["mean"], b, amb) for a, b in zip(z["parts"], r["ref_mean"])]
                e_pk.append(pk[0]); e_mn.append(mn[0]); lab.append(r["case"]); zflags.append(bool(z["zoned"][0][0]))
        e_pk, e_mn, zf = np.array(e_pk), np.array(e_mn), np.array(zflags)
        sel = zf if zf.any() else np.ones_like(zf)
        w = int(np.argmax(np.abs(np.where(sel, e_pk, 0))))
        changed = int(sum(a != b for a, b in zip(zflags, base_zoned)))
        print(f"| {name} | {e_pk[sel].mean():+.2f} | {np.abs(e_pk[sel]).mean():.2f} | {np.abs(e_pk[sel]).max():.1f} ({lab[w]}) | {e_mn[sel].mean():+.2f} | {np.abs(e_mn[sel]).max():.1f} | "
              f"{np.abs(e_pk).mean():.2f} | {np.abs(e_pk).max():.1f} | {int(zf.sum())} / {changed} |", flush=True)


if __name__ == "__main__":
    main()
