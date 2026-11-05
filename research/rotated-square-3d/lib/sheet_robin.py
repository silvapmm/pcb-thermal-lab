#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file sheet_robin.py
@brief A thin conducting sheet with face losses and a Robin film on its round rim (disc and annulus): the closed form (Bessel functions) and three cut-cell finite-volume schemes written independently of the program.
@details The problem is the one the program solves for one copper layer: `-div(S grad T) + G T = q` on the sheet (S sheet conductance in W/K, G loss per area in W/m2K,
         q source per area in W/m2, T the rise over the ambient) with the film on the rim `-S dT/dn = H T` (H in W/m K, the edge coefficient times the thickness).
         This is the Robin condition (flux proportional to the boundary value) that the cut-cell literature treats as `D dq/dn + a q = g` (Barrett, Fogelson and Griffith 2021, eq. 1b)
         and that the program's edge term is. The closed form of the disc and the annulus gives the references: `T = q/G + A I0(k r) + B K0(k r)`, `k = sqrt(G/S)`.

         Schemes (all with the same cover, the sheet conductance S per square of real metal and the film on the node):
         - "program": nodes at the cell centres, the lateral link is the harmonic mean of the cover-scaled conductances over the distance between centres (the FVM and the 3D solid
           of the program), the film `H L` of the outline length in the cell attached to the node directly;
         - "aperture": nodes at the cell centres, the link carries the aperture of the face times the physical S (the partial-face flux of Johansen and Colella, eq. 15 and 16,
           and of Barrett et al., eq. 10), the film on the node;
         - "aperture+bochkov": as "aperture", with the film of Bochkov and Gibou as Barrett et al. write it (eq. 12 to 14): the value at the cell centre is carried to the closest
           boundary point over the signed distance `d` (a Taylor step along the normal) and the film acts there, so the film conductance is `H L / (1 + H d / S)`; `d` is negative when
           the cell centre is outside the sheet (the denominator can then vanish on a coarse grid: the paper says the system is well posed "for a sufficiently refined grid");
         - "links": nodes at the centroids of the open parts, the link is the aperture times S over the distances from the face to the two centroids (two-point flux), film on the node;
         - "links+strip": as "links", with the conduction from the centroid to the outline (half the depth of the open strip) in series with the film, which is the Robin treatment
           of Bochkov and Gibou as quoted by Barrett et al. (eq. 12 to 14: the cell value is carried to the boundary point over the distance d and the film acts there).
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.special import i0, i1, k0, k1

SCHEMES = ("program", "aperture", "aperture+bochkov", "links", "links+strip")


def disc_exact(r, radius, S, G, H, q):
    """!
    @brief Temperature rise of a disc sheet with uniform source and a Robin film on the rim.
    @param r Radius(es) in m.
    @param radius Radius of the disc in m.
    @param S Sheet conductance in W/K.
    @param G Loss per area in W/m2K.
    @param H Rim film in W/m K (edge coefficient times thickness).
    @param q Source per area in W/m2.
    @return Rise in K: (q/G) (1 - C I0(k r)) with C = H / (S k I1(k R) + H I0(k R)).
    """
    k = np.sqrt(G / S)
    c = H / (S * k * i1(k * radius) + H * i0(k * radius))
    return (q / G) * (1.0 - c * i0(k * np.asarray(r)))


def disc_rim_loss(radius, S, G, H, q):
    """!
    @brief Heat leaving through the rim film of the disc.
    @param radius Radius in m.
    @param S Sheet conductance in W/K.
    @param G Loss per area in W/m2K.
    @param H Rim film in W/m K.
    @param q Source per area in W/m2.
    @return Watts, `H T(R) 2 pi R`.
    """
    return float(H * disc_exact(radius, radius, S, G, H, q) * 2.0 * np.pi * radius)


def annulus_exact(r, r1, r2, S, G, H1, H2, q):
    """!
    @brief Temperature rise of an annular sheet (inner radius r1, outer r2) with a Robin film on both rims.
    @param r Radius(es) in m.
    @param r1 Inner radius in m.
    @param r2 Outer radius in m.
    @param S Sheet conductance in W/K.
    @param G Loss per area in W/m2K.
    @param H1 Film of the inner rim in W/m K.
    @param H2 Film of the outer rim in W/m K.
    @param q Source per area in W/m2.
    @return Rise in K: q/G + A I0(k r) + B K0(k r) with A and B from the two rim conditions
            (outward flux `-S T' = H2 T` at r2 and `+S T' = H1 T` at r1).
    """
    k = np.sqrt(G / S)
    t0 = q / G
    # Outer: -S (A k I1(k r2) - B k K1(k r2)) = H2 (t0 + A I0(k r2) + B K0(k r2))
    # Inner: +S (A k I1(k r1) - B k K1(k r1)) = H1 (t0 + A I0(k r1) + B K0(k r1))
    m = np.array([[S * k * i1(k * r2) + H2 * i0(k * r2), -S * k * k1(k * r2) + H2 * k0(k * r2)],
                  [-S * k * i1(k * r1) + H1 * i0(k * r1), S * k * k1(k * r1) + H1 * k0(k * r1)]])
    a, b = np.linalg.solve(m, np.array([-H2 * t0, -H1 * t0]))
    rr = np.asarray(r)
    return t0 + a * i0(k * rr) + b * k0(k * rr)


def annulus_rim_loss(r1, r2, S, G, H1, H2, q):
    """!
    @brief Heat leaving through the two rim films of the annulus.
    @param r1 Inner radius in m.
    @param r2 Outer radius in m.
    @param S Sheet conductance in W/K.
    @param G Loss per area in W/m2K.
    @param H1 Film of the inner rim in W/m K.
    @param H2 Film of the outer rim in W/m K.
    @param q Source per area in W/m2.
    @return Watts.
    """
    t1 = float(annulus_exact(r1, r1, r2, S, G, H1, H2, q))
    t2 = float(annulus_exact(r2, r1, r2, S, G, H1, H2, q))
    return H1 * t1 * 2.0 * np.pi * r1 + H2 * t2 * 2.0 * np.pi * r2


def _overlap(lo_a, hi_a, lo_b, hi_b):
    """!
    @brief Length and first moment of the overlap of two intervals.
    @param lo_a Lower end of the first interval.
    @param hi_a Upper end of the first interval.
    @param lo_b Lower end of the second interval.
    @param hi_b Upper end of the second interval.
    @return (length, integral of the coordinate over the overlap).
    """
    lo, hi = np.maximum(lo_a, lo_b), np.minimum(hi_a, hi_b)
    ln = np.maximum(hi - lo, 0.0)
    return ln, np.where(ln > 0, 0.5 * (hi * hi - lo * lo), 0.0)


def _chords(t, lo, hi, ct, co, radius, inner):
    """!
    @brief Exact length and first moment of the sheet along lines `t = const` within the range [lo, hi] of the other coordinate.
    @param t Positions of the lines (broadcastable against lo and hi).
    @param lo Lower end of the range of the other coordinate.
    @param hi Upper end of the range.
    @param ct Centre of the circles along the line coordinate t.
    @param co Centre of the circles along the other coordinate.
    @param radius Outer radius.
    @param inner Inner radius (0: no hole).
    @return (length, moment): the open set is [co - ho, co - hi_] and [co + hi_, co + ho] with ho and hi_ from the chords of the two circles.
    """
    d2 = (t - ct) ** 2
    ho = np.sqrt(np.maximum(radius ** 2 - d2, 0.0))
    hin = np.sqrt(np.maximum(inner ** 2 - d2, 0.0))
    ho = np.where(radius ** 2 - d2 > 0, ho, 0.0)
    l1, m1 = _overlap(lo, hi, co - ho, co - hin)
    l2, m2 = _overlap(lo, hi, co + hin, co + ho)
    return l1 + l2, m1 + m2


def _chords_y(t, lo, hi, ct, co, radius, inner):
    """!
    @brief The same chords for lines `y = t` (the horizontal faces); the circle centre is (ct, co) = (cx0, cy0) there, so the roles of the coordinates are swapped.
    @param t Positions of the lines (y).
    @param lo Lower end of the range in x.
    @param hi Upper end of the range in x.
    @param ct Centre x.
    @param co Centre y.
    @param radius Outer radius.
    @param inner Inner radius.
    @return (length, moment).
    """
    return _chords(t, lo, hi, co, ct, radius, inner)


class Shape:
    """!
    @brief A round sheet (disc or annulus) cut by a square grid: cover, centroids, apertures and rim length of every cell.
    @details Geometry from exact chords of the circles (apertures exactly; cover and centroid by a midpoint rule over `m` slices per cell with the exact chord in every slice; rim length: a polyline of 200 000 points per circle).
             Attributes: nx, ny, dx, kap (cover), cx, cy (centroids of the open part, m, absolute), ax (ny, nx + 1) and ay (ny + 1, nx) apertures, rim (ny, nx, 2) rim length in the
             cell of the outer (0) and inner (1) circle, x0 and y0 (lower-left corner of the grid).
    """

    def __init__(self, radius, dx, centre=(0.0, 0.0), inner=0.0, m=128):
        """!
        @brief Build the geometry.
        @param radius Outer radius in m.
        @param dx Cell size in m.
        @param centre Centre of the sheet relative to a grid node, in m (the offset against the grid is what the shift study varies).
        @param inner Inner radius in m (0 for a disc).
        @param m Slices per cell side for the cover and the centroid.
        """
        self.radius, self.inner, self.dx = radius, inner, dx
        self.centre = centre
        n = int(np.ceil(2.0 * radius / dx)) + 3
        self.nx = self.ny = n
        self.x0 = self.y0 = -0.5 * n * dx
        cx0, cy0 = centre

        sub = (np.arange(m) + 0.5) / m * dx
        xs = (self.x0 + dx * np.arange(n)[:, None] + sub[None, :]).ravel()               # slice positions along x (m per cell)
        edges = self.x0 + dx * np.arange(n + 1)
        # Exact chords: along a line at x the open set of y is two intervals around the circle centre (one when the line misses the hole)
        len_s, mom_s = _chords(xs[:, None], edges[None, :-1], edges[None, 1:], cx0, cy0, radius, inner)          # (n m, n): rows of cells
        w = dx / m
        self.kap = len_s.reshape(n, m, n).sum(axis=1) * w / dx ** 2                         # (column, row)
        xmom = (xs[:, None] * len_s).reshape(n, m, n).sum(axis=1) * w
        ymom = mom_s.reshape(n, m, n).sum(axis=1) * w
        area = self.kap * dx ** 2
        mid = self.x0 + dx * (np.arange(n) + 0.5)
        with np.errstate(divide="ignore", invalid="ignore"):
            self.cx = np.where(area > 0, xmom / area, mid[:, None])
            self.cy = np.where(area > 0, ymom / area, mid[None, :])
        # Apertures from the same exact chords: vertical faces at the grid lines in x, horizontal faces at the grid lines in y
        self.ax = _chords(edges[:, None], edges[None, :-1], edges[None, 1:], cx0, cy0, radius, inner)[0] / dx            # (n + 1, n)
        self.ay = _chords_y(edges[:, None], edges[None, :-1], edges[None, 1:], cx0, cy0, radius, inner)[0] / dx          # (n + 1, n): face j, column i
        # Rim length per cell from a fine polyline of each circle
        self.rim = np.zeros((n, n, 2))
        for k, rad in enumerate((radius, inner)):
            if rad <= 0:
                continue
            t = np.linspace(0.0, 2.0 * np.pi, 200001)
            px, py = cx0 + rad * np.cos(t), cy0 + rad * np.sin(t)
            seg = np.hypot(np.diff(px), np.diff(py))
            mx, my = 0.5 * (px[1:] + px[:-1]), 0.5 * (py[1:] + py[:-1])
            ci = np.clip(np.floor((mx - self.x0) / dx).astype(int), 0, n - 1)
            cj = np.clip(np.floor((my - self.y0) / dx).astype(int), 0, n - 1)
            np.add.at(self.rim[:, :, k], (ci, cj), seg)


def radius_of(shape):
    """!
    @brief Outer radius of a Shape.
    @param shape Shape.
    @return Radius in m.
    """
    return shape.radius


def solve(shape, S, G, H, q, scheme, H_inner=None, d_min=1e-3):
    """!
    @brief Steady temperature of the sheet on the grid of a `Shape` with one of the schemes.
    @param shape Shape.
    @param S Sheet conductance in W/K.
    @param G Loss per area in W/m2K.
    @param H Outer rim film in W/m K.
    @param q Source per area in W/m2.
    @param scheme One of SCHEMES.
    @param H_inner Film of the inner rim (default: H).
    @param d_min Floor of a face-to-centroid distance as a fraction of the cell (scheme "links").
    @return dict: T (ny, nx) rise (nan outside the sheet), px and py (node positions), q_rim (heat through the rims, W), q_loss (heat through the faces, W), power (W), kap.
    @throws ValueError If the scheme is unknown.
    """
    if scheme not in SCHEMES:
        raise ValueError(f"scheme must be one of {SCHEMES}")
    dx, n = shape.dx, shape.nx
    kap, ax, ay = shape.kap, shape.ax, shape.ay
    exists = kap > 0
    node_x = shape.x0 + dx * (np.arange(n) + 0.5)
    if scheme in ("program", "aperture", "aperture+bochkov"):
        px = node_x[:, None] * np.ones((n, n))
        py = node_x[None, :] * np.ones((n, n))
    else:
        px, py = shape.cx, shape.cy
    idx = -np.ones((n, n), dtype=int)
    idx[exists] = np.arange(int(exists.sum()))
    nn = int(exists.sum())
    rows, cols, vals = [], [], []
    diag = np.zeros(nn)

    def link(i0_, j0_, i1_, j1_, g):
        a, b = idx[i0_, j0_], idx[i1_, j1_]
        if a < 0 or b < 0 or g <= 0.0:
            return
        diag[a] += g
        diag[b] += g
        rows.extend([a, b])
        cols.extend([b, a])
        vals.extend([-g, -g])

    # Links along x (cell i to i + 1, same row j) and along y
    for i in range(n - 1):
        for j in range(n):
            if not (exists[i, j] and exists[i + 1, j]):
                continue
            a = ax[i + 1, j]
            if scheme == "program":
                ka, kb = S * kap[i, j], S * kap[i + 1, j]
                g = 0.0 if ka * kb <= 0 else 2.0 * ka * kb / (ka + kb)
            elif scheme in ("aperture", "aperture+bochkov"):
                g = a * S
            else:
                xf = shape.x0 + dx * (i + 1)
                d1 = max(xf - px[i, j], d_min * dx)
                d2 = max(px[i + 1, j] - xf, d_min * dx)
                g = a * dx * S / (d1 + d2) if a > 0 else 0.0
            link(i, j, i + 1, j, g)
    for i in range(n):
        for j in range(n - 1):
            if not (exists[i, j] and exists[i, j + 1]):
                continue
            a = ay[j + 1, i]
            if scheme == "program":
                ka, kb = S * kap[i, j], S * kap[i, j + 1]
                g = 0.0 if ka * kb <= 0 else 2.0 * ka * kb / (ka + kb)
            elif scheme in ("aperture", "aperture+bochkov"):
                g = a * S
            else:
                yf = shape.y0 + dx * (j + 1)
                d1 = max(yf - py[i, j], d_min * dx)
                d2 = max(py[i, j + 1] - yf, d_min * dx)
                g = a * dx * S / (d1 + d2) if a > 0 else 0.0
            link(i, j, i, j + 1, g)
    # Face losses, rim films and sources
    area = kap * dx * dx
    h_in = H if H_inner is None else H_inner
    L = shape.rim[:, :, 0] + shape.rim[:, :, 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        hl = np.where(L > 0, (H * shape.rim[:, :, 0] + h_in * shape.rim[:, :, 1]) / L, 0.0)          # film per length of the cell's rim
        g_film = hl * L
        if scheme == "aperture+bochkov":
            # Signed distance from the cell centre to the circle that carries the rim of the cell (positive inside the sheet), weighted by the rim lengths
            rho = np.hypot(px - shape.centre[0], py - shape.centre[1])
            d_out, d_in = radius_of(shape) - rho, rho - shape.inner
            dist = np.where(L > 0, (d_out * shape.rim[:, :, 0] + d_in * shape.rim[:, :, 1]) / np.where(L > 0, L, 1.0), 0.0)
            denom = 1.0 + hl * dist / S
            if np.any(denom[L > 0] <= 0.0):
                raise ValueError("the Bochkov film is ill posed on this grid (a cell centre farther outside the sheet than S / H)")
            g_film = np.where(L > 0, g_film / denom, 0.0)
        if scheme == "links+strip":
            depth = 0.5 * np.minimum(area / L, dx)
            g_cond = np.where(L > 0, S * L / depth, np.inf)
            g_film = np.where(L > 0, 1.0 / (1.0 / g_film + 1.0 / g_cond), 0.0)
        g_film = np.nan_to_num(g_film)
    gl = G * area
    sel = exists
    d = diag + (gl + g_film)[sel]
    A = sp.coo_matrix((np.concatenate([vals, d]), (np.concatenate([rows, np.arange(nn)]), np.concatenate([cols, np.arange(nn)]))), shape=(nn, nn)).tocsc()
    T = spla.spsolve(A, q * area[sel])
    out = np.full((n, n), np.nan)
    out[sel] = T
    return {"T": out, "px": px, "py": py, "q_rim": float((g_film[sel] * T).sum()), "q_loss": float((gl[sel] * T).sum()),
            "power": float(q * area.sum()), "kap": kap}
