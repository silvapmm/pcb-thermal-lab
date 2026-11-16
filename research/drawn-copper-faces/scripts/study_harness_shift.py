#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_harness_shift.py
@brief Question (c): which records of the frozen-number boards would move if the FVM and FDM read drawn zones as an import (exact fill, flow-based faces), and by how much?
@details Runs the 17 boards of `tests/regression/regress_boards.py` through `regress_harness.run_one` (the harness of the frozen numbers, steady records, FVM and FDM, cells 2, 1 and
         0.5 mm) twice in one process: with the program as it is and inside `lib/patched.use('faces')` (a COPY of the networks, the program is not edited). Prints, per board, model and
         cell, the largest change of the hottest value, the mean and every part, in K and in per cent of the rise, plus the seconds of both runs. Cache `out/harness_skip.json`.
         Run: `.venv/bin/python research/drawn-copper-faces/scripts/study_harness_shift.py [--models fvm,fdm] [--cells 2,1,0.5]`.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, ROOT)

OUT = os.path.join(HERE, "..", "out", "harness_skip.json")


def values(rec):
    """!
    @brief The temperatures of a record that the comparison reads.
    @param rec Record of `run_one`.
    @return dict name -> value.
    """
    v = {"t_max": rec["t_max"], "t_mean": rec["t_mean"]}
    for p in rec.get("parts") or []:
        v[f"{p['name']}:t_max"] = p["t_max"]
        v[f"{p['name']}:t_mean"] = p["t_mean"]
    return v


def main():
    """!
    @brief Run and print.
    @return None.
    """
    import regress_boards as B
    import regress_harness as H
    import patched as P
    models = ("fvm", "fdm")
    cells = (2.0, 1.0, 0.5)
    for i, a in enumerate(sys.argv):
        if a == "--models":
            models = tuple(sys.argv[i + 1].split(","))
        if a == "--cells":
            cells = tuple(float(x) for x in sys.argv[i + 1].split(","))
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    for name in B.board_names():
        for model in models:
            for cell in cells:
                key = f"{name}|{model}|{cell:g}"
                if key not in res:
                    prob = B.build(name)
                    base = H.run_one(prob, name, model, cell)
                    with P.use("faces"):
                        new = H.run_one(prob, name, model, cell)
                    res[key] = {"base": {"status": base["status"], "seconds": base.get("seconds"), "values": values(base) if base["status"] == "ok" else None},
                                "new": {"status": new["status"], "seconds": new.get("seconds"), "values": values(new) if new["status"] == "ok" else None,
                                        "balance": new.get("balance_error"), "warnings": new.get("warnings")}}
                    json.dump(res, open(OUT, "w"), indent=1)
                r = res[key]
                if r["base"]["values"] is None or r["new"]["values"] is None:
                    print(f"{key:40s} {r['base']['status']} / {r['new']['status']}")
                    continue
                b, n = r["base"]["values"], r["new"]["values"]
                worst = max(b, key=lambda k: abs(n[k] - b[k]))
                d = {k: n[k] - b[k] for k in b}
                big = max(abs(x) for x in d.values())
                print(f"{key:40s} max shift {big:+9.5f} K ({worst}), t_max {d['t_max']:+9.5f} K, t {r['base']['seconds']:.2f} -> {r['new']['seconds']:.2f} s", flush=True)


if __name__ == "__main__":
    main()
