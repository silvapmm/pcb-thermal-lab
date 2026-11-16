#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file report_transient_boards.py
@brief Tables of the transient comparison from the cache of `study_transient_boards.py`: steady resistance, time to 63 %, the response at fixed times and the square wave, of every
       model of the program against the finite-element reference at its finest mesh level (hottest top node and footprint mean). Run with the program's interpreter from the
       repository root: `.venv/bin/python research/transient-reference-boards/scripts/report_transient_boards.py [--json out.json]`.
@details Errors are `model / reference - 1` in percent. The reference is the finest finite-element level in the cache; the change from the previous level is printed as the
         mesh uncertainty. The wave is post-processed by `profiles.wave_response` for the program and for the finite-element step response alike.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import numpy as np                                                       # noqa: E402
import refboards as R                                                    # noqa: E402

TIMES = (0.3, 1.0, 3.0, 10.0, 30.0, 100.0)
WAVES = {"simple4": (2.0, 0.3), "vias": (20.0, 0.3), "plate": (50.0, 0.3), "two2": (20.0, 0.3), "disc": (20.0, 0.3)}


def at(t, z, tt):
    """!
    @brief Response at a time, linear in log time (zero before the first sample).
    @param t Times.
    @param z Curve.
    @param tt Time.
    @return float.
    """
    t, z = np.asarray(t, float), np.asarray(z, float)
    if t[0] <= 0:
        t, z = t[1:], z[1:]
    return float(np.interp(np.log(tt), np.log(t), z))


def levels(res, name):
    """!
    @brief Finite-element levels of a board in the cache, coarse to fine.
    @param res Cache.
    @param name Board.
    @return list of (level str, entry).
    """
    out = [(k.split("|")[2], v) for k, v in res.items() if k.startswith(f"fem|{name}|")]
    return sorted(out, key=lambda x: x[1]["n"])


def main():
    """!
    @brief Print the tables.
    @return None.
    """
    res = json.load(open(os.path.join(HERE, "..", "out", "boards.json")))
    rows = {}
    for name in R.BOARDS:
        lv = levels(res, name)
        if not lv:
            continue
        print(f"\n=== {name}: finite-element levels " + ", ".join(f"{a} ({e['n']} unknowns, energy residual {e['energy_residual']:.1e}, {e['seconds']:.0f} s)" for a, e in lv))
        print("level   steady hot  steady mean  t63 hot    t63 mean   | z(t) hot at " + " ".join(f"{t:g}s" for t in TIMES))
        for a, e in lv:
            print(f"{a:>5}  {e['hot_steady']:10.4f} {e['mean_steady']:11.4f} {e['hot_t63']:9.3f} {e['mean_t63']:10.3f}   | " + " ".join(f"{at(e['t'], e['hot'], t):.4f}" for t in TIMES))
        ref = lv[-1][1]
        wp, wd = WAVES[name]
        sup = {k: R.periodise(ref["t"][1:], ref[k][1:], ref[k + "_steady"], wp, wd) for k in ("hot", "mean")}
        refw = sup
        for k, w2 in sorted(res.items()):
            if k.startswith(f"femwave|{name}|") and float(k.split("|")[3]) == wp:
                tag = k.split("|")[2] + (" " + k.split("|")[5] if len(k.split("|")) > 5 else "")
                print(f"  FEM wave by time stepping, level {tag} ({w2['n']} unknowns): hot peak {w2['hot'][0]:.4f} swing {w2['hot'][0] - w2['hot'][1]:.4f}")
        print(f"  reference wave = superposition of the finest FEM step response: hot peak {sup['hot'][0]:.4f} swing {sup['hot'][0] - sup['hot'][1]:.4f}")
        print(f"reference = level {lv[-1][0]}; wave period {wp} s duty {wd}: reference peak/swing hot {refw['hot'][0]:.4f}/{refw['hot'][0] - refw['hot'][1]:.4f}, mean {refw['mean'][0]:.4f}/{refw['mean'][0] - refw['mean'][1]:.4f} K/W")
        print("model cell | steady err% (hot, mean) | t63 err% (hot, mean) | early z err% at " + " ".join(f"{t:g}s" for t in TIMES[:4]) + " (hot) | wave peak err%, swing err% (hot)")
        for key, v in sorted(res.items()):
            if not (key.startswith(f"prog|{name}|") or key.startswith(f"progold|{name}|")) or "error" in v:
                if key.startswith(f"prog|{name}|") and "error" in v:
                    print(f"{key.split('|')[2]:>8} {key.split('|')[3]:>4} | refused: {v['error'][:80]}")
                continue
            tag, _, model, cell = key.split("|")
            if tag == "progold":
                model = "old-" + model
            e = lambda x, r: 100 * (x / r - 1)                           # noqa: E731
            early = [e(at(v["t"], v["z"], t), at(ref["t"], ref["hot"], t)) for t in TIMES[:4]]
            pk, vl = R.periodise(v["t"], v["z"], v["rth"], wp, wd)
            row = {"steady_hot": e(v["rth"], ref["hot_steady"]), "steady_mean": e(v["rth"], ref["mean_steady"]), "t63_hot": e(v["t63"], ref["hot_t63"]),
                   "t63_mean": e(v["t63"], ref["mean_t63"]), "early": early, "peak": e(pk, refw["hot"][0]), "swing": e(pk - vl, refw["hot"][0] - refw["hot"][1])}
            rows[f"{name}|{model}|{cell}"] = row
            print(f"{model:>11} {cell:>4} | {row['steady_hot']:+6.2f} {row['steady_mean']:+6.2f} | {row['t63_hot']:+6.2f} {row['t63_mean']:+6.2f} | " + " ".join(f"{x:+6.2f}" for x in early)
                  + f" | {row['peak']:+6.2f} {row['swing']:+6.2f}")
    if "--json" in sys.argv:
        json.dump(rows, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)


if __name__ == "__main__":
    main()
