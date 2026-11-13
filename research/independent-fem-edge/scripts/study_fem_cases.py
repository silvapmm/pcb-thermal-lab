#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fem_cases.py
@brief The finite-element values of the canonical boards on three meshes each (Richardson extrapolation and GCI): the strong-edge plate (h_side 10 / 200 / 1000,
       copper to the wall and inset 0.5 mm), the via 0.16 and 3 mm from the wall (200 / 1000), the 20 mm square (copper 1.2 mm in: 10 / 200 / 1000; to the wall:
       200 / 1000), the disc (to the rim and 1.2 mm in: 200 / 1000) and the T with copper to the wall (200).
@details Run from the repository root: `.venv/bin/python research/independent-fem-edge/scripts/study_fem_cases.py [group ...]` with groups `plate`, `via`, `square`, `disc`, `t`,
         `thick`, `thick2`, `thick3` (through-thickness sequences; all when none is given). Every solve is cached in `research/independent-fem-edge/out/fem_cache.json` by its key, so a cut-off loses nothing. One solve at a time;
         the finest meshes are chosen to stay under about 2.5 GB (the peak of every solve is printed).
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import cases                                                            # noqa: E402

CACHE = os.path.join(os.path.dirname(HERE), "out", "fem_cache.json")

PLATE_H = (10.0, 200.0, 1000.0)
HF_PLATE = (0.2, 0.1, 0.05)
HF_SQ = (0.4, 0.2, 0.1)
N_DISC = (8, 16, 32)


def load():
    """!
    @brief Read the cache.
    @return dict.
    """
    return json.load(open(CACHE)) if os.path.exists(CACHE) else {}


def run(key, make, cache, read=("tmax", "heater_mean", "heater_max")):
    """!
    @brief Solve one board unless cached; print and store the read-outs.
    @param key Cache key.
    @param make Callable() -> Board.
    @param cache The cache dict (written after every solve).
    @param read Result keys to keep.
    @return dict of the stored values.
    """
    if key in cache:
        return cache[key]
    t = time.time()
    r = make().solve()
    rec = {k: r[k] for k in read if k in r}
    rec.update({"n": r["n"], "E": r["E"], "balance": r["balance"], "peak_gb": r["peak_gb"], "seconds": time.time() - t})
    cache[key] = rec
    json.dump(cache, open(CACHE, "w"), indent=1)
    print(f"{key:40s} n {r['n']:7d} tmax {r['tmax']:.5f} mean {r['heater_mean']:.5f} bal {r['balance'] - 1:+.1e} peak {r['peak_gb']:.2f} GB {rec['seconds']:.0f} s", flush=True)
    return rec


def main(groups):
    """!
    @brief Run the chosen groups.
    @param groups Group names.
    @return None.
    """
    c = load()
    if "plate" in groups:
        for inset in (0.0, 0.5):
            for h in PLATE_H:
                for hf in HF_PLATE:
                    run(f"plate|{h}|{inset}|{hf}|6", lambda: cases.strong_edge(h, hf=hf, inset=inset), c)
    if "thick" in groups:
        for n_gap in (4, 12):
            run(f"plate|1000.0|0.0|0.1|{n_gap}", lambda: cases.strong_edge(1000.0, hf=0.1, n_gap=n_gap), c)
        run("plate|1000.0|0.0|0.1|6|uniformgap", lambda: cases.strong_edge(1000.0, hf=0.1, n_gap=6, gap_ratio=1.0), c)
    if "thick2" in groups:                                                  # through-thickness sequences (3 / 6 / 12 / 24 elements per gap) on the middle plan mesh
        for h in (200.0, 1000.0):
            for n_gap in (3, 12, 24):
                run(f"plate|{h}|0.0|0.1|{n_gap}", lambda: cases.strong_edge(h, hf=0.1, n_gap=n_gap), c)
        for name, mk in (("sq_in|200.0", lambda n: cases.square(200.0, inset=1.2, hf=0.2, n_gap=n)), ("sq_in|1000.0", lambda n: cases.square(1000.0, inset=1.2, hf=0.2, n_gap=n)),
                         ("sq_wall|1000.0", lambda n: cases.square(1000.0, inset=0.0, hf=0.2, n_gap=n)), ("T_wall|200.0", lambda n: cases.t_outline(200.0, hf=0.2, n_gap=n)),
                         ("disc|1000.0|0.0", lambda n: cases.disc_board(1000.0, inset=0.0, n_side=16, n_gap=n)), ("disc|1000.0|1.2", lambda n: cases.disc_board(1000.0, inset=1.2, n_side=16, n_gap=n))):
            for n_gap in (3, 12):
                run(f"{name}|{0.2 if not name.startswith('disc') else 16}|gap{n_gap}", lambda: mk(n_gap), c)
    if "via" in groups:
        for h in (200.0, 1000.0):
            for d in (0.16, 3.0):
                for hf in HF_PLATE:
                    run(f"via|{h}|{d}|{hf}|6", lambda: cases.strong_edge(h, hf=hf, via_dist=d), c)
        for h in (200.0, 1000.0):                                          # the same mesh with no copper in the cylinder: the via effect on one mesh
            for d in (0.16, 3.0):
                for hf in HF_PLATE:
                    run(f"via|{h}|{d}|{hf}|6|nocopper", lambda: _no_copper(cases.strong_edge(h, hf=hf, via_dist=d)), c)
    # the two-layer boards (1.53 mm gaps) take 12 graded elements per gap (keys ending in g12; the 6-element runs of the first pass stay in the cache)
    if "square" in groups:
        for h in PLATE_H:
            for hf in HF_SQ:
                run(f"sq_in|{h}|{hf}|g12", lambda: cases.square(h, inset=1.2, hf=hf, n_gap=12), c)
        for h in (200.0, 1000.0):
            for hf in HF_SQ:
                run(f"sq_wall|{h}|{hf}|g12", lambda: cases.square(h, inset=0.0, hf=hf, n_gap=12), c)
    if "disc" in groups:
        for inset in (0.0, 1.2):
            for h in (200.0, 1000.0):
                for n in N_DISC:
                    run(f"disc|{h}|{inset}|{n}|g12", lambda: cases.disc_board(h, inset=inset, n_side=n, n_gap=12), c)
    if "t" in groups:
        for hf in HF_SQ:
            run(f"T_wall|200.0|{hf}|g12", lambda: cases.t_outline(200.0, hf=hf, n_gap=12), c)
        run("T_wall|200.0|0.4|full|g12", lambda: cases.t_outline(200.0, hf=0.4, half=False, n_gap=12), c)
    if "thick3" in groups:                                                  # 6 / 12 / 24 elements per gap on the middle plan mesh of every two-layer board
        for name, mk in (("sq_in|10.0|0.2", lambda n: cases.square(10.0, inset=1.2, hf=0.2, n_gap=n)), ("sq_in|200.0|0.2", lambda n: cases.square(200.0, inset=1.2, hf=0.2, n_gap=n)),
                         ("sq_in|1000.0|0.2", lambda n: cases.square(1000.0, inset=1.2, hf=0.2, n_gap=n)), ("sq_wall|200.0|0.2", lambda n: cases.square(200.0, inset=0.0, hf=0.2, n_gap=n)),
                         ("sq_wall|1000.0|0.2", lambda n: cases.square(1000.0, inset=0.0, hf=0.2, n_gap=n)), ("T_wall|200.0|0.2", lambda n: cases.t_outline(200.0, hf=0.2, n_gap=n)),
                         ("disc|200.0|0.0|16", lambda n: cases.disc_board(200.0, inset=0.0, n_side=16, n_gap=n)), ("disc|1000.0|0.0|16", lambda n: cases.disc_board(1000.0, inset=0.0, n_side=16, n_gap=n)),
                         ("disc|200.0|1.2|16", lambda n: cases.disc_board(200.0, inset=1.2, n_side=16, n_gap=n)), ("disc|1000.0|1.2|16", lambda n: cases.disc_board(1000.0, inset=1.2, n_side=16, n_gap=n))):
            for n_gap in (6, 12, 24):
                run(f"{name}|g{n_gap}", lambda: mk(n_gap), c)


def _no_copper(b):
    """!
    @brief Remove the via copper of a board (keeps its mesh).
    @param b Board.
    @return Board.
    """
    b.vias = []
    return b


if __name__ == "__main__":
    main(sys.argv[1:] or ["plate", "thick", "thick2", "via", "square", "disc", "t", "thick3"])
