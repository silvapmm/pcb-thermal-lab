#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file solid_gridline.py
@brief Candidate for the mirror asymmetry of the 3D solid with a via on a grid line: the point footprint of a via that sits exactly on a line between cells is split
       equally over the cells that share the line (the program is not edited; viawell.tuned_footprint is wrapped in memory).
@details viawell.tuned_footprint returns, for a via whose target radius is below that of a point sink on the grid (a cell coarser than about 1.5 drill diameters), the cell
         floor((x - origin) / dx), floor((y - origin_y) / dy). For a via exactly on a line the floor picks the cell to the right and above, and the mirror image of the board
         picks the cell to the left of the mirrored line, so the two boards differ by one cell. For any other position floor commutes with a mirror and nothing is wrong.
         The wrapper changes ONLY a via within 1e-9 of a line: 1 cell becomes 2 (on one line) or 4 (at a crossing) with equal weights, restricted to the board cells.
         Use: with solid_gridline.using(): ... run the 3D solid ...
"""

import contextlib
import math

from pcbthermal import viawell

_ORIG = viawell.tuned_footprint
TOL = 1e-9          # Distance to a line in cells that counts as 'on the line'


def _split(cx, cy, dx, dy, origin, origin_y):
    """!
    @brief Cells that share the lines a point sits on (1, 2 or 4 cells, equal weights).
    @param cx Point x in m.
    @param cy Point y in m.
    @param dx Cell size in x in m.
    @param dy Cell size in y in m.
    @param origin Lower x edge of cell 0 in m.
    @param origin_y Lower y edge of row 0 in m.
    @return dict {(i, j): w}.
    """
    fx, fy = (cx - origin) / dx, (cy - origin_y) / dy
    js = [math.floor(fx)]
    is_ = [math.floor(fy)]
    if abs(fx - round(fx)) < TOL:
        js = [round(fx) - 1, round(fx)]
    if abs(fy - round(fy)) < TOL:
        is_ = [round(fy) - 1, round(fy)]
    w = 1.0 / (len(js) * len(is_))
    return {(i, j): w for i in is_ for j in js}


def tuned_footprint(cx, cy, r_via, dx, origin, cover, dy=None, origin_y=None):
    """!
    @brief viawell.tuned_footprint with the split of a point footprint on a grid line.
    @param cx Via centre x in m.
    @param cy Via centre y in m.
    @param r_via Drill radius in m.
    @param dx Cell size in m.
    @param origin Lower edge of cell 0 in m.
    @param cover Array (ny, nx) of the board share of each cell.
    @param dy Cell size along y in m (None = dx).
    @param origin_y Lower y edge of row 0 in m (None = origin scaled by dy / dx).
    @return dict {(i, j): w}.
    """
    w = _ORIG(cx, cy, r_via, dx, origin, cover, dy, origin_y)
    if len(w) != 1:
        return w
    dy_ = dx if dy is None else dy
    oy = origin * dy_ / dx if origin_y is None else origin_y
    ny, nx = cover.shape
    point = (min(max(int(math.floor((cy - oy) / dy_)), 0), ny - 1), min(max(int(math.floor((cx - origin) / dx)), 0), nx - 1))
    if next(iter(w)) != point:          # the board-part fallback of a via off the board: leave it
        return w
    cells = {k: v for k, v in _split(cx, cy, dx, dy_, origin, oy).items() if 0 <= k[0] < ny and 0 <= k[1] < nx}
    out = viawell.restrict_to_board(cells, cover)
    return out or w


@contextlib.contextmanager
def using():
    """!
    @brief Apply the wrapper for the duration of a with block.
    @return context manager.
    """
    viawell.tuned_footprint = tuned_footprint
    try:
        yield
    finally:
        viawell.tuned_footprint = _ORIG
