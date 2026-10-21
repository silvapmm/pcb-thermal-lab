"""!
@file geometry.py
@brief Polygon helpers and cell-coverage rasterisation for the thermal solvers.

All coordinates are in metres, with the origin at the bottom-left corner of the
board. This module depends only on NumPy so it can run headless.
"""

import numpy as np


def polygon_area(poly):
    """!
    @brief Area of a simple polygon using the shoelace formula.
    @param poly Array-like of shape (n, 2) with the vertices in metres.
    @return Area in square metres (always positive).
    """
    p = np.asarray(poly, dtype=float)
    x, y = p[:, 0], p[:, 1]
    # Shoelace: sum of x_i*y_{i+1} - x_{i+1}*y_i, over a closed polygon
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def polygon_centroid(poly):
    """!
    @brief Area centroid of a simple polygon.
    @param poly Array-like of shape (n, 2) with the vertices in metres.
    @return Tuple (cx, cy) in metres. Falls back to the vertex mean for a degenerate polygon.
    """
    p = np.asarray(poly, dtype=float)
    x, y = p[:, 0], p[:, 1]
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    cross = x * y1 - x1 * y
    a = 0.5 * cross.sum()
    if abs(a) < 1e-30:
        return float(x.mean()), float(y.mean())
    cx = ((x + x1) * cross).sum() / (6.0 * a)
    cy = ((y + y1) * cross).sum() / (6.0 * a)
    return float(cx), float(cy)


def points_in_polygon(px, py, poly):
    """!
    @brief Vectorised even-odd (ray casting) point-in-polygon test.
    @param px Array of x coordinates (any shape), metres.
    @param py Array of y coordinates (same shape as px), metres.
    @param poly Array-like of shape (n, 2) with the polygon vertices.
    @return Boolean array with the shape of px; True where the point is inside.
    """
    p = np.asarray(poly, dtype=float)
    n = len(p)
    inside = np.zeros(px.shape, dtype=bool)
    j = n - 1
    # Loop over polygon edges only; each iteration is vectorised over all points
    for i in range(n):
        xi, yi = p[i]
        xj, yj = p[j]
        # Edge crosses the horizontal ray if the endpoints straddle py
        straddle = (yi > py) != (yj > py)
        # x coordinate where the edge crosses the ray (guard against division by zero)
        with np.errstate(divide="ignore", invalid="ignore"):
            x_cross = (xj - xi) * (py - yi) / (yj - yi) + xi
        inside ^= straddle & (px < x_cross)
        j = i
    return inside


def coverage_fraction(poly, nx, ny, dx, dy, samples=4):
    """!
    @brief Fraction of every grid cell that is covered by a polygon.
    @details Each cell is sub-sampled on a samples x samples lattice; only the cells in the
             polygon bounding box are evaluated, so small polygons are cheap.
    @param poly Polygon vertices (n, 2) in metres.
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param samples Sub-samples per cell side (accuracy of the fraction is about 1/samples^2).
    @return Array of shape (ny, nx) with values in [0, 1].
    """
    p = np.asarray(poly, dtype=float)
    cov = np.zeros((ny, nx))
    # Index range of the cells touched by the polygon bounding box (clipped to the board)
    j0 = max(int(np.floor(p[:, 0].min() / dx)), 0)
    j1 = min(int(np.ceil(p[:, 0].max() / dx)), nx)
    i0 = max(int(np.floor(p[:, 1].min() / dy)), 0)
    i1 = min(int(np.ceil(p[:, 1].max() / dy)), ny)
    if j1 <= j0 or i1 <= i0:
        return cov
    ni, nj = i1 - i0, j1 - j0
    # Sub-sample centres inside every cell of the bounding box
    sub = (np.arange(samples) + 0.5) / samples
    xs = (j0 + (np.arange(nj)[:, None] + sub[None, :])) * dx   # (nj, samples)
    ys = (i0 + (np.arange(ni)[:, None] + sub[None, :])) * dy   # (ni, samples)
    xs = xs.reshape(-1)
    ys = ys.reshape(-1)
    gx, gy = np.meshgrid(xs, ys)
    mask = points_in_polygon(gx, gy, p)
    # Average the samples of each cell: (ni, s, nj, s) -> (ni, nj)
    frac = mask.reshape(ni, samples, nj, samples).mean(axis=(1, 3))
    cov[i0:i1, j0:j1] = frac
    return cov


def cell_index_of_point(x, y, nx, ny, dx, dy):
    """!
    @brief Index of the grid cell that contains a point (clipped to the board).
    @param x X coordinate in metres.
    @param y Y coordinate in metres.
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @return Tuple (i, j) = (row, column) of the cell.
    """
    j = min(max(int(x // dx), 0), nx - 1)
    i = min(max(int(y // dy), 0), ny - 1)
    return i, j


def edge_length_per_cell(poly, nx, ny, dx, dy):
    """!
    @brief Length of the polygon outline that lies inside every grid cell (the perimeter that exchanges heat through the board edge).
    @details Every edge is sampled at steps of a tenth of the smaller cell side and each sample adds its step length to the cell that contains it;
             a point on a cell border is counted in the cell above or to the right, so the total is the perimeter to within a fraction of a percent.
    @param poly Closed polygon (n, 2) in metres (the last vertex joins the first).
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @return Array (ny, nx) of lengths in metres.
    """
    p = np.asarray(poly, dtype=float)
    out = np.zeros((ny, nx))
    step = min(dx, dy) / 10.0
    for a, b in zip(p, np.roll(p, -1, axis=0)):
        length = float(np.hypot(*(b - a)))
        if length <= 0:
            continue
        n = max(int(np.ceil(length / step)), 1)
        t = (np.arange(n) + 0.5) / n                             # Midpoints of the n pieces
        x, y = a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
        j = np.clip((x // dx).astype(int), 0, nx - 1)
        i = np.clip((y // dy).astype(int), 0, ny - 1)
        np.add.at(out, (i, j), length / n)
    return out


def polygon_is_simple(poly):
    """!
    @brief True if the polygon does not cross itself (no two non-adjacent edges intersect).
    @param poly Array-like (n, 2).
    @return bool.
    """
    p = np.asarray(poly, dtype=float)
    n = len(p)

    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])

    for i in range(n):
        a, b = p[i], p[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i or (j + 1) % n == i or (i + 1) % n == j:
                continue                                         # Adjacent edges share a vertex
            c, d = p[j], p[(j + 1) % n]
            if ccw(a, b, c) * ccw(a, b, d) < 0 and ccw(c, d, a) * ccw(c, d, b) < 0:
                return False
    return True


def nearest_active_cell(active, x, y, dx, dy, offset=0.5):
    """!
    @brief The active (on the board) cell or node nearest to a point.
    @param active Boolean array (ny, nx).
    @param x X coordinate in metres.
    @param y Y coordinate in metres.
    @param dx Spacing along x in metres.
    @param dy Spacing along y in metres.
    @param offset 0.5 for cell centres, 0 for nodes at the grid points.
    @return Tuple (i, j) = (row, column).
    """
    ii, jj = np.nonzero(active)
    d = np.hypot((jj + offset) * dx - x, (ii + offset) * dy - y)
    k = int(np.argmin(d))
    return int(ii[k]), int(jj[k])
