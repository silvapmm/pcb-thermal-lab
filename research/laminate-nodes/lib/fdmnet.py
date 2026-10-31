#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fdmnet.py
@brief The construction of lib/rule.py on the program's node-centred FDM: the same laminate nodes in the gaps, with the lateral link of the extra nodes closed at the border of the refined zone.
@details The program's `fdm.Network` keeps neither the sheet conductance S nor the vertical conductances it assembled, so they are recomputed here with the program's own helpers (`zone_fill`,
         `_node_average`, the formulas of fdm.py) and the arrays are handed to `gapnet.apply_ladder`, which changes them as it does for the FVM (the control volume of a node is `net.area`,
         half a cell on the border). The matrix is assembled again (`assemble_fdm`) because the FDM joins two nodes by the **arithmetic mean** of their sheet conductances: for the copper nodes
         that is the program's rule, but for an extra node it would leak half of a refined node's conductance into the neighbouring node that no cell uses (a pinned node, 1 W/K to the
         ambient). The link between two extra nodes is therefore the mean when both are refined and zero otherwise (the FVM's harmonic mean does this by itself). Rectangular boards without
         outline, edge coefficient or metal block (README 8): the first measurement of the FDM with the construction.
@note Written without a run in the preparation phase (py_compile only).
"""

import numpy as np
import scipy.sparse as sp

from pcbthermal import fdm
from pcbthermal.geometry import zone_fill

import gapnet as GN


def build(problem, cell_mm, rule, mean="arithmetic"):
    """!
    @brief The FDM network of the program with the laminate nodes of a rule.
    @param problem A Problem (rectangular board, no h_side, no metal block).
    @param cell_mm Grid spacing in mm (as fdm.Network).
    @param rule A rule.Rule.
    @param mean "arithmetic" or "harmonic" mean of the nodal conductivities of the copper nodes (the program's option).
    @return fdm.Network with the new layers; K assembled by assemble_fdm; attributes ladder and drop as for the FVM.
    @throws NotImplementedError For an outline, an edge coefficient or a metal block.
    """
    b = problem.board
    if b.has_outline() or b.h_side or any(s.is_block() for s in problem.heatsinks):
        raise NotImplementedError("the FDM measurement is for rectangular boards with insulated sides and no block")
    use_one = b.layers == 1 and rule.one_layer
    with GN.rule_off(), (GN.no_program_laminate() if use_one else GN.contextlib.nullcontext()):
        net = fdm.Network(problem, cell_mm, mean)
    L, nx, ny, dx, dy = b.layers, net.nx, net.ny, net.dx, net.dy
    m = b.materials
    cell_fill = zone_fill(problem.zones, L, nx - 1, ny - 1, dx, dy, 4)
    net.fill = np.stack([fdm._node_average(cell_fill[k]) for k in range(L)])
    if b.layers == 1 and not rule.one_layer:
        net.ladder, net.drop = GN.Ladder(rule, [], 1, net.nx * net.ny), np.zeros((net.nl, net.ny, net.nx), dtype=bool)
        return net
    GN._set_sc(net, b, np.asarray(b.slab_thicknesses(), dtype=float), net.fill)
    net.gz = np.zeros((max(L - 1, 0), ny, nx))
    if L > 1:
        d = b.gap_thicknesses()
        net.gz[:] = b.gap_properties()[0][:, None, None] * net.area[None] / d[:, None, None]
        for v in problem.vias:
            j = min(max(int(round(v.x / dx)), 0), nx - 1)
            i = min(max(int(round(v.y / dy)), 0), ny - 1)
            net.gz[:, i, j] += m.k_copper * v.thermal_area(b.via_plating, m.k_copper) / d
    GN.apply_ladder(net, problem, rule, assemble=False)
    net.K = assemble_fdm(net, mean)
    return net


def assemble_fdm(net, mean="arithmetic"):
    """!
    @brief The matrix of an FDM network after the construction (see the module description for the link of the extra nodes).
    @param net Network with S, gz, extra_links, g_amb, area, active, dx, dy, n_board.
    @param mean "arithmetic" or "harmonic" for the copper nodes.
    @return scipy.sparse.csc_matrix.
    """
    Lt, ny, nx = net.nl, net.ny, net.nx
    nb = net.n_board
    n = Lt * ny * nx
    idx = np.arange(n).reshape(Lt, ny, nx)
    wx = np.full(nx, net.dx)
    wx[[0, -1]] = 0.5 * net.dx
    wy = np.full(ny, net.dy)
    wy[[0, -1]] = 0.5 * net.dy
    rows, cols, vals = [], [], []

    def couple(a_idx, b_idx, g):
        a_idx, b_idx, g = a_idx.ravel(), b_idx.ravel(), g.ravel()
        keep = g > 0
        a_idx, b_idx, g = a_idx[keep], b_idx[keep], g[keep]
        rows.extend([a_idx, b_idx, a_idx, b_idx])
        cols.extend([a_idx, b_idx, b_idx, a_idx])
        vals.extend([g, g, -g, -g])

    def face(a, b, is_extra):
        # Copper nodes: the program's mean. Extra nodes: the arithmetic mean where both nodes are used, zero otherwise
        m_ = fdm._mean(a, b, mean)
        ex = 0.5 * (a + b) * ((a > 0) & (b > 0))
        return np.where(is_extra, ex, m_)

    S = net.S
    is_extra = (np.arange(Lt) >= nb)[:, None, None]
    on = net.active
    gx = face(S[:, :, :-1], S[:, :, 1:], is_extra) * wy[None, :, None] / net.dx * (on[:, :-1] & on[:, 1:])[None]
    gy = face(S[:, :-1, :], S[:, 1:, :], is_extra) * wx[None, None, :] / net.dy * (on[:-1, :] & on[1:, :])[None]
    couple(idx[:, :, :-1], idx[:, :, 1:], gx)
    couple(idx[:, :-1, :], idx[:, 1:, :], gy)
    if nb > 1:
        couple(idx[:nb - 1], idx[1:nb], net.gz)
    for a, b, g in net.extra_links:
        couple(idx[a], idx[b], g)
    rows.append(np.arange(n))
    cols.append(np.arange(n))
    vals.append(net.g_amb.ravel())
    return sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()
