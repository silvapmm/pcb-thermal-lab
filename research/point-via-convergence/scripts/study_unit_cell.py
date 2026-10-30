#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_unit_cell.py
@brief How well every via treatment reproduces the effect of a via as the cell shrinks: the periodic unit cell of a via lattice, FVM of the program on copies.
@details Question: which treatment makes the via effect converge with the cell? The board is a p x p mm, four-plane board with insulated edges (so it is a mirror-periodic
         lattice of vias), a source of the same size over the whole top, h_bottom 200 W/m2K, one via. The via effect is E = T_max(no via) - T_max(via) (K). Reference: the
         independent fine-grid layered solver (`sheets2d`, 1/32 mm cells, the barrel spread over its disc), checked against the 3D solver with the barrel drawn at its real size
         (`layered3d`, 1/32 mm) on the cases marked in the output. The via sits on a cell corner, on a cell edge or at a cell centre (the position inside the cell matters for a
         point feature). Treatments are the in-memory patches of `lib/program_patch.py`; "program" is the FVM of develop unchanged.
         Output: tables of the error of E against the reference (percent of E), and `out/unit_cell.json` for make_figures.py.
Usage: python research/point-via-convergence/scripts/study_unit_cell.py [--quick]   (from the repository root; about 10 minutes with 6 processes)
"""

import argparse
import itertools
import json
import math
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
sys.path.insert(0, LIB)

import numpy as np                                                          # noqa: E402

import program_cases as pc                                                  # noqa: E402
import program_patch as pp                                                  # noqa: E402
import resolved_boards as rb                                                # noqa: E402

CELLS = [1.0, 0.5, 0.25, 0.125, 0.0625]
POSITIONS = {"corner": (0.0, 0.0), "edge": (0.5, 0.0), "centre": (0.5, 0.5)}      # offset of the via from the centre of the board, in cells
ETA = math.exp(-0.25)                                                       # radius of the uniform sink density over the disc, in units of the via radius
TREATMENTS = ["program", "peaceman", "area", "tuned", "mw_point", "mw_ring", "mw_area", "mw_tuned", "mw_area@eta", "mw_tuned@eta"]
POWER = 0.01
LAYERS = 4


def cases(quick):
    """!
    @brief The (pitch mm, diameter mm, fill W/mK) cases.
    @param quick True for a short list.
    @return list of tuples.
    """
    if quick:
        return [(4.0, 0.3, 0.0), (4.0, 0.3, 385.0)]
    out = [(4.0, d, f) for d in (0.2, 0.3, 0.5, 1.0) for f in (0.0, 385.0)]
    out += [(p, 0.3, f) for p in (2.0, 8.0) for f in (0.0, 385.0)]
    return out


def reference(pitch, dia, fill, pos_cells, dx_cell, dx_ref=1.0 / 32):
    """!
    @brief Via effect by the independent fine-grid solver for a via at the given position.
    @param pitch Board side in mm.
    @param dia Via diameter in mm.
    @param fill Fill conductivity.
    @param pos_cells Offset from the centre in units of the program's cell.
    @param dx_cell The program's cell in mm.
    @param dx_ref Reference cell in mm.
    @return tuple (E, T_no_via) in K.
    """
    off = (pos_cells[0] * dx_cell, pos_cells[1] * dx_cell)
    par = pc.layer_parameters(pc.unit_cell_board(pitch, dia, fill, LAYERS, offset=off))
    x, y = par["xy"][0]
    t_via = rb.full_board_2d(par, dx_ref * 1e-3, [(x, y, 0)], POWER)
    t_no = rb.full_board_2d(par, dx_ref * 1e-3, [], POWER)
    return t_no - t_via, t_no


def program_run(task):
    """!
    @brief Run the program (copy) for one case, position and cell: every treatment's via effect.
    @param task Tuple (pitch, dia, fill, position name, cell mm).
    @return dict with the task and E for every treatment.
    """
    pitch, dia, fill, pname, cell = task
    pc.load_libraries()
    dx_cell = pitch / max(int(round(pitch / cell)), 2)
    off = tuple(v * dx_cell for v in POSITIONS[pname])
    p_via = pc.unit_cell_board(pitch, dia, fill, LAYERS, offset=off)
    p_no = pc.unit_cell_board(pitch, dia, fill, LAYERS, offset=off)
    p_no.vias = []
    p_via.heaters[0].power = p_no.heaters[0].power = POWER
    t_no = pc.max_rise(p_no, "fvm", cell)
    out = {"task": list(task), "dx": dx_cell, "E": {}}
    for tr in TREATMENTS:
        if tr == "program":
            t = pc.max_rise(p_via, "fvm", cell)
        else:
            name, _, tag = tr.partition("@")
            with pp.patched(name, eta=ETA if tag else 1.0):
                t = pc.max_rise(p_via, "fvm", cell)
        out["E"][tr] = t_no - t
    return out


def main():
    """!
    @brief Run the study and print the tables.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--quick", action="store_true", help="two cases only")
    ap.add_argument("--procs", type=int, default=6)
    args = ap.parse_args()
    pc.load_libraries()
    cs = cases(args.quick)
    tasks = [(p, d, f, pn, c) for (p, d, f) in cs for pn in POSITIONS for c in CELLS if p / c >= 2]
    with mp.Pool(args.procs) as pool:
        runs = pool.map(program_run, tasks, chunksize=1)
    refs = {}
    for (p, d, f) in cs:
        for pn in POSITIONS:
            for c in CELLS:
                if p / c >= 2:
                    refs[(p, d, f, pn, c)] = reference(p, d, f, POSITIONS[pn], p / max(int(round(p / c)), 2))
    os.makedirs(os.path.join(os.path.dirname(HERE), "out"), exist_ok=True)
    rows = []
    for r in runs:
        key = tuple(r["task"])
        e_ref, t_no = refs[key]
        rows.append({"task": r["task"], "dx": r["dx"], "E_ref": e_ref, "T_no": t_no, "E": r["E"]})
    json.dump(rows, open(os.path.join(os.path.dirname(HERE), "out", "unit_cell.json"), "w"), indent=1)
    for (p, d, f) in cs:
        print(f"\n### pitch {p} mm, via {d} mm, {'copper fill' if f else 'open barrel'} (via effect E of the reference in K; worst error over the three positions, percent of E)\n")
        print("| treatment | " + " | ".join(f"{c} mm" for c in CELLS if p / c >= 2) + " |")
        print("| :-- |" + " --: |" * len([c for c in CELLS if p / c >= 2]))
        e_refs = [max(x["E_ref"] for x in rows if x["task"][:3] == [p, d, f] and x["task"][4] == c) for c in CELLS if p / c >= 2]
        print("| reference E (K) | " + " | ".join(f"{e:.2f}" for e in e_refs) + " |")
        for tr in TREATMENTS:
            cells = []
            for c in CELLS:
                if p / c < 2:
                    continue
                errs = [100 * (x["E"][tr] / x["E_ref"] - 1) for x in rows if x["task"][:3] == [p, d, f] and x["task"][4] == c]
                cells.append(f"{max(errs, key=abs):+.1f}")
            print(f"| {tr} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
