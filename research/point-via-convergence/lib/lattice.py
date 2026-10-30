#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file lattice.py
@brief The potential kernel of the five-point stencil on a square lattice: the exact meaning of Peaceman's equivalent radius of a point sink.
@details A unit sink at one node of a square lattice of conductance S between neighbours gives, relative to the sink node, the potential
         phi(0) - phi(x) = a(x) / (4 S), where a is the potential kernel of the simple random walk on Z^2: a(1,0) = 1, a(n,n) = (4/pi) sum_{k<=n} 1/(2k-1)
         and, far away, a(x) = (2/pi) ln|x| + kappa + O(|x|^-2) with kappa = (2 gamma + 3 ln 2) / pi (Fukai and Uchiyama 1996, Kozma and Schreiber 2004; the
         constant is checked numerically here, not taken on trust).
         The continuum point sink in a sheet of conductance S has phi(0) - phi(r) = ln(r / r_eq) / (2 pi S) outside a hole of radius r_eq, so the node of the lattice
         sink behaves as a hole of radius r_eq = exp(-pi kappa / 2) dx = exp(-(gamma + 1.5 ln 2)) dx = 0.19851 dx (the "0.198" of the program documents).
         Peaceman's own argument (all four neighbours equal, Darcy flow between the neighbour ring and the equivalent radius) gives exp(-pi/2) dx = 0.20788 dx.
         The weights of a distributed sink (sum 1) have an effective radius ln r_eff = (pi / 2) (E - kappa), with E = sum_ab w_a w_b a(a - b) (the mean potential seen by the
         distribution, see `effective_radius`).
@note Independent of the program: imports only numpy and scipy.
"""

import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

EULER_GAMMA = 0.5772156649015329
KAPPA = (2.0 * EULER_GAMMA + 3.0 * math.log(2.0)) / math.pi          # asymptotic constant of the potential kernel
R_EQ_EXACT = math.exp(-math.pi * KAPPA / 2.0)                          # equivalent radius of a point sink in units of the lattice spacing (0.19851)
R_EQ_PEACEMAN = math.exp(-math.pi / 2.0)                               # Peaceman's radial-flow argument (0.20788)


def kernel_table(n=12):
    """!
    @brief Exact values of the potential kernel a(x, y) for 0 <= x, y <= n by the harmonic recurrence from the diagonal.
    @param n Largest coordinate.
    @return numpy.ndarray of shape (n + 1, n + 1), symmetric, a[0, 0] = 0.
    @note The forward recurrence amplifies rounding errors by a factor of about 6 per step; n = 12 keeps them below 1e-6 (checked against the finite solve in the tests).
    """
    a = np.zeros((n + 2, n + 2))
    for k in range(1, n + 2):
        a[k, k] = 4.0 / math.pi * sum(1.0 / (2 * j - 1) for j in range(1, k + 1))    # exact diagonal values
    a[1, 0] = a[0, 1] = 1.0
    for m in range(1, n + 1):
        # a(m+1, m) from the harmonic equation at the diagonal node (m, m): 4 a(m,m) = 2 a(m+1,m) + 2 a(m,m-1)
        a[m + 1, m] = a[m, m + 1] = 2.0 * a[m, m] - a[m, m - 1]
        for y in range(m - 1, -1, -1):
            # harmonic at (m, y): a(m+1, y) = 4 a(m, y) - a(m-1, y) - a(m, y+1) - a(m, y-1), with a(m, -1) = a(m, 1)
            ym = a[m, y - 1] if y > 0 else a[m, 1]
            a[m + 1, y] = a[y, m + 1] = 4.0 * a[m, y] - a[m - 1, y] - a[m, y + 1] - ym
    return a[:n + 1, :n + 1]


_TABLE = kernel_table(12)


def a_of(dx, dy):
    """!
    @brief Potential kernel at the integer offset (dx, dy), exact in the table and asymptotic beyond it.
    @param dx Offset in cells along x (integer or integer array).
    @param dy Offset in cells along y.
    @return float or numpy.ndarray The kernel value.
    """
    x, y = np.abs(np.asarray(dx)), np.abs(np.asarray(dy))
    n = _TABLE.shape[0] - 1
    inside = (x <= n) & (y <= n)
    r = np.hypot(x, y)
    far = (2.0 / math.pi) * np.log(np.maximum(r, 1.0)) + KAPPA        # error O(r^-2): below 1e-3 beyond r = 12
    near = _TABLE[np.minimum(x, n), np.minimum(y, n)]
    return np.where(inside, near, far)


def point_sink_solve(half_width=300, spacing=1.0, probes=((20, 0), (20, 20), (40, 0))):
    """!
    @brief Solve a unit point sink on a finite square lattice (Dirichlet zero on the border) and read the equivalent radius from the potential differences.
    @param half_width Number of nodes from the sink to the border.
    @param spacing Lattice spacing (the result is returned in units of it).
    @param probes Offsets in cells at which phi(0) - phi(x) is read.
    @return dict with 'r_eq' (mean over the probes of the radius that fits phi(0) - phi(x) = ln(|x| / r_eq) / (2 pi), in lattice units), 'per_probe' list and 'residual'.
    @note The border value cancels in phi(0) - phi(x); the remaining error is O((|x| / half_width)^2).
    """
    n = 2 * half_width + 1
    idx = np.arange(n * n).reshape(n, n)
    rows, cols, vals = [], [], []
    diag = np.zeros(n * n)
    for a, b in ((idx[:, :-1], idx[:, 1:]), (idx[:-1, :], idx[1:, :])):
        a, b = a.ravel(), b.ravel()
        rows += [a, b]
        cols += [b, a]
        vals += [-np.ones(a.size), -np.ones(a.size)]
        np.add.at(diag, a, 1.0)
        np.add.at(diag, b, 1.0)
    border = np.zeros((n, n), bool)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    diag[border.ravel()] += 1.0                                          # a fixed-temperature ring one conductance beyond the last node
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n * n, n * n)).tocsr() + sp.diags(diag)
    q = np.zeros(n * n)
    q[idx[half_width, half_width]] = 1.0
    phi = spla.spsolve(K.tocsc(), q).reshape(n, n)
    out = []
    for (px, py) in probes:
        d = phi[half_width, half_width] - phi[half_width + py, half_width + px]
        r = math.hypot(px, py)
        out.append(r * math.exp(-2.0 * math.pi * d))                       # ln(r / r_eq) = 2 pi d
    res = float(np.linalg.norm(K @ phi.ravel() - q))
    return {"r_eq": float(np.mean(out)) * spacing, "per_probe": [o * spacing for o in out], "residual": res}


def effective_radius(offsets, weights):
    """!
    @brief Effective radius of a distributed sink (in lattice units) from the pair energy E = sum w_a w_b a(a - b).
    @param offsets Integer array (m, 2) of the cell offsets that carry weight.
    @param weights Array (m,) of non-negative weights.
    @return float Radius r_eff such that the mean potential of the distribution equals that of a hole of radius r_eff: ln r_eff = (pi / 2)(E - kappa).
    """
    o = np.asarray(offsets, dtype=int)
    w = np.asarray(weights, dtype=float)
    w = w / w.sum()
    d = o[:, None, :] - o[None, :, :]
    e = float(w @ a_of(d[..., 0], d[..., 1]) @ w)
    return math.exp(math.pi / 2.0 * (e - KAPPA))
