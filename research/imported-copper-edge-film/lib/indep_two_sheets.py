#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file indep_two_sheets.py
@brief Independent reference of the outline-mask review (imports nothing from pcbthermal): the 20 mm square board of `study_outline_mask.py` in its own frame.
@details Two coupled sheets on the aligned square, cell-centred finite volumes on a grid that resolves the copper exactly (1 mm stripes every 2 mm and a 7 mm pad on
         the top sheet, a plane on the bottom one, both 1.2 mm inside the edge), harmonic links, the gap 0.3 W/mK over 1.53 mm, films 10 W/m2K on both faces and the
         edge film h_side x slab (0.8 mm) in series with the half-cell conduction; 4 mm heater of 1 W (exact area weights). The constants are those of
         `Problem.new(..., 2)` (35 um copper of 385 W/mK, FR-4 0.9 W/mK in-plane). A turned board is the same physics, so its converged heater rise must equal this
         one (with the laminate rule off, `norule` in the study).
         Run: `.venv/bin/python releases/2.6.1/final-opinion/scripts/indep_two_sheets.py <h_side>`; prints (cell, mean rise of the heater K, hottest K) at 0.1, 0.05, 0.025 mm.
"""

import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

K_CU, T_CU, K_LAM, SLAB, D, K_GAP = 385.0, 35e-6, 0.9, 0.8e-3, 1.53e-3, 0.3
A_CU = K_CU * T_CU + K_LAM * (SLAB - T_CU)        # sheet of a copper cell, W/K
B_BARE = K_LAM * SLAB                             # sheet of a bare cell, W/K
L = 20e-3                                         # side of the square, m
INSET = 1.2e-3                                    # copper held inside the edge, m
HT = HB = 10.0                                    # face films, W/m2K


def solve(h, h_side, pattern=True):
    """!
    @brief Steady rise of the two sheets.
    @param h Cell side in m (a divisor of 0.1 mm keeps the copper edges on cell faces).
    @param h_side Edge coefficient in W/m2K.
    @param pattern False for full copper on the top sheet.
    @return Tuple (mean rise of the heater K, hottest rise K).
    """
    n = int(round(L / h))
    h = L / n
    c = (np.arange(n) + 0.5) * h - L / 2
    U, V = np.meshgrid(c, c)
    lim = L / 2 - INSET
    inside = (np.abs(U) <= lim) & (np.abs(V) <= lim)
    stripes = np.floor((V + lim) / 1e-3) % 2 == 0
    pad = (np.abs(U) <= 3.5e-3) & (np.abs(V) <= 3.5e-3)
    top = inside & (stripes | pad) if pattern else inside
    sheets = [np.where(top, A_CU, B_BARE), np.where(inside, A_CU, B_BARE)]
    N = n * n
    rows, cols, vals = [], [], []
    diag = np.zeros(2 * N)
    I, J = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    for layer in range(2):
        s = sheets[layer]
        gx = 2 * s[:, :-1] * s[:, 1:] / (s[:, :-1] + s[:, 1:])
        gy = 2 * s[:-1, :] * s[1:, :] / (s[:-1, :] + s[1:, :])
        for g, a, b in ((gx, (I[:, :-1], J[:, :-1]), (I[:, 1:], J[:, 1:])), (gy, (I[:-1, :], J[:-1, :]), (I[1:, :], J[1:, :]))):
            ia = (layer * N + a[0] * n + a[1]).ravel()
            ib = (layer * N + b[0] * n + b[1]).ravel()
            g = g.ravel()
            rows += [ia, ib]
            cols += [ib, ia]
            vals += [-g, -g]
            np.add.at(diag, ia, g)
            np.add.at(diag, ib, g)
        H = h_side * SLAB
        ge = H * h / (1 + H * (h / 2) / s)          # the film in series with half a cell (second order at the edge)
        e = np.zeros((n, n))
        e[:, 0] += ge[:, 0]
        e[:, -1] += ge[:, -1]
        e[0, :] += ge[0, :]
        e[-1, :] += ge[-1, :]
        diag[layer * N:(layer + 1) * N] += e.ravel() + (HT if layer == 0 else HB) * h * h
    gz = K_GAP / D * h * h
    a = np.arange(N)
    rows += [a, a + N]
    cols += [a + N, a]
    vals += [-np.full(N, gz)] * 2
    diag += gz
    K = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(2 * N, 2 * N)) + sp.diags(diag)
    e0 = np.arange(n) * h - L / 2
    wx = np.clip(np.minimum(e0 + h, 2e-3) - np.maximum(e0, -2e-3), 0, None)
    w = np.outer(wx, wx)
    w /= w.sum()
    q = np.zeros(2 * N)
    q[:N] = w.ravel()
    T = spla.spsolve(K.tocsc(), q)
    return float((w.ravel() * T[:N]).sum()), float(T.max())


if __name__ == "__main__":
    hs = float(sys.argv[1])
    for cell in (0.1e-3, 0.05e-3, 0.025e-3):
        print(hs, cell, solve(cell, hs), flush=True)
