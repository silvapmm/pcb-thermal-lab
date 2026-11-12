#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_outline_mask.py
@brief Review of fix/imported-copper-outline-mask: the mean rise of a heater on turned squares and a disc with imported copper, at several cells, on a chosen tree.
@details A 30 mm box, two layers; the board is a 20 mm square turned by 0, 10, 22.5, 35 or 45 degrees, or a 20 mm disc of 360 vertices. Imported copper at a 0.05 mm
         pixel (4 x 4 sub-samples): on the top layer stripes 1 mm wide every 2 mm plus a 7 mm pad, on the bottom a plane, both held 1.2 mm inside the edge and turned
         with the board; a 4 mm heater of 1 W at the centre, turned with the board; h_top = h_bottom = 10, h_side 10 and 200 W/m2K. A turned board is the same physics
         as the aligned one, so the converged rise does not depend on the angle (up to the antialiased raster of the turned stripes), and with the laminate rule off
         (`norule`) the aligned board can be checked against the independent solver `indep_two_sheets.py`.

         Run from the root of a checkout (PCBT_TREE names the tree whose `pcbthermal` is measured, default the checkout itself):
         `PCBT_TREE=<tree> .venv/bin/python releases/2.7.0/final-opinion/scripts/study_outline_mask.py <rule|norule> <cells, e.g. 2,1,0.5,0.25,0.125> <out.json>`
         Environment: VARIANT=imported (default) or drawn (the same copper as zones), PATTERN=0 for full copper, HS=10,200 for the edge coefficients.
         Prints one line per run: h_side, angle (or disc), cell, mean rise of the heater (K), hottest rise (K), heat-balance error, seconds.
"""

import json
import math
import os
import sys
import time

sys.path.insert(0, os.environ.get("PCBT_TREE", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))))
import numpy as np                                                          # noqa: E402

from pcbthermal import Problem, copper, fvm, laminate                       # noqa: E402

W = 30.0             # box side, mm
C = 15.0             # centre of the board, mm
A = 20.0             # side of the square (diameter of the disc), mm
INSET = 1.2          # copper held inside the edge, mm
PIX = 0.05           # pixel of the imported masks, mm


def to_board(x, y, ang):
    """!
    @brief Coordinates of the box (mm) in the frame of the turned board.
    @param x Box x in mm (array).
    @param y Box y in mm (array).
    @param ang Turn of the board in degrees.
    @return Tuple (u, v) in mm.
    """
    a = math.radians(ang)
    u = (x - C) * math.cos(a) + (y - C) * math.sin(a)
    v = -(x - C) * math.sin(a) + (y - C) * math.cos(a)
    return u, v


def to_box(pts, ang):
    """!
    @brief Points of the board frame (mm) in the box.
    @param pts List of (u, v) in mm.
    @param ang Turn of the board in degrees.
    @return List of [x, y] in mm.
    """
    a = math.radians(ang)
    return [[C + u * math.cos(a) - v * math.sin(a), C + u * math.sin(a) + v * math.cos(a)] for u, v in pts]


def copper_masks(ang, disc, pattern=True, sub=4):
    """!
    @brief The two coverage rasters (rows from the top, 0..255) of the turned copper.
    @param ang Turn in degrees.
    @param disc True for the disc board.
    @param pattern False for full copper on the top layer.
    @param sub Sub-samples per pixel side.
    @return Tuple (top, bottom) of uint8 arrays.
    """
    n = int(round(W / PIX))
    t = (np.arange(n * sub) + 0.5) / sub * PIX
    X, Y = np.meshgrid(t, W - t)                                            # rows from the top of the box
    u, v = to_board(X, Y, ang)
    lim = A / 2 - INSET
    inside = (np.hypot(u, v) <= lim) if disc else ((np.abs(u) <= lim) & (np.abs(v) <= lim))
    stripes = np.floor((v + lim) / 1.0) % 2 == 0
    pad = (np.abs(u) <= 3.5) & (np.abs(v) <= 3.5)
    top = inside & (stripes | pad) if pattern else inside

    def pack(m):
        """!
        @brief Average the sub-samples into 0..255 coverage.
        @param m Boolean array of sub-samples.
        @return uint8 array.
        """
        return np.round(255 * m.reshape(n, sub, n, sub).mean(axis=(1, 3))).astype(np.uint8)
    return pack(top), pack(inside)


def outline(ang, disc):
    """!
    @brief The board outline in mm.
    @param ang Turn in degrees.
    @param disc True for the 360-vertex disc.
    @return List of [x, y].
    """
    if disc:
        th = np.linspace(0, 2 * math.pi, 360, endpoint=False)
        return [[C + A / 2 * math.cos(q), C + A / 2 * math.sin(q)] for q in th]
    return to_box([(-A / 2, -A / 2), (A / 2, -A / 2), (A / 2, A / 2), (-A / 2, A / 2)], ang)


def problem(ang, disc, h_side, imported=True, pattern=True):
    """!
    @brief The board of the study.
    @param ang Turn in degrees.
    @param disc True for the disc.
    @param h_side Edge coefficient in W/m2K.
    @param imported True for imported masks, False for the same copper drawn as zones (squares only).
    @param pattern False for full copper on the top layer.
    @return Problem.
    """
    p = Problem.new(W, W, 2, h_side=h_side)
    p.board.h_top = 10.0
    p.board.h_bottom = 10.0
    p.add_heater(1, 1.0, polygon=to_box([(-2, -2), (2, -2), (2, 2), (-2, 2)], ang), name="U")
    p.set_outline(outline(ang, disc))
    if imported:
        top, bot = copper_masks(ang, disc, pattern)
        p.imported = copper.imported_from_rasters([top, bot], PIX, "faces")
        return p
    lim = A / 2 - INSET

    def rect(u0, v0, u1, v1):
        """!
        @brief A turned rectangle of the board frame.
        @param u0 Left in mm.
        @param v0 Bottom in mm.
        @param u1 Right in mm.
        @param v1 Top in mm.
        @return Polygon in box coordinates.
        """
        return to_box([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], ang)
    p.add_zone(2, polygon=rect(-lim, -lim, lim, lim))
    if pattern:
        k = 0
        while -lim + 2 * k < lim:
            p.add_zone(1, polygon=rect(-lim, -lim + 2 * k, lim, min(-lim + 2 * k + 1, lim)))
            k += 1
        p.add_zone(1, polygon=rect(-3.5, -3.5, 3.5, 3.5))
    else:
        p.add_zone(1, polygon=rect(-lim, -lim, lim, lim))
    return p


def heater_mean(p, cell):
    """!
    @brief Mean rise of the heater (its own area weights) and hottest rise.
    @param p Problem.
    @param cell Cell in mm.
    @return Tuple (mean rise K, hottest rise K, heat-balance error).
    """
    nx = max(int(round(p.board.width * 1000.0 / cell)), 2)
    net = fvm.Network(p, nx, nx)
    r = fvm.solve_steady(p, cell_mm=cell)
    T = r.T[: p.board.layers].ravel()
    w = np.asarray(net.Qw[0]).ravel()[: T.size]
    return float((w * (T - r.ambient)).sum() / w.sum()), float(r.t_max - r.ambient), float(r.balance_error)


def main():
    """!
    @brief Run the cases given on the command line and write the JSON of the results.
    @return None.
    """
    lam = sys.argv[1]
    cells = [float(c) for c in sys.argv[2].split(",")]
    variant = os.environ.get("VARIANT", "imported")
    pattern = os.environ.get("PATTERN", "1") == "1"
    cases = [(a, False) for a in (0, 10, 22.5, 35, 45)] + ([(0, True)] if variant == "imported" else [])
    out = {}
    ctx = laminate.using(0.4, 1) if lam == "norule" else None               # one sub-gap: the laminate rule off (two sheets, as the independent solver)
    if ctx:
        ctx.__enter__()
    for h_side in [float(x) for x in os.environ.get("HS", "10,200").split(",")]:
        for ang, disc in cases:
            p = problem(ang, disc, h_side, imported=variant != "drawn", pattern=pattern)
            for c in cells:
                t0 = time.time()
                m, tm, be = heater_mean(p, c)
                key = f"{h_side}|{'disc' if disc else ang}|{c}"
                out[key] = (m, tm, be)
                print(h_side, "disc" if disc else ang, c, round(m, 4), round(tm, 4), f"{be:.1e}", round(time.time() - t0, 1), flush=True)
    with open(sys.argv[3], "w") as fh:
        json.dump(out, fh)


if __name__ == "__main__":
    main()
