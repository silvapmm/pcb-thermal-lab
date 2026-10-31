#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_s4_heldout.py
@brief S4 checked on boards kept apart from the choice (review): does the tile rule min(1 mm, 0.75 d_nn) of the Analytic via correction, and the macro cap 0.75 of the Lumped
       cluster well, hold on boards that were not used to choose them, including pitches below 0.6 mm?
@details The rule was chosen on the 26 boards of `study_s4_rule.py` and the cap on the boards of `study_s4_lumped.py`. Here:
         Part 1 (held-out boards, fine-grid reference): unit cells of pitch 0.4, 0.45 and 0.5 mm (they do not exercise the pitch branch of the rule: a lone via has no neighbour);
                 thermal pads of pitch 0.45 to 0.9 mm with drills 0.2 to 0.3 mm, 2 and 4 layers, open and copper (the region where the rule and the fixed 1 mm tile differ);
                 lone vias at other distances and with other source sizes and boards, a row of 3, arrays at pitch 1.5 and 2.5 and an off-centre array (the region where they coincide:
                 a check of the 1 mm tile itself on new geometry). Columns: the program's Analytic, fixed 1 mm, the rule; the program's Lumped, the cluster well, the cluster well with
                 the macro cap 0.75.
         Part 2 (the Lumped macro cap on the 17 arrays of `study_s4_arrays.py`, where the cluster well was -32 to -54 % with 100 to 400 vias at pitch 2.0): the reference effect is read
                 from `out/s4_arrays.json` when it exists (it is recomputed otherwise: minutes and GB for the large boards).
         Part 3 (the Lumped macro cap on the example board and its denser arrays of `study_s4_example.py`): the copper-fill gain and the open-via effect, against the FVM with the
                 mean-potential via treatment at 0.25 mm read from `out/s4_example.json` (recomputed otherwise).
         The error is 100 (E_model / E_ref - 1) of the via effect E = T_max(no vias) - T_max(vias).
Usage: python research/young-omega-tiles/scripts/study_s4_heldout.py [--quick]   (from the repository root; a few minutes). Results go to out/s4_heldout.json.
"""

import contextlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import outio                                                                # noqa: E402
import s4cases as sc                                                        # noqa: E402
import tilerule as tr                                                       # noqa: E402
import harness as hz                                                        # noqa: E402
import cases                                                                # noqa: E402
import lumped_patch as lp                                                   # noqa: E402

QUICK = "--quick" in sys.argv
OUT = os.path.join(os.path.dirname(HERE), "out")

# name -> (model, context factory). A_prog is the program as shipped (no self-term, no spread, the program's tile).
VARIANTS = {
    "A_prog": ("analytic", lambda: tr.patched("program", mode="off", spread="none")),
    "A_fixed1": ("analytic", lambda: tr.patched("fixed", t_mm=1.0, floor_mm=0.25)),
    "A_rule": ("analytic", lambda: tr.patched("cap_nn", cap_mm=1.0, k_nn=0.75, floor_mm=0.25)),
    "L_prog": ("lumped", lambda: contextlib.nullcontext()),
    "L_cluster": ("lumped", lambda: lp.patched("krogh", cell="nn", cluster=True)),
    "L_cap075": ("lumped", lambda: lp.patched("krogh", cell="nn", cluster=True, macro_cap=0.75)),
}


def heldout_boards():
    """!
    @brief The boards kept apart: (label, Problem, dx of the reference in mm, family).
    @return list of tuples.
    """
    b = []
    for p in (0.4, 0.45, 0.5):
        b.append((f"unit cell {p} mm, 2 layers, Cu", sc.unit_cell(p, 2), 0.05 if p != 0.45 else 0.025, "unit"))
    # Thermal pads on a 16 mm board with a 4 mm source (dx 0.05 mm divides every coordinate)
    pads = [(5, 0.45, 0.3, 4, 385.0), (5, 0.5, 0.3, 4, 385.0), (5, 0.5, 0.2, 2, 385.0), (4, 0.6, 0.25, 4, 385.0), (6, 0.7, 0.3, 4, 385.0), (4, 0.9, 0.3, 4, 385.0),
            (3, 0.8, 0.3, 2, 0.0), (5, 0.5, 0.3, 4, 0.0)]
    if QUICK:
        pads = pads[:2]
    for n, pitch, d, layers, fk in pads:
        fill = "Cu" if fk > 0 else "open"
        b.append((f"pad {n} x {n} pitch {pitch}, drill {d}, {layers} layers, {fill}", cases.pad(layers, n, pitch, d, fk, side_mm=16.0, source_mm=4.0), 0.05, "pad"))
    if not QUICK:
        # Geometry where rule and fixed 1 mm coincide: a check of the 1 mm tile itself (1/16 mm reference)
        for dist in (1.0, 3.0, 5.0):
            b.append((f"lone via {dist} mm from the source centre (3 mm source, 30 mm board)", cases.lone_via(30.0, 0.3, 385.0, 2, 3.0, dist), 1.0 / 16, "lone"))
        b.append(("lone via 2.5 mm, 5 mm source (via on the source edge)", cases.lone_via(30.0, 0.3, 385.0, 2, 5.0, 2.5), 1.0 / 16, "lone"))
        b.append(("lone via 2 mm, 2 mm source, 25 mm board", cases.lone_via(25.0, 0.3, 385.0, 2, 2.0, 2.0), 1.0 / 16, "lone"))
        b.append(("row of 3, pitch 2.0", cases.row(3, 2.0, 0.3, 385.0), 1.0 / 16, "row"))
        b.append(("3 x 3 array pitch 2.5, 2 layers, Cu", cases.array(2, 3, 2.5, 0.3, 385.0), 1.0 / 16, "array"))
        b.append(("4 x 4 array pitch 1.5, 4 layers, Cu", cases.array(4, 4, 1.5, 0.3, 385.0), 1.0 / 16, "array"))
        b.append(("3 x 3 array pitch 3.5 off-centre (2, 1) mm, open", cases.array(4, 3, 3.5, 0.3, 0.0, offset_mm=(2.0, 1.0)), 1.0 / 16, "array"))
    return b


def run_errors(prob, e_ref, names):
    """!
    @brief Errors of a set of variants on one board, with the tile the rule variants chose.
    @param prob Problem with vias.
    @param e_ref Reference effect in K.
    @param names Variant names of VARIANTS.
    @return dict name -> dict(err, tile_mm).
    """
    q0 = hz.no_vias(prob)
    out = {}
    for name in names:
        model, ctx = VARIANTS[name]
        with ctx():
            tile = tr.cost(prob)["t_mm"] if name in ("A_fixed1", "A_rule") else None
            e = sc.effect(prob, model, 0.5, 300, 10, q0)
        out[name] = {"err": 100.0 * (e / e_ref - 1.0), "tile_mm": tile}
    return out


def part1():
    """!
    @brief The held-out boards.
    @return list of dict.
    """
    print("## 1. Boards kept apart from the choice: error of the via effect (percent; the tile of the rule variants in brackets)\n")
    names = list(VARIANTS)
    recs, rows = [], []
    for label, prob, dx, fam in heldout_boards():
        e_ref = sc.reference_e(prob, dx)
        d_nn, _a = sc.nn_info(prob)
        r = run_errors(prob, e_ref, names)
        recs.append({"board": label, "family": fam, "e_ref": e_ref, "d_nn_mm": d_nn, "errors": r})
        cells = []
        for n in names:
            t = r[n]["tile_mm"]
            cells.append(f"{r[n]['err']:+.1f}" + (f" ({t:.2f})" if t is not None else ""))
        rows.append([label, f"{d_nn:.2f}" if d_nn != float("inf") else "-", f"{e_ref:.3f}"] + cells)
        print(f"{label}: " + ", ".join(f"{n} {r[n]['err']:+.1f}%" for n in names), flush=True)
    print()
    outio.table(["board", "d_nn mm", "E_ref K"] + names, rows)
    summ = []
    for n in names:
        errs = [abs(x["errors"][n]["err"]) for x in recs]
        summ.append([n, f"{sum(errs) / len(errs):.1f}", f"{max(errs):.1f}"])
    outio.table(["variant", "mean |err| %", "max |err| %"], summ)
    return recs


def part2():
    """!
    @brief The Lumped variants on the arrays of study_s4_arrays (reference read from its output).
    @return list of dict.
    """
    print("## 2. The Lumped macro cap on the arrays of study_s4_arrays.py (error of the via effect, percent)\n")
    path = os.path.join(OUT, "s4_arrays.json")
    stored = {}
    if os.path.exists(path):
        with open(path) as f:
            for r in json.load(f):
                stored[(r["n"], r["pitch"])] = r
    plan = [(n, 2.0) for n in (2, 3, 5, 10, 15, 20)] + [(n, 1.0) for n in (2, 3, 5, 10, 15, 20, 24)] + [(n, 3.5) for n in (2, 3, 5, 10)]
    if QUICK:
        plan = [(3, 2.0), (10, 2.0)]
    names = ["L_prog", "L_cluster", "L_cap075"]
    recs, rows = [], []
    for n, pitch in plan:
        prob = sc.big_array(n, pitch)
        if (n, pitch) in stored:
            e_ref, src = stored[(n, pitch)]["e_ref"], "stored"
        else:
            side = prob.board.width * 1e3
            e_ref, src = sc.reference_e(prob, 1.0 / 16 if side <= 60 else 1.0 / 8), "computed"
        r = run_errors(prob, e_ref, names)
        old = stored.get((n, pitch), {}).get("variants", {}).get("L_grp0", {}).get("err")
        recs.append({"vias": n * n, "pitch": pitch, "e_ref": e_ref, "source": src, "errors": r, "cluster_in_s4_arrays": old})
        rows.append([n * n, pitch, f"{e_ref:.2f} ({src})"] + [f"{r[k]['err']:+.1f}" for k in names] + ["-" if old is None else f"{old:+.1f}"])
    outio.table(["vias", "pitch mm", "E_ref K"] + names + ["cluster in s4_arrays"], rows)
    return recs


def part3():
    """!
    @brief The Lumped variants on the example board and its denser arrays (copper-fill gain and open-via effect, K).
    @return list of dict.
    """
    import study_s4_example as se
    print("## 3. The Lumped macro cap on the example board (gain of the copper fill / via effect of the open board, K)\n")
    path = os.path.join(OUT, "s4_example.json")
    ref = {}
    if os.path.exists(path):
        with open(path) as f:
            for r in json.load(f)["arrays"]:
                ref[r["board"]] = r["FVM_fix 0.25 mm"]
    recs, rows = [], []
    for label, arr in (("3 x 3, 3.5 mm (own)", None), ("5 x 5, 1.2 mm", (5, 1.2)), ("7 x 7, 1.0 mm", (7, 1.0))):
        po, pcu, pn = se.board(array=arr), se.board(385.0, array=arr), se.board(none=True)
        if label not in ref:
            ctx = hz.VARIANTS["FVM_fix"][1]
            t_o = se.t_max(po, "fvm", 0.25, ctx)
            ref[label] = {"gain": t_o - se.t_max(pcu, "fvm", 0.25, ctx), "effect_open": se.t_max(pn, "fvm", 0.25, ctx) - t_o}
        rec = {"board": label, "reference": ref[label]}
        cells = [f"{ref[label]['gain']:.2f} / {ref[label]['effect_open']:.2f}"]
        for name in ("L_prog", "L_cluster", "L_cap075"):
            _m, ctx = VARIANTS[name]
            t_o = se.t_max(po, "lumped", 0.5, ctx)
            g, e = t_o - se.t_max(pcu, "lumped", 0.5, ctx), se.t_max(pn, "lumped", 0.5, ctx) - t_o
            rec[name] = {"gain": g, "effect_open": e}
            cells.append(f"{g:.2f} / {e:.2f} ({100.0 * (e / ref[label]['effect_open'] - 1.0):+.0f} %)")
        recs.append(rec)
        rows.append([label] + cells)
    outio.table(["board", "FVM mean-potential 0.25 mm", "Lumped program", "Lumped cluster", "Lumped cluster, macro cap 0.75"], rows)
    return recs


def main():
    """!
    @brief Run the three parts and save.
    @return None.
    """
    sc.load_libraries()
    res = {"heldout": part1(), "arrays_lumped": part2()}
    if not QUICK:
        res["example_lumped"] = part3()
    print("saved", outio.save("s4_heldout", res))


if __name__ == "__main__":
    main()
