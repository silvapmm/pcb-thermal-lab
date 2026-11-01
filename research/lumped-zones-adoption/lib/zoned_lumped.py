#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file zoned_lumped.py
@brief PROPOSAL: the Lumped heater network of the program (2.4.5, with the via wells) with the footprint cut into two zones where a group of vias covers part of it; a copy that imports the program and replaces `lumped._heater_network` in memory (the program is never edited).
@details Run and measured in the README of this folder; the tests are in `tests/test_zoned_lumped.py`.

         What it is. `pcbthermal.lumped._heater_network` gives the footprint of a heater one node per layer. When a dense group of vias (the "core") sits under a larger footprint, the
         heat of the rest of the footprint has to travel sideways to the core, in parallel with the vertical paths of that rest, and the one-node footprint cannot show it (the
         via effect came out up to 60 % too small). This module builds the same network with two footprint nodes per layer:
         * node 0 = A, the footprint outside the core: its share of the source, its films and dielectric, the link to the first ring outside;
         * node 1 = C, the core (the cells within `core_r * d_nn` of a via of a group of two or more vias that lies in the footprint): the rest of the source, the barrels with
           their wells (Kron reduced, as in `viaconstriction.ring_couplings`);
         * nodes 2.. = the rings outside the footprint, as in the program.
         The link A-C of every layer is the logarithmic-potential resistance of the real shapes, `(2 phi_AC - phi_AA - phi_CC) / (2 pi S)` (`mutual_potentials`); A to ring 1 is the
         mean-to-outer-wall resistance of the annulus plus the half ring (`annulus_out_resistance`). The hottest point of the source layer is the largest of three candidates (`ZonePeak`):
         the hottest point of A, the core mean plus the rise of the rim of the cell of one via (the micro peak), and the core mean plus the micro peak plus the bump of a core hotter
         than A. When no core exists or it covers more than `OPTIONS["max_core"]` of the footprint, the footprint is ONE node (nz = 1) and the network is the program's, equal to rounding (1e-10) when
         `micro_peak_single` is False and `footprint="stride"` (the sums of the matrix are made in another order).

         What is new relative to the research copy `research/lumped-via-groups/lib/lumped_zones.py`: it works on the 2.4.5 program (the via couplings are those of
         `viaconstriction.ring_couplings`, copied here in `via_couplings` with a switch for the macro term of the zone nodes and with the barrel-only part kept for the micro peak), the
         capacities of the zones are sums of cell capacities (the transient), the unit source vector and the peak are part of the returned system (`source`, `peak`), the footprint
         potentials can use blocks instead of strides (`footprint="block"`), and the warnings and the raster rule are functions (`zone_warnings`, `tied_cell_mm`).
@note Steady state and the step response of one heater (`step_responses_zoned`); the profile runner of the program needs the same two changes (see INTEGRATION.md 4). Rectangular and polygonal footprints through coverage cells; the radii of the annulus are those of discs of the same area.
"""

import contextlib
import math
import os
import sys

import numpy as np
from scipy import ndimage
from scipy.linalg import lu_factor, lu_solve
from scipy.special import k0

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pcbthermal import lumped, viaconstriction, viawell                      # noqa: E402
from pcbthermal.fvm import board_time_constant                               # noqa: E402
from pcbthermal.geometry import cell_index_of_point                          # noqa: E402

OPTIONS = {
    "zones": True,               # False: every footprint stays one node (the program's network, plus the options below)
    "zone_macro": "none",        # macro term of the cluster well in the zone nodes: "none" (the micro well only) or "cap" (the program's well with the cap of 0.75 fin lengths)
    "max_core": 0.92,            # largest share of the footprint the core may cover before the footprint stays one node
    "core_r": 0.7071,            # radius of the core around a via in nearest-neighbour distances (covers a square lattice)
    "micro_peak": True,          # add the rise of the rim of the cell of a via above the node mean to the peak (zones)
    "micro_peak_single": False,  # the same for the one-node footprint (False: the program's peak, bit for bit)
    "core_peak": True,           # the bump of a core hotter than A
    "bessel_ring1": False,       # apply the Bessel factor f_R of the program to the A-to-ring-1 resistance (three passes)
    "decimation": "block",       # peak and link integrals of a zone with more than `max_cells` cells: "block" (blocks of k x k cells) or "stride" (every step-th cell)
    "footprint": "stride",       # potentials of the one-node footprint: "stride" (the program's, 900 cells) or "block" (the fix proposed in INTEGRATION.md 5)
    "max_cells": 700,            # cells (or blocks) kept per zone in the potential integrals
    "share_rule": "grid",        # the share of the footprint covered by the core that decides zones against one node: "grid" (counted on the Lumped raster) or "fine" (counted on a 0.1 mm grid)
    "fine_mm": 0.1,              # cell of the fine grid of the share rule (mm)
}
LAST = {}                        # diagnostics of the last network built (zones, flows, warnings)
_ORIGINAL = {}                   # the program's functions, saved by `patched`


# ------------------------------------------------------------------------------------------------ closed forms

def annulus_out_resistance(S, r_c, a):
    """!
    @brief Mean-to-outer-wall resistance of an annulus with a uniform source, heat leaving only through the outer wall (inner side insulated).
    @param S Sheet conductance in W/K.
    @param r_c Inner radius in m.
    @param a Outer radius in m.
    @return float Area-mean temperature minus outer-wall temperature per watt generated in the annulus, K/W.
    """
    if a <= r_c:
        return 0.0
    # T(r) - T(a) = q/(2 S) [ (a^2 - r^2)/2 - r_c^2 ln(a/r) ] per unit generation q; mean over the annulus, per Q = q pi (a^2 - r_c^2)
    i1 = a * a * (a * a - r_c * r_c) / 4.0 - (a ** 4 - r_c ** 4) / 8.0
    i2 = r_c * r_c * (a * a / 4.0 - r_c * r_c / 2.0 * math.log(a / r_c) - r_c * r_c / 4.0)
    mean = (i1 - i2) / ((a * a - r_c * r_c) / 2.0) / (2.0 * S)
    return mean / (math.pi * (a * a - r_c * r_c))


def rim_minus_mean(S, R, a):
    """!
    @brief Temperature of the rim of the Krogh cell above the area mean of the cell, per watt taken by the via.
    @param S Sheet conductance in W/K.
    @param R Cell radius in m.
    @param a Radius of the via target in m.
    @return float K/W: [b^2 ln b / (b^2 - 1) - 1/2] / (2 pi S) minus the Krogh mean-to-wall resistance (zero if R <= a).
    """
    if R <= a:
        return 0.0
    b = R / a
    rim = (b * b * math.log(b) / (b * b - 1.0) - 0.5) / (2.0 * math.pi * S)
    return rim - viaconstriction.krogh(S, R, a)


def block_points(w, dx, dy, max_cells):
    """!
    @brief Cells of a region aggregated in blocks of k x k cells, k the smallest that keeps at most about `max_cells` blocks (no aliasing of the stride).
    @param w Weights of the cells (ny, nx), zero outside the region.
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param max_cells Largest number of blocks wanted.
    @return Tuple (positions (n, 2) in m, weights (n,), self distances (n,) in m): the weighted centroid of every block that holds part of the region, its summed weight, and the
            mean log distance inside it, `0.447 sqrt(area)` of the cells of the region in the block (for k = 1 the cell term of the program).
    """
    n = int((w > 0).sum())
    k = max(int(math.ceil(math.sqrt(n / max_cells))), 1)
    ny, nx = w.shape
    big_y, big_x = -(-ny // k), -(-nx // k)
    wp = np.zeros((big_y * k, big_x * k))
    wp[:ny, :nx] = w
    yy, xx = np.mgrid[0:big_y * k, 0:big_x * k]

    def block_sum(a):
        # sum of the k x k cells of every block
        return a.reshape(big_y, k, big_x, k).sum(axis=(1, 3))
    wb, xb, yb, nb = block_sum(wp), block_sum(wp * xx), block_sum(wp * yy), block_sum((wp > 0).astype(float))
    m = wb > 0
    # centres of the cells are at (index + 0.5) cell; the program's potentials use index * cell, the same shift for every point, so distances are unchanged
    pos = np.column_stack([xb[m] / wb[m] * dx, yb[m] / wb[m] * dy])
    return pos, wb[m], 0.447 * np.sqrt(nb[m] * dx * dy)


def stride_points(w, dx, dy, max_cells):
    """!
    @brief Every step-th cell of a region in row order (the program's decimation), with the self distance of the program.
    @param w Weights of the cells (ny, nx), zero outside the region.
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param max_cells Largest number of cells wanted.
    @return Tuple (positions, weights, self distances) as `block_points`.
    """
    idx = np.argwhere(w > 0)
    step = max(int(math.ceil(len(idx) / max_cells)), 1)
    idx = idx[::step]
    return (np.column_stack([idx[:, 1] * dx, idx[:, 0] * dy]), w[w > 0][::step],
            np.full(len(idx), 0.447 * math.sqrt(dx * dy) * math.sqrt(step)))


def _points(w, dx, dy, max_cells, mode):
    """!
    @brief Decimated points of a region by the chosen rule.
    @param w Weights (ny, nx).
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param max_cells Largest number of points.
    @param mode "block" or "stride".
    @return Tuple (positions, weights, self distances).
    """
    return (block_points if mode == "block" else stride_points)(w, dx, dy, max_cells)


def _mean_log(p, wp, dp, q, wq, dq, same, floor):
    """!
    @brief Weighted mean of ln(distance) between two point sets.
    @param p Positions (n, 2).
    @param wp Weights (n,).
    @param dp Self distances (n,) used on the diagonal when `same`.
    @param q Positions (m, 2).
    @param wq Weights (m,).
    @param dq Unused (kept so that the two sets have the same triple).
    @param same True when the two sets are the same set (the diagonal gets the self distance).
    @param floor Smallest distance used between different points (the cell term).
    @return float.
    """
    d = np.hypot(p[:, None, 0] - q[None, :, 0], p[:, None, 1] - q[None, :, 1])
    if same:
        d[np.arange(len(p)), np.arange(len(p))] = dp
    else:
        d = np.maximum(d, floor)
    return float((np.log(d) * wp[:, None] * wq[None, :]).sum() / (wp.sum() * wq.sum()))


def mutual_potentials(w_a, w_c, dx, dy, max_cells=700, mode="block"):
    """!
    @brief 2 phi_AC - phi_AA - phi_CC: mean logarithmic distances between two uniform distributions of heat on the grid (the lossless link of two regions of a sheet, any shapes).
    @details A uniform source on A and a uniform sink on C of equal strength Q on an infinite sheet give `T_A - T_C = Q (2 phi_AC - phi_AA - phi_CC) / (2 pi S)`, phi_XY the mean of
             ln|x - y| over x in X, y in Y. For concentric discs it is the Krogh resistance of the annulus plus `1 / (8 pi S)` of the core.
    @param w_a Weights of the cells of A (ny, nx).
    @param w_c Weights of the cells of C (ny, nx).
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param max_cells Points kept per region.
    @param mode "block" or "stride" decimation.
    @return float (dimensionless).
    """
    pa, wa, da = _points(w_a, dx, dy, max_cells, mode)
    pc_, wc, dc = _points(w_c, dx, dy, max_cells, mode)
    floor = 0.447 * math.sqrt(dx * dy)
    return (2.0 * _mean_log(pa, wa, da, pc_, wc, dc, False, floor) - _mean_log(pa, wa, da, pa, wa, da, True, floor) - _mean_log(pc_, wc, dc, pc_, wc, dc, True, floor))


def footprint_potentials(cov, dx, dy, mode="stride", max_cells=900):
    """!
    @brief Logarithmic potentials of a uniformly heated footprint: the program's `lumped._footprint_potentials` with a choice of decimation.
    @details With "stride" it calls the program's function (every step-th cell above 900). With "block" the cells are aggregated in blocks (same weights and boundary counts), which does not
             alias: the research folder measured the stride 4 to 11 % short in the mean-to-boundary term for 20 to 30 mm squares at 0.5 mm.
    @param cov Footprint coverage (ny, nx).
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param mode "stride" (the program) or "block".
    @param max_cells Points kept.
    @return Tuple (phi_mean, phi_boundary, phi_min).
    """
    if mode == "stride":
        return lumped._footprint_potentials(cov, dx, dy)
    foot = cov > 0
    ny, nx = cov.shape
    # boundary cells: the program's rule (a footprint cell with a 4-neighbour inside the board that is not footprint)
    pad = np.pad(foot, 1, constant_values=True)                              # outside the board counts as footprint: the board edge is adiabatic, not a boundary
    nbr_off = ~pad[2:, 1:-1] | ~pad[:-2, 1:-1] | ~pad[1:-1, 2:] | ~pad[1:-1, :-2]
    bnd = (foot & nbr_off).astype(float)
    pos, wb, db = block_points(cov, dx, dy, max_cells)
    d = np.hypot(pos[:, None, 0] - pos[None, :, 0], pos[:, None, 1] - pos[None, :, 1])
    d[np.arange(len(pos)), np.arange(len(pos))] = db
    phi = (np.log(d) * wb[None, :]).sum(axis=1) / wb.sum()
    phi_mean = float((phi * wb).sum() / wb.sum())
    # the boundary cells keep their own positions (a block centroid lies half a block inside the edge and biased the term by 8 % in the first version):
    # potential of every boundary cell against the block sources; a source block that holds the cell itself gets the self distance of a cell
    bidx = np.argwhere(bnd > 0)
    if len(bidx):
        bpos = np.column_stack([bidx[:, 1] * dx, bidx[:, 0] * dy])
        dd = np.hypot(bpos[:, None, 0] - pos[None, :, 0], bpos[:, None, 1] - pos[None, :, 1])
        # the mean log distance from a point to a block that contains it is about ln(0.447 block side), never below a cell term
        dd = np.maximum(dd, db[None, :])
        phi_b = (np.log(dd) * wb[None, :]).sum(axis=1) / wb.sum()
        phi_bnd = float(phi_b.mean())
    else:
        phi_bnd = phi_mean
    return phi_mean, phi_bnd, float(phi.min())


def _block_weights(a, w, max_cells):
    """!
    @brief Sum of a per-cell array over the same blocks that `block_points(w, ..., max_cells)` uses.
    @param a Per-cell array (ny, nx).
    @param w Weights whose support defines the blocks.
    @param max_cells Largest number of blocks.
    @return Tuple (block size k, array of block sums for the blocks that hold part of the support, in the order of `block_points`).
    """
    n = int((w > 0).sum())
    k = max(int(math.ceil(math.sqrt(n / max_cells))), 1)
    ny, nx = w.shape
    big_y, big_x = -(-ny // k), -(-nx // k)
    wp = np.zeros((big_y * k, big_x * k))
    ap = np.zeros((big_y * k, big_x * k))
    wp[:ny, :nx] = w
    ap[:ny, :nx] = a
    wb = wp.reshape(big_y, k, big_x, k).sum(axis=(1, 3))
    ab = ap.reshape(big_y, k, big_x, k).sum(axis=(1, 3))
    return k, ab[wb > 0]


def footprint_potentials_exact(cov, dx, dy, chunk=400):
    """!
    @brief The same potentials with every footprint cell (no decimation), for the check of the decimations; memory limited by chunks of rows.
    @param cov Footprint coverage (ny, nx).
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param chunk Rows of the distance matrix computed at a time.
    @return Tuple (phi_mean, phi_boundary, phi_min).
    """
    idx = np.argwhere(cov > 0)
    w = cov[cov > 0]
    foot = cov > 0
    pad = np.pad(foot, 1, constant_values=True)
    nbr_off = ~pad[2:, 1:-1] | ~pad[:-2, 1:-1] | ~pad[1:-1, 2:] | ~pad[1:-1, :-2]
    bnd = (foot & nbr_off)[foot]
    pos = np.column_stack([idx[:, 1] * dx, idx[:, 0] * dy])
    self_d = 0.447 * math.sqrt(dx * dy)
    phi = np.zeros(len(pos))
    for s in range(0, len(pos), chunk):
        d = np.hypot(pos[s:s + chunk, None, 0] - pos[None, :, 0], pos[s:s + chunk, None, 1] - pos[None, :, 1])
        d[np.arange(d.shape[0]), np.arange(s, s + d.shape[0])] = self_d
        phi[s:s + chunk] = (np.log(d) * w[None, :]).sum(axis=1) / w.sum()
    phi_mean = float((phi * w).sum() / w.sum())
    return phi_mean, float(phi[bnd].mean()) if bnd.any() else phi_mean, float(phi.min())


# ------------------------------------------------------------------------------------------------ the core

def core_mask(net, cov, vias, core_r=None):
    """!
    @brief The cells of the footprint that the dense groups of vias cover.
    @param net Network (grid).
    @param cov Footprint coverage (ny, nx).
    @param vias ViaSet of the problem (positions, nearest neighbours, groups) or None.
    @param core_r Radius around a via in nearest-neighbour distances (None: `OPTIONS["core_r"]`).
    @return numpy.ndarray bool (ny, nx), or None when no group of two or more vias lies in the footprint.
    """
    if vias is None or len(vias) < 2:
        return None
    r_rel = OPTIONS["core_r"] if core_r is None else core_r
    foot = cov > 0
    core = np.zeros(foot.shape, bool)
    for g in np.unique(vias.group):
        mem = np.flatnonzero(vias.group == g)
        cells = []
        for i in mem:
            ci, cj = cell_index_of_point(vias.x[i], vias.y[i], net.nx, net.ny, net.dx, net.dy)
            if foot[ci, cj]:
                cells.append((ci, cj, i))
        if len(cells) < 2:
            continue
        seed = np.zeros(foot.shape, bool)
        for ci, cj, _ in cells:
            seed[ci, cj] = True
        r = r_rel * float(np.mean([vias.d_nn[i] for _, _, i in cells]))
        dist = ndimage.distance_transform_edt(~seed, sampling=(net.dy, net.dx))
        core |= (dist <= r) & foot
    return core if core.any() else None


class _ViaView:
    """!
    @brief The positions, nearest-neighbour distances and groups of a ViaSet with the positions moved to another frame (what `core_mask` reads).
    """

    def __init__(self, vias, x, y, keep=None):
        """!
        @param vias ViaSet.
        @param x New x positions in m (all the vias of the set).
        @param y New y positions in m (all the vias of the set).
        @param keep Boolean mask of the vias to keep (None: all); the others are dropped, not moved.
        """
        keep = np.ones(len(x), bool) if keep is None else np.asarray(keep, bool)
        self.x, self.y = np.asarray(x)[keep], np.asarray(y)[keep]
        self.d_nn, self.group = np.asarray(vias.d_nn)[keep], np.asarray(vias.group)[keep]

    def __len__(self):
        """!
        @brief Number of vias.
        @return int.
        """
        return len(self.x)


def fine_core_share(net, cov, vias, fine_mm=None):
    """!
    @brief The share of the footprint covered by the core, counted on a grid of about `fine_mm` (the Lumped cell is split by an integer factor; the footprint mask is replicated), so that it does not depend on the raster.
    @param net Network (grid of the Lumped raster).
    @param cov Footprint coverage on the raster (ny, nx).
    @param vias ViaSet or None.
    @param fine_mm Target cell in mm (None: `OPTIONS["fine_mm"]`).
    @return float share in [0, 1] (0 when there is no core).
    """
    from types import SimpleNamespace
    h = (OPTIONS["fine_mm"] if fine_mm is None else fine_mm) * 1e-3
    k = max(int(round(net.dx / h)), 1)
    if k == 1:
        core = core_mask(net, cov, vias)
        return 0.0 if core is None else float(core.sum() / (cov > 0).sum())
    # work on the bounding box of the footprint, at most 600 fine cells a side
    ys, xs = np.nonzero(cov > 0)
    i0, i1, j0, j1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    k = min(k, max(int(600 // max(i1 - i0, j1 - j0)), 1))
    cov_f = np.kron(cov[i0:i1, j0:j1], np.ones((k, k)))
    net_f = SimpleNamespace(nx=(j1 - j0) * k, ny=(i1 - i0) * k, dx=net.dx / k, dy=net.dy / k)
    # the vias in the frame of the box; a via outside the box is dropped: `cell_index_of_point` clips a point to the grid, so a via outside the box would be moved onto its
    # border cells, which are footprint cells for a rectangle (the first version did that: a group straddling the footprint edge read 0.136 instead of 0.118; review)
    x, y = vias.x - j0 * net.dx, vias.y - i0 * net.dy
    keep = (x >= 0.0) & (x < net_f.nx * net_f.dx) & (y >= 0.0) & (y < net_f.ny * net_f.dy)
    if keep.sum() < 2:
        return 0.0
    v = _ViaView(vias, x, y, keep)
    core = core_mask(net_f, cov_f, v)
    # weighted by the coverage: the replicated cells of a partly covered raster cell at the footprint edge count by their share, not whole
    return 0.0 if core is None else float((core * cov_f).sum() / cov_f.sum())


def zone_warnings(net, cov, core):
    """!
    @brief The warnings of the zone model for one heater (the three rules of INTEGRATION.md 6).
    @param net Network (cell size).
    @param cov Footprint coverage.
    @param core Core mask or None.
    @return list of str (empty when none applies).
    """
    out = []
    if core is None:
        return out
    foot = cov > 0
    ys, xs = np.nonzero(foot)
    w_f, h_f = (xs.max() - xs.min() + 1) * net.dx, (ys.max() - ys.min() + 1) * net.dy
    ratio = max(w_f, h_f) / min(w_f, h_f)
    cy, cx = np.nonzero(core)
    off = math.hypot((cx.mean() - xs.mean()) * net.dx, (cy.mean() - ys.mean()) * net.dy)
    if ratio > 1.5 or off > 0.1 * min(w_f, h_f):
        out.append("elongated footprint or vias off its centre: the via effect of this part can be 20 % too large (the part too cool)")
    across = min((cx.max() - cx.min() + 1), (cy.max() - cy.min() + 1))
    if across < 10:
        out.append("the raster cell is coarser than a tenth of the core: the via effect of this part can be 20 % too small")
    return out


def tied_cell_mm(problem, cell_mm, floor_mm=0.5, cells_across=10):
    """!
    @brief The Lumped raster tied to the core: a cell of one tenth of the narrowest core under any heater, not above `cell_mm` and not below `floor_mm`.
    @details The width of a core is estimated from the vias before the grid exists: the bounding box of the vias of each group inside the footprint box plus twice `core_r * d_nn`.
    @param problem The Problem.
    @param cell_mm Raster the user asked for in mm.
    @param floor_mm Smallest cell in mm (the program's clip of the Lumped cell is 0.5).
    @param cells_across Cells wanted across the core.
    @return float Cell in mm.
    """
    if not problem.vias or len(problem.vias) < 2:
        return cell_mm
    vs = viaconstriction.ViaSet(problem)
    width = None
    for h in problem.heaters:
        poly = np.asarray(h.polygon, dtype=float)
        px, py = poly[:, 0], poly[:, 1]
        for g in np.unique(vs.group):
            mem = [i for i in np.flatnonzero(vs.group == g) if px.min() <= vs.x[i] <= px.max() and py.min() <= vs.y[i] <= py.max()]
            if len(mem) < 2:
                continue
            ext = min(np.ptp(vs.x[mem]), np.ptp(vs.y[mem])) + 2.0 * OPTIONS["core_r"] * float(np.mean(vs.d_nn[mem]))
            width = ext if width is None else min(width, ext)
    if width is None:
        return cell_mm
    return float(min(cell_mm, max(floor_mm, 1e3 * width / cells_across)))


# ------------------------------------------------------------------------------------------------ vertical couplings

def via_couplings(vs, net, idx, n_nodes, cnt, s_node, g_top, g_bot, gz_diel, nb, zone_nodes=()):
    """!
    @brief `viaconstriction.ring_couplings` with a switch for the macro term of the zone nodes and with the barrel-only part kept (the micro peak needs it).
    @details Identical to the program's function when `zone_nodes` is empty (checked by the tests: the dictionaries are equal). For a node in `zone_nodes` the macro term
             `N_g R_K(S, R_macro, r_cl)` is added only if `OPTIONS["zone_macro"] == "cap"`; the micro well is always there.
    @param vs ViaSet of the problem.
    @param net Network (grid size and cell size).
    @param idx (ny, nx) node index of every cell.
    @param n_nodes Number of nodes.
    @param cnt (n_nodes,) cells per node.
    @param s_node (L, n_nodes) mean sheet conductance of every node in W/K.
    @param g_top (L, n_nodes) conductance to the ambient through the top face in W/K.
    @param g_bot (L, n_nodes) the same through the bottom face in W/K.
    @param gz_diel (nb - 1, n_nodes) dielectric conductance of every gap and node in W/K (the barrels are not in it).
    @param nb Number of board layers.
    @param zone_nodes Indices of the footprint zone nodes (empty: the program's behaviour).
    @return Tuple (gz, via_gz, seen): gz as `ring_couplings` ({(l, m): array (n_nodes,)}), via_gz the barrel-only couplings with the same keys, seen a list of dicts
            (node, n, r_cell, a) of the vias of every node for the micro peak.
    """
    gz = {(l, l + 1): gz_diel[l].astype(float).copy() for l in range(nb - 1)}
    via_gz, seen = {}, []
    nv = len(vs)
    if nv == 0 or nb < 2:
        return gz, via_gz, seen
    cell = net.dx * net.dy
    eta, cap = viaconstriction.ETA, viaconstriction.MACRO_CAP
    node_of = np.array([int(idx[cell_index_of_point(vs.x[i], vs.y[i], net.nx, net.ny, net.dx, net.dy)]) for i in range(nv)])
    n_node = np.bincount(node_of, minlength=n_nodes)             # vias in every node
    for g in np.unique(vs.group):
        members = np.flatnonzero(vs.group == g)
        n_g = len(members)
        nodes_g = np.unique(node_of[members])
        a_touched = float(sum(cnt[k] * cell for k in nodes_g))   # area of the nodes that the group touches
        r_cell_g = float(np.mean(vs.d_nn[members])) / math.sqrt(math.pi)
        r_macro = math.sqrt(a_touched / math.pi)
        for k in nodes_g:
            mem = members[node_of[members] == k]
            n = len(mem)
            a = eta * float(np.mean(vs.r_via[mem]))
            r_ring = math.sqrt(cnt[k] * cell / (math.pi * n_node[k]))
            r_cell = min(r_ring, r_cell_g)
            r_cl = math.sqrt(n_g) * r_cell
            g_gap = vs.g_gap[mem].sum(axis=0) / n
            g_well = np.full(nb, np.inf)
            area_k = cnt[k] * cell
            use_macro = n_g > 1 and (k not in zone_nodes or OPTIONS["zone_macro"] == "cap")
            for l in range(nb):
                s_l = s_node[l, k]
                if s_l <= 0:
                    g_well[l] = 0.0
                    continue
                loss = (g_top[l, k] + g_bot[l, k]) / area_k
                for m in (l - 1, l + 1):
                    if 0 <= m < nb:
                        loss += gz_diel[min(l, m), k] / area_k
                rc = viaconstriction.krogh(s_l, r_cell, a)
                if use_macro:
                    rm = min(r_macro, cap * math.sqrt(s_l / loss)) if loss > 0 else r_macro
                    if rm > r_cl:
                        rc += n_g * viaconstriction.krogh(s_l, rm, r_cl)
                g_well[l] = math.inf if rc <= 0 else 1.0 / rc
            reduced = viawell.kron_barrel(g_gap, g_well) * n
            for l in range(nb):
                for m in range(l + 1, nb):
                    if reduced[l, m] != 0.0:
                        for d in (gz, via_gz):
                            if (l, m) not in d:
                                d[(l, m)] = np.zeros(n_nodes)
                            d[(l, m)][k] += reduced[l, m]
            seen.append({"node": int(k), "n": n, "r_cell": r_cell, "a": a})
    return gz, via_gz, seen


# ------------------------------------------------------------------------------------------------ the peak

class ZonePeak:
    """!
    @brief The hottest point of the source layer of a heater network as a function of the node temperatures (linear pieces precomputed, so that the transient can call it at every step).
    """

    def __init__(self, layer, nz, r_ac, r_a2, fields, bump, micro, single_coef):
        """!
        @param layer Source layer.
        @param nz Footprint nodes (1 or 2).
        @param r_ac Resistance A-C of the source layer (K/W) or None.
        @param r_a2 Resistance A-ring 1 of the source layer (K/W) or None.
        @param fields Matrix (n, 2) of the field of A in K per (W of q_in, W of q_out), mean removed, or None.
        @param bump Coefficient of the core bump in K per W of heat sent from C to A, or 0.
        @param micro Dict with the barrel couplings and the rim coefficient of the core node, or None.
        @param single_coef Peak coefficient of the one-node footprint in K per W of lateral outflow and the resistance to ring 1, as a tuple (coef, r01), or None.
        """
        self.layer, self.nz, self.r_ac, self.r_a2 = layer, nz, r_ac, r_a2
        self.fields, self.bump, self.micro, self.single = fields, bump, micro, single_coef

    def micro_rise(self, th, node):
        """!
        @brief Rise of the rim of the cell of a via above the node mean: the heat of one via times the rim-to-mean resistance of its cell.
        @param th Node temperatures (L, R).
        @param node Node index that holds the vias.
        @return float K.
        """
        if self.micro is None:
            return 0.0
        i_tot = 0.0
        for (l_a, l_b), g in self.micro["via_gz"].items():
            if l_a == self.layer:
                i_tot += g[node] * (th[self.layer, node] - th[l_b, node])
            elif l_b == self.layer:
                i_tot += g[node] * (th[self.layer, node] - th[l_a, node])
        return max(i_tot, 0.0) / self.micro["n"] * self.micro["rim"]

    def extra(self, th):
        """!
        @brief Peak of the source layer above the temperature of node 0.
        @param th Node temperatures (L, R).
        @return float K (not negative).
        """
        l = self.layer
        if self.nz == 1:
            if self.single is None:
                return 0.0
            coef, r01 = self.single
            lat = (th[l, 0] - th[l, 1]) / r01 if np.isfinite(r01) else 0.0
            return max(lat, 0.0) * coef + (self.micro_rise(th, 0) if OPTIONS["micro_peak_single"] else 0.0)
        q_in = (th[l, 0] - th[l, 1]) / self.r_ac if np.isfinite(self.r_ac) else 0.0
        q_out = (th[l, 0] - th[l, 2]) / self.r_a2 if self.r_a2 is not None and np.isfinite(self.r_a2) else 0.0
        excess = 0.0
        if q_in + q_out > 0 and self.fields is not None:
            excess = float(np.max(self.fields @ np.array([q_in, q_out])))
        mp = self.micro_rise(th, 1) if OPTIONS["micro_peak"] else 0.0
        bump = 0.0
        if OPTIONS["core_peak"] and th[l, 1] > th[l, 0] and np.isfinite(self.r_ac):
            bump = (th[l, 1] - th[l, 0]) / self.r_ac * self.bump
        return max(excess, th[l, 1] + mp + bump - th[l, 0], 0.0)

    def __call__(self, th):
        """!
        @brief Temperature rise of the hottest point of the source layer.
        @param th Node temperatures (L, R).
        @return float K.
        """
        return float(th[self.layer, 0] + self.extra(th))


def _peak_fields(wa, wc, S_a, dx, dy, lam, mode, max_cells):
    """!
    @brief The matrix of the field of A over its points for a unit heat sent to C and a unit heat sent to ring 1 (mean removed), and the core-bump coefficient.
    @details t(x) = [ (q_in + q_out) phi_A(x) - q_in phi_C(x) ] / (2 pi S) with phi_X(x) the mean of K(|x - y|) over y in X and K = K0(d / lam) (lossy sheet) or -ln d.
    @param wa Weights of the cells of A (ny, nx).
    @param wc Weights of the cells of C.
    @param S_a Sheet conductance of A in the source layer in W/K.
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param lam Fin length of the source layer under A in m (None: lossless).
    @param mode "block" or "stride".
    @param max_cells Points per zone.
    @return Tuple (matrix (n, 2), bump coefficient in K per W).
    """
    pa, w_a, d_a = _points(wa, dx, dy, max_cells, mode)
    pc_, w_c, d_c = _points(wc, dx, dy, max_cells, mode)
    floor = 0.447 * math.sqrt(dx * dy)

    def kernel(d):
        # -ln d (lossless) or K0(d / lam); the same sign so that one formula serves both
        return -np.log(d) if lam is None else k0(d / lam)

    def phi(p, q, wq, dq, same):
        d = np.hypot(p[:, None, 0] - q[None, :, 0], p[:, None, 1] - q[None, :, 1])
        if same:
            d[np.arange(len(p)), np.arange(len(p))] = dq
        else:
            d = np.maximum(d, floor)
        return (kernel(d) * wq[None, :]).sum(axis=1) / wq.sum()
    f_a = phi(pa, pa, w_a, d_a, True)
    f_c = phi(pa, pc_, w_c, d_c, False)
    cols = np.column_stack([f_a - f_c, f_a]) / (2.0 * math.pi * S_a)                      # t = cols @ [q_in, q_out]
    mean = (cols * w_a[:, None]).sum(axis=0) / w_a.sum()
    # bump of a core hotter than A: the lossless potential of C heated uniformly with its net lateral outflow, hottest point above the mean
    pcc = np.hypot(pc_[:, None, 0] - pc_[None, :, 0], pc_[:, None, 1] - pc_[None, :, 1])
    pcc[np.arange(len(pc_)), np.arange(len(pc_))] = d_c
    f_cc = (-np.log(pcc) * w_c[None, :]).sum(axis=1) / w_c.sum()
    return cols - mean[None, :], float((f_cc.max() - (f_cc * w_c).sum() / w_c.sum()))


# ------------------------------------------------------------------------------------------------ the network

def heater_network(net, cov, layer, power, rings, vias=None, zone_ok=None):
    """!
    @brief `lumped._heater_network` with the footprint cut into the rest A (node 0) and the core C (node 1) when a group of vias covers only part of it.
    @details Same arguments and keys as the program's function. The returned dict has in addition `source` (unit source vector, the share of A and C by area), `peak` (a `ZonePeak`
             to call with the node temperatures), `nz` (footprint nodes), `cap` per node in "C" (sums of cell capacities, the transient), `warnings` (text) and `node_cells`.
             With `OPTIONS["zones"]` False, or no core, or a core above `max_core` of the footprint, nz = 1 and the network is the program's (equal to rounding when
             `micro_peak_single` is False and `footprint` is "stride").
    @param net Network (per-cell arrays) of the problem.
    @param cov Footprint coverage of the heater, array (ny, nx).
    @param layer 0-based heater layer.
    @param power Heater power (W).
    @param rings Number of rings outside the footprint.
    @param vias ViaSet of the problem or None for a board without vias.
    @param zone_ok Ignored: the decision of the program (`lumped.will_be_zoned`, passed by `lumped.solve_steady` since the adoption); this copy decides by its own `OPTIONS`.
    @return dict as `lumped._heater_network`, with theta of shape (L, R) and R = nz + rings used.
    """
    L, ny, nx = net.nl, net.ny, net.nx
    cell = net.dx * net.dy
    foot = cov > 0
    core = core_mask(net, cov, vias) if OPTIONS["zones"] else None
    if core is not None:
        # the share of the footprint that the core covers decides between the zones and the one-node network; counted on the Lumped grid ("grid", the first design) it changes with
        # the raster (the inverted-T example board: 82 % at 1.0 mm and 95 % at 0.5 mm, a jump of 2.9 K), counted on a fine grid of 0.1 mm ("fine") it does not
        share = core.sum() / foot.sum()
        if OPTIONS["share_rule"] == "fine":
            # the zones need both: a core that leaves room on the geometric footprint and cells of A on the grid (with a handful of A cells the zone network read the part up to 14 % hot)
            share = max(share, fine_core_share(net, cov, vias))
        if share > OPTIONS["max_core"] or core.sum() == foot.sum():
            core = None
    nz = 1 if core is None else 2
    dist = ndimage.distance_transform_edt(~foot, sampling=(net.dy, net.dx))
    outside = ~foot
    rho_max = float(dist.max()) if outside.any() else 0.0

    # --- rings exactly as the program
    if rho_max > 0:
        edges = lumped.ring_edges(rho_max, net.dx, net.dy, rings)
        idx = np.where(foot, 0, 1 + np.minimum(np.searchsorted(edges[1:], dist, side="left"), len(edges) - 2))
    else:
        edges, idx = np.array([0.0]), np.zeros((ny, nx), dtype=int)
    cnt0 = np.bincount(idx.ravel(), minlength=idx.max() + 1)
    used = np.flatnonzero(cnt0 > 0)
    remap = np.full(len(cnt0), -1)
    remap[used] = np.arange(len(used))
    idx = remap[idx]
    R0 = len(used)
    # node index: 0 = footprint (nz = 1) or A = 0, C = 1 (nz = 2); the rings follow
    idx2 = np.where(idx == 0, (np.where(core, 1, 0) if nz == 2 else 0), idx + nz - 1)
    R = R0 + nz - 1
    cnt = np.bincount(idx2.ravel(), minlength=R)
    flat = idx2.ravel()

    def ring_sum(a):
        # sum of a per-cell array over the nodes
        return np.bincount(flat, weights=a.ravel(), minlength=R)

    rho_mean = ring_sum(dist) / cnt
    thick = np.zeros(R)
    for k in range(1, R0):
        lo, hi = edges[used[k] - 1], edges[used[k]]
        thick[k + nz - 1] = max(min(hi, rho_max) - lo, 0.5 * min(net.dx, net.dy))
    length = np.where(thick > 0, cnt * cell / np.maximum(thick, 1e-12), 0.0)

    S = np.array([ring_sum(net.S[l]) / cnt for l in range(L)])
    g_top = np.array([ring_sum(net.g_top[l]) for l in range(L)])
    g_bot = np.array([ring_sum(net.g_bottom[l]) for l in range(L)])
    g_heatsink = np.array([ring_sum(net.g_heatsink[l]) for l in range(L)])
    g_side = np.array([ring_sum(net.g_side[l]) for l in range(L)])
    nb = net.n_board
    g_block = np.array([ring_sum(net.g_block[l]) for l in range(L)])
    gz_diel = np.array([ring_sum(net.gz[l]) for l in range(nb - 1)]) if nb > 1 else np.zeros((0, R))
    via_gz, seen = {}, []
    if vias is not None and len(vias) and nb > 1:
        gz, via_gz, seen = via_couplings(vias, net, idx2, R, cnt, S, g_top, g_bot, gz_diel, nb, zone_nodes=((0, 1) if nz == 2 else ()))
    else:
        # the rings read the barrel as a point conductance (gz_via); the FVM matrix holds it as mean-potential couplings instead
        gz = {(l, l + 1): ring_sum(net.gz[l] + net.gz_via[l]) for l in range(nb - 1)} if nb > 1 else {}
    links = [(a, b, ring_sum(g)) for a, b, g in net.extra_links]
    cap = np.array([ring_sum(net.C[l]) for l in range(L)])               # heat capacity of every node (J/K): a sum of cells, for the zones too

    area_foot = float((cnt[:nz]).sum() * cell)
    a_eq = math.sqrt(area_foot / math.pi)
    # source split by area (coverage) between A and C
    source = np.zeros(L * R)
    if nz == 2:
        cov_a, cov_c = float((cov * (idx2 == 0)).sum()), float((cov * (idx2 == 1)).sum())
        frac_c = cov_c / (cov_a + cov_c)
        source[layer * R + 0], source[layer * R + 1] = 1.0 - frac_c, frac_c
        r_c = math.sqrt(cnt[1] * cell / math.pi)
        a_f = math.sqrt((cnt[0] + cnt[1]) * cell / math.pi)
        pot = mutual_potentials(cov * (idx2 == 0), cov * (idx2 == 1), net.dx, net.dy, OPTIONS["max_cells"], OPTIONS["decimation"])
        first_ring = 2 if R > 2 else None
    else:
        source[layer * R] = 1.0
        phi_mean, phi_bnd, phi_min = footprint_potentials(cov, net.dx, net.dy, OPTIONS["footprint"])
        first_ring = 1 if R > 1 else None

    def lateral(l, f_r):
        # (node a, node b, resistance in K/W) of the lateral links of layer l
        out = []
        if nz == 1:
            for k in range(R - 1):
                if S[l, k] <= 0 or S[l, k + 1] <= 0:
                    continue
                half_k1 = 0.5 * thick[k + 1] / (S[l, k + 1] * length[k + 1])
                if k == 0:
                    out.append((0, 1, f_r[l] * max(phi_bnd - phi_mean, 1e-3) / (2.0 * math.pi * S[l, 0]) + half_k1))
                else:
                    out.append((k, k + 1, 0.5 * thick[k] / (S[l, k] * length[k]) + half_k1))
            return out
        if S[l, 0] > 0 and S[l, 1] > 0:
            out.append((0, 1, pot / (2.0 * math.pi * S[l, 0])))
        if first_ring is not None and S[l, 0] > 0 and S[l, 2] > 0:
            half_k1 = 0.5 * thick[2] / (S[l, 2] * length[2])
            out.append((0, 2, f_r[l] * annulus_out_resistance(S[l, 0], r_c, a_f) + half_k1))
        for k in range(2, R - 1):
            if S[l, k] > 0 and S[l, k + 1] > 0:
                out.append((k, k + 1, 0.5 * thick[k] / (S[l, k] * length[k]) + 0.5 * thick[k + 1] / (S[l, k + 1] * length[k + 1])))
        return out

    def solve(f_r):
        # assemble and solve the network for the given factors on the footprint-to-ring link (one per layer)
        n = L * R
        K = np.zeros((n, n))

        def couple(a, b, g):
            K[a, a] += g
            K[b, b] += g
            K[a, b] -= g
            K[b, a] -= g
        for l in range(L):
            for a, b, r in lateral(l, f_r):
                couple(l * R + a, l * R + b, 1.0 / r)
        for (l_a, l_b), g_ab in gz.items():
            for k in range(R):
                if g_ab[k] != 0.0:
                    couple(l_a * R + k, l_b * R + k, g_ab[k])
        for a, b, g in links:
            for k in range(R):
                if g[k] > 0:
                    couple(a * R + k, b * R + k, g[k])
        diag = (g_top + g_bot + g_heatsink + g_side + g_block).ravel()
        K[np.arange(n), np.arange(n)] += np.where(diag > 0, diag, 0.0)
        Q = power * source
        iso = np.diag(K) <= 0                                   # a block layer that does not reach a node: pin it to zero so that the matrix stays regular
        K[iso, iso] = 1.0
        theta = np.linalg.solve(K, Q)
        return theta, K, Q

    def effective_loss(th, node):
        # vertical heat per kelvin and per area leaving the node of every layer: the program's g_eff
        g_eff = np.zeros(L)
        area = cnt[node] * cell
        for l in range(L):
            loss = (g_top[l, node] + g_bot[l, node] + g_heatsink[l, node] + g_side[l, node] + g_block[l, node]) * th[l, node]
            for (l_a, l_b), g_ab in gz.items():
                if l_a == l:
                    loss += g_ab[node] * (th[l, node] - th[l_b, node])
                elif l_b == l:
                    loss += g_ab[node] * (th[l, node] - th[l_a, node])
            for a, b, g in links:
                if a == l:
                    loss += g[node] * (th[a, node] - th[b, node])
            g_eff[l] = max(loss, 0.0) / (max(th[l, node], 1e-9) * area)
        return g_eff

    f_r = np.ones(L)
    f_p = np.ones(L)
    passes = 3 if (nz == 1 or OPTIONS["bessel_ring1"]) else 1
    for _ in range(passes):
        theta, K, Q = solve(f_r)
        th = theta.reshape(L, R)
        if passes > 1:
            g_eff = effective_loss(th, 0)
            f_r, f_p = lumped._interior_factors(a_eq * np.sqrt(np.maximum(g_eff, 1e-12) / np.maximum(S[:, 0], 1e-12)))

    # --- the peak of the source layer
    lat_l = lateral(layer, f_r)
    if nz == 1:
        r01 = next((r for a, b, r in lat_l if (a, b) == (0, 1)), np.inf)
        coef = f_p[layer] * (phi_mean - phi_min) / (2.0 * math.pi * S[layer, 0])
        micro = None
        if seen:
            n_v = sum(s["n"] for s in seen if s["node"] == 0)
            if n_v:
                rim = sum(s["n"] * rim_minus_mean(S[layer, 0], s["r_cell"], s["a"]) for s in seen if s["node"] == 0) / n_v
                micro = {"via_gz": via_gz, "n": n_v, "rim": rim}
        peak = ZonePeak(layer, 1, None, r01, None, 0.0, micro, (coef, r01))
        warn = []
        r_ac = r_a2 = None
    else:
        r_ac = next((r for a, b, r in lat_l if (a, b) == (0, 1)), np.inf)
        r_a2 = next((r for a, b, r in lat_l if (a, b) == (0, 2)), None)
        # fin length of the source layer under A for the kernel of the peak: films plus the dielectric to the neighbours
        area_a = cnt[0] * cell
        g_loss = (g_top[layer, 0] + g_bot[layer, 0]) / area_a
        for m in (layer - 1, layer):
            if 0 <= m < nb - 1:
                g_loss += gz_diel[m, 0] / area_a
        lam = math.sqrt(S[layer, 0] / g_loss) if g_loss > 0 else None
        fields, bump = _peak_fields(cov * (idx2 == 0), cov * (idx2 == 1), S[layer, 0], net.dx, net.dy, lam, OPTIONS["decimation"], OPTIONS["max_cells"])
        micro = None
        n_v = sum(s["n"] for s in seen if s["node"] == 1)
        if n_v:
            rim = sum(s["n"] * rim_minus_mean(S[layer, 1], s["r_cell"], s["a"]) for s in seen if s["node"] == 1) / n_v
            micro = {"via_gz": via_gz, "n": n_v, "rim": rim}
        bump_coef = bump / (2.0 * math.pi * S[layer, 1])
        peak = ZonePeak(layer, 2, r_ac, r_a2, fields, bump_coef, micro, None)
        warn = zone_warnings(net, cov, core)
    peak_extra = peak.extra(th)
    rho = rho_mean.copy()
    if nz == 2:
        rho[0], rho[1] = 0.0, 1e-9                               # keep the profile increasing for the interpolation of the temperature map
    LAST.clear()
    LAST.update(nz=nz, theta=th.copy(), cnt=cnt.copy(), r_ac=r_ac, r_a2=r_a2, peak_extra=peak_extra, warnings=warn, core=core)
    return {"theta": th, "rho": rho, "dist": dist, "peak_extra": peak_extra,
            "K": K, "C": cap.ravel(), "R": R, "layer": layer, "r01": (r_a2 if nz == 2 else peak.single[1] if peak.single else np.inf),
            "peak_coef": peak.single[0] if (nz == 1 and peak.single) else 0.0,
            "source": source, "peak": peak, "nz": nz, "warnings": warn,
            "out": {"top": float((g_top * th).sum()), "bottom": float((g_bot * th).sum()),
                    "heatsinks": float((g_heatsink * th).sum()), "sides": float((g_side * th).sum())}
                   | ({"blocks": float((g_block * th).sum())} if net.block_info else {}),
            "residual": float(np.linalg.norm(K @ theta - Q) / np.linalg.norm(Q))}


def _own_point(system, theta):
    """!
    @brief Rise at the hottest point of the footprint of a heater from its state: the zone peak when the system has one, else the program's.
    @param system System dict of the heater.
    @param theta State vector (layers * nodes,).
    @return float K.
    """
    peak = system.get("peak")
    if peak is None:
        return _ORIGINAL["own_point"](system, theta)
    return peak(np.asarray(theta).reshape(-1, system["R"]))


def _advance_zoned(self, states, dt, powers):
    """!
    @brief `lumped._LumpedAdapter.advance` with the unit source vector of the zoned system (the program's puts the whole power on node 0 of the layer, which would drive A alone).
    @param self The adapter.
    @param states List of state vectors.
    @param dt Time step in s.
    @param powers Power of every heater during the step (W).
    @return list of new states.
    """
    out = []
    for i, s in enumerate(self.systems):
        src = powers[i] * (s["source"] if "source" in s else _unit_source(s))
        out.append(self.steppers[i].advance(states[i], dt, src))
    return out


def advance_245(self, states, dt, powers):
    """!
    @brief `lumped._LumpedAdapter.advance` of release 2.4.5: the whole power of a heater on node 0 of its layer (node A of a zoned system), the control of the profile studies.
    @details Since the adoption (feature/lumped-zones) the program's adapter splits the source itself, so `_ORIGINAL["advance"]` is no longer the unpatched control.
    @param self The adapter.
    @param states List of state vectors.
    @param dt Time step in s.
    @param powers Power of every heater during the step (W).
    @return list of new states.
    """
    out = []
    for i, s in enumerate(self.systems):
        src = np.zeros(len(s["C"]))
        src[s["layer"] * s["R"]] = powers[i]
        out.append(self.steppers[i].advance(states[i], dt, src))
    return out


@contextlib.contextmanager
def patched(**options):
    """!
    @brief Install the zoned network in `pcbthermal.lumped` for the duration of the context; the program's functions are restored on exit.
    @details The program's own zone model (adopted on feature/lumped-zones) is switched off inside (`lumped.ZONES`), so that its decision and its 0.5 mm raster (`cell_for`) do
             not mix with this copy: the raster is the clip of 2.4.5, as in the runs of the README.
    @param options Overrides of `OPTIONS` for the context (for example `zone_macro="cap"`, `zones=False`).
    @return Context manager.
    """
    old = dict(OPTIONS)
    old_zones = lumped.ZONES
    lumped.ZONES = False
    OPTIONS.update(options)
    _ORIGINAL.update(network=lumped._heater_network, own_point=lumped._own_point, advance=lumped._LumpedAdapter.advance, step_responses=lumped.step_responses)
    lumped._heater_network = heater_network
    lumped._own_point = _own_point
    lumped._LumpedAdapter.advance = _advance_zoned                  # the profile runner: the source split between A and C
    lumped.step_responses = step_responses_zoned                    # the decision average-or-resolve when the Lumped model is the reference
    try:
        yield
    finally:
        lumped._heater_network = _ORIGINAL["network"]
        lumped._own_point = _ORIGINAL["own_point"]
        lumped._LumpedAdapter.advance = _ORIGINAL["advance"]
        lumped.step_responses = _ORIGINAL["step_responses"]
        lumped.ZONES = old_zones
        OPTIONS.clear()
        OPTIONS.update(old)


# ------------------------------------------------------------------------------------------------ the transient

def step_responses_zoned(problem, rings=10, cell_mm=1.0, t_end=None, ratio=3.0, per_stage=4, stages=18, theta_scheme=0.5):
    """!
    @brief `lumped.step_responses` for the zoned network: the unit source vector split between A and C and the zone peak at every step (the program's function puts the whole source on node 0).
    @details A copy of the program's function with two lines changed; it must be called inside `patched()` so that `lumped._unit_networks` builds the zoned systems.
    @param problem A Problem with at least one heater.
    @param rings Rings outside each footprint.
    @param cell_mm Raster in mm.
    @param t_end Last time in s (default: ten board time constants).
    @param ratio Growth factor of the step between stages.
    @param per_stage Steps per stage.
    @param stages Number of stages.
    @param theta_scheme 0.5 (Crank-Nicolson) or 1.0 (implicit Euler).
    @return Tuple (times, z, rth) as `lumped.step_responses`.
    """
    net, systems = lumped._unit_networks(problem, rings, cell_mm)
    if t_end is None:
        t_end = 10.0 * board_time_constant(net)
    dt0 = t_end / (per_stage * (ratio ** stages - 1.0) / (ratio - 1.0))
    rth = np.array([_own_point(s, s["theta"].ravel()) for s in systems])
    times, z = [], []
    for system in systems:
        src = system["source"] if "source" in system else _unit_source(system)
        cache = {}
        x, t, row, tt = np.zeros(len(system["C"])), 0.0, [], []
        for j in range(stages):
            dt = dt0 * ratio ** j
            for _ in range(per_stage):
                key = round(dt, 14)
                if key not in cache:
                    A = np.diag(system["C"] / dt) + theta_scheme * system["K"]
                    B = np.diag(system["C"] / dt) - (1.0 - theta_scheme) * system["K"]
                    cache[key] = (lu_factor(A), B)
                lu, B = cache[key]
                x = lu_solve(lu, B @ x + src)
                t += dt
                tt.append(t)
                row.append(_own_point(system, x))
        times, z = tt, z + [row]
    return np.asarray(times), np.asarray(z), rth


def _unit_source(system):
    """!
    @brief Unit source vector of a program system (the whole power on node 0 of the layer).
    @param system System dict of the heater.
    @return numpy.ndarray (layers * nodes,).
    """
    src = np.zeros(len(system["C"]))
    src[system["layer"] * system["R"]] = 1.0
    return src
