#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file vecaperture.py
@brief Vectorised face apertures (review prototype): the board fraction of every interior face of the grid from the sorted crossings of the outline with each grid line.
@details The aperture of an x-face (the segment of the vertical grid line x = j dx between two horizontal lines) is the length of that segment inside the polygon over dy.
         All the crossings of the outline edges with the vertical grid lines are found at once (each edge gives the lines its x-span covers, half-open so that a vertex on a
         line counts once), sorted by (line, y), given the signs +1 (enter) and -1 (leave) by their rank on the line (even-odd), and the inside length below every grid node
         F(y) = sum over the crossings below y of s_k (y - w_k) is evaluated with prefix sums; the aperture is the difference of F over a face. The work is that of the
         crossings (about the perimeter over the cell) plus one `searchsorted` per crossed line. An outline edge that lies on a grid line has board on one side only, so
         each line is evaluated just left and just right of it (offset 1e-9 of a cell) and the smaller value is kept, as the prototype `cutgeom.cut_geometry_exact` does.
         This is the same signed-clamp construction that `geometry.exact_coverage` integrates over a column, evaluated on the grid lines instead.
"""

import numpy as np


def _line_lengths(poly, n_lines, spacing, n_seg, seg, axis, shift):
    """!
    @brief Inside length over each segment of each grid line of one family.
    @param poly Polygon (n, 2) in m.
    @param n_lines Interior grid lines of the family (j = 1 .. n_lines).
    @param spacing Distance between the lines in m.
    @param n_seg Segments per line (cells along the line).
    @param seg Segment length in m.
    @param axis 0: vertical lines x = j spacing (segments along y); 1: horizontal lines.
    @param shift Offset of the evaluated line from j spacing in m.
    @return Array (n_seg, n_lines) of fractions in [0, 1].
    """
    a = np.asarray(poly, dtype=float)
    b = np.roll(a, -1, axis=0)
    u0, u1 = (a[:, 0], b[:, 0]) if axis == 0 else (a[:, 1], b[:, 1])
    w0, w1 = (a[:, 1], b[:, 1]) if axis == 0 else (a[:, 0], b[:, 0])
    lo, hi = np.minimum(u0, u1), np.maximum(u0, u1)
    # Candidate lines of every edge, with one line of slack: the exact half-open test below decides on the same position for every edge
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
    s = np.where(rank % 2 == 0, 1.0, -1.0)          # even-odd: the crossings enter and leave in turn along the line
    nodes = np.arange(n_seg + 1) * seg
    for a_, b_ in zip(start, stop):                  # one vectorised evaluation per crossed line
        ww, ss = w[a_:b_], s[a_:b_]
        k = np.searchsorted(ww, nodes, side="left")
        c1 = np.r_[0.0, np.cumsum(ss)]
        c2 = np.r_[0.0, np.cumsum(ss * ww)]
        F = nodes * c1[k] - c2[k]                    # inside length below every node of the line
        out[:, j[a_] - 1] = np.diff(F) / seg
    return np.clip(out, 0.0, 1.0)


def apertures(poly, nx, ny, dx, dy):
    """!
    @brief Apertures of all interior faces of the grid.
    @param poly Outline (n, 2) in m.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell width in m.
    @param dy Cell height in m.
    @return (ax (ny, nx - 1), ay (ny - 1, nx)): open fraction of each face.
    """
    ex, ey = 1e-9 * dx, 1e-9 * dy
    ax = np.minimum(_line_lengths(poly, nx - 1, dx, ny, dy, 0, -ex), _line_lengths(poly, nx - 1, dx, ny, dy, 0, ex))
    ay = np.minimum(_line_lengths(poly, ny - 1, dy, nx, dx, 1, -ey), _line_lengths(poly, ny - 1, dy, nx, dx, 1, ey)).T
    return ax, ay
