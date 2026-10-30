#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file sorvia.py
@brief Red-black SOR variants that can carry the mean-potential via couplings of the FVM (in-memory prototypes; the program is not edited).
@details The matrix K of an assembled `fvm.Network` with a via treatment of `program_patch` is the five-point/vertical stencil (an M-matrix) plus the via part
         `K_via = sum_v B_v^T G_v B_v` (dense blocks: every footprint cell of every layer is coupled to every other one, with positive in-plane terms).
         The program's `Network.solve_sor` rebuilds the off-diagonals from the stencil arrays and takes only the diagonal from K, so it iterates a different matrix.
         Variants implemented here (names used in the README):
         * `program`  the program's rule (stencil off-diagonals, diagonal of K): reproduces the failure;
         * `lagged`   (a) the via part is an explicit term `K_via theta` of the residual, recomputed at every colour update (Jacobi-like on the via part);
         * `block`    (c) the cells of every via (footprint x layers) are one block solved exactly (dense inverse) after the two colours (block Gauss-Seidel);
         * `woodbury` (b) SOR on the stencil matrix A = K - K_via only, with the via part by the Sherman-Morrison-Woodbury identity (m + 1 SOR solves of A,
           m = footprint means: layers x vias) and a small direct solve of the capacitance matrix;
         * `ssor_cg`  (d) conjugate gradients preconditioned by symmetric SOR on the true K.
@note Everything here works on arrays of the network; nothing of `pcbthermal/` is modified.
"""

import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def stencil_parts(net):
    """!
    @brief Conductances of the stencil (six neighbours) of a network, as the program's `solve_sor` builds them, plus the matching sparse matrix.
    @param net An assembled `fvm.Network` (steady state; no metal blocks).
    @return dict with g (tuple gl, gr, gd, gu, ga, gb of arrays (L, ny, nx)), S (sparse off-diagonal stencil matrix, negative entries) and shape (L, ny, nx).
    """
    L, ny, nx = net.nl, net.ny, net.nx
    z = lambda: np.zeros((L, ny, nx))                                           # noqa: E731
    gl, gr, gd, gu, ga, gb = z(), z(), z(), z(), z(), z()
    gx = net._harmonic(net.S[:, :, :-1], net.S[:, :, 1:]) * net.dy / net.dx
    gy = net._harmonic(net.S[:, :-1, :], net.S[:, 1:, :]) * net.dx / net.dy
    gr[:, :, :-1], gl[:, :, 1:] = gx, gx
    gu[:, :-1, :], gd[:, 1:, :] = gy, gy
    if L > 1:
        gzz = np.zeros((L - 1, ny, nx))
        gzz[:net.n_board - 1] = net.gz
        for a, _b, g in net.extra_links:
            gzz[a] += g                                                         # the program assumes (a, a + 1)
        gb[:-1], ga[1:] = gzz, gzz
    idx = np.arange(L * ny * nx).reshape(L, ny, nx)
    r, c, v = [], [], []
    for a, b_, g in ((idx[:, :, :-1], idx[:, :, 1:], gx), (idx[:, :-1, :], idx[:, 1:, :], gy)):
        r += [a.ravel(), b_.ravel()]; c += [b_.ravel(), a.ravel()]; v += [-g.ravel(), -g.ravel()]
    if L > 1:
        a, b_, g = idx[:-1], idx[1:], gb[:-1]
        r += [a.ravel(), b_.ravel()]; c += [b_.ravel(), a.ravel()]; v += [-g.ravel(), -g.ravel()]
    n = L * ny * nx
    S = sp.csr_matrix((np.concatenate(v), (np.concatenate(r), np.concatenate(c))), shape=(n, n))
    return {"g": (gl, gr, gd, gu, ga, gb), "S": S, "shape": (L, ny, nx)}


def via_matrix(net):
    """!
    @brief The via part of the matrix: K minus its diagonal minus the stencil.
    @param net An assembled `fvm.Network`.
    @return scipy.sparse.csr_matrix with the off-diagonal entries that the stencil does not hold (zero matrix for the point treatment), explicit zeros removed.
    """
    parts = stencil_parts(net)
    Kv = (net.K.tocsr() - sp.diags(net.K.diagonal()) - parts["S"]).tocsr()
    Kv.data[np.abs(Kv.data) < 1e-12 * np.abs(net.K.diagonal()).max()] = 0.0
    Kv.eliminate_zeros()
    return Kv


def via_operator(net):
    """!
    @brief The via part with its diagonal, rebuilt from the blocks stored by the patch: K_via = sum B^T G B, and the matrices B and G (block diagonal).
    @param net A network built inside `program_patch.patched` with a mean-potential treatment.
    @return tuple (Kfull, B, Gm): Kfull = B^T Gm B (sparse, N x N, with its diagonal), B (m x N, rows = (via, layer) footprint means) and Gm (m x m, block diagonal).
    """
    n = net.nl * net.ny * net.nx
    idx = np.arange(n).reshape(net.nl, net.ny, net.nx)
    rows, cols, vals, Gs = [], [], [], []
    m0 = 0
    for cells, w, G in getattr(net, "_via_blocks", []):
        L = G.shape[0]
        ci = np.array([c[0] for c in cells]); cj = np.array([c[1] for c in cells])
        for l in range(L):
            rows.append(np.full(len(cells), m0 + l)); cols.append(idx[l, ci, cj]); vals.append(w)
        # Laplacian of the Kron-reduced couplings: G[l, m] > 0 couples the means l and m; the matrix is L = diag(sum) - G
        Gl = np.diag(G.sum(axis=1)) - G
        Gs.append(sp.csr_matrix(Gl))
        m0 += L
    if m0 == 0:
        return sp.csr_matrix((n, n)), sp.csr_matrix((0, n)), sp.csr_matrix((0, 0))
    B = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(m0, n))
    Gm = sp.block_diag(Gs, format="csr")
    return (B.T @ Gm @ B).tocsr(), B, Gm


class RB:
    """!
    @brief Red-black SOR on a network with optional extra (via) operator, via blocks and an explicit matrix for the residual.
    """

    def __init__(self, net, K=None, diag=None, omega=None, Kv=None, blocks=None, block_omega=1.0):
        """!
        @brief Prepare the iteration.
        @param net The network (its stencil arrays are used).
        @param K Sparse matrix that defines the residual (default net.K).
        @param diag Diagonal used by the point updates (default the diagonal of K).
        @param omega Relaxation factor (None: the program's 2 / (1 + sin(pi / max(nx, ny)))).
        @param Kv Sparse via part added explicitly to the residual of every point update (None: dropped, as in the program).
        @param blocks List of index arrays (flat unknowns); each is a block solved exactly after the colours (None: no blocks). Cells of a block are skipped by the colours.
        @param block_omega Relaxation factor of the block step.
        """
        self.net = net
        self.K = (net.K if K is None else K).tocsr()
        self.diag = (self.K.diagonal() if diag is None else diag).reshape(net.nl, net.ny, net.nx)
        p = stencil_parts(net)
        self.g, self.shape = p["g"], p["shape"]
        L, ny, nx = self.shape
        self.omega = 2.0 / (1.0 + np.sin(np.pi / max(nx, ny))) if omega is None else omega
        self.Kv = Kv
        li, ii, jj = np.indices(self.shape)
        col = (li + ii + jj) % 2 == 0
        self.masks = [col, ~col]
        self.blocks = blocks
        self.block_omega = block_omega
        if blocks:
            skip = np.zeros(L * ny * nx, bool)
            for b in blocks:
                skip[b] = True
            skip = skip.reshape(self.shape)
            self.masks = [m & ~skip for m in self.masks]
            rows = np.concatenate(blocks)
            self.Kb = self.K[rows, :]
            inv = [np.linalg.inv(self.K[b][:, b].toarray()) for b in blocks]
            self.Binv = sp.block_diag(inv, format="csr")
            self.brows = rows

    def _neigh(self, t, pad):
        """!
        @brief Weighted sum of the six neighbour temperatures (zero-padded copy).
        @param t Temperatures (L, ny, nx).
        @param pad Work array (L + 2, ny + 2, nx + 2).
        @return The sum, shape (L, ny, nx).
        """
        pad[1:-1, 1:-1, 1:-1] = t
        gl, gr, gd, gu, ga, gb = self.g
        return (gl * pad[1:-1, 1:-1, :-2] + gr * pad[1:-1, 1:-1, 2:] + gd * pad[1:-1, :-2, 1:-1] +
                gu * pad[1:-1, 2:, 1:-1] + ga * pad[:-2, 1:-1, 1:-1] + gb * pad[2:, 1:-1, 1:-1])

    def sweep(self, theta, q):
        """!
        @brief One sweep: the two colours, then the via blocks (when any).
        @param theta Current iterate, shape (L, ny, nx).
        @param q Right-hand side, shape (L, ny, nx).
        @return The new iterate.
        """
        L, ny, nx = self.shape
        if not hasattr(self, "_pad"):
            self._pad = np.zeros((L + 2, ny + 2, nx + 2))
        for m in self.masks:
            new = self._neigh(theta, self._pad) + q
            if self.Kv is not None:
                # The via part is an explicit term of the residual, evaluated with the current iterate (including the colour just updated)
                new = new - (self.Kv @ theta.ravel()).reshape(self.shape)
            new = new / self.diag
            theta = theta + self.omega * np.where(m, new - theta, 0.0)
        if self.blocks:
            # Block Gauss-Seidel step: the exact solve of every via block given the rest
            r = q.ravel()[self.brows] - self.Kb @ theta.ravel()
            tf = theta.ravel().copy()
            tf[self.brows] += self.block_omega * (self.Binv @ r)
            theta = tf.reshape(self.shape)
        return theta

    def solve(self, rhs, tol=1e-9, max_iter=200000, theta0=None, check=10):
        """!
        @brief Iterate until the relative residual of the true matrix is below tol.
        @param rhs Right-hand side, shape (L, ny, nx) or flat.
        @param tol Stopping tolerance on |K theta - rhs| / |rhs|.
        @param max_iter Sweep limit.
        @param theta0 Starting vector (default zeros).
        @param check Sweeps between residual evaluations (also the sampling of the history).
        @return dict(theta, iterations, converged, residual, history [(sweep, residual)], seconds).
        """
        L, ny, nx = self.shape
        q = np.asarray(rhs, float).reshape(self.shape)
        qn = max(np.linalg.norm(q), 1e-300)
        theta = np.zeros(self.shape) if theta0 is None else np.array(theta0, float).reshape(self.shape)
        hist, conv, t0, res = [], False, time.perf_counter(), np.inf
        for it in range(1, max_iter + 1):
            theta = self.sweep(theta, q)
            if it % check == 0:
                res = np.linalg.norm(self.K @ theta.ravel() - q.ravel()) / qn
                hist.append((it, float(res)))
                if not np.isfinite(res):
                    break
                if res < tol:
                    conv = True
                    break
        return {"theta": theta, "iterations": it, "converged": conv, "residual": float(res), "history": hist,
                "seconds": time.perf_counter() - t0}


def via_blocks(net):
    """!
    @brief Index arrays of the unknowns of every via (footprint cells of every layer), as blocks for `RB`.
    @param net A network built inside `program_patch.patched`.
    @return list of integer arrays; blocks of vias that share a cell are merged.
    """
    n = net.nl * net.ny * net.nx
    idx = np.arange(n).reshape(net.nl, net.ny, net.nx)
    sets = []
    for cells, w, G in getattr(net, "_via_blocks", []):
        ci = np.array([c[0] for c in cells]); cj = np.array([c[1] for c in cells])
        sets.append(set(idx[:, ci, cj].ravel().tolist()))
    merged = []
    for s in sets:
        for m in [m for m in merged if m & s]:
            s |= m
            merged.remove(m)
        merged.append(s)
    return [np.array(sorted(s)) for s in merged]


def solve_variant(net, variant, omega=None, tol=1e-9, max_iter=200000, block_omega=1.0):
    """!
    @brief Solve K theta = Q with one of the SOR variants.
    @param net An assembled network (inside or outside the patch; the via blocks are read from `net._via_blocks` when present).
    @param variant program, lagged, block or woodbury.
    @param omega Relaxation factor (None: the program's).
    @param tol Stopping tolerance of the residual.
    @param max_iter Sweep limit (per solve).
    @param block_omega Relaxation factor of the block step (variant block).
    @return dict as `RB.solve` (for woodbury: iterations = total sweeps of all the inner solves, history of the first solve, extra key solves).
    """
    Q = net.Q
    if variant == "program":
        return RB(net, omega=omega).solve(Q, tol, max_iter)
    if variant == "lagged":
        Kv = via_matrix(net)
        return RB(net, omega=omega, Kv=Kv if Kv.nnz else None).solve(Q, tol, max_iter)
    if variant == "block":
        return RB(net, omega=omega, blocks=via_blocks(net), block_omega=block_omega).solve(Q, tol, max_iter)
    if variant == "woodbury":
        return _woodbury(net, omega, tol, max_iter)
    raise ValueError(variant)


def _woodbury(net, omega, tol, max_iter):
    """!
    @brief SOR on A = K - K_via plus the Woodbury correction: theta = y0 - Z (I + C Gm)^-1 B y0, with y0 = A^-1 Q, Z = A^-1 B^T Gm, C = B A^-1 B^T.
    @param net The network.
    @param omega Relaxation factor.
    @param tol Tolerance of every inner solve.
    @param max_iter Sweep limit of every inner solve.
    @return dict like `RB.solve` with the sums over the inner solves.
    """
    Kfull, B, Gm = via_operator(net)
    n = net.K.shape[0]
    A = (net.K - Kfull).tocsr()
    rb = RB(net, K=A, diag=A.diagonal(), omega=omega)
    t0 = time.perf_counter()
    first = rb.solve(net.Q, tol, max_iter)
    total, ok = first["iterations"], first["converged"]
    y0 = first["theta"].ravel()
    m = B.shape[0]
    if m == 0:
        return first
    # Columns of A^-1 B^T (m solves); their SOR is the cost of the method
    Zc = np.zeros((n, m))
    Bt = B.T.tocsc()
    for k in range(m):
        s = rb.solve(Bt[:, k].toarray().ravel(), tol, max_iter)
        total += s["iterations"]
        ok = ok and s["converged"]
        Zc[:, k] = s["theta"].ravel()
    C = B @ Zc                                                                  # B A^-1 B^T (m x m)
    Gd = Gm.toarray()
    # theta = y0 - Zc Gm (I + C Gm)^-1 (B y0)
    corr = np.linalg.solve(np.eye(m) + C @ Gd, B @ y0)
    theta = (y0 - Zc @ (Gd @ corr)).reshape(net.nl, net.ny, net.nx)
    res = np.linalg.norm(net.K @ theta.ravel() - net.Q.ravel()) / np.linalg.norm(net.Q)
    return {"theta": theta, "iterations": total, "converged": bool(ok), "residual": float(res), "history": first["history"],
            "seconds": time.perf_counter() - t0, "solves": m + 1}


def ssor_cg(net, omega=1.0, tol=1e-9, max_iter=20000, order="natural"):
    """!
    @brief Conjugate gradients on the true K preconditioned by SSOR, M = (D/w + E) (w/(2-w)) D^-1 (D/w + F) with K = E + D + F (Saad, section 10.2).
    @param net The network.
    @param omega SSOR relaxation (1 = symmetric Gauss-Seidel).
    @param tol Relative residual tolerance.
    @param max_iter Iteration limit.
    @param order natural (the program's flat order) or redblack (red cells, black cells, then the via cells).
    @return dict(theta, iterations, converged, residual, seconds).
    """
    K = net.K.tocsr()
    n = K.shape[0]
    perm = np.arange(n)
    if order == "redblack":
        li, ii, jj = np.indices((net.nl, net.ny, net.nx))
        col = ((li + ii + jj) % 2).ravel()
        isvia = np.zeros(n, bool)
        for b in via_blocks(net):
            isvia[b] = True
        key = np.where(isvia, 2, col)
        perm = np.argsort(key, kind="stable")
    Kp = K[perm][:, perm].tocsr()
    d = Kp.diagonal()
    Lw = (sp.tril(Kp, -1) + sp.diags(d / omega)).tocsr()
    Uw = (sp.triu(Kp, 1) + sp.diags(d / omega)).tocsr()

    # M^-1 = (2-w)/w ... derived: M = (D/w+E) (w/(2-w)) D^-1 (D/w+F) -> M^-1 r = ((2-w)/w) (D/w+F)^-1 D (D/w+E)^-1 r
    def minv(r):
        y = spla.spsolve_triangular(Lw, r, lower=True)
        return spla.spsolve_triangular(Uw, d * y, lower=False) * (2.0 - omega) / omega

    q = net.Q.ravel()[perm]
    count = [0]
    t0 = time.perf_counter()
    theta, info = spla.cg(Kp, q, rtol=tol, atol=0.0, maxiter=max_iter, M=spla.LinearOperator(Kp.shape, matvec=minv), callback=lambda x: count.__setitem__(0, count[0] + 1))
    out = np.empty(n)
    out[perm] = theta
    res = np.linalg.norm(K @ out - net.Q.ravel()) / np.linalg.norm(net.Q)
    return {"theta": out.reshape(net.nl, net.ny, net.nx), "iterations": count[0], "converged": info == 0, "residual": float(res), "seconds": time.perf_counter() - t0}
