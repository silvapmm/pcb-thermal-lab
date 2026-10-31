#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_square_reference.py
@brief (Review) Against an independent continuum value, how far are the program's 3D solid and the cut-cell copy on the shifted and turned squares?
@details The shifted and the turned square (board and part moved together) are the same continuum problem as the aligned square, so their
         answer is the continuum answer of the aligned square. `lib/square3d.py` (imports nothing of the program) solves the aligned square on
         its quarter with cells the edge never cuts, on a ladder of cells down to 1/32 mm, and a Richardson step gives the continuum value; the
         same with the part turned by 45 degrees (a diamond) gives the continuum effect of turning the part alone. The program, the cut-cell copy
         and the copy with the footprint of the part sampled on 8 x 8 points (`cutcell_src8`, as the FVM samples it) are then compared with that
         value: the 20 mm board of section 4 (h_side 2000 W/m2K) at 0.5, 0.25 and 0.125 mm, and the 40 mm board of section 2 at 1 mm.
         Prints markdown tables and writes out/square_reference.json.
Usage: .venv/bin/python research/rotated-square-3d/scripts/study_square_reference.py   (from the repository root)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import axisym3d   # noqa: E402
import rotsq      # noqa: E402
import runs       # noqa: E402
import square3d   # noqa: E402


def reference(side_mm, part_mm, h_side, ns, diamond=False):
    """!
    @brief Ladder of the independent quarter-board solver and its Richardson value.
    @param side_mm Board side in mm.
    @param part_mm Part side in mm.
    @param h_side Edge coefficient in W/m2K.
    @param ns Cells along the half side, coarse to fine (each twice the previous).
    @param diamond True for the part turned by 45 degrees.
    @return Tuple (list of (cell in mm, temperature in degC, energy balance), extrapolated temperature in degC).
    """
    p = rotsq.board(0, h_side, side_mm=side_mm, box_mm=side_mm + 10.0, part_mm=part_mm)
    b = p.board
    ladder = []
    for n in ns:
        r = square3d.solve_quarter(side_mm / 1000.0, part_mm / 1000.0, 2.0, axisym3d.slabs_of(p), b.h_top, b.h_bottom, h_side, n, diamond=diamond)
        ladder.append((r["cell"] * 1000.0, r["t_centre"] + b.ambient, r["balance"]))
    return ladder, square3d.richardson(ladder[-2][1], ladder[-1][1])


def main():
    """!
    @brief Run the references and the models and print the tables.
    @return None.
    """
    out = {}
    print("**Independent reference** (`lib/square3d.py`), maximum temperature in degC, energy balance in brackets\n")
    print("| board | part | ladder: cell (mm) temperature (degC) [energy balance] | Richardson |")
    print("| :-- | :-- | :-- | --: |")
    refs = {}
    for diamond in (False, True):
        ladder, ext = reference(20.0, 3.0, 2000.0, (20, 40, 80, 160, 320), diamond)
        key = "20mm_2000_" + ("diamond" if diamond else "square")
        refs[key] = ext
        out[key] = {"ladder": ladder, "richardson": ext}
        print(f"| 20 mm, h_side 2000 | {'turned 45' if diamond else 'aligned'} | " + "; ".join(f"{c:g}: {t:.3f} [{bal:.6f}]" for c, t, bal in ladder) + f" | {ext:.3f} |", flush=True)
    for hs in (100.0, 1000.0):
        ladder, ext = reference(40.0, 6.0, hs, (20, 40, 80, 160), False)
        refs[f"40mm_{hs:g}"] = ext
        out[f"40mm_{hs:g}"] = {"ladder": ladder, "richardson": ext}
        print(f"| 40 mm, h_side {hs:g} | aligned | " + "; ".join(f"{c:g}: {t:.3f} [{bal:.6f}]" for c, t, bal in ladder) + f" | {ext:.3f} |", flush=True)

    ref = refs["20mm_2000_square"]
    models = ("solid3d", "cutcell", "cutcell_src8")
    layouts = [("aligned", 0, 0.0), ("shift 1/2 cell", 0, 0.5), ("turned 20", 20, 0.0), ("turned 45", 45, 0.0)]
    print(f"\n**20 mm board, h_side 2000**: maximum temperature in degC, in brackets the difference to the continuum value {ref:.2f} degC (K)\n")
    print("| cell | layout | " + " | ".join(models) + " |")
    print("| --: | :-- | " + " | ".join("--:" for _ in models) + " |")
    for cell in (0.5, 0.25, 0.125):
        for name, ang, sh in layouts:
            p = rotsq.board(ang, 2000.0, side_mm=20.0, box_mm=30.0, part_mm=3.0, part_angle_deg=float(ang), shift_mm=(sh * cell, sh * cell))
            row = []
            for m in models:
                t = runs.tmax(p, m, cell)
                out[f"20mm|{cell:g}|{name}|{m}"] = t
                row.append(f"{t:.2f} ({t - ref:+.2f})")
            print(f"| {cell:g} | {name} | " + " | ".join(row) + " |", flush=True)

    print("\n**40 mm board, 1 mm cells** (section 2): maximum temperature in degC, in brackets the difference to the continuum value (K)\n")
    print("| h_side | continuum | layout | " + " | ".join(models) + " |")
    print("| --: | --: | :-- | " + " | ".join("--:" for _ in models) + " |")
    for hs in (100.0, 1000.0):
        r40 = refs[f"40mm_{hs:g}"]
        for name, ang, part_ang in (("aligned", 0, 0.0), ("both 20", 20, 20.0), ("board only 20", 20, 0.0), ("both 45", 45, 45.0)):
            p = rotsq.board(ang, hs, part_angle_deg=part_ang)
            row = []
            for m in models:
                t = runs.tmax(p, m, 1.0)
                out[f"40mm|{hs:g}|{name}|{m}"] = t
                row.append(f"{t:.2f} ({t - r40:+.2f})")
            print(f"| {hs:g} | {r40:.2f} | {name} | " + " | ".join(row) + " |", flush=True)
    runs.save("square_reference.json", out)


if __name__ == "__main__":
    main()
