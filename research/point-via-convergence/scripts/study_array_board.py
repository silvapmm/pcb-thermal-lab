#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_array_board.py
@brief The copper-fill gain of the 3 x 3 via-array board of research/via-fill against the cell size, for every via treatment, in the FVM and the FDM of the program (copies).
@details Board: 21 x 21 mm, four copper planes, 3 x 3 vias of 0.3 mm at 3.5 mm pitch under a 10 x 10 mm source of 2 W, h 10 / 200 W/m2K, insulated edges.
         References: the fine-grid layered solver (`sheets2d`, the idealisation of the program resolved) and the 3D solver with the barrels drawn (`layered3d`, 1/12 mm and 0.1 mm).
         Prints the open-barrel rise and the gain (copper fill minus open) per treatment and cell; writes `out/array_board.json`.
Usage: python research/point-via-convergence/scripts/study_array_board.py [--model fvm|fdm] [--solid3d]   (from the repository root; about 6 minutes)
"""

import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import program_cases as pc                                                  # noqa: E402
import program_patch as pp                                                  # noqa: E402
import resolved_boards as rb                                                # noqa: E402

CELLS = [1.0, 0.5, 0.25, 0.125, 0.0625]
ETA = math.exp(-0.25)                                                       # radius of the uniform sink density over the disc, in units of the via radius
TREATMENTS = ["program", "peaceman", "area", "tuned", "mw_point", "mw_ring", "mw_area", "mw_tuned", "mw_area@eta", "mw_tuned@eta", "mw_disc@eta"]


def run(model, tr, cell, fill):
    """!
    @brief Maximum rise of the array board for a model, treatment, cell and fill.
    @param model fvm or fdm.
    @param tr Treatment name or "program".
    @param cell Cell in mm.
    @param fill Fill conductivity.
    @return float Rise in K.
    """
    p = pc.array_board(fill)
    if tr == "program":
        return pc.max_rise(p, model, cell)
    name, _, tag = tr.partition("@")
    with pp.patched(name, eta=ETA if tag else 1.0):
        return pc.max_rise(p, model, cell)


def sweep(model):
    """!
    @brief Gain against a fine series of cells (21 mm divided into n cells) for the program and the recommended treatment: does the treatment change smoothly across the regimes?
    @param model fvm or fdm.
    @return list of (cell mm, program gain, mean-coupling area gain, mean-coupling centred-disc gain).
    """
    rows = []
    for n in (21, 28, 35, 42, 56, 70, 84, 105, 126, 168, 210, 252, 336):
        c = 21.0 / n
        g = [run(model, tr, c, 385.0) - run(model, tr, c, 0.0) for tr in ("program", "mw_area@eta", "mw_disc@eta")]
        rows.append((c, g[0], g[1], g[2]))
        print(f"* {c:.4f} mm: program {g[0]:+.2f}, mw_area@eta {g[1]:+.2f}, mw_disc@eta {g[2]:+.2f}", flush=True)
    return rows


def main():
    """!
    @brief Run the study and print the tables.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--model", default="fvm")
    ap.add_argument("--sweep", action="store_true", help="only the fine series of cells")
    ap.add_argument("--solid3d", action="store_true", help="also run the 3D solid of the program at 1, 0.5 and 0.25 mm")
    args = ap.parse_args()
    pc.load_libraries()
    if args.sweep:
        rows = sweep(args.model)
        os.makedirs(os.path.join(os.path.dirname(HERE), "out"), exist_ok=True)
        json.dump(rows, open(os.path.join(os.path.dirname(HERE), "out", f"array_sweep_{args.model}.json"), "w"))
        return
    out = {"model": args.model, "cells": CELLS, "ref": {}, "rows": {}}
    print(f"## 3 x 3 via-array board, {args.model.upper()} of the program\n")
    print("References (open rise, copper-fill gain, K):\n")
    for dx in (1 / 16, 1 / 32):
        o = rb.array_quadrant(pc.layer_parameters(pc.array_board(0.0)), dx * 1e-3, 2.0, 5e-3)
        c = rb.array_quadrant(pc.layer_parameters(pc.array_board(385.0)), dx * 1e-3, 2.0, 5e-3)
        out["ref"][f"2d_{dx:.4f}"] = [o, c - o]
        print(f"* fine-grid layered solver, {dx:.4f} mm: open {o:.2f}, gain {c - o:+.2f}")
    for dx in (0.1, 1 / 12):
        o = rb.array_3d(pc.layer_parameters(pc.array_board(0.0)), dx * 1e-3, 2.0, 5e-3)
        c = rb.array_3d(pc.layer_parameters(pc.array_board(385.0)), dx * 1e-3, 2.0, 5e-3)
        out["ref"][f"3d_{dx:.4f}"] = [o, c - o]
        print(f"* 3D solver, barrels drawn, {dx:.4f} mm: open {o:.2f}, gain {c - o:+.2f}")
    print("\n| treatment | " + " | ".join(f"{c} mm" for c in CELLS) + " |")
    print("| :-- |" + " --: |" * len(CELLS))
    for tr in TREATMENTS:
        row = []
        for c in CELLS:
            o, f = run(args.model, tr, c, 0.0), run(args.model, tr, c, 385.0)
            row.append((o, f - o))
        out["rows"][tr] = row
        print(f"| {tr} | " + " | ".join(f"{o:.2f} / {g:+.2f}" for o, g in row) + " |", flush=True)
    if args.solid3d:
        print("\n3D solid of the program (open rise / gain):")
        row = []
        for c in (1.0, 0.5, 0.25):
            o, f = run("solid3d", "program", c, 0.0), run("solid3d", "program", c, 385.0)
            row.append((o, f - o))
            print(f"* {c} mm: {o:.2f} / {f - o:+.2f}", flush=True)
        out["solid3d"] = row
    os.makedirs(os.path.join(os.path.dirname(HERE), "out"), exist_ok=True)
    json.dump(out, open(os.path.join(os.path.dirname(HERE), "out", f"array_board_{args.model}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
