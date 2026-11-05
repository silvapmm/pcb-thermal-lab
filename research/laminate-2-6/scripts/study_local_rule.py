#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_local_rule.py
@brief Item A of research/laminate-2-6: does a LOCAL laminate rule (more and graded sub-layers only under and around small parts) bring a small part over a thick laminate to the reference at
       a fraction of the cost of a global fine rule? Thick-laminate cases of paper-case-studies (S x S source on W x W, two layers, h = 1e3), FVM at 0.25 mm.
@details Rules compared: the default (0.4 mm, 4 sub-gaps), the global (0.2, 8) and (0.1, 16) options, and local rules of lib/local_laminate.py (trigger, target, cap, grade).
         References: equation 50 on the bare board and the extrapolated 3D numbers of paper-case-studies 16.4 (S = 2 mm, pad and bare); elsewhere the pad board is compared with the global (0.1, 16)
         run only (no independent reference on record), and it is said so in the table.
         Output: a table on stdout and out/study_local_rule.json. Run (repository root, light: at most 0.5 GB, a few minutes):
         .venv/bin/python research/laminate-2-6/scripts/study_local_rule.py [--quick]
"""

import json
import sys

import _boot26

import s2board as B

CONFIGS = {
    "default": dict(),
    "G(0.2,8)": dict(s_max=0.2, n_max=8),
    "G(0.1,16)": dict(s_max=0.1, n_max=16),
    "L1 t.10/.05 cap16": dict(local=dict(trigger=0.10, target=0.05, n_cap=16)),
    "L2 t.10/.05 cap32": dict(local=dict(trigger=0.10, target=0.05, n_cap=32)),
    "L3 t.05/.03 cap32": dict(local=dict(trigger=0.05, target=0.03, n_cap=32)),
    "L4 t.05/.03 cap32 g1.3": dict(local=dict(trigger=0.05, target=0.03, n_cap=32, grade=1.3)),
    "L5 t.05/.05 cap16 g1.3": dict(local=dict(trigger=0.05, target=0.05, n_cap=16, grade=1.3)),
}
CONFIGS2 = {                                   # second round (--round2): the candidate of the first round with its trigger lowered, and the sensitivity to the margin
    "default": dict(),
    "G(0.1,16)": dict(s_max=0.1, n_max=16),
    "L1 t.10/.05 cap16": dict(local=dict(trigger=0.10, target=0.05, n_cap=16)),
    "L6 t.05/.05 cap16": dict(local=dict(trigger=0.05, target=0.05, n_cap=16)),
    "L6 margin x0.5": dict(local=dict(trigger=0.05, target=0.05, n_cap=16, margin_scale=0.5)),
    "L6 margin x2": dict(local=dict(trigger=0.05, target=0.05, n_cap=16, margin_scale=2.0)),
    "L7 t.07/.07 cap16": dict(local=dict(trigger=0.07, target=0.07, n_cap=16)),
}
CASES = [(2.0, 20.0, 0.8), (2.0, 20.0, 1.6), (2.0, 20.0, 3.2), (5.0, 20.0, 0.8), (5.0, 20.0, 1.6), (5.0, 20.0, 3.2), (10.0, 40.0, 1.6), (10.0, 40.0, 3.2)]


def main(argv=None):
    """!
    @brief Run the sweep and print the table.
    @param argv Command line (--quick: only S = 2 mm).
    @return None
    """
    argv = sys.argv[1:] if argv is None else argv
    cases = [c for c in CASES if c[0] == 2.0] if "--quick" in argv else CASES
    global_configs = CONFIGS
    if "--round2" in argv:
        cases = [c for c in CASES if c[0] in (2.0, 5.0) and c[2] >= 0.8 and c[1] == 20.0]
        global_configs = CONFIGS2
    rows = []
    for S, W, t in cases:
        c = B.case(S, t, W=W)
        for pad in (False, True):
            ref, src = B.reference(c, pad)
            g16 = None
            for name, cfg in global_configs.items():
                if name == "G(0.1,16)" and W > 20.0:
                    continue                                # 435 000 unknowns, refused by the memory guard in paper-case-studies 11.3
                r, n, dt = B.run(c, pad, 0.25, **cfg)
                if name == "G(0.1,16)":
                    g16 = r
                rows.append(dict(S=S, W=W, t=t, pad=pad, cfg=name, R=r, unknowns=n, sec=dt, ref=ref, src=src))
    for row in rows:
        base = next(x for x in rows if x["S"] == row["S"] and x["t"] == row["t"] and x["pad"] == row["pad"] and x["cfg"] == "default")
        g = next((x for x in rows if x["S"] == row["S"] and x["t"] == row["t"] and x["pad"] == row["pad"] and x["cfg"] == "G(0.1,16)"), None)
        ref = row["ref"] if row["ref"] is not None else (g["R"] if g else None)
        row["err"] = None if ref is None else (row["R"] / ref - 1.0) * 100.0
        row["cost_u"] = row["unknowns"] / base["unknowns"]
        row["cost_t"] = row["sec"] / max(base["sec"], 1e-9)
    print("S  W   t   board  rule                    R'(K/W)  err%%(vs ref)  unknowns x default  time x default  ref")
    for r in rows:
        print(f"{r['S']:<4g}{r['W']:<4g}{r['t']:<4g}{'pad ' if r['pad'] else 'bare'}  {r['cfg']:<24}{r['R']:9.3f}  {('%+7.2f' % r['err']) if r['err'] is not None else '   n/a'}  "
              f"{r['cost_u']:8.2f}  {r['cost_t']:8.1f}   {r['src'] if r['ref'] is not None else 'vs G(0.1,16)'}")
    (_boot26.OUT / ("study_local_rule2.json" if "--round2" in argv else "study_local_rule.json")).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
