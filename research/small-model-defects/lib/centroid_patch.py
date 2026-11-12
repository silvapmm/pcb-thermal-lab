#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file centroid_patch.py
@brief Candidate for the mirror asymmetry of the Lumped model: the rise that the other heaters cause at the centroid of a heater is read by interpolating the
       distance raster at the centroid, not from the cell that floor() picks (the program is not edited; the source of lumped.solve_steady is rewritten in memory).
@details lumped.solve_steady adds to the own peak of heater j the rise of every other heater i at the centroid of j, read as _radial(ri, ri["dist"][ij], ...) with
         ij = (floor(cy / dy), floor(cx / dx)): the CELL that holds the centroid, whose centre is up to half a cell away from it, always towards the larger x and y.
         A mirror image of the board puts the same centroid on the other side of the cell, so the two boards differ. The patch reads the distance at the centroid by a
         bilinear interpolation of the cell-centre raster, which commutes with a mirror of a board whose sides are a whole number of cells.
         Use: with centroid_patch.using(): ... run the Lumped model ...
"""

import contextlib
import inspect
import textwrap

import numpy as np

from pcbthermal import lumped

_ORIG = lumped.solve_steady


def interp_at(raster, cx, cy, dx, dy):
    """!
    @brief Bilinear interpolation of a cell-centred raster at a point (clamped at the border cells).
    @param raster Array (ny, nx) of values at the cell centres ((j + 0.5) dx, (i + 0.5) dy).
    @param cx Point x in m.
    @param cy Point y in m.
    @param dx Cell size in x in m.
    @param dy Cell size in y in m.
    @return float.
    """
    ny, nx = raster.shape
    fx = min(max(cx / dx - 0.5, 0.0), nx - 1.0)
    fy = min(max(cy / dy - 0.5, 0.0), ny - 1.0)
    j0, i0 = int(np.floor(fx)), int(np.floor(fy))
    j1, i1 = min(j0 + 1, nx - 1), min(i0 + 1, ny - 1)
    tx, ty = fx - j0, fy - i0
    return float((1 - tx) * (1 - ty) * raster[i0, j0] + tx * (1 - ty) * raster[i0, j1] + (1 - tx) * ty * raster[i1, j0] + tx * ty * raster[i1, j1])


def _patched():
    """!
    @brief solve_steady with the interpolated read of the other heaters at the centroid.
    @return function.
    """
    src = textwrap.dedent(inspect.getsource(_ORIG))
    old = 'theta_j += _radial(ri, ri["dist"][ij], ri["theta"][hj.layer])'
    new = 'theta_j += _radial(ri, _interp_at(ri["dist"], cj[0], cj[1], net.dx, net.dy), ri["theta"][hj.layer])'
    if old not in src:
        raise RuntimeError("lumped.solve_steady changed: update the patch")
    ns = dict(vars(lumped))
    ns["_interp_at"] = interp_at
    exec(compile(src.replace(old, new), "<centroid_patch>", "exec"), ns)
    return ns["solve_steady"]


@contextlib.contextmanager
def using():
    """!
    @brief Apply the patch for the duration of a with block.
    @return context manager.
    """
    lumped.solve_steady = _patched()
    try:
        yield
    finally:
        lumped.solve_steady = _ORIG
