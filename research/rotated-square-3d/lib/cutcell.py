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

from pcbthermal.geometry import points_in_polygon                            # noqa: E402


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
