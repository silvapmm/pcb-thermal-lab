#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file analytic_edge.py
@brief A copy of the steady Analytic solve (pcbthermal/analytic.py, no metal block) with three ways of treating a convective board edge: faces, Robin basis, strips.

@details The program moves the edge loss to the faces (edge "faces": h_edge,l added to the surface coefficient, insulated cosine basis). This module repeats the
         steady solution on top of the program's own `analytic._effective_sheet` (copper fill, sheet conductances, tiles, via plan) and changes only the edge:

         - "faces": the program's treatment; reproduces `analytic.solve_steady` (checked by tests/test_analytic_edge.py).
         - "none": the edge left out (what the program did before the transfer).
         - "robin": the cosine basis is replaced by the eigenfunctions of the convective edge (robin_basis.py), so the edge loss is where the edge is. The edge
           parameter is common to all the layers, beta = h_side P_edge/(2(W+H)) sum(slab) / sum(S) (1/m): exact when every layer has the same ratio s_l / S_l (a stack
           with the same copper in every layer), approximate otherwise (measured in the README).
         - "robin_res": "robin" plus, for each layer, the part of its edge conductance that the common beta does not carry, moved to the faces (the residuals sum to zero).
         - "strips": the cosine basis, no transfer, and the edge cells as local conductances to the ambient in the Green-function correction (tiles of `strip_mm` along the
           outline, one tile deep; the prototype of the reviewer), for boards without vias or heatsinks.

         The local corrections of vias and heatsinks use the same tile system as the program, with the basis functions of the chosen edge. No metal block, steady state only.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from pcbthermal import analytic, laminate, viaconstriction   # noqa: E402
from pcbthermal.geometry import coverage_fraction, polygon_area   # noqa: E402
from robin_basis import Basis   # noqa: E402


def edge_beta(sh, problem):
    """!
    @brief The common edge parameter of the Robin basis.
    @param sh Dict from analytic._effective_sheet.
    @param problem The Problem.
    @return Tuple (beta in 1/m, h_side effective W/m2K on the rectangle).
    """
    b = problem.board
    if not b.h_side:
        return 0.0, 0.0
    perim = getattr(b, "edge_perimeter", None) or 2.0 * (sh["W"] + sh["H"])
    h_eff = b.h_side * perim / (2.0 * (sh["W"] + sh["H"]))          # keeps the total edge conductance of a board with an outline
    return h_eff * float(sh["slab"].sum()) / float(sh["S"].sum()), h_eff


def modal_matrix(sh, h_surf, g, eig2):
    """!
    @brief The (M, N, L, L) tridiagonal modal matrices with a given eigenvalue array.
    @param sh Sheet dict.
    @param h_surf Surface coefficient per layer (L,).
    @param g Gap conductance per area (L-1,).
    @param eig2 Eigenvalue sum lam_x^2 + lam_y^2, shape (M, N).
    @return Array (M, N, L, L).
    """
    L, S = sh["L"], sh["S"]
    A = np.zeros(eig2.shape + (L, L))
    for l in range(L):
        A[:, :, l, l] = S[l] * eig2 + h_surf[l]
        if l > 0:
            A[:, :, l, l] += g[l - 1]
            A[:, :, l, l - 1] -= g[l - 1]
        if l < L - 1:
            A[:, :, l, l] += g[l]
            A[:, :, l, l + 1] -= g[l]
    return A


def solve(problem, cell_mm=1.0, n_terms=300, edge="faces", n_green=64, strip_mm=1.0, local=True):
    """!
    @brief Steady Analytic solution with the chosen edge treatment.
    @param problem A Problem (no metal block).
    @param cell_mm Sampling cell in mm.
    @param n_terms Modes per direction.
    @param edge "faces", "none", "robin", "robin_res" (Robin with the layer mismatch of the edge parameter moved to the faces) or "strips".
    @param n_green Modes per direction of the tile Green function (vias, heatsinks); "strips" uses at least this many.
    @param strip_mm Tile size along the outline for "strips".
    @param local Apply the local corrections of vias and heatsinks.
    @return Dict with T (L, ny, nx rise over ambient + ambient), t_max, a (M, N, L), bx, by, sh, p_faces, p_edge, p_heatsinks, beta.
    """
    problem = problem.drop_off_board_vias()
    problem = laminate.series_bottom_problem(problem)
    sh = analytic._effective_sheet(problem, cell_mm)
    b, m, W, H, L = sh["b"], sh["m"], sh["W"], sh["H"], sh["L"]
    S, lam, d_diel, g_diel = sh["S"], sh["lam"], sh["d_diel"], sh["g_diel"]
    xs, ys, nx, ny = sh["xs"], sh["ys"], sh["nx"], sh["ny"]
    M = N = n_terms
    h_surf = np.zeros(L)
    h_surf[0] += b.h_top
    h_surf[L - 1] += b.h_bottom
    robin = edge in ("robin", "robin_res")
    beta, h_eff = (edge_beta(sh, problem) if robin else (0.0, 0.0))
    res = np.zeros(L)
    if edge == "faces":
        h_surf = h_surf + sh["h_edge"]
    elif edge == "robin_res" and h_eff:
        # the basis carries beta_c S_l per metre of edge in layer l; the rest of h_eff slab_l (it sums to zero over the layers) goes to the faces
        res = (h_eff * sh["slab"] - beta * S) * 2.0 * (W + H) / (W * H)
        h_surf = h_surf + res
    bx, by = Basis(W, beta, M), Basis(H, beta, N)
    g = g_diel.copy()

    # --- modal sources
    q_mn = np.zeros((M, N, L))
    for ht in problem.heaters:
        x1, x2, y1, y2 = analytic._equivalent_rectangle(ht.polygon, W, H)
        q0 = ht.power / ((x2 - x1) * (y2 - y1))
        q_mn[:, :, ht.layer] += q0 * np.outer(bx.project(x1, x2) / bx.norm, by.project(y1, y2) / by.norm)
    eig2 = bx.eig2[:, None] + by.eig2[None, :]
    A = modal_matrix(sh, h_surf, g, eig2)
    Ainv = np.linalg.inv(A)
    a_mn = np.einsum("mnlk,mnk->mnl", Ainv, q_mn)

    heatsink_extraction = 0.0
    strip_loss = 0.0
    nvs = problem.vias or problem.heatsinks
    rects, C, selfterm = None, None, None
    if edge == "strips" and b.h_side:
        ntx, nty = max(int(round(W * 1000.0 / strip_mm)), 1), max(int(round(H * 1000.0 / strip_mm)), 1)
        tw, th = W / ntx, H / nty
        perim = getattr(b, "edge_perimeter", None) or 2.0 * (W + H)
        hs = b.h_side * perim / (2.0 * (W + H))
        active = [(r, c) for r in range(nty) for c in range(ntx) if r in (0, nty - 1) or c in (0, ntx - 1)]
        Nt = len(active)
        rects = [(c * tw, (c + 1) * tw, r * th, (r + 1) * th) for r, c in active]
        C = np.zeros((Nt * L, Nt * L))
        for i, (r, c) in enumerate(active):
            length = (th if c == 0 else 0.0) + (th if c == ntx - 1 else 0.0) + (tw if r == 0 else 0.0) + (tw if r == nty - 1 else 0.0)
            for l in range(L):
                C[i * L + l, i * L + l] += hs * sh["slab"][l] * length
        mg_modes = max(n_green, 150)
        Mg, Ng = min(M, mg_modes), min(N, mg_modes)
    elif local and nvs and edge != "strips":
        ntx, nty, tw, th = analytic._tile_grid(W, H, lam)
        vs = viaconstriction.ViaSet(problem) if problem.vias and L > 1 else None
        if vs is not None:
            plan = viaconstriction.plan(problem, vs, (ntx, nty, tw, th), L)
            (ntx, nty, tw, th), via_weights = plan["grid"], plan["weights"]
        c_via = np.zeros((nty, ntx, max(L - 1, 0)))
        for iv, v in enumerate(problem.vias if vs is not None else []):
            cond = m.k_copper * v.thermal_area(b.via_plating, m.k_copper) / d_diel
            for (row, col), w in via_weights[iv].items():
                c_via[row, col] += w * cond
        g_hs = np.zeros((L, nty, ntx))
        for s in problem.heatsinks:
            g_hs[s.layer] += s.h_extra * tw * th * coverage_fraction(s.polygon, ntx, nty, tw, th, 8)
        active = np.argwhere((c_via.sum(axis=2) > 0) | (g_hs.sum(axis=0) > 0))
        Nt = len(active)
        if Nt:
            rects = [(c * tw, (c + 1) * tw, r * th, (r + 1) * th) for r, c in active]
            C = np.zeros((Nt * L, Nt * L))
            for r, (row, col) in enumerate(active):
                for l in range(L - 1):
                    cv = c_via[row, col, l]
                    i1, i2 = r * L + l, r * L + l + 1
                    C[i1, i1] += cv
                    C[i2, i2] += cv
                    C[i1, i2] -= cv
                    C[i2, i1] -= cv
                for l in range(L):
                    C[r * L + l, r * L + l] += g_hs[l, row, col]
            if vs is not None:
                selfterm = (active, via_weights, vs, tw, th)
            Mg, Ng = min(M, n_green), min(N, n_green)
    if rects is not None:
        Nt = len(rects)
        PX = np.stack([bx.project(r[0], r[1]) for r in rects], axis=1)           # (M, Nt)
        PY = np.stack([by.project(r[2], r[3]) for r in rects], axis=1)
        areas_x = np.array([r[1] - r[0] for r in rects])
        areas_y = np.array([r[3] - r[2] for r in rects])
        Ux, Uy = PX / areas_x, PY / areas_y
        y0 = np.stack([np.einsum("mr,mn,nr->r", Ux, a_mn[:, :, l], Uy) for l in range(L)], axis=1)
        Gm = np.zeros((Nt, L, Nt, L))
        for l in range(L):
            for k in range(L):
                Wm = Ainv[:Mg, :Ng, l, k] / (bx.norm[:Mg, None] * by.norm[None, :Ng])
                acc = np.zeros((Nt, Nt))
                for n in range(Ng):
                    acc += ((Ux[:Mg].T * Wm[:, n]) @ Ux[:Mg]) * np.outer(Uy[n], Uy[n])
                Gm[:, l, :, k] = acc
        G = Gm.reshape(Nt * L, Nt * L)
        if selfterm is not None:
            G = viaconstriction.add_self_terms(G, selfterm[0], selfterm[1], selfterm[2], selfterm[3], selfterm[4], S)
        lhs = G @ C
        lhs[np.diag_indices_from(lhs)] += 1.0
        yv = np.linalg.solve(lhs, y0.reshape(-1))
        f = -(C @ yv).reshape(Nt, L)
        if edge == "strips":
            strip_loss = float((C @ yv).sum())          # C is diagonal here: the heat of each edge cell is g * y
        else:
            heatsink_extraction = float(sum(g_hs[l, row, col] * yv[r * L + l] for r, (row, col) in enumerate(active) for l in range(L)))
        for k in range(L):
            q_corr = np.einsum("mr,nr->mn", (PX / areas_x) * f[:, k], PY / areas_y) / (bx.norm[:, None] * by.norm[None, :])
            a_mn = a_mn + np.einsum("mnl,mn->mnl", Ainv[:, :, :, k], q_corr)

    ex_, ey_ = bx.evaluate(xs), by.evaluate(ys)
    theta = np.stack([ey_ @ a_mn[:, :, l].T @ ex_.T for l in range(L)])
    T = theta + b.ambient

    # --- heat out of the board
    ix, iy = bx.project(0.0, W), by.project(0.0, H)
    mean_rise = np.array([ix @ a_mn[:, :, l] @ iy for l in range(L)])              # integral of theta over the plan (K m2)
    p_faces = b.h_top * mean_rise[0] + b.h_bottom * mean_rise[L - 1]
    p_edge = 0.0
    if edge == "faces":
        p_edge = float(sum(sh["h_edge"][l] * mean_rise[l] for l in range(L)))
    elif robin and h_eff:
        e_x, e_y = bx.evaluate([0.0, W]), by.evaluate([0.0, H])
        for l in range(L):
            a = a_mn[:, :, l]
            along_y = (e_x @ a) @ iy                                                # theta at x=0 and x=W integrated over y
            along_x = (e_y @ a.T) @ ix
            p_edge += beta * float(S[l]) * float(along_y.sum() + along_x.sum()) + float(res[l] * mean_rise[l])
    elif edge == "strips":
        p_edge = strip_loss
    p_hs = heatsink_extraction
    if not local and problem.heatsinks:
        p_hs = 0.0
    return {"T": T, "t_max": float(T.max()), "a": a_mn, "bx": bx, "by": by, "sh": sh, "beta": beta, "p_faces": float(p_faces), "p_edge": float(p_edge),
            "p_heatsinks": p_hs, "power": sh["power"], "mean_rise": mean_rise}


def step_response(problem, edge="faces", n_terms=300, cell_mm=1.0, times=None):
    """!
    @brief Unit-step response (rise at the hottest point of the first heater per watt) of the uniform board with the chosen edge treatment.
    @details The same modal system as analytic._modal_dynamics (C a' + A a = q, exact propagator), with the basis of the edge. Vias and heatsinks are smeared with scale 1
             (the program's calibration of the scale is not repeated: boards used here have none).
    @param problem A Problem (uniform, no local elements).
    @param edge "faces", "none" or "robin".
    @param n_terms Modes per direction.
    @param cell_mm Sampling cell in mm.
    @param times Times in s (default 160 log-spaced values around the time constant).
    @return Tuple (times, z in K/W, rth in K/W, tau_63 in s).
    """
    problem = problem.drop_off_board_vias()
    problem = laminate.series_bottom_problem(problem)
    sh = analytic._effective_sheet(problem, cell_mm)
    b, m, W, H, L = sh["b"], sh["m"], sh["W"], sh["H"], sh["L"]
    M = N = n_terms
    h_surf = np.zeros(L)
    h_surf[0] += b.h_top
    h_surf[L - 1] += b.h_bottom
    beta = 0.0
    if edge == "robin":
        beta, _ = edge_beta(sh, problem)
    elif edge == "faces":
        h_surf = h_surf + sh["h_edge"]
    bx, by = Basis(W, beta, M), Basis(H, beta, N)
    A = modal_matrix(sh, h_surf, sh["g_diel"], bx.eig2[:, None] + by.eig2[None, :])
    fill, tc, slab = sh["fill"], sh["tc"], sh["slab"]
    c_l = fill * m.rho_copper * m.cp_copper * tc + (slab - fill * tc) * sh["rho_cp_lam"]
    cinv = 1.0 / np.sqrt(c_l)
    mu, V = np.linalg.eigh(A * cinv[None, None, :, None] * cinv[None, None, None, :])
    back = cinv[None, None, :, None] * V
    ht = problem.heaters[0]
    x1, x2, y1, y2 = analytic._equivalent_rectangle(ht.polygon, W, H)
    q = np.zeros((M, N, L))
    q[:, :, ht.layer] = np.outer(bx.project(x1, x2) / bx.norm, by.project(y1, y2) / by.norm) / ((x2 - x1) * (y2 - y1))
    G = np.einsum("mnlk,mnl->mnk", back, q)                         # source in the eigen coordinates
    ex_, ey_ = bx.evaluate(sh["xs"]), by.evaluate(sh["ys"])
    a_ss = np.einsum("mnlk,mnk->mnl", back, G / mu)
    fields = np.stack([ey_ @ a_ss[:, :, l].T @ ex_.T for l in range(L)])
    lay, iy, ix = np.unravel_index(int(np.argmax(fields)), fields.shape)
    U = bx.evaluate([sh["xs"][ix]])[0][:, None, None] * by.evaluate([sh["ys"][iy]])[0][None, :, None] * back[:, :, lay, :]
    rth = float((U * G / mu).sum())
    tau = float(c_l.sum() / max(b.h_top + b.h_bottom + sh["h_edge"].sum(), 1e-9))
    if times is None:
        times = tau * np.logspace(-4, 1.5, 160)
    z = np.array([float((U * G * (1.0 - np.exp(-mu * t)) / mu).sum()) for t in times])
    target = (1.0 - np.exp(-1.0)) * rth
    k = int(np.argmax(z >= target))
    f = (target - z[k - 1]) / (z[k] - z[k - 1])
    t63 = float(np.exp(np.log(times[k - 1]) + f * (np.log(times[k]) - np.log(times[k - 1]))))
    return times, z, rth, t63
