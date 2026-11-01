#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file warm_refs.py
@brief Builds, one board at a time in one process, the fine-grid layered references of the 93 simple boards (36 family, 26 held-out, 30 edge and off-centre, the symmetry board) into `out/refcache`.
@details The cache of the earlier run was lost with the worktree. One process keeps the peak memory at that of one 1/16 mm solve (about 1.2 GB); the time of each board is printed so that the cost
         of the whole set is known. Boards already cached are skipped (the key is the hash of the spec). Usage: python research/lumped-zones-adoption/scripts/warm_refs.py [--limit N]
         (from the repository root, with the program's .venv).
"""

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, HERE)

import zref                                                                  # noqa: E402


def all_specs():
    """!
    @brief The labelled specs of the 93 simple boards.
    @return list of (label, spec).
    """
    import study_edge_and_offcentre as se
    import study_family
    import study_holdout
    out = [(f"family {i}", s) for i, s in enumerate(study_family.specs(False))]
    out += list(study_holdout.holdout_specs())
    out += list(se.boards())
    out.append(("symmetry", dict(n=5, pitch=1.2, src=10.0, fill=385.0, offset=(1.5, 0.0), src_wh=(12.0, 8.0))))
    return out


def main():
    """!
    @brief Build the references.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    specs = all_specs()
    print("boards:", len(specs), flush=True)
    t_all = time.time()
    for i, (label, spec) in enumerate(specs[:args.limit or None]):
        t0 = time.time()
        zref.refs.reference(spec)
        print(f"{i:3d} {label[:60]:60s} {time.time() - t0:6.1f} s", flush=True)
    print(f"total {time.time() - t_all:.0f} s", flush=True)


if __name__ == "__main__":
    main()
