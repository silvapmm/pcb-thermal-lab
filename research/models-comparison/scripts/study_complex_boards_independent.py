#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_complex_boards_independent.py
@brief Is the reference of study_complex_boards.py (the program's 3D solid at 1 mm) right on its one-layer boards? A check against a solver that shares no code with the program.

@details Three one-layer boards of study_complex_boards.py (full copper on 3.2 mm, the LED strip with three pads on a trace, the 20 mm pad) are solved by the
         independent 3D finite-volume solver of research/solid3d-verification/lib/layered3d.py (0.5 mm cells, the copper as one slab with the conductivity of every
         cell, the laminate as 8 slabs, films on both faces, the film also under the sources as in the program) and by the five models of the program. The independent
         solver is isotropic and has insulated sides, so the boards are made the same for both: FR-4 0.3 W/mK in every direction and no edge loss. It also prints the
         grid sensitivity of the 3D solid itself (1 mm against 0.5 mm) on the anisotropic boards of the study. The zones of these boards are rectangles, so their cover
         of a cell is exact on the 0.5 mm grid.
Usage: .venv/bin/python research/models-comparison/scripts/study_complex_boards_independent.py   (from the repository root; about 2 minutes)
"""

import copy
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "solid3d-verification", "lib"))

import layered3d                                                                     # noqa: E402
import study_complex_boards as cb                                                    # noqa: E402
from pcbthermal import Problem, analytic, fdm, fvm, lumped, solid3d                  # noqa: E402
from pcbthermal.examples import example_block_board, example_board                   # noqa: E402

BOARDS = ("1 layer, full copper, 3.2 mm", "1 layer, LED strip, three pads on a trace", "1 layer, 20 mm pad")
DX = 0.5e-3                     # Cell of the independent solver (m)


def _bbox(poly):
    """!
    @brief Bounding rectangle of a polygon.
    @param poly Array (n, 2) of vertices in m.
    @return tuple (x0, y0, x1, y1) in m.
    """
    a = np.asarray(poly)
    return float(a[:, 0].min()), float(a[:, 1].min()), float(a[:, 0].max()), float(a[:, 1].max())


def independent_rise(p):
    """!
    @brief Maximum temperature rise of the top face of a one-layer board from the independent solver.
    @param p Problem with one layer, rectangular zones and rectangular heaters (isotropic FR-4 and no edge loss already set).
    @return float Rise in K.
    """
    b, m = p.board, p.board.materials
    nx, ny = int(round(b.width / DX)), int(round(b.height / DX))
    xs, ys = (np.arange(nx) + 0.5) * DX, (np.arange(ny) + 0.5) * DX
    k_top = np.full((ny, nx), m.k_fr4_through)            # Bare cells of the copper slab are laminate
    for z in p.zones:
        x0, y0, x1, y1 = _bbox(z.polygon)
        k_top[(xs[None, :] > x0) & (xs[None, :] < x1) & (ys[:, None] > y0) & (ys[:, None] < y1)] = m.k_copper
    t_cu = b.copper_thickness[0]
    slabs = [(t_cu, k_top, 1), (b.thickness - t_cu, m.k_fr4_through, 8)]
    rects = [_bbox(h.polygon) for h in p.heaters]
    r = layered3d.solve(DX, nx, ny, slabs, rects, [h.power for h in p.heaters], b.h_top, b.h_bottom, film_under_source=True)
    return float(r["T"][0].max())


def main():
    """!
    @brief Print the grid sensitivity of the 3D solid and the models against the independent solver.
    @return None.
    """
    items = dict(cb.boards({"Problem": Problem, "example_board": example_board, "example_block_board": example_block_board}))
    print("3D solid of the study (anisotropic FR-4, edge loss): rise at 1 mm and 0.5 mm")
    for name in BOARDS:
        a, b = solid3d.solve_steady(items[name], 1.0).delta_t, solid3d.solve_steady(items[name], 0.5).delta_t
        print(f"  {name}: {a:.2f} K, {b:.2f} K ({100 * (a / b - 1):+.1f} %)")
    print("\nSame boards made isotropic (FR-4 0.3 W/mK) and without edge loss: error of the rise against the independent solver (0.5 mm)")
    for name in BOARDS:
        p = copy.deepcopy(items[name])
        p.board.materials.k_fr4_inplane = p.board.materials.k_fr4_through
        p.board.h_side = None
        ref = independent_rise(p)
        res = {"fvm": fvm.solve_steady(p, 1.0), "fdm": fdm.solve_steady(p, 1.0), "lumped": lumped.solve_steady(p), "analytic": analytic.solve_steady(p),
               "solid3d 1 mm": solid3d.solve_steady(p, 1.0), "solid3d 0.5 mm": solid3d.solve_steady(p, 0.5)}
        print(f"  {name}: independent {ref:.2f} K; " + ", ".join(f"{k} {100 * (r.delta_t / ref - 1):+.1f} %" for k, r in res.items()))


if __name__ == "__main__":
    main()
