#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review_tables.py
@brief Review tables: the author's sweep, E3 and the decision against the reviewer's 3D reference, the cases the author did not test, and the window rule T_w.

@details Reads out/review_sample.json and out/review_cases.json (study_review_reference.py) and out/sweep_e3.json (study_estimator.py); prints the tables of README section 9.
Run from the repository root after those scripts: `.venv/bin/python research/fast-wave-oscillation/scripts/study_review_tables.py`.
"""

import json
import os

import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import axisym_stack as A                                             # noqa: E402
import impedance_layer as IL                                         # noqa: E402

# The cases with the heater off the top layer: (layers, heater layer 0-based, part side m) for the two-sided E3 of lib/impedance_layer.py
OFF_TOP = {"inner layer 2 of 4, 10 mm": (4, 1, 10e-3), "inner layer 2 of 4, 5 mm": (4, 1, 5e-3), "bottom layer of 2, 10 mm": (2, 1, 10e-3)}
OUT = os.path.join(HERE, "..", "out")
POWERS = [0.5, 1, 2, 5, 10, 20]


def pct(x):
    """!
    @brief Min, 5 %, median, 95 %, max of an array as text.
    @param x Values.
    @return String.
    """
    p = np.percentile(np.asarray(x, dtype=float), [0, 5, 50, 95, 100])
    return " / ".join(f"{v:.3f}" for v in p)


def decisions(rows, est, true="ref"):
    """!
    @brief Wrong decisions of one estimate of the oscillation, one heater, budget 1 K, for the powers of POWERS.
    @param rows Records.
    @param est Function of a record giving the estimated swing per watt.
    @param true Key of the true swing per watt.
    @return Tuple (total, wrongly averaged, wrongly resolved, worst true swing averaged).
    """
    tot = wa = wr = 0
    worst = 0.0
    for r in rows:
        for P in POWERS:
            tot += 1
            e, t = P * est(r), P * r[true]
            if e <= 1.0 < t:
                wa += 1
                worst = max(worst, t)
            if t <= 1.0 < e:
                wr += 1
    return tot, wa, wr, worst


def main():
    """!
    @brief Print.
    @return None.
    """
    s = json.load(open(os.path.join(OUT, "review_sample.json")))
    print(f"== A. sample: {len(s)} cases (12 boards x 11 frequencies x 4 duties) ==")
    print("reviewer's 3D reference / author's axisymmetric reference:", pct([r["ref"] / r["author_ref"] for r in s if r["author_ref"]]))
    for f in sorted({r["f"] for r in s}):
        sub = [r for r in s if r["f"] == f]
        print(f"  f {f:7g} Hz: rev/author {pct([r['ref'] / r['author_ref'] for r in sub])}; FVM/rev {pct([r['fvm'] / r['ref'] for r in sub])}; "
              f"E3/rev {pct([r['e3'] / r['ref'] for r in sub])}")
    print("FVM (side/4) / reference:", pct([r["fvm"] / r["ref"] for r in s]))
    print("FVM (2 mm, the application's cell) / FVM (side/4):", pct([r["fvm_2mm"] / r["fvm"] for r in s]))
    for side in (2.0, 5.0, 10.0):
        print(f"   side {side:g} mm: FVM 2 mm / FVM side/4 {pct([r['fvm_2mm'] / r['fvm'] for r in s if r['side'] == side])}")
    print("FDM / FVM (same cell):", pct([r["fdm"] / r["fvm"] for r in s]))
    print("E3 / reference:", pct([r["e3"] / r["ref"] for r in s]))
    print("E3 / reference, f >= 1 Hz:", pct([r["e3"] / r["ref"] for r in s if r["f"] >= 1]))
    print("Table: FVM / reference, duty 50 %, h 10 (layers, side: 0.1 .. 3000 Hz)")
    for L in (1, 2, 4):
        for side in (2.0, 5.0, 10.0):
            row = sorted([r for r in s if r["layers"] == L and r["side"] == side and r["h"] == 10 and r["duty"] == 0.5], key=lambda r: r["f"])
            print(f"  {L}, {side:4g} mm: " + " ".join(f"{r['fvm'] / r['ref']:.2f}" for r in row))
    for name, est in (("program FVM (side/4)", lambda r: r["fvm"]), ("program FVM (2 mm)", lambda r: r["fvm_2mm"]), ("program FDM", lambda r: r["fdm"]),
                      ("floor max(FVM, E3)", lambda r: max(r["fvm"], r["e3"])), ("floor max(FVM 2 mm, E3)", lambda r: max(r["fvm_2mm"], r["e3"]))):
        tot, wa, wr, worst = decisions(s, est)
        print(f"decisions, {name}: {tot} decisions, wrongly averaged {wa} ({100 * wa / tot:.1f} %), wrongly resolved {wr}, worst true swing averaged {worst:.2f} K")
    # The window rule T_w = 5 s (s / 0.8 mm)^2, s = thickness / layers: on the period (proposal) and on the shortest stretch
    for key, label in (("period", "period"), ("stretch", "shortest stretch")):
        print(f"window rule on the {label}: FVM / reference where the rule says 'the program is right' (>= T_w)")
        for L in (1, 2, 4):
            tw = 5.0 * ((1.6 / L) / 0.8) ** 2
            t = (lambda r: 1 / r["f"]) if key == "period" else (lambda r: min(r["duty"], 1 - r["duty"]) / r["f"])
            sub = [r["fvm"] / r["ref"] for r in s if r["layers"] == L and t(r) >= tw]
            print(f"   {L} layers, T_w {tw:g} s: {len(sub)} cases, " + (pct(sub) if sub else "none"))
    print("FVM / reference against the shortest stretch (all boards; 10 % reached where):")
    for lo, hi in ((0, 0.1), (0.1, 0.3), (0.3, 1), (1, 2), (2, 4), (4, 6)):
        for L in (1, 2, 4):
            sub = [r["fvm"] / r["ref"] for r in s if r["layers"] == L and lo <= min(r["duty"], 1 - r["duty"]) / r["f"] < hi]
            if sub:
                print(f"   stretch {lo:g}-{hi:g} s, {L} layers: min {min(sub):.3f}, max {max(sub):.3f}")
    if not os.path.exists(os.path.join(OUT, "review_cases.json")):
        return
    c = json.load(open(os.path.join(OUT, "review_cases.json")))
    if os.path.exists(os.path.join(OUT, "review_bare.json")):
        # The bare cases of review_cases.json were run before the thin surface cell (top_first) existed: replaced by the run of `bare`
        bare = json.load(open(os.path.join(OUT, "review_bare.json")))
        names = {r["case"] for r in bare}
        c = [r for r in c if r["case"] not in names] + bare
    if os.path.exists(os.path.join(OUT, "review_example.json")):
        c += json.load(open(os.path.join(OUT, "review_example.json")))
    for r in c:
        if r["case"] in OFF_TOP:
            L, lay, side = OFF_TOP[r["case"]]
            r["e3_layer"] = IL.square_swing_on_layer(A.Stack(layers=L), lay, 1.0 / r["f"], r["duty"], float(np.sqrt(side * side / np.pi)), 10.0, 10.0)
    print("== B. cases the author did not test (duty 30 %): reference K/W, FVM/ref, FDM/ref, E3/ref, floor/ref (and the two-sided E3/ref for a heater off the top) ==")
    for case in dict.fromkeys(r["case"] for r in c):
        rows = sorted([r for r in c if r["case"] == case and r["duty"] == 0.3], key=lambda r: r["f"])
        print(f"  {case}")
        for r in rows:
            fdm = f"{r['fdm'] / r['ref']:.3f}" if r.get("fdm") else "  -  "
            two = f"  E3 two-sided {r['e3_layer'] / r['ref']:.3f}" if "e3_layer" in r else ""
            print(f"    {r['f']:7g} Hz ref {r['ref']:.5f}  FVM {r['fvm'] / r['ref']:.3f}  FDM {fdm}  E3 {r['e3'] / r['ref']:.3f}  floor {max(r['fvm'], r['e3']) / r['ref']:.3f}{two}")
        allr = [r for r in c if r["case"] == case]
        tot, wa, wr, worst = decisions(allr, lambda r: r["fvm"])
        tot2, wa2, wr2, worst2 = decisions(allr, lambda r: max(r["fvm"], r["e3"]))
        extra = ""
        if case in OFF_TOP:
            _, wa3, wr3, _ = decisions(allr, lambda r: max(r["fvm"], r["e3_layer"]))
            extra = f"; two-sided floor wrongly averaged {wa3}, wrongly resolved {wr3}"
        print(f"    decisions ({tot}): program wrongly averaged {wa}, floor wrongly averaged {wa2}, floor wrongly resolved {wr2}{extra}")


if __name__ == "__main__":
    main()
