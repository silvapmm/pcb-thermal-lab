#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file truth3d.py
@brief Independent 3D reference of the edge-film study: a quarter of the 20 mm board (copper held inside the edge) resolved through the thickness, with the edge film on the wall (imports nothing from pcbthermal).
@details Cartesian cell-centred finite volumes, anisotropic laminate (0.9 W/mK in the plane, 0.3 through it), copper 385 W/mK, real copper thickness (35 um) and the real
         laminate between the copper layers cut into `nz_lam` sub-slabs per gap, so nothing of the program's idealisation (one node per copper layer plus the laminate rule) is
         used. The quarter x, y in [0, L/2] has insulated symmetry planes at 0; the wall at L/2 has the film h_side in series with the half-cell conduction (second order);
         the top and bottom faces have the films h_top, h_bottom (also under the heater, as the program does); the heater is a square of the top face. Copper of every layer is a
         centred square held `inset` inside the wall (full copper inside, so the quarter symmetry holds); the top layer may be a smaller centred pad. Copper edges lie on cell faces.
         The gap between copper layers is (board thickness - layers x 35 um) / (layers - 1), as the simple stack-up of the program.
         Returned: mean rise of the heater over the top-copper cells it covers, the hottest rise and the heat-balance error.
         Usage: `python truth3d.py <h_side> <cells mm, comma separated> [nz_lam] [layers]`.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

K_CU, T_CU, K_XY, K_Z = 385.0, 35e-6, 0.9, 0.3
HEAT = 4e-3                                        # side of the heater, m


def solve(h_side, cell_mm, nz_lam=12, half=10e-3, inset=1.2e-3, h_top=10.0, h_bottom=10.0, power=1.0, pad_half=None, layers=2, board_t=1.6e-3):
    """!
    @brief Steady rise of the quarter board.
    @param h_side Edge film in W/m2K on the whole wall (copper and laminate).
    @param cell_mm Cell in the plane in mm (must divide the half side and the inset: 0.1, 0.05, 0.2, 0.4).
    @param nz_lam Sub-slabs of the laminate in every gap between copper layers.
    @param half Half side of the board in m.
    @param inset Distance of the copper edge from the wall, m.
    @param h_top Top film, W/m2K.
    @param h_bottom Bottom film, W/m2K.
    @param power Heater power for the whole square, W (a quarter is applied).
    @param pad_half Half side of a top copper pad; None for full copper inside the inset on the top layer.
    @param layers Copper layers (2 or more; inner layers are full copper inside the inset).
    @param board_t Board thickness in m.
    @return Tuple (mean rise of the heater K, hottest rise K, heat balance error).
    """
    d = cell_mm * 1e-3
    n = int(round(half / d))
    c = (np.arange(n) + 0.5) * d
    X, Y = np.meshgrid(c, c)
    lim = half - inset
    cu_all = (X < lim + 1e-12) & (Y < lim + 1e-12)
    cu_top = cu_all if pad_half is None else (X < pad_half + 1e-12) & (Y < pad_half + 1e-12)
    gap = (board_t - layers * T_CU) / (layers - 1)
    dz, kxy_l, kz_l = [], [], []
    for li in range(layers):
        mk = cu_top if li == 0 else cu_all
        dz.append(T_CU)
        kxy_l.append(np.where(mk, K_CU, K_XY))
        kz_l.append(np.where(mk, K_CU, K_Z))
        if li < layers - 1:
            for _ in range(nz_lam):
                dz.append(gap / nz_lam)
                kxy_l.append(np.full((n, n), K_XY))
                kz_l.append(np.full((n, n), K_Z))
    nz = len(dz)
    kxy, kz = np.array(kxy_l), np.array(kz_l)
    N = n * n
    idx = np.arange(nz * N).reshape(nz, n, n)
    rows, cols, vals = [], [], []
    diag = np.zeros(nz * N)

    def link(a, b, g):
        """!
        @brief Symmetric link of conductance g between node arrays a and b.
        @param a Node indices.
        @param b Node indices.
        @param g Conductance W/K (array).
        @return None.
        """
        a, b, g = a.ravel(), b.ravel(), np.broadcast_to(g, a.shape).ravel()
        rows.extend([a, b])
        cols.extend([b, a])
        vals.extend([-g, -g])
        np.add.at(diag, a, g)
        np.add.at(diag, b, g)

    gw_x, gw_y = [], []
    for k in range(nz):
        a, b = kxy[k][:, :-1], kxy[k][:, 1:]
        link(idx[k, :, :-1], idx[k, :, 1:], dz[k] * 2 * a * b / (a + b))
        a, b = kxy[k][:-1, :], kxy[k][1:, :]
        link(idx[k, :-1, :], idx[k, 1:, :], dz[k] * 2 * a * b / (a + b))
        # the wall at x = half and y = half: film in series with the half-cell conduction, over the face dz x d
        gx = 1.0 / (1.0 / (h_side * dz[k] * d) + (d / 2) / (kxy[k][:, -1] * dz[k] * d))
        gy = 1.0 / (1.0 / (h_side * dz[k] * d) + (d / 2) / (kxy[k][-1, :] * dz[k] * d))
        np.add.at(diag, idx[k, :, -1], gx)
        np.add.at(diag, idx[k, -1, :], gy)
        gw_x.append(gx)
        gw_y.append(gy)
    for k in range(nz - 1):
        r = dz[k] / (2 * kz[k] * d * d) + dz[k + 1] / (2 * kz[k + 1] * d * d)
        link(idx[k], idx[k + 1], 1.0 / r)
    rh_t = dz[0] / (2 * kz[0] * d * d)
    rh_b = dz[-1] / (2 * kz[-1] * d * d)
    gt = 1.0 / (rh_t + 1.0 / (h_top * d * d))
    gb = 1.0 / (rh_b + 1.0 / (h_bottom * d * d))
    np.add.at(diag, idx[0].ravel(), gt.ravel())
    np.add.at(diag, idx[-1].ravel(), gb.ravel())
    heater = (X < HEAT / 2 + 1e-12) & (Y < HEAT / 2 + 1e-12)
    q = np.zeros(nz * N)
    q[idx[0].ravel()] = (power / 4.0 * heater / heater.sum()).ravel()
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nz * N, nz * N)).tocsr() + sp.diags(diag)
    T = spla.spsolve(K.tocsc(), q).reshape(nz, n, n)
    out = (gt * T[0]).sum() + (gb * T[-1]).sum()
    for k in range(nz):                                                     # heat through the two walls
        out += (gw_x[k] * T[k][:, -1]).sum() + (gw_y[k] * T[k][-1, :]).sum()
    return float(T[0][heater].mean()), float(T[0].max()), float(out / (power / 4.0) - 1.0)


if __name__ == "__main__":
    import sys
    hs = float(sys.argv[1])
    for cell in [float(x) for x in sys.argv[2].split(",")]:
        print(hs, cell, solve(hs, cell, int(sys.argv[3]) if len(sys.argv) > 3 else 12, layers=int(sys.argv[4]) if len(sys.argv) > 4 else 2), flush=True)
