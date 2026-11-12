#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cases.py
@brief The boards of the edge-film study: a 20 mm board (rectangle without an outline, square outline turned by any angle, 20 mm disc) with copper held 1.2 mm inside the edge, drawn as zones or imported as masks.
@details Same physics as `lib/study_outline_mask.py` (the reviewer's board) plus a rectangle with no outline in a 20 mm box and any number of layers (every inner layer is a plane
         inside the inset, the top layer is full copper inside the inset or stripes and a pad). The heater is a 4 mm square of 1 W at the centre, turned with the board;
         h_top = h_bottom = 10 W/m2K. `run` returns the mean rise of the heater (its own area weights), the hottest rise and the heat-balance error.
"""

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..")))
sys.path.insert(0, HERE)

from pcbthermal import Problem, copper, fvm                                    # noqa: E402
import study_outline_mask as sm                                                # noqa: E402

A = sm.A
INSET = sm.INSET
PIX = sm.PIX


def set_inset(mm):
    """!
    @brief Set the distance of the copper edge from the board edge for the next boards.
    @param mm Inset in mm.
    @return None.
    """
    global INSET
    INSET = mm
    sm.INSET = mm


def build(shape, kind, h_side, layers=2, pattern=False, ang=0.0, pixel=PIX):
    """!
    @brief The Problem of one case.
    @param shape 'rect' (20 mm board, no outline), 'square' (20 mm square outline in a 30 mm box, turned by `ang`) or 'disc'.
    @param kind 'imported' (masks) or 'drawn' (zones).
    @param h_side Edge coefficient W/m2K.
    @param layers Copper layers.
    @param pattern True: stripes 1 mm every 2 mm plus a 7 mm pad on the top layer; False: full copper inside the inset.
    @param ang Turn in degrees (square only).
    @param pixel Pixel of the imported masks in mm.
    @return Problem.
    """
    if shape == "rect":
        W, C = A, A / 2
        p = Problem.new(W, W, layers, h_side=h_side)
        p.board.h_top = 10.0
        p.board.h_bottom = 10.0
        p.add_heater(1, 1.0, polygon=[[C - 2, C - 2], [C + 2, C - 2], [C + 2, C + 2], [C - 2, C + 2]], name="U")
        lim = A / 2 - INSET
        if kind == "drawn":
            for l in range(layers):
                if l == 0 and pattern:
                    k = 0
                    while -lim + 2 * k < lim:
                        p.add_zone(1, polygon=[[C - lim, C - lim + 2 * k], [C + lim, C - lim + 2 * k], [C + lim, C + min(-lim + 2 * k + 1, lim)], [C - lim, C + min(-lim + 2 * k + 1, lim)]])
                        k += 1
                    p.add_zone(1, polygon=[[C - 3.5, C - 3.5], [C + 3.5, C - 3.5], [C + 3.5, C + 3.5], [C - 3.5, C + 3.5]])
                else:
                    p.add_zone(l + 1, polygon=[[C - lim, C - lim], [C + lim, C - lim], [C + lim, C + lim], [C - lim, C + lim]])
        else:
            n = int(round(W / pixel))
            sub = 4
            t = (np.arange(n * sub) + 0.5) / sub * pixel
            X, Y = np.meshgrid(t, W - t)
            u, v = X - C, Y - C
            inside = (np.abs(u) <= lim) & (np.abs(v) <= lim)
            stripes = np.floor((v + lim) / 1.0) % 2 == 0
            pad = (np.abs(u) <= 3.5) & (np.abs(v) <= 3.5)
            top = inside & (stripes | pad) if pattern else inside

            def pack(m):
                """!
                @brief Average the sub-samples into 0..255 coverage.
                @param m Boolean sub-sample array.
                @return uint8 array.
                """
                return np.round(255 * m.reshape(n, sub, n, sub).mean(axis=(1, 3))).astype(np.uint8)
            p.imported = copper.imported_from_rasters([pack(top)] + [pack(inside)] * (layers - 1), pixel, "faces")
        return p
    disc = shape == "disc"
    p = Problem.new(sm.W, sm.W, layers, h_side=h_side)
    p.board.h_top = 10.0
    p.board.h_bottom = 10.0
    p.add_heater(1, 1.0, polygon=sm.to_box([(-2, -2), (2, -2), (2, 2), (-2, 2)], ang), name="U")
    p.set_outline(sm.outline(ang, disc))
    if kind == "imported":
        top, bot = sm.copper_masks(ang, disc, pattern)
        p.imported = copper.imported_from_rasters([top] + [bot] * (layers - 1), pixel, "faces")
        return p
    lim = A / 2 - INSET

    def rect(u0, v0, u1, v1):
        """!
        @brief A turned rectangle of the board frame in box coordinates.
        @param u0 Left mm.
        @param v0 Bottom mm.
        @param u1 Right mm.
        @param v1 Top mm.
        @return Polygon.
        """
        return sm.to_box([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], ang)
    for l in range(1, layers):
        p.add_zone(l + 1, polygon=rect(-lim, -lim, lim, lim))
    if pattern:
        k = 0
        while -lim + 2 * k < lim:
            p.add_zone(1, polygon=rect(-lim, -lim + 2 * k, lim, min(-lim + 2 * k + 1, lim)))
            k += 1
        p.add_zone(1, polygon=rect(-3.5, -3.5, 3.5, 3.5))
    else:
        p.add_zone(1, polygon=rect(-lim, -lim, lim, lim))
    return p


def run(p, cell):
    """!
    @brief Mean heater rise, hottest rise and balance of the program at one cell.
    @param p Problem.
    @param cell Cell in mm.
    @return Tuple (mean K, hottest K, balance error).
    """
    nx = max(int(round(p.board.width * 1000.0 / cell)), 2)
    net = fvm.Network(p, nx, nx)
    r = fvm.solve_steady(p, cell_mm=cell)
    T = r.T[: p.board.layers].ravel()
    w = np.asarray(net.Qw[0]).ravel()[: T.size]
    return float((w * (T - r.ambient)).sum() / w.sum()), float(r.t_max - r.ambient), float(r.balance_error)
