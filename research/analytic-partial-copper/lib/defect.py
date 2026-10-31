#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file defect.py
@brief A candidate for the Analytic model on partial copper: the cosine series of a board of bare nodes plus a Green-function (Woodbury) correction for the lateral conductance of the copper, and laminate nodes through the thickness.

@details The program's Analytic model replaces the copper of every layer by one uniform sheet (the fill averaged with weights K0(r / lambda) around the heaters) and solves it by a cosine
         series. A copper pad on bare laminate is not a uniform sheet: the heat spreads in the pad and meets a weak sheet at its edge. This candidate does two things.

         1. **The stack is a list of nodes** (`stack()`): the copper layers, and between them n nodes through each laminate gap (a one-layer board gets n laminate nodes under the copper, the
            construction of `pcbthermal/laminate.py`), joined by k_z A / gap. The program has one node per copper layer and, for a one-layer board, the laminate as a film in series with the
            bottom film (`laminate.series_bottom_problem`).
         2. **The copper is a defect on a bare base**: the series is solved for the board in which every node has the sheet conductance of its weakest tile (S0, the bare laminate where a copper
            layer has gaps), and the copper that a tile adds, dS = S_link - S0 >= 0 on the link between two tiles (S_link the harmonic mean of the two tile sheets, the rule of the FVM), is put
            back through the tile Green-function system `(I + G C) y = y0` that the program uses for vias and heatsinks (`analytic.solve_steady`), with C the lateral Laplacian of the added
            conductance on the tile mean temperatures, and the heat the defect injects, f = -C y, projected on the cosine modes.

         The base is the weakest sheet and not the strongest one on purpose: the correction then acts only where there is copper, and it converges with the tile size (a base of copper with
         negative defects does not: the discrete Laplacian of the tiles removes too little at the wave numbers of a 6 mm source, 1 mm tiles still 5 points low, measured in README 5.4).
         Nothing of the program is edited; the helpers it exposes are read.
@note A measured candidate (research/analytic-partial-copper), not a program change.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pcbthermal import analytic                                               # noqa: E402
from pcbthermal.geometry import zone_fill                                     # noqa: E402


def stack(board, n_sub=1):
    """!
    @brief The node list of a board: copper nodes and the laminate nodes between and under them.
    @param board A Board.
    @param n_sub Nodes through every laminate gap (a one-layer board: laminate nodes under the copper). 1 reproduces the nodes of a multilayer board of the program.
    @return dict with kind (list: "cu" with the 0-based copper layer, or "lam"), slab (m), tc (copper thickness of the node, m), k_xy (laminate in-plane conductivity of the node),
            g_up (vertical conductance per area to the node above, W/m2K; entry 0 is unused), h_top, h_bottom (films, W/m2K).
    """
    L = board.layers
    tc = [float(x) for x in np.asarray(board.copper_thickness, dtype=float)]
    m = board.materials
    nodes = []
    if L == 1:
        t_lam = float(board.slab_thicknesses()[0]) - tc[0]
        g = t_lam / n_sub
        nodes.append(("cu", 0, tc[0] + g / 2, tc[0], m.k_fr4_inplane, 0.0))
        for i in range(n_sub):
            slab = g if i < n_sub - 1 else g / 2
            nodes.append(("lam", None, slab, 0.0, m.k_fr4_inplane, m.k_fr4_through / g))
    else:
        kz, kxy, _ = board.gap_properties()
        gaps = board.gap_thicknesses()
        for l in range(L):
            slab = tc[l] + (gaps[l - 1] / (2 * n_sub) if l > 0 else 0.0) + (gaps[l] / (2 * n_sub) if l < L - 1 else 0.0)
            k_here = kxy[l] if l < L - 1 else kxy[l - 1]
            # A copper node is joined to the node above by the last sub-gap of the gap above it
            g_up = float(kz[l - 1] * n_sub / gaps[l - 1]) if l > 0 else 0.0
            nodes.append(("cu", l, slab, tc[l], float(k_here), g_up))
            if l < L - 1:
                for _ in range(1, n_sub):
                    nodes.append(("lam", None, gaps[l] / n_sub, 0.0, float(kxy[l]), float(kz[l] * n_sub / gaps[l])))
    return {"kind": [(n[0], n[1]) for n in nodes], "slab": np.array([n[2] for n in nodes]), "tc": np.array([n[3] for n in nodes]), "k_xy": np.array([n[4] for n in nodes]),
            "g_up": np.array([n[5] for n in nodes]), "h_top": float(board.h_top), "h_bottom": float(board.h_bottom)}


def solve(problem, n_sub=1, tile_mm=1.0, cell_mm=0.5, n_terms=300, n_green=None, base="min", max_unknowns=6000):
    """!
    @brief Solve a Problem (copper zones and heaters on the top layer, no vias or heatsinks) with the stack of nodes and the copper as a defect on the bare base.
    @param problem A Problem.
    @param n_sub Nodes through every laminate gap (1: the program's nodes; a one-layer board then has one laminate node, not the series film).
    @param tile_mm Tile size in mm of the copper links.
    @param cell_mm Cell size in mm of the sampling grid of the result.
    @param n_terms Cosine modes per direction of the base solution.
    @param n_green Cosine modes per direction of the tile Green function (None: enough for the tile: board / tile times 1.2).
    @param base "min": the base board is the weakest sheet of every node and the copper is added on the links (dS >= 0); "max": the base is the strongest and the bare tiles subtract.
    @param max_unknowns Largest size of the dense tile system (tiles with a defect times the nodes that carry one).
    @return dict with T (nodes, ny, nx) rise over the ambient, max (K, on the first node), tiles (number of tiles with a link that differs from the base) and nodes.
    @throws ValueError If a heater is not on the first layer, the board has vias, heatsinks or an outline (not modelled here), or the tile system is larger than max_unknowns.
    @note The fill of a tile that a copper edge crosses enters the harmonic mean like the FVM's partly covered cell, so a copper edge in the middle of a tile behaves as if the copper
          reached further (README, chapter Review: -3 to -8 % against the FVM with the same nodes for an edge half a 1 mm tile off the grid). Results are claimed only for edges on tile edges.
    """
    problem.validate()
    b = problem.board
    W, H, L = b.width, b.height, b.layers
    if any(h.layer != 0 for h in problem.heaters):
        raise ValueError("the candidate takes heaters on the first copper layer")
    # Vias, heatsinks and outlines are not part of the construction: refuse instead of silently dropping them (review finding)
    if problem.vias or problem.heatsinks or b.has_outline():
        raise ValueError("the candidate does not model vias, heatsinks or a board outline")
    st = stack(b, n_sub)
    n_nodes = len(st["slab"])
    m = b.materials
    ntx, nty = max(int(round(W * 1e3 / tile_mm)), 2), max(int(round(H * 1e3 / tile_mm)), 2)
    tw, th = W / ntx, H / nty
    fill = zone_fill(problem.zones, L, ntx, nty, tw, th, 4)
    # Tile sheet of every node: copper nodes mix copper and laminate by the fill, laminate nodes are bare
    S_t = np.empty((n_nodes, nty, ntx))
    for i, (kind, l) in enumerate(st["kind"]):
        f = fill[l] if kind == "cu" else np.zeros((nty, ntx))
        S_t[i] = f * m.k_copper * st["tc"][i] + st["k_xy"][i] * (st["slab"][i] - f * st["tc"][i])
    S0 = S_t.reshape(n_nodes, -1).min(axis=1) if base == "min" else S_t.reshape(n_nodes, -1).max(axis=1)
    # Base solution
    M = N = n_terms
    ex = np.where(np.arange(M) == 0, 1.0, 2.0)
    ey = np.where(np.arange(N) == 0, 1.0, 2.0)
    q = np.zeros((M, N, n_nodes))
    for ht, unit in zip(problem.heaters, analytic._heater_unit_sources(problem, M, N)):
        q[:, :, 0] += ht.power * unit[:, :, 0]
    h_l = np.zeros(n_nodes)
    h_l[0] += st["h_top"]
    h_l[-1] += st["h_bottom"]
    k2 = ((np.arange(M) * np.pi / W) ** 2)[:, None] + ((np.arange(N) * np.pi / H) ** 2)[None, :]
    A = np.zeros((M, N, n_nodes, n_nodes))
    for i in range(n_nodes):
        A[:, :, i, i] += S0[i] * k2 + h_l[i]
        if i > 0:
            g = st["g_up"][i]
            A[:, :, i, i] += g
            A[:, :, i - 1, i - 1] += g
            A[:, :, i, i - 1] -= g
            A[:, :, i - 1, i] -= g
    Ainv = np.linalg.inv(A)
    a_mn = np.einsum("mnlk,mnk->mnl", Ainv, q)
    # Links whose sheet differs from the base
    links = []
    for i in range(n_nodes):
        sx = 2.0 * S_t[i][:, :-1] * S_t[i][:, 1:] / (S_t[i][:, :-1] + S_t[i][:, 1:])
        for r, c in np.argwhere(np.abs(sx - S0[i]) > 1e-9 * S0[i]):
            links.append((i, (r, c), (r, c + 1), (sx[r, c] - S0[i]) * th / tw))
        sy = 2.0 * S_t[i][:-1, :] * S_t[i][1:, :] / (S_t[i][:-1, :] + S_t[i][1:, :])
        for r, c in np.argwhere(np.abs(sy - S0[i]) > 1e-9 * S0[i]):
            links.append((i, (r, c), (r + 1, c), (sy[r, c] - S0[i]) * tw / th))
    Nt = 0
    if links:
        mask = np.zeros((nty, ntx), dtype=bool)
        for _, a_, b_, _ in links:
            mask[a_] = True
            mask[b_] = True
        active = np.argwhere(mask)
        Nt = len(active)
        pos = {(int(r), int(c)): k for k, (r, c) in enumerate(active)}
        rect = [(c * tw, (c + 1) * tw, r * th, (r + 1) * th) for r, c in active]
        PX = np.stack([analytic._cos_projection(x1, x2, W, M) for x1, x2, _, _ in rect], axis=1)
        PY = np.stack([analytic._cos_projection(y1, y2, H, N) for _, _, y1, y2 in rect], axis=1)
        Ux, Uy = PX / tw, PY / th
        y0 = np.stack([np.einsum("mr,mn,nr->r", Ux, a_mn[:, :, i], Uy) for i in range(n_nodes)], axis=1)
        ng = int(min(M, n_green or max(100, 1.2 * W * 1e3 / tile_mm)))
        # Only the nodes that carry a defect need rows in G
        ids = sorted({lk[0] for lk in links})
        if Nt * len(ids) > max_unknowns:
            raise ValueError(f"{Nt} tiles x {len(ids)} nodes = {Nt * len(ids)} unknowns above the limit of {max_unknowns}: use a larger tile")
        Gm = np.zeros((Nt, len(ids), Nt, len(ids)))
        for a, i in enumerate(ids):
            for c, k in enumerate(ids):
                Wm = Ainv[:ng, :ng, i, k] * (ex[:ng, None] * ey[None, :ng]) / (W * H)
                acc = np.zeros((Nt, Nt))
                for n in range(ng):
                    acc += ((Ux[:ng].T * Wm[:, n]) @ Ux[:ng]) * np.outer(Uy[n], Uy[n])
                Gm[:, a, :, c] = acc
        nid = len(ids)
        G = Gm.reshape(Nt * nid, Nt * nid)
        C = np.zeros((Nt * nid, Nt * nid))
        for i, a_, b_, d in links:
            ia = ids.index(i)
            p, q_ = pos[(int(a_[0]), int(a_[1]))] * nid + ia, pos[(int(b_[0]), int(b_[1]))] * nid + ia
            C[p, p] += d
            C[q_, q_] += d
            C[p, q_] -= d
            C[q_, p] -= d
        y0v = np.stack([y0[:, i] for i in ids], axis=1).reshape(-1)
        y = np.linalg.solve(np.eye(Nt * nid) + G @ C, y0v)
        f = -(C @ y).reshape(Nt, nid)
        Pxf, Pyf = PX / tw, PY / th
        for a, i in enumerate(ids):
            q_corr = np.einsum("mr,nr->mn", Pxf * f[:, a], Pyf) * (ex[:, None] * ey[None, :]) / (W * H)
            a_mn += np.einsum("mnl,mn->mnl", Ainv[:, :, :, i], q_corr)
    nx = max(int(round(W * 1000.0 / cell_mm)), 2)
    ny = max(int(round(H * 1000.0 / cell_mm)), 2)
    xs, ys = (np.arange(nx) + 0.5) * (W / nx), (np.arange(ny) + 0.5) * (H / ny)
    cx = np.cos(np.outer(xs, np.arange(M) * np.pi / W))
    cy = np.cos(np.outer(ys, np.arange(N) * np.pi / H))
    T = np.stack([cy @ a_mn[:, :, i].T @ cx.T for i in range(n_nodes)])
    return {"T": T, "max": float(T[0].max()), "tiles": Nt, "nodes": n_nodes}


def tile_for(problem, per_source=6.0, cap_mm=1.0):
    """!
    @brief The tile size the candidate needs: the smallest heater side divided by `per_source`, at most `cap_mm`.
    @details Measured in README 5.4: a heater three tiles across overshoots by 13 to 18 % (four laminate nodes), six tiles across is within about one point of twelve.
    @param problem A Problem.
    @param per_source Tiles across the smallest heater side.
    @param cap_mm Largest tile in mm.
    @return Tile size in mm.
    """
    sides = []
    for h in problem.heaters:
        xs, ys = h.polygon[:, 0], h.polygon[:, 1]
        sides.append(min(xs.max() - xs.min(), ys.max() - ys.min()) * 1e3)
    return float(min(cap_mm, min(sides) / per_source))
