#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fvm_cutcell.py
@brief Prototype of the cut-cell treatment (option P1) for the layered finite-volume model, written as a subclass of `pcbthermal.fvm.Network` outside the program.
@details The program's FVM scales the sheet conductance of a cell by its board cover and joins two cells with the harmonic mean of the scaled
         values over the distance between the cell centres (`fvm.Network._assemble`). On a cell that the outline cuts this is wrong in the direction
         that crosses the cut (a half cell of board is reached through half the cross-section over a full cell width, and the heat has to cross only
         three quarters of a cell, not one) and right only along the edge.

         The cut-cell scheme of this prototype keeps everything else of the network (cover, capacities, vertical links, films, vias, laminate nodes)
         and replaces the lateral links (and optionally the edge film) by values from the real shape of the cell (`cutcell.cut_geometry`):

         - the node of a cut cell lives at the centroid of its board part;
         - the conductance between two neighbours is the aperture of the shared face (the board fraction of its length) times the face length times the
           physical sheet conductance, over the series resistance `d1 / S1 + d2 / S2` of the distances from the face to the two centroids, measured along
           the face normal (two-point flux, symmetric, the same stencil as the 3D copy `rotsq.CUT_LINKS`);
         - mode "aperture" keeps the nodes at the cell centres (as the program and as Johansen and Colella's cell-centred values) and changes only the
           cross-section of the link to the aperture;
         - mode "links+strip" also puts the conduction from the centroid to the outline (half the depth of the board strip, `0.5 c dx dy / L`) in series
           with the edge film; mode "links" leaves the film on the node as the program does.

         The program itself is not edited: `CutCellNetwork` is plugged in by `with using_cutcell(mode): fvm.solve_steady(...)`, which replaces
         `fvm.Network` for the block. Boards with metal blocks are refused (their layers carry another scaling of S).
"""

import contextlib
import os
import sys

import numpy as np
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from pcbthermal import fvm                                                  # noqa: E402
import cutcell                                                              # noqa: E402
import cutcell_exact                                                        # noqa: E402

MODES = ("links", "links+strip", "aperture")


class CutCellNetwork(fvm.Network):
    """!
    @brief The layered FVM network with the lateral links (and optionally the edge film) of the cut-cell scheme.
    @details Class attributes set the variant before a build: `mode` (one of MODES), `samples` (the sampling M x M per cell of the geometry),
             `d_min` (smallest distance from a face to a centroid, as a fraction of the cell side; limits the conductance of a link between two
             slivers that straddle a face) and `ap_min` (apertures below this fraction of the face are taken as zero).
    """

    mode = "links"
    samples = 16
    d_min = 1e-3
    ap_min = 0.0
    exact = False

    def __init__(self, problem, nx, ny, assemble=True, with_blocks=True, ladder=True):
        """!
        @brief Build the program's network without the matrix, add the geometry of the cut cells, then assemble.
        @param problem A validated Problem (no metal blocks).
        @param nx Cells along x.
        @param ny Cells along y.
        @param assemble False leaves the matrix unbuilt (as the parent).
        @param with_blocks Passed on.
        @param ladder Passed on.
        @throws ValueError If the problem has a metal block.
        """
        if any(s.is_block() for s in problem.heatsinks):
            raise ValueError("the cut-cell prototype does not handle metal blocks")
        super().__init__(problem, nx, ny, assemble=False, with_blocks=with_blocks, ladder=ladder)
        b = problem.board
        self.geo = None
        if b.has_outline():
            geo_fn = cutcell_exact.cut_geometry_exact if self.exact else cutcell.cut_geometry_fast
            self.geo = geo_fn(b.outline, nx, ny, self.dx, self.dy, m=self.samples)
            if self.mode == "links+strip":
                self._strip_edge()
        self.K = self._assemble() if assemble else None

    def _physical_sheet(self):
        """!
        @brief Sheet conductance per square of every node layer, without the cover factor (W/K).
        @return Array (nl, ny, nx), zero where the cell is off the board.
        """
        out = np.zeros_like(self.S)
        np.divide(self.S, self.cover[None], out=out, where=self.cover[None] > 0)
        return out

    def _strip_edge(self):
        """!
        @brief Put the conduction from the node to the outline in series with the edge film (mode "links+strip").
        @details The distance is half the depth of the board strip behind the outline in the cell, `0.5 min(c dx dy / L, max(dx, dy))` (a whole edge
                 cell: dx / 2); g_side and g_amb change together so that the energy balance of `power_out` still adds up.
        """
        L = self._edge_lengths()
        sp_ = self._physical_sheet()
        with np.errstate(divide="ignore", invalid="ignore"):
            depth = 0.5 * np.minimum(self.cover * self.dx * self.dy / L, max(self.dx, self.dy))
            r_cond = depth[None] / (sp_ * L[None])
            g_old = self.g_side
            g_new = np.where(g_old > 0, 1.0 / (1.0 / g_old + np.nan_to_num(r_cond, nan=0.0, posinf=0.0)), 0.0)
        self.g_amb = self.g_amb + (g_new - g_old)
        self.g_side = g_new

    def _lateral_links(self):
        """!
        @brief Conductances (W/K) of the lateral links of every node layer.
        @return Tuple (gx, gy): shapes (nl, ny, nx - 1) and (nl, ny - 1, nx).
        """
        if self.geo is None:
            # A rectangle: the program's own expressions (cover is one everywhere), so the matrix is the program's
            gx = self._harmonic(self.S[:, :, :-1], self.S[:, :, 1:]) * self.dy / self.dx
            gy = self._harmonic(self.S[:, :-1, :], self.S[:, 1:, :]) * self.dx / self.dy
            return gx, gy
        dx, dy, nx, ny = self.dx, self.dy, self.nx, self.ny
        g = self.geo
        sp_ = self._physical_sheet()
        act = self.active
        # x links: face between column j and j + 1 at x = (j + 1) dx; distances along x from the face to the two centroids
        xf = (np.arange(1, nx) * dx)[None, :]
        if self.mode == "aperture":
            # Johansen-Colella form: nodes stay at the cell centres, only the cross-section of the link is the aperture
            d1 = d2 = np.full_like(g["xc"][:, :-1], 0.5 * dx)
        else:
            d1 = np.maximum(xf - g["xc"][:, :-1], self.d_min * dx)
            d2 = np.maximum(g["xc"][:, 1:] - xf, self.d_min * dx)
        ap = g["ax"] * (act[:, :-1] & act[:, 1:])
        ap = np.where(ap < self.ap_min, 0.0, ap)
        s1, s2 = sp_[:, :, :-1], sp_[:, :, 1:]
        with np.errstate(divide="ignore", invalid="ignore"):
            r = d1[None] / s1 + d2[None] / s2
            gx = np.where((s1 > 0) & (s2 > 0), ap[None] * dy / r, 0.0)
        yf = (np.arange(1, ny) * dy)[:, None]
        if self.mode == "aperture":
            d1 = d2 = np.full_like(g["yc"][:-1], 0.5 * dy)
        else:
            d1 = np.maximum(yf - g["yc"][:-1], self.d_min * dy)
            d2 = np.maximum(g["yc"][1:] - yf, self.d_min * dy)
        ap = g["ay"] * (act[:-1] & act[1:])
        ap = np.where(ap < self.ap_min, 0.0, ap)
        s1, s2 = sp_[:, :-1, :], sp_[:, 1:, :]
        with np.errstate(divide="ignore", invalid="ignore"):
            r = d1[None] / s1 + d2[None] / s2
            gy = np.where((s1 > 0) & (s2 > 0), ap[None] * dx / r, 0.0)
        return gx, gy

    def _program_links(self):
        """!
        @brief The lateral links of the program's own assembly (harmonic mean of the cover-scaled sheets, imported faces), as `fvm.Network._assemble` builds them.
        @return Tuple (gx, gy): shapes (nl, ny, nx - 1) and (nl, ny - 1, nx).
        """
        gx = self._harmonic(self.S[:, :, :-1], self.S[:, :, 1:]) * self.dy / self.dx
        gy = self._harmonic(self.S[:, :-1, :], self.S[:, 1:, :]) * self.dx / self.dy
        for layer, (fx, fy) in self._imported_faces().items():
            on = self.active
            gx[layer] = fx * (on[:, :-1] & on[:, 1:])
            gy[layer] = fy * (on[:-1, :] & on[1:, :])
        return gx, gy

    def _links_for_solvers(self):
        """!
        @brief The lateral links of the variant with the imported layers left as the program builds them (the reduced sheet has its own faces).
        @return Tuple (gx, gy) as `_lateral_links`.
        """
        gx, gy = self._lateral_links()
        if self.geo is not None:
            gx0, gy0 = self._program_links()
            for layer in self._imported_faces():
                gx[layer], gy[layer] = gx0[layer], gy0[layer]
        return gx, gy

    def _assemble(self):
        """!
        @brief The program's matrix plus the difference between the cut-cell links and the program's links (a development-proof way to swap the links).
        @details The parent builds K with every other term (vertical links, vias, laminate nodes, films); only the lateral couplings change, so the difference is
                 added as symmetric couplings (it may be negative). Without an outline the parent's matrix is returned untouched.
        @return scipy.sparse.csr_matrix.
        """
        K = super()._assemble()
        if self.geo is None:
            return K
        L, ny, nx = self.nl, self.ny, self.nx
        idx = np.arange(L * ny * nx).reshape(L, ny, nx)
        gx1, gy1 = self._links_for_solvers()
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


def _patched_sor():
    """!
    @brief The parent's `solve_sor` with its own lateral-link block replaced by a call to `_links_for_solvers` (so the point SOR sees the cut-cell links).
    @details The text of the parent method is edited in memory and refused when the block is not found exactly once (the program changed).
    @return Function to install as `CutCellNetwork.solve_sor`.
    @throws RuntimeError If the block of the parent was not found.
    """
    import inspect
    import textwrap
    text = textwrap.dedent(inspect.getsource(fvm.Network.solve_sor))
    start = text.index("    gx = self._harmonic(")
    end = text.index("    gr[:, :, :-1], gl[:, :, 1:] = gx, gx")
    if text.count("    gx = self._harmonic(") != 1 or start > end:
        raise RuntimeError("the parent solve_sor changed: update _patched_sor")
    text = text[:start] + "    gx, gy = self._links_for_solvers()\n" + text[end:]
    ns = {}
    exec(compile(text, "<patched solve_sor>", "exec"), vars(fvm), ns)
    return ns["solve_sor"]


CutCellNetwork.solve_sor = _patched_sor()


@contextlib.contextmanager
def using_cutcell(mode="links", samples=16, d_min=1e-3, ap_min=0.0, exact=False):
    """!
    @brief Replace `fvm.Network` by the cut-cell network for the duration of a block.
    @param mode one of MODES (see the module header; "aperture" keeps the nodes at the cell centres).
    @param samples Sampling M x M per cell for the geometry.
    @param d_min Smallest face-to-centroid distance as a fraction of the cell side.
    @param ap_min Apertures below this fraction are zero.
    @param exact True: the geometry of the cut cells by exact clipping (`cutcell_exact`) and the cover of the whole network exact too (`Board.cover` replaced).
    @return Context manager (yields the network class).
    @throws ValueError If the mode is unknown.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    CutCellNetwork.mode, CutCellNetwork.samples = mode, samples
    CutCellNetwork.d_min, CutCellNetwork.ap_min, CutCellNetwork.exact = d_min, ap_min, exact
    original = fvm.Network
    fvm.Network = CutCellNetwork
    try:
        if exact:
            with cutcell_exact.using_exact_cover():
                yield CutCellNetwork
        else:
            yield CutCellNetwork
    finally:
        fvm.Network = original


def tmax(problem, cell_mm, scheme="program", **kw):
    """!
    @brief Hottest board temperature of the layered FVM with the program's treatment or a cut-cell variant.
    @param problem Problem.
    @param cell_mm Cell size in mm.
    @param scheme "program" (the unmodified `fvm.solve_steady`), "links", "links+strip" or "aperture".
    @param kw More options for `using_cutcell` (samples, d_min, ap_min).
    @return Hottest temperature in degrees Celsius.
    """
    return float(solve(problem, cell_mm, scheme, **kw).t_max)


def solve(problem, cell_mm, scheme="program", **kw):
    """!
    @brief Full `SteadyResult` of the layered FVM with the program's treatment or a cut-cell variant.
    @param problem Problem.
    @param cell_mm Cell size in mm.
    @param scheme "program", "links" or "links+strip".
    @param kw More options for `using_cutcell`.
    @return pcbthermal.results.SteadyResult.
    """
    # A suffix "@exact" asks for the exact cover and geometry ("program@exact" is the program's links with only the exact cover)
    base, _, flag = scheme.partition("@")
    if flag == "exact":
        kw = dict(kw, exact=True)
    if base == "program":
        if flag == "exact":
            with cutcell_exact.using_exact_cover():
                return fvm.solve_steady(problem, cell_mm=cell_mm)
        return fvm.solve_steady(problem, cell_mm=cell_mm)
    with using_cutcell(base, **kw):
        return fvm.solve_steady(problem, cell_mm=cell_mm)
