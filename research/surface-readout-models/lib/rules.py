#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file rules.py
@brief The surface read-out rules of this study, written on a copy (the program is not edited): the face fluxes from a layer-temperature field and the uniform conductances of the Analytic (for the Analytic and the Lumped), the same rule from the links of the 3D solid, and the frame rule of the transient.
@details Rule F ("field"): a model that has a temperature per layer and per cell but no per-cell face flux (the Lumped, the Analytic) gets the fluxes of the outer layer from that field and from the UNIFORM conductances
         that the Analytic itself uses (analytic._effective_sheet: the film of each outer face in series with the half copper, h_top_eff and h_bottom_eff, and the laminate conductance per gap g_diel):
             top face of layer 1:      q_top = q_src - h_top_eff theta_1,    q_bot = -g_diel[0] (theta_1 - theta_2)      (a one-layer board: q_bot = -h_bottom_eff theta_1)
             bottom face of layer L:   q_top = g_diel[L-2] (theta_{L-1} - theta_L),    q_bot = q_src - h_bottom_eff theta_L
         and the parabola of pcbthermal/thickness.py (offsets). q_src is the power density of the parts on that face (power over footprint area, the footprint cells of the layer's grid). No via, block or heatsink
         conductance is in these fluxes (a via carries heat the uniform g_diel does not see); the bound q_src t / (2 k) never reads a flux but the source and is the "upper bound" of the offset.
         Rule S ("solid links"): the 3D solid has every conductance, so the same parabola is fed with its own links, the heat that leaves the copper slab downwards and through the films.
         Rule T ("frame"): a transient frame of the FVM carries the node temperatures of every layer; the same fluxes are read from its conductance matrix K (thickness._couplings_out), the frame's
         temperature and the source, so the parabola is identical to the steady one (storage and lateral flow enter only through the node temperatures).
"""

import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from pcbthermal import analytic, laminate, thickness  # noqa: E402
from pcbthermal.geometry import coverage_fraction, polygon_area  # noqa: E402


def source_flux(problem, ny, nx, dx, dy):
    """!
    @brief Power density of the parts on every layer, spread over the cells of their footprint.
    @param problem The Problem.
    @param ny Cells along y.
    @param nx Cells along x.
    @param dx Cell width in m.
    @param dy Cell height in m.
    @return Array (layers, ny, nx) in W/m2 (the part's power over its footprint area, on the cells it covers).
    """
    L = problem.board.layers
    q = np.zeros((L, ny, nx))
    for h in problem.heaters:
        cov = coverage_fraction(h.polygon, nx, ny, dx, dy, 4)
        area = polygon_area(h.polygon)
        if area > 0 and h.power > 0:
            q[h.layer] += h.power / area * (cov > 0)
    return q


def field_rule(problem, T, cell_mm=1.0):
    """!
    @brief Rule F: the surface of the two outer faces from a layer-temperature field, the uniform conductances of the Analytic and the parabola.
    @param problem The Problem.
    @param T Temperature of every layer, shape (layers, ny, nx), degC (the column read-out of the model).
    @param cell_mm Cell size of the sheet (only the fill average of the sheet uses it).
    @return dict with top, bottom (surface maps in degC, shape (ny, nx)), d_top, d_bottom (surface minus column in K), bound_top, bound_bottom (q_src t / 2k in K, zero where no part) and q_src (layers, ny, nx).
    """
    prob = laminate.series_bottom_problem(problem)
    sh = analytic._effective_sheet(prob, cell_mm)
    b = problem.board
    L = b.layers
    ny, nx = T.shape[1:]
    dx, dy = b.width / nx, b.height / ny
    th = np.asarray(T) - b.ambient
    q = source_flux(problem, ny, nx, dx, dy)
    t = np.asarray(b.copper_thickness)
    k = b.materials.k_copper
    g = np.asarray(sh["g_diel"], dtype=float)
    ht, hb = sh["h_top_eff"], sh["h_bottom_eff"]
    if L == 1:
        qt0, qb0 = q[0] - ht * th[0], -hb * th[0]
        d_top, _ = thickness.offsets(t[0], k, qt0, qb0)
        _, d_bot = thickness.offsets(t[0], k, qt0, qb0)
        top, bottom, lt, lb = d_top, d_bot, 0, 0
    else:
        qt0, qb0 = q[0] - ht * th[0], -g[0] * (th[0] - th[1])
        d_top, _ = thickness.offsets(t[0], k, qt0, qb0)
        qtL, qbL = g[L - 2] * (th[L - 2] - th[L - 1]), q[L - 1] - hb * th[L - 1]
        _, d_bot = thickness.offsets(t[L - 1], k, qtL, qbL)
        lt, lb = 0, L - 1
    return {"top": th[lt] + b.ambient + d_top, "bottom": th[lb] + b.ambient + d_bot, "d_top": d_top, "d_bottom": d_bot,
            "bound_top": q[0] * t[0] / (2.0 * k), "bound_bottom": q[L - 1] * t[L - 1] / (2.0 * k), "q_src": q}


def solid_rule(net, theta_all, n_cu=1):
    """!
    @brief Rule S on a 3D solid network (the program's, n_cu = 1, or the patched one of research/through-thickness-readout/lib/solid3d_sublayers.py with n_cu slabs through the copper of layer 1).
    @details n_cu = 1: the column mean of the copper slab is taken as its node, the fluxes are the source and the film above (g_top) and everything that leaves the slab through the z links below, and the parabola
             of thickness.offsets gives the face. n_cu > 1: the copper is resolved, the face is the first slab plus the half slab that the injection at the node skips, `q_top dz / (2 k)` (option B of
             research/through-thickness-readout 1), and the column mean is the mean of the sub-slabs.
    @param net A Solid (or the patched one) after solve.
    @param theta_all Rise of every slab, shape (slabs, ny, nx), in K.
    @param n_cu Slabs through the copper of layer 1.
    @return dict with col (column mean map of layer 1, degC), top (surface map, degC), d_top (surface minus column in K), mask (cells of the parts of layer 1).
    """
    b = net.problem.board
    ny, nx = net.ny, net.nx
    n = ny * nx
    s0 = net.board_slab[0]
    k = b.materials.k_copper
    t = float(b.copper_thickness[0])
    area = net.area_b
    q_src = net.Q.reshape(net.ns, ny, nx)[s0] / area
    g_top = net.g["top"].reshape(net.ns, ny, nx)[s0] + net.g["heatsinks"].reshape(net.ns, ny, nx)[s0]
    th0 = theta_all[s0]
    col = theta_all[s0:s0 + n_cu].mean(axis=0)
    mask = q_src > 0
    if n_cu > 1:
        top = th0 + q_src * (t / n_cu) / (2.0 * k)
        return {"col": col + b.ambient, "top": top + b.ambient, "d_top": top - col, "mask": mask}
    # n_cu = 1: heat that leaves the slab downwards = the couplings of slab s0 to slab s0 + 1
    sub = net.K.tocsr()[s0 * n:(s0 + 1) * n].tocoo()
    cl = sub.col // n
    sel = cl == s0 + 1
    g = -sub.data[sel]
    q_down = np.bincount(sub.row[sel], weights=g * (th0.ravel()[sub.row[sel]] - theta_all.reshape(net.ns, n)[s0 + 1][sub.col[sel] - (s0 + 1) * n]), minlength=n).reshape(ny, nx) / area
    q_t = q_src - g_top * th0 / area
    d_top, _ = thickness.offsets(t, k, q_t, -q_down)
    return {"col": th0 + b.ambient, "top": th0 + b.ambient + d_top, "d_top": d_top, "mask": mask}
