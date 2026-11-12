#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file run_ref.py
@brief Runs the independent 3D reference (lib/ref3d.py) over the configurations of the study and caches every result in out/ref_cache.jsonl.
@details Question: what is the 3D answer (no-via rise and via effect) for the S1 board at the edge coefficients, sub-slab counts, plan cells, via distances, via
         representations and copper insets of the study. One heavy job at a time: the runs are sequential and the peak resident memory of each is printed.
         Run from the repository root: `.venv/bin/python research/strong-edge-laminate/scripts/run_ref.py [group ...]` (groups: base, nsub, dx, dist, inset, rim; default all).
"""

import json
import os
import resource
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "lib"))
import ref3d                                                        # noqa: E402

OUT = os.path.join(ROOT, "out")
CACHE = os.path.join(OUT, "ref_cache.jsonl")


def key(h, n_sub, dx_inv, via, dist_mm, inset_mm):
    """!
    @brief Cache key of one configuration.
    @param h Side film coefficient in W/m2K.
    @param n_sub Sub-slabs per gap.
    @param dx_inv Inverse plan cell in 1/mm (16 means 1/16 mm).
    @param via 'none', 'cyl', 'link' or 'rim'.
    @param dist_mm Via distance from the edge in mm.
    @param inset_mm Copper inset in mm.
    @return str key.
    """
    return f"h{h:g}|n{n_sub}|dx{dx_inv:g}|{via}|d{dist_mm:g}|i{inset_mm:g}"


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


def get(h, n_sub=8, dx_inv=16, via="none", dist_mm=0.16, inset_mm=0.0):
    """!
    @brief One reference result, from the cache or computed (and appended to the cache).
    @param h Side film coefficient in W/m2K.
    @param n_sub Sub-slabs per gap.
    @param dx_inv Inverse plan cell in 1/mm.
    @param via 'none', 'cyl', 'link' or 'rim'.
    @param dist_mm Via distance from the edge in mm.
    @param inset_mm Copper inset in mm.
    @return dict with tmax, balance, n, seconds, rss_gb.
    """
    k = key(h, n_sub, dx_inv, via, 0.0 if via == "none" else dist_mm, inset_mm)
    c = load()
    if k in c:
        return c[k]
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    kw = {}
    if via == "link":
        kw["gv_gap"] = ref3d.barrel_gv()
    if via == "rim":
        kw["r_in"] = 0.125e-3
    r = ref3d.solve(h, n_sub, 1e-3 / dx_inv, via, via_dist=dist_mm * 1e-3, inset=inset_mm * 1e-3, **kw)
    r.update(key=k, seconds=round(time.time() - t0, 1), rss_gb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 2))
    with open(CACHE, "a") as f:
        f.write(json.dumps(r) + "\n")
    print(json.dumps(r), flush=True)
    return r


def groups():
    """!
    @brief The configurations of every group (plan cell 1/8 mm unless stated: the 1/16 mm solves peak at 7.5 GB, so they are kept to a few headline rows).
    @return dict group name -> list of keyword dicts for `get`.
    """
    g = {}
    g["base"] = [dict(h=h, dx_inv=8, via=v) for h in (10, 200, 500, 1000, 2000) for v in ("none", "cyl")] + [dict(h=h, dx_inv=8, via="link") for h in (200, 1000)]
    g["nsub"] = [dict(h=1000, n_sub=n, dx_inv=8, via=v) for n in (2, 4, 16, 32) for v in ("none", "cyl")]
    g["dx"] = [dict(h=1000, n_sub=8, dx_inv=d, via=v) for d in (4, 12) for v in ("none", "cyl")] + [dict(h=1000, n_sub=4, dx_inv=16, via=v) for v in ("none", "cyl")]
    g["dist"] = [dict(h=h, dx_inv=8, via="cyl", dist_mm=d) for h in (200, 1000) for d in (0.5, 1.0, 3.0)]
    g["inset"] = [dict(h=h, dx_inv=8, via=v, dist_mm=1.0, inset_mm=0.5) for h in (200, 1000) for v in ("none", "cyl")]
    g["rim"] = [dict(h=1000, dx_inv=8, via="rim")]
    g["fine"] = [dict(h=h, n_sub=8, dx_inv=16, via=v) for h in (200,) for v in ("none", "cyl")]
    return g


if __name__ == "__main__":
    allg = groups()
    names = sys.argv[1:] or list(allg)
    for nme in names:
        for cfg in allg[nme]:
            get(**cfg)
