#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_sweep.py
@brief Study 2: the Lumped part reading (zoned, and one node) against the FVM at 0.5 mm on 100 x 80 mm boards, part over a dense via group, sweeping the via count, pitch, drill, layers, part size, h, fill, offset and a second part.
@details Per case the table gives, in percent of the FVM rise of the part (peak with peak, mean with mean): the error of the Lumped zoned and of the one-node Lumped on the part peak and
         on the part mean, and the error of the via effect E (the same board without vias minus with vias, per model, in percent of the FVM's E). The board maximum equals the
         hottest part peak in every model and is not repeated. Cases are one factor at a time around the base board plus the full count x pitch x part x layers grid.
         `heater_stats` is the read-out (peak = hottest of the field and `heater_peak` for the Lumped; max cell under the footprint for the FVM), mean = coverage-weighted footprint mean of
         the painted field.
Usage: python research/lumped-dense-via-group/scripts/study_sweep.py [--grid] [--cell 0.5]   (from the repository root; ONE process; 4-layer cases at 0.5 mm take a few GB)
"""

import argparse
import itertools
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import viastudy as v                                                          # noqa: E402

BASE = dict(layers=2, n=5, pitch=1.0, drill=0.3, part=8.0, power=3.0, h=10.0, filled=False, offset=(0.0, 0.0), second=None)


def cases(grid):
    """!
    @brief The list of (label, kwargs) cases.
    @param grid True to add the full count x pitch x part x layers grid.
    @return list.
    """
    out = [("base", {})]
    for k, vals in (("n", (3, 8)), ("pitch", (0.8, 1.5, 2.0)), ("drill", (0.6,)), ("layers", (4,)), ("part", (6.0, 10.0)), ("h", (30.0, 100.0)), ("filled", (True,))):
        for x in vals:
            out.append((f"{k}={x}", {k: x}))
    out += [("offset 2,0", {"offset": (2.0, 0.0)}), ("offset 3,3", {"offset": (3.0, 3.0)}),
            ("second part 14 mm away", {"second": (14.0, 0.0, 6.0, 2.0)}), ("second part 9 mm away (touching)", {"second": (9.0, 0.0, 6.0, 2.0)}),
            ("4L filled 8x8 @0.8", {"layers": 4, "filled": True, "n": 8, "pitch": 0.8})]
    if grid:
        for L, part, n, pitch in itertools.product((2, 4), (6.0, 10.0), (3, 5, 8), (0.8, 1.0, 1.5, 2.0)):
            out.append((f"grid L{L} part{part:g} n{n} pitch{pitch}", {"layers": L, "part": part, "n": n, "pitch": pitch}))
    return out


def errs(r, ref, amb, key):
    """!
    @brief Error of every part of a run against the reference, in percent of the reference rise.
    @param r run() result of the model.
    @param ref run() result of the reference.
    @param amb Ambient in degC.
    @param key 'peak' or 'mean'.
    @return list of percent errors, one per part.
    """
    return [v.pct(a[key], b[key], amb) for a, b in zip(r["parts"], ref["parts"])]


def main():
    """!
    @brief Run the cases and print the tables; write out/sweep.json.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--grid", action="store_true")
    ap.add_argument("--cell", type=float, default=0.5)
    args = ap.parse_args()
    rows = []
    cache = {}
    print("| case | FVM rise K (part 1) | Lumped zoned peak % | zoned mean % | one-node peak % | one-node mean % | E fvm K | E zoned err % | E one-node err % | zoned? | no-via baseline % | zoned peak minus baseline % | core share |")
    print("| :-- | --: | --: | --: | --: | --: | --: | --: | --: | :-- | --: | --: | --: |")
    for label, kw in cases(args.grid):
        t0 = time.time()
        a = {**BASE, **kw}
        p = v.board(**a)
        p0 = v.board(**{**a, "n": 0})
        key0 = json.dumps({k: a[k] for k in ("layers", "part", "h", "offset", "second")} | {"cell": args.cell}, sort_keys=True, default=str)
        if key0 not in cache:
            cache[key0] = {m: v.run(p0, m, args.cell) for m in ("fvm", "lumped1")}
        r0 = cache[key0]
        ref = v.run(p, "fvm", args.cell)
        z = v.run(p, "lumped", args.cell)
        o = v.run(p, "lumped1", args.cell)
        amb = ref["amb"]
        # Via effect on the hottest part: no-via board minus the board with vias, per model (peak of part 1)
        e = {"fvm": r0["fvm"]["parts"][0]["peak"] - ref["parts"][0]["peak"], "z": r0["lumped1"]["parts"][0]["peak"] - z["parts"][0]["peak"],
             "o": r0["lumped1"]["parts"][0]["peak"] - o["parts"][0]["peak"]}
        row = {"case": label, "kw": {k: kw[k] for k in kw}, "rise_fvm": ref["parts"][0]["peak"] - amb,
               "zoned_peak": errs(z, ref, amb, "peak"), "zoned_mean": errs(z, ref, amb, "mean"), "one_peak": errs(o, ref, amb, "peak"), "one_mean": errs(o, ref, amb, "mean"),
               "E_fvm": e["fvm"], "E_zoned_err": 100 * (e["z"] / e["fvm"] - 1) if e["fvm"] > 1e-9 else None, "E_one_err": 100 * (e["o"] / e["fvm"] - 1) if e["fvm"] > 1e-9 else None,
               "zoned": [bool(x[0]) for x in z["zoned"]], "no_via_err": [v.pct(r0["lumped1"]["parts"][i]["peak"], r0["fvm"]["parts"][i]["peak"], amb) for i in range(len(p.heaters))],
               "ref_peak": [x["peak"] for x in ref["parts"]], "ref_mean": [x["mean"] for x in ref["parts"]], "amb": amb,
               "ref0_peak": [x["peak"] for x in r0["fvm"]["parts"]], "l1_0_peak": [x["peak"] for x in r0["lumped1"]["parts"]], "core": v.core_info(p), "seconds": time.time() - t0}
        rows.append(row)
        f = lambda xs: " / ".join(f"{x:+.1f}" for x in xs)
        print(f"| {label} | {row['rise_fvm']:.1f} | {f(row['zoned_peak'])} | {f(row['zoned_mean'])} | {f(row['one_peak'])} | {f(row['one_mean'])} | {row['E_fvm']:.2f} | "
              f"{row['E_zoned_err'] if row['E_zoned_err'] is None else round(row['E_zoned_err'], 1)} | {row['E_one_err'] if row['E_one_err'] is None else round(row['E_one_err'], 1)} | {row['zoned']} | {f(row['no_via_err'])} | {f([a - b for a, b in zip(row['zoned_peak'], row['no_via_err'])])} | {row['core']['share']:.2f} |", flush=True)
    os.makedirs(os.path.join(os.path.dirname(HERE), "out"), exist_ok=True)
    with open(os.path.join(os.path.dirname(HERE), "out", "sweep.json"), "w") as fh:
        json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    main()
