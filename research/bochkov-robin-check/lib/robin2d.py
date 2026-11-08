#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file robin2d.py
@brief Independent 2D cell-centred finite-volume solver of -div(mu grad u) = f with Robin conditions mu du/dn + alpha u = g on a cut Cartesian grid.
@details Prototype (outside the program) of the symmetric scheme of Bochkov and Gibou (2019; thesis of Bochkov 2020, chapter 1, sections 1.4.1, 1.4.2, 1.4.6):
         fluxes between cells with the length of the cut face (eq. 1.7), the Robin term with the unknown eliminated through the first-order relation
         u_ij = u(r_G) + d du/dn (eqs. 1.10 to 1.14), and the kink treatment of cells with two boundary pieces (eqs. 1.15 to 1.19).
         Variants (`scheme`):

         - `bg`        eq. 1.14 per smooth cell, eq. 1.19 for cells with two pieces (the thesis' symmetric scheme);
         - `bg_nokink` eq. 1.14 applied to each piece of a kink cell with the distance to its own line (no kink treatment);
         - `film`      the scheme of the program proposal (`research/cut-cell-links`): ONE film per cell, length of all the boundary in the cell, `d` the signed
                       distance from the cell centre to the closest point of the whole outline, denominator floored at `floor` (0.25);
         - `nofilm`    the Robin term alpha L u_ij at the cell centre (d = 0), what a plain cell-centred scheme does.

         Domains: a triangle (the thesis' test of section 1.5.2, with kinks) and a disc (smooth). Geometry is exact (clipping, circle intersections).
@note Everything is SI-free (a dimensionless test). Run through `research/bochkov-robin-check/scripts/study_triangle_disc.py`.
"""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

GL_X, GL_W = np.polynomial.legendre.leggauss(4)
GL_X = 0.5 * (GL_X + 1.0)   # nodes on [0, 1]
GL_W = 0.5 * GL_W           # weights summing to 1


class Triangle:
    """!
    @brief Convex polygon domain described by straight components (the triangle of the thesis section 1.5.2).
    @param verts Vertices (m, 2) counter-clockwise.
    @param alphas List of callables alpha(x, y), one per edge (edge k joins vertex k to k+1).
    @param u_exact Callable u(x, y).
    @param grad_exact Callable returning (ux, uy).
    """

    smooth_comps = False

    def __init__(self, verts, alphas, u_exact, grad_exact):
        """!
        @brief Store the polygon, the edge normals and the data.
        @param verts Vertices (m, 2) counter-clockwise.
        @param alphas Robin coefficient per edge.
        @param u_exact Exact solution.
        @param grad_exact Exact gradient.
        @return None
        """
        self.v = np.asarray(verts, float)
        self.m = len(self.v)
        self.alphas = alphas
        self.u, self.gu = u_exact, grad_exact
        e = np.roll(self.v, -1, axis=0) - self.v
        self.len = np.hypot(e[:, 0], e[:, 1])
        self.t = e / self.len[:, None]
        self.n = np.stack([self.t[:, 1], -self.t[:, 0]], axis=1)   # outward for a counter-clockwise polygon
        self.ncomp = self.m

    def phi_comp(self, p, x, y):
        """!
        @brief Signed distance to the infinite line of component p (negative inside).
        @param p Component index.
        @param x x coordinates.
        @param y y coordinates.
        @return Array of d.
        """
        return (x - self.v[p, 0]) * self.n[p, 0] + (y - self.v[p, 1]) * self.n[p, 1]

    def foot(self, p, x, y):
        """!
        @brief Foot of the perpendicular from (x, y) on the line of component p.
        @param p Component index.
        @param x x coordinates.
        @param y y coordinates.
        @return (xf, yf).
        """
        d = self.phi_comp(p, x, y)
        return x - d * self.n[p, 0], y - d * self.n[p, 1]

    def normal(self, p, x, y):
        """!
        @brief Outward normal of component p at points (constant).
        @param p Component index.
        @param x x coordinates.
        @param y y coordinates.
        @return (nx, ny) arrays.
        """
        return np.full_like(x, self.n[p, 0]), np.full_like(x, self.n[p, 1])

    def seg_len(self, x0, y0, x1, y1):
        """!
        @brief Length of the segment (x0,y0)-(x1,y1) inside the polygon (exact clip against the half-planes).
        @param x0 Start x (array).
        @param y0 Start y.
        @param x1 End x.
        @param y1 End y.
        @return Array of lengths.
        """
        lo = np.zeros_like(x0)
        hi = np.ones_like(x0)
        dx, dy = x1 - x0, y1 - y0
        for p in range(self.m):
            a = (x0 - self.v[p, 0]) * self.n[p, 0] + (y0 - self.v[p, 1]) * self.n[p, 1]   # phi at start
            b = dx * self.n[p, 0] + dy * self.n[p, 1]                                     # slope of phi
            with np.errstate(divide="ignore", invalid="ignore"):
                t = -a / b
            lo = np.where((b > 0) & (t > lo), t, lo) if False else lo
            # phi(t) = a + b t <= 0
            hi = np.where(b > 0, np.minimum(hi, t), hi)
            lo = np.where(b < 0, np.maximum(lo, t), lo)
            bad = (b == 0) & (a > 0)
            hi = np.where(bad, -1.0, hi)
        return np.hypot(dx, dy) * np.clip(hi - lo, 0.0, None)

    def inside(self, x, y):
        """!
        @brief True where the point is inside the polygon.
        @param x x coordinates.
        @param y y coordinates.
        @return Boolean array.
        """
        ok = np.ones(np.shape(x), bool)
        for p in range(self.m):
            ok &= self.phi_comp(p, x, y) < 0
        return ok

    def poly_signed_distance(self, x, y):
        """!
        @brief Signed distance to the polygon boundary (closest point on the segments), negative inside, with the closest point.
        @param x x coordinates.
        @param y y coordinates.
        @return (d, xc, yc, comp).
        """
        best = np.full(np.shape(x), np.inf)
        bx = np.zeros(np.shape(x))
        by = np.zeros(np.shape(x))
        bc = np.zeros(np.shape(x), int)
        for p in range(self.m):
            s = (x - self.v[p, 0]) * self.t[p, 0] + (y - self.v[p, 1]) * self.t[p, 1]
            s = np.clip(s, 0.0, self.len[p])
            cx = self.v[p, 0] + s * self.t[p, 0]
            cy = self.v[p, 1] + s * self.t[p, 1]
            dist = np.hypot(x - cx, y - cy)
            upd = dist < best
            best = np.where(upd, dist, best)
            bx = np.where(upd, cx, bx)
            by = np.where(upd, cy, by)
            bc = np.where(upd, p, bc)
        return np.where(self.inside(x, y), -best, best), bx, by, bc

    def pieces(self, xl, yl):
        """!
        @brief Pieces of the boundary between the grid lines: component, quadrature points and weights.
        @param xl Vertical grid line coordinates (cell borders).
        @param yl Horizontal grid line coordinates.
        @return Dict with comp, mid (m, 2), pts (m, 4, 2), w (m, 4).
        """
        out = {"comp": [], "mid": [], "pts": [], "w": []}
        for p in range(self.m):
            a, d, L = self.v[p], self.t[p], self.len[p]
            ts = [0.0, 1.0]
            for g in xl:
                if abs(d[0]) > 1e-14:
                    s = (g - a[0]) / (d[0] * L)
                    if 0 < s < 1:
                        ts.append(s)
            for g in yl:
                if abs(d[1]) > 1e-14:
                    s = (g - a[1]) / (d[1] * L)
                    if 0 < s < 1:
                        ts.append(s)
            ts = np.unique(np.array(ts))
            t0, t1 = ts[:-1], ts[1:]
            tm = 0.5 * (t0 + t1)
            for k in range(len(tm)):
                q = t0[k] + (t1[k] - t0[k]) * GL_X
                out["comp"].append(p)
                out["mid"].append(a + d * L * tm[k])
                out["pts"].append(np.stack([a[0] + d[0] * L * q, a[1] + d[1] * L * q], axis=1))
                out["w"].append(GL_W * (t1[k] - t0[k]) * L)
        return {k: np.array(v) for k, v in out.items()}

    def alpha(self, p, x, y):
        """!
        @brief Robin coefficient of component p.
        @param p Component index.
        @param x x coordinates.
        @param y y coordinates.
        @return alpha values.
        """
        return self.alphas[p](x, y)

    def g(self, p, x, y):
        """!
        @brief Robin data g = mu du/dn + alpha u from the exact solution (mu = 1).
        @param p Component index.
        @param x x coordinates.
        @param y y coordinates.
        @return g values.
        """
        gx, gy = self.gu(x, y)
        return gx * self.n[p, 0] + gy * self.n[p, 1] + self.alpha(p, x, y) * self.u(x, y)


class Disc:
    """!
    @brief Disc domain (one smooth component).
    @param c Centre (2,).
    @param r Radius.
    @param alpha Callable alpha(x, y).
    @param u_exact Callable u(x, y).
    @param grad_exact Callable returning (ux, uy).
    """

    smooth_comps = True
    ncomp = 1

    def __init__(self, c, r, alpha, u_exact, grad_exact):
        """!
        @brief Store the disc and the data.
        @param c Centre.
        @param r Radius.
        @param alpha Robin coefficient.
        @param u_exact Exact solution.
        @param grad_exact Exact gradient.
        @return None
        """
        self.c = np.asarray(c, float)
        self.r = float(r)
        self.alpha_f = alpha
        self.u, self.gu = u_exact, grad_exact

    def phi_comp(self, p, x, y):
        """!
        @brief Signed distance to the circle (negative inside).
        @param p Component index (unused).
        @param x x coordinates.
        @param y y coordinates.
        @return d.
        """
        return np.hypot(x - self.c[0], y - self.c[1]) - self.r

    def foot(self, p, x, y):
        """!
        @brief Closest point on the circle.
        @param p Component index (unused).
        @param x x coordinates.
        @param y y coordinates.
        @return (xf, yf).
        """
        rr = np.hypot(x - self.c[0], y - self.c[1])
        return self.c[0] + self.r * (x - self.c[0]) / rr, self.c[1] + self.r * (y - self.c[1]) / rr

    def normal(self, p, x, y):
        """!
        @brief Outward normal at points on or near the circle.
        @param p Component index (unused).
        @param x x coordinates.
        @param y y coordinates.
        @return (nx, ny).
        """
        rr = np.hypot(x - self.c[0], y - self.c[1])
        return (x - self.c[0]) / rr, (y - self.c[1]) / rr

    def seg_len(self, x0, y0, x1, y1):
        """!
        @brief Length of a segment inside the disc (exact quadratic).
        @param x0 Start x.
        @param y0 Start y.
        @param x1 End x.
        @param y1 End y.
        @return Lengths.
        """
        dx, dy = x1 - x0, y1 - y0
        fx, fy = x0 - self.c[0], y0 - self.c[1]
        a = dx * dx + dy * dy
        b = 2 * (fx * dx + fy * dy)
        c = fx * fx + fy * fy - self.r ** 2
        disc = b * b - 4 * a * c
        ok = disc > 0
        sq = np.sqrt(np.where(ok, disc, 0.0))
        t0 = (-b - sq) / (2 * a)
        t1 = (-b + sq) / (2 * a)
        return np.where(ok, np.hypot(dx, dy) * np.clip(np.minimum(t1, 1) - np.maximum(t0, 0), 0, None), 0.0)

    def inside(self, x, y):
        """!
        @brief True inside the disc.
        @param x x coordinates.
        @param y y coordinates.
        @return Boolean array.
        """
        return self.phi_comp(0, x, y) < 0

    def poly_signed_distance(self, x, y):
        """!
        @brief Signed distance to the circle and the closest point.
        @param x x coordinates.
        @param y y coordinates.
        @return (d, xc, yc, comp).
        """
        fx, fy = self.foot(0, x, y)
        return self.phi_comp(0, x, y), fx, fy, np.zeros(np.shape(x), int)

    def pieces(self, xl, yl):
        """!
        @brief Arc pieces between the grid lines with quadrature points and weights.
        @param xl Vertical grid line coordinates.
        @param yl Horizontal grid line coordinates.
        @return Dict with comp, mid, pts, w.
        """
        th = [0.0, 2 * np.pi]
        for g in xl:
            q = (g - self.c[0]) / self.r
            if abs(q) < 1:
                a = np.arccos(q)
                th += [a % (2 * np.pi), (-a) % (2 * np.pi)]
        for g in yl:
            q = (g - self.c[1]) / self.r
            if abs(q) < 1:
                a = np.arcsin(q)
                th += [a % (2 * np.pi), (np.pi - a) % (2 * np.pi)]
        th = np.unique(np.array(th))
        out = {"comp": [], "mid": [], "pts": [], "w": []}
        for k in range(len(th) - 1):
            t0, t1 = th[k], th[k + 1]
            if t1 - t0 < 1e-15:
                continue
            q = t0 + (t1 - t0) * GL_X
            tm = 0.5 * (t0 + t1)
            out["comp"].append(0)
            out["mid"].append(self.c + self.r * np.array([np.cos(tm), np.sin(tm)]))
            out["pts"].append(np.stack([self.c[0] + self.r * np.cos(q), self.c[1] + self.r * np.sin(q)], axis=1))
            out["w"].append(GL_W * (t1 - t0) * self.r)
        return {k: np.array(v) for k, v in out.items()}

    def alpha(self, p, x, y):
        """!
        @brief Robin coefficient.
        @param p Component index (unused).
        @param x x coordinates.
        @param y y coordinates.
        @return alpha.
        """
        return self.alpha_f(x, y)

    def g(self, p, x, y):
        """!
        @brief Robin data from the exact solution (mu = 1).
        @param p Component index (unused).
        @param x x coordinates.
        @param y y coordinates.
        @return g.
        """
        gx, gy = self.gu(x, y)
        nx, ny = self.normal(0, x, y)
        return gx * nx + gy * ny + self.alpha(0, x, y) * self.u(x, y)


def solve(dom, n, shift=(0.0, 0.0), scheme="bg", floor=0.25, rational=False, f=None, lo=-1.0, hi=1.0, strips=64, kink_cond=1e4):
    """!
    @brief Solve -Laplace u = f in the domain with the Robin data of the exact solution on an n x n cell-centred grid.
    @param dom Domain (Triangle or Disc).
    @param n Number of cells per direction (grid points over [lo, hi], cell size h = (hi - lo)/(n - 1)).
    @param shift Grid shift in units of h.
    @param scheme One of bg, bg_nokink, film, nofilm.
    @param floor Floor of the film denominator (film scheme), relative to mu (0.25 in the program proposal).
    @param rational For the film scheme, replace the denominator by 1/(1 + alpha d) where the centre is outside the domain (d alpha > 0): the same slope at d = 0, positive for any alpha d.
    @param f Source callable f(x, y); default 2 u_exact (u = sin x cos y).
    @param lo Lower coordinate of the first node.
    @param hi Upper coordinate of the last node.
    @param strips Midpoint strips used for the cell area.
    @param kink_cond Condition number above which a kink cell falls back to separate pieces.
    @return Dict with u (n, n), active mask, X, Y, h, info counts.
    """
    h = (hi - lo) / (n - 1)
    xs = lo + shift[0] * h + np.arange(n) * h
    ys = lo + shift[1] * h + np.arange(n) * h
    X, Y = np.meshgrid(xs, ys)           # arrays indexed [j, i]
    # face lengths: vertical faces (between i and i+1), horizontal faces (between j and j+1)
    xf = xs[:-1] + 0.5 * h
    Lx = dom.seg_len(np.broadcast_to(xf[None, :], (n, n - 1)), np.broadcast_to((ys - 0.5 * h)[:, None], (n, n - 1)),
                     np.broadcast_to(xf[None, :], (n, n - 1)), np.broadcast_to((ys + 0.5 * h)[:, None], (n, n - 1))).copy()
    yf = ys[:-1] + 0.5 * h
    Ly = dom.seg_len(np.broadcast_to((xs - 0.5 * h)[None, :], (n - 1, n)), np.broadcast_to(yf[:, None], (n - 1, n)),
                     np.broadcast_to((xs + 0.5 * h)[None, :], (n - 1, n)), np.broadcast_to(yf[:, None], (n - 1, n))).copy()
    # cell areas by vertical strips (midpoint rule)
    V = np.zeros((n, n))
    for s in range(strips):
        xx = X - 0.5 * h + (s + 0.5) * h / strips
        V += dom.seg_len(xx, Y - 0.5 * h, xx, Y + 0.5 * h) * (h / strips)
    # boundary pieces binned to cells
    xl = np.concatenate([xs - 0.5 * h, [xs[-1] + 0.5 * h]])
    yl = np.concatenate([ys - 0.5 * h, [ys[-1] + 0.5 * h]])
    pc = dom.pieces(xl, yl)
    pi = np.floor((pc["mid"][:, 0] - xs[0]) / h + 0.5).astype(int)
    pj = np.floor((pc["mid"][:, 1] - ys[0]) / h + 0.5).astype(int)
    # a cell is a node of the system when any part of the domain touches it: a positive volume, a cut face or a boundary piece
    # (a sliver can have a volume below the strip resolution and still carry the flux of a cut face)
    active = V > 1e-10 * h * h
    touched = np.zeros((n, n), bool)
    touched[:, :-1] |= Lx > 0
    touched[:, 1:] |= Lx > 0
    touched[:-1, :] |= Ly > 0
    touched[1:, :] |= Ly > 0
    active |= touched
    # unknown numbering
    idx = -np.ones((n, n), int)
    idx[active] = np.arange(active.sum())
    N = int(active.sum())
    diag = np.zeros(N)
    rhs = np.zeros(N)
    rows, cols, vals = [], [], []
    # fluxes between cells (eq. 1.7), mu = 1
    for (Lf, di, dj) in ((Lx, 0, 1), (Ly, 1, 0)):
        for j in range(Lf.shape[0]):
            pass
    ii, jj = np.nonzero((Lx > 0) & active[:, :-1] & active[:, 1:])
    c = Lx[ii, jj] / h
    a, b = idx[ii, jj], idx[ii, jj + 1]
    np.add.at(diag, a, c)
    np.add.at(diag, b, c)
    rows += [a, b]; cols += [b, a]; vals += [-c, -c]
    ii, jj = np.nonzero((Ly > 0) & active[:-1, :] & active[1:, :])
    c = Ly[ii, jj] / h
    a, b = idx[ii, jj], idx[ii + 1, jj]
    np.add.at(diag, a, c)
    np.add.at(diag, b, c)
    rows += [a, b]; cols += [b, a]; vals += [-c, -c]
    # source f(r_ij) V
    if f is None:
        def f(x, y):
            return 2.0 * dom.u(x, y)
    rhs[idx[active]] += f(X[active], Y[active]) * V[active]
    # Robin terms per cell
    cellp = {}
    for k in range(len(pc["comp"])):
        i, j = pi[k], pj[k]
        if 0 <= i < n and 0 <= j < n and active[j, i]:
            cellp.setdefault((j, i), []).append(k)
    stats = {"kink": 0, "kink_fallback": 0, "floor_hits": 0, "negative_denominator": 0}
    for (j, i), ks in cellp.items():
        r = idx[j, i]
        x0, y0 = X[j, i], Y[j, i]
        Lp = np.array([pc["w"][k].sum() for k in ks])
        ints_g = np.array([(pc["w"][k] * dom.g(pc["comp"][k], pc["pts"][k][:, 0], pc["pts"][k][:, 1])).sum() for k in ks])
        comps = [pc["comp"][k] for k in ks]
        if scheme == "nofilm":
            for k, p in zip(ks, comps):
                al = dom.alpha(p, pc["pts"][k][:, 0], pc["pts"][k][:, 1])
                diag[r] += (pc["w"][k] * al).sum()
            rhs[r] += ints_g.sum()
            continue
        if scheme == "film":
            # one distance per cell (closest point of the whole outline, floored denominator), each piece with its own alpha and g
            d, cx, cy, cp = dom.poly_signed_distance(np.array([x0]), np.array([y0]))
            d = float(d[0])
            for p in dict.fromkeys(comps):
                grp = [k for k, q in zip(ks, comps) if q == p]
                L = sum(pc["w"][k].sum() for k in grp)
                ig = sum((pc["w"][k] * dom.g(p, pc["pts"][k][:, 0], pc["pts"][k][:, 1])).sum() for k in grp)
                fx, fy = dom.foot(p, np.array([x0]), np.array([y0]))
                al = float(dom.alpha(p, fx, fy)[0])
                gg = float(dom.g(p, fx, fy)[0])
                den = 1.0 - al * d
                if den < 0.0:
                    stats["negative_denominator"] += 1
                if den < floor:
                    stats["floor_hits"] += 1
                    den = floor
                if rational and d * al > 0.0:
                    # same first-order slope as 1 - alpha d, but positive and bounded for any alpha d
                    den = 1.0 / (1.0 + al * d)
                # series film: the data g = alpha u_ambient enters with the same factor as the conductance (the program's form),
                # which keeps the pair (diag, rhs) consistent when the denominator is floored; without the floor it equals eq. 1.14
                diag[r] += al * L / den
                rhs[r] += ig / den
            continue
        kinkcell = (len(ks) >= 2 and len(set(comps)) >= 2 and scheme == "bg")
        if kinkcell:
            stats["kink"] += 1
            # keep the first piece of each of the first two components
            sel = []
            for p in dict.fromkeys(comps):
                sel.append([k for k, q in zip(ks, comps) if q == p])
            if len(sel) == 2:
                rho = []; nn = []; aa = []; gg = []
                for grp in sel:
                    p = pc["comp"][grp[0]]
                    wsum = sum(pc["w"][k].sum() for k in grp)
                    cen = sum((pc["w"][k][:, None] * pc["pts"][k]).sum(axis=0) for k in grp) / wsum
                    fx, fy = dom.foot(p, np.array([cen[0]]), np.array([cen[1]]))
                    nx_, ny_ = dom.normal(p, fx, fy)
                    rho.append((fx[0], fy[0])); nn.append((nx_[0], ny_[0]))
                    aa.append(float(dom.alpha(p, fx, fy)[0])); gg.append(float(dom.g(p, fx, fy)[0]))
                Nm = np.array([[nn[q][0] + aa[q] * (rho[q][0] - x0), nn[q][1] + aa[q] * (rho[q][1] - y0)] for q in range(2)])
                if np.linalg.cond(Nm) < kink_cond:
                    av = np.linalg.solve(Nm, np.array(aa))
                    bv = np.linalg.solve(Nm, np.array(gg))
                    for k in ks:
                        p = pc["comp"][k]
                        px, py = pc["pts"][k][:, 0], pc["pts"][k][:, 1]
                        al = dom.alpha(p, px, py)
                        wq = pc["w"][k]
                        dr = np.stack([px - x0, py - y0], axis=1)
                        diag[r] += (wq * al * (1.0 - dr @ av)).sum()
                        rhs[r] += (wq * dom.g(p, px, py)).sum() - (wq * al * (dr @ bv)).sum()
                    continue
                stats["kink_fallback"] += 1
        # smooth cell (or kink cell without the kink treatment): eq. 1.14 per component
        for p in dict.fromkeys(comps):
            grp = [k for k, q in zip(ks, comps) if q == p]
            L = sum(pc["w"][k].sum() for k in grp)
            ig = sum((pc["w"][k] * dom.g(p, pc["pts"][k][:, 0], pc["pts"][k][:, 1])).sum() for k in grp)
            d = float(dom.phi_comp(p, np.array([x0]), np.array([y0]))[0])
            fx, fy = dom.foot(p, np.array([x0]), np.array([y0]))
            al = float(dom.alpha(p, fx, fy)[0])
            gg = float(dom.g(p, fx, fy)[0])
            den = 1.0 - al * d
            if den <= 0.0:
                stats["negative_denominator"] += 1
            diag[r] += al * L / den
            rhs[r] += ig + gg * d * al * L / den
    A = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(N, N)).tocsr() + sp.diags(diag)
    sol = spla.spsolve(A.tocsc(), rhs)
    u = np.full((n, n), np.nan)
    u[active] = sol
    return {"u": u, "active": active, "X": X, "Y": Y, "h": h, "stats": stats, "A": A, "V": V}


def errors(dom, res):
    """!
    @brief L-infinity errors of the solution (cell centres inside the domain) and of its central-difference gradient.
    @param dom Domain.
    @param res Result of `solve`.
    @return (err_u, err_grad).
    """
    X, Y, u, h = res["X"], res["Y"], res["u"], res["h"]
    ins = dom.inside(X, Y) & res["active"]
    ue = dom.u(X, Y)
    eu = np.abs(u - ue)[ins].max()
    # gradient by central differences where the whole 3 x 3 stencil is inside
    ok = ins.copy()
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            ok &= np.roll(np.roll(ins, di, axis=1), dj, axis=0)
    ok[0, :] = ok[-1, :] = False
    ok[:, 0] = ok[:, -1] = False
    ux = (np.roll(u, -1, axis=1) - np.roll(u, 1, axis=1)) / (2 * h)
    uy = (np.roll(u, -1, axis=0) - np.roll(u, 1, axis=0)) / (2 * h)
    gx, gy = dom.gu(X, Y)
    eg = np.maximum(np.abs(ux - gx), np.abs(uy - gy))[ok].max() if ok.any() else np.nan
    return float(eu), float(eg)


def u_ex(x, y):
    """!
    @brief The exact solution of the thesis section 1.5.2 triangle test, sin(x) cos(y).
    @param x x coordinates.
    @param y y coordinates.
    @return u.
    """
    return np.sin(x) * np.cos(y)


def grad_ex(x, y):
    """!
    @brief Gradient of `u_ex`.
    @param x x coordinates.
    @param y y coordinates.
    @return (ux, uy).
    """
    return np.cos(x) * np.cos(y), -np.sin(x) * np.sin(y)


def thesis_triangle():
    """!
    @brief The triangle of the thesis section 1.5.2 (corners (0.74, -0.86), (-0.83, -0.11), (0.37, 0.87)) with alpha 1, 0 and x - y + (x + y)^2 on the right, bottom and left sides.
    @return Triangle domain.
    """
    # counter-clockwise order; edge k joins v[k] to v[k+1]
    v = [(0.74, -0.86), (0.37, 0.87), (-0.83, -0.11)]
    # edge 0: right side, edge 1: left side (upper), edge 2: bottom? check below by geometry
    verts = np.array(v)
    # orientation: make counter-clockwise
    area = 0.5 * np.sum(verts[:, 0] * np.roll(verts[:, 1], -1) - np.roll(verts[:, 0], -1) * verts[:, 1])
    if area < 0:
        verts = verts[::-1]
    # classify the three sides by their mid-point: right (largest x), bottom (lowest y), left (smallest x - y)
    mids = 0.5 * (verts + np.roll(verts, -1, axis=0))
    right = int(np.argmax(mids[:, 0]))
    rest = [k for k in range(3) if k != right]
    bottom = rest[int(np.argmin([mids[k, 1] for k in rest]))]
    left = [k for k in rest if k != bottom][0]
    al = [None] * 3
    al[right] = lambda x, y: np.ones_like(x)
    al[bottom] = lambda x, y: np.zeros_like(x)
    al[left] = lambda x, y: x - y + (x + y) ** 2
    return Triangle(verts, al, u_ex, grad_ex)


def disc_domain(alpha_scale=1.0):
    """!
    @brief A disc (centre (0.1, -0.05), radius 0.7) with the positive coefficient alpha = alpha_scale (2 + sin(x + y)) and u = sin x cos y.
    @param alpha_scale Multiplier of the Robin coefficient (large values make the edge stiff).
    @return Disc domain.
    """
    return Disc((0.1, -0.05), 0.7, lambda x, y: alpha_scale * (2.0 + np.sin(x + y)), u_ex, grad_ex)
