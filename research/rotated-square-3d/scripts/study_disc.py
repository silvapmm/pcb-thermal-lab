#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_disc.py
@brief Against an independent axisymmetric reference, how far are the program's 3D solid and its cut-cell copy on a round board, where every edge cell is cut?
@details A round board of 40 mm (two copper planes, full copper, 2 W in a round part of 3 mm radius at the centre) is axisymmetric: the 3D problem
         of the real slabs reduces to rings times slabs (`lib/axisym3d.py`, its own finite volumes, 4000 rings, checked against 2000). The program
         and the copies run on a 128-sided polygon of the same area. The edge coefficient goes from 10 to 5000 W/m2K and the cell from 1 to 0.25 mm.
         Prints the rise of the top copper at the centre of the reference and of each model, and the error as a percentage of the reference rise.
         A second table gives the FVM and the FDM (one node per layer) against the axisymmetric reduction of the layered model
         (`axisym3d.solve_layered_disc`), the reference of their own idealisation; the two idealisations differ at high edge coefficients by physics, not by the grid.
Usage: .venv/bin/python research/rotated-square-3d/scripts/study_disc.py   (from the repository root)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import axisym3d   # noqa: E402
import rotsq      # noqa: E402
import runs       # noqa: E402


def reference_rise(p, part_r_mm, diameter_mm, n_rings):
    """!
    @brief Rise of the top copper at the centre from the axisymmetric solver, for the slabs and films of a Problem.
    @param p Problem built by `rotsq.disc_board`.
    @param part_r_mm Part radius in mm.
    @param diameter_mm Board diameter in mm.
    @param n_rings Rings.
    @return Tuple (rise in K, result dict).
    """
    b = p.board
    res = axisym3d.solve_disc(diameter_mm / 2000.0, part_r_mm / 1000.0, p.heaters[0].power, axisym3d.slabs_of(p), b.h_top, b.h_bottom, b.h_side, n_rings)
    return res["t_top_max"], res


def main():
    """!
    @brief Run the sweep and print the table.
    @return None.
    """
    d, a = 40.0, 3.0
    out = {}
    cells = (1.0, 0.5, 0.25)
    print("| h_side | reference rise (K) | " + " | ".join(f"program {c:g} mm | cut-cell {c:g} mm" for c in cells) + " |")
    print("| --: | --: | " + " | ".join("--: | --:" for _ in cells) + " |")
    for hs in (10.0, 100.0, 1000.0, 5000.0):
        p = rotsq.disc_board(d, a, hs)
        amb = p.board.ambient
        ref, _ = reference_rise(p, a, d, 4000)
        ref2, _ = reference_rise(p, a, d, 2000)
        row = []
        for c in cells:
            for m in ("solid3d", "cutcell"):
                t = runs.tmax(p, m, c) - amb
                out[f"{hs:g}|{c:g}|{m}"] = t
                row.append(f"{t:.2f} ({100 * (t - ref) / ref:+.1f} %)")
        out[f"{hs:g}|ref"] = ref
        print(f"| {hs:g} | {ref:.2f} (2000 rings {ref2:.2f}) | " + " | ".join(row) + " |", flush=True)
    # The layered models (one node per layer) against the layered reference: how the cut edge shows in them
    print("\n| h_side | layered reference rise (K) | " + " | ".join(f"FVM {c:g} mm | FDM {c:g} mm" for c in cells) + " |")
    print("| --: | --: | " + " | ".join("--: | --:" for _ in cells) + " |")
    for hs in (10.0, 100.0, 1000.0, 5000.0):
        p = rotsq.disc_board(d, a, hs)
        amb = p.board.ambient
        ref = axisym3d.solve_layered_disc(p, d / 2000.0, a / 1000.0, 4000)
        row = []
        for c in cells:
            for m in ("fvm", "fdm"):
                t = runs.tmax(p, m, c) - amb
                out[f"{hs:g}|{c:g}|{m}"] = t
                row.append(f"{t:.2f} ({100 * (t - ref) / ref:+.1f} %)")
        out[f"{hs:g}|layered_ref"] = ref
        print(f"| {hs:g} | {ref:.2f} | " + " | ".join(row) + " |", flush=True)
    runs.save("disc.json", out)


if __name__ == "__main__":
    main()
