#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_example_board.py
@brief The example board of the program (100 x 80 mm, 4 layers, 9 vias under U1): maximum temperature and copper-fill gain against the cell, for the via treatments (copies).
@details For each cell: T_max with open vias, with copper-filled vias and without vias, for the program and for the treatments, in the FVM and the FDM. The cells 0.125 mm and
         finer are left out for the whole board (800 x 640 x 4 cells); the local board of `study_array_board.py` covers them. Writes `out/example_board_<model>.json`.
Usage: python research/point-via-convergence/scripts/study_example_board.py [--model fvm|fdm] [--fine]   (from the repository root; about 6 minutes)
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

ETA = math.exp(-0.25)
TREATMENTS = ["program", "peaceman", "area", "mw_tuned", "mw_area@eta", "mw_tuned@eta", "mw_disc@eta"]


def example_with(fill_k=None):
    """!
    @brief The example board with a fill on every via, or without vias (fill_k None).
    @param fill_k Fill conductivity in W/mK, or None for no vias.
    @return Problem.
    """
    p = pc.example_board()
    if fill_k is None:
        p.vias = []
    else:
        for v in p.vias:
            v.filled, v.fill_k = False, fill_k
    return p


def main():
    """!
    @brief Run the study and print the table.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--model", default="fvm")
    ap.add_argument("--fine", action="store_true", help="add the 0.125 mm cell (about 2 million unknowns)")
    args = ap.parse_args()
    pc.load_libraries()
    cells = [2.0, 1.0, 0.5, 0.25] + ([0.125] if args.fine else [])
    res = {"model": args.model, "cells": cells, "no_via": {}, "rows": {}}
    print(f"## Example board, {args.model.upper()}: open T_max (degC) / copper-fill gain (K)\n")
    print("| treatment | " + " | ".join(f"{c} mm" for c in cells) + " |")
    print("| :-- |" + " --: |" * len(cells))
    nv = example_with(None)
    res["no_via"] = {c: pc.max_rise(nv, args.model, c) + nv.board.ambient for c in cells}
    print("| no vias | " + " | ".join(f"{res['no_via'][c]:.2f}" for c in cells) + " |", flush=True)
    for tr in TREATMENTS:
        row = []
        for c in cells:
            vals = []
            for fk in (0.0, 385.0):
                p = example_with(fk)
                if tr == "program":
                    vals.append(pc.max_rise(p, args.model, c) + p.board.ambient)
                else:
                    name, _, tag = tr.partition("@")
                    with pp.patched(name, eta=ETA if tag else 1.0):
                        vals.append(pc.max_rise(p, args.model, c) + p.board.ambient)
            row.append((vals[0], vals[1] - vals[0]))
        res["rows"][tr] = row
        print(f"| {tr} | " + " | ".join(f"{o:.2f} / {g:+.2f}" for o, g in row) + " |", flush=True)
    os.makedirs(os.path.join(os.path.dirname(HERE), "out"), exist_ok=True)
    json.dump(res, open(os.path.join(os.path.dirname(HERE), "out", f"example_board_{args.model}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
