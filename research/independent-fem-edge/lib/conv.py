#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file conv.py
@brief Cached finite-element solves of the canonical boards and the grid-convergence analysis (Richardson extrapolation, grid-convergence index).
@details A solve is identified by a key (case, parameters); results are appended to `out/fem_cache.jsonl` (git-ignored) so that an interrupted run resumes. Memory is read from the
         process after each solve and a solve whose estimated size exceeds `MAX_NODES` is refused (the stated limit, 4 GB at about 190 000 nodes on this machine).
"""

import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import boards                                                                  # noqa: E402

OUT = os.path.join(HERE, "..", "out")
CACHE = os.path.join(OUT, "fem_cache.jsonl")
MAX_NODES = 160000


def _load():
    """!
    @brief Read the cache.
    @return dict key -> result.
    """
    d = {}
    if os.path.exists(CACHE):
        for line in open(CACHE):
            r = json.loads(line)
            d[r["key"]] = r
    return d


def solve(case, **kw):
    """!
    @brief Solve one canonical board (cached).
    @param case 'strong' (strong_edge), 'square' or 'tout'.
    @param kw Arguments of the board builder.
    @return dict with mean, tmax, balance, n, peak_gb, seconds.
    """
    key = case + "|" + json.dumps(kw, sort_keys=True)
    cache = _load()
    if key in cache:
        return cache[key]
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    builder = {"strong": boards.strong_edge, "square": boards.square, "tout": boards.t_outline}[case]
    m, hm, tc = builder(**kw)
    nodes = (m.nx + 1) * (m.ny + 1) * (m.nz + 1)
    if nodes > 1.3 * MAX_NODES:
        raise MemoryError(f"{key}: {nodes} grid nodes above the limit")
    out = boards.read_out(m, hm, tc, m.solve())
    out.update(key=key, seconds=round(time.time() - t0, 1))
    with open(CACHE, "a") as fh:
        fh.write(json.dumps(out) + "\n")
    return out


def richardson(f1, f2, f3, r=2.0):
    """!
    @brief Observed order, extrapolated value and grid-convergence index of three solutions on meshes refined by the constant ratio r (f1 coarsest).
    @param f1 Coarse value.
    @param f2 Medium value.
    @param f3 Fine value.
    @param r Refinement ratio.
    @return dict with `p`, `ext`, `gci` (fraction, fine-mesh, safety factor 1.25) or `monotone` False when the differences change sign.
    """
    a, b = f2 - f1, f3 - f2
    if a == 0 or b == 0 or a * b < 0:
        return {"monotone": False, "p": float("nan"), "ext": f3, "gci": abs(b / f3) if f3 else float("nan")}
    p = math.log(a / b) / math.log(r)
    p = min(max(p, 0.5), 4.0)
    ext = f3 + b / (r ** p - 1.0)
    return {"monotone": True, "p": p, "ext": ext, "gci": 1.25 * abs(b / f3) / (r ** p - 1.0)}
