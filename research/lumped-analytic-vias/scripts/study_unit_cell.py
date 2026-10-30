#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_unit_cell.py
@brief Simple board 1: the periodic unit cell of a via lattice (a p x p board, full copper on every layer, a source over the whole top, one via at the centre, insulated edges).
@details Question: how wrong are the Lumped and Analytic models in the via effect E = T_max(no via) - T_max(via) when ONE effect is present, the constriction of the heat that
         converges on the barrel? In this board there is no lateral gradient between cells (the lattice is periodic), no heater footprint, no ring or tile structure to speak of
         (Lumped: one ring, ring 0 is the whole board; Analytic: a few tiles), no neighbour interaction other than the lattice itself. The reference is the layered fine-grid solver
         at 1/16 mm with the barrel drawn by area (`sheets2d`), whose via has the target radius 0.78 r_v by construction; the 3D solver with the barrel drawn (`layered3d`)
         is run on a subset to show the floor of the layered idealisation. Sweep: layers (2, 4, 6), drill (0.2, 0.3, 0.6, 1.0 mm), pitch (2, 3, 4, 6, 8 mm), open and copper fill.
         Variants: the program (`L_prog`, `A_prog`), the constriction patches and the FVM at 0.5 mm.
Usage: python research/lumped-analytic-vias/scripts/study_unit_cell.py [--quick] [--procs N]   (from the repository root; writes out/unit_cell.json)
"""

import argparse
import json
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import harness as hz                                                         # noqa: E402
import program_cases as pc                                                   # noqa: E402

NAMES = ["FVM", "FVM_fix", "L_prog", "L_ring", "L_grp0", "L_grp", "A_prog", "A_on", "A_bil", "A_fin"]


def run_case(task):
    """!
    @brief One case of the sweep: reference and the error of every variant.
    @param task (layers, dia, pitch, fill).
    @return dict with the task, E_ref, E_3d (None when not computed) and the errors in percent.
    """
    layers, dia, pitch, fill = task
    pc.load_libraries()
    prob = pc.unit_cell_board(pitch, dia, fill, layers=layers)
    e_ref, _, _ = hz.reference_uniform(prob, 1.0 / 16)
    errs = hz.errors(prob, e_ref, 0.5, NAMES)
    return {"task": list(task), "E_ref": e_ref, "err": errs}


def main():
    """!
    @brief Run the sweep and print the tables.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--procs", type=int, default=6)
    args = ap.parse_args()
    layers = [2, 4] if args.quick else [2, 4, 6]
    dias = [0.3, 0.6] if args.quick else [0.2, 0.3, 0.6, 1.0]
    pitches = [3, 4, 8] if args.quick else [2, 3, 4, 6, 8]
    tasks = [(l, d, p, f) for l in layers for f in (0.0, 385.0) for d in dias for p in pitches if d < 0.6 * p]
    with mp.Pool(args.procs) as pool:
        rows = pool.map(run_case, tasks, chunksize=1)
    os.makedirs(os.path.join(os.path.dirname(HERE), "out"), exist_ok=True)
    json.dump(rows, open(os.path.join(os.path.dirname(HERE), "out", "unit_cell.json"), "w"), indent=1)
    print("## Unit cell: error of the via effect against the fine-grid layered reference (percent of E)\n")
    print("| layers | fill | drill mm | pitch mm | E_ref K | " + " | ".join(NAMES) + " |")
    print("| --: | :-- | --: | --: | --: |" + " --: |" * len(NAMES))
    for r in rows:
        l, d, p, f = r["task"]
        print(f"| {l} | {'Cu' if f else 'open'} | {d} | {p} | {r['E_ref']:.2f} | " + " | ".join(f"{r['err'][n]:+.1f}" for n in NAMES) + " |")
    print("\n## Summary (mean and maximum of the absolute error, percent)\n")
    print("| variant | mean | max |")
    print("| :-- | --: | --: |")
    for n in NAMES:
        v = [abs(r["err"][n]) for r in rows]
        print(f"| {n} | {sum(v) / len(v):.1f} | {max(v):.1f} |")


if __name__ == "__main__":
    main()
