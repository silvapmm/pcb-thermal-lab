#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_published.py
@brief Validation (3): does the finite-element solver reproduce the published spreading cases (Seri Lee's plate: 0.66 / 1.29 / 2.38 K/W; the Culham-Yovanovich
       coupon layer orders: 15.02 / about 11.6 / 8.28 / about 7.4 / 5.00 W/mK) and the repository's finite-volume values for them (0.6679 / 1.2842 / 2.2745 K/W;
       14.67 / 11.30 / 7.81 / 6.99 / 4.74 W/mK, `research/effective-conductivity`)?
@details Run from the repository root: `.venv/bin/python research/independent-fem-edge/scripts/study_published.py` (a few minutes, under 1 GB). Writes `research/independent-fem-edge/out/published.json`.
         Reading status: the published numbers are taken from `research/effective-conductivity/README.md` 4.2 and 4.4 and `study_culham_1998.py` (status S for
         this folder: the papers themselves were not reopened here).
"""

import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import cases                                                            # noqa: E402
import refine                                                           # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out", "published.json")
PAPER_LEE = {"centre": 0.66, "edge midpoint": 1.29, "corner": 2.38}
REPO_LEE = {"centre": 0.6679, "edge midpoint": 1.2842, "corner": 2.2745}
PAPER_CULHAM = {1: 15.02, 2: 11.6, 3: 8.28, 4: 7.4, 5: 5.00}
REPO_CULHAM = {1: 14.67, 2: 11.30, 3: 7.81, 4: 6.99, 5: 4.74}


def main():
    """!
    @brief Run both cases and print the tables.
    @return None.
    """
    res = {"lee": {}, "culham": {}}
    print("== Seri Lee's plate: Rc (K/W) by mesh (fine size near the source edges, mm), observed order, extrapolation")
    for pos in ("centre", "edge midpoint", "corner"):
        hs = (2.0, 1.0, 0.5) if pos != "centre" else (2.0, 1.0, 0.5, 0.25)
        vals, ns = [], []
        for hf in hs:
            t = time.time()
            b, read = cases.lee_plate(pos, hf=hf)
            r = b.solve()
            vals.append(read(r))
            ns.append(r["n"])
            print(f"   {pos:14s} hf {hf:5.2f} n {r['n']:7d} Rc {vals[-1]:.5f} balance {r['balance'] - 1:+.1e} peak {r['peak_gb']:.2f} GB {time.time() - t:.0f} s", flush=True)
        ri = refine.richardson(vals[-3:])
        res["lee"][pos] = {"hf": hs, "Rc": vals, "n": ns, "p": ri["p"], "ext": ri["ext"], "gci": ri["gci"]}
        print(f"   {pos:14s} p {ri['p']:.2f} ext {ri['ext']:.4f} GCI {100 * ri['gci']:.2f} %  paper {PAPER_LEE[pos]}  ({100 * (ri['ext'] / PAPER_LEE[pos] - 1):+.1f} %)  repo FV {REPO_LEE[pos]} ({100 * (ri['ext'] / REPO_LEE[pos] - 1):+.2f} %)", flush=True)
        json.dump(res, open(OUT, "w"), indent=1)
    print("== Culham-Yovanovich coupon: R_solid (K/W) and effective conductivity (W/mK) of the five layer orders, quarter domain")
    for case, layers in cases.CULHAM_LAYERS.items():
        row = {}
        for hf in (1.0, 0.5):
            t = time.time()
            b, read = cases.culham_block(layers, hf=hf)
            r = b.solve()
            rs = read(r)
            total = sum(tk[0] for tk in layers)
            ke = cases.culham_effective(rs, hf=hf, total=total)
            row[str(hf)] = {"R_solid": rs, "k_eff": ke, "n": r["n"], "balance": r["balance"]}
            print(f"   case {case} hf {hf:4.2f} n {r['n']:6d} R_solid {rs:.5f} k_eff {ke:.3f}  paper {PAPER_CULHAM[case]} ({100 * (ke / PAPER_CULHAM[case] - 1):+.1f} %)  repo FV {REPO_CULHAM[case]} ({100 * (ke / REPO_CULHAM[case] - 1):+.1f} %)  {time.time() - t:.0f} s", flush=True)
        res["culham"][str(case)] = row
        json.dump(res, open(OUT, "w"), indent=1)


if __name__ == "__main__":
    main()
