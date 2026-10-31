#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file edge_image.py
@brief The image of an insulated straight edge in the lattice kernel of a via footprint (candidate correction of study S1), and the restriction of a footprint to the cells on the board.
@details Background (research/point-via-convergence): a via is a conductor joined to the planes by Peaceman wells of conductance G_c = 2 pi S / ln(r_eff / r_t), where r_eff is the
         lattice effective radius of its footprint (weights w on cells) and r_t = exp(-1/4) r_v the target radius. The lattice carries the sheet outside the footprint, so the wall of
         an insulated edge acts through the lattice automatically: on a cell-centred grid whose edge lies on a cell face the discrete solution is the sum of the footprint and its
         mirror image about the face. But the discrete image sits at the mirror of the CELL centres, not of the via: a via 0.16 mm from the edge in a 1 mm cell has its true image at
         0.32 mm and the grid image at 1.0 mm. The mean potential of the footprint differs by (I / 2 pi S) ln(D_lat / D_true), with
         * ln D_lat / dx = (pi / 2)(P_img - kappa), P_img = sum_ab w_a w_b A(x_a - x'_b) (A the lattice potential kernel, x' the mirror image of the cell centre b about the wall),
         * D_true = 2 max(delta, r_v), delta the distance from the via centre to the wall.
         The well must therefore carry the extra term c = ln(D_lat / D_true): G_c = 2 pi S / (ln(r_eff / r_t) + c). For a corner (two walls) the sum runs over the two
         single images and the diagonal image (D_true = 2 sqrt(delta_x^2 + delta_y^2)). The correction is a hypothesis of this study; `scripts/study_edge_distance.py` tests it
         against the resolved reference.
         `restrict_to_board` keeps only footprint cells with cover > 0, weighted by the cover, and `fold_into_grid` moves the weight that falls outside the grid to the mirror cell.
"""

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "point-via-convergence", "lib"))
import lattice                                                              # noqa: E402


def a_cont(di, dj):
    """!
    @brief Potential kernel of the five-point lattice at real-valued offsets (bilinear interpolation of the exact values at integer offsets).
    @param di Offset along rows in lattice units (array or float).
    @param dj Offset along columns in lattice units.
    @return numpy.ndarray of A(di, dj); equal to `lattice.a_of` where the offsets are integers.
    """
    di = np.asarray(di, dtype=float)
    dj = np.asarray(dj, dtype=float)
    i0, j0 = np.floor(di + 1e-9), np.floor(dj + 1e-9)
    fi, fj = di - i0, dj - j0
    i0, j0 = i0.astype(int), j0.astype(int)
    a00 = lattice.a_of(i0, j0)
    a10 = lattice.a_of(i0 + 1, j0)
    a01 = lattice.a_of(i0, j0 + 1)
    a11 = lattice.a_of(i0 + 1, j0 + 1)
    return (1 - fi) * (1 - fj) * a00 + fi * (1 - fj) * a10 + (1 - fi) * fj * a01 + fi * fj * a11


def centres(weights, dx, origin=0.0):
    """!
    @brief Positions of the cell centres of a footprint.
    @param weights dict {(i, j): w} (i row = y, j column = x).
    @param dx Cell size in m.
    @param origin Lower edge of cell 0 in m (0 for cell-centred volumes, -dx/2 for node-centred ones).
    @return tuple (keys, w, X, Y) with arrays of the weights and the centre coordinates in m.
    """
    keys = list(weights)
    w = np.array([weights[k] for k in keys], dtype=float)
    X = origin + (np.array([k[1] for k in keys], dtype=float) + 0.5) * dx
    Y = origin + (np.array([k[0] for k in keys], dtype=float) + 0.5) * dx
    return keys, w, X, Y


def mirror(X, Y, wall):
    """!
    @brief Mirror image of points about a wall.
    @param X x coordinates in m.
    @param Y y coordinates in m.
    @param wall tuple (axis, position) with axis "x" (a wall at x = position) or "y".
    @return tuple (X', Y').
    """
    axis, p = wall
    return (2.0 * p - X, Y) if axis == "x" else (X, 2.0 * p - Y)


def image_energy(weights, dx, origin, images):
    """!
    @brief P_img = sum_ab w_a w_b A(x_a - x'_b) for one image of the footprint.
    @param weights dict {(i, j): w}.
    @param dx Cell size in m.
    @param origin Lower edge of cell 0 in m.
    @param images List of walls applied in turn to the footprint (one wall: the single image; two walls: the diagonal image).
    @return float, in lattice units.
    """
    _, w, X, Y = centres(weights, dx, origin)
    Xi, Yi = X, Y
    for wall in images:
        Xi, Yi = mirror(Xi, Yi, wall)
    di = (Y[:, None] - Yi[None, :]) / dx
    dj = (X[:, None] - Xi[None, :]) / dx
    return float(w @ a_cont(di, dj) @ w)


def log_image_distance(weights, dx, origin, images):
    """!
    @brief ln(D_lat) for the image of a footprint, D_lat in metres.
    @param weights dict {(i, j): w}.
    @param dx Cell size in m.
    @param origin Lower edge of cell 0 in m.
    @param images Walls of the image (see image_energy).
    @return float ln(D_lat / 1 m), D_lat = dx exp((pi / 2)(P_img - kappa)).
    """
    p = image_energy(weights, dx, origin, images)
    return math.log(dx) + math.pi / 2.0 * (p - lattice.KAPPA)


def well_correction(weights, via_xy, r_via, dx, origin, walls):
    """!
    @brief The extra term c = sum ln(D_lat / D_true) over the images of a via next to insulated straight walls.
    @param weights dict {(i, j): w} footprint of the via (already restricted to the board).
    @param via_xy Via centre (x, y) in m.
    @param r_via Drill radius in m (the true distance is clipped at this value: a via cut by the edge).
    @param dx Cell size in m.
    @param origin Lower edge of cell 0 in m.
    @param walls List of (axis, position) of the walls that matter (at most two of different axes; with two, the diagonal image is added).
    @return float c (0 for no wall).
    """
    if not walls:
        return 0.0
    x, y = via_xy
    delta = [abs((x if axis == "x" else y) - p) for axis, p in walls]
    c = 0.0
    for wall, d in zip(walls, delta):
        c += log_image_distance(weights, dx, origin, [wall]) - math.log(2.0 * max(d, r_via))
    if len(walls) == 2:                                                       # the corner: the diagonal image, distance 2 sqrt(dx^2 + dy^2)
        d2 = math.hypot(delta[0], delta[1])
        c += log_image_distance(weights, dx, origin, list(walls)) - math.log(2.0 * max(d2, r_via))
    return c


def well_conductance_image(s_sheet, r_eff, r_target, c):
    """!
    @brief Peaceman well with the edge term: 2 pi S / (ln(r_eff / r_t) + c).
    @param s_sheet Sheet conductance of the layer at the via in W/K.
    @param r_eff Lattice effective radius of the footprint in m.
    @param r_target Radius the well must reproduce in m.
    @param c Edge term from `well_correction`.
    @return float in W/K (infinite when the denominator is not positive: the footprint already lowers the resistance more than the geometry allows).
    """
    den = math.log(r_eff / r_target) + c
    return math.inf if den <= 0.0 else 2.0 * math.pi * s_sheet / den


def restrict_to_board(weights, cover, ny, nx):
    """!
    @brief Keep the footprint cells that are on the grid and on the board, weighted by the cover, and renormalise.
    @param weights dict {(i, j): w}.
    @param cover Array (ny, nx) of the fraction of every cell on the board (None: all ones).
    @param ny Rows of the grid.
    @param nx Columns of the grid.
    @return dict {(i, j): w} with weights summing to 1; empty when no cell is on the board.
    """
    out = {}
    for (i, j), x in weights.items():
        if not (0 <= i < ny and 0 <= j < nx):
            continue
        f = 1.0 if cover is None else float(cover[i, j])
        if f > 0.0:
            out[(i, j)] = x * f
    tot = sum(out.values())
    return {k: v / tot for k, v in out.items()} if tot > 0 else {}


def fold_into_grid(weights, ny, nx):
    """!
    @brief Move the weight that lies outside the grid to the mirror cell about the nearest grid edge (the cell-centred image of a cut footprint), then renormalise.
    @param weights dict {(i, j): w} (cells may be outside 0..ny-1, 0..nx-1).
    @param ny Rows of the grid.
    @param nx Columns of the grid.
    @return dict {(i, j): w} on the grid.
    """
    def fold(k, n):
        if k < 0:
            k = -1 - k
        if k >= n:
            k = 2 * n - 1 - k
        return min(max(k, 0), n - 1)

    out = {}
    for (i, j), x in weights.items():
        key = (fold(i, ny), fold(j, nx))
        out[key] = out.get(key, 0.0) + x
    tot = sum(out.values())
    return {k: v / tot for k, v in out.items()}
