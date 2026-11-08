#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_rule.py
@brief Warning rule for a part near a board side or corner: hits and false alarms on the sweep, 17 frozen boards and random boards; and the robustness of the image-potential correction.
@details Part A reads out/edge_sweep.json (study_edge_sweep.py). Part B runs the 17 boards of tests/regression (the five-model harness list) with the Lumped as the program has it and with the
         candidate "potlinks", against the FVM at 0.5 mm, on the hottest temperature of the board. Part C does the same on random single-part boards (2 or 4 layers, copper fill 0.4 to 1,
         board 30 to 100 mm, part 2 to 12 mm anywhere on the board, edge film 5 to 200 W/m2K; seed 20260101). A case is bad when the program's Lumped reads the rise more than 8 % too cool.
         The rule flags a part when its gap g1 to the nearest side is at most max(k * side, floor) or both gaps g1, g2 are at most max(k2 * side, floor).
         Writes out/rule.json. Run from the repository root with PCBT_TREE set as for the other studies.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import boards as B  # noqa: E402
import gaps as G  # noqa: E402
import variants as V  # noqa: E402
from pcbthermal import SolverOptions, simulate  # noqa: E402

BAD = -8.0                       # percent of the rise


def flagged(side, g1, g2, k=1.0, floor=5.0):
    """!
    @brief The warning rule.
    @param side Equivalent side of the part in mm.
    @param g1 Gap to the nearest side in mm.
    @param g2 Gap to the nearest side of the other direction in mm.
    @param k Gap in sides.
    @param floor Smallest gap that always counts, in mm.
    @return bool.
    """
    return g1 <= max(k * side, floor)


def rates(items, k, floor):
    """!
    @brief Hit and false-alarm counts of the rule on a list of (side, g1, g2, bad).
    @param items List of tuples.
    @param k Gap in sides.
    @param floor Floor in mm.
    @return (bad cases, hits, flagged cases, false alarms).
    """
    nb = sum(1 for *_, bad in items if bad)
    hit = sum(1 for s, a, b2, bad in items if bad and flagged(s, a, b2, k, floor))
    fl = sum(1 for s, a, b2, bad in items if flagged(s, a, b2, k, floor))
    return nb, hit, fl, fl - hit


def run_problem(p, cell=0.5):
    """!
    @brief Hottest rise of the FVM and of the Lumped variants for a problem.
    @param p Problem.
    @param cell Cell in mm.
    @return dict model -> rise in K (None when a model fails).
    """
    out = {}
    for name, model, var in (("fvm", "fvm", None), ("program", "lumped", "program"), ("potlinks", "lumped", "potlinks")):
        try:
            if var:
                V.install(var)
            r = simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model]
            out[name] = float(r.t_max - p.board.ambient)
        except Exception as e:                       # a board the model cannot run is reported, not hidden
            out[name] = None
            out[name + "_error"] = str(e)[:60]
    return out


def main():
    """!
    @brief Run parts A, B and C and print the tables.
    @return None.
    """
    sweep = json.loads((B.OUT / "edge_sweep.json").read_text())
    items = []
    for c in sweep:
        side = c["side"]
        g1 = c["d"] if c["place"] == "edge" else c["d"]
        items.append((side, g1, c["d"], c["program"][1] < BAD))
    print("## A. sweep (hottest node, bad = more than 8 % too cool):", len(items), "cases,", sum(i[3] for i in items), "bad")
    print("| k (sides) | floor mm | flagged | hits | false alarms | missed |")
    print("| --: | --: | --: | --: | --: | --: |")
    for k in (0.0, 0.5, 1.0, 2.0):
        for floor in (0.0, 2.0, 5.0, 10.0):
            nb, hit, fl, fa = rates(items, k, floor)
            print(f"| {k:g} | {floor:g} | {fl} | {hit}/{nb} | {fa} | {nb - hit} |")
    res = {"sweep_items": items}

    sys.path.insert(0, str(B.tree.ROOT / "tests" / "regression"))
    import regress_boards as RB  # noqa: E402
    print("\n## B. the 17 frozen boards (hottest rise, error of the Lumped against the FVM at 0.5 mm, %)")
    print("| board | parts | side mm | g1 mm | program % | potlinks % | flagged (k 1, floor 5) |")
    print("| :-- | --: | --: | --: | --: | --: | :-- |")
    frozen = []
    for name in RB.board_names():
        p = RB.build(name, B.tree.ROOT / "examples")
        gs = G.gaps_mm(p)
        r = run_problem(p)
        if r.get("fvm") is None:
            print(f"| {name} | - | - | - | fvm failed | | |")
            continue
        e = {v: (None if r.get(v) is None else 100 * (r[v] / r["fvm"] - 1)) for v in ("program", "potlinks")}
        flag = any(flagged(*g) for g in gs)
        g1 = min((g[1] for g in gs), default=float("nan"))
        s = max((g[0] for g in gs), default=float("nan"))
        frozen.append({"board": name, "gaps": gs, "err": e, "flagged": flag})
        f = lambda x: "n/a" if x is None else f"{x:+.1f}"
        print(f"| {name} | {len(gs)} | {s:.1f} | {g1:.1f} | {f(e['program'])} | {f(e['potlinks'])} | {'yes' if flag else 'no'} |", flush=True)
    res["frozen"] = frozen

    rng = np.random.default_rng(20260101)
    rows = []
    for i in range(120):
        W = float(rng.uniform(30, 100))
        H = float(rng.uniform(30, 100))
        side = float(rng.uniform(2, 12))
        cx = float(rng.uniform(side / 2, W - side / 2))
        cy = float(rng.uniform(side / 2, H - side / 2))
        p = B.board(W, H, side, (cx, cy), layers=int(rng.choice([2, 4])), fill=float(rng.choice([1.0, 0.7, 0.4])), h_side=float(np.exp(rng.uniform(np.log(5), np.log(200)))))
        gs = G.gaps_mm(p)[0]
        r = run_problem(p)
        if r.get("fvm") is None or r.get("program") is None:
            continue
        rows.append({"W": W, "H": H, "gaps": gs, "program": 100 * (r["program"] / r["fvm"] - 1), "potlinks": None if r.get("potlinks") is None else 100 * (r["potlinks"] / r["fvm"] - 1)})
    res["random"] = rows
    items_r = [(r["gaps"][0], r["gaps"][1], r["gaps"][2], r["program"] < BAD) for r in rows]
    print("\n## C. random single-part boards:", len(rows), "boards,", sum(i[3] for i in items_r), "bad")
    print("| k | floor mm | flagged | hits | false alarms | missed |")
    print("| --: | --: | --: | --: | --: | --: |")
    for k in (0.5, 1.0, 2.0):
        for floor in (2.0, 5.0, 10.0):
            nb, hit, fl, fa = rates(items_r, k, floor)
            print(f"| {k:g} | {floor:g} | {fl} | {hit}/{nb} | {fa} | {nb - hit} |")
    for v in ("program", "potlinks"):
        a = np.array([r[v] for r in rows if r[v] is not None])
        print(f"{v}: mean {a.mean():+.1f} %, min {a.min():+.1f}, max {a.max():+.1f}, share beyond -8 %: {np.mean(a < BAD):.2f}, beyond +8 %: {np.mean(a > 8):.2f}")
    B.OUT.mkdir(exist_ok=True)
    (B.OUT / "rule.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
