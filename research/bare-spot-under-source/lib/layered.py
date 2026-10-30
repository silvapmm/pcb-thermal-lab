#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file layered.py
@brief The layered finite-volume model of the program with the dielectric gaps cut into sub-gaps (extra laminate nodes), on a copy: dense, graded or only where the copper is absent.
@details The arrays of the program's own network (sheet conductance S of every layer node, the vertical conductance of every gap, the conductances to the ambient, the sources) are
         read from `fvm.Network(assemble=False)` and the matrix is assembled again here, so that the node construction of a gap can be changed without editing `pcbthermal/`.
         Construction (the same as `laminate.py` for a one-layer board, applied to a gap): a gap of thickness d is cut into sub-gaps s_1 ... s_m (sum d); a node sits at every boundary
         between sub-gaps; consecutive nodes are joined by k_z A / s_i; the copper node keeps its copper and half of the first sub-gap below (and of the last above), the new node j
         holds (s_j + s_{j+1}) / 2 of laminate and conducts sideways with k_inplane times that thickness. In the cells where a gap is not refined ("passive" cells) the extra nodes
         hold no lateral conduction and are joined in series by equal sub-gaps, which is exactly one link of conductance k_z A / d, so those cells are the program's own.
         With one sub-gap everywhere the result is the program's FVM to round-off (tests/test_layered.py).
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from pcbthermal import fvm


def harmonic(a, b):
    """!
    @brief Harmonic mean 2ab/(a+b) of two conductances, zero where either is zero (the program's rule for the link between neighbouring cells).
    @param a First array.
    @param b Second array.
    @return numpy.ndarray.
    """
    s = a + b
    return np.where(s > 0, 2.0 * a * b / np.where(s > 0, s, 1.0), 0.0)


def graded(d, first, ratio, m):
    """!
    @brief Sub-gap thicknesses of a gap: the first one given, each next one `ratio` times larger, the last absorbs the rest so that the sum is d.
    @param d Gap thickness in m.
    @param first Thickness of the first (outer) sub-gap in m.
    @param ratio Growth ratio of the sub-gaps.
    @param m Number of sub-gaps.
    @return numpy.ndarray of m thicknesses summing to d (if `first` is too large the equal split is used).
    """
    s = first * ratio ** np.arange(m)
    if s[:-1].sum() >= d * 0.9 or m == 1:
        return np.full(m, d / m)
    s[-1] = d - s[:-1].sum()
    return s


def flag_bare(fill, threshold=1.0, margin=0):
    """!
    @brief Cells to refine: those whose copper fill is below a threshold (+ a margin of cells).
    @param fill Copper fill (ny, nx) of the layer(s) that bound the gap (the smaller of the two).
    @param threshold Cells with fill below this are bare enough (1.0: any cell with some laminate showing; the default 1.0 flags a cell with fill < 1).
    @param margin Cells added around the flagged ones (4-neighbour dilation, repeated).
    @return Boolean array (ny, nx).
    """
    m = fill < threshold - 1e-12
    for _ in range(margin):
        d = m.copy()
        d[1:] |= m[:-1]
        d[:-1] |= m[1:]
        d[:, 1:] |= m[:, :-1]
        d[:, :-1] |= m[:, 1:]
        m = d
    return m


def solve(net, gaps, kz, kxy, parts, flags, skin=None, tcu=None):
    """!
    @brief Steady rise of the layered model with refined gaps.
    @param net A fvm.Network built with assemble=False (arrays S, gz, g_amb, Q, cover, fill are read).
    @param gaps Thickness of every gap in m (layers - 1).
    @param kz Through conductivity of every gap in W/mK.
    @param kxy In-plane conductivity of every gap in W/mK.
    @param parts For every gap, the array of its sub-gap thicknesses in m for the refined cells, or None for no refinement (one sub-gap).
    @param flags For every gap, the boolean array (ny, nx) of the refined cells (ignored when parts is None).
    @param skin Optional list (one per gap) of the thickness in m that the laminate of a refined-or-flagged cell contributes to the lateral conduction of each copper node next to the gap
                (instead of d/2); used with parts None to test a thinner lateral path without new unknowns.
    @param tcu Optional copper thickness of every layer in m: the vertical path between two copper nodes then includes the half thickness of each adjacent layer where the copper is absent
                (a node sits at mid-thickness of its layer, copper conducts across it for free, laminate does not): d + (1 - f_a) t_a / 2 + (1 - f_b) t_b / 2.
    @return dict with T (list of per-node arrays (ny, nx) in node order: layer 0, gap-0 nodes, layer 1, ...), top (ny, nx rise of layer 0), peak, nodes (count per cell).
    """
    L, ny, nx = net.nl, net.ny, net.nx
    cell = net.dx * net.dy * net.cover
    # Node list: (layer or gap sub-node), each with its arrays S (lateral), Q, g_amb
    nodes = []
    S = [net.S[l].copy() for l in range(L)]
    Q = [net.Q[l].copy() for l in range(L)]
    G = [net.g_amb[l].copy() for l in range(L)]
    vias = []                                                     # (gap, conductance array) of the barrels of vias in refined gaps
    chain = []                                                    # per gap: list of (S, link conductance arrays between consecutive nodes)
    gap_nodes = []
    for g in range(L - 1):
        # Added laminate path where a layer has no copper (zero where the copper is full: those cells are the program's own)
        if tcu is not None:
            ta, tb = (1.0 - net.fill[g]) * tcu[g] / 2, (1.0 - net.fill[g + 1]) * tcu[g + 1] / 2
        else:
            ta = tb = np.zeros((ny, nx))
        tadd = ta + tb
        via_g = np.maximum(net.gz[g] - kz[g] * cell / gaps[g], 0.0)         # the barrels of vias: parallel to the whole gap, between the two copper nodes
        gz_g = np.where(tadd > 0, kz[g] * cell / (gaps[g] + tadd) + via_g, net.gz[g])
        if parts[g] is None or len(parts[g]) < 2:
            gap_nodes.append(None)
            chain.append([gz_g])
            if skin is not None and skin[g] is not None:
                # A thinner lateral path in the flagged cells: the copper nodes keep only `skin` of the half gap in their lateral conduction
                cut = np.where(flags[g], kxy[g] * (gaps[g] / 2 - np.minimum(skin[g], gaps[g] / 2)) * net.cover, 0.0)
                S[g] = S[g] - cut
                S[g + 1] = S[g + 1] - cut
            continue
        s = np.asarray(parts[g], dtype=float)
        m = len(s)
        fl = flags[g]
        d = gaps[g]
        eq = np.full(m, d / m)
        # Per-cell sub-gap thicknesses: refined cells use `s`, the others equal parts (a series of m equal links is the single link)
        sub = np.where(fl[None], s[:, None, None], eq[:, None, None]).copy()
        sub[0] += ta                                                # the added path goes to the outer sub-gaps (the node sits at mid-thickness of its layer)
        sub[-1] += tb
        links = [kz[g] * cell / sub[i] for i in range(m)]
        vias.append((g, via_g))
        # Lateral conduction: copper nodes give up the laminate that moves to the new nodes (refined cells only)
        S[g] = S[g] - np.where(fl, kxy[g] * (d / 2 - s[0] / 2) * net.cover, 0.0)
        S[g + 1] = S[g + 1] - np.where(fl, kxy[g] * (d / 2 - s[-1] / 2) * net.cover, 0.0)
        extra = []
        for j in range(m - 1):
            th = (s[j] + s[j + 1]) / 2
            extra.append(np.where(fl, kxy[g] * th * net.cover, 0.0))
        gap_nodes.append(extra)
        chain.append(links)
    # Number the nodes: layer 0, gap-0 nodes, layer 1, ...
    order = []
    for l in range(L):
        order.append(("L", l, None))
        if l < L - 1 and gap_nodes[l] is not None:
            for j in range(len(gap_nodes[l])):
                order.append(("G", l, j))
    nn = len(order)
    pos = {key: i for i, key in enumerate(order)}
    idx = np.arange(nn * ny * nx).reshape(nn, ny, nx)
    rows, cols, vals = [], [], []

    def couple(a, b, g):
        a, b, g = a.ravel(), b.ravel(), np.broadcast_to(g, a.shape).ravel()
        keep = g > 0
        a, b, g = a[keep], b[keep], g[keep]
        rows.extend([a, b, a, b])
        cols.extend([a, b, b, a])
        vals.extend([g, g, -g, -g])

    Sn, Qn, Gn = [], [], []
    for key in order:
        kind, l, j = key
        if kind == "L":
            Sn.append(S[l])
            Qn.append(Q[l])
            Gn.append(G[l])
        else:
            Sn.append(gap_nodes[l][j])
            Qn.append(np.zeros((ny, nx)))
            Gn.append(np.zeros((ny, nx)))
    for i in range(nn):
        gx = harmonic(Sn[i][:, :-1], Sn[i][:, 1:]) * net.dy / net.dx
        gy = harmonic(Sn[i][:-1, :], Sn[i][1:, :]) * net.dx / net.dy
        couple(idx[i][:, :-1], idx[i][:, 1:], gx)
        couple(idx[i][:-1, :], idx[i][1:, :], gy)
    for g in range(L - 1):
        seq = [pos[("L", g, None)]] + ([pos[("G", g, j)] for j in range(len(gap_nodes[g]))] if gap_nodes[g] is not None else []) + [pos[("L", g + 1, None)]]
        for a, b, lk in zip(seq[:-1], seq[1:], chain[g]):
            couple(idx[a], idx[b], lk)
    for g, v in vias:
        couple(idx[pos[("L", g, None)]], idx[pos[("L", g + 1, None)]], v)
    diag = np.stack(Gn).ravel()
    rows.append(np.arange(nn * ny * nx))
    cols.append(np.arange(nn * ny * nx))
    vals.append(diag)
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nn * ny * nx,) * 2).tocsc()
    th = spla.spsolve(K, np.stack(Qn).ravel()).reshape(nn, ny, nx)
    top = th[pos[("L", 0, None)]]
    peak_node = float(top.max())
    if tcu is not None:
        # The heat is injected at the node, mid-thickness of the top layer, but the part sits on the face: where the copper is absent half the layer thickness of laminate lies between
        dq = Q[0] * (1.0 - net.fill[0]) * tcu[0] / 2 / (kz[0] * cell)
        top = top + dq
    base = [th[pos[("L", l, None)]] for l in range(L)]
    peak_all = max(float(top.max()), max(float(b.max()) for b in base[1:]) if L > 1 else 0.0)
    return {"T": th, "top": top, "peak": float(top.max()), "peak_all": peak_all, "peak_node": peak_node, "nodes": nn, "unknowns": nn * ny * nx}


def network(problem, cell_mm):
    """!
    @brief The program's own network of a problem on a square grid of the given cell (arrays only, no matrix).
    @param problem A Problem.
    @param cell_mm Cell size in mm.
    @return fvm.Network.
    """
    b = problem.board
    nx, ny = int(round(b.width * 1e3 / cell_mm)), int(round(b.height * 1e3 / cell_mm))
    return fvm.Network(problem, nx, ny, assemble=False)


def gap_data(problem):
    """!
    @brief Thickness, through and in-plane conductivity of every gap of the board.
    @param problem A Problem.
    @return Tuple of three arrays (gaps in m, kz, kxy in W/mK).
    """
    b = problem.board
    kz, kxy, _ = b.gap_properties()
    return b.gap_thicknesses(), kz, kxy
