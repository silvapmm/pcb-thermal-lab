"""!
@file zone_shapely.py
@brief The union of the zones computed once as polygons (a polygon boolean union by GEOS through shapely) and the exact area of every cell: the alternative to the sub-sample lattice, and an exact reference for the fill field.
@details Question answered: what would the exact union cost, and how far is the lattice from it? For solid zones the fill of a cell is area(union of the zones that cover the cell) / area(cell). For zones of different fill the
         largest fill at every point is a layer cake: with the distinct fills f_1 > f_2 > ... > f_n (f_{n+1} = 0), R_k = union of the zones with fill >= f_k, the fill of a point is sum_k (f_k - f_{k+1}) [point in R_k],
         so the cell fill is sum_k (f_k - f_{k+1}) area(R_k in cell) / area(cell). Cells fully inside or fully outside a region are classified without cutting (prepared geometry); only the cells the boundary crosses are intersected.
         shapely is a research tool here (installed in the project's .venv for the Gerber research); it is NOT a dependency of the program and the proposal does not use it.
"""

import sys

import numpy as np

from paths import OUT

try:
    import shapely
except ImportError:                                  # not in the project's venv: `pip install --no-deps --target research/zone-union/out/pylib shapely` (git-ignored)
    sys.path.insert(0, str(OUT / "pylib"))
    import shapely
from shapely.geometry import Polygon                 # noqa: E402


def region_fraction(geom, nx, ny, dx, dy):
    """!
    @brief Exact fraction of every cell covered by a (multi)polygon.
    @param geom shapely geometry in metres.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width (m).
    @param dy Cell height (m).
    @return numpy.ndarray (ny, nx).
    """
    out = np.zeros((ny, nx))
    if geom.is_empty:
        return out
    x0, y0, x1, y1 = geom.bounds
    j0, j1 = max(int(np.floor(x0 / dx)), 0), min(int(np.ceil(x1 / dx)), nx)
    i0, i1 = max(int(np.floor(y0 / dy)), 0), min(int(np.ceil(y1 / dy)), ny)
    if j1 <= j0 or i1 <= i0:
        return out
    jj, ii = np.meshgrid(np.arange(j0, j1), np.arange(i0, i1))
    boxes = shapely.box(jj.ravel() * dx, ii.ravel() * dy, (jj.ravel() + 1) * dx, (ii.ravel() + 1) * dy)
    shapely.prepare(geom)
    inside = shapely.contains(geom, boxes)
    touch = shapely.intersects(geom, boxes) & ~inside
    area = np.zeros(len(boxes))
    area[inside] = dx * dy
    if touch.any():
        area[touch] = shapely.area(shapely.intersection(boxes[touch], geom))
    out[i0:i1, j0:j1] = (area / (dx * dy)).reshape(ii.shape)
    return out


def exact_fill(zones, layers, nx, ny, dx, dy):
    """!
    @brief Exact cell fill of every layer under the rule "largest fill at every point" (the limit of the lattice for an infinite number of samples).
    @param zones Iterable of zones with polygon (metres), layer and fill.
    @param layers Number of layers.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width (m).
    @param dy Cell height (m).
    @return numpy.ndarray (layers, ny, nx).
    """
    out = np.zeros((layers, ny, nx))
    for layer in range(layers):
        mine = [z for z in zones if z.layer == layer and z.fill > 0]
        levels = sorted({z.fill for z in mine}, reverse=True)
        for k, f in enumerate(levels):
            nxt = levels[k + 1] if k + 1 < len(levels) else 0.0
            # Region of the points whose largest fill is at least f; make_valid repairs a polygon that touches itself
            polys = [shapely.make_valid(Polygon(z.polygon)) for z in mine if z.fill >= f]
            region = shapely.union_all(polys)
            out[layer] += (f - nxt) * region_fraction(region, nx, ny, dx, dy)
    return out
