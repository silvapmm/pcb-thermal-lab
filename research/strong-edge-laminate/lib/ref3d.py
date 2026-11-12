#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file ref3d.py
@brief Independent 3D finite-volume reference of a small 4-layer board with a cooled side wall (imports nothing of pcbthermal).
@details Half domain (the plane y = W/2 is a symmetry plane, insulated). Every copper layer is one slab of one cell; every FR-4 gap is cut into `n_sub` slabs; the side film
         `h_side` acts on the walls x = 0, x = W and y = 0 of EVERY slab (copper and laminate), as the physical wall does. Optional copper inset: the copper cells within
         `inset` of the walls are FR-4. The via has four representations, to test the sensitivity of the reference to it:
         * `none`   no via;
         * `cyl`    resolved copper cylinder: the conductivity of every cell of the drill disc is mixed by the area share of the disc in the cell (copper through the gap slabs);
         * `link`   copper-to-copper links between the cells of the disc, one per gap, total conductance `gv_gap` given by the caller (the older reference of validation 28);
         * `rim`    like `cyl` but a hollow barrel: copper only in the annulus between `r_in` and the drill radius (plated barrel, core of FR-4 conductivity).
         The cell-centred conduction between cells of different conductivity uses the harmonic mean.
         Returns the hottest top-layer temperature rise, the heat balance (loss through the films over the power) and the unknown count.
"""

import math

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

W = 10e-3                                         # board side in m
KCU, KFR = 385.0, 0.3                             # copper and FR-4 conductivities, W/mK
TCU = 35e-6                                       # copper thickness, m
TOTAL = 1.6e-3                                    # board thickness, m
L = 4                                             # copper layers
GAP = (TOTAL - L * TCU) / (L - 1)                 # dielectric gap, m
HTOP, HBOT = 10.0, 200.0                          # face coefficients, W/m2K
POWER = 0.5                                       # source, W
SRC = (1e-3, 4e-3, 4e-3, 6e-3)                    # source x0 y0 x1 y1 in m


def disc_share(xs, ys, cx, cy, r, dx, sub=8):
    """!
    @brief Area share of a disc in each plan cell (sub x sub supersampling).
    @param xs Cell centres in x (m).
    @param ys Cell centres in y (m).
    @param cx Disc centre x (m).
    @param cy Disc centre y (m).
    @param r Disc radius (m).
    @param dx Cell size (m).
    @param sub Supersampling per side.
    @return numpy.ndarray (ny, nx) of shares in [0, 1].
    """
    off = (np.arange(sub) + 0.5) / sub - 0.5
    share = np.zeros((ys.size, xs.size))
    for oy in off:
        for ox in off:
            share += (((xs[None, :] + ox * dx - cx) ** 2 + (ys[:, None] + oy * dx - cy) ** 2) <= r * r)
    return share / (sub * sub)


def solve(h_side, n_sub, dx, via="none", via_dist=0.16e-3, via_r=0.15e-3, gv_gap=0.0, inset=0.0, r_in=0.0, power=POWER, with_balance=True):
    """!
    @brief Solve the 3D steady state.
    @param h_side Side film coefficient in W/m2K (0: insulated walls).
    @param n_sub Sub-slabs per FR-4 gap.
    @param dx Plan cell in m (divides W/2).
    @param via 'none', 'cyl', 'link' or 'rim' (see the file header).
    @param via_dist Distance of the via centre from the wall x = W in m.
    @param via_r Drill radius in m.
    @param gv_gap Total barrel conductance per gap for 'link' (W/K, whole via).
    @param inset Copper inset from the walls in m (0: the copper reaches the wall).
    @param r_in Inner radius of the copper annulus for 'rim' in m.
    @param power Source power in W (whole board).
    @param with_balance Also compute the heat balance.
    @return dict with tmax (top-layer maximum rise, K), balance (loss / power), n (unknowns).
    """
    nx = int(round(W / dx))
    ny = int(round(W / dx / 2))
    dz, kind = [], []
    for l in range(L):
        dz.append(TCU); kind.append(("cu", l))
        if l < L - 1:
            for _ in range(n_sub):
                dz.append(GAP / n_sub); kind.append(("gap", l))
    nz = len(dz)
    xs = (np.arange(nx) + 0.5) * dx
    ys = (np.arange(ny) + 0.5) * dx
    # conductivity of every cell
    k3 = np.empty((nz, ny, nx))
    cu_mask = np.ones((ny, nx), dtype=bool)
    if inset > 0:
        cu_mask = (xs[None, :] > inset) & (xs[None, :] < W - inset) & (ys[:, None] > inset)
    for z, kd in enumerate(kind):
        k3[z] = (np.where(cu_mask, KCU, KFR)) if kd[0] == "cu" else KFR
    cx, cy = W - via_dist, W / 2
    if via in ("cyl", "rim"):
        share = disc_share(xs, ys, cx, cy, via_r, dx)
        if via == "rim":
            share = np.clip(share - disc_share(xs, ys, cx, cy, r_in, dx), 0.0, 1.0)
        for z in range(nz):
            # parallel mix of copper (the barrel) and the local material by area share
            k3[z] = share * KCU + (1.0 - share) * k3[z]
    idx = np.arange(nz * ny * nx).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(nz * ny * nx)
    gamb = np.zeros(nz * ny * nx)
    rhs = np.zeros(nz * ny * nx)

    def link(a, b, g):
        g = np.broadcast_to(g, a.shape)
        rows.extend([a.ravel(), b.ravel()]); cols.extend([b.ravel(), a.ravel()]); vals.extend([-g.ravel(), -g.ravel()])
        diag[a.ravel()] += g.ravel(); diag[b.ravel()] += g.ravel()    # the indices are unique within one call

    def harm(k1, k2):
        return 2.0 * k1 * k2 / (k1 + k2)

    for z in range(nz):
        kz = k3[z]
        link(idx[z, :, :-1], idx[z, :, 1:], harm(kz[:, :-1], kz[:, 1:]) * dz[z])
        link(idx[z, :-1, :], idx[z, 1:, :], harm(kz[:-1, :], kz[1:, :]) * dz[z])
        if h_side > 0:
            gf = h_side * dz[z] * dx
            for sel, kk in ((idx[z, :, 0], kz[:, 0]), (idx[z, :, -1], kz[:, -1]), (idx[z, 0, :], kz[0, :])):
                gc = kk * dz[z] * 2.0                       # half-cell conduction k (dz dx) / (dx / 2)
                g = 1.0 / (1.0 / gc + 1.0 / gf)
                diag[sel] += g
                gamb[sel] += g
    area = dx * dx
    for z in range(nz - 1):
        r = dz[z] / (2 * k3[z] * area) + dz[z + 1] / (2 * k3[z + 1] * area)
        link(idx[z], idx[z + 1], 1.0 / r)
    gtop = 1.0 / (1.0 / (HTOP * area) + dz[0] / (2 * k3[0] * area))
    gbot = 1.0 / (1.0 / (HBOT * area) + dz[-1] / (2 * k3[-1] * area))
    diag[idx[0].ravel()] += gtop.ravel(); gamb[idx[0].ravel()] += gtop.ravel()
    diag[idx[-1].ravel()] += gbot.ravel(); gamb[idx[-1].ravel()] += gbot.ravel()
    m = (xs[None, :] > SRC[0]) & (xs[None, :] < SRC[2]) & (ys[:, None] > SRC[1]) & (ys[:, None] < SRC[3])
    rhs[idx[0][m]] += 0.5 * power / m.sum()
    if via == "link":
        vm = ((xs[None, :] - cx) ** 2 + (ys[:, None] - cy) ** 2) <= via_r ** 2
        cu_z = [i for i, kd in enumerate(kind) if kd[0] == "cu"]
        for a, b in zip(cu_z[:-1], cu_z[1:]):
            link(idx[a][vm], idx[b][vm], 0.5 * gv_gap / vm.sum())    # half of the via lives in the half domain
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(diag.size,) * 2) + sp.diags(diag)
    lu = spla.splu(A.tocsc(), permc_spec="MMD_AT_PLUS_A", diag_pivot_thresh=0.0, options=dict(SymmetricMode=True))
    T = lu.solve(rhs)
    out = {"tmax": float(T[idx[0].ravel()].max()), "n": int(diag.size)}
    if with_balance:
        out["balance"] = float((gamb * T).sum() / (0.5 * power))
    return out


def barrel_gv(extra_t=0.5, r=0.15e-3, fill_k=KCU):
    """!
    @brief The program's barrel conductance per gap of a copper-filled via: k A / (d + extra_t t_cu).
    @param extra_t Fraction of the copper thickness added to the gap (the program's BARREL_COPPER_FRACTION).
    @param r Drill radius in m.
    @param fill_k Fill conductivity in W/mK.
    @return float conductance in W/K of the whole via over one gap (solid disc).
    """
    return fill_k * math.pi * r * r / (GAP + extra_t * TCU)
