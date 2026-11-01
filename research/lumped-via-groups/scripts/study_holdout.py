#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_holdout.py
@brief Review: does the zone model hold on boards that were not used to choose it, and do the proposed warning rules flag the boards where it fails?
@details The ladder of the zone model (core radius 0.7071 d_nn, the 0.92 share, the lossless link with the lossy peak) was chosen on the 36 boards of `study_family.py` and
         the layouts of `study_zone_sensitivity.py`. This study runs the same variants on 26 boards that change what those boards keep fixed: the bottom film (10 and 50
         W/m2K instead of 200), the board thickness (0.8 and 2.4 mm), the layer count (3 and 8), the drill (0.2 and 0.5 mm), pitches between the earlier ones (1.5, 2.5,
         3.0 mm), true rectangular footprints of side ratio 1.5 and 2, clusters off the centre of the footprint and sparse arrays. The reference is the same fine-grid
         layered solver (`refs.reference`, cached in out/refcache). The second part evaluates the warning rules of `INTEGRATION.md` 4 on every board of the family, the
         sensitivity study and this one: the nearest-neighbour distance against 0.7 of the fin length of the source layer, the side ratio of the footprint against 1.5, the
         offset of the core centroid against a quarter of the smaller side of the footprint, and the rules after the review (side ratio, offset against 0.1). The third part runs
         the 36 boards of the family on the 1.0 mm raster that the program gives the Lumped model by default.
Usage: python research/lumped-via-groups/scripts/study_holdout.py [--procs N] [--ref-procs N]   (from the repository root; about 40 minutes the first time)
"""

import argparse
import json
import math
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FOLDER, "lib"))
sys.path.insert(0, HERE)

import refs                                                                  # noqa: E402

NAMES = ["L_prog", "L_nn", "L_grp0", "L_zone_p", "L_zone_r", "L_zone"]


def holdout_specs():
    """!
    @brief The held-out boards (none of them is in the family or the sensitivity study).
    @return list of (label, spec) tuples.
    """
    out = []
    for fill in (385.0, 0.0):
        f = "Cu" if fill else "open"
        out += [
            (f"h_bottom 10, 5x5 @ 1.2, src 10, {f}", dict(n=5, pitch=1.2, src=10.0, fill=fill, h_bottom=10.0)),
            (f"h_bottom 50, 5x5 @ 1.2, src 10, {f}", dict(n=5, pitch=1.2, src=10.0, fill=fill, h_bottom=50.0)),
            (f"0.8 mm board, 5x5 @ 1.5, src 12, {f}", dict(n=5, pitch=1.5, src=12.0, fill=fill, thickness=0.8)),
            (f"3 layers, 4x4 @ 1.2, src 8, {f}", dict(layers=3, n=4, pitch=1.2, src=8.0, fill=fill)),
            (f"source 12 x 8 (ratio 1.5), 5x5 @ 1.2, {f}", dict(n=5, pitch=1.2, src=10.0, src_wh=(12.0, 8.0), fill=fill)),
            (f"source 14 x 7 (ratio 2), 5x5 @ 1.2, {f}", dict(n=5, pitch=1.2, src=10.0, src_wh=(14.0, 7.0), fill=fill)),
            (f"4x4 @ 1.0 off centre 2 mm in src 12, {f}", dict(n=4, pitch=1.0, src=12.0, fill=fill, src_wh=(12.0, 12.0), offset=(2.0, 0.0))),
            (f"sparse 3x3 @ 3.0 in src 12, {f}", dict(n=3, pitch=3.0, src=12.0, fill=fill)),
            (f"sparse 4x4 @ 2.5 in src 12, {f}", dict(n=4, pitch=2.5, src=12.0, fill=fill)),
        ]
    out += [
        ("2.4 mm board, 5x5 @ 1.2, src 10, Cu", dict(n=5, pitch=1.2, src=10.0, fill=385.0, thickness=2.4)),
        ("8 layers, 6x6 @ 1.0, src 12, Cu", dict(layers=8, n=6, pitch=1.0, src=12.0, fill=385.0)),
        ("drill 0.5, 4x4 @ 1.5, src 12, Cu", dict(n=4, pitch=1.5, src=12.0, fill=385.0, dia=0.5)),
        ("drill 0.2, 7x7 @ 0.6, src 8, Cu", dict(n=7, pitch=0.6, src=8.0, fill=385.0, dia=0.2)),
        ("4x4 @ 1.0 off centre (3.5, 1.5) in src 12, Cu", dict(n=4, pitch=1.0, src=12.0, fill=385.0, src_wh=(12.0, 12.0), offset=(3.5, 1.5))),
        ("h_bottom 10, 7x7 @ 1.0, src 14, Cu", dict(n=7, pitch=1.0, src=14.0, fill=385.0, h_bottom=10.0)),
        ("h_bottom 10, sparse 3x3 @ 3.0, src 12, Cu", dict(n=3, pitch=3.0, src=12.0, fill=385.0, h_bottom=10.0)),
        ("h_bottom 10, source 14 x 7, 5x5 @ 1.2, Cu", dict(n=5, pitch=1.2, src=10.0, src_wh=(14.0, 7.0), fill=385.0, h_bottom=10.0)),
    ]
    return out


def features(spec):
    """!
    @brief The quantities of the warning rules for one board.
    @param spec dict.
    @return dict with d_nn / lambda (lambda = sqrt(S / g) of the source layer, g the top film plus the dielectric below per area), the side ratio of the footprint and the
            offset of the via centroid from the footprint centroid over the smaller side.
    """
    import program_cases as pc
    pc.load_libraries()
    p = refs.make_problem(spec)
    par = pc.layer_parameters(p)
    lam = math.sqrt(par["S"][0] / (par["h_top"] + par["gz_area"][0]))
    xs = [q[0] for q in p.heaters[0].polygon]
    ys = [q[1] for q in p.heaters[0].polygon]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    fx, fy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    inside = [v for v in p.vias if min(xs) < v.x < max(xs) and min(ys) < v.y < max(ys)]
    if len(inside) < 2:
        return {"dnn_lam": math.nan, "ratio": max(w, h) / min(w, h), "offset": math.nan}
    pts = [(v.x, v.y) for v in inside]
    d_nn = min(math.hypot(a[0] - b[0], a[1] - b[1]) for i, a in enumerate(pts) for b in pts[i + 1:])
    cx, cy = sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts)
    return {"dnn_lam": d_nn / lam, "ratio": max(w, h) / min(w, h), "offset": math.hypot(cx - fx, cy - fy) / min(w, h), "lam_mm": lam * 1e3}


def run(item):
    """!
    @brief Reference, variants and features of one board.
    @param item (label, spec).
    @return dict.
    """
    label, spec = item
    ref = refs.reference(spec)
    e = {n: refs.lumped_E(spec, n) for n in NAMES}
    return {"label": label, "spec": spec, "E_ref": ref["E"], "core_share": ref["core_share"], "err": {n: 100.0 * (e[n] / ref["E"] - 1.0) for n in NAMES}, "feat": features(spec)}


def flagged(f):
    """!
    @brief The warning rules of the researcher (INTEGRATION.md 4 before the review, option C).
    @param f Features of a board.
    @return bool True if any rule fires.
    """
    return (f["dnn_lam"] > 0.7) or (f["ratio"] > 1.5) or (f["offset"] > 0.25)


def flagged_review(f):
    """!
    @brief The warning rules after the review: the side ratio of the footprint above 1.5 or the core centroid off the footprint centroid by more than 0.1 of its smaller side
           (the sparse rule is dropped: with the bump of a hot core the sparse boards are within 7 %). Chosen on the same 72 boards it is checked on.
    @param f Features of a board.
    @return bool True if any rule fires.
    """
    return (f["ratio"] > 1.5) or (f["offset"] > 0.1)


def main():
    """!
    @brief Run the held-out boards and the warning check, print the tables.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--ref-procs", type=int, default=2)
    args = ap.parse_args()
    items = holdout_specs()
    with mp.Pool(args.ref_procs) as pool:
        pool.map(refs.reference, [s for _, s in items], chunksize=1)
    with mp.Pool(args.procs) as pool:
        rows = pool.map(run, items, chunksize=1)
    json.dump(rows, open(os.path.join(FOLDER, "out", "holdout.json"), "w"), indent=1)
    print("## 1. Held-out boards (error of E, percent of the fine-grid reference)\n")
    print("| board | core share | E_ref K | d_nn / lambda | side ratio | offset | " + " | ".join(NAMES) + " |")
    print("| :-- | --: | --: | --: | --: | --: |" + " --: |" * len(NAMES))
    for r in rows:
        f = r["feat"]
        print(f"| {r['label']} | {r['core_share']:.2f} | {r['E_ref']:.3f} | {f['dnn_lam']:.2f} | {f['ratio']:.2f} | {f['offset']:.2f} | "
              + " | ".join(f"{r['err'][n]:+.1f}" for n in NAMES) + " |")
    print("\n| variant | mean | max | within 10 % | model cooler (unsafe) |\n| :-- | --: | --: | --: | --: |")
    for n in NAMES:
        v = [r["err"][n] for r in rows]
        print(f"| {n} | {sum(abs(x) for x in v) / len(v):.1f} | {max(abs(x) for x in v):.1f} | {sum(abs(x) <= 10 for x in v)} of {len(v)} | {sum(x > 0 for x in v)} |")

    # Part 2: the warning rules on every board (family, sensitivity layouts, held-out)
    fam = json.load(open(os.path.join(FOLDER, "out", "family.json")))
    allb = [(f"family {i}", r["spec"], 100.0 * (r["E"]["L_zone"] / r["ref"]["E"] - 1.0)) for i, r in enumerate(fam)]
    sens = [dict(n=5, pitch=1.2, src=10.0, offset=(2.0, 0.0)), dict(n=5, pitch=1.2, src=10.0, offset=(3.0, 2.0)), dict(n=5, pitch=1.2, src=11.0, src_aspect=1.6),
            dict(n=5, pitch=1.2, src=14.0, clusters=[(-3.0, 0.0, 3, 1.0), (3.0, 0.0, 3, 1.0)]), dict(n=5, pitch=1.2, src=14.0, clusters=[(2.5, 0.0, 3, 1.0)])]
    for s in sens:
        for fill in (385.0, 0.0):
            sp = dict(s, fill=fill)
            allb.append((f"sensitivity {s}", sp, 100.0 * (refs.lumped_E(sp, "L_zone") / refs.reference(sp)["E"] - 1.0)))
    allb += [(r["label"], r["spec"], r["err"]["L_zone"]) for r in rows]
    feats = [features(spec) for _, spec, _ in allb]
    print(f"\n## 2. Warning rules on {len(allb)} boards (L_zone more than 10 % too cool = 'bad')\n")
    for title, rule in (("researcher (d_nn / lambda > 0.7, side ratio > 1.5, offset > 0.25)", flagged), ("review (side ratio > 1.5, offset > 0.1)", flagged_review)):
        tp = fp = fn = tn = 0
        misses = []
        for (label, spec, e), f in zip(allb, feats):
            fl = rule(f)
            bad = e > 10.0
            tp += fl and bad
            fp += fl and not bad
            fn += (not fl) and bad
            tn += (not fl) and not bad
            if bad and not fl:
                misses.append((label, e))
        print(f"{title}: flagged and bad {tp}, flagged and good {fp}, not flagged and bad {fn}, not flagged and good {tn}")
        for label, e in misses:
            print(f"  missed: {label}: {e:+.1f} %")

    # Part 3: the raster of the program. The studies run the Lumped model on a 0.5 mm raster; the program clips the Lumped cell to 0.5 to 1.0 mm and its default
    # cell (1.0 mm, and Auto for any part wider than 4 mm) gives 1.0 mm
    names3 = ["L_prog", "L_nn", "L_grp0", "L_zone_r", "L_zone"]
    with mp.Pool(args.procs) as pool:
        e1 = pool.map(_family_at_1mm, [(r["spec"], names3) for r in fam], chunksize=1)
    print("\n## 3. The 36 boards of the family on the 1.0 mm raster of the program's default (mean / max absolute error, within 10 %)\n")
    print("| variant | 0.5 mm mean | 0.5 mm max | 1.0 mm mean | 1.0 mm max | 1.0 mm within 10 % |\n| :-- | --: | --: | --: | --: | --: |")
    for n in names3:
        a = [abs(100.0 * (r["E"][n] / r["ref"]["E"] - 1.0)) for r in fam]
        b = [abs(100.0 * (e[n] / r["ref"]["E"] - 1.0)) for e, r in zip(e1, fam)]
        print(f"| {n} | {sum(a) / len(a):.1f} | {max(a):.1f} | {sum(b) / len(b):.1f} | {max(b):.1f} | {sum(x <= 10 for x in b)} of {len(b)} |")
    print("\n| board | " + " | ".join(f"{n} 1.0 mm" for n in names3) + " |\n| :-- |" + " --: |" * len(names3))
    for e, r in zip(e1, fam):
        s = {**refs.DEFAULT, **r["spec"]}
        print(f"| {s['src']:.0f} mm, {s['layers']} layers, {s['n']}x{s['n']} @ {s['pitch']}, {'Cu' if s['fill'] else 'open'} | "
              + " | ".join(f"{100.0 * (e[n] / r['ref']['E'] - 1.0):+.1f}" for n in names3) + " |")


def _family_at_1mm(item):
    """!
    @brief Via effect of some variants on one board at the 1.0 mm raster.
    @param item (spec, names).
    @return dict name -> E in K.
    """
    spec, names = item
    return {n: refs.lumped_E(spec, n, 1.0) for n in names}


if __name__ == "__main__":
    main()
