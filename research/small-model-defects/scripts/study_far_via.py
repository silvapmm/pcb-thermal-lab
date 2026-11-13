#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_far_via.py
@brief Item 1: why does the Lumped model heat when a via is added far from the heater? Reproduces it, shows the cause (the far via joins the cluster through the
       grouping rule) and measures a candidate fix.
@details Board: 60 x 60 mm, 2 layers, full copper, h_top 10, h_bottom 15, h_side 10 W/m2K, one 8 x 8 mm 5 W part at the centre, a group of n vias under it (n = 0, 1, 2, 4, 16),
         one more via at a distance D from the part. Reports the change of the hottest temperature (FVM, Lumped, Analytic) with the program's grouping and with the
         variants of lib/grouping.py, and the group sizes. Usage: python research/small-model-defects/scripts/study_far_via.py   (from the repository root; a few minutes).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
sys.path.insert(0, str(HERE.parent / "lib"))

import numpy as np                                                          # noqa: E402

import grouping                                                             # noqa: E402
from pcbthermal import viaconstriction as vc                               # noqa: E402
from pcbthermal.api import SolverOptions, simulate                          # noqa: E402
from pcbthermal.model import Problem                                        # noqa: E402


def board(vias, layers=2, cu_um=35.0, size=8.0):
    """!
    @brief The study board.
    @param vias List of (x, y) in mm (0.3 mm drill).
    @param layers Copper layers.
    @param cu_um Copper thickness in um.
    @param size Side of the square part in mm.
    @return Problem.
    """
    p = Problem.new(60, 60, layers=layers, copper_um=cu_um, h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_full_copper()
    p.add_heater(1, 5.0, rect=(30 - size / 2, 30 - size / 2, 30 + size / 2, 30 + size / 2), name="U")
    for v in vias:
        p.add_via(*v, diameter=0.3)
    return p


def tmax(vias, cell, variant="program", layers=2, models=("fvm", "lumped", "analytic")):
    """!
    @brief Hottest temperatures of the models for a via list.
    @param vias List of (x, y) in mm.
    @param cell Cell in mm.
    @param variant Grouping variant of lib/grouping.py.
    @param layers Copper layers.
    @param models Models to run.
    @return dict model -> degC.
    """
    with grouping.using(variant):
        s = simulate(board(vias, layers), SolverOptions(models=models, cell_mm=cell))
    return {k: float(r.t_max) for k, r in s.results.items()}


def array(n):
    """!
    @brief n vias under the part: 0, 1, 2 (a pair), 4 (2 x 2), 16 (4 x 4) at 2 mm pitch.
    @param n Count.
    @return list of (x, y) in mm.
    """
    if n == 0:
        return []
    if n == 1:
        return [(30.0, 30.0)]
    side = {2: (2, 1), 4: (2, 2), 16: (4, 4)}[n]
    return [(30 - (side[0] - 1) + 2 * i, 30 - (side[1] - 1) + 2 * j) for i in range(side[0]) for j in range(side[1])]


def group_info(vias):
    """!
    @brief Group of the last via: its size and nearest-neighbour distance.
    @param vias List of (x, y) in mm.
    @return (size of the group of the last via, its d_nn in mm).
    """
    pts = np.array(vias) / 1000.0
    d = vc.nearest_neighbour(pts)
    g = vc.via_groups(pts, d)
    return int((g == g[-1]).sum()), float(d[-1] * 1000.0)


def main():
    """!
    @brief Run the sweeps and print the tables.
    @return None.
    """
    cell = 1.0
    print("== 1. Reproduction: change of the hottest temperature (K) when ONE via is added 25 mm from the part centre (cell 1 mm) ==")
    print("vias under the part | FVM | Lumped | Analytic | vias in the group of the far via")
    for n in (0, 1, 2, 4, 16):
        base = tmax(array(n), cell)
        v = array(n) + [(5.0, 30.0)]
        r = tmax(v, cell)
        size, dnn = group_info(v)
        print(f"{n} | " + " | ".join(f"{r[k] - base[k]:+.3f}" for k in ("fvm", "lumped", "analytic")) + f" | {size} of {len(v)} (d_nn {dnn:.1f} mm)")
    print("\n== 2. Dependence on the distance of the added via (16 vias under the part) ==")
    base = tmax(array(16), cell)
    print("distance from the centre mm | d_nn of the far via mm | in the group | FVM | Lumped | Lumped min | Lumped min_inf")
    for dist in (5, 8, 10, 12, 15, 20, 25):
        v = array(16) + [(30.0 - dist, 30.0)]
        size, dnn = group_info(v)
        row = {var: tmax(v, cell, variant=var, models=("fvm", "lumped") if var == "program" else ("lumped",)) for var in ("program", "min", "min_inf")}
        print(f"{dist} | {dnn:.1f} | {'yes' if size > 1 else 'no'} | {row['program']['fvm'] - base['fvm']:+.3f} | {row['program']['lumped'] - base['lumped']:+.3f} | "
              f"{row['min']['lumped'] - base['lumped']:+.3f} | {row['min_inf']['lumped'] - base['lumped']:+.3f}")
    print("\n== 3. Number of far vias (16 under the part; vias on a 6 mm row 22 mm away) ==")
    print("far vias | FVM | Lumped | Lumped min_inf")
    for m in (1, 2, 4, 8):
        v = array(16) + ([(8.0, 30.0)] if m == 1 else [(8.0, 27.0 + 6.0 * k / (m - 1)) for k in range(m)])
        a = tmax(v, cell)
        b = tmax(v, cell, variant="min_inf", models=("lumped",))
        print(f"{m} | {a['fvm'] - base['fvm']:+.3f} | {a['lumped'] - base['lumped']:+.3f} | {b['lumped'] - base['lumped']:+.3f}")
    print("\n== 4. Layers and cell (16 under the part + one via 25 mm away) ==")
    print("layers | cell mm | FVM | Lumped | Lumped min_inf")
    for layers in (2, 4):
        for c in (1.0, 0.5):
            b0 = tmax(array(16), c, layers=layers)
            v = array(16) + [(5.0, 30.0)]
            a = tmax(v, c, layers=layers)
            b = tmax(v, c, variant="min_inf", layers=layers, models=("lumped",))
            print(f"{layers} | {c} | {a['fvm'] - b0['fvm']:+.3f} | {a['lumped'] - b0['lumped']:+.3f} | {b['lumped'] - b0['lumped']:+.3f}")


if __name__ == "__main__":
    main()
