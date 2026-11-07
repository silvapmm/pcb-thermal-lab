#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_down_board_effect.py
@brief How far does the hottest rise of a board move if the face turned down used a 1/5 law instead of 0.27 Ra^(1/4)? 17 harness boards at computed h, the example board, the frozen records.
@details The program is not edited: `convection.h_natural_horizontal` is replaced in memory by lib/down_laws.use_down for the duration of one run. FVM, cell 2 mm, h_mode "computed",
         orientation "horizontal" (layer 1 looks up, the last layer looks down), emissivity as the board has it.
         Part 1: the 17 boards of the regression harness as they are (the frozen records: manual coefficients) with the patched function counting its calls; a count of zero means
         no frozen record can move. Part 2: the same 17 boards at computed h, the percent change of the hottest rise for each candidate law, with and without radiation.
         Part 3: the example board (computed h, horizontal; vertical for the check that nothing moves; power x0.5 and x2).
Usage: .venv/bin/python research/face-down-convection/scripts/study_down_board_effect.py   (a few minutes; one process, below 1.5 GB)
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(ROOT, "tests", "regression"))
sys.path.insert(0, ROOT)

import down_laws as D  # noqa: E402
import regress_boards  # noqa: E402
from pcbthermal import api  # noqa: E402
from pcbthermal import model  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
LAWS = {"program": D.program_down, "incropera": D.incropera7, "gl_mean": D.gl_mean, "vdi": D.vdi}
EXAMPLE = os.path.join(ROOT, "examples", "example_board.pcbt.json")


def run(problem, law, mode=None, orientation=None, eps0=False, scale=1.0, cell=2.0):
    """!
    @brief One FVM run with one lower-face law.
    @param problem Problem (modified).
    @param law Key of LAWS.
    @param mode h_mode to set, or None to keep the board's.
    @param orientation Orientation to set, or None to keep the board's.
    @param eps0 True: emissivities zero (convection only).
    @param scale Factor on every heater power.
    @param cell Cell size in mm.
    @return dict with rise (K), the face coefficients (W/m2K, convection plus radiation) and the number of calls of the horizontal law.
    """
    b = problem.board
    if mode:
        b.h_mode = mode
    if orientation:
        b.orientation = orientation
    if eps0:
        b.emissivity_top = b.emissivity_bottom = 0.0
    for h in problem.heaters:
        h.power *= scale
    with D.use_down(LAWS[law]) as calls:
        sim = api.simulate(problem, api.SolverOptions(models=("fvm",), cell_mm=cell))
    r = sim.results["fvm"]
    hh = sim.h_used.get("fvm")
    return {"rise": float(r.delta_t), "t_max": float(r.t_max), "h": None if hh is None else [float(x) for x in hh[:2]], "calls": calls["n"]}


def main():
    """!
    @brief Run the three parts and print the tables.
    @return None.
    """
    t0 = time.time()
    out = {"frozen": [], "boards": [], "example": []}
    print("Part 1: the 17 boards as the frozen records run them (calls of the horizontal law)")
    for name in regress_boards.board_names():
        p = regress_boards.build(name)
        r = run(p, "incropera")
        out["frozen"].append({"board": name, "h_mode": p.board.h_mode, "calls": r["calls"]})
        print(f"  {name:22s} h_mode {p.board.h_mode:8s} calls {r['calls']}", flush=True)
    print("\nPart 2: 17 boards at computed h, percent change of the hottest rise against the program")
    print("board                  rise K   Incropera  GLmean   VDI   | no radiation: Incropera GLmean VDI")
    for name in regress_boards.board_names():
        row = {"board": name}
        for tag, kw in (("rad", {}), ("conv", {"eps0": True})):
            for lv in LAWS:
                try:
                    row[f"{tag}|{lv}"] = run(regress_boards.build(name), lv, mode="computed", orientation="horizontal", **kw)
                except Exception as exc:                            # a board the program refuses is recorded, not hidden
                    row[f"{tag}|{lv}"] = {"error": str(exc)[:80]}
        out["boards"].append(row)
        base = row["rad|program"].get("rise")
        cb = row["conv|program"].get("rise")

        def pct(key, ref):
            v = row[key].get("rise")
            return "  n/a" if v is None or ref is None else f"{100 * (v / ref - 1):+5.1f}"

        print(f"{name:22s} {base if base is None else round(base, 2)!s:>7}   " + "  ".join(pct(f"rad|{lv}", base) for lv in list(LAWS)[1:]) + "   | " + "  ".join(pct(f"conv|{lv}", cb) for lv in list(LAWS)[1:]), flush=True)
    print("\nPart 3: example board, computed h")
    for tag, kw in (("horizontal", {"orientation": "horizontal"}), ("vertical", {"orientation": "vertical"}),
                    ("horizontal x0.5", {"orientation": "horizontal", "scale": 0.5}), ("horizontal x2", {"orientation": "horizontal", "scale": 2.0})):
        row = {"case": tag}
        for lv in LAWS:
            p = model.load_problem(EXAMPLE) if hasattr(model, "load_problem") else None
            if p is None:
                from pcbthermal import project
                p = project.load(EXAMPLE)
            row[lv] = run(p, lv, mode="computed", **kw)
        out["example"].append(row)
        b = row["program"]
        print(f"  {tag:16s} program rise {b['rise']:.2f} K (calls {b['calls']}), bottom h {b['h'][1]:.2f}; change % " +
              "  ".join(f"{lv} {100 * (row[lv]['rise'] / b['rise'] - 1):+.2f}" for lv in list(LAWS)[1:]) +
              f"; h_bottom " + " ".join(f"{row[lv]['h'][1]:.2f}" for lv in LAWS), flush=True)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "down_board_effect.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"{time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
