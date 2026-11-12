#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_frozen_impact.py
@brief Which frozen-number records of the regression harness the candidates move: the interpolated centroid read of the Lumped (item 2) and the split footprint of a via on a
       grid line in the 3D solid (item 3). The grouping rule (item 1) and the harmonic FDM (item 2) are measured in study_grouping_impact.py (part A) and study_fdm_gap.py (part B).
@details The 17 boards of releases/regression-harness at 2 and 1 mm (the 3D solid only where its memory guard allows and only boards with vias or an outline for the
         solid), hottest temperature with the program and with the candidate; prints the records that move by more than 1e-9 K.
         Usage: python research/small-model-defects/scripts/study_frozen_impact.py   (from the repository root; about 3 minutes).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(ROOT / "releases" / "regression-harness" / "lib"))

import centroid_patch                                                       # noqa: E402
import regress_boards as rb                                                 # noqa: E402
import solid_gridline                                                       # noqa: E402
from pcbthermal.api import SolverOptions, simulate                          # noqa: E402


def tmax(name, cell, model):
    """!
    @brief Hottest temperature of a harness board.
    @param name Board name.
    @param cell Cell in mm.
    @param model Model key.
    @return float degC or None when the model refuses the board.
    """
    try:
        return float(simulate(rb.build(name), SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max)
    except Exception:                                                        # refused by the memory guard or by the model (a block with faces for the Lumped)
        return None


def main():
    """!
    @brief Run both comparisons.
    @return None.
    """
    for title, model, ctx, cells in (("Lumped, interpolated centroid read", "lumped", centroid_patch.using, (2.0, 1.0, 0.5)),
                                     ("3D solid, split footprint on a grid line", "solid3d", solid_gridline.using, (2.0, 1.0))):
        print(f"\n== {title}: harness records that move ==")
        moved = total = 0
        for name in rb.board_names():
            for cell in cells:
                a = tmax(name, cell, model)
                with ctx():
                    b = tmax(name, cell, model)
                if a is None or b is None:
                    continue
                total += 1
                if abs(a - b) > 1e-9:
                    moved += 1
                    print(f"{name} | cell {cell} | program {a:.4f} | candidate {b:.4f} | {b - a:+.4f} K", flush=True)
        print(f"{moved} of {total} records move")


if __name__ == "__main__":
    main()
