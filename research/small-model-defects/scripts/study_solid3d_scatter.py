#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_solid3d_scatter.py
@brief Item 3: is the split footprint closer to the truth? The hottest temperature of the 3D solid for a lone via moved across one cell, program and candidate, against the FVM.
@details Board plate_lone_via of the regression harness (60 x 60 mm, 2 layers, 8 mm part, a 0.3 mm via under it) with the via at (30 + s, 30 + s) for s from 0 to 0.5 cell
         (30 is a grid line at 1 and 2 mm; s = 0.5 cell is the centre of a cell). A physical via moved by a fraction of a cell changes the answer little, so the spread over
         s is the discretisation scatter of the footprint rule. Usage: python research/small-model-defects/scripts/study_solid3d_scatter.py   (from the repository root; about 2 minutes).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(ROOT / "releases" / "regression-harness" / "lib"))

import regress_boards as rb                                                 # noqa: E402
import solid_gridline                                                       # noqa: E402
from pcbthermal.api import SolverOptions, simulate                          # noqa: E402


def board(s):
    """!
    @brief plate_lone_via with the via moved by s mm in x and y.
    @param s Shift in mm.
    @return Problem.
    """
    p = rb.build("plate_lone_via")
    p.vias[0].x += s / 1000.0
    p.vias[0].y += s / 1000.0
    return p


def main():
    """!
    @brief Print the table.
    @return None.
    """
    for cell in (2.0, 1.0):
        print(f"\n== cell {cell} mm: hottest temperature (degC) against the shift s of the via (mm) ==")
        print("s | FVM | solid3d program | solid3d candidate")
        rows = []
        for f in (0.0, 0.1, 0.25, 0.5):
            s = f * cell
            fvm = float(simulate(board(s), SolverOptions(models=("fvm",), cell_mm=cell)).results["fvm"].t_max)
            a = float(simulate(board(s), SolverOptions(models=("solid3d",), cell_mm=cell)).results["solid3d"].t_max)
            with solid_gridline.using():
                b = float(simulate(board(s), SolverOptions(models=("solid3d",), cell_mm=cell)).results["solid3d"].t_max)
            rows.append((a, b))
            print(f"{s:.3f} | {fvm:.3f} | {a:.3f} | {b:.3f}", flush=True)
        print(f"spread over s (max - min): program {max(r[0] for r in rows) - min(r[0] for r in rows):.3f} K, candidate {max(r[1] for r in rows) - min(r[1] for r in rows):.3f} K")


if __name__ == "__main__":
    main()
