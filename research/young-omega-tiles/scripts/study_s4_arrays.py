#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_s4_arrays.py
@brief S4, many vias: arrays of 4 to 576 vias under a source, the error of the via effect of the Lumped and Analytic models (program, patch of the review, rule of this study) against the
       fine-grid reference, and the cost of the correction (tiles, unknowns of the dense system, seconds, peak memory) with the coarsening above 1200 tiles exercised.
@details Boards: `s4cases.big_array(n, pitch)`, full copper on four layers, copper-filled 0.3 mm barrels, a source that covers the array. n = 2, 3, 5, 10, 15, 20, 24 at pitches 2.0 and 1.0
         mm (n = 24 at 1.0 mm is 576 vias), and 2, 3, 5, 10 at 3.5 mm. The reference is `reference_uniform` on a 1/16 mm grid (1/8 mm for boards above 60 mm).
         Variants: `A_prog` (the program), `A_fin` (self-term, spread, fixed 1 mm tile: the proposal under review), `A_rule` (the rule chosen by `study_s4_rule.py`, default
         cap 1 mm / 0.75 d), `A_rule+modes` (the same with 2 modes of G per tile), `L_prog`, `L_grp0` (the Lumped proposal).
Usage: python research/young-omega-tiles/scripts/study_s4_arrays.py [--quick] [--rule cap_nn|fixed|nn_radius]   (from the repository root; the 576-via reference takes several minutes).
       Results go to out/s4_arrays.json.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import outio                                                                # noqa: E402
import s4cases as sc                                                        # noqa: E402
import tilerule as tr                                                       # noqa: E402
import harness as hz                                                        # noqa: E402

QUICK = "--quick" in sys.argv
RULE_KIND = sys.argv[sys.argv.index("--rule") + 1] if "--rule" in sys.argv else "cap_nn"


def variants():
    """!
    @brief The models compared: name -> (model, context factory, modes_c).
    @return dict.
    """
    return {
        "A_prog": ("analytic", lambda: tr.patched("program", mode="off", spread="none"), 0.0),
        "A_fin": ("analytic", lambda: tr.patched("fixed", t_mm=1.0, floor_mm=0.25), 0.0),
        "A_rule": ("analytic", lambda: tr.patched(RULE_KIND, cap_mm=1.0, k_nn=0.75, m_rad=8.0, floor_mm=0.25), 0.0),
        "A_rule+modes": ("analytic", lambda: tr.patched(RULE_KIND, cap_mm=1.0, k_nn=0.75, m_rad=8.0, floor_mm=0.25, modes_c=2.0), 2.0),
        "L_prog": ("lumped", hz.VARIANTS["L_prog"][1], 0.0),
        "L_grp0": ("lumped", hz.VARIANTS["L_grp0"][1], 0.0),
    }


def main():
    """!
    @brief Run the arrays and print the tables.
    @return None.
    """
    sc.load_libraries()
    plan = [(n, 2.0) for n in (2, 3, 5, 10, 15, 20)] + [(n, 1.0) for n in (2, 3, 5, 10, 15, 20, 24)] + [(n, 3.5) for n in (2, 3, 5, 10)]
    if QUICK:
        plan = [(3, 2.0), (10, 2.0), (10, 1.0), (20, 1.0)]
    vs = variants()
    recs = []
    for n, pitch in plan:
        prob = sc.big_array(n, pitch)
        side = prob.board.width * 1e3
        dx = 1.0 / 16 if side <= 60 else 1.0 / 8
        e_ref = sc.reference_e(prob, dx, f"array{n}-{pitch}")
        q0 = hz.no_vias(prob)
        row = {"n": n, "vias": n * n, "pitch": pitch, "side": side, "e_ref": e_ref, "variants": {}}
        for name, (model, ctx, c) in vs.items():
            with ctx():
                cst = tr.cost(prob) if model == "analytic" and name != "A_prog" else None
                modes = max(300, int(math.ceil(c * side / max(cst["t_mm"], 0.1))) + 8) if (c > 0 and cst) else 300
                e, dt, peak = sc.timed_effect(prob, model, 0.5, modes, 10, q0)
            row["variants"][name] = {"err": 100.0 * (e / e_ref - 1.0), "seconds": dt, "peak_mb": peak, "tile_mm": cst["t_mm"] if cst else None, "unknowns": cst["unknowns"] if cst else None}
        recs.append(row)
        print(f"n={n} pitch={pitch} done: " + ", ".join(f"{k} {v['err']:+.1f}%" for k, v in row["variants"].items()), flush=True)
    names = list(vs)
    print("\n## Error of the via effect (percent) and E_ref (K)\n")
    outio.table(["vias", "pitch mm", "board mm", "E_ref K"] + names, [[r["vias"], r["pitch"], f"{r['side']:.0f}", f"{r['e_ref']:.2f}"] + [f"{r['variants'][k]['err']:+.1f}" for k in names] for r in recs])
    print("## Cost of the Analytic variants: tile mm / unknowns of the dense system / seconds of the run with vias / peak MB\n")
    an = [k for k in names if k.startswith("A_") and k != "A_prog"]
    outio.table(["vias", "pitch mm"] + an + ["A_prog s"], [[r["vias"], r["pitch"]] + [f"{r['variants'][k]['tile_mm']:.2f} / {r['variants'][k]['unknowns']} / {r['variants'][k]['seconds']:.2f} / "
                                                                                    f"{r['variants'][k]['peak_mb']:.0f}" for k in an] + [f"{r['variants']['A_prog']['seconds']:.2f}"] for r in recs])
    print("saved", outio.save("s4_arrays", recs))


if __name__ == "__main__":
    main()
