#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_row_lone.py
@brief A lone via and a row of five vias next to a source on a 16 mm two-plane board: the via effect against the cell, program and treatments (copies), FVM and FDM.
@details Board: 16 x 16 mm, two copper planes, 0.5 W in a 3 mm square source in the middle, h 10 / 200 W/m2K, insulated edges; vias of 0.3 and 0.6 mm (open and copper-filled) in
         a row to the right of the source starting 1 mm from its edge (pitch 1 mm; n = 1 is the lone via). The via effect E = T_max(no via) - T_max(via) is compared with the
         independent fine-grid layered solver at 1/32 mm (`sheets2d`; the source and the vias lie on its cell edges).
Usage: python research/point-via-convergence/scripts/study_row_lone.py [--model fvm|fdm]   (from the repository root; about 8 minutes)
"""

import argparse
import json
import math
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import program_cases as pc                                                  # noqa: E402
import program_patch as pp                                                  # noqa: E402
import resolved_boards as rb                                                # noqa: E402

CELLS = [1.0, 0.5, 0.25, 0.125, 0.0625]
ETA = math.exp(-0.25)
TREATMENTS = ["program", "peaceman", "mw_tuned", "mw_area@eta", "mw_tuned@eta"]
SIDE, SOURCE, GAP, PITCH, POWER = 16.0, 3.0, 1.0, 1.0, 0.5


def reference(n, dia, fill, dx_ref=1.0 / 32):
    """!
    @brief Via effect by the independent fine-grid solver.
    @param n Vias in the row.
    @param dia Diameter in mm.
    @param fill Fill conductivity.
    @param dx_ref Reference cell in mm.
    @return float E in K.
    """
    p = pc.row_board(n, PITCH, dia, fill, SIDE, 2, SOURCE, GAP)
    par = pc.layer_parameters(p)
    c = SIDE / 2 * 1e-3
    rect = (c - SOURCE / 2 * 1e-3, c - SOURCE / 2 * 1e-3, c + SOURCE / 2 * 1e-3, c + SOURCE / 2 * 1e-3)
    vias = [(x, y, k) for k, (x, y) in enumerate(par["xy"])]
    t_via = rb.full_board_2d(par, dx_ref * 1e-3, vias, POWER, rect)
    t_no = rb.full_board_2d(par, dx_ref * 1e-3, [], POWER, rect)
    return t_no - t_via


def program_run(task):
    """!
    @brief Via effect of every treatment for one case and cell.
    @param task (model, n, dia, fill, cell).
    @return dict.
    """
    model, n, dia, fill, cell = task
    pc.load_libraries()
    p_no = pc.row_board(n, PITCH, dia, fill, SIDE, 2, SOURCE, GAP, none=True)
    p_via = pc.row_board(n, PITCH, dia, fill, SIDE, 2, SOURCE, GAP)
    t_no = pc.max_rise(p_no, model, cell)
    out = {}
    for tr in TREATMENTS:
        if tr == "program":
            t = pc.max_rise(p_via, model, cell)
        else:
            name, _, tag = tr.partition("@")
            with pp.patched(name, eta=ETA if tag else 1.0):
                t = pc.max_rise(p_via, model, cell)
        out[tr] = t_no - t
    return {"task": list(task), "E": out}


def main():
    """!
    @brief Run the study and print the tables.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--model", default="fvm")
    ap.add_argument("--procs", type=int, default=6)
    args = ap.parse_args()
    cases = [(n, d, f) for n in (1, 5) for d in (0.3, 0.6) for f in (0.0, 385.0)]
    tasks = [(args.model, n, d, f, c) for (n, d, f) in cases for c in CELLS]
    with mp.Pool(args.procs) as pool:
        runs = pool.map(program_run, tasks, chunksize=1)
    refs = {c: reference(*c) for c in cases}
    rows = [{"task": r["task"], "E": r["E"], "E_ref": refs[tuple(r["task"][1:4])]} for r in runs]
    os.makedirs(os.path.join(os.path.dirname(HERE), "out"), exist_ok=True)
    json.dump(rows, open(os.path.join(os.path.dirname(HERE), "out", f"row_lone_{args.model}.json"), "w"), indent=1)
    print(f"## {args.model.upper()}: error of the via effect against the fine-grid reference (percent of E)\n")
    print("| case | E_ref (K) | treatment | " + " | ".join(f"{c} mm" for c in CELLS) + " |")
    print("| :-- | --: | :-- |" + " --: |" * len(CELLS))
    for (n, d, f) in cases:
        sel = {r["task"][4]: r for r in rows if tuple(r["task"][1:4]) == (n, d, f)}
        for tr in TREATMENTS:
            lab = f"{n} via{'s' if n > 1 else ''}, {d} mm, {'Cu fill' if f else 'open'}" if tr == TREATMENTS[0] else ""
            e = f"{refs[(n, d, f)]:.3f}" if tr == TREATMENTS[0] else ""
            print(f"| {lab} | {e} | {tr} | " + " | ".join(f"{100 * (sel[c]['E'][tr] / refs[(n, d, f)] - 1):+.1f}" for c in CELLS) + " |")


if __name__ == "__main__":
    main()
