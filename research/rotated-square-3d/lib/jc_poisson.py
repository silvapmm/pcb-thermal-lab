#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file jc_poisson.py
@brief Independent implementation of the Cartesian grid embedded boundary scheme of Johansen and Colella for Poisson's equation with Dirichlet data, written from the report text, to reproduce their Problem 1 (Tables I and II).
@details Nothing of the program is imported. The scheme (report LBNL-39908, section 3, equations 13 to 18; page numbers of the report):
         - unknowns phi at the CELL CENTRES of every cell with a positive volume fraction, also where the centre is outside the domain (p. 8);
         - cell divergence (eq. 14): `kappa (L phi) = (1/dx) [sum of aperture * flux on the four faces + front length * flux on the front]`, in unit cells;
         - full face flux: central difference (eq. 15); partial face flux (eq. 16): `a [ (1 + a)/2 g_own + (1 - a)/2 g_neighbour ]`, the gradient of
           the neighbouring face on the side where the open part of the face lies (linear interpolation of the gradient to the midpoint of the open part);
         - front flux (eq. 17, 18): a quadratic through the Dirichlet value at the midpoint of the front and two values interpolated (quadratically along the grid
           line) on the first two grid lines that the inward normal crosses and that do not pass through the cell itself;
         - the geometry is the piecewise-linear front through the intersections of the boundary with the grid lines (marching squares; a boundary that crosses
           an edge twice is ignored, as the report clips it).
         The test problem is the report's Problem 1: the "flower" `r <= 0.30 + 0.15 cos(6 theta)`, `phi = r^4 cos(3 theta)`, `Laplacian phi = 7 r^2 cos(3 theta)`
         (the report prints a symbol that reads like pi for the 7; the exact Laplacian of `r^4 cos 3 theta` is `(16 - 9) r^2 cos 3 theta`).
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def flower_radius(theta):
    """!
    @brief Radius of the boundary of the flower domain.
    @param theta Polar angle in radians.
    @return Radius (0.30 + 0.15 cos 6 theta).
    """
    return 0.30 + 0.15 * np.cos(6.0 * theta)


def phi_exact(x, y):
    """!
    @brief Exact solution r^4 cos(3 theta), written as r Re((x + i y)^3).
    @param x Abscissa.
    @param y Ordinate.
    @return phi (same shape as x).
    """
    return np.hypot(x, y) * np.real((x + 1j * y) ** 3)


def rho_exact(x, y):
    """!
    @brief Laplacian of the exact solution, 7 r^2 cos(3 theta) = 7 Re((x + i y)^3) / r.
    @param x Abscissa.
    @param y Ordinate.
    @return rho.
    """
    return 7.0 * np.real((x + 1j * y) ** 3) / np.maximum(np.hypot(x, y), 1e-300)


def _g(x, y):
    """!
    @brief Signed function of the domain: negative inside, zero on the boundary.
    @param x Abscissa.
    @param y Ordinate.
    @return r - R(theta).
    """
    return np.hypot(x, y) - flower_radius(np.arctan2(y, x))


def _cross(p0, p1):
    """!
    @brief Point of the boundary on a segment whose ends lie on both sides of it (bisection, 60 steps).
    @param p0 First end (x, y).
    @param p1 Second end (x, y).
    @return (t, x, y) with t the fraction of the segment from p0.
    """
    lo, hi = 0.0, 1.0
    g0 = _g(*p0)
    g1 = _g(*p1)
    if (g0 < 0) == (g1 < 0):
        # Both ends have the same sign of g: the node flagged outside by the 0.1 % shift lies just inside the true boundary; the crossing is at that node
        t = 0.0 if abs(g0) < abs(g1) else 1.0
        return t, p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1])
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        gm = _g(p0[0] + mid * (p1[0] - p0[0]), p0[1] + mid * (p1[1] - p0[1]))
        if (gm < 0) == (g0 < 0):
            lo = mid
        else:
            hi = mid
    t = 0.5 * (lo + hi)
    return t, p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1])


class Grid:
    """!
    @brief The cut-cell geometry of the flower on a grid of n cells per unit length over the box [-0.5, 0.5]^2.
    @details Attributes: n, dx, kap (n, n) volume fractions, ex (n + 1, n) and ey (n, n + 1) apertures of the vertical and horizontal faces
             (ex[i, j] is the face at x_i of row j), cx and cy (n, n) centroids of the open part, front dict {(i, j): (length in cells, midpoint, outward normal)}.
    """

    def __init__(self, n):
        """!
        @brief Build the geometry.
        @param n Cells per unit length (and per side of the box).
        @throws ValueError If a cell is crossed four times (saddle), which the scheme does not allow.
        """
        self.n = n
        self.dx = 1.0 / n
        x = -0.5 + self.dx * np.arange(n + 1)
        X, Y = np.meshgrid(x, x, indexing="ij")
        gv = _g(X, Y)
        # The report (p. 13) shifts the boundary by at most 0.1 % of the grid spacing to remove cells smaller than 1e-6 dx dy: a node that lies inside but
        # within 1e-3 dx of the boundary is taken as outside, which removes the sliver triangles at such a node
        ins = gv < -1e-3 * self.dx
        self.ins = ins
        self.kap = np.zeros((n, n))
        self.cx = (x[:-1, None] + 0.5 * self.dx) * np.ones((n, n))
        self.cy = (x[None, :-1] + 0.5 * self.dx) * np.ones((n, n))
        # Aperture of each grid edge: the inside fraction (marching squares on the edge ends)
        self.ex = np.zeros((n + 1, n))
        self.ey = np.zeros((n, n + 1))
        self.cross_x = {}
        self.cross_y = {}
        for i in range(n + 1):
            for j in range(n):
                a, b = ins[i, j], ins[i, j + 1]
                self.ex[i, j] = self._edge(a, b, (x[i], x[j]), (x[i], x[j + 1]), self.cross_x, (i, j))
        for i in range(n):
            for j in range(n + 1):
                a, b = ins[i, j], ins[i + 1, j]
                self.ey[i, j] = self._edge(a, b, (x[i], x[j]), (x[i + 1], x[j]), self.cross_y, (i, j))
        # Volume fraction and front of every cell
        nin = ins[:-1, :-1].astype(int) + ins[1:, :-1] + ins[1:, 1:] + ins[:-1, 1:]
        self.kap[nin == 4] = 1.0
        self.front = {}
        for i, j in zip(*np.nonzero((nin > 0) & (nin < 4))):
            self._cut_cell(i, j, x)

    @staticmethod
    def _edge(a, b, p0, p1, store, key):
        """!
        @brief Open fraction of a grid edge from the inside flags of its two ends.
        @param a Inside flag of the first end.
        @param b Inside flag of the second end.
        @param p0 First end.
        @param p1 Second end.
        @param store Dict receiving the crossing point.
        @param key Key of the edge.
        @return Fraction of the edge inside.
        """
        if a and b:
            return 1.0
        if not a and not b:
            return 0.0
        t, px, py = _cross(p0, p1)
        store[key] = (px, py)
        return t if a else 1.0 - t

    def _cut_cell(self, i, j, x):
        """!
        @brief Volume fraction, centroid and front of a cell with some corners inside.
        @param i Column of the cell.
        @param j Row of the cell.
        @param x Grid-line coordinates.
        @throws ValueError If the cell is crossed four times.
        """
        ins = self.ins
        # Corners counter-clockwise from the south-west, with the edge between each pair and its crossing point if any
        corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
        edges = [("y", (i, j)), ("x", (i + 1, j)), ("y", (i, j + 1)), ("x", (i, j))]
        poly, cross_pts = [], []
        for k in range(4):
            c0, c1 = corners[k], corners[(k + 1) % 4]
            a, b = ins[c0], ins[c1]
            if a:
                poly.append((x[c0[0]], x[c0[1]]))
            if a != b:
                kind, key = edges[k]
                pt = (self.cross_y if kind == "y" else self.cross_x)[key]
                poly.append(pt)
                cross_pts.append(pt)
        if len(cross_pts) != 2:
            raise ValueError("cell crossed %d times (saddle) at (%d, %d)" % (len(cross_pts), i, j))
        px = np.array([p[0] for p in poly])
        py = np.array([p[1] for p in poly])
        # Shoelace area and centroid of the open polygon
        cr = px * np.roll(py, -1) - np.roll(px, -1) * py
        area = 0.5 * cr.sum()
        if area < 0:
            area, cr = -area, -cr
        self.kap[i, j] = area / self.dx ** 2
        if area > 0:
            self.cx[i, j] = ((px + np.roll(px, -1)) * cr).sum() / (6.0 * area)
            self.cy[i, j] = ((py + np.roll(py, -1)) * cr).sum() / (6.0 * area)
        (x0, y0), (x1, y1) = cross_pts
        length = np.hypot(x1 - x0, y1 - y0)
        if length < 1e-9 * self.dx:
            # The shifted boundary touches the cell in one point only: the cell is whole (a flipped corner) or empty (one inside corner)
            self.kap[i, j] = 1.0 if area > 0.5 * self.dx ** 2 else 0.0
            self.cx[i, j] = (x[i] + 0.5 * self.dx)
            self.cy[i, j] = (x[j] + 0.5 * self.dx)
            return
        mid = (0.5 * (x0 + x1), 0.5 * (y0 + y1))
        nrm = np.array([y1 - y0, -(x1 - x0)]) / length
        # Outward normal points away from the open polygon centroid
        if nrm @ np.array([mid[0] - self.cx[i, j], mid[1] - self.cy[i, j]]) < 0:
            nrm = -nrm
        self.front[(i, j)] = (length / self.dx, mid, nrm)


def _lagrange3(ys, vals, y):
    """!
    @brief Quadratic Lagrange interpolation through three equally spaced points.
    @param ys The three abscissae.
    @param vals The three values.
    @param y Where to evaluate.
    @return Interpolated value.
    """
    y0, y1, y2 = ys
    return (vals[0] * (y - y1) * (y - y2) / ((y0 - y1) * (y0 - y2))
            + vals[1] * (y - y0) * (y - y2) / ((y1 - y0) * (y1 - y2))
            + vals[2] * (y - y0) * (y - y1) / ((y2 - y0) * (y2 - y1)))




def assemble(grid):
    """!
    @brief The flux balance of eq. 14 of every cell as a sparse matrix and a constant vector.
    @details Row of a cell: outward flux through the four faces (aperture times the difference of the two cell values, face length and 1/dx cancel) plus the
             outward flux through the front, `-lf dx g` with the inward quadratic gradient `g` of eq. 17; the Dirichlet value of the front is the constant `b0`
             so that `outflow = A phi + b0` and the equation is `outflow = kappa dx^2 rho`.
    @param grid Grid.
    @return (A, b0, idx, stats): matrix over the cells with kappa > 0, constant vector, index map (n, n) (-1 where the cell has no volume), counters of
            the cells where a stencil was not available (faces falling back to the plain gradient, fronts with no valid stencil).
    """
    n, dx = grid.n, grid.dx
    idx = -np.ones((n, n), dtype=int)
    cells = np.argwhere(grid.kap > 0)
    idx[grid.kap > 0] = np.arange(len(cells))
    m = len(cells)
    xc = -0.5 + dx * (np.arange(n) + 0.5)
    rows, cols, vals = [], [], []
    b0 = np.zeros(m)
    stats = {"face_fallback": 0, "front_fallback": 0}
    for r, (i, j) in enumerate(cells):
        # Faces: axis 0 = faces normal to x (west side 0 at x_i, east side 1 at x_{i+1}); axis 1 = faces normal to y
        for axis in (0, 1):
            for side in (0, 1):
                if axis == 0:
                    a = grid.ex[i + side, j]
                    lo, hi = (i - 1 + side, j), (i + side, j)
                else:
                    a = grid.ey[i, j + side]
                    lo, hi = (i, j - 1 + side), (i, j + side)
                if a <= 0.0 or idx[lo] < 0 or idx[hi] < 0:
                    continue
                sign = 1.0 if side == 1 else -1.0
                terms = [(1.0, lo, hi)]
                if a < 1.0:
                    # The open part of the face is at the end whose corner is inside; interpolate the gradient with the face next to it on that side
                    if axis == 0:
                        sh = (0, -1) if grid.ins[i + side, j] else (0, 1)
                    else:
                        sh = (-1, 0) if grid.ins[i, j + side] else (1, 0)
                    lo2, hi2 = (lo[0] + sh[0], lo[1] + sh[1]), (hi[0] + sh[0], hi[1] + sh[1])
                    if all(0 <= c < n for c in lo2 + hi2) and idx[lo2] >= 0 and idx[hi2] >= 0:
                        terms = [((1.0 + a) / 2.0, lo, hi), ((1.0 - a) / 2.0, lo2, hi2)]
                    else:
                        stats["face_fallback"] += 1
                for w, c_lo, c_hi in terms:
                    rows += [r, r]
                    cols += [idx[c_hi], idx[c_lo]]
                    vals += [sign * a * w, -sign * a * w]
        if (i, j) not in grid.front:
            continue
        lf, mid, nrm = grid.front[(i, j)]
        s = -nrm                                            # inward normal
        phi_b = float(phi_exact(mid[0], mid[1]))
        done = False
        for fam in ((0, 1) if abs(s[0]) >= abs(s[1]) else (1, 0)):
            # fam 0: the vertical grid lines of the columns i + sg and i + 2 sg; fam 1: the horizontal lines of the rows j + sg and j + 2 sg
            sg = 1 if s[fam] > 0 else -1
            base, oth = (i, j)[fam], 1 - fam
            if not (0 <= base + 2 * sg < n):
                continue
            picks, dn, ok = [], [], True
            for q in (1, 2):
                line_i = base + sg * q
                dn.append(abs((xc[line_i] - mid[fam]) / s[fam]))
                pos = mid[oth] + s[oth] * (xc[line_i] - mid[fam]) / s[fam]
                jc = min(max(int(np.floor((pos + 0.5) / dx)), 2), n - 3)
                found = None
                # Centred triple of cell centres along the line; one-sided triples when a cell of the centred one has no volume
                for shift in ((-1, 0, 1), (0, 1, 2), (-2, -1, 0)):
                    trip = [(line_i, jc + t) if fam == 0 else (jc + t, line_i) for t in shift]
                    if all(idx[c] >= 0 for c in trip):
                        found = (trip, [xc[jc + t] for t in shift])
                        break
                if found is None:
                    ok = False
                    break
                trip, ys = found
                wts = [_lagrange3(ys, np.eye(3)[t], pos) for t in range(3)]
                picks.append((trip, wts))
            if not ok:
                continue
            d1, d2 = dn
            # Inward derivative g = c1 (phi1 - phiB) + c2 (phi2 - phiB); the outward flux of the front is -lf dx g
            c1 = (d2 / d1) / (d2 - d1)
            c2 = -(d1 / d2) / (d2 - d1)
            for coef, (trip, wts) in ((c1, picks[0]), (c2, picks[1])):
                for cell, w in zip(trip, wts):
                    rows.append(r)
                    cols.append(idx[cell])
                    vals.append(-lf * dx * coef * w)
            b0[r] += lf * dx * (c1 + c2) * phi_b
            done = True
            break
        if not done:
            stats["front_fallback"] += 1
    return sp.csr_matrix((vals, (rows, cols)), shape=(m, m)), b0, idx, stats


def solve(n):
    """!
    @brief Solve Problem 1 on a grid of n cells per unit length and return the errors that the report tabulates.
    @param n Cells per unit length.
    @return dict: xi_inf (max |phi - phi_exact| over all cells with kappa > 0), xi_1 (sum |xi| kappa dx^2), xi_1_mean (the same over the area of the domain),
            tau_partial_inf (max kappa |tau| over the cut cells), tau_full_inf (max |tau| over the full cells), n_partial, n_full, area, stats.
    """
    g = Grid(n)
    dx = g.dx
    A, b0, idx, stats = assemble(g)
    sel = g.kap > 0
    cells = np.argwhere(sel)
    xc = -0.5 + dx * (np.arange(g.n) + 0.5)
    kap = g.kap[sel]
    rho = rho_exact(g.cx[sel], g.cy[sel])                     # evaluated at the centroid of the open part (the report, p. 14, Problem 1)
    phi = spla.spsolve(A.tocsc(), kap * dx * dx * rho - b0)
    exact = phi_exact(xc[cells[:, 0]], xc[cells[:, 1]])
    xi = phi - exact
    area = float((g.kap * dx * dx).sum())
    full = kap >= 1.0 - 1e-12
    # Truncation error (eq. 19): tau = rho - L phi_exact with L the same operator, so kappa tau = kappa rho - outflow / dx^2
    k_tau = kap * rho - (A @ exact + b0) / dx ** 2
    return {
        "xi_inf": float(np.abs(xi).max()), "xi_1": float((np.abs(xi) * kap).sum() * dx * dx), "area": area,
        "xi_1_mean": float((np.abs(xi) * kap).sum() * dx * dx / area),
        "tau_partial_inf": float(np.abs(k_tau[~full]).max()), "tau_full_inf": float(np.abs(k_tau[full]).max()),
        "n_partial": int((~full).sum()), "n_full": int(full.sum()), "stats": stats,
    }
