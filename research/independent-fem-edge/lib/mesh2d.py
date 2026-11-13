#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file mesh2d.py
@brief Plan (2D) quadrilateral meshes of a board: graded tensor grids, outlines by polygon, O-grid (butterfly) patches for a disc or a via cylinder.
@details A `Quad2D` holds node coordinates (N, 2) in m, quads (Q, 4) counter-clockwise and an integer tag per quad (the region a quad belongs
         to: 0 the plain board, or the ring index of an O-grid patch). The 3D board mesh is this plan mesh extruded through the stack (`board.py`).
         The O-grid makes a circle a conforming boundary (its nodes lie exactly on the circle; the boundary is the inscribed polygon of 4 n
         sides), so a disc board and the drill circle of a via are represented by real faces, not by an area share of cut cells.
"""

import numpy as np


def grid1d(length, breaks, zones, h_fine, growth=1.3, h_max=0.5e-3, start=0.0):
    """!
    @brief Graded 1D node list that contains every break point: size `h_fine` inside the zones, growing linearly with the distance from them.
    @param length End coordinate (m).
    @param breaks Coordinates that must be nodes (m); the ends are added.
    @param zones List of (a, b) intervals (m) where the size is `h_fine`.
    @param h_fine Fine element size (m).
    @param growth Size growth per unit distance from a zone (size = h_fine + (growth - 1) d).
    @param h_max Largest element size (m).
    @param start First coordinate (m).
    @return numpy.ndarray of increasing node coordinates.
    """
    pts = sorted(set([float(start), float(length)] + [float(b) for b in breaks if start < b < length]))
    zs = np.asarray(zones, float).reshape(-1, 2)

    def size(x):
        """!
        @brief Target size at x.
        @param x Coordinate.
        @return float.
        """
        if zs.size == 0:
            return h_max
        d = np.maximum(np.maximum(zs[:, 0] - x, x - zs[:, 1]), 0.0).min()
        return min(h_max, h_fine + (growth - 1.0) * d)

    out = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        steps, x = [], a
        while x < b - 1e-15:
            s = size(x)
            steps.append(s)
            x += s
        # the march overshoots b: drop the last step when it overshoots by more than half of it, then rescale to land on b exactly
        if len(steps) > 1 and (x - b) > 0.5 * steps[-1]:
            steps.pop()
        steps = np.asarray(steps) * (b - a) / sum(steps)
        out.extend((a + np.cumsum(steps)).tolist())
        out[-1] = b
    return np.asarray(out)


def uniform_window(xn, x0, x1, n):
    """!
    @brief Replace the nodes of a 1D node list inside [x0, x1] by n uniform intervals (x0 and x1 become nodes); used for an O-grid window.
    @param xn Node coordinates.
    @param x0 Window start.
    @param x1 Window end.
    @param n Intervals inside the window.
    @return numpy.ndarray.
    """
    keep = xn[(xn < x0 - 1e-12) | (xn > x1 + 1e-12)]
    return np.asarray(sorted(set(keep.tolist() + np.linspace(x0, x1, n + 1).tolist())))


def point_in_polygon(pts, poly):
    """!
    @brief Even-odd test of points against a polygon (ray casting, vectorised).
    @param pts Points (P, 2).
    @param poly Polygon vertices (V, 2), closed implicitly.
    @return bool array (P,).
    """
    pts = np.asarray(pts, float)
    poly = np.asarray(poly, float)
    x, y = pts[:, 0], pts[:, 1]
    inside = np.zeros(pts.shape[0], bool)
    V = poly.shape[0]
    for i in range(V):
        xa, ya = poly[i]
        xb, yb = poly[(i + 1) % V]
        cross = (ya > y) != (yb > y)
        with np.errstate(divide="ignore", invalid="ignore"):
            xi = xa + (y - ya) * (xb - xa) / (yb - ya)
        inside ^= cross & (x < xi)
    return inside


class Quad2D:
    """!
    @brief A plan quadrilateral mesh with a region tag per quad.
    """

    def __init__(self, xy, quads, tag=None):
        """!
        @brief Create the mesh.
        @param xy Node coordinates (N, 2) in m.
        @param quads Quads (Q, 4), counter-clockwise.
        @param tag Integer tag per quad (default 0).
        @return None.
        """
        self.xy = np.asarray(xy, float)
        self.quads = np.asarray(quads, np.int64).reshape(-1, 4)
        self.tag = np.zeros(self.quads.shape[0], np.int64) if tag is None else np.asarray(tag, np.int64)

    def centroids(self):
        """!
        @brief Quad centroids (mean of the four corners).
        @return numpy.ndarray (Q, 2).
        """
        return self.xy[self.quads].mean(axis=1)

    def areas(self):
        """!
        @brief Signed areas of the quads (shoelace; positive when counter-clockwise).
        @return numpy.ndarray (Q,).
        """
        p = self.xy[self.quads]
        x, y = p[:, :, 0], p[:, :, 1]
        return 0.5 * ((x * np.roll(y, -1, axis=1)) - (np.roll(x, -1, axis=1) * y)).sum(axis=1)

    def remove(self, mask):
        """!
        @brief Drop the quads where mask is True and the nodes no quad uses any more.
        @param mask bool (Q,).
        @return Quad2D (new).
        """
        q = self.quads[~mask]
        t = self.tag[~mask]
        used = np.zeros(self.xy.shape[0], bool)
        used[q.ravel()] = True
        remap = np.cumsum(used) - 1
        return Quad2D(self.xy[used], remap[q], t)

    def boundary_edges(self):
        """!
        @brief Edges that belong to exactly one quad, oriented as that quad runs them (counter-clockwise: the outside is on the right).
        @return Tuple (edges (B, 2) node ids, quad index (B,) of the owner).
        """
        q = self.quads
        e = np.stack([q, np.roll(q, -1, axis=1)], axis=2).reshape(-1, 2)       # (4Q, 2)
        owner = np.repeat(np.arange(q.shape[0]), 4)
        key = np.sort(e, axis=1)
        _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
        single = cnt[inv.ravel()] == 1
        return e[single], owner[single]

    def rotate(self, angle_deg, about=(0.0, 0.0)):
        """!
        @brief Rigidly rotate the mesh about a point (the physics is invariant; the rotated board is the same board).
        @param angle_deg Angle in degrees, counter-clockwise.
        @param about Centre of the rotation (m).
        @return Quad2D (new).
        """
        a = np.radians(angle_deg)
        c, s = np.cos(a), np.sin(a)
        p = self.xy - np.asarray(about, float)
        xy = np.column_stack([c * p[:, 0] - s * p[:, 1], s * p[:, 0] + c * p[:, 1]]) + np.asarray(about, float)
        return Quad2D(xy, self.quads.copy(), self.tag.copy())


def tensor(xn, yn):
    """!
    @brief Structured quad mesh of a tensor grid.
    @param xn Node coordinates in x (m).
    @param yn Node coordinates in y (m).
    @return Quad2D with tag 0 everywhere; node id = j (nx + 1) + i.
    """
    xn, yn = np.asarray(xn, float), np.asarray(yn, float)
    nx, ny = xn.size - 1, yn.size - 1
    X, Y = np.meshgrid(xn, yn)
    xy = np.column_stack([X.ravel(), Y.ravel()])
    nid = np.arange((nx + 1) * (ny + 1)).reshape(ny + 1, nx + 1)
    q = np.stack([nid[:-1, :-1], nid[:-1, 1:], nid[1:, 1:], nid[1:, :-1]], axis=2).reshape(-1, 4)
    return Quad2D(xy, q)


def merge(a, b, tol=1e-12):
    """!
    @brief Union of two meshes, identifying nodes that coincide within tol (m).
    @param a First mesh.
    @param b Second mesh.
    @param tol Coincidence tolerance in m.
    @return Quad2D.
    """
    xy = np.vstack([a.xy, b.xy])
    key = np.round(xy / tol).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    q = np.vstack([a.quads, b.quads + a.xy.shape[0]])
    return Quad2D(xy[first], inv[q], np.concatenate([a.tag, b.tag]))


def ogrid(cx, cy, s0, radii, n_side, outer, n_blend=0, tag_offset=0, n_inner=0):
    """!
    @brief O-grid (butterfly) patch: a central square, rings bounded by circles, and an outer boundary that is a square window or a circle.
    @details Rays are the uniform parameterisation of the inner square (n_side intervals per side, 4 n_side rays); level j of ray i is the point of
             circle j on that ray; the outer level is the window square point (on the same ray, so that it coincides with a uniform tensor grid of
             n_side intervals across the window) or the circle of radius `outer[1]`. `n_blend` levels blended between the last circle and a square
             window keep the aspect ratio in that corner region. Tags: 0 the inner square, j the ring between level j-1 and level j (1 ... ),
             plus `tag_offset`.
    @param cx Centre x (m).
    @param cy Centre y (m).
    @param s0 Half side of the inner square (m); must be below radii[0] / sqrt(2).
    @param radii Increasing circle radii (m); the last one is the outer boundary when outer is ('circle', R) and R == radii[-1].
    @param n_side Intervals per side of the inner square (and of the window).
    @param outer ('square', a) with a the half side of the window (m), or ('circle', R).
    @param n_blend Blended levels between the last circle and the window square.
    @param tag_offset Added to every tag.
    @param n_inner Blended levels between the inner square and the first circle (keeps the radial size of those elements in step with the angular one;
                   without them the first ring never refines radially and the Q1 elements there stop converging).
    @return Quad2D.
    """
    radii = list(radii)
    assert s0 * np.sqrt(2.0) < radii[0], "inner square corner must lie inside the first circle"
    n = n_side
    # inner square: uniform tensor grid
    t = np.linspace(-s0, s0, n + 1)
    inner = tensor(t + cx, t + cy)
    nid = np.arange((n + 1) ** 2).reshape(n + 1, n + 1)
    loop = np.concatenate([nid[0, :-1], nid[:-1, n], nid[n, :0:-1], nid[::-1, 0][:-1]])    # counter-clockwise, 4 n nodes
    p = inner.xy[loop] - np.array([cx, cy])
    theta = np.arctan2(p[:, 1], p[:, 0])
    u = np.column_stack([np.cos(theta), np.sin(theta)])
    levels = [inner.xy[loop]]
    first = np.array([cx, cy]) + radii[0] * u
    for b in range(1, n_inner + 1):
        f = b / (n_inner + 1)
        levels.append((1 - f) * levels[0] + f * first)
    for r in radii:
        levels.append(np.array([cx, cy]) + r * u)
    if outer[0] == "square":
        a = outer[1]
        sq = np.array([cx, cy]) + p * (a / s0)
        last = levels[-1]
        for b in range(1, n_blend + 1):
            f = b / (n_blend + 1)
            levels.append((1 - f) * last + f * sq)
        levels.append(sq)
    else:
        if abs(outer[1] - radii[-1]) > 1e-15:
            levels.append(np.array([cx, cy]) + outer[1] * u)
    # nodes: inner grid first, then the levels 1.. (level 0 is the inner loop itself)
    xy = [inner.xy]
    ids = [loop]
    base = inner.xy.shape[0]
    for lv in levels[1:]:
        xy.append(lv)
        ids.append(np.arange(base, base + lv.shape[0]))
        base += lv.shape[0]
    quads = [inner.quads]
    tags = [np.zeros(inner.quads.shape[0], np.int64)]
    m = loop.size
    for j in range(1, len(levels)):
        lo, hi = ids[j - 1], ids[j]
        nxt = np.roll(np.arange(m), -1)
        quads.append(np.column_stack([lo, hi, hi[nxt], lo[nxt]]))        # counter-clockwise: inward edge first, outer level runs forward
        tags.append(np.full(m, max(j - n_inner, 1), np.int64))           # every level inside the first circle is ring 1
    out = Quad2D(np.vstack(xy), np.vstack(quads), np.concatenate(tags) + tag_offset)
    assert (out.areas() > 0).all(), "O-grid quads must be counter-clockwise"
    return out


def embed_ogrid(base, cx, cy, half, n_side, radii, s0=None, n_blend=1, tag_offset=100, n_inner=0):
    """!
    @brief Replace the quads of a tensor mesh inside the square window [cx - half, cx + half] x [cy - half, cy + half] by an O-grid patch.
    @details The window boundary must be meshed uniformly with n_side intervals per side in `base` (use `uniform_window` on both axes first).
    @param base Tensor mesh (Quad2D).
    @param cx Window centre x (m).
    @param cy Window centre y (m).
    @param half Half side of the window (m).
    @param n_side Intervals per window side in the base mesh.
    @param radii Circle radii inside the window (m), increasing, all below `half`.
    @param s0 Half side of the inner square (default 0.55 radii[0] / sqrt 2).
    @param n_blend Blended levels between the last circle and the window.
    @param tag_offset Tags of the patch start here (tag_offset = inner square, +j the j-th ring).
    @param n_inner Blended levels between the inner square and the first circle.
    @return Quad2D.
    """
    c = base.centroids()
    inside = (np.abs(c[:, 0] - cx) < half) & (np.abs(c[:, 1] - cy) < half)
    cut = base.remove(inside)
    if s0 is None:
        s0 = 0.55 * radii[0] / np.sqrt(2.0)
    patch = ogrid(cx, cy, s0, radii, n_side, ("square", half), n_blend=n_blend, tag_offset=tag_offset, n_inner=n_inner)
    return merge(cut, patch)


def disc(R, n_side, radii_inner=(), s0=None, n_rings=None, ratio=1.0, n_inner=None):
    """!
    @brief O-grid mesh of a disc of radius R centred at the origin (conforming boundary: the inscribed 4 n_side-gon).
    @param R Disc radius (m).
    @param n_side Intervals per side of the inner square.
    @param radii_inner Extra circle radii that must be levels (a copper edge inside the disc, for example).
    @param s0 Half side of the inner square (default 0.4 R).
    @param n_rings Rings between the first circle and the outer circle (default: radial size about the angular size at the rim).
    @param ratio Growth ratio of the ring thickness outwards (1: uniform; below 1: finer at the rim).
    @param n_inner Blended levels between the inner square and the first circle (default: radial size about the angular size).
    @return Quad2D.
    """
    if s0 is None:
        s0 = 0.4 * R
    if n_rings is None:
        n_rings = max(int(round(n_side * 0.35 / 1.2)), 1)
    if n_inner is None:
        n_inner = max(int(round(n_side * 0.25 / 0.8)) - 1, 0)
    r0 = s0 * np.sqrt(2.0) * 1.15
    w = ratio ** np.arange(n_rings)
    cum = np.concatenate([[0.0], np.cumsum(w)]) / w.sum()
    radii = sorted(set((r0 + (R - r0) * cum).tolist() + [float(r) for r in radii_inner if r0 < r < R]))
    radii[-1] = R
    return ogrid(0.0, 0.0, s0, radii, n_side, ("circle", R), n_inner=n_inner)
