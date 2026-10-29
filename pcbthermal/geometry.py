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


def _sample_mask(poly, nx, ny, dx, dy, samples):
    """!
    @brief Which sub-samples of the cells in the bounding box of a polygon lie inside it.
    @param poly Polygon vertices (n, 2) in metres.
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param samples Sub-samples per cell side.
    @return None when the polygon touches no cell, else (i0, i1, j0, j1, mask) with mask of shape (ni, samples, nj, samples), True inside.
    """
    p = np.asarray(poly, dtype=float)
    # Index range of the cells touched by the polygon bounding box (clipped to the board)
    j0 = max(int(np.floor(p[:, 0].min() / dx)), 0)
    j1 = min(int(np.ceil(p[:, 0].max() / dx)), nx)
    i0 = max(int(np.floor(p[:, 1].min() / dy)), 0)
    i1 = min(int(np.ceil(p[:, 1].max() / dy)), ny)
    if j1 <= j0 or i1 <= i0:
        return None
    ni, nj = i1 - i0, j1 - j0
    # Sub-sample centres inside every cell of the bounding box
    sub = (np.arange(samples) + 0.5) / samples
    xs = (j0 + (np.arange(nj)[:, None] + sub[None, :])) * dx   # (nj, samples)
    ys = (i0 + (np.arange(ni)[:, None] + sub[None, :])) * dy   # (ni, samples)
    gx, gy = np.meshgrid(xs.reshape(-1), ys.reshape(-1))
    return i0, i1, j0, j1, points_in_polygon(gx, gy, p).reshape(ni, samples, nj, samples)


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
    cov = np.zeros((ny, nx))
    got = _sample_mask(poly, nx, ny, dx, dy, samples)
    if got is None:
        return cov
    i0, i1, j0, j1, mask = got
    # Average the samples of each cell: (ni, s, nj, s) -> (ni, nj)
    cov[i0:i1, j0:j1] = mask.mean(axis=(1, 3))
    return cov


def zone_fill(zones, layers, nx, ny, dx, dy, samples=4):
    """!
    @brief Copper fill of every layer: the union of its zones, taken at every sub-sample point and then averaged over the cell.
    @details Zones of one layer overlap or touch; where they do, the fill of a point is the largest fill of the zones that contain it. Taking that
             maximum per cell (the older rule) lost the copper of two zones that meet inside a cell: each covered half of it and the cell kept only
             the larger half. The union per sample point keeps both halves (hatched zones keep their fill inside the polygon).
    @param zones Iterable of zones with polygon (metres), layer (0-based) and fill (0 to 1).
    @param layers Number of board layers.
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param samples Sub-samples per cell side.
    @return Array of shape (layers, ny, nx) with values in [0, 1].
    """
    out = np.zeros((layers, ny, nx))
    for layer in range(layers):
        mine = [z for z in zones if z.layer == layer]
        if not mine:
            continue
        fine = np.zeros((ny, samples, nx, samples))       # Fill of every sub-sample point of this layer
        for z in mine:
            got = _sample_mask(z.polygon, nx, ny, dx, dy, samples)
            if got is None:
                continue
            i0, i1, j0, j1, mask = got
            window = fine[i0:i1, :, j0:j1, :]
            np.maximum(window, mask * z.fill, out=window)
        out[layer] = fine.mean(axis=(1, 3))
    return out


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
    @details Every edge is sampled at steps of a tenth of the smaller cell side and each sample adds its step length to the cell that contains it.
             Every sample is first nudged a thousandth of the smaller cell side towards the inside of the polygon: a side that lies exactly on a
             grid line would otherwise be given (by the floor and by rounding) to the cell outside the board, and the callers, which keep only
             the cells on the board, would drop its edge loss. The nudge is far above floating-point noise and far below a cell, so nothing else
             moves. The total is the perimeter to within a fraction of a percent, whichever way the outline is placed on the grid.
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
    nudge = 1e-3 * min(dx, dy)                                   # Distance moved towards the inside of the polygon
    # Orientation: positive signed area = counter-clockwise, so the inside is on the left of every side
    sign = 1.0 if np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]) >= 0 else -1.0
    for a, b in zip(p, np.roll(p, -1, axis=0)):
        length = float(np.hypot(*(b - a)))
        if length <= 0:
            continue
        # Unit vector pointing into the board, perpendicular to the side
        inward = sign * np.array([-(b[1] - a[1]), b[0] - a[0]]) / length
        n = max(int(np.ceil(length / step)), 1)
        t = (np.arange(n) + 0.5) / n                             # Midpoints of the n pieces
        x = a[0] + t * (b[0] - a[0]) + nudge * inward[0]
        y = a[1] + t * (b[1] - a[1]) + nudge * inward[1]
        j = np.clip((x // dx).astype(int), 0, nx - 1)
        i = np.clip((y // dy).astype(int), 0, ny - 1)
        np.add.at(out, (i, j), length / n)
    return out


def edge_length_on_board(poly, nx, ny, dx, dy, active):
    """!
    @brief Length of the polygon outline inside every cell that is on the board, with the whole perimeter kept.
    @details `edge_length_per_cell` gives the outline to the cells it crosses; where it crosses a cell taken as off the board (a sliver of
             board that none of the cover sub-samples falls in), the callers would drop that length. It is moved instead to the nearest cell
             on the board (centre distance; split equally between equally near cells, so that mirror images stay mirror images), the cell
             that conducts the heat of the sliver in the model. Without this a slanted or curved outline lost 2 to 6 % of its perimeter at
             every cell size (a disc, an ellipse, a rotated square), so the edge loss did not converge with the grid.
    @param poly Closed polygon (n, 2) in metres (the last vertex joins the first).
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param active Boolean array (ny, nx), True for the cells on the board.
    @return Array (ny, nx) of lengths in metres, zero off the board; it adds up to the perimeter when any cell is on the board.
    """
    out = edge_length_per_cell(poly, nx, ny, dx, dy)
    active = np.asarray(active, dtype=bool)
    lost = (out > 0) & ~active
    if not lost.any() or not active.any():
        return out * active
    for i, j in zip(*np.nonzero(lost)):
        # Search the 5 x 5 window around the cell first (the nearest board cell is almost always a neighbour); fall back to the whole grid
        i0, j0 = max(i - 2, 0), max(j - 2, 0)
        ci, cj = np.nonzero(active[i0:i + 3, j0:j + 3])
        ci, cj = (ci + i0, cj + j0) if ci.size else np.nonzero(active)
        d = np.hypot((cj - j) * dx, (ci - i) * dy)
        best = d <= d.min() * (1.0 + 1e-9)                      # Every equally near cell gets an equal share
        np.add.at(out, (ci[best], cj[best]), out[i, j] / int(best.sum()))
        out[i, j] = 0.0
    return out * active


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


def rounded_rectangle(width, height, radius, segments=8):
    """!
    @brief Outline of a rectangle with rounded corners, as a polygon (each corner is an arc of `segments` edges).
    @param width Width of the rectangle (any unit).
    @param height Height of the rectangle (same unit).
    @param radius Corner radius (same unit); limited to half of the shorter side.
    @param segments Edges per quarter circle (8 gives a deviation of 0.5 % of the radius from the true arc).
    @return List of [x, y], counter-clockwise from the lower-left corner's start.
    """
    r = min(float(radius), width / 2.0, height / 2.0)
    pts = []
    # Corner centres and the start angle of the arc of each corner, counter-clockwise from the lower-right corner
    for cx, cy, a0 in ((width - r, r, -90.0), (width - r, height - r, 0.0), (r, height - r, 90.0), (r, r, 180.0)):
        for k in range(segments + 1):
            a = np.radians(a0 + 90.0 * k / segments)
            pts.append([cx + r * np.cos(a), cy + r * np.sin(a)])
    return pts


def nearest_edge_point(poly, point):
    """!
    @brief Closest point of a polygon's boundary to a point.
    @param poly Array-like (n, 2) of vertices (any length unit).
    @param point (x, y) in the same unit.
    @return Tuple (edge, q, distance): index i of the edge from vertex i to vertex i+1, the closest point q on it (array of 2) and its distance to `point`.
    """
    p = np.asarray(poly, dtype=float)
    pt = np.asarray(point, dtype=float)
    best = (0, p[0], float("inf"))
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]
        ab = b - a
        n2 = float(np.dot(ab, ab))
        # Projection parameter clamped to the segment (a degenerate edge falls back to its start)
        t = 0.0 if n2 == 0.0 else min(max(float(np.dot(pt - a, ab)) / n2, 0.0), 1.0)
        q = a + t * ab
        d = float(np.hypot(*(pt - q)))
        if d < best[2]:
            best = (i, q, d)
    return best


def insert_vertex(poly, point):
    """!
    @brief Add a vertex to a polygon on the edge closest to a point, so the shape does not change until the new vertex is moved.
    @param poly Array-like (n, 2) of vertices.
    @param point (x, y) near the wanted edge, same unit.
    @return Tuple (new vertices as an (n+1, 2) array, index of the new vertex).
    """
    p = np.asarray(poly, dtype=float)
    edge, q, _ = nearest_edge_point(p, point)
    return np.insert(p, edge + 1, q, axis=0), edge + 1


def nearest_vertex(poly, point):
    """!
    @brief Vertex of a polygon closest to a point.
    @param poly Array-like (n, 2) of vertices.
    @param point (x, y) in the same unit.
    @return Tuple (index, distance).
    """
    p = np.asarray(poly, dtype=float)
    d = np.hypot(p[:, 0] - point[0], p[:, 1] - point[1])
    k = int(np.argmin(d))
    return k, float(d[k])
