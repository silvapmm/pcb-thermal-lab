"""!
@file fdm.py
@brief Node-centred finite-difference thermal solver of the same layered model, kept as a comparison model.

@details The classic finite-difference discretisation of the model of fvm.py: the unknowns are the temperatures at the grid
         nodes (nx + 1 by ny + 1 per layer, nodes on the board edges), the material properties are sampled **at the nodes**, the
         conductivity between two nodes is the mean of the two nodal values (arithmetic by default, harmonic on request), a
         heater distributes its power over the nodes inside its footprint, and the edge nodes use half control volumes (the
         standard second-order treatment of a convective boundary with ghost nodes). It solves the same equations with the same
         sheet conductance, dielectric resistance, vias, heatsinks and convection as the FVM, so the difference between the two is the
         difference of the discretisation: point sampling of the copper and of the sources instead of cell averages, and the
         way the interface between copper and FR-4 is treated.

         This is not the removed wxPython solver: that one also had modelling errors (see docs/validation.md, section 6). It exists to
         answer "what would a correct FDM give?" and is not meant for design work: use the FVM.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from .geometry import coverage_fraction, edge_length_on_board, nearest_active_cell, points_in_polygon, polygon_centroid
from . import blocks, fvm, laminate
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
        slab = b.slab_thicknesses()[:, None, None]                           # Thickness of each layer node (equal in the simple stack-up)
        self.laminate = laminate.nodes(b)                                    # Laminate nodes under the copper of a one-layer board (laminate.py)
        if self.laminate is not None:
            slab = np.full((1, 1, 1), self.laminate.copper_slab)
        k_lam, rho_cp_lam = (v[:, None, None] for v in b.layer_laminate())  # Dielectric part of each node
        tc = np.asarray(b.copper_thickness)[:, None, None]

        def cover(poly, samples):
            return _node_average(coverage_fraction(poly, cells_x, cells_y, dx, dy, samples)) if sampling == "area" \
                else _inside(poly, X, Y).astype(float)

        # Share of every node's control volume that is board (ones for a rectangle); nodes off the board carry nothing
        if b.has_outline():
            ncov = cover(b.outline, 8)
            ncov = np.where(ncov >= 0.01, ncov, 0.0)
        else:
            ncov = np.ones((ny, nx))
        self.active = ncov > 0
        self.cover = ncov
        area = area * ncov                                                   # Board area of every control volume
        self.area = area

        # Copper fill at the nodes
        fill = np.zeros((L, ny, nx))
        for z in problem.zones:
            fill[z.layer] = np.maximum(fill[z.layer], cover(z.polygon, 4) * z.fill)
        S = (fill * m.k_copper * tc + k_lam * (slab - fill * tc)) * ncov     # Sheet conductance per node (W/K)
        # Heat capacity of every node (J/K)
        self.C = (fill * m.rho_copper * m.cp_copper * tc + (slab - fill * tc) * rho_cp_lam) * area[None]
        # Edge length exposed in the control volume of every node (for the edge coefficient of the laminate nodes)
        if b.has_outline():
            edge_nodes = edge_length_on_board(b.outline + np.array([0.5 * dx, 0.5 * dy]), nx, ny, dx, dy, self.active)
        else:
            edge_nodes = np.zeros((ny, nx))
            edge_nodes[:, 0] += wy
            edge_nodes[:, -1] += wy
            edge_nodes[0, :] += wx
            edge_nodes[-1, :] += wx
        lam = laminate.extra_layers(b, self.laminate, area, ncov, edge_nodes, b.h_side) if self.laminate is not None else []
        NL = len(lam)
        self.laminate_layers = list(range(L, L + NL))
        if NL:
            S = np.concatenate([S, np.stack([ly["S"] for ly in lam])])
            self.C = np.concatenate([self.C, np.stack([ly["C"] for ly in lam])])
        # Metal blocks: one extra layer of nodes per face that carries blocks (see blocks.py), after the laminate nodes
        ex = blocks.extra_layers(problem, lambda poly, n: cover(poly, n) * ncov, area, fill, dx, dy)      # Cut at the outline, as in the FVM
        E = len(ex)
        self.n_board, self.nl = L, L + NL + E
        if E:
            S = np.concatenate([S, np.stack([ly["S"] for ly in ex])])
            self.C = np.concatenate([self.C, np.stack([ly["C"] for ly in ex])])
        self.extra_links = [(L + k - 1 if k else 0, L + k, ly["g_link"]) for k, ly in enumerate(lam)]
        self.extra_links += [(ly["board_layer"], L + NL + k, ly["g_link"]) for k, ly in enumerate(ex)]
        self.block_info = [{"layer": L + NL + k, "face": ly["face"], "cov": ly["cov"], "names": ly["names"], "g_link": ly["g_link"],
                            "board_layer": ly["board_layer"]} for k, ly in enumerate(ex)]
        Lt = L + NL + E

        n = Lt * ny * nx
        idx = np.arange(n).reshape(Lt, ny, nx)
        rows, cols, vals = [], [], []

        def couple(a_idx, b_idx, g):
            a_idx, b_idx, g = a_idx.ravel(), b_idx.ravel(), g.ravel()
            keep = g > 0
            a_idx, b_idx, g = a_idx[keep], b_idx[keep], g[keep]
            rows.extend([a_idx, b_idx, a_idx, b_idx])
            cols.extend([a_idx, b_idx, b_idx, a_idx])
            vals.extend([g, g, -g, -g])

        # Lateral: face conductivity (mean of the two nodes) times the width of the face over the distance
        # (No heat crosses a face that touches a node off the board, whatever the mean of the two conductivities says)
        on = self.active
        couple(idx[:, :, :-1], idx[:, :, 1:], _mean(S[:, :, :-1], S[:, :, 1:], mean) * wy[None, :, None] / dx * (on[:, :-1] & on[:, 1:])[None])
        couple(idx[:, :-1, :], idx[:, 1:, :], _mean(S[:, :-1, :], S[:, 1:, :], mean) * wx[None, None, :] / dy * (on[:-1, :] & on[1:, :])[None])
        # Vertical: dielectric over the control area, plus the via barrels at the nearest node
        if L > 1:
            d = b.gap_thicknesses()
            gz = (b.gap_properties()[0][:, None, None] * area[None] / d[:, None, None]).copy()
            for v in problem.vias:
                # A via is a point: all its conductance goes to the node nearest to it (spreading it over the neighbours was
                # tried and removes the constriction, giving temperatures 2 % too low against the 3D solid)
                j = min(max(int(round(v.x / dx)), 0), nx - 1)
                i = min(max(int(round(v.y / dy)), 0), ny - 1)
                gz[:, i, j] += m.k_copper * v.thermal_area(b.via_plating, m.k_copper) / d
            couple(idx[:L - 1], idx[1:L], gz)
        for a_layer, b_layer, g in self.extra_links:           # Contact of a metal block with its board face
            couple(idx[a_layer], idx[b_layer], g)
        # Ambient: faces, heatsinks and edges
        self.g_top = np.zeros((Lt, ny, nx)); self.g_bottom = np.zeros_like(self.g_top)
        self.g_heatsink = np.zeros_like(self.g_top); self.g_side = np.zeros_like(self.g_top); self.g_block = np.zeros_like(self.g_top)
        self.g_top[0] = b.h_top * area
        if NL:
            for k, ly in enumerate(lam):                       # The bottom film acts on the last laminate node, the edge on every one
                self.g_bottom[L + k] = ly["g_bottom"]
                self.g_side[L + k] = ly["g_side"]
        else:
            self.g_bottom[L - 1] = b.h_bottom * area
        for sk in problem.heatsinks:
            if sk.is_block():
                continue                                       # A metal block is a layer of its own
            self.g_heatsink[sk.layer] += sk.h_extra * area * cover(sk.polygon, 4)
        for k, ly in enumerate(ex):
            self.g_block[L + NL + k] = ly["g_amb"]
            (self.g_top if ly["face"] == 0 else self.g_bottom)[ly["board_layer"]] *= ly["face_scale"]
        if b.h_side and b.has_outline():
            # Non-rectangular board: the outline length inside the control volume of every node times the slab thickness
            edge = edge_length_on_board(b.outline + np.array([0.5 * dx, 0.5 * dy]), nx, ny, dx, dy, self.active)
            self.g_side[:L] += b.h_side * slab[:, :, :] * edge[None]
        elif b.h_side:
            sl = slab[:, :, 0]                                  # (L, 1): per-layer slab
            self.g_side[:L, :, 0] += b.h_side * wy[None, :] * sl
            self.g_side[:L, :, -1] += b.h_side * wy[None, :] * sl
            self.g_side[:L, 0, :] += b.h_side * wx[None, :] * sl
            self.g_side[:L, -1, :] += b.h_side * wx[None, :] * sl
        self.g_amb = self.g_top + self.g_bottom + self.g_heatsink + self.g_side + self.g_block
        # Nodes off the board are pinned to ambient (they carry no heat); the pin is kept apart because it is not a path to the air
        self.g_pin = np.zeros_like(self.g_amb)
        self.g_pin[:, ~self.active] = 1.0
        self.g_amb = self.g_amb + self.g_pin
        rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(self.g_amb.ravel())
        self.K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsc()

        # Sources: unit-power weights of every heater (they sum to 1), so the power is exact on any grid
        self.Qw, self.Q = [], np.zeros((Lt, ny, nx))
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
            w = w * self.active                         # A part is only heated on the board
            if not (w > 0).any():                       # Footprint smaller than the grid: the node nearest to the centroid
                cx, cy = polygon_centroid(h.polygon)
                w = np.zeros((ny, nx))
                i, j = min(max(int(round(cy / dy)), 0), ny - 1), min(max(int(round(cx / dx)), 0), nx - 1)
                if not self.active[i, j]:                       # A part off the board: its power goes to the nearest board node
                    i, j = nearest_active_cell(self.active, cx, cy, dx, dy, offset=0.0)
                w[i, j] = 1.0
            full = np.zeros((Lt, ny, nx))
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
    theta_all, res = net.solve_steady()
    nb = net.n_board
    theta = theta_all[:nb]                                   # The board; the blocks are kept apart
    T = theta + b.ambient
    area, dx, dy = net.area, net.dx, net.dy
    total_area = area.sum()
    inside = net.active
    l, i, j = np.unravel_index(int(np.argmax(np.where(inside[None], T, -np.inf))), T.shape)
    out = SteadyResult(
        model="fdm", ambient=b.ambient, power_in=float(net.Q.sum()), t_max=float(T[:, inside].max()), t_min=float(T[:, inside].min()),
        t_mean=float((T * area[None]).sum() / (nb * total_area)),
        layer_mean=[float((T[q] * area).sum() / total_area) for q in range(nb)],
        t_max_location=(int(l), j * dx, i * dy), T=T, dx=dx, dy=dy,
        power_out=_power_out(net, theta_all),
        grid="nodes", residual=res, extras={"nodes": float(T.size), "harmonic": float(mean == "harmonic"),
                                            "area_sampling": float(sampling == "area")},
        warnings=[])
    if not inside.all():
        out.arrays["board_mask"] = inside
    fvm.attach_laminate_results(out, net, theta_all + b.ambient, area)
    fvm.attach_block_results(out, net, theta_all + b.ambient, theta_all)
    return out


def _power_out(net, theta):
    """!
    @brief Heat leaving through every path.
    @param net The Network.
    @param theta Rise of all layers (board first) in kelvin.
    @return Dict top, bottom, heatsinks, sides and, with metal blocks, blocks (watts).
    """
    out = {"top": float((net.g_top * theta).sum()), "bottom": float((net.g_bottom * theta).sum()),
           "heatsinks": float((net.g_heatsink * theta).sum()), "sides": float((net.g_side * theta).sum())}
    if net.extra_links:
        out["blocks"] = float((net.g_block * theta).sum())
    return out


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
