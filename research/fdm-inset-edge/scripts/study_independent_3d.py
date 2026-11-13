#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_independent_3d.py
@brief Does the face-fill variant of the FDM stay closer to an INDEPENDENT 3D solver on the copper-edge boards of validation 41 (the boards where the harmonic mean was judged)?
@details The reference is `tests/helpers/layered3d.py` (imports nothing from the program) at the SAME cell, as in validation 41, copper patterned slab by slab, insulated sides.
         Boards: `plate_pad` and `one_layer_pad` (the harness boards with a reference), the 3 mm gap across both layers (50 x 24 mm) and the copper strips 2 mm / gap 2 mm
         (40 x 20 mm). Columns: FVM, FDM harmonic (the program), FDM with faces from the cell fill (variant), percent of the reference rise (hottest rise as in
         `tests/test_fdm_harmonic_face.py`). Run from the repository root: `.venv/bin/python research/fdm-inset-edge/scripts/study_independent_3d.py`.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(1, os.path.join(ROOT, "tests", "helpers"))
sys.path.insert(2, os.path.join(ROOT, "tests", "regression"))
sys.path.insert(3, os.path.join(HERE, "..", "lib"))

import numpy as np                                            # noqa: E402

import layered3d as L                                         # noqa: E402
import regress_boards as RB                                   # noqa: E402
import fdm_variant                                            # noqa: E402
from pcbthermal import Problem, fdm, fvm                      # noqa: E402
from pcbthermal.model import Materials                        # noqa: E402

AMB = 25.0
T = 35e-6


def gap_board():
    """!
    @brief The 3 mm gap board of tests/test_fdm_harmonic_face.py.
    @return Problem.
    """
    p = Problem.new(50.0, 24.0, layers=2, thickness_mm=1.6, copper_um=35.0, ambient=AMB, h_top=10.0, h_bottom=15.0, h_side=None,
                    materials=Materials(k_fr4_through=0.3, k_fr4_inplane=0.3))
    for layer in (1, 2):
        p.add_zone(layer, rect=(0, 0, 23.0, 24.0))
        p.add_zone(layer, rect=(26.0, 0, 50.0, 24.0))
    p.add_heater(1, 2.0, rect=(16, 9, 22, 15), name="U")
    return p


def gap_ref(cell):
    """!
    @brief Independent reference of the gap board.
    @param cell Cell in mm.
    @return Rise in K.
    """
    n, m = int(round(50 / cell)), int(round(24 / cell))
    xs = (np.arange(n) + 0.5) * cell
    k = np.where((xs > 23.0) & (xs < 26.0), 0.3, 385.0)[None, :] * np.ones((m, 1))
    r = L.solve(cell * 1e-3, n, m, [(T, k, 1), (1.6e-3 - 2 * T, 0.3, 8), (T, k, 1)], (16e-3, 9e-3, 22e-3, 15e-3), 2.0, 10.0, 15.0, film_under_source=True)
    return float(r["cell_max_source"])


def strips_board():
    """!
    @brief Copper strips 2 mm wide every 4 mm along x (gaps 2 mm) on both layers of a 40 x 20 mm board, a 4 x 4 mm 1 W part on a strip.
    @return Problem.
    """
    p = Problem.new(40.0, 20.0, layers=2, thickness_mm=1.6, copper_um=35.0, ambient=AMB, h_top=10.0, h_bottom=15.0, h_side=None,
                    materials=Materials(k_fr4_through=0.3, k_fr4_inplane=0.3))
    for layer in (1, 2):
        for y0 in np.arange(0.0, 20.0, 4.0):
            p.add_zone(layer, rect=(0, y0, 40.0, y0 + 2.0))
    p.add_heater(1, 1.0, rect=(18, 8, 22, 12), name="U")
    return p


def strips_ref(cell):
    """!
    @brief Independent reference of the strips board.
    @param cell Cell in mm.
    @return Rise in K.
    """
    n, m = int(round(40 / cell)), int(round(20 / cell))
    ys = (np.arange(m) + 0.5) * cell
    k = np.where((ys % 4.0) < 2.0, 385.0, 0.3)[:, None] * np.ones((1, n))
    r = L.solve(cell * 1e-3, n, m, [(T, k, 1), (1.6e-3 - 2 * T, 0.3, 8), (T, k, 1)], (18e-3, 8e-3, 22e-3, 12e-3), 1.0, 10.0, 15.0, film_under_source=True)
    return float(r["cell_max_source"])


def spec_ref(name, cell):
    """!
    @brief Independent reference of a harness board with a reference specification (plate_pad, one_layer_pad).
    @param name Board name.
    @param cell Cell in mm.
    @return Rise in K.
    """
    s = RB.REFERENCE_SPECS[name]
    n = int(round(s["size"] / cell))
    xs = (np.arange(n) + 0.5) * cell
    x0, y0, x1, y1 = s["pad"]
    inside = ((xs[None, :] > x0) & (xs[None, :] < x1) & (xs[:, None] > y0) & (xs[:, None] < y1))
    k = np.where(inside, s["k_cu"], s["k_lam"])
    t, tot = s["cu_um"] * 1e-6, s["thickness"] * 1e-3
    if s["layers"] == 2:
        slabs = [(t, k, 1), (tot - 2 * t, s["k_lam"], 8), (t, k, 1)]
    else:
        slabs = [(t, k, 1), (tot - t, s["k_lam"], 8)]
    src = tuple(v * 1e-3 for v in s["src"])
    r = L.solve(cell * 1e-3, n, n, slabs, src, s["power"], s["h_top"], s["h_bottom"], film_under_source=True)
    return float(r["cell_max_source"])


def main():
    """!
    @brief Print the table.
    @return None.
    """
    harm = fdm_variant.harmonic()                            # the program with face_fill=False (as the study found it)
    cases = [("plate_pad", lambda: RB.build("plate_pad"), lambda c: spec_ref("plate_pad", c), (1.0, 0.5)),
             ("one_layer_pad", lambda: RB.build("one_layer_pad"), lambda c: spec_ref("one_layer_pad", c), (1.0, 0.5)),
             ("gap 3 mm (50x24)", gap_board, gap_ref, (1.0, 0.5, 0.25)),
             ("strips 2/2 (40x20)", strips_board, strips_ref, (1.0, 0.5, 0.25))]
    res = {}
    print(f"{'board':20s} {'cell':>5s} {'ref K':>8s} {'FVM %':>8s} {'FDM harm %':>10s} {'face %':>8s}")
    for name, build, ref, cells in cases:
        for cell in cells:
            r = ref(cell)
            p = build()
            amb = p.board.ambient
            v = [float(m.solve_steady(p, cell).t_max) - amb for m in (fvm, harm, fdm)]
            res[f"{name}|{cell}"] = [100 * (x / r - 1) for x in v]
            print(f"{name:20s} {cell:5.2f} {r:8.3f} " + " ".join(f"{100 * (x / r - 1):+8.2f}" for x in v), flush=True)

    json.dump(res, open(os.path.join(HERE, "..", "out", "independent.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
