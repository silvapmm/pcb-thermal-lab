#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_zones_on_245.py
@brief Study 1: does the zone network, put on top of the 2.4.5 via wells, keep the accuracy it had on the older micro well, and does the macro cap of the cluster well help or count twice inside the zones?
@details Boards: the 36 simple boards of the family (n x n arrays under square sources), the 26 held-out boards of the earlier review, and the example board with its 9 vias and with 5 x 5,
         7 x 7 and 20 x 20 arrays under U1 (open and copper-filled). Reference: the fine-grid layered solver of the earlier folder for the simple boards (`refs.reference`) and the program's
         own FVM at 0.25 mm for the example board (the program's FVM holds the mean-potential via since the point-via fix, so the earlier `FVM_fix` patch is the program).
         Variants (`zref.VARIANTS`): `P245` the program, `Z_none` zones with the micro well in the zones, `Z_cap` zones with the cluster well and its macro cap of 0.75 fin lengths in the
         zones, and the ablations `Z_none_nomp` (no micro peak), `Z_none_fr` (Bessel factor on the link to ring 1), `Z_cap_nocb` (no bump of a hot core).
         Success criterion (fixed before running): the chosen zone variant is within 6 % mean and 15 % maximum on the 36 boards, within 8 % mean on the held-out boards, within 10 % of the
         example-board effect on the safe side, and not worse than `P245` on any board by more than 5 points; the program's own mean and maximum error on the same boards is the number to beat.
         Prints Markdown tables and writes out/zones_on_245.json.
Usage: python research/lumped-zones-adoption/scripts/study_zones_on_245.py [--quick] [--procs N] [--old-cache]   (from the repository root; hours when the references are not cached: do not run on a busy machine)
"""

import argparse
import contextlib
import json
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import zref                                                                  # noqa: E402

NAMES = ["P245", "Z_none", "Z_cap", "Z_none_nomp", "Z_none_fr", "Z_cap_nocb"]
EXAMPLE_BOARDS = [("example, 9 vias at 3.5 mm", 0, 3.5), ("5 x 5 at 1.2 mm", 5, 1.2), ("7 x 7 at 1.0 mm", 7, 1.0), ("20 x 20 at 1.0 mm", 20, 1.0)]


def one(item):
    """!
    @brief Reference and Lumped variants of one simple board.
    @param item (label, spec, cell_mm).
    @return dict with label, spec, E_ref, E, err.
    """
    label, spec, cell = item
    e_ref = zref.refs.reference(spec)["E"]
    e = {n: zref.lumped_E(spec, n, cell) for n in NAMES}
    return {"label": label, "spec": spec, "E_ref": e_ref, "E": e, "err": {n: zref.error_pct(e[n], e_ref) for n in NAMES}}


def example_rows(quick):
    """!
    @brief The example board with several via layouts in every variant.
    @param quick True: only the original 9 vias.
    @return list of dict rows (board, fill, E_ref, E, T_max, T_ref).
    """
    import harness as hz
    import program_cases as pc
    import study_real_boards as srb
    pc.load_libraries()
    path = os.path.join(zref.OUT, "real_ref.json")
    cache = json.load(open(path)) if os.path.exists(path) else {}
    rows = []
    for label, n, pitch in EXAMPLE_BOARDS[:1] if quick else EXAMPLE_BOARDS:
        for fill in (0.0, 385.0):
            prob = srb.example(fill, n, pitch)
            q0 = hz.no_vias(prob)
            key = f"{n}_{pitch}_{fill}"
            if key not in cache:
                # the program's FVM at 0.25 mm is the reference (it holds the mean-potential via); not independent of the layered idealisation
                cache[key] = hz.effect(prob, "fvm", contextlib.nullcontext, 0.25, q0)
                cache[key + "_tmax"] = pc.max_rise(prob, "fvm", 0.25) + prob.board.ambient
                os.makedirs(zref.OUT, exist_ok=True)
                json.dump(cache, open(path, "w"))
            e, t = {}, {}
            for n_ in NAMES:
                with zref.VARIANTS[n_]():
                    t[n_] = pc.max_rise(prob, "lumped", 0.5) + prob.board.ambient
                    e[n_] = pc.max_rise(q0, "lumped", 0.5) + prob.board.ambient - t[n_]
            rows.append({"board": label, "fill": fill, "E_ref": cache[key], "E": e, "T_max": t, "T_ref": cache[key + "_tmax"]})
            print(f"{label} fill {fill}: E_ref {cache[key]:.3f} K  " + "  ".join(f"{k} {zref.error_pct(e[k], cache[key]):+.1f}%" for k in NAMES), flush=True)
    return rows


def main():
    """!
    @brief Run the three sets and print the tables.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--old-cache", action="store_true", help="copy the reference cache of lumped-via-groups first")
    args = ap.parse_args()
    if args.old_cache:
        print("copied", zref.use_old_cache(), "cached references")
    import study_family
    import study_holdout
    fam = [(f"family {i}", s, 0.5) for i, s in enumerate(study_family.specs(args.quick))]
    hold = [(lab, s, 0.5) for lab, s in study_holdout.holdout_specs()]
    if args.quick:
        hold = hold[:4]
    with mp.get_context("spawn").Pool(args.procs) as pool:
        fam_rows = pool.map(one, fam, chunksize=1)
        hold_rows = pool.map(one, hold, chunksize=1)
    print(zref.table(fam_rows, NAMES, "Family: arrays under square sources"))
    print(zref.table(hold_rows, NAMES, "Held-out boards"))
    # board by board, where a zone variant is worse than the program by more than 5 points
    for name in ("Z_none", "Z_cap"):
        worse = [r["label"] for r in fam_rows + hold_rows if abs(r["err"][name]) > abs(r["err"]["P245"]) + 5.0]
        print(f"\n{name} is worse than P245 by more than 5 points on {len(worse)} boards: {worse}")
    ex = example_rows(args.quick)
    print("\n| board | fill | E_ref K | " + " | ".join(NAMES) + " |\n| :-- | :-- | --: |" + " --: |" * len(NAMES))
    for r in ex:
        print(f"| {r['board']} | {'Cu' if r['fill'] else 'open'} | {r['E_ref']:.3f} | " + " | ".join(f"{zref.error_pct(r['E'][k], r['E_ref']):+.1f}" for k in NAMES) + " |")
    print("\n| board | fill | " + " | ".join(NAMES) + " | FVM 0.25 mm |\n| :-- | :-- |" + " --: |" * (len(NAMES) + 1))
    for r in ex:
        print(f"| {r['board']} | {'Cu' if r['fill'] else 'open'} | " + " | ".join(f"{r['T_max'][k]:.2f}" for k in NAMES) + f" | {r['T_ref']:.2f} |")
    print("\nwritten", zref.save_json("zones_on_245.json", {"family": fam_rows, "holdout": hold_rows, "example": ex}))


if __name__ == "__main__":
    main()
