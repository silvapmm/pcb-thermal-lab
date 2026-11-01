#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file review_refs.py
@brief The reviewer's own references, written independently of `sheets2d` and `layered3d` (numpy and scipy only, nothing of the program).
@details Three solvers, all with a uniform 1 W source on the top copper and insulated edges:
         * `axisym_3d`      the unit cell of a via lattice as its equal-area disc (Wigner-Seitz cell) in (r, z) finite volumes, with the real barrel: the plating annulus
                            inside the drill radius, the fill core (or nothing for an open barrel), the copper planes, the FR-4 gaps and the film under the bottom copper;
         * `axisym_layered` the same disc in the layered idealisation (one radial sheet per copper layer, the dielectric coupling per area, the film on the last sheet),
                            the barrel conductance spread uniformly over the drill disc (the sink of target radius exp(-1/4) r_v);
         * `cartesian_layered` the layered idealisation on a square board of any layout (five-point stencil), barrels spread over the drill disc by 8 x 8 sub-sampling.
         Each returns the maximum (and, for the discs, the area mean) of the top-copper rise, so that the via effect E = T(no via) - T(via) can be read on the maximum,
         as the program reports it, or on the mean, as the one-cell closed form computes it.
"""

import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spl


def _assemble(n, rows, cols, vals, diag):
    """!
    @brief Sparse matrix from off-diagonal triplets and a diagonal.
    @param n Size.
    @param rows Row indices (array).
    @param cols Column indices (array).
    @param vals Off-diagonal values (array).
    @param diag Diagonal (array of length n).
    @return scipy.sparse.csc_matrix.
    """
    r = np.concatenate([rows, np.arange(n)])
    c = np.concatenate([cols, np.arange(n)])
    v = np.concatenate([vals, diag])
    return sp.csc_matrix((v, (r, c)), shape=(n, n))


def axisym_3d(layers, t_cu, gap, R, r_v, plating, k_fill, via=True, k_cu=385.0, k_fr4=0.3, h_bot=200.0, n_out=120, n_cu=3, n_gap=16):
    """!
    @brief Rise of the top copper of a disc cell of a via lattice, 3D axisymmetric finite volumes with the real barrel.
    @param layers Copper layers.
    @param t_cu Copper thickness in m.
    @param gap Dielectric gap in m (equal gaps).
    @param R Radius of the cell in m.
    @param r_v Drill radius in m (the plating is inside it).
    @param plating Plating thickness in m.
    @param k_fill Conductivity of the core in W/mK (0: open barrel, no material).
    @param via False: the board without the hole and barrel.
    @param k_cu Copper conductivity in W/mK.
    @param k_fr4 FR-4 conductivity in W/mK (isotropic).
    @param h_bot Film under the bottom copper in W/m2K.
    @param n_out Radial cells outside the drill (geometric).
    @param n_cu Axial cells per copper layer.
    @param n_gap Axial cells per gap.
    @return tuple (maximum, area mean) of the top rise in K for 1 W.
    """
    r_in = r_v - plating
    # Radial faces: the core, the plating, then a geometric grading to the rim
    rf = np.concatenate([np.linspace(0.0, r_in, 7), np.linspace(r_in, r_v, 5)[1:], r_v * (R / r_v) ** (np.arange(1, n_out + 1) / n_out)])
    zf = [0.0]
    for l in range(layers):
        zf += list(zf[-1] + t_cu * np.arange(1, n_cu + 1) / n_cu)
        if l < layers - 1:
            zf += list(zf[-1] + gap * np.arange(1, n_gap + 1) / n_gap)
    zf = np.array(zf)
    nr, nz = len(rf) - 1, len(zf) - 1
    rc = 0.5 * (rf[1:] + rf[:-1])
    zc = 0.5 * (zf[1:] + zf[:-1])
    is_cu = np.zeros(nz, bool)
    z0 = 0.0
    for l in range(layers):
        is_cu |= (zc > z0) & (zc < z0 + t_cu)
        z0 += t_cu + gap
    k = np.where(is_cu[:, None], k_cu, k_fr4) * np.ones((nz, nr))
    if via:
        k[:, rc < r_in] = max(k_fill, 1e-9)                     # an open core carries (almost) nothing
        k[:, (rc > r_in) & (rc < r_v)] = k_cu                   # the plating runs through the whole thickness
    dz = np.diff(zf)
    idx = np.arange(nz * nr).reshape(nz, nr)
    # Radial conductances: two half cells in series, logarithmic
    ra = np.log(rf[1:-1] / rc[:-1])[None, :] / (2 * math.pi * k[:, :-1] * dz[:, None])
    rb = np.log(rc[1:] / rf[1:-1])[None, :] / (2 * math.pi * k[:, 1:] * dz[:, None])
    g_r = 1.0 / (ra + rb)
    area = math.pi * (rf[1:] ** 2 - rf[:-1] ** 2)
    g_z = area[None, :] / (0.5 * dz[:-1, None] / k[:-1] + 0.5 * dz[1:, None] / k[1:])
    rows = np.concatenate([idx[:, :-1].ravel(), idx[:-1, :].ravel()])
    cols = np.concatenate([idx[:, 1:].ravel(), idx[1:, :].ravel()])
    g = np.concatenate([g_r.ravel(), g_z.ravel()])
    diag = np.zeros(nz * nr)
    np.add.at(diag, rows, g)
    np.add.at(diag, cols, g)
    solid_b = k[-1] > 1e-6
    diag[idx[-1]] += np.where(solid_b, area / (1.0 / h_bot + 0.5 * dz[-1] / k[-1]), 0.0)
    K = _assemble(nz * nr, np.concatenate([rows, cols]), np.concatenate([cols, rows]), -np.concatenate([g, g]), diag)
    solid = k[0] > 1e-6
    w = area * solid
    Q = np.zeros(nz * nr)
    Q[idx[0]] = w / w.sum()
    top = spl.spsolve(K, Q).reshape(nz, nr)[0]
    return float(top[solid].max()), float((top * w).sum() / w.sum())


def axisym_layered(S, gz_area, h_bot, R, r_v, gv, via=True, n=400):
    """!
    @brief Rise of the top sheet of a disc cell in the layered idealisation, barrel spread uniformly over the drill disc.
    @param S (L,) sheet conductances in W/K.
    @param gz_area (L-1,) dielectric conductance per area in W/m2K.
    @param h_bot Film under the last sheet in W/m2K.
    @param R Cell radius in m.
    @param r_v Drill radius in m.
    @param gv (L-1,) barrel conductance of the via across each gap in W/K.
    @param via False: no via (the uniform one-dimensional solution).
    @param n Radial cells outside the drill.
    @return tuple (maximum, area mean) of the top rise in K for 1 W.
    """
    L = len(S)
    rf = np.concatenate([np.linspace(0.0, r_v, 41), r_v * (R / r_v) ** (np.arange(1, n + 1) / n)])
    nr = len(rf) - 1
    rc = np.where(rf[:-1] > 0, np.sqrt(rf[:-1] * rf[1:]), 0.5 * rf[1:])
    area = math.pi * (rf[1:] ** 2 - rf[:-1] ** 2)
    K = sp.lil_matrix((L * nr, L * nr))

    def link(a, b, g):
        # Conductance g between nodes a and b
        K[a, a] += g
        K[b, b] += g
        K[a, b] -= g
        K[b, a] -= g
    for l in range(L):
        for j in range(nr - 1):
            r1 = math.log(rf[j + 1] / rc[j]) / (2 * math.pi * S[l])
            r2 = math.log(rc[j + 1] / rf[j + 1]) / (2 * math.pi * S[l])
            link(l * nr + j, l * nr + j + 1, 1.0 / (r1 + r2))
        if l < L - 1:
            for j in range(nr):
                g = gz_area[l] * area[j]
                if via and rf[j + 1] <= r_v * (1 + 1e-12):
                    g += gv[l] * area[j] / (math.pi * r_v ** 2)
                link(l * nr + j, (l + 1) * nr + j, g)
    for j in range(nr):
        K[(L - 1) * nr + j, (L - 1) * nr + j] += h_bot * area[j]
    Q = np.zeros(L * nr)
    Q[:nr] = area / area.sum()
    top = spl.spsolve(K.tocsc(), Q)[:nr]
    return float(top.max()), float((top * area).sum() / area.sum())


def cartesian_layered(width, S, gz_area, h_top, h_bot, rect, power, vias, dx):
    """!
    @brief Maximum rise of the top sheet of a square board in the layered idealisation (five-point stencil, insulated edges).
    @param width Board side in m.
    @param S (L,) sheet conductances in W/K.
    @param gz_area (L-1,) dielectric conductance per area in W/m2K.
    @param h_top Film on the first sheet in W/m2K.
    @param h_bot Film on the last sheet in W/m2K.
    @param rect Source rectangle (x0, y0, x1, y1) in m on the first sheet (its edges on the grid).
    @param power Power in W.
    @param vias List of (x, y, r_v, gv) with gv the (L-1,) barrel conductances in W/K, spread over the drill disc.
    @param dx Cell size in m.
    @return float Maximum rise of the top sheet in K.
    """
    L = len(S)
    n = int(round(width / dx))
    N = n * n
    idx = np.arange(N).reshape(n, n)
    rows, cols, vals = [], [], []
    for l in range(L):
        o = l * N
        for a, b in ((idx[:, :-1], idx[:, 1:]), (idx[:-1, :], idx[1:, :])):
            rows.append(o + a.ravel())
            cols.append(o + b.ravel())
            vals.append(np.full(a.size, S[l]))
    gzc = np.zeros((max(L - 1, 0), n, n))
    for l in range(L - 1):
        gzc[l] = gz_area[l] * dx * dx
    sub = (np.arange(8) + 0.5) / 8
    for (x, y, rv, gv) in vias:
        for i in range(max(int((y - rv) / dx) - 1, 0), min(int((y + rv) / dx) + 2, n)):
            for j in range(max(int((x - rv) / dx) - 1, 0), min(int((x + rv) / dx) + 2, n)):
                px = j * dx + sub[None, :] * dx
                py = i * dx + sub[:, None] * dx
                f = float(((px - x) ** 2 + (py - y) ** 2 <= rv * rv).mean())
                if f > 0:
                    gzc[:, i, j] += np.asarray(gv) * f * dx * dx / (math.pi * rv * rv)
    for l in range(L - 1):
        rows.append(l * N + idx.ravel())
        cols.append((l + 1) * N + idx.ravel())
        vals.append(gzc[l].ravel())
    rows, cols, vals = np.concatenate(rows), np.concatenate(cols), np.concatenate(vals)
    diag = np.zeros(L * N)
    np.add.at(diag, rows, vals)
    np.add.at(diag, cols, vals)
    diag[:N] += h_top * dx * dx
    diag[(L - 1) * N:] += h_bot * dx * dx
    K = _assemble(L * N, np.concatenate([rows, cols]), np.concatenate([cols, rows]), -np.concatenate([vals, vals]), diag)
    x0, y0, x1, y1 = rect
    j0, j1, i0, i1 = int(round(x0 / dx)), int(round(x1 / dx)), int(round(y0 / dx)), int(round(y1 / dx))
    Q = np.zeros(L * N)
    q = np.zeros((n, n))
    q[i0:i1, j0:j1] = power / ((i1 - i0) * (j1 - j0))
    Q[:N] = q.ravel()
    return float(spl.spsolve(K, Q)[:N].max())


def krogh_disc(S, R, a):
    """!
    @brief Mean-to-wall resistance of a disc cell with a uniform source and a central sink (the reviewer's own copy, from the profile integrated by hand).
    @param S Sheet conductance in W/K.
    @param R Cell radius in m.
    @param a Sink radius in m.
    @return float Resistance in K/W.
    """
    b2 = (R / a) ** 2
    return (b2 * b2 * math.log(R / a) / (b2 - 1) ** 2 - b2 / (2 * (b2 - 1)) - 0.25) / (2 * math.pi * S)
