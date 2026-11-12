#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cutlinks.py
@brief Prototype (outside the program) of the cut-cell schemes for the layered FVM on top of the exact board cover: lateral links from the real shape of the cell and the boundary film.
@details The program on this branch (`fix/exact-board-cover`) already has the exact cover of every cell (`Board.cover` by clipping), so the volumes, the edge
         length and the part weights are exact. What remains is how a cut cell is joined to its neighbours and to the air through its outline. The program joins
         two cells with the harmonic mean of the cover-scaled sheets over one cell width and puts the edge film on the node. Here a subclass of
         `pcbthermal.fvm.Network` adds to the program's own matrix the difference between the links of a scheme and the program's links, and changes the edge film.
         Schemes (`SCHEMES`):

         - `program`           the unmodified network (exact cover, links `harmonic(S c1, S c2) dy / dx`, film on the node);
         - `aperture`          nodes at the cell centres, link `a S dy / dx` with `a` the open fraction of the shared face (Johansen and Colella eq. 15, 16 reduced to the
                               two-point form), film on the node;
         - `aperture+film`     as `aperture`, the film in series with the conduction from the cell centre to the closest outline point,
                               `g = g0 / (1 + g0 d / (S L))`, `d` the signed distance (negative when the centre is outside), the Robin treatment that Barrett and others
                               (eq. 12 to 14) take from Bochkov and Gibou; the factor `1 + g0 d / (S L)` is floored at `film_floor` so that the film cannot be more than `1/film_floor` times stiffer;
         - `links`             nodes at the centroids of the board part, link `a S dy / (d1 + d2)` with the distances from the face to the two centroids along the normal;
         - `links+film`        `links` with the same film, `d` measured from the centroid;
         - `links+strip`       `links` with the conduction over half the depth of the board strip in series with the film (the earlier prototype).

         Only the lateral links of the copper and laminate node layers of boards without imported copper and without a metal block are changed; the vertical links,
         the vias, the capacities and the heat sources are the program's.
"""

import contextlib
import os
import sys

import numpy as np
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from pcbthermal import fvm                                      # noqa: E402
from pcbthermal.geometry import points_in_polygon               # noqa: E402
import cutgeom                                                  # noqa: E402

SCHEMES = ("program", "aperture", "aperture+film", "links", "links+film", "links+strip")


def signed_distance(poly, x, y, chunk=4000):
    """!
    @brief Signed distance from points to the closest point of a polygon (positive inside).
    @param poly Outline (n, 2) in metres.
    @param x X of the points (1-D array).
    @param y Y of the points (1-D array).
    @param chunk Points per block (keeps the block of distances small).
    @return Array of distances in metres.
    """
    poly = np.asarray(poly, dtype=float)
    a, b = poly, np.roll(poly, -1, axis=0)
    ab = b - a
    ll = np.maximum((ab ** 2).sum(axis=1), 1e-300)
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    out = np.empty(len(x))
    for s in range(0, len(x), chunk):
        px, py = x[s:s + chunk, None], y[s:s + chunk, None]
        t = np.clip(((px - a[:, 0]) * ab[:, 0] + (py - a[:, 1]) * ab[:, 1]) / ll, 0.0, 1.0)
        d2 = (px - a[:, 0] - t * ab[:, 0]) ** 2 + (py - a[:, 1] - t * ab[:, 1]) ** 2
        out[s:s + chunk] = np.sqrt(d2.min(axis=1))
    inside = points_in_polygon(x, y, poly)
    return np.where(inside, out, -out)


class CutLinkNetwork(fvm.Network):
    """!
    @brief The layered FVM network with the lateral links and the edge film of a cut-cell scheme.
    @details Class attributes set before a build: `mode` (one of SCHEMES), `film_floor` (smallest value of `1 + g0 d/(S L)`), `d_min` (smallest face-to-centroid
             distance, fraction of the cell side), `film_rect` (apply the film to the border cells of a board without an outline too).
    """

    mode = "links"
    film_floor = 0.25
    d_min = 1e-3
    film_rect = False

    def __init__(self, problem, nx, ny, assemble=True, with_blocks=True, ladder=True):
        """!
        @brief Build the program's network without the matrix, add the geometry of the cut cells and the film, then assemble.
        @param problem A validated Problem (no metal block, no imported copper).
        @param nx Cells along x.
        @param ny Cells along y.
        @param assemble False leaves the matrix unbuilt.
        @param with_blocks Passed on.
        @param ladder Passed on.
        @throws ValueError If the problem has a metal block or imported copper.
        """
        if any(s.is_block() for s in problem.heatsinks):
            raise ValueError("the prototype does not handle metal blocks")
        if getattr(problem, "imported", None):
            raise ValueError("the prototype does not handle imported copper")
        # 2.6.0 adopted `aperture+film` into the program (`cut_cells=True` by default) and added the laminate edge band; the schemes of this study are built on the
        # earlier network (cut cells off, no band), which is what `program` meant when the tables were made (audit 2.6.1: without this the links and the film were
        # counted twice, once by the program and once by the prototype)
        with _no_edge_band():
            super().__init__(problem, nx, ny, assemble=False, with_blocks=with_blocks, ladder=ladder, cut_cells=False)
        b = problem.board
        self.geo = None
        self.film_factor = None
        if b.has_outline():
            self.geo = cutgeom.cut_geometry_exact(b.outline, nx, ny, self.dx, self.dy)
            if self.mode.endswith("+film") or self.mode == "links+strip":
                self._film(b.outline)
        elif self.film_rect and self.mode.endswith("+film"):
            self._film_rect()
        self.K = self._assemble() if assemble else None

    def _physical_sheet(self):
        """!
        @brief Sheet conductance per square of every node layer without the cover factor (W/K), zero off the board.
        @return Array (nl, ny, nx).
        """
        out = np.zeros_like(self.S)
        np.divide(self.S, self.cover[None], out=out, where=self.cover[None] > 0)
        return out

    def _film(self, outline):
        """!
        @brief Put the conduction from the node to the closest outline point in series with the edge film (modes +film and +strip).
        @param outline Outline polygon (n, 2) in metres.
        """
        L = self._edge_lengths()
        sp_ = self._physical_sheet()
        g0 = self.g_side.copy()
        cells = np.argwhere(L > 0)
        if self.mode == "links+strip":
            with np.errstate(divide="ignore", invalid="ignore"):
                depth = 0.5 * np.minimum(self.cover * self.dx * self.dy / L, max(self.dx, self.dy))
            d = np.where(L > 0, depth, 0.0)
        else:
            use_centroid = self.mode.startswith("links")
            xc = self.geo["xc"] if use_centroid else (np.arange(self.nx)[None, :] + 0.5) * self.dx * np.ones((self.ny, 1))
            yc = self.geo["yc"] if use_centroid else (np.arange(self.ny)[:, None] + 0.5) * self.dy * np.ones((1, self.nx))
            d = np.zeros((self.ny, self.nx))
            if len(cells):
                d[cells[:, 0], cells[:, 1]] = signed_distance(outline, xc[cells[:, 0], cells[:, 1]], yc[cells[:, 0], cells[:, 1]])
        with np.errstate(divide="ignore", invalid="ignore"):
            # 1 + g0 d / (S L) per node layer
            fac = 1.0 + np.where((sp_ > 0) & (L[None] > 0), g0 * d[None] / (sp_ * L[None]), 0.0)
        fac = np.where(g0 > 0, np.maximum(fac, self.film_floor), 1.0)
        g_new = np.where(g0 > 0, g0 / fac, 0.0)
        self.g_amb = self.g_amb + (g_new - g0)
        self.g_side = g_new
        self.film_factor = fac

    def _film_rect(self):
        """!
        @brief The film in series with the conduction over half a cell on the four borders of a board without an outline (the node is half a cell from the edge).
        @details The factor is `1 + H d / S` with `H` the film per length of edge (g_side over the length) and `d` the half cell normal to the edge, the same expression as
                 for an outline (the length cancels), so a rectangle and the same rectangle drawn as an outline give the same network.
        """
        dx, dy, nx, ny = self.dx, self.dy, self.nx, self.ny
        if nx < 3 or ny < 3:
            return
        g0 = self.g_side
        sp_ = self._physical_sheet()
        left = np.zeros((ny, nx), bool); right = left.copy(); bottom = left.copy(); top = left.copy()
        left[:, 0] = True; right[:, -1] = True; bottom[0, :] = True; top[-1, :] = True
        corner = (left | right) & (bottom | top)
        # Film per length of edge: g_side over the edge length of the cell (a corner cell has two edges with the same H)
        H = np.zeros_like(g0)
        lx = np.where(left | right, dy, 0.0) + np.where(bottom | top, dx, 0.0)
        np.divide(g0, lx[None], out=H, where=lx[None] > 0)
        new = g0.copy()
        with np.errstate(divide="ignore", invalid="ignore"):
            for mask, length, d in ((left | right, dy, 0.5 * dx), (bottom | top, dx, 0.5 * dy)):
                fac = np.where(sp_ > 0, 1.0 + H * d / sp_, 1.0)
                fac = np.maximum(fac, self.film_floor)
                old_e = H * length * mask[None]
                new = new - old_e + old_e / fac
        del corner
        self.g_amb = self.g_amb + (new - g0)
        self.g_side = new
        self.film_factor = None

    def _lateral_links(self):
        """!
        @brief Conductances (W/K) of the lateral links of every node layer for the scheme.
        @return Tuple (gx, gy): shapes (nl, ny, nx - 1) and (nl, ny - 1, nx).
        """
        if self.geo is None or self.mode == "program":
            return super()._lateral_links()                   # the earlier links (cover-scaled harmonic mean; cut cells are off)
        dx, dy, nx, ny = self.dx, self.dy, self.nx, self.ny
        g = self.geo
        sp_ = self._physical_sheet()
        act = self.active
        centroid = self.mode.startswith("links")
        xf = (np.arange(1, nx) * dx)[None, :]
        if centroid:
            d1 = np.maximum(xf - g["xc"][:, :-1], self.d_min * dx)
            d2 = np.maximum(g["xc"][:, 1:] - xf, self.d_min * dx)
        else:
            d1 = d2 = np.full_like(g["xc"][:, :-1], 0.5 * dx)
        ap = g["ax"] * (act[:, :-1] & act[:, 1:])
        s1, s2 = sp_[:, :, :-1], sp_[:, :, 1:]
        with np.errstate(divide="ignore", invalid="ignore"):
            r = d1[None] / s1 + d2[None] / s2
            gx = np.where((s1 > 0) & (s2 > 0), ap[None] * dy / r, 0.0)
        yf = (np.arange(1, ny) * dy)[:, None]
        if centroid:
            d1 = np.maximum(yf - g["yc"][:-1], self.d_min * dy)
            d2 = np.maximum(g["yc"][1:] - yf, self.d_min * dy)
        else:
            d1 = d2 = np.full_like(g["yc"][:-1], 0.5 * dy)
        ap = g["ay"] * (act[:-1] & act[1:])
        s1, s2 = sp_[:, :-1, :], sp_[:, 1:, :]
        with np.errstate(divide="ignore", invalid="ignore"):
            r = d1[None] / s1 + d2[None] / s2
            gy = np.where((s1 > 0) & (s2 > 0), ap[None] * dx / r, 0.0)
        return gx, gy

    def _program_links(self):
        """!
        @brief The program's own lateral links.
        @return Tuple (gx, gy).
        """
        gx = self._harmonic(self.S[:, :, :-1], self.S[:, :, 1:]) * self.dy / self.dx
        gy = self._harmonic(self.S[:, :-1, :], self.S[:, 1:, :]) * self.dx / self.dy
        return gx, gy

    def _assemble(self):
        """!
        @brief The program's matrix plus the difference between the scheme's links and the program's links.
        @return scipy.sparse.csr_matrix.
        """
        K = super()._assemble()
        if self.geo is None or self.mode == "program" or hasattr(fvm.Network, "_lateral_links"):
            # 2.6.0: the program's assembly reads its links through `_lateral_links`, which this class overrides, so K already holds the scheme's links
            return K
        L, ny, nx = self.nl, self.ny, self.nx
        idx = np.arange(L * ny * nx).reshape(L, ny, nx)
        gx1, gy1 = self._lateral_links()
        gx0, gy0 = self._program_links()
        rows, cols, vals = [], [], []
        for a_idx, b_idx, d in ((idx[:, :, :-1], idx[:, :, 1:], gx1 - gx0), (idx[:, :-1, :], idx[:, 1:, :], gy1 - gy0)):
            a, bb, dd = a_idx.ravel(), b_idx.ravel(), d.ravel()
            keep = dd != 0
            a, bb, dd = a[keep], bb[keep], dd[keep]
            rows.extend([a, bb, a, bb])
            cols.extend([a, bb, bb, a])
            vals.extend([dd, dd, -dd, -dd])
        n = L * ny * nx
        D = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
        return (K + D).tocsr()

    # The point SOR and the CG of the program use their own copies of the links; the studies use the direct solver only
    def solve_sor(self, *a, **k):
        """!
        @brief Not available in the prototype (the studies use the direct solver).
        @param a Ignored.
        @param k Ignored.
        @throws NotImplementedError Always.
        """
        raise NotImplementedError("the prototype is for the direct solver")


@contextlib.contextmanager
def _no_edge_band():
    """!
    @brief Switch off the laminate edge band of 2.6.0 (`laminate.edge_band`) for a block, so that the schemes are studied on the earlier plan of the laminate nodes.
    @return Context manager.
    """
    from pcbthermal import laminate
    saved = laminate.edge_band
    laminate.edge_band = lambda edge, d, dx, active: np.zeros(np.shape(active), dtype=bool)
    try:
        yield
    finally:
        laminate.edge_band = saved


@contextlib.contextmanager
def using(mode="links", film_floor=0.25, d_min=1e-3, film_rect=False):
    """!
    @brief Replace `fvm.Network` by the prototype for the duration of a block.
    @param mode One of SCHEMES.
    @param film_floor Smallest value of the film denominator.
    @param d_min Smallest face-to-centroid distance as a fraction of the cell.
    @param film_rect Apply the film to a board without an outline too.
    @return Context manager (yields the network class).
    @throws ValueError If the mode is unknown.
    """
    if mode not in SCHEMES:
        raise ValueError(f"mode must be one of {SCHEMES}")
    CutLinkNetwork.mode, CutLinkNetwork.film_floor = mode, film_floor
    CutLinkNetwork.d_min, CutLinkNetwork.film_rect = d_min, film_rect
    original = fvm.Network
    fvm.Network = CutLinkNetwork
    try:
        yield CutLinkNetwork
    finally:
        fvm.Network = original


def solve(problem, cell_mm, scheme="program", **kw):
    """!
    @brief Full steady result of the layered FVM with a scheme.
    @param problem Problem.
    @param cell_mm Cell in mm.
    @param scheme One of SCHEMES (`program` is the network before 2.6.0: exact cover, cut cells off, no edge band) or `current` (the program of the tree, `fvm.solve_steady`).
    @param kw Options of `using`.
    @return pcbthermal.results.SteadyResult.
    """
    if scheme == "current":
        return fvm.solve_steady(problem, cell_mm=cell_mm)
    with using(scheme, **kw):
        return fvm.solve_steady(problem, cell_mm=cell_mm)


def tmax(problem, cell_mm, scheme="program", **kw):
    """!
    @brief Hottest board temperature for a scheme.
    @param problem Problem.
    @param cell_mm Cell in mm.
    @param scheme One of SCHEMES.
    @param kw Options of `using`.
    @return degC.
    """
    return float(solve(problem, cell_mm, scheme, **kw).t_max)


def matrix_checks(problem, cell_mm, scheme):
    """!
    @brief Structure of the system matrix of a scheme: symmetry, M-matrix property, positive definiteness, conditioning.
    @param problem Problem.
    @param cell_mm Cell in mm.
    @param scheme One of SCHEMES.
    @return dict(n, asym, pos_offdiag, min_diag_dominance, lam_min, lam_max, cond, ratio_max): the largest relative asymmetry, the number of positive
            off-diagonal entries, the smallest (diagonal - sum |off|) / diagonal (negative: not diagonally dominant), the extreme eigenvalues of the
            symmetric matrix scaled by its diagonal (a Jacobi scaling, which is what the point iteration sees) and their ratio.
    """
    import scipy.sparse.linalg as spla
    from pcbthermal import model
    problem.validate()
    nx = max(int(round(problem.board.width * 1000.0 / cell_mm)), 1)
    ny = max(int(round(problem.board.height * 1000.0 / cell_mm)), 1)
    if scheme == "current":
        net = fvm.Network(problem, nx, ny)
    else:
        CutLinkNetwork.mode = scheme
        net = CutLinkNetwork(problem, nx, ny)
    K = net.K.tocsr()
    act = np.repeat(net.active.ravel()[None, :], net.nl, axis=0).ravel() if net.nl else None
    keep = np.nonzero(act)[0]
    K = K[keep][:, keep].tocsr()
    asym = abs(K - K.T).max() / max(abs(K).max(), 1e-300)
    off = K - sp.diags(K.diagonal())
    pos = int((off.data > 1e-14 * abs(K).max()).sum())
    absoff = abs(off).sum(axis=1).A1
    dd = float(((K.diagonal() - absoff) / K.diagonal()).min())
    Dm = sp.diags(1.0 / np.sqrt(K.diagonal()))
    A = (Dm @ K @ Dm).tocsc()
    lmax = spla.eigsh(A, k=1, which="LA", return_eigenvectors=False)[0]
    lmin = spla.eigsh(A, k=1, sigma=0.0, which="LM", return_eigenvectors=False)[0]
    return {"n": int(K.shape[0]), "asym": float(asym), "pos_offdiag": pos, "min_diag_dominance": dd,
            "lam_min": float(lmin), "lam_max": float(lmax), "cond": float(lmax / lmin)}
