"""!
@file fvm.py
@brief Cell-centred finite-volume thermal solver for a multi-layer PCB (steady and transient).

@details Every copper layer is a 2D sheet of cells. A cell is a control volume of size
dx x dy and thickness t_pcb / layers. Heat flows

- sideways between neighbouring cells through the layer sheet conductance
  S = f * k_cu * t_cu + k_fr4_inplane * (slab - f * t_cu), where f is the copper fill,
- vertically between layers through the FR-4 dielectric (and the via barrels),
- to ambient through the top and bottom surfaces, the heatsinks and, optionally, the edges.

The steady problem is the sparse symmetric positive definite system K*theta = Q with
theta = T - T_ambient, solved directly (sparse LU) or with Conjugate Gradients. The transient
problem adds the heat capacity C and is advanced with the theta-method (implicit Euler or
Crank-Nicolson). Because the scheme is a finite-volume balance, the heat leaving the board
equals the injected power to solver precision, which the results report.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from . import blocks, laminate
from .geometry import edge_length_on_board, nearest_active_cell, coverage_fraction, cell_index_of_point, polygon_centroid
from .results import SteadyResult, TransientResult
from .numfmt import num

# Column ordering of the sparse LU: the thermal matrices are symmetric, and the symmetric minimum-degree ordering gives about half
# the fill and 40 % less time than the default COLAMD (measured on the example board at 1 and 0.5 mm)
ORDERING = "MMD_AT_PLUS_A"


class Network:
    """!
    @brief Assembled thermal network: conductances, capacities, sources and the sparse matrix.
    """

    def __init__(self, problem, nx, ny, assemble=True, with_blocks=True):
        """!
        @brief Build the network of a problem on an nx x ny grid.
        @param problem A validated Problem.
        @param nx Number of cells along x.
        @param ny Number of cells along y.
        @param assemble If False, skip building the sparse matrix (the lumped model only needs the per-cell arrays).
        @param with_blocks If False the metal blocks (heatsinks with a thickness) are left out: the heatsinks only add their coefficient on the
               board face (the lumped and analytic models see them that way).
        """
        problem.validate()
        self.problem = problem
        b = problem.board
        m = b.materials
        self.nx, self.ny, self.nl = nx, ny, b.layers
        self.n_board = b.layers                        # Board layers; the metal blocks, if any, add layers after them
        self.extra_links = []                          # (layer a, layer b, conductance array) between non-adjacent layers
        self.block_info = []
        self.laminate_layers = []                      # Indices of the laminate node layers of a one-layer board (laminate.py)
        self.dx, self.dy = b.width / nx, b.height / ny
        L, dx, dy = b.layers, self.dx, self.dy
        # Fraction of every cell that is board (all ones for a rectangle); cells off the board carry nothing
        self.cover = b.cover(nx, ny, dx, dy)
        self.active = self.cover > 0
        cell = dx * dy * self.cover          # Board area of every cell (m2), (ny, nx)
        slab = b.slab_thicknesses()          # Thickness represented by each layer node (m)
        k_lam, rho_cp_lam = b.layer_laminate()   # In-plane conductivity and volumetric heat capacity of the dielectric part of each node
        t_cu = np.asarray(b.copper_thickness)
        # A one-layer board gets laminate nodes under its copper (laminate.py): the copper node keeps the copper and half a gap
        self.laminate = laminate.nodes(b)
        if self.laminate is not None:
            slab = np.array([self.laminate.copper_slab])
        if np.any(t_cu >= slab):
            raise ValueError("copper thickness must be smaller than thickness / layers")

        # --- Copper fill fraction of every layer (union of its zones, hatching via 'fill')
        f = np.zeros((L, ny, nx))
        for z in problem.zones:
            cov = coverage_fraction(z.polygon, nx, ny, dx, dy, samples=4) * z.fill
            f[z.layer] = np.maximum(f[z.layer], cov)
        self.fill = f

        # --- Sheet conductance (W/K) and heat capacity (J/K) of every cell
        tc = t_cu[:, None, None]
        diel_t = slab[:, None, None] - f * tc          # Dielectric thickness left in the slab (m)
        self.S = (f * m.k_copper * tc + k_lam[:, None, None] * diel_t) * self.cover
        self.C = (f * m.rho_copper * m.cp_copper * tc + diel_t * rho_cp_lam[:, None, None]) * cell

        # --- Vertical conductance between layer l and l+1 (W/K)
        self.gz = np.zeros((max(L - 1, 0), ny, nx))
        if L > 1:
            d = b.gap_thicknesses()                    # One value per gap (equal in the simple stack-up)
            k_gap = b.gap_properties()[0]
            self.gz[:] = k_gap[:, None, None] * cell[None] / d[:, None, None]    # Dielectric alone
            for v in problem.vias:
                i, j = cell_index_of_point(v.x, v.y, nx, ny, dx, dy)
                # The barrel conducts in parallel with the dielectric, across every gap
                self.gz[:, i, j] += m.k_copper * v.thermal_area(b.via_plating, m.k_copper) / d

        # --- Conductance to ambient (W/K): top, bottom, heatsinks and edges are kept separate
        self.g_top = np.zeros((L, ny, nx))
        self.g_bottom = np.zeros((L, ny, nx))
        self.g_heatsink = np.zeros((L, ny, nx))
        self.g_side = np.zeros((L, ny, nx))
        self.g_top[0] = b.h_top * cell
        if self.laminate is None:
            self.g_bottom[L - 1] = b.h_bottom * cell   # (With laminate nodes the bottom film acts on the last of them, below)
        for s in problem.heatsinks:
            if s.is_block() and with_blocks:
                continue                               # A metal block is a layer of its own (below)
            cov = coverage_fraction(s.polygon, nx, ny, dx, dy, samples=4)
            self.g_heatsink[s.layer] += s.h_extra * cell * cov
        self.g_block = np.zeros((L, ny, nx))
        if self.laminate is not None:
            self._add_laminate(b, cell)
        if with_blocks:
            area = cell.copy()
            # The block is cut at the board outline: a cell off the board carries no block (it would be pinned to the ambient and drain the block)
            layers = blocks.extra_layers(problem, lambda poly, n: coverage_fraction(poly, nx, ny, dx, dy, samples=n) * self.cover, area, f, dx, dy)
            self._add_blocks(layers)
        if b.h_side and b.has_outline():
            # Edge of a non-rectangular board: the length of the outline inside every cell times the slab thickness
            edge = edge_length_on_board(b.outline, nx, ny, dx, dy, self.active)
            self.g_side[:L] += b.h_side * slab[:, None, None] * edge[None]
        elif b.h_side:
            # Each edge cell exposes a face of (cell edge length) x (slab thickness)
            sl = slab[:, None]
            self.g_side[:L, :, 0] += b.h_side * dy * sl
            self.g_side[:L, :, -1] += b.h_side * dy * sl
            self.g_side[:L, 0, :] += b.h_side * dx * sl
            self.g_side[:L, -1, :] += b.h_side * dx * sl
        self.g_amb = self.g_top + self.g_bottom + self.g_heatsink + self.g_side + self.g_block
        # Cells off the board are isolated: pin them to ambient so the matrix stays regular (they carry no heat: theta = 0).
        # The pin is kept apart (g_pin) because it is not a path to the air: the time constant must leave it out
        self.g_pin = np.zeros_like(self.g_amb)
        self.g_pin[:, ~self.active] = 1.0
        self.g_amb = self.g_amb + self.g_pin

        # --- Heat sources (W): the requested power is spread exactly over the covered cells.
        # The unit-power distribution of every heater (weights that sum to 1) is kept, so that the source of a
        # power profile can be rebuilt at every time step as a matrix-vector product.
        self.Qw = []
        L = self.nl                                    # Board layers plus the block layers
        self.Q = np.zeros((L, ny, nx))
        for h in problem.heaters:
            cov = coverage_fraction(h.polygon, nx, ny, dx, dy, samples=8) * self.active      # A part is only heated on the board
            if cov.sum() <= 0:
                # Footprint smaller than the sampling: put all the power in the centroid cell
                cx, cy = polygon_centroid(h.polygon)
                i, j = cell_index_of_point(cx, cy, nx, ny, dx, dy)
                if not self.active[i, j]:                      # A part off the board: its power goes to the nearest board cell
                    i, j = nearest_active_cell(self.active, cx, cy, dx, dy)
                cov[i, j] = 1.0
            w = np.zeros((L, ny, nx))
            w[h.layer] = cov / cov.sum()
            self.Qw.append(w)
            self.Q += h.power * w
        n_cells = L * ny * nx
        # Sparse (cells x heaters) matrix of the weights, and the flat indices of every footprint
        self.Qw_matrix = sp.csc_matrix(np.stack([w.ravel() for w in self.Qw], axis=1)) if self.Qw \
            else sp.csc_matrix((n_cells, 0))
        self.footprints = [np.flatnonzero(w.ravel() > 0) for w in self.Qw]

        self.K = self._assemble() if assemble else None

    def _edge_lengths(self):
        """!
        @brief Length of the board edge exposed in every cell (m): the outline inside the cell, or the cell sides on the border of a rectangle.
        @return Array (ny, nx).
        """
        b = self.problem.board
        if b.has_outline():
            return edge_length_on_board(b.outline, self.nx, self.ny, self.dx, self.dy, self.active)
        e = np.zeros((self.ny, self.nx))
        e[:, 0] += self.dy
        e[:, -1] += self.dy
        e[0, :] += self.dx
        e[-1, :] += self.dx
        return e

    def _add_laminate(self, b, cell):
        """!
        @brief Append the laminate nodes of a one-layer board (laminate.py) as node layers under the copper, joined by vertical conductances.
        @param b The Board.
        @param cell Board area of every cell (m2), shape (ny, nx).
        """
        layers = laminate.extra_layers(b, self.laminate, cell, self.cover, self._edge_lengths(), b.h_side)
        zeros = np.zeros((len(layers), self.ny, self.nx))
        base = self.nl
        self.S = np.concatenate([self.S, np.stack([ly["S"] for ly in layers])])
        self.C = np.concatenate([self.C, np.stack([ly["C"] for ly in layers])])
        self.g_top = np.concatenate([self.g_top, zeros])
        self.g_bottom = np.concatenate([self.g_bottom, np.stack([ly["g_bottom"] for ly in layers])])
        self.g_heatsink = np.concatenate([self.g_heatsink, zeros])
        self.g_side = np.concatenate([self.g_side, np.stack([ly["g_side"] for ly in layers])])
        self.g_block = np.concatenate([self.g_block, zeros])
        for k, ly in enumerate(layers):
            self.extra_links.append((base + k - 1 if k else 0, base + k, ly["g_link"]))
        self.laminate_layers = list(range(base, base + len(layers)))
        self.nl = base + len(layers)

    def _add_blocks(self, layers):
        """!
        @brief Append the layers of the metal blocks to the arrays of the network (see blocks.py).
        @param layers List from blocks.extra_layers.
        """
        if not layers:
            return
        base, ny, nx = self.nl, self.ny, self.nx            # The block layers come after the board and the laminate nodes
        E = len(layers)
        zeros = np.zeros((E, ny, nx))
        self.S = np.concatenate([self.S, np.stack([ly["S"] for ly in layers])])
        self.C = np.concatenate([self.C, np.stack([ly["C"] for ly in layers])])
        for name in ("g_top", "g_bottom", "g_heatsink", "g_side"):
            setattr(self, name, np.concatenate([getattr(self, name), zeros]))
        self.g_block = np.concatenate([self.g_block, np.stack([ly["g_amb"] for ly in layers])])
        # (g_pin is built after the blocks, so it already has their layers)
        for k, ly in enumerate(layers):
            idx = base + k
            self.extra_links.append((ly["board_layer"], idx, ly["g_link"]))
            # The face covered by the block no longer exchanges heat with the air
            (self.g_top if ly["face"] == 0 else self.g_bottom)[ly["board_layer"]] *= ly["face_scale"]
            self.block_info.append({"layer": idx, "face": ly["face"], "cov": ly["cov"], "names": ly["names"],
                                    "g_link": ly["g_link"], "board_layer": ly["board_layer"]})
        self.nl = base + E

    # ------------------------------------------------------------------ assembly
    @staticmethod
    def _harmonic(a, b):
        """!
        @brief Harmonic mean of two conductances (series combination of the half cells).
        @param a First array.
        @param b Second array.
        @return Array with 2ab/(a+b), zero where both are zero.
        """
        s = a + b
        out = np.zeros_like(s)
        np.divide(2.0 * a * b, s, out=out, where=s > 0)
        return out

    def _assemble(self):
        """!
        @brief Assemble the sparse conductance matrix K (W/K).
        @return scipy.sparse.csr_matrix of shape (N, N), N = layers * ny * nx.
        """
        L, ny, nx = self.nl, self.ny, self.nx
        nb = self.n_board
        idx = np.arange(L * ny * nx).reshape(L, ny, nx)
        rows, cols, vals = [], [], []

        def couple(a_idx, b_idx, g):
            # A symmetric coupling g between nodes a and b adds +g to both diagonals and -g off diagonal
            a, bb, gg = a_idx.ravel(), b_idx.ravel(), g.ravel()
            keep = gg > 0
            a, bb, gg = a[keep], bb[keep], gg[keep]
            rows.extend([a, bb, a, bb])
            cols.extend([a, bb, bb, a])
            vals.extend([gg, gg, -gg, -gg])

        # Lateral couplings: face width / distance gives dy/dx (x) and dx/dy (y)
        gx = self._harmonic(self.S[:, :, :-1], self.S[:, :, 1:]) * self.dy / self.dx
        gy = self._harmonic(self.S[:, :-1, :], self.S[:, 1:, :]) * self.dx / self.dy
        couple(idx[:, :, :-1], idx[:, :, 1:], gx)
        couple(idx[:, :-1, :], idx[:, 1:, :], gy)
        if nb > 1:
            couple(idx[:nb - 1], idx[1:nb], self.gz)
        for a_layer, b_layer, g in self.extra_links:           # Contact of a metal block with its board face
            couple(idx[a_layer], idx[b_layer], g)
        # Conductance to ambient only adds to the diagonal
        n = L * ny * nx
        diag = self.g_amb.ravel()
        rows.append(np.arange(n))
        cols.append(np.arange(n))
        vals.append(diag)
        K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                          shape=(n, n)).tocsr()
        return K

    # ------------------------------------------------------------------ solving
    def solve_steady(self, method="direct", rtol=1e-12):
        """!
        @brief Solve K*theta = Q for the steady temperature rise.
        @param method "direct" (sparse LU) or "cg" (Conjugate Gradients, Jacobi preconditioned).
        @param rtol Relative tolerance for "cg".
        @return Tuple (theta, residual): rise array of shape (layers, ny, nx) and relative residual.
        @throws RuntimeError If the iterative solver does not converge.
        """
        q = self.Q.ravel()
        if method == "direct":
            theta = spla.spsolve(self.K.tocsc(), q, permc_spec=ORDERING)
        elif method == "cg":
            # Jacobi (diagonal) preconditioner keeps CG cheap and robust for SPD thermal matrices
            dinv = 1.0 / self.K.diagonal()
            M = spla.LinearOperator(self.K.shape, matvec=lambda x: dinv * x)
            theta, info = spla.cg(self.K, q, rtol=rtol, atol=0.0, maxiter=20000, M=M)
            if info != 0:
                raise RuntimeError(f"CG did not converge (info={info})")
        else:
            raise ValueError("method must be 'direct' or 'cg'")
        res = np.linalg.norm(self.K @ theta - q) / max(np.linalg.norm(q), 1e-300)
        return theta.reshape(self.nl, self.ny, self.nx), float(res)

    def solve_sor(self, omega=None, tol=1e-9, max_iter=200000, criterion="residual"):
        """!
        @brief Solve K*theta = Q with red-black Successive Over-Relaxation (vectorised with NumPy).
        @details Every sweep updates the "red" nodes (l+i+j even) and then the "black" ones, each colour in one
                 array operation, so the iteration is the classical SOR of the original program but fast.
                 theta_new = (sum_m G_m theta_m + Q) / diag, theta += omega * (theta_new - theta).
        @param omega Relaxation factor; None picks 2 / (1 + sin(pi / n)) with n the longest grid side.
        @param tol Stopping tolerance.
        @param max_iter Sweep limit.
        @param criterion "residual" stops when |K theta - Q| / |Q| < tol (reliable);
                         "step" stops when the largest change of one sweep is below tol in kelvin
                         (the rule of the original program, which can stop far from the solution).
        @return Tuple (theta, residual, info) with info = dict(iterations, converged, omega, last_step).
        """
        if self.block_info:
            raise ValueError("SOR does not support metal blocks: use the direct solver or the conjugate gradients")
        L, ny, nx = self.nl, self.ny, self.nx
        if omega is None:
            omega = 2.0 / (1.0 + np.sin(np.pi / max(nx, ny)))
        K, Q = self.K, self.Q
        diag = K.diagonal().reshape(L, ny, nx)
        # Conductances towards the six neighbours (zero where the neighbour does not exist)
        gl = np.zeros((L, ny, nx)); gr = np.zeros((L, ny, nx))     # x-1, x+1
        gd = np.zeros((L, ny, nx)); gu = np.zeros((L, ny, nx))     # y-1, y+1
        ga = np.zeros((L, ny, nx)); gb = np.zeros((L, ny, nx))     # layer-1, layer+1
        gx = self._harmonic(self.S[:, :, :-1], self.S[:, :, 1:]) * self.dy / self.dx
        gy = self._harmonic(self.S[:, :-1, :], self.S[:, 1:, :]) * self.dx / self.dy
        gr[:, :, :-1], gl[:, :, 1:] = gx, gx
        gu[:, :-1, :], gd[:, 1:, :] = gy, gy
        if L > 1:
            # Vertical conductances between consecutive node layers: the dielectric gaps of the board and the links of the laminate nodes
            gzz = np.zeros((L - 1, ny, nx))
            gzz[:self.n_board - 1] = self.gz
            for a, b_layer, g in self.extra_links:
                gzz[a] += g                            # The laminate links join consecutive layers (a, a + 1)
            gb[:-1], ga[1:] = gzz, gzz
        l_i, i_i, j_i = np.indices((L, ny, nx))
        colour = (l_i + i_i + j_i) % 2 == 0
        masks = (colour, ~colour)
        qn = np.linalg.norm(Q)
        theta = np.zeros((L, ny, nx))
        pad = np.zeros((L + 2, ny + 2, nx + 2))
        converged, last_step, it = False, np.inf, 0

        def neighbours(t):
            # Weighted sum of the neighbour temperatures using a zero-padded copy
            pad[1:-1, 1:-1, 1:-1] = t
            return (gl * pad[1:-1, 1:-1, :-2] + gr * pad[1:-1, 1:-1, 2:] + gd * pad[1:-1, :-2, 1:-1] +
                    gu * pad[1:-1, 2:, 1:-1] + ga * pad[:-2, 1:-1, 1:-1] + gb * pad[2:, 1:-1, 1:-1])

        for it in range(1, max_iter + 1):
            step = 0.0
            for m in masks:
                new = (neighbours(theta) + Q) / diag
                delta = np.where(m, new - theta, 0.0)
                theta = theta + omega * delta
                step = max(step, float(np.abs(delta).max()))
            last_step = step
            if criterion == "step":
                if step < tol:
                    converged = True
                    break
            elif it % 10 == 0 or step < tol:
                if np.linalg.norm(K @ theta.ravel() - Q.ravel()) / max(qn, 1e-300) < tol:
                    converged = True
                    break
        res = float(np.linalg.norm(K @ theta.ravel() - Q.ravel()) / max(qn, 1e-300))
        return theta, res, {"iterations": it, "converged": converged, "omega": float(omega), "last_step": last_step}

    def power_out(self, theta):
        """!
        @brief Heat leaving the board through every path for a given temperature rise.
        @param theta Rise array of shape (layers, ny, nx).
        @return Dict with keys top, bottom, heatsinks, sides in watts.
        """
        out = {
            "top": float((self.g_top * theta).sum()),
            "bottom": float((self.g_bottom * theta).sum()),
            "heatsinks": float((self.g_heatsink * theta).sum()),
            "sides": float((self.g_side * theta).sum()),
        }
        if self.extra_links:
            out["blocks"] = float((self.g_block * theta).sum())           # Heat leaving through the exposed surface of the blocks
        return out


def _result_from_theta(net, theta, residual, model="fvm"):
    """!
    @brief Package a temperature-rise field as a SteadyResult.
    @param net The Network that produced it.
    @param theta Rise array (layers, ny, nx) in kelvin.
    @param residual Relative residual of the linear solve.
    @param model Model name to store.
    @return SteadyResult with absolute temperatures.
    """
    amb = net.problem.board.ambient
    nb = net.n_board
    T_all = theta + amb
    T = T_all[:nb]                                     # The board; the block layers are kept apart
    inside = net.active                                # Cells that are board (all of them for a rectangle)
    cover = net.cover
    k = int(np.argmax(np.where(inside[None], T, -np.inf)))
    l, i, j = np.unravel_index(k, T.shape)
    res = SteadyResult(
        model=model, ambient=amb, power_in=float(net.Q.sum()),
        t_max=float(T[:, inside].max()), t_min=float(T[:, inside].min()),
        t_mean=float((T * cover[None]).sum() / (nb * cover.sum())),
        layer_mean=[float((T[n] * cover).sum() / cover.sum()) for n in range(nb)],
        t_max_location=(int(l), (j + 0.5) * net.dx, (i + 0.5) * net.dy),
        T=T, dx=net.dx, dy=net.dy, power_out=net.power_out(theta), residual=residual,
        extras={"cells": float(inside.sum() * nb)},
    )
    if not inside.all():
        res.arrays["board_mask"] = inside              # The plots leave the cells off the board blank
    attach_laminate_results(res, net, T_all, cover)
    attach_block_results(res, net, T_all, theta)
    return res


def attach_laminate_results(res, net, T_all, weights):
    """!
    @brief Put the mean temperature of the bottom face of a one-layer board (its last laminate node) in a result, for the computed heat transfer coefficients.
    @param res SteadyResult of the board.
    @param net Network with laminate nodes (nothing is done without them).
    @param T_all Temperatures of all node layers in degC.
    @param weights Board area or cover of every cell or node, shape (ny, nx).
    """
    layers = getattr(net, "laminate_layers", None)
    if not layers:
        return
    res.extras["bottom_face_mean"] = float((T_all[layers[-1]] * weights).sum() / weights.sum())


def attach_block_results(res, net, T_all, theta):
    """!
    @brief Put the temperature of the metal blocks, the heat they take and the heat flux entering them in a result.
    @details arrays["block_flux"] is the heat flux through the interface into every block cell or node, in W/m2 of block area (zero off the blocks),
             and arrays["block_face"] the face (0 top, 1 bottom) of every block layer; checks.check_thick_plates reads them.
    @param res SteadyResult of the board.
    @param net Network with block layers (nothing is done without them).
    @param T_all Temperatures of all layers, board first, in degC.
    @param theta Rise of all layers in kelvin.
    """
    if not net.block_info:
        return
    # Only the block layers: on a one-layer board the laminate nodes sit between the board layer and the blocks
    ids = [bi["layer"] for bi in net.block_info]
    res.arrays["block_T"] = T_all[ids]                 # (blocks layers, ny, nx), ambient where there is no block
    res.arrays["block_cov"] = np.stack([bi["cov"] for bi in net.block_info])
    res.arrays["block_face"] = np.array([bi["face"] for bi in net.block_info])
    # Plan area of every cell (FVM) or node (FDM) on the board, in m2: the flux is the heat into the block over the block's share of it
    area = net.area if hasattr(net, "area") else net.dx * net.dy * net.cover
    flux = []
    for bi in net.block_info:
        heat = bi["g_link"] * (theta[bi["board_layer"]] - theta[bi["layer"]])
        share = bi["cov"] * area
        flux.append(np.where(share > 0, heat / np.where(share > 0, share, 1.0), 0.0))
    res.arrays["block_flux"] = np.stack(flux)
    for k, bi in enumerate(net.block_info):
        sel = bi["cov"] > 0
        tag = "top" if bi["face"] == 0 else "bottom"
        layer_theta = theta[bi["layer"]]
        res.extras[f"block_{tag}_max"] = float(T_all[bi["layer"]][sel].max())
        res.extras[f"block_{tag}_mean"] = float((T_all[bi["layer"]][sel] * bi["cov"][sel]).sum() / bi["cov"][sel].sum())
        res.extras[f"block_{tag}_w_to_block"] = float((bi["g_link"] * (theta[bi["board_layer"]] - layer_theta)).sum())
        res.extras[f"block_{tag}_w_to_air"] = float((net.g_block[bi["layer"]] * layer_theta).sum())


def solve_steady(problem, cell_mm=2.0, method="direct", sor_omega=None, sor_tol=1e-9, sor_criterion="residual"):
    """!
    @brief Steady-state FVM solution of a problem.
    @param problem A Problem.
    @param cell_mm Target cell size in millimetres (the grid is nx = round(width / cell)).
    @param method "direct" (sparse LU), "cg" (conjugate gradients) or "sor" (red-black SOR, for comparison).
    @param sor_omega Relaxation factor for "sor" (None = automatic).
    @param sor_tol Tolerance for "sor".
    @param sor_criterion "residual" or "step" (see Network.solve_sor).
    @return SteadyResult (for "sor" the extras hold iterations, omega and converged).
    """
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    net = Network(problem, nx, ny)
    if method == "sor":
        theta, res, info = net.solve_sor(omega=sor_omega, tol=sor_tol, criterion=sor_criterion)
        r = _result_from_theta(net, theta, res)
        r.extras.update({"iterations": float(info["iterations"]), "omega": info["omega"],
                         "converged": float(info["converged"])})
        if not info["converged"]:
            r.warnings.append(f"SOR did not converge in {info['iterations']} sweeps (residual {num(res)})")
        return r
    theta, res = net.solve_steady(method=method)
    return _result_from_theta(net, theta, res)


def solve_transient(problem, t_end, n_out=40, cell_mm=2.0, substeps=4, theta_scheme=1.0,
                    log_times=True):
    """!
    @brief Transient response to a power step starting from a board at ambient temperature.
    @details Uses the theta-method: (C/dt + theta*K) x1 = (C/dt - (1-theta)*K) x0 + Q.
             theta = 1 is implicit Euler (robust), theta = 0.5 is Crank-Nicolson (more accurate).
             Both are unconditionally stable for the diffusion equation.
    @param problem A Problem.
    @param t_end Final time in seconds.
    @param n_out Number of output frames (excluding t = 0); in logarithmic mode it is rounded up to a multiple of 10.
    @param cell_mm Target cell size in millimetres.
    @param substeps Implicit steps between two output frames (linear mode only; logarithmic mode uses one step per frame).
    @param theta_scheme 1.0 for implicit Euler, 0.5 for Crank-Nicolson.
    @param log_times If True the time step doubles in ten stages (resolves fast and slow parts with few factorisations).
    @return TransientResult.
    """
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    return transient_from_network(Network(problem, nx, ny), b.ambient, t_end, n_out, substeps, theta_scheme, log_times)


def transient_from_network(net, ambient, t_end, n_out=40, substeps=4, theta_scheme=1.0, log_times=True, grid="cells"):
    """!
    @brief Power-step transient of any thermal network with the attributes of Network (also the finite-difference one).
    @details The network provides K (sparse conductances), C (heat capacity per unknown), Q (source), nl, ny, nx and solve_steady().
    @param net The network.
    @param ambient Ambient temperature in degC.
    @param t_end Final time in seconds.
    @param n_out Number of output frames (excluding t = 0).
    @param substeps Implicit steps between two frames (linear mode only).
    @param theta_scheme 1.0 for implicit Euler, 0.5 for Crank-Nicolson.
    @param log_times True for the doubling time step.
    @param grid "cells" or "nodes": what the frames hold.
    @return TransientResult.
    """
    ny, nx = net.ny, net.nx
    nb = getattr(net, "n_board", net.nl)
    steady_theta, _ = net.solve_steady()
    weights = mean_weights(net)                             # Board area of every cell or node: the mean leaves out what is off the board

    # --- Time grid: every frame is one time step, and the steps are built so that few distinct dt occur
    # (one LU factorisation per distinct dt). Linear: one dt. Logarithmic: dt doubles stage after stage.
    if log_times:
        stages = 10
        per_stage = max(int(np.ceil(n_out / stages)), 1)
        dt0 = t_end / (per_stage * (2 ** stages - 1))
        dts = np.concatenate([np.full(per_stage, dt0 * 2.0 ** j) for j in range(stages)])
    else:
        dts = np.full(max(n_out, 1) * max(substeps, 1), t_end / (max(n_out, 1) * max(substeps, 1)))
    step_times = np.concatenate([[0.0], np.cumsum(dts)])
    step_times[-1] = t_end                                  # Remove round-off at the end
    keep = np.arange(len(step_times)) if log_times else np.arange(0, len(step_times), max(substeps, 1))
    times = step_times[keep]

    N = net.nl * ny * nx
    Cd = net.C.ravel()
    q = net.Q.ravel()
    x = np.zeros(N)                                         # Rise above ambient, starts at zero
    frames = {0: x.reshape(net.nl, ny, nx)[:nb] + ambient}
    cache = {}
    kept = set(keep.tolist())
    for k, dt in enumerate(dts, start=1):
        key = round(float(dt), 12)
        if key not in cache:
            A = (sp.diags(Cd / dt) + theta_scheme * net.K).tocsc()
            B = (sp.diags(Cd / dt) - (1.0 - theta_scheme) * net.K).tocsr()
            cache[key] = (spla.splu(A, permc_spec=ORDERING), B)
        lu, B = cache[key]
        x = lu.solve(B @ x + q)
        if k in kept:
            frames[k] = x.reshape(net.nl, ny, nx)[:nb] + ambient
    frames = np.asarray([frames[k] for k in keep])
    inside = weights > 0
    return TransientResult(
        times=times, t_max=frames[:, :, inside].reshape(len(times), -1).max(axis=1),
        t_mean=(frames * weights).sum(axis=(1, 2, 3)) / (nb * weights.sum()), frames=frames,
        steady_t_max=float(steady_theta[:nb].max() + ambient), ambient=ambient, grid=grid,
    )


def step_responses(problem, cell_mm=2.0, t_end=None, ratio=3.0, per_stage=4, stages=18, theta_scheme=0.5):
    """!
    @brief Response of every heater's hottest point to a unit power step of that heater, all heaters at once.
    @details The heaters are solved as several right-hand sides of the same matrices. The time step grows by
             the factor `ratio` after every `per_stage` steps (one matrix factorisation per stage), which covers
             about nine decades of time with a few dozen steps. The result Z_i(t) is in degC per W and is what the
             power-profile analysis uses to estimate oscillations and periodic peaks.
    @param problem A Problem with at least one heater.
    @param cell_mm Target cell size in millimetres.
    @param t_end Last time in seconds (default: ten board time constants).
    @param ratio Growth factor of the time step between stages.
    @param per_stage Steps per stage.
    @param stages Number of stages.
    @param theta_scheme 0.5 (Crank-Nicolson) or 1.0 (implicit Euler).
    @return Tuple (times, z, rth): times (nt,) in s without t = 0, z (n_heaters, nt) in degC/W and rth (n_heaters,)
            in degC/W (steady state).
    @throws ValueError If the problem has no heater.
    """
    if not problem.heaters:
        raise ValueError("the problem has no heater")
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    return step_responses_from_network(Network(problem, nx, ny), t_end, ratio, per_stage, stages, theta_scheme)


def step_responses_from_network(net, t_end=None, ratio=3.0, per_stage=4, stages=18, theta_scheme=0.5):
    """!
    @brief Step responses of the heaters of any network with the attributes of Network (see step_responses).
    @param net The network (K, C, g_amb, Qw_matrix).
    @param t_end Last time in seconds (default: ten board time constants).
    @param ratio Growth factor of the time step between stages.
    @param per_stage Steps per stage.
    @param stages Number of stages.
    @param theta_scheme 0.5 (Crank-Nicolson) or 1.0 (implicit Euler).
    @return Tuple (times, z, rth).
    """
    if t_end is None:
        t_end = 10.0 * board_time_constant(net)
    Q = net.Qw_matrix.toarray()                                   # (cells, heaters), unit power each
    rth = (spla.splu(net.K.tocsc(), permc_spec=ORDERING).solve(Q)).max(axis=0)
    # Step sizes: per_stage steps of dt0 * ratio^j for j = 0..stages-1, scaled so that they sum to t_end
    geometric = per_stage * (ratio ** stages - 1.0) / (ratio - 1.0)
    dt0 = t_end / geometric
    Cd = net.C.ravel()
    x = np.zeros_like(Q)
    times, z, t = [], [], 0.0
    for j in range(stages):
        dt = dt0 * ratio ** j
        A = (sp.diags(Cd / dt) + theta_scheme * net.K).tocsc()
        B = (sp.diags(Cd / dt) - (1.0 - theta_scheme) * net.K).tocsr()
        lu = spla.splu(A, permc_spec=ORDERING)
        for _ in range(per_stage):
            x = lu.solve((B @ x) + Q)
            t += dt
            times.append(t)
            z.append(x.max(axis=0))
    return np.asarray(times), np.asarray(z).T, rth


def estimate_time_constant(problem, cell_mm=5.0):
    """!
    @brief Slowest-scale thermal time constant of the whole board, C_total / G_total.
    @details Uniform-board estimate: the total heat capacity divided by the total conductance to ambient.
             The hottest point reaches 63 % much sooner; the board mean needs a few of these constants.
    @param problem A Problem.
    @param cell_mm Cell size used to aggregate the properties (the result hardly depends on it).
    @return Time constant in seconds.
    """
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    net = Network(problem, nx, ny, assemble=False, with_blocks=False)
    return board_time_constant(net)


def board_time_constant(net):
    """!
    @brief Total heat capacity over the total conductance to the ambient of a network, C_total / G_total.
    @details The conductance that pins the cells or nodes off a board with an outline (g_pin, 1 W/K each) keeps the matrix regular but is not a
             path to the air; it is left out (counting it gave 0.2 s instead of about 100 s on a round board of 100 mm).
    @param net A network with C, g_amb and optionally g_pin (fvm.Network, fdm.Network).
    @return Time constant in seconds.
    """
    g = net.g_amb.sum() - (net.g_pin.sum() if getattr(net, "g_pin", None) is not None else 0.0)
    return float(net.C.sum() / g)


def mean_weights(net):
    """!
    @brief Weights of the board mean over the grid of a network: the board area of every cell (FVM) or node (FDM).
    @param net A network (fvm.Network has cover and dx, dy; fdm.Network has area).
    @return Array (ny, nx) in m2, zero off the board.
    """
    if getattr(net, "area", None) is not None:
        return np.asarray(net.area, dtype=float)
    return np.asarray(net.cover, dtype=float) * net.dx * net.dy
