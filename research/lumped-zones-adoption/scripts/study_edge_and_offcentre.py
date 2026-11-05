#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge_and_offcentre.py
@brief Study 4: the arrays that cross the footprint edge, the clusters off the centre of the footprint and the rows and lone vias beside it, with and without the zones (the worst cases of the 2.4.5 review).
@details The review of 2.4.5 measured the Lumped effect of an array that straddles the footprint edge up to 80 % too large (the part too cool), because the rings carry no angular resolution; the
         earlier folder measured the zone model up to 21 % too cool on clusters off the centre. Boards (specs of `refs.make_problem`, copper-filled and open):
         (a) a 5 x 5 array at 1.2 mm under a 12 x 12 mm footprint, the array moved in x by 0, 2, 4, 5, 6, 7 and 9 mm (the footprint edge is at 6 mm from the centre; the array is wholly inside, across the
         edge, then wholly outside); (b) the same array moved in x and y by (2, 0) and (3.5, 1.5) mm (off the centre but inside); (c) a 5 x 5 array moved by (0, 0) under footprints 12 x 12, 14 x 7 and 17.6 x 6.9 mm
         (the side ratio of the warning); (d) a 3 x 3 array at 3.5 mm whose nearest via is 1, 2 and 4 mm outside a 6 mm footprint (a group outside the footprint, which keeps the 2.4.5 well with the macro cap in every variant).
         Variants: `P245`, `Z_none`, `Z_cap`. Error of E against the fine-grid reference, the zone warnings raised, and whether the sign is on the safe side.
         Success criterion (fixed before running): with the zones, no board is more than 25 % too large in E (part too cool) without a warning; the boards with the array across the edge improve over `P245`
         or are flagged; the boards of (d) are equal (to rounding, 1e-9) between `P245` and the zone variants (the zones do not touch groups outside the footprint).
         Not verified: arrays wider than the footprint, several groups in one footprint, a guard ring.
Usage: python research/lumped-zones-adoption/scripts/study_edge_and_offcentre.py [--quick] [--procs N]   (from the repository root; reference solves of 480 x 480 cells and more dominate)
"""

import argparse
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import zref                                                                  # noqa: E402
import zoned_lumped as zl                                                    # noqa: E402

NAMES = ["P245", "Z_none", "Z_cap"]


def boards():
    """!
    @brief The labelled specs of the four families (a) to (d).
    @return list of (label, spec).
    """
    out = []
    for fill in (385.0, 0.0):
        f = "Cu" if fill else "open"
        base = dict(layers=4, n=5, pitch=1.2, dia=0.3, fill=fill, side=30.0, src=12.0, src_wh=(12.0, 12.0))
        for dx in (0.0, 2.0, 4.0, 5.0, 6.0, 7.0, 9.0):
            out.append((f"(a) 5x5 shifted {dx:g} mm in x under 12x12, {f}", {**base, "offset": (dx, 0.0)}))
        for off in ((2.0, 0.0), (3.5, 1.5)):
            out.append((f"(b) 5x5 off centre {off}, {f}", {**base, "offset": off}))
        for wh in ((12.0, 12.0), (14.0, 7.0), (17.6, 6.9)):
            out.append((f"(c) 5x5 under {wh[0]:g}x{wh[1]:g}, {f}", {**base, "src_wh": wh}))
        for dx in (1.0, 2.0, 4.0):
            out.append((f"(d) 3x3 @ 3.5 mm, nearest via {dx:g} mm outside a 6 mm footprint, {f}", dict(layers=4, n=3, pitch=3.5, dia=0.3, fill=fill, side=30.0, src=6.0, offset=(6.5 + dx, 0.0), src_wh=(6.0, 6.0))))
    return out


def one(item):
    """!
    @brief Reference and variants of one board, with the warnings of the zone model.
    @param item (label, spec).
    @return dict.
    """
    label, spec = item
    e_ref = zref.refs.reference(spec)["E"]
    e = {n: zref.lumped_E(spec, n, 0.5) for n in NAMES}
    prob = zref.refs.make_problem(spec)
    with zref.VARIANTS["Z_none"]():
        zref.pc.max_rise(prob, "lumped", 0.5)
        warn = list(zl.LAST.get("warnings", []))
        nz = int(zl.LAST.get("nz", 1))
    return {"label": label, "E_ref": e_ref, "E": e, "err": {n: zref.error_pct(e[n], e_ref) for n in NAMES}, "warnings": warn, "nz": nz}


def main():
    """!
    @brief Run the boards and print the tables and the checks of the criterion.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    todo = boards()[:6] + boards()[-3:] if args.quick else boards()
    with mp.get_context("spawn").Pool(args.procs) as pool:
        rows = pool.map(one, todo, chunksize=1)
    print("\n| board | E_ref K | " + " | ".join(NAMES) + " | zones | warning |\n| :-- | --: |" + " --: |" * len(NAMES) + " :-- | :-- |")
    for r in rows:
        print(f"| {r['label']} | {r['E_ref']:.3f} | " + " | ".join(f"{r['err'][n]:+.1f}" for n in NAMES) + f" | {'2' if r['nz'] == 2 else '1'} | {'yes' if r['warnings'] else ''} |")
    bad = [r["label"] for r in rows if r["err"]["Z_none"] > 25.0 and not r["warnings"]]
    print(f"\nboards with the zone model more than 25 % too cool and no warning: {bad}")
    d_rows = [r for r in rows if r["label"].startswith("(d)")]
    same = [abs(r["E"]["Z_none"] - r["E"]["P245"]) < 1e-9 * max(abs(r["E"]["P245"]), 1e-12) for r in d_rows]
    print(f"group outside the footprint: zone variants equal to the program on {sum(same)} of {len(same)} boards")
    for title, tag in (("(a) across the edge", "(a)"), ("(b) off centre", "(b)"), ("(c) side ratio", "(c)"), ("(d) outside", "(d)")):
        sel = [r for r in rows if r["label"].startswith(tag)]
        print(f"\n{title}: " + ", ".join(f"{n} mean {zref.summarize([r['err'][n] for r in sel])['mean']:.1f} max {zref.summarize([r['err'][n] for r in sel])['max']:.1f}" for n in NAMES))
    print("\nwritten", zref.save_json("edge_offcentre.json", rows))


if __name__ == "__main__":
    main()
