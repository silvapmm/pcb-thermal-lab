#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file ref3d.py
@brief The independent 3D reference of a centred part over a centred via array: the test helper `layered3d` (imports nothing of the program) on one quadrant, barrels drawn.
@details Only NUMBERS are read from the program's `Problem` (copper and FR-4 conductivities, thicknesses, plating, films); the solve is `tests/helpers/layered3d.py`. Quadrant symmetry
         (insulated sides, so `h_side` = 0 and the part and the array centred on the board). Each plane is a whole copper slab (as the program draws it); the gap slabs hold, per
         cell, the area share of the barrel copper (annulus of the plating, or the whole disc if filled) and of the fill or air in the core, sampled 16 x 16 per cell. The part's
         surface temperatures come from the top row of cells under the part (`max_source`, `mean_source`), with the film acting under the source as in the program.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tests", "helpers"))
import layered3d                                                              # noqa: E402

K_AIR = 0.03                                                                  # W/mK of an open barrel core


def barrel_shares(vias, plating, dx, n, sub=16):
    """!
    @brief Area share of barrel copper and of the core in every cell of the quadrant.
    @param vias List of (x, y, radius, filled, fill_k) in m in the frame of the quadrant (origin at the board centre).
    @param plating Plating thickness in m.
    @param dx Cell in m.
    @param n Cells per side of the quadrant.
    @param sub Sample points per cell side.
    @return Tuple (f_cu, f_core) of arrays (n, n).
    """
    f_cu, f_core = np.zeros((n, n)), np.zeros((n, n))
    off = (np.arange(sub) + 0.5) / sub * dx
    for (x, y, r, filled, fk) in vias:
        # Via and its mirror images across the two symmetry lines fall in the quadrant as their own copy: count each via once with its full area if inside, the part
        # of a via cut by the symmetry line is already the quadrant's share because the samples outside the quadrant are not drawn
        j0, j1 = max(int((x - r) // dx), 0), min(int((x + r) // dx), n - 1)
        i0, i1 = max(int((y - r) // dx), 0), min(int((y + r) // dx), n - 1)
        for i in range(i0, i1 + 1):
            for j in range(j0, j1 + 1):
                px = j * dx + off[None, :]
                py = i * dx + off[:, None]
                d2 = (px - x) ** 2 + (py - y) ** 2
                r_in = max(r - plating, 0.0)
                if filled:
                    f_cu[i, j] += (d2 <= r * r).mean()
                else:
                    f_cu[i, j] += ((d2 <= r * r) & (d2 >= r_in * r_in)).mean()
                    f_core[i, j] += (d2 < r_in * r_in).mean()
    return np.minimum(f_cu, 1.0), np.minimum(f_core, 1.0)


def solve(p, dx_mm=0.125, n_sub=4):
    """!
    @brief Part peak, part mean and board maximum (degC) of a board whose part and via array are centred, by the independent 3D solver.
    @param p Problem from viastudy.board with offset (0, 0), one part and a rectangular board with h_side = 0.
    @param dx_mm Cell in mm (it must divide half the part side).
    @param n_sub Sub-slabs per gap.
    @return dict peak, mean, board (degC) and the number of cells.
    """
    b = p.board
    m = b.materials
    dx = dx_mm * 1e-3
    n = int(round(b.width / 2 / dx))
    ny = int(round(b.height / 2 / dx))
    assert abs(n * dx - b.width / 2) < 1e-9 and abs(ny * dx - b.height / 2) < 1e-9
    h = p.heaters[0]
    xs = h.polygon[:, 0]
    ys = h.polygon[:, 1]
    cx, cy = b.width / 2, b.height / 2
    src = (0.0, 0.0, (xs.max() - xs.min()) / 2, (ys.max() - ys.min()) / 2)
    vias = [(v.x - cx, v.y - cy, v.diameter / 2, v.filled, v.fill_k) for v in p.vias if v.x >= cx - 1e-12 and v.y >= cy - 1e-12]
    f_cu, f_core = barrel_shares(vias, b.via_plating, dx, max(n, ny))
    f_cu, f_core = f_cu[:ny, :n], f_core[:ny, :n]
    fk = np.mean([v[4] for v in vias]) if vias else 0.0
    k_core = fk if fk > 0 else K_AIR
    gaps = b.gap_thicknesses()
    k_gap = float(b.gap_properties()[0][0])
    k_cell = f_cu * m.k_copper + f_core * k_core + (1 - f_cu - f_core) * k_gap
    plane = np.full((ny, n), m.k_copper)
    slabs = []
    for l in range(b.layers):
        slabs.append((float(b.copper_thickness[l]), plane, 1))
        if l < b.layers - 1:
            slabs.append((float(gaps[l]), k_cell, n_sub))
    res = layered3d.solve(dx, n, ny, slabs, src, h.power / 4.0, b.h_top, b.h_bottom, film_under_source=True)
    amb = b.ambient
    return {"peak": amb + float(res["max_source"]), "mean": amb + float(res["mean_source"]), "board": amb + float(res["T"][0].max()), "cells": int(res["T"].size)}
