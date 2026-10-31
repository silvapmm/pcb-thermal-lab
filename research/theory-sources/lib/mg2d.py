#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file mg2d.py
@brief A two-dimensional geometric multigrid V-cycle (Algorithm 3 of McCormick and Tamstorf, Multigrid primer, arXiv:2605.17828) for the five-point Poisson problem, for topic 16.
@details Dirichlet problem -Laplace(u) = f on the unit square, n x n interior points (n = 2^k - 1), five-point stencil; relaxation is red-black Gauss-Seidel (mu pre-sweeps, nu post-sweeps),
restriction is full weighting, interpolation is bilinear, the coarsest grid (3 x 3) is solved exactly. The per-cycle convergence factor is measured as the ratio of consecutive residual norms.
"""

import numpy as np


def residual(u, f, h):
    """!
    @brief Residual f - A u of the five-point operator with zero Dirichlet boundary.
    @param u Array (n, n) of the iterate.
    @param f Array (n, n) of the right-hand side.
    @param h Mesh size.
    @return Array (n, n) of the residual.
    """
    p = np.pad(u, 1)
    return f - (4.0 * u - p[:-2, 1:-1] - p[2:, 1:-1] - p[1:-1, :-2] - p[1:-1, 2:]) / (h * h)


def smooth(u, f, h, sweeps):
    """!
    @brief Red-black Gauss-Seidel sweeps.
    @param u Array (n, n), updated in place.
    @param f Right-hand side.
    @param h Mesh size.
    @param sweeps Number of full sweeps (red then black).
    @return The updated array.
    """
    n = u.shape[0]
    ii, jj = np.indices((n, n))
    for _ in range(sweeps):
        for colour in (0, 1):
            p = np.pad(u, 1)
            new = 0.25 * (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:] + h * h * f)
            mask = (ii + jj) % 2 == colour
            u[mask] = new[mask]
    return u


def restrict(r):
    """!
    @brief Full-weighting restriction from n to (n - 1) / 2 interior points.
    @param r Fine array.
    @return Coarse array.
    """
    p = np.pad(r, 1)
    c = (4 * p[2:-1:2, 2:-1:2] + 2 * (p[1:-2:2, 2:-1:2] + p[3::2, 2:-1:2] + p[2:-1:2, 1:-2:2] + p[2:-1:2, 3::2])
         + p[1:-2:2, 1:-2:2] + p[1:-2:2, 3::2] + p[3::2, 1:-2:2] + p[3::2, 3::2]) / 16.0
    return c


def prolong(c):
    """!
    @brief Bilinear interpolation from m to 2 m + 1 interior points.
    @param c Coarse array.
    @return Fine array.
    """
    m = c.shape[0]
    n = 2 * m + 1
    f = np.zeros((n, n))
    p = np.pad(c, 1)
    f[1::2, 1::2] = c
    f[0::2, 1::2] = 0.5 * (p[:-1, 1:-1] + p[1:, 1:-1])
    f[1::2, 0::2] = 0.5 * (p[1:-1, :-1] + p[1:-1, 1:])
    f[0::2, 0::2] = 0.25 * (p[:-1, :-1] + p[:-1, 1:] + p[1:, :-1] + p[1:, 1:])
    return f


def vcycle(u, f, h, mu=2, nu=1):
    """!
    @brief One V(mu, nu) cycle.
    @param u Iterate (n, n).
    @param f Right-hand side.
    @param h Mesh size.
    @param mu Pre-smoothing sweeps.
    @param nu Post-smoothing sweeps.
    @return The new iterate.
    """
    n = u.shape[0]
    if n <= 3:                                                   # coarsest grid: direct solve of the small system
        size = n * n
        a = np.zeros((size, size))
        for k in range(size):
            e = np.zeros(size)
            e[k] = 1.0
            a[:, k] = -residual(e.reshape(n, n), np.zeros((n, n)), h).ravel()
        return np.linalg.solve(a, f.ravel()).reshape(n, n)
    u = smooth(u, f, h, mu)
    r = residual(u, f, h)
    e = vcycle(np.zeros(((n - 1) // 2,) * 2), restrict(r), 2 * h, mu, nu)
    u = u + prolong(e)
    return smooth(u, f, h, nu)


def convergence_factors(n, cycles=10, seed=0):
    """!
    @brief Residual reduction factor of every V(2,1) cycle for a random right-hand side.
    @param n Interior points per side (2^k - 1).
    @param cycles Number of cycles.
    @param seed Seed of the random generator.
    @return List of ratios ||r_k|| / ||r_(k-1)||.
    """
    rng = np.random.default_rng(seed)
    h = 1.0 / (n + 1)
    f = rng.standard_normal((n, n))
    u = np.zeros((n, n))
    norms = [np.linalg.norm(residual(u, f, h))]
    for _ in range(cycles):
        u = vcycle(u, f, h)
        norms.append(np.linalg.norm(residual(u, f, h)))
    return [norms[i + 1] / norms[i] for i in range(cycles)]
