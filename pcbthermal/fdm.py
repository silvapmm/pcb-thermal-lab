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

         This is not the removed wxPython solver: that one also had modelling errors (see docs/validation.md, section 6). It exists to
         answer "what would a correct FDM give?" and is not meant for design work: use the FVM.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from .geometry import coverage_fraction, points_in_polygon, polygon_centroid
from . import fvm
from .fvm import ORDERING
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


def _node_average(cell_values):
    """!
    @brief Average of the cell values around every node (each node sees up to four cells).
    @param cell_values Array (ny, nx) of cell values.
    @return Array (ny + 1, nx + 1): the mean over the cells that touch each node, weighted by the shared area.
    """
    ny, nx = cell_values.shape
    acc = np.zeros((ny + 1, nx + 1))
    cnt = np.zeros((ny + 1, nx + 1))
    for di in (0, 1):
        for dj in (0, 1):
            acc[di:di + ny, dj:dj + nx] += cell_values
            cnt[di:di + ny, dj:dj + nx] += 1.0
    return acc / cnt


class Network:
    """!
    @brief The finite-difference network: conductances, capacities, sources and the sparse matrix, on the nodes of the grid.
    @details Offers the same attributes as fvm.Network (nl, ny, nx, K, C, Q, Qw_matrix, footprints, g_amb, solve_steady), with ny and nx
             the number of nodes, so the transient and the power-profile machinery of the FVM runs on it unchanged.
    """

    def __init__(self, problem, cell_mm=2.0, mean="arithmetic", sampling="area"):
        """!
        @param problem A Problem.
        @param cell_mm Target grid spacing in millimetres (the board is divided into round(width / spacing) intervals).
        @param mean "arithmetic" (classic) or "harmonic" mean of the nodal conductivities on a face.
        @param sampling "area" (covered fraction of the control volume around each node, removes most of the grid-to-grid scatter)
               or "point" (the classic test of whether the node lies inside a polygon).
        @throws ValueError If the sampling is unknown.
        """
        problem.validate()
        if sampling not in ("area", "point"):
            raise ValueError("sampling must be 'area' or 'point'")
        self.problem = problem
        b, m = problem.board, problem.board.materials
        L, W, H = b.layers, b.width, b.height
        cells_x = max(int(round(W * 1000.0 / cell_mm)), 2)
        cells_y = max(int(round(H * 1000.0 / cell_mm)), 2)
        dx, dy = W / cells_x, H / cells_y
        nx, ny = cells_x + 1, cells_y + 1                                    # Nodes
        self.nl, self.nx, self.ny, self.dx, self.dy = L, nx, ny, dx, dy
        X, Y = np.meshgrid(np.arange(nx) * dx, np.arange(ny) * dy)           # (ny, nx)
        # Control-volume size of every node: half a cell on the edges
        wx = np.full(nx, dx); wx[[0, -1]] = 0.5 * dx
        wy = np.full(ny, dy); wy[[0, -1]] = 0.5 * dy
        area = np.outer(wy, wx)                                              # m2
        self.area = area
        slab = b.thickness / L
        tc = np.asarray(b.copper_thickness)[:, None, None]

        def cover(poly, samples):
            return _node_average(coverage_fraction(poly, cells_x, cells_y, dx, dy, samples)) if sampling == "area" \
                else _inside(poly, X, Y).astype(float)

        # Copper fill at the nodes
        fill = np.zeros((L, ny, nx))
        for z in problem.zones:
            fill[z.layer] = np.maximum(fill[z.layer], cover(z.polygon, 4) * z.fill)
        S = fill * m.k_copper * tc + m.k_fr4_inplane * (slab - fill * tc)    # Sheet conductance per node (W/K)
        # Heat capacity of every node (J/K)
        self.C = (fill * m.rho_copper * m.cp_copper * tc + (slab - fill * tc) * m.rho_fr4 * m.cp_fr4) * area[None]

        n = L * ny * nx
        idx = np.arange(n).reshape(L, ny, nx)
        rows, cols, vals = [], [], []

        def couple(a_idx, b_idx, g):
            a_idx, b_idx, g = a_idx.ravel(), b_idx.ravel(), g.ravel()
            keep = g > 0
            a_idx, b_idx, g = a_idx[keep], b_idx[keep], g[keep]
            rows.extend([a_idx, b_idx, a_idx, b_idx])
            cols.extend([a_idx, b_idx, b_idx, a_idx])
            vals.extend([g, g, -g, -g])

        # Lateral: face conductivity (mean of the two nodes) times the width of the face over the distance
        couple(idx[:, :, :-1], idx[:, :, 1:], _mean(S[:, :, :-1], S[:, :, 1:], mean) * wy[None, :, None] / dx)
        couple(idx[:, :-1, :], idx[:, 1:, :], _mean(S[:, :-1, :], S[:, 1:, :], mean) * wx[None, None, :] / dy)
        # Vertical: dielectric over the control area, plus the via barrels at the nearest node
        if L > 1:
            d = b.dielectric_thickness()
            gz = np.broadcast_to(m.k_fr4_through * area / d, (L - 1, ny, nx)).copy()
            for v in problem.vias:
                # A via is a point: all its conductance goes to the node nearest to it (spreading it over the neighbours was
                # tried and removes the constriction, giving temperatures 2 % too low against the 3D solid)
                j = min(max(int(round(v.x / dx)), 0), nx - 1)
                i = min(max(int(round(v.y / dy)), 0), ny - 1)
                gz[:, i, j] += m.k_copper * v.copper_area(b.via_plating) / d
            couple(idx[:-1], idx[1:], gz)
        # Ambient: faces, sinks and edges
        self.g_top = np.zeros((L, ny, nx)); self.g_bottom = np.zeros_like(self.g_top)
        self.g_sink = np.zeros_like(self.g_top); self.g_side = np.zeros_like(self.g_top)
        self.g_top[0] = b.h_top * area
        self.g_bottom[L - 1] = b.h_bottom * area
        for sk in problem.sinks:
            self.g_sink[sk.layer] += sk.h_extra * area * cover(sk.polygon, 4)
        if b.h_side:
            self.g_side[:, :, 0] += b.h_side * wy[None, :] * slab
            self.g_side[:, :, -1] += b.h_side * wy[None, :] * slab
            self.g_side[:, 0, :] += b.h_side * wx[None, :] * slab
            self.g_side[:, -1, :] += b.h_side * wx[None, :] * slab
        self.g_amb = self.g_top + self.g_bottom + self.g_sink + self.g_side
        rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(self.g_amb.ravel())
        self.K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()

        # Sources: unit-power weights of every heater (they sum to 1), so the power is exact on any grid
        self.Qw, self.Q = [], np.zeros((L, ny, nx))
        for h in problem.heaters:
            if sampling == "area":
                # Each cell's covered area is shared by its four nodes
                w = np.zeros((ny, nx))
                cov = coverage_fraction(h.polygon, cells_x, cells_y, dx, dy, 8)
                for di in (0, 1):
                    for dj in (0, 1):
                        w[di:di + cells_y, dj:dj + cells_x] += cov
            else:
                w = _inside(h.polygon, X, Y).astype(float)
            if not (w > 0).any():                       # Footprint smaller than the grid: the node nearest to the centroid
                cx, cy = polygon_centroid(h.polygon)
                w = np.zeros((ny, nx))
                w[min(max(int(round(cy / dy)), 0), ny - 1), min(max(int(round(cx / dx)), 0), nx - 1)] = 1.0
            full = np.zeros((L, ny, nx))
            full[h.layer] = w / w.sum()
            self.Qw.append(full)
            self.Q += h.power * full
        self.Qw_matrix = sp.csc_matrix(np.stack([w.ravel() for w in self.Qw], axis=1)) if self.Qw else sp.csc_matrix((n, 0))
        self.footprints = [np.flatnonzero(w.ravel() > 0) for w in self.Qw]

    def solve_steady(self, method="direct"):
        """!
        @brief Solve K theta = Q.
        @param method Only "direct" (sparse LU); the argument keeps the interface of fvm.Network.
        @return Tuple (theta of shape (layers, ny, nx) in kelvin above ambient, relative residual).
        """
        q = self.Q.ravel()
        theta = spla.spsolve(self.K, q, permc_spec=ORDERING)
        res = float(np.linalg.norm(self.K @ theta - q) / max(np.linalg.norm(q), 1e-300))
        return theta.reshape(self.nl, self.ny, self.nx), res


def solve_steady(problem, cell_mm=2.0, mean="arithmetic", sampling="area"):
    """!
    @brief Steady-state finite-difference solution of a problem.
    @param problem A Problem.
    @param cell_mm Target grid spacing in millimetres (nx = round(width / spacing) intervals).
    @param mean "arithmetic" (classic) or "harmonic" mean of the nodal conductivities on a face.
    @param sampling "area" (default) or "point" (see Network).
    @return SteadyResult with the field at the nodes (layers, ny + 1, nx + 1).
    """
    net = Network(problem, cell_mm, mean, sampling)
    b = problem.board
    theta, res = net.solve_steady()
    T = theta + b.ambient
    area, dx, dy = net.area, net.dx, net.dy
    total_area = area.sum()
    l, i, j = np.unravel_index(int(np.argmax(T)), T.shape)
    return SteadyResult(
        model="fdm", ambient=b.ambient, power_in=float(net.Q.sum()), t_max=float(T.max()), t_min=float(T.min()),
        t_mean=float((T * area[None]).sum() / (net.nl * total_area)),
        layer_mean=[float((T[q] * area).sum() / total_area) for q in range(net.nl)],
        t_max_location=(int(l), j * dx, i * dy), T=T, dx=dx, dy=dy,
        power_out={"top": float((net.g_top * theta).sum()), "bottom": float((net.g_bottom * theta).sum()),
                   "sinks": float((net.g_sink * theta).sum()), "sides": float((net.g_side * theta).sum())},
        grid="nodes", residual=res, extras={"nodes": float(T.size), "harmonic": float(mean == "harmonic"),
                                            "area_sampling": float(sampling == "area")},
        warnings=[])


def solve_transient(problem, t_end, n_out=40, cell_mm=2.0, substeps=4, theta_scheme=1.0, log_times=True):
    """!
    @brief Power-step transient of the finite-difference model, from a board at ambient temperature.
    @details The same theta-method as fvm.solve_transient on the finite-difference network; the frames hold the values at the nodes.
    @param problem A Problem.
    @param t_end Final time in seconds.
    @param n_out Number of output frames after t = 0.
    @param cell_mm Target grid spacing in millimetres.
    @param substeps Implicit steps between two frames (linear mode only).
    @param theta_scheme 1.0 for implicit Euler, 0.5 for Crank-Nicolson.
    @param log_times True for the doubling time step.
    @return TransientResult with grid "nodes".
    """
    return fvm.transient_from_network(Network(problem, cell_mm), problem.board.ambient, t_end, n_out, substeps, theta_scheme,
                                      log_times, grid="nodes")


def step_responses(problem, cell_mm=2.0, **kwargs):
    """!
    @brief Unit-step response of every heater's hottest node (see fvm.step_responses).
    @param problem A Problem with at least one heater.
    @param cell_mm Target grid spacing in millimetres.
    @param kwargs Further arguments of fvm.step_responses_from_network (t_end, ratio, per_stage, stages, theta_scheme).
    @return Tuple (times, z, rth).
    @throws ValueError If the problem has no heater.
    """
    if not problem.heaters:
        raise ValueError("the problem has no heater")
    return fvm.step_responses_from_network(Network(problem, cell_mm), **kwargs)
