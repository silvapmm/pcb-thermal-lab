#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file runner.py
@brief The common measurement of the studies: the program's FVM (or a rule) against the resolved reference on a spec, with a disk cache of the reference and the error in percent.
@details `reference(spec, ...)` solves the resolved 3D solver once per (board, grid, sub-slabs, grading) and keeps the answer in out/ref_cache.json (git-ignored), the key being the text of the
         spec and the grid. `fvm_peak(spec, rule, cell_mm)` builds the program's network with a rule (lib/gapnet.py), solves it directly and returns the peak under the parts with and without the
         face term, the unknowns and the flagged cells. `err(a, b)` is the signed error in percent of the rise. All peaks are rises above the ambient in K.
"""

import json
import time
from pathlib import Path

import boards as BD
import gapnet as GN
import ref3d as R3
import rule as RU

HERE = Path(__file__).resolve().parents[1]
CACHE = HERE / "out" / "ref_cache.json"


def _load():
    """!
    @brief The reference cache.
    @return dict.
    """
    try:
        return json.loads(CACHE.read_text())
    except Exception:
        return {}


def reference(spec, dx_mm=0.25, nsub=8, ratio=1.0, quadrant=None):
    """!
    @brief Resolved reference peak of a spec, cached.
    @param spec A boards.Spec.
    @param dx_mm Cell size in mm.
    @param nsub Sub-slabs per gap.
    @param ratio Grading.
    @param quadrant See ref3d.setup.
    @return dict with max (face), mean, max_centre, unknowns, balance.
    """
    key = json.dumps([repr(spec), dx_mm, nsub, ratio, quadrant], sort_keys=True)
    cache = _load()
    if key in cache:
        return cache[key]
    p = BD.problem(spec)
    r = R3.solve_spec(spec, p, dx_mm, nsub, ratio, quadrant)
    out = {k: r[k] for k in ("max", "mean", "max_centre", "unknowns", "balance")}
    cache[key] = out
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache))
    return out


def err(a, b):
    """!
    @brief Signed error of a against b in percent of b.
    @param a Value under test (a rise in K).
    @param b Reference (a rise in K).
    @return float.
    """
    return 100.0 * (a / b - 1.0)


def fvm_peak(spec, rule, cell_mm, p=None, fill=None, solver="direct"):
    """!
    @brief The program's FVM with the laminate nodes of a rule: peak under the part, unknowns, flagged cells, time.
    @param spec A boards.Spec (or None when `p` is given).
    @param rule A rule.Rule.
    @param cell_mm Cell size in mm.
    @param p The Problem (built from the spec when None).
    @param fill Optional copper fill replacing the one of the zones.
    @param solver "direct" or "ragged" (the matrix without the unused interior nodes).
    @return dict with peak (with the face term), raw, unknowns (dense and ragged counts), flagged (cells per gap), seconds.
    """
    p = p or BD.problem(spec)
    net = GN.build(p, cell_mm, rule, fill=fill)
    t0 = time.perf_counter()
    if solver == "ragged":
        theta, nun = GN.solve_ragged(net)
    else:
        theta, _ = net.solve_steady()
        nun = theta.size
    dt = time.perf_counter() - t0
    peak, raw = GN.peak_under_parts(net, theta, p, rule)
    one = p.board.layers == 1
    return {"peak": peak, "raw": raw, "solved": nun, "counts": net.ladder.counts(one), "flagged": [int(g.flagged.sum()) for g in net.ladder.gaps],
            "n": [g.n for g in net.ladder.gaps], "seconds": dt}


def row(spec, rules, cell_mm=0.5, ref_dx=0.25, ref_nsub=8):
    """!
    @brief Errors of several rules against the reference on one spec.
    @param spec A boards.Spec.
    @param rules Dict name -> rule.Rule.
    @param cell_mm Cell size in mm.
    @param ref_dx Cell of the reference in mm.
    @param ref_nsub Sub-slabs per gap of the reference.
    @return dict with ref (face peak), and per rule name: peak, error in percent, unknown ratio (ragged), flagged cells.
    """
    ref = reference(spec, ref_dx, ref_nsub)
    out = {"spec": spec.name, "ref": ref["max"], "ref_centre": ref["max_centre"]}
    p = BD.problem(spec)
    for name, rl in rules.items():
        r = fvm_peak(spec, rl, cell_mm, p)
        out[name] = {"peak": r["peak"], "err": err(r["peak"], ref["max"]), "err_raw": err(r["raw"], ref["max"]), "ratio": r["counts"]["ratio_ragged"],
                     "ratio_dense": r["counts"]["ratio_dense"], "flagged": r["flagged"], "n": r["n"]}
    return out


__all__ = ["reference", "err", "fvm_peak", "row", "RU"]
