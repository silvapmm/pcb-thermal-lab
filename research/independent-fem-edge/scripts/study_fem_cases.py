#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fem_cases.py
@brief Do the earlier edge, cut-cell and laminate conclusions hold against a different METHOD? Finite-element solves of four canonical cooled-wall boards with mesh convergence, the cell-centred finite-volume references and the program.
@details Commands (run from the repository root with `.venv/bin/python research/independent-fem-edge/scripts/study_fem_cases.py <command>`; one heavy job at a time, each solve under 2.5 GB):
         * `fem`      the finite-element solves, cached in `out/fem_cache.jsonl`: plate (a), via (b), 20 mm square (c), T outline (d), plan and through-thickness refinement sequences;
         * `fv`       the finite-volume references of the repository on the same boards (`strong-edge-laminate/lib/ref3d.py` at 1/4 and 1/8 mm, stored truths of `imported-copper-edge-film`), `out/fv.json`;
         * `prog`     the program (this tree) on the boards: plate and via with the simple and the physical stack-up, default and 8 sub-gaps; the squares and the T turned and shifted, `out/prog.json`;
         * `report`   tables from the caches (Richardson, GCI, errors).
"""

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(FOLDER, "..", ".."))
sys.path.insert(0, os.path.join(FOLDER, "lib"))
sys.path.insert(0, ROOT)
import conv                                                                    # noqa: E402

OUT = os.path.join(FOLDER, "out")
H_STRONG = (10.0, 200.0, 1000.0)
PLAN = (0.2, 0.1, 0.05)                                                        # plan refinement sequence (ratio 2), mm, near walls, source and via
VIA_PLAN = (0.28, 0.14, 0.07)                                                  # the via sequences stay below 4 GB: the fine zone around the via adds nodes
NG = (4, 8, 16)                                                                # bricks per gap


def fem():
    """!
    @brief Run the finite-element solves (cached) in the order coarse to fine, one at a time.
    @return None.
    """
    for h in H_STRONG:
        for hf in PLAN:                                                        # plan sequence at 8 bricks per gap
            r = conv.solve("strong", h_side=h, hf=hf, n_gap=8)
            print("plate", h, "hf", hf, "ng 8", round(r["tmax"], 4), r["n"], round(r["peak_gb"], 2), r["seconds"], flush=True)
        for ng in (4, 16):                                                     # through-thickness sequence at hf 0.1
            r = conv.solve("strong", h_side=h, hf=0.1, n_gap=ng)
            print("plate", h, "hf 0.1 ng", ng, round(r["tmax"], 4), r["n"], round(r["peak_gb"], 2), r["seconds"], flush=True)
    for h in (200.0, 1000.0):
        for d in (None, 0.16, 3.0):
            for hf in VIA_PLAN:
                try:
                    r = conv.solve("strong", h_side=h, hf=hf, n_gap=8, **({} if d is None else dict(via_dist=d)))
                except MemoryError as e:
                    print("skipped", e)
                    continue
                print("via", h, d, "hf", hf, round(r["tmax"], 4), r["n"], round(r["peak_gb"], 2), r["seconds"], flush=True)
    for case in ("square", "tout"):
        for kw in ([dict(inset=0.0, h_side=h) for h in (200.0, 1000.0)] + [dict(inset=1.2, h_side=h) for h in (10.0, 200.0, 1000.0)] if case == "square" else [dict(h_side=200.0)]):
            for hf in (0.4, 0.2, 0.1):
                try:
                    r = conv.solve(case, hf=hf, n_gap=8, **kw)
                except MemoryError as e:
                    print("skipped", e)
                    continue
                print(case, kw, "hf", hf, round(r["mean"], 4), r["n"], round(r["peak_gb"], 2), r["seconds"], flush=True)


def seq(case, key, vals, **kw):
    """!
    @brief Richardson analysis of a plan-refinement sequence.
    @param case Board.
    @param key Result key ('tmax' or 'mean').
    @param vals Fine sizes coarse to fine.
    @param kw Fixed arguments.
    @return dict from `conv.richardson` plus the three values.
    """
    f = [conv.solve(case, hf=v, **kw)[key] for v in vals]
    out = conv.richardson(*f)
    out["f"] = f
    return out


def report():
    """!
    @brief Print the convergence tables from the caches.
    @return None.
    """
    print("plate: tmax (K) by plan size, ng 8; Richardson; z sequence at hf 0.1")
    for h in H_STRONG:
        a = seq("strong", "tmax", PLAN, h_side=h, n_gap=8)
        z = [conv.solve("strong", h_side=h, hf=0.1, n_gap=n)["tmax"] for n in NG]
        print(f"  h {h:6.0f}: plan {[round(v, 4) for v in a['f']]} p {a['p']:.2f} ext {a['ext']:.4f} GCI {100 * a['gci']:.2f} %   z(4/8/16) {[round(v, 4) for v in z]}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "fem":
        fem()
    elif cmd == "report":
        report()
    else:
        raise SystemExit(__doc__)
