#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_edge_conductance.py
@brief How much conductance to the air does the edge of a turned square have in the FVM and in the 3D solid, against the perimeter and against the aligned square?
@details The total side conductance of a network is the sum over cells (and slabs) of the conductance between the cell and the air through the
         edge. For the FVM it is `h_side * thickness * perimeter` whatever the angle (checked against the shoelace perimeter of the outline).
         For the 3D solid every cell and slab has the film `h L dz` in series with the conduction through half a cell, `d / (kx L dz)`; a cell
         that the outline cuts has its in-plane conductivity multiplied by its cover in the program (`kx * cover`), which lengthens the half-cell
         term by 1 / cover. The study prints, for h_side from 10 to 5000 W/m2K, the total side conductance of the program's 3D solid and of the
         cut-cell copy for a square turned by 0, 10, 20 and 45 degrees, as a ratio to the aligned square, with the FVM value and the perimeter.
Usage: .venv/bin/python research/rotated-square-3d/scripts/study_edge_conductance.py   (from the repository root)
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import numpy as np   # noqa: E402

import rotsq         # noqa: E402
import runs          # noqa: E402
from pcbthermal import fvm   # noqa: E402


def g_side_3d(mod, problem, cell):
    """!
    @brief Total side conductance of the 3D network of a variant.
    @param mod Module from `rotsq.variant_solid3d`.
    @param problem Problem.
    @param cell Cell size in mm.
    @return Conductance in W/K.
    """
    return float(mod.Solid(problem, cell).g["sides"].sum())


def main():
    """!
    @brief Print the conductance tables.
    @return None.
    """
    cell = 1.0
    n = int(round(60.0 / cell))
    prog, cut = rotsq.variant_solid3d("program"), rotsq.variant_solid3d("cutcell")
    data = {}
    print(f"cell {cell:g} mm, square 40 mm in a 60 mm box, two copper layers (perimeter 160 mm for every angle)\n")
    print("| h_side | angle | perimeter (mm) | FVM G (mW/K) | FVM G / (h t P) | 3D program G (mW/K) | ratio to aligned | 3D cut-cell G (mW/K) | ratio to aligned |")
    print("| --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    for hs in (10.0, 100.0, 1000.0, 5000.0):
        base = {}
        for ang in (0, 10, 20, 45):
            p = rotsq.board(ang, hs)
            net = fvm.Network(p, n, n, assemble=False, with_blocks=False)
            per = rotsq.perimeter_mm(p.board.outline) * (1000.0 if p.board.outline.max() < 1.0 else 1.0)
            g_fvm = float(net.g_side.sum())
            ideal = hs * p.board.thickness * per / 1000.0
            gp, gc = g_side_3d(prog, p, cell), g_side_3d(cut, p, cell)
            if ang == 0:
                base = {"p": gp, "c": gc}
            data[f"{hs:g}|{ang}"] = {"per": per, "fvm": g_fvm, "ideal": ideal, "program": gp, "cutcell": gc}
            print(f"| {hs:g} | {ang} | {per:.1f} | {g_fvm * 1e3:.2f} | {g_fvm / ideal:.3f} | {gp * 1e3:.2f} | {gp / base['p']:.3f} | {gc * 1e3:.2f} | {gc / base['c']:.3f} |", flush=True)
    runs.save("edge_conductance.json", data)


if __name__ == "__main__":
    main()
