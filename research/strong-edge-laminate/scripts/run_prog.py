#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file run_prog.py
@brief Runs the program's FVM on the S1 edge board over the study grid (edge coefficient, cell, laminate sub-gaps, via distance, copper inset) and caches the hottest rise.
@details Question: how much of the error of the whole board and of the via effect near a cooled edge comes from the laminate idealisation (sub-gaps, cell) and how much
         from the via. Every result is appended to out/prog_cache.jsonl as the rise without the via and with it. The program is only imported, never changed.
         Run from the repository root: `.venv/bin/python research/strong-edge-laminate/scripts/run_prog.py [group ...]` (groups: plate, near, dist, inset, fine; default all).
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "lib"))
import prog                                                         # noqa: E402

OUT = os.path.join(ROOT, "out")
CACHE = os.path.join(OUT, "prog_cache.jsonl")


def key(h, cell, n_sub, dist_mm, inset_mm):
    """!
    @brief Cache key.
    @param h Side film coefficient in W/m2K.
    @param cell Cell in mm.
    @param n_sub Sub-gaps (None: the defaults, 2 on this board).
    @param dist_mm Via distance from the edge in mm (None: no via).
    @param inset_mm Copper inset in mm.
    @return str key.
    """
    return f"h{h:g}|c{cell:g}|n{n_sub}|d{dist_mm}|i{inset_mm:g}"


def load():
    """!
    @brief Read the cache.
    @return dict key -> record.
    """
    out = {}
    if os.path.exists(CACHE):
        for line in open(CACHE):
            r = json.loads(line)
            out[r["key"]] = r
    return out


def get(h, cell, n_sub=None, dist_mm=None, inset_mm=0.0):
    """!
    @brief One program rise, from the cache or computed.
    @param h Side film coefficient in W/m2K.
    @param cell Cell in mm.
    @param n_sub Sub-gaps per gap (None: the defaults).
    @param dist_mm Via distance in mm (None: no via).
    @param inset_mm Copper inset in mm.
    @return float rise in K.
    """
    k = key(h, cell, n_sub, dist_mm, inset_mm)
    c = load()
    if k in c:
        return c[k]["rise"]
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    rise = prog.run(prog.board(h, dist_mm, inset_mm), cell, n_sub)
    with open(CACHE, "a") as f:
        f.write(json.dumps(dict(key=k, rise=rise, seconds=round(time.time() - t0, 2))) + "\n")
    return rise


def groups():
    """!
    @brief Configurations of every group as (h, cell, n_sub, dist, inset) tuples.
    @return dict.
    """
    ns = (None, 4, 8, 16, 32)
    g = {}
    g["plate"] = [(h, c, n, None, 0.0) for h in (10, 200, 500, 1000, 2000) for c in (1.0, 0.5, 0.25) for n in ns]
    g["near"] = [(h, c, n, 0.16, 0.0) for h in (10, 200, 500, 1000, 2000) for c in (1.0, 0.5, 0.25) for n in ns]
    g["dist"] = [(h, c, n, d, 0.0) for h in (200, 1000) for d in (None, 0.5, 1.0, 3.0) for c in (0.5, 0.25) for n in (None, 8, 16)]
    g["inset"] = [(h, c, n, d, 0.5) for h in (200, 1000) for d in (None, 1.0) for c in (0.5, 0.25) for n in (None, 8, 16)]
    g["fine"] = [(1000, 0.125, n, d, 0.0) for n in (None, 8, 16) for d in (None, 0.16)]
    return g


if __name__ == "__main__":
    allg = groups()
    for nme in sys.argv[1:] or list(allg):
        for cfg in allg[nme]:
            get(*cfg)
        print("done", nme, flush=True)
