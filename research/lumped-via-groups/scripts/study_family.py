#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_family.py
@brief Simple boards: an n x n via array of a given pitch under a square source of a given size (4 layers, full copper), the via effect E of the Lumped variants against the fine-grid reference.
@details The family isolates one geometric ratio at a time: the share of the footprint that the vias cover (core / footprint) at fixed pitch (source 6, 10, 14 mm with the same array),
         the pitch at fixed share, the fill (open barrel against copper: the barrel resistance sets how much the lateral path matters), the number of layers (2, 4, 6) and the film of the
         bottom face (200 and 15 W/m2K: the fin length of the lower planes). Variants: the program (`L_prog`), the micro well only with the cell of the ring (`L_ring`) or of the nearest
         neighbour (`L_nn`), the group term of `lumped-analytic-vias` (`L_grp0`, a series Krogh well of the cluster in every plane), the group term outside the footprint only (`L_out`: the
         hypothesis that the rings already carry the spreading inside the footprint; for an array that lies entirely in the footprint it equals `L_nn`), the same group term scaled by
         0.25 / 0.5 / 0.75 (the oracle scan: the factor that would make E exact), the lossy macro cell (`L_loss`) and the two-zone footprint (`L_zone`, `lib/lumped_zones.py`).
         Error = 100 (E_model / E_ref - 1) %; positive means the model is cooler than the reference with vias (E too large).
Usage: python research/lumped-via-groups/scripts/study_family.py [--quick] [--procs N]   (from the repository root; writes out/family.json; about 15 minutes)
"""

import argparse
import json
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import refs                                                                  # noqa: E402
import lumped_groups as lg                                                   # noqa: E402

NAMES = ["L_prog", "L_ring", "L_nn", "L_grp0", "L_loss", "L_zone0", "L_zone_c1", "L_zone_disc", "L_zone_p", "L_zone_r", "L_zone", "L_zone_k"]
SCAN = (0.25, 0.5, 0.75)


def specs(quick):
    """!
    @brief The boards of the family.
    @param quick True: a short list for a check.
    @return list of spec dicts.
    """
    out = []
    arrays = [(3, 1.0), (3, 2.0), (3, 3.5), (5, 1.2), (5, 0.8), (7, 1.0)]
    for src in (6.0, 10.0, 14.0):
        for n, pitch in arrays:
            if (n - 1) * pitch > src - 1.0:
                continue                                                       # the outer vias must lie inside the footprint
            for fill in (0.0, 385.0):
                out.append(dict(layers=4, n=n, pitch=pitch, fill=fill, src=src))
    if not quick:
        # layers and bottom film at one array
        for layers in (2, 6):
            for fill in (0.0, 385.0):
                out.append(dict(layers=layers, n=5, pitch=1.2, fill=fill, src=10.0))
    else:
        out = out[:4]
    return out


def run(spec):
    """!
    @brief Reference and Lumped variants of one board.
    @param spec dict.
    @return dict with the spec, E_ref, E of every variant, the scan and the errors.
    """
    ref = refs.reference(spec)
    e = {n: refs.lumped_E(spec, n) for n in NAMES}
    scan = {}
    for f in SCAN:
        with_f = refs.variants_f(f)
        import harness as hz
        p = refs.make_problem(spec)
        scan[f] = hz.effect(p, "lumped", with_f, 0.5, hz.no_vias(p))
    return {"spec": spec, "ref": ref, "E": e, "scan": {str(k): v for k, v in scan.items()}}


def best_factor(row):
    """!
    @brief The factor on the group term of L_grp0 that makes E exact (linear interpolation on the scan 0, 0.25, ..., 1).
    @param row One result.
    @return float or None if E_ref lies outside the scanned range.
    """
    pts = [(0.0, row["E"]["L_nn"])] + [(float(k), v) for k, v in sorted(row["scan"].items(), key=lambda kv: float(kv[0]))] + [(1.0, row["E"]["L_grp0"])]
    t = row["ref"]["E"]
    for (f0, e0), (f1, e1) in zip(pts[:-1], pts[1:]):
        if (e0 - t) * (e1 - t) <= 0 and e0 != e1:
            return f0 + (t - e0) / (e1 - e0) * (f1 - f0)
    return None


def main():
    """!
    @brief Run the family and print the tables.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--ref-procs", type=int, default=2)
    args = ap.parse_args()
    sp = specs(args.quick)
    # The fine-grid references are large sparse solves (about 3 GB each): few at a time; the Lumped runs are light
    with mp.Pool(args.ref_procs) as pool:
        pool.map(refs.reference, sp, chunksize=1)
    with mp.Pool(args.procs) as pool:
        rows = pool.map(run, sp, chunksize=1)
    os.makedirs(os.path.join(os.path.dirname(HERE), "out"), exist_ok=True)
    json.dump(rows, open(os.path.join(os.path.dirname(HERE), "out", "family.json"), "w"), indent=1)
    print("## Error of the via effect E (percent of the fine-grid reference), 4 layers unless stated\n")
    print("| source mm | layers | array | fill | core share | E_ref K | best f | " + " | ".join(NAMES) + " |")
    print("| --: | --: | :-- | :-- | --: | --: | --: |" + " --: |" * len(NAMES))
    for r in rows:
        s = {**refs.DEFAULT, **r["spec"]}
        bf = best_factor(r)
        print(f"| {s['src']:.0f} | {s['layers']} | {s['n']}x{s['n']} @ {s['pitch']} | {'Cu' if s['fill'] else 'open'} | {r['ref']['core_share']:.2f} | {r['ref']['E']:.3f} | "
              + (f"{bf:.2f}" if bf is not None else "n/a") + " | " + " | ".join(f"{100 * (r['E'][n] / r['ref']['E'] - 1):+.1f}" for n in NAMES) + " |")
    print("\n## Summary (mean and maximum absolute error, percent)\n")
    print("| variant | mean | max | cases |\n| :-- | --: | --: | --: |")
    for n in NAMES:
        v = [abs(100 * (r["E"][n] / r["ref"]["E"] - 1)) for r in rows]
        print(f"| {n} | {sum(v) / len(v):.1f} | {max(v):.1f} | {len(v)} |")
    bfs = [best_factor(r) for r in rows]
    bfs = [b for b in bfs if b is not None]
    if bfs:
        print(f"\nBest factor on the group term: min {min(bfs):.2f}, max {max(bfs):.2f}, over {len(bfs)} of {len(rows)} cases")


if __name__ == "__main__":
    main()
