#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_solid3d_gridline.py
@brief Item 3: the 3D solid is not mirror-symmetric when a via sits on a grid line. Reproduces it, locates the cause (the cell chosen by floor in the point footprint) and measures
       a candidate (a point footprint split over the cells that share the line).
@details Board 40 x 30 mm, 2 layers, h_side 10, a 6 x 6 mm 3 W part off-centre, one via (or a pair) under it. The via x runs over positions relative to the grid
         (on a line, a quarter cell, half cell); each board is run with the via at x and at W - x (the mirror image, part mirrored too) and the difference of the hottest
         temperature is the asymmetry. Reports FVM, FDM and the 3D solid (program) and the 3D solid with the candidate footprint of lib/solid_gridline.py.
         Usage: python research/small-model-defects/scripts/study_solid3d_gridline.py   (from the repository root; about 3 minutes).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parent / "lib"))

import solid_gridline                                                       # noqa: E402
from pcbthermal.api import SolverOptions, simulate                          # noqa: E402
from pcbthermal.model import Problem                                        # noqa: E402

W, H = 40.0, 30.0


def board(vx, mirror, n=1, layers=2, dia=0.3):
    """!
    @brief Board with a part and vias; mirror puts the same board in x -> W - x.
    @param vx Via x in mm (before mirroring).
    @param mirror True for the mirror image.
    @param n 1 (one via at vx), 2 (a pair 1 mm apart in x), 4 (2 x 2 at 1 mm).
    @param layers Copper layers.
    @param dia Drill in mm.
    @return Problem.
    """
    p = Problem.new(W, H, layers=layers, h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_full_copper()
    px0 = 10.0
    xs = (lambda x: W - x) if mirror else (lambda x: x)
    a, b = sorted((xs(px0), xs(px0 + 6.0)))
    p.add_heater(1, 3.0, rect=(a, 12.0, b, 18.0))
    offs = {1: [(0.0, 0.0)], 2: [(0.0, 0.0), (1.0, 0.0)], 4: [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]}[n]
    for dx, dy in offs:
        p.add_via(xs(vx + dx), 15.0 + dy, diameter=dia)
    return p


def run(p, cell, models=("fvm", "fdm", "solid3d")):
    """!
    @brief Hottest temperatures.
    @param p Problem.
    @param cell Cell in mm.
    @param models Models.
    @return dict.
    """
    s = simulate(p, SolverOptions(models=models, cell_mm=cell))
    return {k: float(r.t_max) for k, r in s.results.items()}


def main():
    """!
    @brief Run the table.
    @return None.
    """
    print("== 3D solid: mirror difference of the hottest temperature (mirror - original, K) for a via at x, 1 mm cell; the cells are [k, k+1) mm ==")
    print("n vias | via x mm | FVM | FDM | solid3d (program) | solid3d (candidate) | rise solid3d program | candidate")
    for n in (1, 2, 4):
        for vx in (12.0, 12.25, 12.5, 12.75, 13.0):
            a = run(board(vx, False, n), 1.0)
            b = run(board(vx, True, n), 1.0)
            with solid_gridline.using():
                ca = run(board(vx, False, n), 1.0, ("solid3d",))
                cb = run(board(vx, True, n), 1.0, ("solid3d",))
            print(f"{n} | {vx} | {b['fvm'] - a['fvm']:+.3f} | {b['fdm'] - a['fdm']:+.3f} | {b['solid3d'] - a['solid3d']:+.3f} | {cb['solid3d'] - ca['solid3d']:+.3f} | "
                  f"{a['solid3d'] - 25:.3f} | {ca['solid3d'] - 25:.3f}", flush=True)
    print("\n== Cell 0.5 mm, one via ==")
    for vx in (12.0, 12.25, 12.5):
        a = run(board(vx, False, 1), 0.5, ("solid3d",))
        b = run(board(vx, True, 1), 0.5, ("solid3d",))
        with solid_gridline.using():
            ca = run(board(vx, False, 1), 0.5, ("solid3d",))
            cb = run(board(vx, True, 1), 0.5, ("solid3d",))
        print(f"{vx} | program {b['solid3d'] - a['solid3d']:+.3f} | candidate {cb['solid3d'] - ca['solid3d']:+.3f}", flush=True)


if __name__ == "__main__":
    main()
