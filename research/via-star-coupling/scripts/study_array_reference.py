#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_array_reference.py
@brief Does the via effect of a dense 10 x 10 array of 0.3 mm vias read right against a resolved 3D solid, before and after the star coupling?
@details A 16 mm, four-layer board (copper on all layers, 3 W on an 8 mm part, h = 10 and 100 W/m2K on the faces, 10 x 10 vias at 0.8 mm pitch under the part, copper-filled so that
         the barrel is not the question) is the dense_via_board of tests/test_maximum_principle.py made small enough for the 3D solid to resolve it. The via effect is the maximum
         rise without the vias minus the maximum rise with them; the FVM runs at 1, 0.5 and 0.25 mm on the program tree given with `--tree` ("before" = a checkout of the commit
         before the star coupling), the 3D solid at 0.2 and 0.1 mm (it reads viawell.tuned_footprint, which the star does not change, so one run serves both trees; the second
         number of the pair shows whether it has converged).
         Run from the repository root: `.venv/bin/python research/via-star-coupling/scripts/study_array_reference.py --tree . [--no-3d]`.
"""

import argparse
import logging
import os
import sys


def board(tree, with_vias, fill_k=385.0, size=16.0, pitch=0.8, n=10):
    """!
    @brief The small dense-array board.
    @param tree Root of the program tree.
    @param with_vias False for the reference without vias.
    @param fill_k Via fill conductivity in W/mK.
    @param size Side of the board in mm.
    @param pitch Via pitch in mm.
    @param n Vias per side.
    @return Problem.
    """
    from pcbthermal import Problem
    p = Problem.new(size, size, 4, h_top=10.0, h_bottom=100.0)
    c = size / 2.0
    for layer in (1, 2, 3, 4):
        p.add_zone(layer, rect=(0.5, 0.5, size - 0.5, size - 0.5))
    p.add_heater(1, 3.0, rect=(c - 4, c - 4, c + 4, c + 4), name="Q1")
    if with_vias:
        h = (n - 1) / 2.0
        for i in range(n):
            for j in range(n):
                p.add_via(c + (i - h) * pitch, c + (j - h) * pitch, 0.3, fill_k=fill_k)
    return p


def main():
    """!
    @brief Print the via effect of the FVM (and the 3D solid) on the array board.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--tree", default=os.getcwd(), help="root of the program tree")
    ap.add_argument("--no-3d", action="store_true", help="skip the 3D solid")
    a = ap.parse_args()
    tree = os.path.abspath(a.tree)
    for p in (os.path.join(tree, "tests"), tree):
        sys.path.insert(0, p)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    logging.disable(logging.WARNING)
    import test_maximum_principle as tmp
    from pcbthermal import solid3d
    from pcbthermal.model import reload_libraries
    reload_libraries()
    print("tree", tree)
    for cell in (1.0, 0.5, 0.25):
        for kind in ("fvm", "fdm"):
            n0 = tmp.network(board(tree, False), kind, cell)
            n1 = tmp.network(board(tree, True), kind, cell)
            t0, t1 = n0.solve_steady()[0], n1.solve_steady()[0]
            e = float(t0[:4].max() - t1[:4].max())
            print(f"{kind} {cell:5.3f} mm: via effect {e:7.3f} K, positive entries of K {tmp.positive_entries(n1)[0]}", flush=True)
    if not a.no_3d:
        for cell in (0.2, 0.1):
            e = solid3d.solve_steady(board(tree, False), cell).t_max - solid3d.solve_steady(board(tree, True), cell).t_max
            print(f"solid3d {cell:5.3f} mm: via effect {e:7.3f} K", flush=True)


if __name__ == "__main__":
    main()
