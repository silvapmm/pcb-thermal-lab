#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file general.py
@brief Boards that are not symmetric (pads off the centre, several pads, a source off the pad, a window in the copper): the program's Problem and the independent resolved 3D solution on the whole board.
@details `lib/pads.py` solves a quadrant because its pad and source are centred. Here the copper of the top layer is a list of rectangles (a pad, two pads, the frame around a window), the second
         layer is full or empty, and the source is any rectangle on the top layer; the reference solves the whole board with resolved3d (cells of dx_mm, 8 sub-slabs through the laminate) and reads the
         hottest cell of the source. Edges of every rectangle must lie on cell edges. Same data as lib/pads.py: the numbers come from the Problem.
"""

import numpy as np

import pads as P
import resolved3d as r3
from pcbthermal import Problem
from pcbthermal.model import Materials


def problem(bd, top_rects, source, bottom="full"):
    """!
    @brief The program's Problem.
    @param bd A pads.Pad (size, thickness, copper, films, laminate; its pad and source fields are ignored).
    @param top_rects List of copper rectangles (x0, y0, x1, y1) in mm on the top layer.
    @param source The part, a rectangle (x0, y0, x1, y1) in mm on the top layer.
    @param bottom "full" or "empty" for the second layer of a two-layer board.
    @return Problem.
    """
    mats = Materials(k_fr4_through=bd.k_through, k_fr4_inplane=bd.k_inplane)
    p = Problem.new(bd.size, bd.size, bd.layers, bd.thickness, bd.copper, h_top=bd.h_top, h_bottom=bd.h_bottom, h_side=None, materials=mats)
    if bd.layers > 1:
        p.board.make_advanced()
    for r in top_rects:
        p.add_zone(1, rect=tuple(r))
    if bd.layers > 1 and bottom == "full":
        p.add_zone(2, rect=(0, 0, bd.size, bd.size))
    p.add_heater(1, bd.power, rect=tuple(source))
    return p


def reference(bd, top_rects, source, bottom="full", dx_mm=0.5, nsub=8, p=None):
    """!
    @brief The resolved 3D solution of the whole board.
    @param bd A pads.Pad.
    @param top_rects Copper rectangles (mm) of the top layer.
    @param source The part rectangle (mm).
    @param bottom "full" or "empty".
    @param dx_mm Cell size of the reference in mm.
    @param nsub Sub-slabs through the laminate.
    @param p The Problem (built when None).
    @return dict with peak (K, hottest cell of the source), balance and unknowns.
    """
    p = p or problem(bd, top_rects, source, bottom)
    b = p.board
    kcu, tcu = float(b.materials.k_copper), [float(x) for x in b.copper_thickness]
    n = int(round(bd.size / dx_mm))
    xs = (np.arange(n) + 0.5) * dx_mm
    f1 = np.zeros((n, n))
    for x0, y0, x1, y1 in top_rects:
        f1[((xs[:, None] > y0) & (xs[:, None] < y1)) & ((xs[None, :] > x0) & (xs[None, :] < x1))] = 1.0

    def mix(f):
        return bd.k_inplane + f * (kcu - bd.k_inplane), bd.k_through + f * (kcu - bd.k_through)

    kxy, kz = mix(f1)
    slabs = [(tcu[0], kxy, kz, 1)]
    if bd.layers == 1:
        slabs.append((bd.thickness * 1e-3 - tcu[0], bd.k_inplane, bd.k_through, nsub))
    else:
        slabs.append(((bd.thickness * 1e-3 - sum(tcu)) / (bd.layers - 1), bd.k_inplane, bd.k_through, nsub))
        kxy2, kz2 = mix(np.ones((n, n)) if bottom == "full" else np.zeros((n, n)))
        slabs.append((tcu[1], kxy2, kz2, 1))
    src = tuple(v * 1e-3 for v in source)
    res = r3.solve(dx_mm * 1e-3, n, n, slabs, src, bd.power, b.h_top, b.h_bottom)
    return {"peak": float(res["surf"][res["mask"]].max()), "balance": res["balance"], "unknowns": int(res["T"].size)}
