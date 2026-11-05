#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cutcell.py
@brief The geometry of the cells that the outline of a board cuts: board fraction, centroid of the board part, aperture of every cell face.
@details A cell that the outline cuts holds a strip or a corner of board. A cut-cell finite-volume scheme needs three things that the program's
         area weighting does not use: where the board part of the cell is (its centroid, where the temperature of the cell lives), how much of
         every face between two cells is board (the aperture, which is the conducting cross-section of the link), and the depth of the board
         part behind the outline (the path of the heat to the edge). Everything is found by sampling every cell on an M x M lattice with the
         program's own point-in-polygon test (`geometry.points_in_polygon`); M = 16 gives the cover to 1/256 and the centroid to a fraction of a percent of a cell.
"""

import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pcbthermal.geometry import points_in_polygon, edge_length_per_cell     # noqa: E402


def cut_geometry(poly, nx, ny, dx, dy, m=16):
    """!
    @brief Board fraction, centroid and face apertures of every cell of a grid for a polygon outline.
    @param poly Outline polygon (n, 2) in metres.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param m Samples per cell side.
    @return dict with cover (ny, nx), xc and yc (ny, nx) absolute centroid of the board part in metres (the cell centre where there is none),
            ax (ny, nx-1) and ay (ny-1, nx) the board fraction of the face between a cell and its right (upper) neighbour.
    """
    # Lattice of sample points over the whole grid
    xs = (np.arange(nx * m) + 0.5) * (dx / m)
    ys = (np.arange(ny * m) + 0.5) * (dy / m)
    X, Y = np.meshgrid(xs, ys)
    inside = points_in_polygon(X, Y, poly)
    cnt = inside.reshape(ny, m, nx, m).sum(axis=(1, 3)).astype(float)
    cover = cnt / (m * m)
    with np.errstate(divide="ignore", invalid="ignore"):
        xc = np.where(cnt > 0, (X * inside).reshape(ny, m, nx, m).sum(axis=(1, 3)) / cnt, (np.arange(nx)[None, :] + 0.5) * dx)
        yc = np.where(cnt > 0, (Y * inside).reshape(ny, m, nx, m).sum(axis=(1, 3)) / cnt, (np.arange(ny)[:, None] + 0.5) * dy)
    # Aperture of the face between column j and j+1: samples along the face that are on the board on both sides of it
    tiny = 1e-4 * min(dx, dy)
    xf = np.arange(1, nx) * dx
    Yf, Xf = np.meshgrid(ys, xf, indexing="ij")
    both = points_in_polygon(Xf - tiny, Yf, poly) & points_in_polygon(Xf + tiny, Yf, poly)
    ax = both.reshape(ny, m, nx - 1).mean(axis=1)
    yf = np.arange(1, ny) * dy
    Yg, Xg = np.meshgrid(yf, xs, indexing="ij")
    both = points_in_polygon(Xg, Yg - tiny, poly) & points_in_polygon(Xg, Yg + tiny, poly)
    ay = both.reshape(ny - 1, nx, m).mean(axis=2)
    return {"cover": cover, "xc": xc, "yc": yc, "ax": ax, "ay": ay}


def cut_geometry_fast(poly, nx, ny, dx, dy, m=16):
    """!
    @brief Same result as `cut_geometry`, sampling only the cells the outline crosses and the faces next to them.
    @details `cut_geometry` tests m x m points in every cell, which costs (cells x m^2 x polygon sides): 7 million points and 128 sides for a 168 x 168 grid
             of a round board. A cell is cut when the outline crosses it (`geometry.edge_length_per_cell > 0`) or its four corners are not all on the same
             side; every other cell is whole (cover 1, centroid at the centre) or empty. Faces are sampled only where a neighbour is cut; the others have
             aperture one between two whole cells and zero otherwise. The cost grows with the perimeter (cells along the edge), not with the area.
    @param poly Outline polygon (n, 2) in metres.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param m Samples per cell side in the cut cells.
    @return dict as `cut_geometry` (cover, xc, yc, ax, ay), plus `cut` (Boolean, the cells that were sampled).
    """
    # Corner test: a cell whose four corners are not all inside or all outside is cut; the edge length catches the thin slivers the corners miss
    cx, cy = np.meshgrid(np.arange(nx + 1) * dx, np.arange(ny + 1) * dy)
    corner = points_in_polygon(cx, cy, poly)
    ins = corner[:-1, :-1].astype(int) + corner[:-1, 1:] + corner[1:, :-1] + corner[1:, 1:]
    cut = ((ins > 0) & (ins < 4)) | (edge_length_per_cell(poly, nx, ny, dx, dy) > 0)
    # Cells that are not cut: whole when the centre is inside
    ccx, ccy = np.meshgrid((np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dy)
    centre_in = points_in_polygon(ccx, ccy, poly)
    cover = np.where(cut, 0.0, centre_in.astype(float))
    xc, yc = ccx.copy(), ccy.copy()
    ii, jj = np.nonzero(cut)
    if ii.size:
        off = (np.arange(m) + 0.5) / m
        sx = (jj[:, None, None] + off[None, None, :]) * dx + 0 * off[None, :, None]       # (n, m, m): x of the samples
        sy = (ii[:, None, None] + off[None, :, None]) * dy + 0 * off[None, None, :]
        inside = points_in_polygon(sx, sy, poly)
        cnt = inside.sum(axis=(1, 2)).astype(float)
        cover[ii, jj] = cnt / (m * m)
        with np.errstate(divide="ignore", invalid="ignore"):
            xc[ii, jj] = np.where(cnt > 0, (sx * inside).sum(axis=(1, 2)) / cnt, xc[ii, jj])
            yc[ii, jj] = np.where(cnt > 0, (sy * inside).sum(axis=(1, 2)) / cnt, yc[ii, jj])
    tiny = 1e-4 * min(dx, dy)
    off = (np.arange(m) + 0.5) / m
    # x faces (between column j and j + 1): sampled where either neighbour is cut, else both whole
    ax = (centre_in[:, :-1] & centre_in[:, 1:]).astype(float) * (~cut[:, :-1] & ~cut[:, 1:])
    fi, fj = np.nonzero(cut[:, :-1] | cut[:, 1:])
    if fi.size:
        px = (fj[:, None] + 1) * dx + 0 * off[None, :]
        py = (fi[:, None] + off[None, :]) * dy
        ax[fi, fj] = (points_in_polygon(px - tiny, py, poly) & points_in_polygon(px + tiny, py, poly)).mean(axis=1)
    ay = (centre_in[:-1] & centre_in[1:]).astype(float) * (~cut[:-1] & ~cut[1:])
    fi, fj = np.nonzero(cut[:-1] | cut[1:])
    if fi.size:
        px = (fj[:, None] + off[None, :]) * dx
        py = (fi[:, None] + 1) * dy + 0 * off[None, :]
        ay[fi, fj] = (points_in_polygon(px, py - tiny, poly) & points_in_polygon(px, py + tiny, poly)).mean(axis=1)
    return {"cover": cover, "xc": xc, "yc": yc, "ax": ax, "ay": ay, "cut": cut}
