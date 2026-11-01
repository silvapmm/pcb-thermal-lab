#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file young.py
@brief Estimates of the Jacobi spectral radius rho_J and of Young's optimum relaxation factor of the red-black SOR, and the matrices on which they are tested.
@details Setting of the study S3. For a symmetric positive definite K = D - N (D its diagonal, N the off-diagonal part) whose graph is two-colourable (the six-neighbour
         stencil of the program is, by the parity of l + i + j) the Jacobi matrix J = D^-1 N is similar to the symmetric J_s = D^-1/2 N D^-1/2 = I - A_s, A_s = D^-1/2 K D^-1/2,
         whose eigenvalues come in pairs +-mu. The red-black ordering is consistently ordered, so the SOR iteration matrix has the eigenvalues given by Young's relation
         (lambda + omega - 1)^2 = lambda omega^2 mu^2 and the optimum is omega_opt = 2 / (1 + sqrt(1 - rho_J^2)), rho_J = max mu = 1 - lambda_min(A_s) (Saad 2003, section 4.2.5,
         Theorem 4.16 and eq. 4.47; Young 1971 not obtained, see the README).
         Estimators (each returns rho and the number of products with K that it spent):
         * `rho_rayleigh`: the Rayleigh quotient of A_s with the trial vector D^1/2 1, rho >= 1 - (1^T K 1) / (1^T D 1): one product, a LOWER bound of rho_J (min-max), so the
           omega that follows is on the safe side (below the optimum);
         * `rho_closed_form`: the same number from the conductance arrays alone (sum of the ambient conductances over the sum of the diagonal), no product with K;
         * `rho_lanczos`: k steps of the Lanczos process on J_s started at the trial vector above (Ritz values are lower bounds of the largest eigenvalue and rise with k:
           Saad, Large Eigenvalue Problems, 2nd ed., section 6.6, Theorem 6.4, eq. 6.42);
         * `rho_power`: the power method (Saad, op. cit., Algorithm 4.1, Theorem 4.1) on (I + J_s) / 2, because the plain power method on J_s does not converge: the spectrum is
           symmetric (+mu and -mu have the same modulus);
         * `rho_exact`: dense eigenvalues (n <= 3000) or ARPACK with a tight tolerance;
         * `adaptive_omega`: the estimate from the decay of the SOR itself (no extra product): after s sweeps at omega_0 the ratio of successive corrections is the dominant
           eigenvalue lambda of the SOR matrix, and Young's relation gives mu = (lambda + omega_0 - 1) / (omega_0 sqrt(lambda)) (valid while omega_0 < omega_opt).
         Also the textbook test matrices (`poisson_matrix`: 5-point Laplacian with fixed edges, rho_J = cos(pi / (n + 1)); `torus_matrix`: periodic plate with a uniform loss, rho_J
         = 4 g / (4 g + a)), a plate with the stencil of the program (`plate_matrix`), `rho_sor` (Young's relation solved for lambda), and `sor_iteration_radius` (the spectral
         radius of the SOR iteration matrix computed from its dense eigenvalues: independent of Young's relation).
"""

import math
import time

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


# --------------------------------------------------------------------------------------------------------------------------------------------------------------
# Matrices
# --------------------------------------------------------------------------------------------------------------------------------------------------------------
def poisson_matrix(n):
    """!
    @brief The 5-point Laplacian on an n x n grid with fixed (zero) edges: the model problem of the SOR theory.
    @param n Interior points per side.
    @return scipy.sparse.csr_matrix of order n*n (diagonal 4, neighbours -1).
    """
    t = sp.diags([-np.ones(n - 1), 2.0 * np.ones(n), -np.ones(n - 1)], [-1, 0, 1])
    i = sp.identity(n)
    return (sp.kron(i, t) + sp.kron(t, i)).tocsr()


def torus_matrix(nx, ny, g=1.0, a=0.01):
    """!
    @brief A periodic plate (a torus, even sizes) with the uniform conductance g between neighbours and a uniform loss a to the ambient in every cell.
    @param nx Cells along x (even).
    @param ny Cells along y (even).
    @param g Conductance between neighbours in W/K.
    @param a Conductance of every cell to the ambient in W/K.
    @return scipy.sparse.csr_matrix; the Jacobi eigenvalues are 2 g (cos(2 pi p / nx) + cos(2 pi q / ny)) / (4 g + a) and rho_J = 4 g / (4 g + a).
    @throws ValueError If a size is odd (the graph would not be two-colourable) or smaller than 3.
    """
    if nx % 2 or ny % 2 or nx < 4 or ny < 4:
        raise ValueError("the torus needs even sizes of at least 4")
    ring = lambda n: sp.diags([-np.ones(n - 1), 2.0 * np.ones(n), -np.ones(n - 1)], [-1, 0, 1]).tolil()   # noqa: E731
    rx, ry = ring(nx), ring(ny)
    rx[0, nx - 1] = rx[nx - 1, 0] = -1.0
    ry[0, ny - 1] = ry[ny - 1, 0] = -1.0
    return (g * (sp.kron(sp.identity(ny), rx.tocsr()) + sp.kron(ry.tocsr(), sp.identity(nx))) + a * sp.identity(nx * ny)).tocsr()


def plate_matrix(nl, ny, nx, gx, gy, gz, g_amb, extra_diag=None):
    """!
    @brief The matrix of a layered plate with the stencil of the program: six neighbours, insulated edges (a missing neighbour adds nothing to the diagonal) and a loss to the ambient.
    @param nl Layers.
    @param ny Cells along y.
    @param nx Cells along x.
    @param gx Conductance between x-neighbours in W/K: scalar or array of shape (nl, ny, nx - 1).
    @param gy Conductance between y-neighbours: scalar or array (nl, ny - 1, nx).
    @param gz Conductance between consecutive layers: scalar or array (nl - 1, ny, nx).
    @param g_amb Conductance of every cell to the ambient: scalar or array (nl, ny, nx).
    @param extra_diag Optional array (nl, ny, nx) added to the diagonal (a pinned cell, a via leak).
    @return scipy.sparse.csr_matrix of order nl*ny*nx.
    """
    idx = np.arange(nl * ny * nx).reshape(nl, ny, nx)
    gx = np.broadcast_to(np.asarray(gx, float), (nl, ny, max(nx - 1, 0)))
    gy = np.broadcast_to(np.asarray(gy, float), (nl, max(ny - 1, 0), nx))
    gz = np.broadcast_to(np.asarray(gz, float), (max(nl - 1, 0), ny, nx))
    rows, cols, vals = [], [], []
    diag = np.broadcast_to(np.asarray(g_amb, float), (nl, ny, nx)).copy()
    if extra_diag is not None:
        diag = diag + extra_diag
    for a, b, g in ((idx[:, :, :-1], idx[:, :, 1:], gx), (idx[:, :-1, :], idx[:, 1:, :], gy), (idx[:-1], idx[1:], gz)):
        if a.size == 0:
            continue
        a, b, g = a.ravel(), b.ravel(), np.asarray(g, float).ravel()
        rows += [a, b]; cols += [b, a]; vals += [-g, -g]
        np.add.at(diag.reshape(-1), a, g)
        np.add.at(diag.reshape(-1), b, g)
    rows.append(idx.ravel()); cols.append(idx.ravel()); vals.append(diag.ravel())
    n = nl * ny * nx
    return sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n))


# --------------------------------------------------------------------------------------------------------------------------------------------------------------
# Operators and the textbook relations
# --------------------------------------------------------------------------------------------------------------------------------------------------------------
def jacobi_symmetric(K):
    """!
    @brief The symmetric Jacobi operator J_s = I - D^-1/2 K D^-1/2 of a matrix and the vector D^1/2 1 (the trial vector of the Rayleigh quotient).
    @param K Sparse symmetric positive definite matrix.
    @return Tuple (matvec, n, sqrt_diag, counter): matvec(x) applies J_s and increments counter[0].
    """
    d = np.asarray(K.diagonal(), float)
    s = 1.0 / np.sqrt(d)
    Kc = K.tocsr()
    counter = [0]

    def matvec(x):
        counter[0] += 1
        return x - s * (Kc @ (s * x))

    return matvec, K.shape[0], np.sqrt(d), counter


def omega_young(rho):
    """!
    @brief Young's optimum relaxation factor for a Jacobi spectral radius.
    @param rho Spectral radius of the Jacobi matrix, 0 <= rho < 1.
    @return float 2 / (1 + sqrt(1 - rho^2)).
    """
    return 2.0 / (1.0 + math.sqrt(max(1.0 - rho * rho, 0.0)))


def omega_program(nx, ny):
    """!
    @brief The relaxation factor of the program's `Network.solve_sor`: 2 / (1 + sin(pi / max(nx, ny))).
    @param nx Cells along x.
    @param ny Cells along y.
    @return float.
    """
    return 2.0 / (1.0 + math.sin(math.pi / max(nx, ny)))


def rho_from_omega_young(omega):
    """!
    @brief The Jacobi radius for which a given omega is Young's optimum (inverse of `omega_young`).
    @param omega Relaxation factor in (1, 2).
    @return float rho_J = 2 sqrt(omega - 1) / omega.
    """
    return 2.0 * math.sqrt(omega - 1.0) / omega


def rho_sor(omega, mu):
    """!
    @brief Spectral radius of the SOR iteration matrix of a consistently ordered matrix from the Jacobi radius mu (Young's relation solved for the dominant lambda).
    @param omega Relaxation factor.
    @param mu Jacobi spectral radius.
    @return float: ((omega mu + sqrt(omega^2 mu^2 - 4 (omega - 1))) / 2)^2 below the optimum, omega - 1 above it.
    """
    disc = omega * omega * mu * mu - 4.0 * (omega - 1.0)
    if disc <= 0.0:
        return abs(omega - 1.0)
    return ((omega * mu + math.sqrt(disc)) / 2.0) ** 2


def sweeps_predicted(omega, mu, reduction=1e-9):
    """!
    @brief Number of sweeps that the asymptotic rate predicts for a reduction of the error (a guide: the measured count also has a pre-asymptotic part).
    @param omega Relaxation factor.
    @param mu Jacobi spectral radius.
    @param reduction Factor by which the error is reduced.
    @return float ln(reduction) / ln(rho_sor).
    """
    r = rho_sor(omega, mu)
    return math.log(reduction) / math.log(r) if 0.0 < r < 1.0 else float("inf")


def sor_iteration_radius(K, omega):
    """!
    @brief Spectral radius of the SOR iteration matrix (D + omega L)^-1 ((1 - omega) D - omega U) from its dense eigenvalues, natural ordering (independent of Young's relation).
    @param K Symmetric matrix (order up to a few hundred).
    @param omega Relaxation factor.
    @return float.
    """
    Kd = K.toarray() if sp.issparse(K) else np.asarray(K, float)
    D = np.diag(np.diag(Kd))
    L = np.tril(Kd, -1)
    U = np.triu(Kd, 1)
    M = np.linalg.solve(D + omega * L, (1.0 - omega) * D - omega * U)
    return float(np.max(np.abs(np.linalg.eigvals(M))))


# --------------------------------------------------------------------------------------------------------------------------------------------------------------
# Estimators of rho_J
# --------------------------------------------------------------------------------------------------------------------------------------------------------------
def rho_exact(K, dense_limit=3000):
    """!
    @brief The Jacobi spectral radius by eigenvalues (the reference of the study).
    @param K Sparse symmetric positive definite matrix.
    @param dense_limit Order up to which dense `eigvalsh` is used; above it ARPACK with a tight tolerance.
    @return float max |eig(J_s)|.
    """
    mv, n, _, _ = jacobi_symmetric(K)
    if n <= dense_limit:
        d = 1.0 / np.sqrt(K.diagonal())
        a = (sp.diags(d) @ K @ sp.diags(d)).toarray()
        w = np.linalg.eigvalsh(a)
        return float(max(abs(1.0 - w[0]), abs(1.0 - w[-1])))
    op = spla.LinearOperator((n, n), matvec=mv, dtype=float)
    w = spla.eigsh(op, k=2, which="LA", tol=1e-13, ncv=60, return_eigenvectors=False)
    return float(np.max(w))


def rho_rayleigh(K, linked_only=True):
    """!
    @brief The Rayleigh-quotient lower bound of rho_J with the trial vector D^1/2 1: 1 - (1^T K 1) / (1^T D 1).
    @details Nodes that have no link (the cells off a board with an outline are pinned to the ambient and decoupled) are eigenvectors of the Jacobi matrix with mu = 0: they dilute
             the quotient (the loss of the pins is counted as loss of the board) and the bound collapses (omega 1.009 on a round board in `study_s3_boards.py`). They are left out of
             the sums when `linked_only` is true (found by that study; regression test `test_rayleigh_ignores_decoupled_nodes`).
    @param K Sparse symmetric positive definite matrix.
    @param linked_only True: sum only over the nodes that have at least one off-diagonal entry.
    @return Tuple (rho, products): one product with K.
    """
    d = np.asarray(K.diagonal(), float)
    one = np.ones(K.shape[0])
    if linked_only:
        off = np.asarray(abs(K - sp.diags(d)).sum(axis=1)).ravel()
        one = (off > 0).astype(float)
    return float(1.0 - (one @ (K @ one)) / (one @ d)), 1


def rho_closed_form(g_links_total, g_amb_total, diag_sum=None):
    """!
    @brief The same bound from conductance totals, no product with K: each link is counted twice in the diagonal, so sum(D) = 2 G_links + G_amb (+ extra diagonal).
    @param g_links_total Sum of the conductances of all links of the stencil (and of the via couplings) in W/K.
    @param g_amb_total Sum of the conductances to the ambient (faces, edges, pinned cells) in W/K.
    @param diag_sum Sum of the diagonal when it is known (overrides the first two).
    @return float 1 - G_amb / sum(D).
    """
    s = diag_sum if diag_sum is not None else 2.0 * g_links_total + g_amb_total
    return 1.0 - g_amb_total / s


def lanczos_top(matvec, v0, k):
    """!
    @brief k steps of the symmetric Lanczos process with full reorthogonalisation; the largest Ritz value after each step.
    @param matvec Function x -> J x of a symmetric operator.
    @param v0 Start vector.
    @param k Number of steps.
    @return list of the largest Ritz values after steps 1..k (non-decreasing; each is a lower bound of the largest eigenvalue).
    """
    n = len(v0)
    V = np.zeros((k + 1, n))
    alpha, beta = [], []
    V[0] = v0 / np.linalg.norm(v0)
    out = []
    for j in range(k):
        w = matvec(V[j])
        a = float(w @ V[j])
        w = w - a * V[j] - (beta[-1] * V[j - 1] if j else 0.0)
        w -= V[: j + 1].T @ (V[: j + 1] @ w)                                  # full reorthogonalisation: cheap for k <= 60
        b = float(np.linalg.norm(w))
        alpha.append(a)
        T = np.diag(alpha) + (np.diag(beta, 1) + np.diag(beta, -1) if beta else 0.0)
        out.append(float(np.linalg.eigvalsh(T)[-1]))
        if b < 1e-14:
            break
        beta.append(b)
        V[j + 1] = w / b
    return out


def rho_lanczos(K, k, start="uniform", seed=0):
    """!
    @brief The Jacobi radius from k Lanczos steps on J_s.
    @param K Sparse symmetric positive definite matrix.
    @param k Steps (products with K).
    @param start "uniform" (the trial vector D^1/2 1, which carries almost all of the dominant mode of a plate) or "random".
    @param seed Seed of the random start.
    @return Tuple (rho, products, history) with history the Ritz value after every step.
    """
    mv, n, sd, cnt = jacobi_symmetric(K)
    v0 = sd.copy() if start == "uniform" else np.random.default_rng(seed).standard_normal(n)
    hist = lanczos_top(mv, v0, k)
    return hist[-1], cnt[0], hist


def rho_power(K, m, start="uniform", seed=0):
    """!
    @brief The Jacobi radius from m steps of the power method on (I + J_s) / 2 (spectrum in [0, 1], dominant eigenvalue (1 + rho) / 2), Rayleigh quotient at the end.
    @param K Sparse symmetric positive definite matrix.
    @param m Steps (products with K).
    @param start "uniform" or "random".
    @param seed Seed of the random start.
    @return Tuple (rho, products).
    """
    mv, n, sd, cnt = jacobi_symmetric(K)
    x = sd.copy() if start == "uniform" else np.random.default_rng(seed).standard_normal(n)
    x /= np.linalg.norm(x)
    q = 0.0
    for _ in range(m):
        y = 0.5 * (x + mv(x))
        q = float(x @ y)
        x = y / np.linalg.norm(y)
    return 2.0 * q - 1.0, cnt[0]


def adaptive_omega(step_norms, omega0):
    """!
    @brief Young's omega from the decay of the SOR corrections themselves (the Hageman-Young idea), no extra product with K.
    @param step_norms Norms of the corrections of consecutive sweeps (at least three, from a window where the decay has become geometric).
    @param omega0 Relaxation factor used in those sweeps (must be below the optimum, otherwise the decay is omega0 - 1 and says nothing about mu).
    @return Tuple (omega_new, mu_hat, lam_hat); omega_new = omega0 when the decay is not usable.
    """
    r = np.asarray(step_norms, float)
    lam = float((r[-1] / r[0]) ** (1.0 / (len(r) - 1)))
    if lam <= abs(omega0 - 1.0) * 1.02 or lam >= 1.0:
        return omega0, float("nan"), lam
    mu = (lam + omega0 - 1.0) / (omega0 * math.sqrt(lam))
    if not 0.0 < mu < 1.0:
        return omega0, mu, lam
    return omega_young(mu), mu, lam


def parity_colour(nl, ny, nx):
    """!
    @brief The red-black colouring of a layered grid: parity of l + i + j (the stencil couples only cells of opposite colour).
    @param nl Layers.
    @param ny Cells along y.
    @param nx Cells along x.
    @return Boolean array of length nl*ny*nx (True = red).
    """
    li, ii, jj = np.indices((nl, ny, nx))
    return ((li + ii + jj) % 2 == 0).ravel()


def sor_rb_matrix(K, b, colour, omega, tol=1e-9, max_iter=60000, check=10):
    """!
    @brief Red-black SOR on any sparse matrix with a two-colouring (an independent implementation: nothing of the program is used).
    @param K Sparse symmetric positive definite matrix whose off-diagonal entries join cells of opposite colour only.
    @param b Right-hand side.
    @param colour Boolean array, True = red.
    @param omega Relaxation factor.
    @param tol Stopping tolerance on |K x - b| / |b|.
    @param max_iter Sweep limit.
    @param check Sweeps between residual evaluations.
    @return Tuple (x, sweeps, converged).
    """
    Kc = K.tocsr()
    d = Kc.diagonal()
    x = np.zeros(K.shape[0])
    bn = max(np.linalg.norm(b), 1e-300)
    masks = (colour, ~colour)
    for it in range(1, max_iter + 1):
        for m in masks:
            r = b - Kc @ x
            x[m] += omega * r[m] / d[m]
        if it % check == 0 and np.linalg.norm(b - Kc @ x) / bn < tol:
            return x, it, True
    return x, max_iter, False


def timed(fn, *args, **kw):
    """!
    @brief Call a function and measure its wall time.
    @param fn Function.
    @param args Positional arguments.
    @param kw Keyword arguments.
    @return Tuple (result, seconds).
    """
    t0 = time.perf_counter()
    r = fn(*args, **kw)
    return r, time.perf_counter() - t0
