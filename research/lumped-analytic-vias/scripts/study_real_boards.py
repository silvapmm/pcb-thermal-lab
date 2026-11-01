#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_real_boards.py
@brief The example board of the program (100 x 80 mm, four layers, two parts, a heatsink, computed film coefficients off) with its 9 vias and with denser arrays under U1.
@details Boards are what the maintainer works with: no symmetry, several parts, a heatsink, partial copper. The reference is the FVM with the corrected via treatment of
         research/point-via-convergence (`mw_disc@eta`) on a 0.25 mm cell, which is within 0.4 to 1 % of the fine-grid layered reference on the simple boards of this folder
         (`study_arrays.py`, FVM_fix); it is NOT independent of the layered idealisation, it is the best the program has. The via effect E = T_max(no vias) - T_max(vias) is compared
         for the program and the patches, with open barrels and copper fill, for the 3.5 mm array of the example and for 7 x 7 and 5 x 5 arrays at 1.2 and 1.0 mm replacing it.
Usage: python research/lumped-analytic-vias/scripts/study_real_boards.py [--ref-cell 0.25]   (from the repository root; about 10 minutes)
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import harness as hz                                                         # noqa: E402
import program_cases as pc                                                   # noqa: E402
from pcbthermal import project                                              # noqa: E402

NAMES = ["FVM", "L_prog", "L_ring", "L_grp0", "L_grp", "A_prog", "A_on", "A_bil", "A_fin"]


def example(fill_k, n, pitch):
    """!
    @brief The example board with its vias replaced by an n x n array of the given pitch centred on the same point.
    @param fill_k Fill conductivity of the vias in W/mK.
    @param n Vias per side (0 keeps the original 9 at 3.5 mm).
    @param pitch Pitch in mm.
    @return Problem.
    """
    root = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    prob = project.load_project(os.path.join(root, "examples", "example_board.pcbt.json")).problem
    if n:
        d = prob.vias[0].diameter * 1e3
        cx = sum(v.x for v in prob.vias) / len(prob.vias) * 1e3
        cy = sum(v.y for v in prob.vias) / len(prob.vias) * 1e3
        prob.vias = []
        for i in range(n):
            for j in range(n):
                prob.add_via(cx + (i - (n - 1) / 2) * pitch, cy + (j - (n - 1) / 2) * pitch, d)
    for v in prob.vias:
        v.fill_k = fill_k
    return prob


def main():
    """!
    @brief Run the boards and print the table.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--ref-cell", type=float, default=0.25)
    args = ap.parse_args()
    pc.load_libraries()
    boards = [("example, 9 vias at 3.5 mm", 0, 3.5), ("5 x 5 at 1.2 mm", 5, 1.2), ("7 x 7 at 1.0 mm", 7, 1.0)]
    rows = []
    for label, n, pitch in boards:
        for fill in (0.0, 385.0):
            prob = example(fill, n, pitch)
            q0 = hz.no_vias(prob)
            e_ref = hz.effect(prob, "fvm", hz.VARIANTS["FVM_fix"][1], args.ref_cell, q0)
            e = {k: hz.effect(prob, hz.VARIANTS[k][0], hz.VARIANTS[k][1], 0.5 if k != "FVM" else 1.0, q0) for k in NAMES}
            rows.append({"board": label, "fill": fill, "E_ref": e_ref, "E": e})
            print(f"{label} fill {fill}: E_ref {e_ref:.3f} K  " + "  ".join(f"{k} {100 * (e[k] / e_ref - 1):+.1f}%" for k in NAMES), flush=True)
    os.makedirs(os.path.join(os.path.dirname(HERE), "out"), exist_ok=True)
    json.dump(rows, open(os.path.join(os.path.dirname(HERE), "out", "real_boards.json"), "w"), indent=1)
    print("\n| board | fill | E_ref K | " + " | ".join(NAMES) + " |\n| :-- | :-- | --: |" + " --: |" * len(NAMES))
    for r in rows:
        print(f"| {r['board']} | {'Cu' if r['fill'] else 'open'} | {r['E_ref']:.3f} | " + " | ".join(f"{100 * (r['E'][k] / r['E_ref'] - 1):+.1f}" for k in NAMES) + " |")
    print("\n| board | gain K (ref) | " + " | ".join(NAMES) + " |\n| :-- | --: |" + " --: |" * len(NAMES))
    for i in range(0, len(rows), 2):
        o, c = rows[i], rows[i + 1]
        g = c["E_ref"] - o["E_ref"]
        print(f"| {o['board']} | {g:.3f} | " + " | ".join(f"{100 * (((c['E'][k] - o['E'][k]) / g) - 1):+.1f}" for k in NAMES) + " |")


if __name__ == "__main__":
    main()
