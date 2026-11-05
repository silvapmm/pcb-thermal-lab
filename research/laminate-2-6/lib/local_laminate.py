#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file local_laminate.py
@brief Prototype of the LOCAL laminate rule (proposal A of research/laminate-2-6): more and graded sub-layers only under and around small parts, the default rule elsewhere; also the
       optional extra flag of the cells at the board edge (proposal B, the nodes version).
@details The program is not edited: `local_rule(problem, ...)` is a context manager that replaces, for the duration of a run, the three functions of `pcbthermal.laminate` that the FVM and
         FDM call (`plan_gaps`, `build`, `count_unknowns`). It is a copy of `laminate.build` generalised to a chain that differs from cell to cell.

         **Chains.** A gap of thickness d has one *fine* chain of n_f sub-gaps (depth fractions `u`, uniform or geometric: the sub-gaps grow by the ratio `grade` away from the face of
         the copper layer that carries the part). A cell with level n_c (n_f / n_c an integer, a power of two) uses every r = n_f / n_c -th node of the fine chain, so the depths of the
         coarse cells are a subset of the fine ones (the same layer index means the same depth). The node of a cell holds the laminate half way to its two neighbours in ITS chain
         (lateral conductance and capacity), so the laminate is conserved cell by cell. The unused interior nodes are the `drop` mask of the ladder and cost nothing in the direct solve.

         **Levels.** Default: n0 = laminate.n_for_gap in the cells the default rule flags. Around a small part (the side of the region through which its heat enters the laminate, as in
         checks._spread_side, smaller than d / (n0 * TRIGGER)) the level goes up to n_p = n0 2^m >= d / (target * side) (at most n_cap), in the footprint grown by `margin` cells, and
         halves with every further `margin` cells. Only the cells that the default rule flags are refined (a cell with copper on both sides of the gap does not need it).

         **Edge cells (proposal B).** With `edge=True` the cells that touch the board edge (and the `edge_margin` cells next to them) are flagged at level n0 even where the copper is
         full; with the edge coefficient this lets the laminate of the edge lose heat at its own temperature (research/analytic-edge-spatial 8.4).

         Limits of the prototype: boards of two or more layers (a one-layer board keeps the program's rule), no metal block, the footprint is the bounding raster of the polygon.
"""

import contextlib
import math

import numpy as np
from scipy import ndimage

from pcbthermal import checks, laminate
from pcbthermal.geometry import coverage_fraction

TRIGGER = 0.10         # A part is "small" for a gap when d / n0 > TRIGGER * side (default value of the prototype; the warning of checks uses 0.15 bare, 0.10 pad)
TARGET = 0.05          # Sub-gap aimed at under a small part: TARGET * side
N_CAP = 32             # Most sub-gaps of the fine chain


class LocalPlan:
    """!
    @brief What the local rule decided for one gap (the fields of laminate.GapPlan plus the chain).
    """

    def __init__(self, gap, d, n_f, lvl, u):
        """!
        @brief Store the plan.
        @param gap 0-based gap.
        @param d Gap thickness in m.
        @param n_f Sub-gaps of the fine chain.
        @param lvl Integer array (ny, nx): sub-gaps of the chain of every cell (0: the gap is one link).
        @param u Depth fractions of the fine chain, n_f + 1 values from 0 (upper copper node) to 1.
        @return None.
        """
        self.gap, self.d, self.n, self.lvl, self.u = gap, d, n_f, lvl, u
        self.flagged = lvl > 0


def depths(n_f, grade, toward_top):
    """!
    @brief Depth fractions of a graded chain.
    @param n_f Number of sub-gaps.
    @param grade Ratio of every sub-gap to the one nearer the face of the part (1: uniform).
    @param toward_top True when the part is on the layer above the gap (finest sub-gap at the top).
    @return numpy array of n_f + 1 values from 0 to 1.
    """
    w = grade ** np.arange(n_f, dtype=float)
    if not toward_top:
        w = w[::-1]
    return np.concatenate([[0.0], np.cumsum(w) / w.sum()])


def _part_info(problem, fill, dx, dy):
    """!
    @brief The footprint and the effective side of every part.
    @param problem A Problem.
    @param fill Copper fill (L, ny, nx).
    @param dx Cell width in m.
    @param dy Cell height in m.
    @return List of (layer, footprint mask, effective side in m).
    """
    L, ny, nx = fill.shape
    out = []
    for h in problem.heaters:
        poly = np.asarray(h.polygon, dtype=float)
        side = float(min(np.ptp(poly[:, 0]), np.ptp(poly[:, 1])))
        cov = coverage_fraction(h.polygon, nx, ny, dx, dy, 4)
        foot = cov > 0
        if not foot.any() or side <= 0:
            continue
        mostly = cov >= 0.5
        cu = fill[h.layer] >= 0.5
        eff = side
        if cu.any() and (foot & cu).any():
            dist = ndimage.distance_transform_edt(cu) if not cu.all() else None
            eff = checks._spread_side(fill[h.layer], mostly if mostly.any() else foot, side, dx, dist)
        out.append((h.layer, foot, eff))
    return out


def make_plan_gaps(problem, trigger=TRIGGER, target=TARGET, n_cap=N_CAP, grade=1.0, margin_scale=1.0, edge=False, edge_margin=1):
    """!
    @brief Build the replacement of laminate.plan_gaps for one problem.
    @param problem A Problem (its heaters give the small parts).
    @param trigger A part is small for a gap when d / n0 > trigger * side.
    @param target Sub-gap aimed at under a small part, as a share of its side.
    @param n_cap Most sub-gaps of the fine chain.
    @param grade Grading ratio of the fine chain (1: uniform).
    @param margin_scale Multiplier of the margin (cells) around a part that gets the fine level.
    @param edge True to flag the cells at the board edge (proposal B).
    @param edge_margin Cells next to the edge cells that are flagged too.
    @return Function (board, fill, dx, active, s_max=None, n_max=None) -> list of LocalPlan.
    """

    def plan(board, fill, dx, active, s_max=None, n_max=None):
        """!
        @brief Local replacement of laminate.plan_gaps.
        @param board A Board.
        @param fill Copper fill (L, ny, nx).
        @param dx Cell size in m.
        @param active Boolean (ny, nx) of the cells on the board.
        @param s_max Longest sub-gap (None: parameters()).
        @param n_max Most sub-gaps (None: parameters()).
        @return List of LocalPlan, one per gap.
        """
        assert board.layers >= 2, "the prototype is for boards of two or more layers"
        ps, pn = laminate.parameters()
        s_max, n_max = ps if s_max is None else s_max, pn if n_max is None else n_max
        L, ny, nx = fill.shape
        dy = board.height / ny
        dxx = board.width / nx
        parts = _part_info(problem, fill, dxx, dy)
        d_all = board.gap_thicknesses()
        if edge:
            ring = np.zeros((ny, nx), dtype=bool)
            ring[0, :] = ring[-1, :] = True
            ring[:, 0] = ring[:, -1] = True
            ring = ndimage.binary_dilation(ring, iterations=edge_margin) & active
        out = []
        for g in range(L - 1):
            d = float(d_all[g])
            n0 = laminate.n_for_gap(d, s_max, n_max)
            flagged = laminate.flag_cells(fill[g], fill[g + 1], d, dx, active) if n0 > 1 else np.zeros((ny, nx), dtype=bool)
            if edge and n0 > 1:
                flagged = flagged | ring
            lvl = np.where(flagged, n0, 0)
            m0 = laminate.margin_cells(d, dx)
            n_f = n0
            toward_top = None
            near = [(lay, foot, eff) for (lay, foot, eff) in parts if lay in (g, g + 1)]
            reqs = []
            for lay, foot, eff in near:
                if n0 < 1 or d / n0 <= trigger * eff * (1 + 1e-9) or not (flagged & foot).any():
                    continue
                n_p = n0
                while n_p < n_cap and d / n_p > target * eff * (1 + 1e-9):
                    n_p *= 2
                reqs.append((lay, foot, min(n_p, n_cap)))
            if reqs:
                n_f = max(r[2] for r in reqs)
                toward_top = (max(reqs, key=lambda r: r[2])[0] == g)
                for lay, foot, n_p in reqs:
                    levels = int(round(math.log2(n_p / n0)))
                    dist = ndimage.distance_transform_edt(~foot)
                    for m in range(levels, 0, -1):             # finest level first: its region is the smallest
                        nm = n0 * 2 ** m
                        reach = m0 * margin_scale * (levels - m + 1)
                        lvl = np.where((dist <= reach + 1e-9) & flagged & (lvl < nm), nm, lvl)
            u = depths(n_f, grade, True if toward_top is None else toward_top)
            out.append(LocalPlan(g, d, n_f, lvl, u))
        return out

    return plan


def build_local(board, fill, cell, cover, active, edge, S, C, gz, g_bottom, g_side, plans):
    """!
    @brief Replacement of laminate.build for LocalPlan chains (same arguments and result).
    @param board A Board (two layers or more).
    @param fill Copper fill (L, ny, nx).
    @param cell Board area of every cell in m2.
    @param cover Board share of every cell.
    @param active Boolean (ny, nx) of the cells on the board.
    @param edge Exposed edge length of every cell in m.
    @param S Lateral conductance of the copper nodes.
    @param C Heat capacity of the copper nodes.
    @param gz Single links between copper layers.
    @param g_bottom Bottom-face conductance of the copper nodes.
    @param g_side Edge conductance of the copper nodes.
    @param plans List of LocalPlan (or of laminate.GapPlan, then the original build is used).
    @return laminate.LadderBuild.
    """
    if not plans or not isinstance(plans[0], LocalPlan):
        return _ORIG["build"](board, fill, cell, cover, active, edge, S, C, gz, g_bottom, g_side, plans)
    ny, nx = cell.shape
    L0 = board.layers
    t_cu = np.asarray(board.copper_thickness, dtype=float)
    hs = float(board.h_side or 0.0)
    kz_g, kxy_g, rcp_g = board.gap_properties()
    S, C, g_side, g_bottom = S.copy(), C.copy(), g_side.copy(), g_bottom.copy()
    gz = gz.copy()
    out = laminate.LadderBuild(S, C, gz, g_bottom, g_side)

    def first_last(p):
        """!
        @brief Per-cell first and last sub-gap (m) of the chain of the plan.
        @param p A LocalPlan.
        @return Tuple of arrays (ny, nx).
        """
        sf, sl = np.zeros((ny, nx)), np.zeros((ny, nx))
        for lv in np.unique(p.lvl[p.lvl > 0]):
            r = p.n // lv
            m = p.lvl == lv
            sf[m] = p.d * (p.u[r] - p.u[0])
            sl[m] = p.d * (p.u[p.n] - p.u[p.n - r])
        return sf, sl

    firsts = {p.gap: first_last(p) for p in plans}
    share = np.ones((L0, ny, nx))
    held = board.slab_thicknesses() - t_cu
    demand = np.zeros((L0, ny, nx))
    for p in plans:
        sf, sl = firsts[p.gap]
        demand[p.gap] += np.where(p.flagged, p.d / 2.0 - sf / 2.0, 0.0)
        demand[p.gap + 1] += np.where(p.flagged, p.d / 2.0 - sl / 2.0, 0.0)
    short = demand > held[:, None, None] * (1.0 + 1e-12)
    share = np.where(short, held[:, None, None] / np.where(short, demand, 1.0), 1.0)
    nxt = L0
    drop = []
    for p in plans:
        d, n_f, F, a = p.d, p.n, p.flagged, p.gap
        b = a + 1
        sf, sl = firsts[a]
        kz, kxy, rcp = float(kz_g[a]), float(kxy_g[a]), float(rcp_g[a])
        lam = gz[a].copy()
        ea = (1.0 - fill[a]) * t_cu[a] / 2.0
        eb = (1.0 - fill[b]) * t_cu[b] / 2.0
        single = np.where(ea + eb > 0, lam * d / (d + ea + eb), lam)
        move_a = (d / 2.0 - np.where(F, sf / 2.0, d / 2.0)) * share[a]
        move_b = (d / 2.0 - np.where(F, sl / 2.0, d / 2.0)) * share[b]
        fill_in = np.where((share[a] < 1.0) | (share[b] < 1.0), 0.5 * (share[a] + share[b]), 1.0)
        out.S[a] = np.maximum(out.S[a] - kxy * move_a * cover, 0.0)
        out.C[a] = np.maximum(out.C[a] - rcp * move_a * cell, 0.0)
        out.g_side[a] -= hs * move_a * edge
        out.S[b] = np.maximum(out.S[b] - kxy * move_b * cover, 0.0)
        out.C[b] = np.maximum(out.C[b] - rcp * move_b * cell, 0.0)
        out.g_side[b] -= hs * move_b * edge
        rcell = np.where(F, n_f // np.maximum(p.lvl, 1), 0)         # Stride of the chain of every cell in the fine chain
        first = nxt
        u = p.u
        for j in range(1, n_f):
            uses = F & (rcell > 0) & (j % np.maximum(rcell, 1) == 0)
            th = np.zeros((ny, nx))
            for r in np.unique(rcell[uses]):
                m = uses & (rcell == r)
                th[m] = d * (u[j + r] - u[j - r]) / 2.0              # Laminate half way to the neighbours of this cell's chain
            out.layers.append({"S": np.where(uses, kxy * th * cover * fill_in, 0.0), "C": np.where(uses, rcp * th * cell * fill_in, 0.0),
                               "g_bottom": np.zeros((ny, nx)), "g_side": np.where(uses, hs * th * edge * fill_in, 0.0), "pin": ~uses})
            drop.append(~uses)
            nxt += 1
        out.gz[a] = np.where(F, 0.0, single)

        def node(k):
            """!
            @brief Index of the node at fine depth k.
            @param k Fine-chain index 0..n_f.
            @return Layer index.
            """
            return a if k == 0 else (b if k == n_f else first + k - 1)

        for r in np.unique(rcell[F]):
            m = F & (rcell == r)
            for k in range(r, n_f + 1, r):
                ext = (ea if k - r == 0 else 0.0) + (eb if k == n_f else 0.0)
                out.links.append((node(k - r), node(k), np.where(m, lam * d / (d * (u[k] - u[k - r]) + ext), 0.0)))
    full = np.zeros((nxt, ny, nx), dtype=bool)
    if drop:
        full[L0:] = np.stack(drop)
    out.ladder = laminate.Ladder(plans, L0, False, full, -1)
    return out


def count_local(board, plans, cells):
    """!
    @brief Replacement of laminate.count_unknowns for LocalPlan chains.
    @param board A Board.
    @param plans List of plans.
    @param cells Cells of the grid.
    @return Tuple (unknowns, node layers).
    """
    if not plans or not isinstance(plans[0], LocalPlan):
        return _ORIG["count_unknowns"](board, plans, cells)
    L = board.layers
    layers = L + sum(p.n - 1 for p in plans)
    unknowns = L * cells
    for p in plans:
        rcell = np.where(p.flagged, p.n // np.maximum(p.lvl, 1), 0)
        for j in range(1, p.n):
            unknowns += int((p.flagged & (j % np.maximum(rcell, 1) == 0)).sum())
    return unknowns, layers


_ORIG = {"plan_gaps": laminate.plan_gaps, "build": laminate.build, "count_unknowns": laminate.count_unknowns}


@contextlib.contextmanager
def local_rule(problem, **kw):
    """!
    @brief Run with the local laminate rule (replaces three functions of pcbthermal.laminate inside the block; this process only).
    @param problem The Problem that will be run (its heaters give the small parts).
    @param kw Options of make_plan_gaps.
    @return Context manager.
    """
    laminate.plan_gaps = make_plan_gaps(problem, **kw)
    laminate.build = build_local
    laminate.count_unknowns = count_local
    try:
        yield
    finally:
        laminate.plan_gaps, laminate.build, laminate.count_unknowns = _ORIG["plan_gaps"], _ORIG["build"], _ORIG["count_unknowns"]
