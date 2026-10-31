#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file gapnet.py
@brief The construction of lib/rule.py on the program's own FVM network: laminate nodes in the gaps (and under the copper of a one-layer board) as extra node layers, built on a `fvm.Network` by
        changing its arrays, so that the program's direct solver, conjugate gradients, transient machinery and the Lumped model's ring sums run on it without a line of the program changed.
@details What is changed on the arrays of `fvm.Network(assemble=False)` (all in `build`):
         * a **gap** (the laminate between copper node a and b; for a one-layer board between the copper node and a new bottom node) is cut into the sub-gaps of `rule.sub_gaps`;
         * in a **flagged cell** the copper nodes keep the copper and half of their first/last sub-gap (S and C lose the rest), every interior node j holds (s_j + s_{j+1}) / 2 of laminate
           (lateral conductance k_inplane times that, heat capacity rho c times that), consecutive nodes are joined by the link of the program times d / s (the barrels of vias are in every
           sub-link: a series of homogeneous pieces is the single link, to round-off, when nothing else changes; `via_mode = "parallel"` leaves them across the whole gap as the copy of
           bare-spot-under-source does);
         * the vertical correction lengthens the first and last sub-gap by (1 - f) t / 2 of the adjacent copper layer (its laminate where there is no copper);
         * in every other cell the gap is the program's single link (`net.gz`), and the interior nodes of that cell are pinned to zero with no coupling (they cost a row, no fill);
         * one-layer boards: the program's own laminate nodes are switched off while the network is built (`no_program_laminate`), the copper node keeps t_cu + s_1 / 2 of the board, a bottom
           node (always present, like the bottom copper node of a two-layer board) takes the last half sub-gap and the bottom film.
         The extra layers are appended after the board layers (as `laminate.py` and `blocks.py` do), joined by `net.extra_links`; `net.n_board` stays the number of copper layers so that the
         results keep only them. Returned network keeps `net.ladder` (what was built) and `net.drop` (the interior nodes that no cell uses, for the ragged solve).
         `solve_sor_general` is a red-black SOR on any bipartite network (the point SOR of `fvm.Network.solve_sor` assumes that extra links join layers a and a + 1).
@note Written without a run in the preparation phase (py_compile only); tests/test_gapnet.py is the first thing to run.
"""

import contextlib
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.sparse import csgraph

from pcbthermal import fvm, laminate

import rule as RU


@contextlib.contextmanager
def no_program_laminate():
    """!
    @brief Switch off the two laminate nodes that `laminate.py` gives a one-layer board while a network is built (restored on exit); the program is not edited, only its module attribute.
    @return Context manager.
    """
    old = laminate.nodes
    laminate.nodes = lambda board, count=None: None
    try:
        yield
    finally:
        laminate.nodes = old


@dataclass
class GapInfo:
    """!
    @brief What was built for one gap.
    """
    gap: int                       # 0-based gap (layers a = gap, b = gap + 1); a one-layer board has gap 0 with b = the bottom node
    d: float                       # thickness (m)
    n: int                         # sub-gaps in the flagged cells
    s: np.ndarray                  # sub-gap thicknesses (m)
    flagged: np.ndarray            # boolean (ny, nx)
    first_layer: int               # index of the first interior node layer (-1 when none)
    interior: int                  # number of interior node layers
    bottom_layer: int = -1         # one-layer board: index of the bottom node layer


@dataclass
class Ladder:
    """!
    @brief Description of the construction on a network.
    """
    rule: object
    gaps: list = field(default_factory=list)
    n_board: int = 1
    cells: int = 0

    def counts(self, one_layer=False):
        """!
        @brief Unknown counts of the construction (rule.unknowns).
        @param one_layer True for a one-layer board.
        @return dict.
        """
        fl = [int(g.flagged.sum()) for g in self.gaps]
        ns = [g.n if g.interior else 1 for g in self.gaps]
        return RU.unknowns(self.n_board, self.cells, fl, ns, one_layer)


def _set_sc(net, b, slab, fill):
    """!
    @brief Recompute the sheet conductance and heat capacity of the copper nodes from the copper fill and the slab of every node.
    @param net fvm.Network (arrays only).
    @param b Board.
    @param slab Thickness represented by every layer node in m, shape (L,).
    @param fill Copper fill (L, ny, nx).
    @return None (net.S, net.C, net.fill are replaced).
    """
    m = b.materials
    k_lam, rcp_lam = b.layer_laminate()
    tc = np.asarray(b.copper_thickness, dtype=float)[:, None, None]
    diel = np.asarray(slab, dtype=float)[:, None, None] - fill * tc
    cell = np.asarray(net.area, dtype=float) if getattr(net, "area", None) is not None else net.dx * net.dy * net.cover
    net.fill = fill
    net.S = (fill * m.k_copper * tc + k_lam[:, None, None] * diel) * net.cover
    net.C = (fill * m.rho_copper * m.cp_copper * tc + diel * rcp_lam[:, None, None]) * cell


def build(problem, cell_mm, rule, fill=None, assemble=True):
    """!
    @brief The program's FVM network with the laminate nodes of a rule.
    @param problem A Problem (no metal blocks).
    @param cell_mm Cell size in mm.
    @param rule A rule.Rule.
    @param fill Optional copper fill (L, ny, nx) that replaces the one computed from the zones (a mask brought from a real board); the Problem still gives geometry and sources.
    @param assemble False: arrays only (the sweeps that do not solve).
    @return fvm.Network with the attributes `ladder` (Ladder) and `drop` (boolean (nl, ny, nx) of the interior nodes no cell uses, for the ragged solve).
    @throws NotImplementedError If the problem has a metal block (outside this study, README 8).
    """
    b = problem.board
    if any(s.is_block() for s in problem.heatsinks):
        raise NotImplementedError("metal blocks are not part of this study")
    nx, ny = max(int(round(b.width * 1e3 / cell_mm)), 2), max(int(round(b.height * 1e3 / cell_mm)), 2)
    use_one = b.layers == 1 and rule.one_layer
    ctx = no_program_laminate() if use_one else contextlib.nullcontext()
    with ctx:
        net = fvm.Network(problem, nx, ny, assemble=False, with_blocks=False)
    return apply_ladder(net, problem, rule, fill, assemble)


def apply_ladder(net, problem, rule, fill=None, assemble=True):
    """!
    @brief Change the arrays of a network (fvm.Network, or the shim of fdmnet.py) into the network of the rule: the whole construction of the module description.
    @param net Network built with assemble=False (and, for a one-layer board with rule.one_layer, without the program's laminate nodes).
    @param problem The Problem.
    @param rule A rule.Rule.
    @param fill Optional copper fill (L, ny, nx) replacing net.fill.
    @param assemble True: net.K = net._assemble() (the FVM); the FDM assembles itself.
    @return The same network, with `ladder` and `drop`.
    """
    b = problem.board
    nx, ny = net.nx, net.ny
    L0 = b.layers
    one = L0 == 1
    use_one = one and rule.one_layer
    ladder = Ladder(rule, [], L0, nx * ny)
    net.ladder, net.drop = ladder, None
    if one and not rule.one_layer:
        # laminate.py as it is: nothing to build (the preset "program" and the comparisons that keep the program's two laminate nodes)
        net.drop = np.zeros((net.nl, ny, nx), dtype=bool)
        if assemble:
            net.K = net._assemble()
        return net
    m = b.materials
    cell = np.asarray(net.area, dtype=float) if getattr(net, "area", None) is not None else net.dx * net.dy * net.cover     # the FDM has the area of the control volume
    hs = float(b.h_side or 0.0)
    edge = net._edge_lengths() if (hs and hasattr(net, "_edge_lengths")) else np.zeros((ny, nx))
    t_cu = np.asarray(b.copper_thickness, dtype=float)
    fl = net.fill.copy() if fill is None else np.asarray(fill, dtype=float).copy()
    if rule.rebuild_slabs and L0 >= 3 and b.dielectrics is None:
        d_all = b.gap_thicknesses()
        slab = t_cu + np.array([(d_all[l - 1] / 2 if l > 0 else 0.0) + (d_all[l] / 2 if l < L0 - 1 else 0.0) for l in range(L0)])
        _set_sc(net, b, slab, fl)
    elif fill is not None:
        _set_sc(net, b, np.asarray(b.slab_thicknesses(), dtype=float), fl)

    # --- Gap data
    gaps = []
    if one:
        t_lam = float(b.slab_thicknesses()[0]) - float(t_cu[0])
        gaps.append(dict(a=0, b=None, d=t_lam, kz=m.k_fr4_through, kxy=m.k_fr4_inplane, rcp=m.rho_fr4 * m.cp_fr4, link=m.k_fr4_through * cell / t_lam, via=np.zeros_like(cell)))
    else:
        d_all = b.gap_thicknesses()
        kz, kxy, rcp = b.gap_properties()
        for g in range(L0 - 1):
            via = np.maximum(net.gz[g] - kz[g] * cell / d_all[g], 0.0)
            gaps.append(dict(a=g, b=g + 1, d=float(d_all[g]), kz=float(kz[g]), kxy=float(kxy[g]), rcp=float(rcp[g]), link=net.gz[g].copy(), via=via))

    new_S, new_C, new_gb, new_gs, new_pin, links = [], [], [], [], [], []
    nxt = L0                                                    # index of the next extra layer
    gz = net.gz.copy() if L0 > 1 else net.gz
    g_bottom, g_side = net.g_bottom.copy(), net.g_side.copy()
    S, C = net.S.copy(), net.C.copy()

    # --- Plan: n and the flagged cells of every gap, then the cost cap (rule.budget) lowers the largest n until the ragged unknowns fit
    plan = []
    for gd in gaps:
        n = RU.n_for_gap(rule, gd["d"])
        fb_ = None if gd["b"] is None else fl[gd["b"]]
        F = RU.flag_cells(rule, fl[gd["a"]], fb_, gd["d"], net.dx, net.active) if n > 1 else np.zeros((ny, nx), dtype=bool)
        plan.append([n if F.any() else 1, F if F.any() else np.zeros((ny, nx), dtype=bool)])
    if rule.budget > 0:
        while True:
            u = RU.unknowns(L0, nx * ny, [int(p_[1].sum()) for p_ in plan], [p_[0] for p_ in plan], one)
            if u["ratio_ragged"] <= rule.budget or all(p_[0] <= 1 for p_ in plan):
                break
            j = int(np.argmax([p_[0] for p_ in plan]))
            plan[j][0] -= 1
            if plan[j][0] <= 1:
                plan[j] = [1, np.zeros((ny, nx), dtype=bool)]

    for gi, gd in enumerate(gaps):
        d, a, bb = gd["d"], gd["a"], gd["b"]
        fa = fl[a]
        fb = None if bb is None else fl[bb]
        n, F = plan[gi]
        s = RU.sub_gaps(d, n, rule.ratio)
        refined = n > 1
        ea = (1.0 - fa) * t_cu[a] / 2.0 if rule.vert else np.zeros((ny, nx))
        eb = (1.0 - fb) * t_cu[bb] / 2.0 if (rule.vert and bb is not None) else np.zeros((ny, nx))
        lam = gd["link"] - gd["via"]                                       # laminate part of the program's link (the barrels are the rest)
        info = GapInfo(gi, d, n, s, F, -1, 0)
        # Lateral and capacity share that moves from the copper node a (and b) to the new nodes, flagged cells only
        if one:
            keep_a = np.where(F, s[0] / 2.0, d / 2.0)                      # one-layer: the copper node keeps t_cu + half the first sub-gap in every cell
            move_a = d - keep_a                                            # (the program's slab for this board holds the whole laminate)
        else:
            keep_a = np.where(F, s[0] / 2.0, d / 2.0)
            move_a = d / 2.0 - keep_a                                      # zero in the cells that are not refined
        S[a] -= gd["kxy"] * move_a * net.cover
        C[a] -= gd["rcp"] * move_a * cell
        g_side[a] -= hs * move_a * edge
        # Interior nodes
        first = nxt
        for j in range(1, n):
            th = (s[j - 1] + s[j]) / 2.0
            new_S.append(np.where(F, gd["kxy"] * th * net.cover, 0.0))
            new_C.append(np.where(F, gd["rcp"] * th * cell, 0.0))
            new_gb.append(np.zeros((ny, nx)))
            new_gs.append(np.where(F, hs * th * edge, 0.0))
            new_pin.append(~F)
            nxt += 1
        info.first_layer, info.interior = (first if n > 1 else -1), n - 1
        # The end node: the copper node b, or the new bottom node of a one-layer board
        if one:
            keep_b = np.where(F, s[-1] / 2.0, d / 2.0)
            new_S.append(gd["kxy"] * keep_b * net.cover)
            new_C.append(gd["rcp"] * keep_b * cell)
            new_gb.append(b.h_bottom * cell)
            new_gs.append(hs * keep_b * edge)
            new_pin.append(~net.active)
            b_idx = nxt
            info.bottom_layer = b_idx
            nxt += 1
            g_bottom[0] = 0.0                                              # the film moves from the copper node to the bottom node
        else:
            move_b = d / 2.0 - np.where(F, s[-1] / 2.0, d / 2.0)
            S[bb] -= gd["kxy"] * move_b * net.cover
            C[bb] -= gd["rcp"] * move_b * cell
            g_side[bb] -= hs * move_b * edge
            b_idx = bb
        # Links. Not refined (and the passive cells of a refined gap): the single link with the vertical correction; the barrels are never corrected
        single = np.where(ea + eb > 0, lam * d / (d + ea + eb) + gd["via"], gd["link"])          # unchanged (bit for bit) where there is nothing to correct
        chain_nodes = [a] + list(range(first, first + n - 1)) + [b_idx]
        if not one:
            if rule.via_mode == "parallel":
                gz[gd["a"]] = np.where(F, gd["via"], single)
            else:
                gz[gd["a"]] = np.where(F, 0.0, single)
        if one:
            links.append((a, b_idx, np.where(F, 0.0, single)))           # the cells that are not refined: the whole laminate is one link from the copper node to the bottom node
        if refined:
            for k in range(n):
                ext = (ea if k == 0 else 0.0) + (eb if k == n - 1 else 0.0)
                sub = lam * d / (s[k] + ext)
                if rule.via_mode != "parallel":
                    sub = sub + gd["via"] * d / s[k]
                links.append((chain_nodes[k], chain_nodes[k + 1], np.where(F, sub, 0.0)))
        ladder.gaps.append(info)

    # --- Append the new layers
    k = nxt - L0
    z = np.zeros((k, ny, nx))
    net.S, net.C = np.concatenate([S, np.stack(new_S)]) if k else S, np.concatenate([C, np.stack(new_C)]) if k else C
    if L0 > 1:
        net.gz = gz
    net.g_top = np.concatenate([net.g_top, z])
    net.g_heatsink = np.concatenate([net.g_heatsink, z])
    net.g_block = np.concatenate([net.g_block, z])
    net.g_bottom = np.concatenate([g_bottom, np.stack(new_gb)]) if k else g_bottom
    net.g_side = np.concatenate([g_side, np.stack(new_gs)]) if k else g_side
    pin_new = np.stack([p | ~net.active for p in new_pin]) if k else np.zeros((0, ny, nx), dtype=bool)
    net.g_pin = np.concatenate([net.g_pin, pin_new.astype(float)]) if k else net.g_pin
    net.g_amb = net.g_top + net.g_bottom + net.g_heatsink + net.g_side + net.g_block + net.g_pin
    drop = np.zeros((net.nl + k, ny, nx), dtype=bool)
    if k:
        drop[L0:] = np.stack(new_pin) & net.active[None]                   # interior nodes of the cells that do not use them (the bottom node of a one-layer board is never one)
        for g in ladder.gaps:
            if g.bottom_layer >= 0:
                drop[g.bottom_layer] = False
    net.drop = drop
    net.Q = np.concatenate([net.Q, z])
    net.Qw = [np.concatenate([w, z]) for w in net.Qw]
    net.Qw_matrix = sp.csc_matrix(np.stack([w.ravel() for w in net.Qw], axis=1)) if net.Qw else sp.csc_matrix((net.Q.size, 0))
    net.footprints = [np.flatnonzero(w.ravel() > 0) for w in net.Qw]
    net.extra_links = list(net.extra_links) + links
    net.nl = nxt
    if one:
        net.laminate_layers = [g.bottom_layer for g in ladder.gaps if g.bottom_layer >= 0]
    if assemble:
        net.K = net._assemble()
    return net


def footprint_values(net, theta, problem, rule):
    """!
    @brief The rise in every cell of the footprint of every heater, raw (the node) and with the face term.
    @details A part on the face of a copper layer injects at the node, which sits at mid-thickness of the layer; where the copper is absent the half layer of laminate between the node and
             the face adds Q (1 - f)^p t / (2 k_z A) (p = rule.face, applied to cells with f < 1; negative: no term). Only the outer layers (the top: layer 1) have a face.
    @param net The network from build().
    @param theta Solution (nl, ny, nx) in K.
    @param problem The Problem.
    @param rule The rule.
    @return list of (raw, corrected) pairs of 1D arrays, one per heater.
    """
    b = problem.board
    cell = np.asarray(net.area, dtype=float) if getattr(net, "area", None) is not None else net.dx * net.dy * net.cover
    t_cu = np.asarray(b.copper_thickness, dtype=float)
    kz_lam = b.gap_properties()[0] if b.layers > 1 else np.array([b.materials.k_fr4_through])
    out = []
    for w, h in zip(net.Qw, problem.heaters):
        l = h.layer
        sel = w[l] > 0
        raw = theta[l][sel]
        if rule.face < 0 or l not in (0, b.layers - 1) or not sel.any():
            out.append((raw, raw.copy()))
            continue
        kz = kz_lam[0] if l == 0 else kz_lam[-1]
        f = net.fill[l][sel]
        pw = np.power(np.maximum(1.0 - f, 0.0), rule.face) if rule.face > 0 else np.ones_like(f)
        fac = np.where(f < 1.0 - 1e-12, pw, 0.0)
        out.append((raw, raw + net.Q[l][sel] * fac * t_cu[l] / (2.0 * kz * cell[sel])))
    return out


def peak_under_parts(net, theta, problem, rule):
    """!
    @brief Peak rise under the parts with the face term, and the raw peak of the node.
    @param net The network from build().
    @param theta Solution (nl, ny, nx) in K.
    @param problem The Problem.
    @param rule The rule.
    @return tuple (peak with the term, raw peak) over the cells of the footprints, in K.
    """
    vals = footprint_values(net, theta, problem, rule)
    return max(float(c.max()) for _, c in vals if c.size), max(float(r.max()) for r, _ in vals if r.size)


def solve_ragged(net):
    """!
    @brief Steady solve without the interior nodes that no cell uses (the cheap implementation of the dense layers: slice the matrix, solve, scatter).
    @param net The network from build() (K assembled).
    @return tuple (theta (nl, ny, nx), number of unknowns solved).
    """
    keep = ~net.drop.ravel()
    idx = np.flatnonzero(keep)
    Kr = net.K.tocsr()[idx][:, idx].tocsc()
    x = np.zeros(net.K.shape[0])
    x[idx] = spla.spsolve(Kr, net.Q.ravel()[idx], permc_spec=fvm.ORDERING)
    return x.reshape(net.nl, net.ny, net.nx), int(idx.size)


def two_colour(K):
    """!
    @brief Two-colouring of the graph of a symmetric matrix (the colours of a red-black sweep), or None when the graph has an odd cycle.
    @param K Sparse symmetric matrix.
    @return numpy.ndarray of 0/1 per unknown, or None.
    """
    A = (abs(K) > 0).astype(int)
    A.setdiag(0)
    A.eliminate_zeros()
    n = A.shape[0]
    colour = -np.ones(n, dtype=int)
    for start in range(n):
        if colour[start] >= 0:
            continue
        order = csgraph.breadth_first_order(A, start, directed=False, return_predecessors=False)
        dist = csgraph.shortest_path(A, directed=False, unweighted=True, indices=start)
        colour[order] = (dist[order].astype(int)) % 2
    coo = A.tocoo()
    if np.any(colour[coo.row] == colour[coo.col]):
        return None
    return colour


def solve_sor_general(net, omega=None, tol=1e-9, max_iter=200000):
    """!
    @brief Red-black SOR on the assembled matrix of any network whose graph is bipartite (the ladder, with vias in the sub-links), by sparse row blocks of the two colours.
    @details Same residual stopping rule as `fvm.Network.solve_sor` (|K theta - Q| / |Q| < tol, checked every 10 sweeps) and the same default omega, 2 / (1 + sin(pi / max(nx, ny))), so that
             the sweeps of the program's network and of the ladder are comparable. A pinned node (zero coupling) converges in one sweep.
    @param net Network with K and Q.
    @param omega Relaxation factor (None: the program's default).
    @param tol Residual tolerance.
    @param max_iter Sweep limit.
    @return tuple (theta (nl, ny, nx), residual, dict(iterations, converged, omega, colours_ok)).
    """
    K = net.K.tocsr()
    q = net.Q.ravel()
    col = two_colour(K)
    if col is None:
        return None, np.inf, {"iterations": 0, "converged": False, "omega": omega, "colours_ok": False}
    if omega is None:
        omega = 2.0 / (1.0 + np.sin(np.pi / max(net.nx, net.ny)))
    diag = K.diagonal()
    idx = [np.flatnonzero(col == c) for c in (0, 1)]
    rows = [K[i] for i in idx]
    x = np.zeros(K.shape[0])
    qn = max(np.linalg.norm(q), 1e-300)
    converged, it = False, 0
    for it in range(1, max_iter + 1):
        for c in (0, 1):
            i = idx[c]
            r = q[i] - rows[c] @ x
            x[i] += omega * r / diag[i]
        if it % 10 == 0 and np.linalg.norm(K @ x - q) / qn < tol:
            converged = True
            break
    res = float(np.linalg.norm(K @ x - q) / qn)
    return x.reshape(net.nl, net.ny, net.nx), res, {"iterations": it, "converged": converged, "omega": float(omega), "colours_ok": True}
