"""!
@file fdm.py
@brief Node-centred finite-difference thermal solver of the same layered model, kept as a comparison model.

@details The classic finite-difference discretisation of the model of fvm.py: the unknowns are the temperatures at the grid
         nodes (nx + 1 by ny + 1 per layer, nodes on the board edges), the material properties are sampled **at the nodes**, the
         conductivity between two nodes is the mean of the two nodal values (arithmetic by default, harmonic on request), a
         heater distributes its power over the nodes inside its footprint, and the edge nodes use half control volumes (the
         standard second-order treatment of a convective boundary with ghost nodes). It solves the same equations with the same
         sheet conductance, dielectric resistance, vias, sinks and convection as the FVM, so the difference between the two is the
         difference of the discretisation: point sampling of the copper and of the sources instead of cell averages, and the
         way the interface between copper and FR-4 is treated.

         This is not the removed wxPython solver: that one also had modelling errors (see docs/new_approach.md). It exists to
         answer "what would a correct FDM give?" and is not meant for design work: use the FVM.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from .geometry import points_in_polygon, polygon_centroid
from .results import SteadyResult


def _mean(a, b, kind):
    """!
    @brief Mean of the nodal conductivities on the two sides of a face.
    @param a Array of the first node values.
    @param b Array of the second node values.
    @param kind "arithmetic" or "harmonic".
    @return Array with the face value (harmonic mean is zero where both are zero).
    """
    if kind == "arithmetic":
        return 0.5 * (a + b)
    s = a + b
    out = np.zeros_like(s)
    np.divide(2.0 * a * b, s, out=out, where=s > 0)
    return out


def _inside(poly, X, Y):
    """!
    @brief Nodes inside a polygon, with the rule "left and bottom edge in, right and top edge out".
    @details For an axis-aligned rectangle on the grid this gives exactly the area of the rectangle in nodes (no double count of
             the border); for other polygons it is the usual point-in-polygon test.
    @param poly Polygon vertices (n, 2) in metres.
    @param X Array of node x coordinates.
    @param Y Array of node y coordinates.
    @return Boolean array like X.
    """
    xs, ys = poly[:, 0], poly[:, 1]
    rect = len(poly) == 4 and np.allclose(sorted(set(np.round(xs, 12))), [xs.min(), xs.max()]) \
        and np.allclose(sorted(set(np.round(ys, 12))), [ys.min(), ys.max()])
    if rect:
        eps = 1e-9 * max(xs.max(), ys.max())
        return (X >= xs.min() - eps) & (X < xs.max() - eps) & (Y >= ys.min() - eps) & (Y < ys.max() - eps)
    return points_in_polygon(X.ravel(), Y.ravel(), poly).reshape(X.shape)


def solve_steady(problem, cell_mm=2.0, mean="arithmetic"):
    """!
    @brief Steady-state finite-difference solution of a problem.
    @param problem A Problem.
    @param cell_mm Target grid spacing in millimetres (nx = round(width / spacing) intervals).
    @param mean "arithmetic" (classic) or "harmonic" mean of the nodal conductivities on a face.
    @return SteadyResult with the field at the nodes (layers, ny + 1, nx + 1).
    """
    problem.validate()
    b, m = problem.board, problem.board.materials
    L, W, H = b.layers, b.width, b.height
    nx = max(int(round(W * 1000.0 / cell_mm)), 2)
    ny = max(int(round(H * 1000.0 / cell_mm)), 2)
    dx, dy = W / nx, H / ny
    X, Y = np.meshgrid(np.arange(nx + 1) * dx, np.arange(ny + 1) * dy)         # (ny + 1, nx + 1)
    # Control-volume size of every node: half a cell on the edges
    wx = np.full(nx + 1, dx); wx[[0, -1]] = 0.5 * dx
    wy = np.full(ny + 1, dy); wy[[0, -1]] = 0.5 * dy
    area = np.outer(wy, wx)                                                   # (ny + 1, nx + 1) in m2
    slab = b.thickness / L
    tc = np.asarray(b.copper_thickness)[:, None, None]

    # Copper fill sampled at the nodes
    fill = np.zeros((L, ny + 1, nx + 1))
    for z in problem.zones:
        fill[z.layer] = np.maximum(fill[z.layer], _inside(z.polygon, X, Y) * z.fill)
    S = fill * m.k_copper * tc + m.k_fr4_inplane * (slab - fill * tc)         # Sheet conductance per node (W/K)

    n = L * (ny + 1) * (nx + 1)
    idx = np.arange(n).reshape(L, ny + 1, nx + 1)
    rows, cols, vals = [], [], []

    def couple(a, bb, g):
        a, bb, g = a.ravel(), bb.ravel(), g.ravel()
        keep = g > 0
        a, bb, g = a[keep], bb[keep], g[keep]
        rows.extend([a, bb, a, bb])
        cols.extend([a, bb, bb, a])
        vals.extend([g, g, -g, -g])

    # Lateral: face conductivity (mean of the two nodes) times the width of the face over the distance
    sx = _mean(S[:, :, :-1], S[:, :, 1:], mean)
    sy = _mean(S[:, :-1, :], S[:, 1:, :], mean)
    couple(idx[:, :, :-1], idx[:, :, 1:], sx * wy[None, :, None] / dx)
    couple(idx[:, :-1, :], idx[:, 1:, :], sy * wx[None, None, :] / dy)
    # Vertical: dielectric over the control area, plus the via barrels at the nearest node
    if L > 1:
        d = b.dielectric_thickness()
        gz = np.broadcast_to(m.k_fr4_through * area / d, (L - 1, ny + 1, nx + 1)).copy()
        for v in problem.vias:
            j = min(max(int(round(v.x / dx)), 0), nx)
            i = min(max(int(round(v.y / dy)), 0), ny)
            gz[:, i, j] += m.k_copper * v.copper_area(b.via_plating) / d
        couple(idx[:-1], idx[1:], gz)
    # Ambient: faces, sinks and edges
    g_amb = np.zeros((L, ny + 1, nx + 1))
    g_top = np.zeros_like(g_amb); g_bottom = np.zeros_like(g_amb); g_sink = np.zeros_like(g_amb); g_side = np.zeros_like(g_amb)
    g_top[0] = b.h_top * area
    g_bottom[L - 1] = b.h_bottom * area
    for s in problem.sinks:
        g_sink[s.layer] += s.h_extra * area * _inside(s.polygon, X, Y)
    if b.h_side:
        g_side[:, :, 0] += b.h_side * wy[None, :] * slab
        g_side[:, :, -1] += b.h_side * wy[None, :] * slab
        g_side[:, 0, :] += b.h_side * wx[None, :] * slab
        g_side[:, -1, :] += b.h_side * wx[None, :] * slab
    g_amb = g_top + g_bottom + g_sink + g_side
    rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(g_amb.ravel())
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()

    # Sources: the power is divided equally among the nodes inside the footprint (the node nearest to the centroid if none)
    Q = np.zeros((L, ny + 1, nx + 1))
    for h in problem.heaters:
        sel = _inside(h.polygon, X, Y)
        if not sel.any():
            cx, cy = polygon_centroid(h.polygon)
            sel = np.zeros_like(sel)
            sel[min(max(int(round(cy / dy)), 0), ny), min(max(int(round(cx / dx)), 0), nx)] = True
        Q[h.layer][sel] += h.power / sel.sum()
    theta = spla.spsolve(K, Q.ravel())
    res = float(np.linalg.norm(K @ theta - Q.ravel()) / max(np.linalg.norm(Q), 1e-300))
    theta = theta.reshape(L, ny + 1, nx + 1)

    T = theta + b.ambient
    total_area = area.sum()
    k = int(np.argmax(T))
    l, i, j = np.unravel_index(k, T.shape)
    return SteadyResult(
        model="fdm", ambient=b.ambient, power_in=float(Q.sum()), t_max=float(T.max()), t_min=float(T.min()),
        t_mean=float((T * area[None]).sum() / (L * total_area)),
        layer_mean=[float((T[q] * area).sum() / total_area) for q in range(L)],
        t_max_location=(int(l), j * dx, i * dy), T=T, dx=dx, dy=dy,
        power_out={"top": float((g_top * theta).sum()), "bottom": float((g_bottom * theta).sum()),
                   "sinks": float((g_sink * theta).sum()), "sides": float((g_side * theta).sum())},
        residual=res, extras={"nodes": float(T.size), "harmonic": float(mean == "harmonic")},
        warnings=["finite-difference comparison model: node sampling of the copper and of the heater footprint; "
                  "use the FVM for design work"])
