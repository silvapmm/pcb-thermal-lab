#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file geometry.py
@brief Polygon helpers and cell-coverage rasterisation for the thermal solvers.

All coordinates are in metres, with the origin at the bottom-left corner of the
board. This module depends only on NumPy so it can run headless.
"""

import math

import numpy as np


def polygon_self_intersects(poly):
    """!
    @brief Whether the outline of a polygon crosses itself (two of its edges that are not neighbours cut each other).
    @details The fill of the program follows the even-odd rule, so a crossing outline leaves the crossed part empty (a pentagram is filled
             between its arms, not in its centre), and the Gerber format does not allow such a contour. The test is exact for proper crossings;
             edges that only touch at an end point or run along each other are not reported.
    @param poly Array-like (n, 2) of vertices; the closing edge from the last to the first vertex is included.
    @return bool.
    """
    # One implementation for both questions (the box-sweep test of polygon_is_simple): the all-pairs loop that stood here cost 3.7 s at 20 000 vertices
    return not polygon_is_simple(poly)


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


# Sub-samples per cell side for the sampled rules that remain: the part weights of a pair of polygons that cannot be clipped exactly (a polygon
# that crosses itself, or a concave part of more than _EAR_MAX_VERTICES vertices on a concave outline). The board cover (FVM, FDM, 3D solid) and the weights of the usual part are exact (`exact_coverage`) since
# fix/exact-board-cover; before it ONE lattice was shared by the cover and the weights (a 4 x 4 board cover against 8 x 8 part weights gave an
# edge-shift scatter of 2.95 K at 1 mm on a small T; 8 x 8 everywhere gave 1.47 K; the exact cover gives about 0.65 K).
BOARD_SAMPLES = 8


# Cells whose exact coverage is closer than this to 0 or 1 are snapped to it: the column sums below carry a rounding noise of a few 1e-10 of a cell
_EXACT_SNAP = 1e-9


def exact_coverage(poly, nx, ny, dx, dy):
    """!
    @brief Exact fraction of every grid cell that a simple polygon covers (no sampling).
    @details For a polygon traversed once, the length of the vertical section that lies inside it and between two horizontal grid lines is
             the sum over the edges that the vertical line crosses of +/- (clamp(y_edge, lower, upper) - lower), the sign being that of the
             direction of the edge (the lower edges of a counter-clockwise polygon go to the right, the upper ones to the left). Integrated
             over a grid column, the cell covers follow from the differences of one function of the grid lines,
             Phi(Y) = sum_e s_e integral of min(y_e(x), Y) dx, which is piecewise linear in Y per edge piece. Each (edge, column) piece
             contributes Y * width below its lowest point, a constant above its highest point (both accumulated by cumulative sums over the
             grid lines) and an explicit trapezoid-minus-triangle value only on the grid lines it crosses, so the work is that of the cells
             the outline cuts, vectorised, and a board of 1000 vertices on a 0.25 mm grid takes milliseconds. A zero-width bridge (two
             opposite edges on the same line, as the clip of a concave polygon leaves) cancels exactly. The same area as clipping each cell
             with `clip_polygon`, and exactly the polygon area (checked against analytic areas in the tests).
    @param poly Polygon vertices (n, 2) in metres, either orientation, not crossing itself.
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @return Array (ny, nx) with the covered fraction in [0, 1]; values within 1e-9 of 0 or 1 are snapped to them.
    """
    p = np.asarray(poly, dtype=float)
    out = np.zeros((ny, nx))
    if len(p) < 3:
        return out
    orient = np.sign(polygon_area_signed(p))
    if orient == 0:
        return out
    x0, y0 = p[:, 0], p[:, 1]
    x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    # Edges to the right are the lower ones of a counter-clockwise polygon (inside above them): sign -1; to the left +1; a vertical edge adds nothing
    sgn = np.where(x1 > x0, -orient, orient)
    left = np.minimum(x0, x1)
    right = np.maximum(x0, x1)
    yl = np.where(x0 <= x1, y0, y1)                                    # Height at the left end of the edge
    yr = np.where(x0 <= x1, y1, y0)                                    # Height at the right end
    keep = (right > left) & (right > 0.0) & (left < nx * dx)
    sgn, left, right, yl, yr = sgn[keep], left[keep], right[keep], yl[keep], yr[keep]
    if sgn.size == 0:
        return out
    # One piece per (edge, column): the columns an edge spans, with the x range of the edge inside each one
    c0 = np.maximum(np.floor(left / dx).astype(np.int64), 0)
    c1 = np.minimum(np.floor(right / dx).astype(np.int64), nx - 1)
    cnt = np.maximum(c1 - c0 + 1, 0)
    e = np.repeat(np.arange(sgn.size), cnt)
    col = np.repeat(c0, cnt) + (np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt))
    xa = np.maximum(left[e], col * dx)
    xb = np.minimum(right[e], (col + 1) * dx)
    w = xb - xa
    ok = w > 0.0
    e, col, xa, xb, w = e[ok], col[ok], xa[ok], xb[ok], w[ok]
    slope = (yr[e] - yl[e]) / (right[e] - left[e])
    ya = yl[e] + slope * (xa - left[e])
    yb = yl[e] + slope * (xb - left[e])
    s = sgn[e]
    lo, hi = np.minimum(ya, yb), np.maximum(ya, yb)
    # Grid lines Y_k = k dy, k = 0..ny: k <= klo lie at or below the piece, k >= khi at or above it, those between cross it
    klo = np.floor(lo / dy).astype(np.int64)
    khi = np.maximum(np.ceil(hi / dy).astype(np.int64), klo + 1)
    phi = np.zeros((ny + 1, nx))
    # Below the piece: min(y, Y) = Y, so the sum is Y_k times the signed widths of the pieces with klo >= k (a reverse cumulative sum)
    low = np.zeros((ny + 1, nx))
    sel = klo >= 0
    np.add.at(low, (np.minimum(klo[sel], ny), col[sel]), s[sel] * w[sel])
    low = np.cumsum(low[::-1], axis=0)[::-1]
    phi += (np.arange(ny + 1) * dy)[:, None] * low
    # Above the piece: min(y, Y) = y, a constant from khi on (a forward cumulative sum)
    high = np.zeros((ny + 1, nx))
    sel = khi <= ny
    np.add.at(high, (np.maximum(khi[sel], 0), col[sel]), (s * w * 0.5 * (ya + yb))[sel])
    phi += np.cumsum(high, axis=0)
    # On the lines that cross the piece: integral of y minus integral of max(y - Y, 0), the second being a trapezoid or a triangle
    k_from = np.maximum(klo + 1, 0)
    k_to = np.minimum(khi - 1, ny)
    n = np.maximum(k_to - k_from + 1, 0)
    if n.sum():
        r = np.repeat(np.arange(n.size), n)
        k = np.repeat(k_from, n) + (np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n))
        Y = k * dy
        pq = ya[r] - Y, yb[r] - Y
        pp, qq = np.maximum(pq[0], 0.0), np.maximum(pq[1], 0.0)
        span = np.abs(pq[0]) + np.abs(pq[1])
        mixed = pq[0] * pq[1] < 0.0
        # Mixed signs: a triangle of height (positive end)^2 / (|p| + |q|) / 2 per unit of width; same signs: the trapezoid (zero when both are below)
        tri = np.where(mixed, (pp * pp + qq * qq) / np.where(span > 0.0, 2.0 * span, 1.0), 0.5 * (pp + qq))
        np.add.at(phi, (k, col[r]), s[r] * w[r] * (0.5 * (ya[r] + yb[r]) - tri))
    out = np.diff(phi, axis=0) / (dx * dy)
    out = np.clip(out, 0.0, 1.0)
    out[out < _EXACT_SNAP] = 0.0
    out[out > 1.0 - _EXACT_SNAP] = 1.0
    return out


def _line_lengths(poly, n_lines, spacing, n_seg, seg, axis, shift):
    """!
    @brief Inside length over each segment of each interior grid line of one family (helper of `face_apertures`).
    @details All the crossings of the outline edges with the lines are found at once (each edge gives the lines its span covers, half-open so that a vertex on a line counts once),
             sorted by (line, position), given the signs +1 (enter) and -1 (leave) by their rank on the line (even-odd), and the inside length below every grid node,
             F(y) = sum over the crossings below y of s_k (y - w_k), is evaluated with prefix sums; the fraction of a segment is the difference of F over it.
    @param poly Polygon (n, 2) in metres.
    @param n_lines Interior grid lines of the family (j = 1 .. n_lines).
    @param spacing Distance between the lines in metres.
    @param n_seg Segments per line (cells along the line).
    @param seg Segment length in metres.
    @param axis 0: vertical lines x = j spacing (segments along y); 1: horizontal lines.
    @param shift Offset of the evaluated line from j spacing in metres.
    @return Array (n_seg, n_lines) of fractions in [0, 1].
    """
    a = np.asarray(poly, dtype=float)
    b = np.roll(a, -1, axis=0)
    u0, u1 = (a[:, 0], b[:, 0]) if axis == 0 else (a[:, 1], b[:, 1])
    w0, w1 = (a[:, 1], b[:, 1]) if axis == 0 else (a[:, 0], b[:, 0])
    lo, hi = np.minimum(u0, u1), np.maximum(u0, u1)
    # Candidate lines of every edge with one line of slack: the exact half-open test below decides on the same position for every edge
    j0 = np.floor((lo - shift) / spacing).astype(np.int64)
    j1 = np.ceil((hi - shift) / spacing).astype(np.int64)
    cnt = np.clip(j1 - j0 + 1, 0, None)
    e = np.repeat(np.arange(len(a)), cnt)
    j = j0[e] + (np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt))
    pos = j * spacing + shift
    keep = (j >= 1) & (j <= n_lines) & (((u0[e] <= pos) & (u1[e] > pos)) | ((u1[e] <= pos) & (u0[e] > pos)))
    e, j, pos = e[keep], j[keep], pos[keep]
    w = w0[e] + (pos - u0[e]) / (u1[e] - u0[e]) * (w1[e] - w0[e])
    order = np.lexsort((w, j))
    j, w = j[order], w[order]
    out = np.zeros((n_seg, n_lines))
    if not len(j):
        return out
    start = np.r_[0, np.flatnonzero(np.diff(j)) + 1]
    stop = np.r_[start[1:], len(j)]
    rank = np.arange(len(j)) - np.repeat(start, stop - start)
    s = np.where(rank % 2 == 0, 1.0, -1.0)          # Even-odd: the crossings enter and leave in turn along the line
    nodes = np.arange(n_seg + 1) * seg
    for a_, b_ in zip(start, stop):                  # One vectorised evaluation per crossed line
        ww, ss = w[a_:b_], s[a_:b_]
        k = np.searchsorted(ww, nodes, side="left")
        c1 = np.r_[0.0, np.cumsum(ss)]
        c2 = np.r_[0.0, np.cumsum(ss * ww)]
        out[:, j[a_] - 1] = np.diff(nodes * c1[k] - c2[k]) / seg
    return np.clip(out, 0.0, 1.0)


# Bounds on the work an outline can ask of the cut-cell and edge-distance code (a project file is hostile: 20 000 long zigzag edges would otherwise need
# tens of millions of pieces or crossings and several GB). Normal outlines (a few thousand edges, a few thousand cells long) are three orders below them.
OUTLINE_MAX_PIECES = 2_000_000
OUTLINE_MAX_CROSSINGS = 10_000_000


def outline_crossings(poly, spacing):
    """!
    @brief Upper bound of the crossings of an outline with the grid lines of a cell: the total extent of its edges along x and y over the cell.
    @param poly Outline polygon (n, 2) in metres; non-finite coordinates raise.
    @param spacing Cell size in metres (positive).
    @return float Number of grid lines the edges span, summed over both families.
    @throws ValueError If a coordinate is not finite.
    """
    p = np.asarray(poly, dtype=float)
    if not np.isfinite(p).all():
        raise ValueError("the board outline has a coordinate that is not a finite number")
    d = np.abs(p - np.roll(p, -1, axis=0))
    return float(d.sum() / max(spacing, 1e-300))


def face_apertures(poly, nx, ny, dx, dy, cover=None):
    """!
    @brief Open fraction of every interior face of the grid: the part of the face (the cell side shared by two neighbours) that lies on the board.
    @details This is the length of the outline-inside part of a grid-line segment over the segment (the aperture of a cut-cell scheme: Johansen and Colella 1998 eq. 15 to 16;
             Barrett, Fogelson and Griffith 2022 eq. 10 to 11). It is built from the sorted crossings of the outline with the grid lines, the same signed-sum construction that
             `exact_coverage` integrates over a column, and costs about the perimeter over the cell: 20 000 vertices on a 0.25 mm grid take about 0.1 s and a few MB. An outline edge
             that lies on a grid line has board on one side only, so each line is evaluated just left and just right of it (1e-9 of a cell) and the smaller value is kept: such a
             face gets 0, which is right (nothing crosses the outline). Values within 1e-9 of 0 or 1 are snapped to them, and with `cover` given, a face between two whole cells
             (cover 1 both) is exactly 1, so that an outline on the grid lines reproduces the links of a rectangle bit for bit.
    @param poly Outline polygon (n, 2) in metres, either orientation, not crossing itself.
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param cover Optional board cover (ny, nx) of the cells (see `exact_coverage`).
    @return Tuple (ax, ay): ax (ny, nx - 1) the open fraction of the face between cell (i, j) and (i, j + 1), ay (ny - 1, nx) between (i, j) and (i + 1, j).
    @throws ValueError If a coordinate is not finite or the outline crosses more than OUTLINE_MAX_CROSSINGS grid lines (too many edges for this cell).
    """
    p = np.asarray(poly, dtype=float)
    if len(p) >= 3 and outline_crossings(p, min(dx, dy)) > OUTLINE_MAX_CROSSINGS:
        raise ValueError("the board outline has too many long edges for this cell size (more than 1e7 crossings of the grid lines): use a coarser cell or a simpler outline")
    ax, ay = np.zeros((ny, max(nx - 1, 0))), np.zeros((max(ny - 1, 0), nx))
    if len(p) >= 3:
        ex, ey = 1e-9 * dx, 1e-9 * dy
        if nx > 1:
            ax = np.minimum(_line_lengths(p, nx - 1, dx, ny, dy, 0, -ex), _line_lengths(p, nx - 1, dx, ny, dy, 0, ex))
        if ny > 1:
            ay = np.minimum(_line_lengths(p, ny - 1, dy, nx, dx, 1, -ey), _line_lengths(p, ny - 1, dy, nx, dx, 1, ey)).T
    for a in (ax, ay):
        a[a < _EXACT_SNAP] = 0.0
        a[a > 1.0 - _EXACT_SNAP] = 1.0
    if cover is not None:
        c = np.asarray(cover)
        ax[(c[:, :-1] >= 1.0) & (c[:, 1:] >= 1.0)] = 1.0
        ay[(c[:-1] >= 1.0) & (c[1:] >= 1.0)] = 1.0
    return ax, ay


def signed_distance_to_outline(poly, x, y):
    """!
    @brief Signed distance from points to the closest point of a polygon outline (positive inside, negative outside).
    @details The outline is cut into pieces of at most 1/2000 of the bounding-box diagonal, a k-d tree of their mid-points gives the 6 nearest pieces of every point, the exact
             point-to-segment distance to those 6 is taken, and the answer is accepted when no other piece can be nearer (its mid-point is farther than the candidate distance
             plus half a piece); the few points that fail this test are measured against every segment. The sign is that of the side of the nearest segment (the orientation is
             known from the signed area); a point whose nearest point is a vertex of the outline gets the even-odd test of `points_in_polygon`, which a vertex needs (at a
             reflex corner the side of one segment is not the side of the board).
    @param poly Closed polygon (n, 2) in metres.
    @param x X of the points (1-D array, metres).
    @param y Y of the points (1-D array, metres).
    @return Array of distances in metres, shape of x.
    @throws ValueError If a coordinate of the outline is not finite.
    """
    from scipy.spatial import cKDTree
    p = np.asarray(poly, dtype=float)
    if not np.isfinite(p).all():
        raise ValueError("the board outline has a coordinate that is not a finite number")
    x = np.atleast_1d(np.asarray(x, dtype=float))
    y = np.atleast_1d(np.asarray(y, dtype=float))
    out = np.zeros(x.shape)
    if len(x) == 0 or len(p) < 3:
        return out
    a, b = p, np.roll(p, -1, axis=0)
    ab = b - a
    seg_len = np.hypot(ab[:, 0], ab[:, 1])
    # Pieces: every segment cut into equal parts, so that the distance to a mid-point bounds the distance to its piece within half a piece
    diag = float(np.hypot(*(p.max(axis=0) - p.min(axis=0))))
    # The piece count is bounded: a long zigzag outline would otherwise need perimeter / (diag / 2000) pieces (40 million for 20 000 edges of the diagonal);
    # a coarser piece only widens the certified search (more points fall back to the exact test), it never changes the answer
    piece = max(diag / 2000.0, float(seg_len.sum()) / OUTLINE_MAX_PIECES, 1e-12)
    parts = np.maximum(np.ceil(seg_len / piece).astype(np.int64), 1)
    seg_of = np.repeat(np.arange(len(p)), parts)
    k_in = np.arange(parts.sum()) - np.repeat(np.cumsum(parts) - parts, parts)
    pa = a[seg_of] + ab[seg_of] * (k_in / parts[seg_of])[:, None]
    pb = a[seg_of] + ab[seg_of] * ((k_in + 1) / parts[seg_of])[:, None]
    mid = 0.5 * (pa + pb)
    pab = pb - pa
    half = 0.5 * np.hypot(pab[:, 0], pab[:, 1])
    pll = np.maximum((pab ** 2).sum(axis=1), 1e-300)
    pts = np.column_stack([x, y])
    k = int(min(6, len(mid)))
    dm, im = cKDTree(mid).query(pts, k=k)
    dm, im = dm.reshape(len(pts), k), im.reshape(len(pts), k)
    # Exact distance to the k candidate pieces
    t = np.clip(((pts[:, None, 0] - pa[im, 0]) * pab[im, 0] + (pts[:, None, 1] - pa[im, 1]) * pab[im, 1]) / pll[im], 0.0, 1.0)
    d = np.hypot(pts[:, None, 0] - pa[im, 0] - t * pab[im, 0], pts[:, None, 1] - pa[im, 1] - t * pab[im, 1])
    best = d.argmin(axis=1)
    rows = np.arange(len(pts))
    dist, piece_best, t_best = d[rows, best], im[rows, best], t[rows, best]
    # Certified when no piece beyond the k-th can be nearer: its mid-point is at least dm[:, -1] away, so it is at least dm[:, -1] - half away
    bad = (dm[:, -1] - half.max()) < dist if len(mid) > k else np.zeros(len(pts), bool)
    first_piece = np.cumsum(parts) - parts
    for i in np.flatnonzero(bad):
        tt = np.clip(((x[i] - a[:, 0]) * ab[:, 0] + (y[i] - a[:, 1]) * ab[:, 1]) / np.maximum(seg_len ** 2, 1e-300), 0.0, 1.0)
        dd = np.hypot(x[i] - a[:, 0] - tt * ab[:, 0], y[i] - a[:, 1] - tt * ab[:, 1])
        j = int(dd.argmin())
        # The piece and the parameter within it of the nearest point, so that the vertex test below sees an end of the segment (the first piece with
        # the parameter of the whole segment hid the far end: a point nearest to a vertex then got the side of one segment, wrong near a corner)
        kp = int(min(max(np.floor(tt[j] * parts[j]), 0), parts[j] - 1))
        dist[i], piece_best[i], t_best[i] = dd[j], first_piece[j] + kp, tt[j] * parts[j] - kp
    # Side of the nearest segment: the left of the direction a -> b is the inside of a counter-clockwise polygon
    orient = 1.0 if polygon_area_signed(p) >= 0 else -1.0
    sg = seg_of[piece_best]
    cross = ab[sg, 0] * (y - a[sg, 1]) - ab[sg, 1] * (x - a[sg, 0])
    inside = orient * cross > 0
    # A vertex of the outline is where a piece at the end of its segment is nearest at its end (a joint inside a segment lies on a straight line: the side test holds)
    at_start = (k_in[piece_best] == 0) & (t_best <= 0.0)
    at_end = (k_in[piece_best] == parts[sg] - 1) & (t_best >= 1.0)
    vertex = at_start | at_end
    if vertex.any():
        inside[vertex] = points_in_polygon(x[vertex], y[vertex], p)
    return np.where(inside, dist, -dist)


def _sample_mask(poly, nx, ny, dx, dy, samples, clip=None):
    """!
    @brief Which sub-samples of the cells in the bounding box of a polygon lie inside it.
    @param poly Polygon vertices (n, 2) in metres.
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param samples Sub-samples per cell side.
    @param clip Optional second polygon (n, 2) in metres, tested on the very same sample points.
    @return None when the polygon touches no cell, else (i0, i1, j0, j1, mask) with mask of shape (ni, samples, nj, samples), True inside;
            with clip, (i0, i1, j0, j1, mask, clip_mask), the second mask True inside the clip polygon.
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
    shape = (ni, samples, nj, samples)
    inside = points_in_polygon(gx, gy, p).reshape(shape)
    if clip is None:
        return i0, i1, j0, j1, inside
    # The clip polygon on the very same sample points, so that the caller can intersect the two shapes sample by sample
    return i0, i1, j0, j1, inside, points_in_polygon(gx, gy, np.asarray(clip, dtype=float)).reshape(shape)


def coverage_fraction(poly, nx, ny, dx, dy, samples=4):
    """!
    @brief Fraction of every grid cell that is covered by a polygon.
    @details Each cell is sub-sampled on a samples x samples lattice; only the cells in the
             polygon bounding box are evaluated, so small polygons are cheap. When the box holds more than
             _EDGE_ONLY_CELLS cells (a board outline), the full lattice is taken only in the cells an edge touches
             and one sample decides every other cell (`_coverage_edge_cells`, bit-identical to the full lattice).
    @param poly Polygon vertices (n, 2) in metres.
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param samples Sub-samples per cell side (accuracy of the fraction is about 1/samples^2).
    @return Array of shape (ny, nx) with values in [0, 1].
    """
    cov = np.zeros((ny, nx))
    p = np.asarray(poly, dtype=float)
    if len(p) >= 3 and samples > 1:
        # A large polygon (a board outline) is sampled in full only in the cells its edges touch: bit-identical, and 30 to 60 times
        # cheaper in time and memory on a fine grid (a 128-vertex disc on 1000 x 1000 cells: 34 s and 2.6 GB at 8 x 8 for the full lattice)
        j0 = max(int(np.floor(p[:, 0].min() / dx)), 0)
        j1 = min(int(np.ceil(p[:, 0].max() / dx)), nx)
        i0 = max(int(np.floor(p[:, 1].min() / dy)), 0)
        i1 = min(int(np.ceil(p[:, 1].max() / dy)), ny)
        if j1 <= j0 or i1 <= i0:
            return cov
        if (i1 - i0) * (j1 - j0) > _EDGE_ONLY_CELLS:
            cov[i0:i1, j0:j1] = _coverage_edge_cells(p, i0, i1, j0, j1, dx, dy, samples)
            return cov
    got = _sample_mask(poly, nx, ny, dx, dy, samples)
    if got is None:
        return cov
    i0, i1, j0, j1, mask = got
    # Average the samples of each cell: (ni, s, nj, s) -> (ni, nj)
    cov[i0:i1, j0:j1] = mask.mean(axis=(1, 3))
    return cov


# Above this many cells in the bounding box, coverage_fraction samples in full only the cells touched by an edge of the polygon
_EDGE_ONLY_CELLS = 4096


def _coverage_edge_cells(p, i0, i1, j0, j1, dx, dy, samples):
    """!
    @brief Coverage of the cells of a bounding box, with the full sample lattice only in the cells that an edge of the polygon touches.
    @details A cell that no edge touches lies wholly inside or wholly outside the polygon, so all its samples agree and one of them gives
             its value (1.0 or 0.0, which is also the exact mean of its samples). The touched cells are found by walking every edge in steps
             of a quarter of a cell and marking the cells of the steps, then growing the marks by one cell (a step can cross into a
             neighbour); a mark too many only costs a full sampling. The sample points are the very ones of `_sample_mask`, so the result
             is bit-identical to the full lattice.
    @param p Polygon vertices (n, 2) in metres.
    @param i0 First row of the box.
    @param i1 Row after the last of the box.
    @param j0 First column of the box.
    @param j1 Column after the last of the box.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param samples Sub-samples per cell side.
    @return Array (i1 - i0, j1 - j0) with values in [0, 1].
    """
    ni, nj = i1 - i0, j1 - j0
    sub = (np.arange(samples) + 0.5) / samples
    # Cells touched by an edge: walk every edge (the closing one included) in steps of at most a quarter of the smaller cell side
    edge = np.zeros((ni, nj), dtype=bool)
    step = 0.25 * min(dx, dy)
    q = np.vstack([p, p[:1]])
    for (xa, ya), (xb, yb) in zip(q[:-1], q[1:]):
        t = np.linspace(0.0, 1.0, int(math.ceil(math.hypot(xb - xa, yb - ya) / step)) + 2)
        jj = np.clip(np.floor((xa + t * (xb - xa)) / dx).astype(np.int64) - j0, 0, nj - 1)
        ii = np.clip(np.floor((ya + t * (yb - ya)) / dy).astype(np.int64) - i0, 0, ni - 1)
        edge[ii, jj] = True
    # Grow the marks by one cell in the eight directions (rows, then columns)
    grown = edge.copy()
    grown[1:, :] |= edge[:-1, :]
    grown[:-1, :] |= edge[1:, :]
    edge = grown.copy()
    edge[:, 1:] |= grown[:, :-1]
    edge[:, :-1] |= grown[:, 1:]
    # Untouched cells: their first sample point (the same coordinates as in _sample_mask) decides the whole cell
    xs = (j0 + (np.arange(nj) + sub[0])) * dx
    ys = (i0 + (np.arange(ni) + sub[0])) * dy
    gx, gy = np.meshgrid(xs, ys)
    box = points_in_polygon(gx, gy, p).astype(float)
    # Touched cells: the full lattice, averaged like in coverage_fraction (a mean of 0/1 values over samples^2 points is exact)
    ie, je = np.nonzero(edge)
    if ie.size:
        sx = (j0 + (je[:, None] + sub[None, :])) * dx          # (m, samples) along x
        sy = (i0 + (ie[:, None] + sub[None, :])) * dy          # (m, samples) along y
        gx = np.ascontiguousarray(np.broadcast_to(sx[:, None, :], (ie.size, samples, samples)))
        gy = np.ascontiguousarray(np.broadcast_to(sy[:, :, None], (ie.size, samples, samples)))
        box[ie, je] = points_in_polygon(gx, gy, p).mean(axis=(1, 2))
    return box


# Largest concave part that is cut into triangles for the exact weights (ear clipping is quadratic in the vertices); a bigger one is sampled
_EAR_MAX_VERTICES = 400


def _triangulate(poly):
    """!
    @brief Cut a simple polygon into triangles (ear clipping), so that a concave polygon can be clipped exactly by convex pieces.
    @details Collinear and repeated vertices are dropped first (they add no area); a vertex is an ear when its turn has the sign of the polygon and no
             other vertex lies in or on its triangle. The triangles cover the polygon once, so the sum of their exact cell areas is the exact cell area of
             the polygon.
    @param poly Polygon vertices (n, 2) in metres, either orientation, not crossing itself.
    @return list of numpy.ndarray triangles (3, 2) in metres, counter-clockwise, or None when no ear is found (a degenerate polygon).
    """
    p = np.asarray(poly, dtype=float)
    if polygon_area_signed(p) < 0:
        p = p[::-1]
    pts = [tuple(v) for v in p]
    scale = max(float(np.ptp(p[:, 0])), float(np.ptp(p[:, 1])), 1e-30)
    tol = 1e-12 * scale * scale

    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    tris = []
    guard = 0
    while len(pts) > 3 and guard < 4 * len(p) * len(p):
        guard += 1
        n = len(pts)
        # Drop a collinear or repeated vertex: it changes nothing in the polygon
        flat = next((i for i in range(n) if abs(cross(pts[i - 1], pts[i], pts[(i + 1) % n])) <= tol), None)
        if flat is not None:
            del pts[flat]
            continue
        for i in range(n):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
            if cross(a, b, c) <= 0.0:
                continue                                                  # A reflex vertex is never an ear
            # No other vertex in the triangle or on its sides (a vertex on a side would leave a sliver outside the polygon)
            if any(cross(a, b, q) >= -tol and cross(b, c, q) >= -tol and cross(c, a, q) >= -tol
                   for q in pts if q not in (a, b, c)):
                continue
            tris.append(np.array([a, b, c]))
            del pts[i]
            break
        else:
            return None
    if len(pts) == 3 and abs(cross(*pts)) > tol:
        tris.append(np.array(pts))
    return tris


def _part_on_board(poly, outline):
    """!
    @brief The part of a polygon that lies on the board, as polygons, by exact clipping.
    @details Sutherland-Hodgman needs one convex operand: a convex part (every rectangle and drawn footprint) clips the outline, or a convex
             outline clips the part. When both are concave the part is cut into triangles (`_triangulate`) and each triangle clips the outline, so
             the weights stay exact and do not jump when a vertex move makes a part concave. A concave outline cut by a convex piece can leave
             zero-width bridges, which have no area and cancel in `exact_coverage`. A polygon that crosses itself (read by the even-odd rule of the
             models) is not clipped.
    @param poly Part polygon vertices (n, 2) in metres.
    @param outline Board outline vertices (m, 2) in metres.
    @return list of numpy.ndarray pieces (k, 2) in metres whose areas add up to the part on the board, or None when the pair cannot be clipped exactly.
    """
    pa, ob = np.asarray(poly, dtype=float), np.asarray(outline, dtype=float)
    if polygon_self_intersects(ob) or polygon_self_intersects(pa):
        return None
    if _is_convex(pa):
        return [clip_polygon(ob, pa)]
    if _is_convex(ob):
        return [clip_polygon(pa, ob)]
    if len(pa) > _EAR_MAX_VERTICES:
        return None
    tris = _triangulate(pa)
    if tris is None:
        return None
    # The outline is cut to the box of the part once, so that every triangle clips a short polygon and not the whole outline
    x0, y0 = pa.min(axis=0)
    x1, y1 = pa.max(axis=0)
    local = clip_polygon(ob, np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]))
    if len(local) < 3:
        return []
    return [clip_polygon(local, t) for t in tris]


def part_weights(poly, outline, nx, ny, dx, dy, samples=BOARD_SAMPLES, cover=None):
    """!
    @brief Weight of every grid cell in the heating of a part: the share of the cell that is inside the part AND on the board.
    @details A part that crosses the board outline must heat the board only where it lies on it. The product of the two coverages
             (part x board) is exact only when one of them covers the whole cell; on a cell cut by both it is wrong (a part that covers
             the whole cell gets the right weight, but a part edge and the outline in the same cell give part cover x board cover instead of
             the area that is in both).
             With an outline the weight is the exact area of the part on the board in each cell over the area of the cell (the part is clipped to
             the outline (a concave part on a concave outline is cut into triangles first) and the result is intersected with the cells by `exact_coverage`). It is also the share of the board part of the cell that
             the part covers times the exact board cover of the cell (`Board.cover`), so the heat density on the board part of every cell is the
             part's density, consistently with the board area the model gives the cell. When the pair cannot be clipped (a polygon that
             crosses itself, or a concave part of more than _EAR_MAX_VERTICES vertices on a concave outline) the older rule is used: the intersection is taken sample by sample on the same points; if the model
             represents the board share of the cell by its own cover, the weight is the share of the cell's board samples that are in the part, times
             that cover. The caller normalises the weights so that the total power is exact.
    @param poly Part polygon vertices (n, 2) in metres.
    @param outline Board outline vertices (n, 2) in metres, or None for a rectangular board (then the result is coverage_fraction).
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param samples Sub-samples per cell side (rectangular board and the sampled fallback only).
    @param cover Optional board cover of every cell used by the model (ny, nx), in [0, 1]; used only by the sampled fallback (the exact weight needs no
           normalisation); None gives the plain intersection share.
    @return Array of shape (ny, nx) with values in [0, 1].
    """
    if outline is None:
        return coverage_fraction(poly, nx, ny, dx, dy, samples)
    pieces = _part_on_board(poly, outline)
    if pieces is not None:
        out = np.zeros((ny, nx))
        for piece in pieces:
            if len(piece) >= 3:
                out += exact_coverage(piece, nx, ny, dx, dy)
        return np.minimum(out, 1.0)
    out = np.zeros((ny, nx))
    got = _sample_mask(poly, nx, ny, dx, dy, samples, clip=outline)
    if got is None:
        return out
    i0, i1, j0, j1, part, board = got
    both = (part & board).sum(axis=(1, 3)).astype(float)       # Samples in the part and on the board, per cell
    if cover is None:
        out[i0:i1, j0:j1] = both / (samples * samples)
        return out
    n_board = board.sum(axis=(1, 3))
    # Share of the board part of the cell that the part covers, times the board share the model uses for the cell
    share = np.divide(both, n_board, out=np.zeros_like(both), where=n_board > 0)
    out[i0:i1, j0:j1] = share * np.asarray(cover, dtype=float)[i0:i1, j0:j1]
    return out


def _clip_to_box(poly, width, height):
    """!
    @brief Clip a polygon to the rectangle [0, width] x [0, height] (Sutherland-Hodgman, one box edge at a time).
    @param poly Polygon vertices (n, 2) in metres.
    @param width Box width in metres.
    @param height Box height in metres.
    @return numpy.ndarray Vertices (m, 2) of the clipped polygon in metres (m = 0 when nothing is left).
    """
    pts = [tuple(v) for v in np.asarray(poly, dtype=float)]
    # Each box edge as (axis, limit, keep_greater): the kept side is the inside half-plane
    for axis, limit, keep_greater in ((0, 0.0, True), (0, width, False), (1, 0.0, True), (1, height, False)):
        if not pts:
            break

        def inside(q):
            return q[axis] >= limit if keep_greater else q[axis] <= limit

        res = []
        prev = pts[-1]
        for cur in pts:
            if inside(cur) != inside(prev):
                # The edge crosses the limit: add the crossing point
                t = (limit - prev[axis]) / (cur[axis] - prev[axis])
                res.append((prev[0] + t * (cur[0] - prev[0]), prev[1] + t * (cur[1] - prev[1])))
            if inside(cur):
                res.append(cur)
            prev = cur
        pts = res
    return np.array(pts, dtype=float).reshape(-1, 2)


# Points per side of the lattice laid on the bounding box of a part to find its share inside an outline (the part's own size, not the cell's)
PART_SHARE_SAMPLES = 96


def part_board_share(poly, width, height, outline=None):
    """!
    @brief Share of a part polygon that lies on the board, from the geometry and not from the cell raster.
    @details A rectangular board (no outline) is the exact clip of the polygon to the box. With an outline the lattice is laid on the
             bounding box of the part itself (PART_SHARE_SAMPLES points per side), so a part smaller than a cell is judged as finely as a large one;
             the 4 x 4 lattice of the cell cover read a 1 mm part on a 2.5 mm cell as 22 % outside the board although it was inside.
    @param poly Part polygon vertices (n, 2) in metres.
    @param width Board width in metres.
    @param height Board height in metres.
    @param outline Board outline vertices (n, 2) in metres, or None for the rectangle.
    @return float Share in [0, 1] (1 for a polygon of zero area).
    """
    p = np.asarray(poly, dtype=float)
    area = polygon_area(p)
    if area <= 0:
        return 1.0
    clipped = _clip_to_box(p, width, height)
    share_box = polygon_area(clipped) / area if len(clipped) >= 3 else 0.0
    if outline is None:
        return float(min(share_box, 1.0))
    if share_box <= 0.0:
        return 0.0
    # The outline is a general polygon: count lattice points of the part that fall inside it
    n = PART_SHARE_SAMPLES
    gx, gy = np.meshgrid(p[:, 0].min() + (np.arange(n) + 0.5) / n * np.ptp(p[:, 0]), p[:, 1].min() + (np.arange(n) + 0.5) / n * np.ptp(p[:, 1]))
    in_part = points_in_polygon(gx.ravel(), gy.ravel(), p)
    if not in_part.any():
        return float(min(share_box, 1.0))
    on_board = points_in_polygon(gx.ravel(), gy.ravel(), np.asarray(outline, dtype=float))
    return float((in_part & on_board).sum() / in_part.sum())


def _is_convex(poly):
    """!
    @brief Whether a polygon is convex (all turns of its boundary have the same sign; collinear vertices are allowed).
    @param poly Polygon vertices (n, 2) in metres.
    @return bool True for a convex polygon.
    """
    p = np.asarray(poly, dtype=float)
    # A repeated vertex is an edge of no length whose turns read 0 on both sides: at a reflex corner it hid the turn, so an L with its inner
    # corner repeated was taken as convex and clipping by it gave the whole box (found by the review of fix/exact-board-cover)
    d1 = np.roll(p, -1, axis=0) - p
    p = p[np.abs(d1).max(axis=1) > 1e-12 * max(float(np.abs(p).max()), 1e-30)]
    if len(p) < 3:
        return False
    d1 = np.roll(p, -1, axis=0) - p
    d2 = np.roll(d1, -1, axis=0)
    cross = d1[:, 0] * d2[:, 1] - d1[:, 1] * d2[:, 0]
    scale = 1e-12 * max(float(np.abs(d1).max()) ** 2, 1e-30)      # Tolerance relative to the size, so a collinear vertex is not a turn
    if not (np.all(cross >= -scale) or np.all(cross <= scale)):
        return False
    # Turns of one sign are not enough: a pentagram turns the same way at every vertex but goes round twice and crosses itself, and clipping by it
    # gave the whole square at its centre (which the even-odd fill of the program leaves empty). A convex polygon turns once in total (2 pi)
    dot = d1[:, 0] * d2[:, 0] + d1[:, 1] * d2[:, 1]
    return bool(abs(float(np.arctan2(cross, dot).sum())) < 3.0 * math.pi)


def clip_polygon(subject, clip):
    """!
    @brief Clip a polygon to a convex polygon (Sutherland-Hodgman, one edge of the clip polygon at a time).
    @details Exact for any subject polygon when the clip polygon is convex (a concave subject may leave zero-width bridges, which have no area).
    @param subject Polygon to clip, vertices (n, 2) in metres.
    @param clip Convex clip polygon, vertices (m, 2) in metres, either orientation.
    @return numpy.ndarray Vertices (k, 2) of the clipped polygon in metres (k = 0 when nothing is left).
    """
    c = np.asarray(clip, dtype=float)
    if polygon_area_signed(c) < 0:
        c = c[::-1]                                            # Counter-clockwise: the inside is on the left of every edge
    pts = [tuple(v) for v in np.asarray(subject, dtype=float)]
    for k in range(len(c)):
        a, b = c[k], c[(k + 1) % len(c)]
        ex, ey = b[0] - a[0], b[1] - a[1]
        if not pts:
            break

        def side(q):
            return ex * (q[1] - a[1]) - ey * (q[0] - a[0])      # Positive on the left (inside)

        res = []
        prev = pts[-1]
        for cur in pts:
            s_cur, s_prev = side(cur), side(prev)
            if (s_cur >= 0) != (s_prev >= 0):
                t = s_prev / (s_prev - s_cur)
                res.append((prev[0] + t * (cur[0] - prev[0]), prev[1] + t * (cur[1] - prev[1])))
            if s_cur >= 0:
                res.append(cur)
            prev = cur
        pts = res
    return np.array(pts, dtype=float).reshape(-1, 2)


def polygon_area_signed(poly):
    """!
    @brief Signed area of a polygon (positive for counter-clockwise vertices).
    @param poly Polygon vertices (n, 2) in metres.
    @return float Signed area in m2.
    """
    p = np.asarray(poly, dtype=float)
    return 0.5 * float(np.dot(p[:, 0], np.roll(p[:, 1], -1)) - np.dot(p[:, 1], np.roll(p[:, 0], -1)))


def polygon_overlap_area(a, b):
    """!
    @brief Area shared by two polygons, from the geometry and not from a cell raster.
    @details Exact (Sutherland-Hodgman) when at least one polygon is convex and neither outline crosses itself, which covers every rectangle and every
             part footprint drawn as a convex shape. Two concave polygons, or an outline that crosses itself (read by the even-odd rule, as the fill of the
             models), are measured with a PART_SHARE_SAMPLES x PART_SHARE_SAMPLES lattice laid on the intersection of their bounding boxes (within about
             1 % of the smaller area on random star-shaped pairs against shapely).
    @param a First polygon vertices (n, 2) in metres.
    @param b Second polygon vertices (m, 2) in metres.
    @return float Overlap area in m2 (0 when they are apart or only touch).
    """
    pa, pb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    x0, x1 = max(pa[:, 0].min(), pb[:, 0].min()), min(pa[:, 0].max(), pb[:, 0].max())
    y0, y1 = max(pa[:, 1].min(), pb[:, 1].min()), min(pa[:, 1].max(), pb[:, 1].max())
    if x1 <= x0 or y1 <= y0:
        return 0.0
    # The clip measures the winding-number area, so a subject whose outline crosses itself (a pentagram: its centre wound twice) would count twice
    # what the even-odd fill of the program leaves empty; such a polygon goes to the lattice, which uses the even-odd rule like the models
    # (a polygon that _is_convex accepts turns once and cannot cross itself, so only the subject is tested)
    if _is_convex(pb) and not polygon_self_intersects(pa):
        clipped = clip_polygon(pa, pb)
    elif _is_convex(pa) and not polygon_self_intersects(pb):
        clipped = clip_polygon(pb, pa)
    else:
        n = PART_SHARE_SAMPLES
        gx, gy = np.meshgrid(x0 + (np.arange(n) + 0.5) / n * (x1 - x0), y0 + (np.arange(n) + 0.5) / n * (y1 - y0))
        both = points_in_polygon(gx.ravel(), gy.ravel(), pa) & points_in_polygon(gx.ravel(), gy.ravel(), pb)
        return float(both.sum() / n / n * (x1 - x0) * (y1 - y0))
    return abs(polygon_area_signed(clipped)) if len(clipped) >= 3 else 0.0


def bbox_overlap_pairs(polys):
    """!
    @brief Index pairs of polygons whose bounding boxes overlap with a positive area, found by a sweep instead of testing every pair.
    @details The pairs are exactly those for which polygon_overlap_area does not stop at its own bounding-box test (it returns 0 when the boxes only
             touch or are apart), so running the exact overlap on these pairs alone gives the same results as running it on all pairs. The sweep sorts
             the boxes by their left edge and, for each one, looks only at the boxes that start before its right edge and tests the y range with NumPy:
             near-linear for parts spread over a board (about n log n plus the number of candidate pairs), quadratic only if every box overlaps in x
             (and then in vectorised comparisons: 1000 parts in one column take about 10 ms). A box with no width or no height, or with a NaN
             coordinate, is left out: its box test in polygon_overlap_area fails (or its exact overlap is NaN), so it never gives a warning.
    @param polys Sequence of polygons, each None (skipped) or an array-like (n, 2) of vertices in metres.
    @return List of (i, j) with i < j in increasing order (the order of the double loop over i and j).
    """
    idx = [k for k, p in enumerate(polys) if p is not None]
    if len(idx) < 2:
        return []
    pts = [np.asarray(polys[k], dtype=float) for k in idx]
    boxes = np.array([[p[:, 0].min(), p[:, 0].max(), p[:, 1].min(), p[:, 1].max()] for p in pts], dtype=float)
    # A box with no width or no height (a point, a segment along an axis) overlaps nothing with a positive area: the box test of polygon_overlap_area
    # takes min(right) - max(left), which is at most the width of each box. The sweep below tests only the edges of the partner, so such a box would
    # pass when it lies inside another one; it is dropped here (as a box with a NaN coordinate, for which the exact overlap is NaN and never warns)
    keep = (boxes[:, 1] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 2])
    boxes = boxes[keep]
    ids = np.array(idx)[keep]
    if len(ids) < 2:
        return []
    order = np.argsort(boxes[:, 0], kind="stable")
    xmin, xmax, ymin, ymax = (boxes[order, c] for c in range(4))
    ids = ids[order]
    pairs = []
    for a in range(len(order)):
        # Boxes sorted after a that start strictly before the right edge of a overlap it in x (those starting at or after it only touch)
        hi = int(np.searchsorted(xmin, xmax[a], side="left"))
        if hi <= a + 1:
            continue
        sl = slice(a + 1, hi)
        # Strict overlaps in x (the sorted partner starts at or after a, so only its right edge must pass the left edge of a) and in y
        ok = (xmax[sl] > xmin[a]) & (ymin[sl] < ymax[a]) & (ymax[sl] > ymin[a])
        for b in np.nonzero(ok)[0]:
            i, j = int(ids[a]), int(ids[a + 1 + b])
            pairs.append((i, j) if i < j else (j, i))
    pairs.sort()
    return pairs


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


def disc_board_share(x, y, r, width, height, outline=None):
    """!
    @brief Share of a disc (a drill) that lies on the board, from a fixed sample of the disc.
    @details The sample is the centre plus 6 rings of 24 points at the mid-radii of equal-area annuli, so the share is an area fraction that does not
             depend on any grid. The board is the box (0..width, 0..height) or, with an outline, the outline polygon. It is 0.0 only when no sample
             point (centre included) is on the board, which is the rule "the via has no board under it". One disc of discs_board_share.
    @param x Centre x in m.
    @param y Centre y in m.
    @param r Radius in m (0 = a point).
    @param width Board width in m (the box used when there is no outline).
    @param height Board height in m.
    @param outline Outline polygon (n, 2) in m, or None for the rectangle.
    @return float in [0, 1].
    """
    return float(discs_board_share([x], [y], [r], width, height, outline)[0])


def discs_board_share(x, y, r, width, height, outline=None):
    """!
    @brief Share of each of many discs (the drills of the vias) that lies on the board; the sample of disc_board_share, vectorised.
    @details With an outline, a disc whose centre is farther than its radius from every edge is wholly on one side, so its share is that of its centre
             (1 or 0, which the sample would give too); only the discs near an edge are sampled. This keeps the live input check fast on a board with
             thousands of vias and a long outline (2000 vias, 400 vertices: 6.9 s with one polygon test per disc).
    @param x Array-like of centre x in m.
    @param y Array-like of centre y in m.
    @param r Array-like of radii in m (0 = a point).
    @param width Board width in m (the box used when there is no outline).
    @param height Board height in m.
    @param outline Outline polygon (n, 2) in m, or None for the rectangle.
    @return numpy.ndarray of float in [0, 1], one per disc.
    """
    x, y, r = (np.asarray(a, dtype=float).ravel() for a in (x, y, r))
    out = np.zeros(x.size)
    if x.size == 0:
        return out
    n_ring, n_ang = 6, 24
    # Mid-radius of the k-th of n equal-area annuli: r sqrt((k + 1/2) / n), as a fraction of r
    rad = np.sqrt((np.arange(n_ring) + 0.5) / n_ring)
    ang = 2.0 * math.pi * (np.arange(n_ang) + 0.5) / n_ang
    ux = np.concatenate([[0.0], (rad[:, None] * np.cos(ang)[None, :]).ravel()])     # unit sample, the centre first
    uy = np.concatenate([[0.0], (rad[:, None] * np.sin(ang)[None, :]).ravel()])

    def share(sel):
        # Sample the selected discs and count the points on the board (the centre is one more sample, so a disc of zero radius is decided by its
        # centre and a centre on the board is never share 0)
        px = x[sel, None] + r[sel, None] * ux[None, :]
        py = y[sel, None] + r[sel, None] * uy[None, :]
        if outline is None:
            inside = (px >= 0.0) & (px <= width) & (py >= 0.0) & (py <= height)
        else:
            inside = points_in_polygon(px, py, outline)
        return inside.mean(axis=1)

    if outline is None:
        return share(np.arange(x.size))
    poly = np.asarray(outline, dtype=float)
    a, b = poly, np.roll(poly, -1, axis=0)
    dmin = np.full(x.size, np.inf)
    for (ax, ay), (bx, by) in zip(a, b):
        # Distance of every centre to this edge (the segment from a to b)
        ex, ey = bx - ax, by - ay
        ll = ex * ex + ey * ey
        t = np.clip(((x - ax) * ex + (y - ay) * ey) / ll, 0.0, 1.0) if ll > 0 else np.zeros_like(x)
        dmin = np.minimum(dmin, np.hypot(x - ax - t * ex, y - ay - t * ey))
    near = dmin <= r
    out[~near] = points_in_polygon(x[~near], y[~near], poly).astype(float)
    if near.any():
        out[near] = share(np.flatnonzero(near))
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
    @brief True if the polygon does not cross itself (no two non-adjacent edges cross properly).
    @param poly Array-like (n, 2) of vertices (any length unit).
    @return bool.
    @note Same rule as the all-pairs test (strict sign change of both orientation tests, so touching
          and collinear overlaps are not crossings) but about O(n log n + k): the edges are sorted by
          the left end of their box and only pairs whose boxes overlap are tested, in vectorised blocks
          (k is the number of overlapping boxes; it is n^2 / 2 at worst, a star of long spikes:
          2.3 s at 20 000 vertices). Two edges that cross properly always have overlapping boxes, so
          the box test drops no real crossing. It differs from the old all-pairs loop in one place,
          on purpose: for nearly collinear edges that lie apart (the points of a straight side
          subdivided several times) the rounded orientation products can change sign at random, and
          the all-pairs loop then reported a crossing that exact arithmetic does not have and refused
          a valid outline; the box test never compares such edges. The boxes are padded by 1e-9 of
          the extent, which only adds pairs whose boxes touch to within that distance.
    """
    p = np.asarray(poly, dtype=float)
    n = len(p)
    if n < 4:
        return True                                              # Every pair of edges of a triangle is adjacent
    a = p
    b = np.roll(p, -1, axis=0)
    ok = np.isfinite(a).all(axis=1) & np.isfinite(b).all(axis=1)  # An edge with a NaN or inf end never crosses
    idx = np.nonzero(ok)[0]
    if len(idx) < 2:
        return True
    a, b = a[idx], b[idx]
    span = float(max(np.ptp(p[np.isfinite(p).all(axis=1)], axis=0).max(), 0.0))   # Extent of the finite vertices (at least two exist here)
    pad = 1e-9 * span
    xlo = np.minimum(a[:, 0], b[:, 0]) - pad
    xhi = np.maximum(a[:, 0], b[:, 0]) + pad
    ylo = np.minimum(a[:, 1], b[:, 1]) - pad
    yhi = np.maximum(a[:, 1], b[:, 1]) + pad
    order = np.argsort(xlo, kind="stable")
    idx, a, b, xlo, xhi, ylo, yhi = idx[order], a[order], b[order], xlo[order], xhi[order], ylo[order], yhi[order]
    m = len(idx)
    # For the edge at sorted position s the partners are the later positions whose box starts before its box ends
    hi = np.searchsorted(xlo, xhi, side="right")
    cnt = np.maximum(hi - (np.arange(m) + 1), 0)
    cum = np.concatenate(([0], np.cumsum(cnt)))
    block = 1 << 20                                              # Candidate pairs tested per block (bounds the memory)
    s0 = 0
    while s0 < m:
        # Largest run of edges whose candidate pairs fit in one block (at least one edge)
        s1 = int(np.searchsorted(cum, cum[s0] + block, side="right")) - 1
        s1 = min(max(s1, s0 + 1), m)
        c = cnt[s0:s1]
        total = int(c.sum())
        if total:
            si = np.repeat(np.arange(s0, s1), c)
            start = np.repeat(cum[s0:s1] - cum[s0], c)
            tj = np.arange(total) - start + si + 1               # Later sorted position of each partner
            keep = (ylo[si] <= yhi[tj]) & (ylo[tj] <= yhi[si])
            si, tj = si[keep], tj[keep]
            ei, ej = idx[si], idx[tj]
            lo, hi_ = np.minimum(ei, ej), np.maximum(ei, ej)
            # Adjacent edges (consecutive, or the closing edge against the first) share a vertex and are skipped
            keep = (hi_ != lo + 1) & ~((lo == 0) & (hi_ == n - 1))
            si, tj = si[keep], tj[keep]
            if len(si):
                A, B, C, D = a[si], b[si], a[tj], b[tj]
                # Same arithmetic as the all-pairs orientation test, so the signs agree exactly
                def ccw(P, Q, R):
                    return (R[:, 1] - P[:, 1]) * (Q[:, 0] - P[:, 0]) - (Q[:, 1] - P[:, 1]) * (R[:, 0] - P[:, 0])
                cross = (ccw(A, B, C) * ccw(A, B, D) < 0) & (ccw(C, D, A) * ccw(C, D, B) < 0)
                if cross.any():
                    return False
        s0 = s1
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
