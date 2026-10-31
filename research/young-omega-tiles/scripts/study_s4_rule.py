#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_s4_rule.py
@brief S4, the tile rule: candidate rules for the tile of the Analytic via correction on the simple and the dense boards, and the limit where the rule breaks.
@details Candidates (`tilerule.tile_by_rule`): the program's tile with the self-term and the spread (`program`), a fixed 1 mm (`fixed`, the proposal under review), a multiple of the median
         nearest-neighbour distance d (`nn`, k = 0.5, 0.75, 1), the smaller of a cap of 1 mm and 0.75 d (`cap_nn`), a multiple of the target radius a of the barrel (`radius`, m = 6, 8, 10)
         and the smaller of 0.75 d and 8 a (`nn_radius`). Every rule is capped at the program's tile, floored at 0.25 mm, and coarsened above 1200 active tiles.
         Part 1: error of every rule on the simple boards (and the tile it chose), mean and maximum absolute error.
         Part 2 (where the rule breaks): the dense boards (pitch 0.45 to 1.0 mm with the 0.3 mm drill, drills of 0.2 to 0.8 mm at 1.5 mm pitch): the rules that survive Part 1 against the
                 reference, with the tile the rule chose, the ratio tile / pitch and tile / a.
         Part 3 (the floor and the second constant): the floor of the tile (0.25, 0.4, 0.6 mm) on the dense boards, and the modes of G (64 against 2 per tile) on the rule that wins.
Usage: python research/young-omega-tiles/scripts/study_s4_rule.py [--quick]   (from the repository root; minutes). Results go to out/s4_rule.json.
"""

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import outio                                                                # noqa: E402
import s4cases as sc                                                        # noqa: E402
import tilerule as tr                                                       # noqa: E402
import harness as hz                                                        # noqa: E402

QUICK = "--quick" in sys.argv
RES = {}

RULES = {
    "program tile": dict(kind="program"),
    "fixed 1 mm": dict(kind="fixed", t_mm=1.0),
    "cap 1 mm / 0.75 d": dict(kind="cap_nn", cap_mm=1.0, k_nn=0.75),
    "0.5 d": dict(kind="nn", k_nn=0.5),
    "0.75 d": dict(kind="nn", k_nn=0.75),
    "1.0 d": dict(kind="nn", k_nn=1.0),
    "6 a": dict(kind="radius", m_rad=6.0),
    "8 a": dict(kind="radius", m_rad=8.0),
    "10 a": dict(kind="radius", m_rad=10.0),
    "min(0.75 d, 8 a)": dict(kind="nn_radius", k_nn=0.75, m_rad=8.0),
}


def evaluate(items, rules, floor_mm=0.25, modes_c=0.0):
    """!
    @brief Error of every rule on every board.
    @param items Entries of `s4cases.corpus`.
    @param rules Dict name -> keyword arguments of `tilerule.patched`.
    @param floor_mm Floor of the tile in mm.
    @param modes_c Modes of G per tile.
    @return list of dicts (board, rule, err, tile_mm, e_ref, d_nn, a, unknowns).
    """
    out = []
    for item in items:
        prob = item["problem"]
        e_ref = sc.reference_e(prob, item["dx"], item["label"])
        q0 = hz.no_vias(prob)
        d_nn, a = sc.nn_info(prob)
        side = prob.board.width * 1e3
        for name, kw in rules.items():
            with tr.patched(floor_mm=floor_mm, modes_c=modes_c, **kw):
                cst = tr.cost(prob)
                m = max(300, int(math.ceil(modes_c * side / max(cst["t_mm"], 0.1))) + 8) if modes_c > 0 else 300
                e = sc.effect(prob, "analytic", 0.5, m, 10, q0)
            out.append({"board": item["label"], "pitch": item["pitch"], "rule": name, "err": 100.0 * (e / e_ref - 1.0), "tile_mm": cst["t_mm"], "e_ref": e_ref, "d_nn_mm": d_nn, "a_mm": a,
                        "unknowns": cst["unknowns"]})
    return out


def show(res, rules, title):
    """!
    @brief Print the table board x rule and the summary.
    @param res Output of `evaluate`.
    @param rules The rule names.
    @param title Heading.
    @return None.
    """
    print(f"## {title}\n")
    boards = list(dict.fromkeys(r["board"] for r in res))
    rows = []
    for b in boards:
        rr = {r["rule"]: r for r in res if r["board"] == b}
        rows.append([b] + [f"{rr[n]['err']:+.1f} ({rr[n]['tile_mm']:.2f})" for n in rules])
    outio.table(["board (error % (tile mm))"] + list(rules), rows)
    srows = []
    for n in rules:
        e = np.array([r["err"] for r in res if r["rule"] == n])
        srows.append([n, f"{np.mean(np.abs(e)):.1f}", f"{np.max(np.abs(e)):.1f}", f"{e.min():+.1f}", f"{e.max():+.1f}"])
    outio.table(["rule", "mean |err| %", "max |err| %", "min %", "max %"], srows)


def main():
    """!
    @brief Run the three parts and save.
    @return None.
    """
    sc.load_libraries()
    rules = RULES if not QUICK else {k: RULES[k] for k in ("program tile", "fixed 1 mm", "cap 1 mm / 0.75 d", "0.75 d", "8 a", "min(0.75 d, 8 a)")}
    simple = sc.corpus("simple")
    if QUICK:
        simple = simple[::2]
    r1 = evaluate(simple, rules)
    show(r1, rules, "1. Candidate tile rules on the simple boards (error of the via effect, percent; the tile chosen in brackets)")
    RES["simple"] = r1
    dense = sc.corpus("dense")
    survivors = {k: v for k, v in rules.items() if k != "program tile"}
    r2 = evaluate(dense, survivors)
    show(r2, survivors, "2. Where the rules break: the dense boards")
    RES["dense"] = r2
    best = min(survivors, key=lambda n: np.mean([abs(r["err"]) for r in r1 + r2 if r["rule"] == n]))
    print(f"rule with the smallest mean absolute error over both sets: {best}\n")
    fl = {}
    for f in (0.25, 0.4, 0.6):
        fl[f"floor {f} mm"] = evaluate(dense, {best: survivors[best]}, floor_mm=f)
    rows = []
    for item in dense:
        rows.append([item["label"]] + [f"{[r for r in fl[k] if r['board'] == item['label']][0]['err']:+.1f} ({[r for r in fl[k] if r['board'] == item['label']][0]['tile_mm']:.2f})" for k in fl])
    print(f"## 3. The floor of the tile (rule {best}; error % (tile mm))\n")
    outio.table(["board"] + list(fl), rows)
    m2 = evaluate(dense, {best: survivors[best]}, modes_c=2.0)
    print("modes of G: 64 (the program) against 2 per tile on the dense boards\n")
    outio.table(["board", "64 modes %", "2 W/t %"], [[x["board"], f"{y['err']:+.1f}", f"{x['err']:+.1f}"] for x, y in
                zip(m2, evaluate(dense, {best: survivors[best]}))])
    RES["floor"] = fl
    RES["modes2"] = m2
    RES["best"] = best
    print("saved", outio.save("s4_rule", RES))


if __name__ == "__main__":
    main()
