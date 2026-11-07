#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cutcell_exact.py
@brief Exact geometry of the cells that an outline cuts (area, centroid, face apertures) by clipping, instead of the 8 x 8 and 16 x 16 point sampling.
@details The program samples the board cover 8 x 8 per cell (`geometry.BOARD_SAMPLES`), so the area of a turned board is off by a few parts in a thousand and
         jumps with the position of the edge (a straight edge gives covers that are multiples of 1/8). Here every cut cell is clipped against the polygon
         (`geometry.clip_polygon`, Sutherland-Hodgman against the convex cell box: exact for any subject polygon) and the area and centroid come from the clipped polygon;
         the aperture of a face is the length of the face that has board on both sides, found from the crossings of the outline with the line of the face (exact).
         The same function names and the same result keys as `cutcell.cut_geometry_fast` (cover, xc, yc, ax, ay, cut), so it is a drop-in replacement.
         `exact_cover(...)` has the signature of `Board.cover` and can replace it for the duration of a block (`using_exact_cover`) to measure what an exact cover does to the
         volumes and the films of the program itself.
"""

import contextlib
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pcbthermal import geometry                                           # noqa: E402
from pcbthermal.geometry import points_in_polygon, edge_length_per_cell, clip_polygon, polygon_area_signed   # noqa: E402


def _cut_cells(poly, nx, ny, dx, dy):
    """!
    @brief Boolean map of the cells that the outline crosses (a corner test plus the edge length, which catches slivers).
    @param poly Outline (n, 2) in metres.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @return (cut, centre_in): the cut map and the map of cell centres inside the polygon.
    """
    cx, cy = np.meshgrid(np.arange(nx + 1) * dx, np.arange(ny + 1) * dy)
    corner = points_in_polygon(cx, cy, poly)
    ins = corner[:-1, :-1].astype(int) + corner[:-1, 1:] + corner[1:, :-1] + corner[1:, 1:]
    cut = ((ins > 0) & (ins < 4)) | (edge_length_per_cell(poly, nx, ny, dx, dy) > 0)
    ccx, ccy = np.meshgrid((np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dy)
    return cut, points_in_polygon(ccx, ccy, poly)


def _clip_area_centroid(poly, x0, y0, x1, y1):
    """!
    @brief Area and centroid of the part of the polygon inside one cell box.
    @param poly Outline (n, 2) in metres.
    @param x0 Left of the box.
    @param y0 Bottom of the box.
    @param x1 Right of the box.
    @param y1 Top of the box.
    @return (area, cx, cy) with the centroid in metres (the box centre when the area is zero).
    """
    c = clip_polygon(poly, np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]))
    if len(c) < 3:
        return 0.0, 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    x, y = c[:, 0], c[:, 1]
    xn, yn = np.roll(x, -1), np.roll(y, -1)
    cr = x * yn - xn * y
    a = 0.5 * cr.sum()
    if abs(a) < 1e-30:
        return 0.0, 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    return abs(a), float(((x + xn) * cr).sum() / (6 * a)), float(((y + yn) * cr).sum() / (6 * a))


def _inside_length(poly, vertical, pos, lo, hi):
    """!
    @brief Length of the segment (a vertical line x = pos from y = lo to hi, or a horizontal line y = pos from x = lo to hi) that lies inside the polygon.
    @param poly Outline (n, 2) in metres.
    @param vertical True for a vertical segment.
    @param pos The x (vertical) or y (horizontal) of the segment.
    @param lo Start along the segment.
    @param hi End along the segment.
    @return Length in metres.
    """
    p = np.asarray(poly, dtype=float)
    a, b = p, np.roll(p, -1, axis=0)
    u0, u1 = (a[:, 0], b[:, 0]) if vertical else (a[:, 1], b[:, 1])         # the coordinate that is fixed along the segment
    w0, w1 = (a[:, 1], b[:, 1]) if vertical else (a[:, 0], b[:, 0])         # the coordinate along it
    # An edge crosses the line when its ends are on different sides (half-open, so a vertex on the line counts once)
    cross = ((u0 <= pos) & (u1 > pos)) | ((u1 <= pos) & (u0 > pos))
    t = (pos - u0[cross]) / (u1[cross] - u0[cross])
    w = np.sort(w0[cross] + t * (w1[cross] - w0[cross]))
    if len(w) < 2:
        return 0.0
    # Even-odd: the intervals (w0, w1), (w2, w3), ... are inside
    total = 0.0
    for k in range(0, len(w) - 1, 2):
        total += max(0.0, min(w[k + 1], hi) - max(w[k], lo))
    return total


def cut_geometry_exact(poly, nx, ny, dx, dy, m=None):
    """!
    @brief Cover, centroid and face apertures of every cell by exact clipping (the keys of `cutcell.cut_geometry_fast`).
    @param poly Outline polygon (n, 2) in metres.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param m Unused (the sampling resolution of the sampled version).
    @return dict with cover, xc, yc, ax (ny, nx - 1), ay (ny - 1, nx) and cut.
    """
    poly = np.asarray(poly, dtype=float)
    cut, centre_in = _cut_cells(poly, nx, ny, dx, dy)
    cover = np.where(cut, 0.0, centre_in.astype(float))
    xc = (np.arange(nx)[None, :] + 0.5) * dx * np.ones((ny, 1))
    yc = (np.arange(ny)[:, None] + 0.5) * dy * np.ones((1, nx))
    for i, j in zip(*np.nonzero(cut)):
        a, cx, cy = _clip_area_centroid(poly, j * dx, i * dy, (j + 1) * dx, (i + 1) * dy)
        cover[i, j] = a / (dx * dy)
        xc[i, j], yc[i, j] = cx, cy
    # x faces: between column j and j + 1, the length with board on both sides of the face, over dy
    tiny = 1e-6 * min(dx, dy)
    ax = (centre_in[:, :-1] & centre_in[:, 1:]).astype(float) * (~cut[:, :-1] & ~cut[:, 1:])
    for i, j in zip(*np.nonzero(cut[:, :-1] | cut[:, 1:])):
        xf = (j + 1) * dx
        # Both sides: the intervals just left and just right of the face, intersected by taking the shorter inside length (exact for a face the outline crosses once)
        lo, hi = i * dy, (i + 1) * dy
        ax[i, j] = min(_inside_length(poly, True, xf - tiny, lo, hi), _inside_length(poly, True, xf + tiny, lo, hi)) / dy
    ay = (centre_in[:-1] & centre_in[1:]).astype(float) * (~cut[:-1] & ~cut[1:])
    for i, j in zip(*np.nonzero(cut[:-1] | cut[1:])):
        yf = (i + 1) * dy
        lo, hi = j * dx, (j + 1) * dx
        ay[i, j] = min(_inside_length(poly, False, yf - tiny, lo, hi), _inside_length(poly, False, yf + tiny, lo, hi)) / dx
    return {"cover": cover, "xc": xc, "yc": yc, "ax": ax, "ay": ay, "cut": cut}


def exact_cover(self, nx, ny, dx, dy, samples=None, minimum=0.01):
    """!
    @brief `Board.cover` with the exact area of every cut cell (replaces the 8 x 8 sampling); cells below `minimum` are taken as off the board, as in the program.
    @param self Board.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param samples Unused.
    @param minimum Smallest coverage kept.
    @return Array (ny, nx).
    """
    if self.outline is None:
        return np.ones((ny, nx))
    c = cut_geometry_exact(self.outline, nx, ny, dx, dy)["cover"]
    return np.where(c >= minimum, c, 0.0)


@contextlib.contextmanager
def using_exact_cover():
    """!
    @brief Replace `Board.cover` by the exact cover for a block (the volumes, films and sheets of the program then use the exact area of every cut cell).
    @return Context manager.
    """
    from pcbthermal import model
    original = model.Board.cover
    model.Board.cover = exact_cover
    try:
        yield
    finally:
        model.Board.cover = original
