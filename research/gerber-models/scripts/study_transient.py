#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_transient.py
@brief Does the conductance mapping also give the right time response? The heat capacity stays an arithmetic (volume) average; only the conductances change.
@details One copper sheet as the program models it (copper phase: k_cu t_cu + k_lam (slab - t_cu); laminate phase: k_lam slab; slab 1.6 mm), 1 W step on a 6 x 6 mm
         block, implicit Euler with three constant steps (0.02 s up to 1 s, 0.2 s up to 10 s, 2 s up to 120 s). Reference: the 0.1 mm mask.
         Error of the mean temperature of the block at 0.1, 1, 10 and 120 s, over two windows per board (14 windows), cells of 0.6 and 1.0 mm.
         Run: .venv/bin/python research/gerber-models/scripts/study_transient.py (from the repository root) (about 5 minutes).
"""

import _bootstrap  # noqa: F401  (puts the import paths of research/gerber-models in order)

from multiprocessing import Pool

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

import conduction as cd
import windows

PIX = windows.PIX
RHO_CP_CU, RHO_CP_LAM = 8960.0 * 385.0, 1850.0 * 1100.0        # J/m3K
TC, SLAB = cd.T_CU, cd.T_LAM
A_PHASE = cd.K_CU * TC + cd.K_LAM * (SLAB - TC)                 # copper phase conductance (W/K)
B_PHASE = cd.K_LAM * SLAB                                       # laminate phase conductance (W/K)
C_CU_PHASE = RHO_CP_CU * TC + RHO_CP_LAM * (SLAB - TC)         # J/m2K
C_LAM_PHASE = RHO_CP_LAM * SLAB
SEGMENTS = ((0.02, 50), (0.2, 45), (2.0, 55))                   # (step s, number of steps)
REPORT = (0.1, 1.0, 10.0, 120.0)


def response(gx, gy, c_cell, cell_mm, k0, k1, power=1.0):
    """!
    @brief Mean temperature of a heated block against time (implicit Euler, three constant steps).
    @param gx Face conductances along x (ny, nx - 1), W/K.
    @param gy Face conductances along y (ny - 1, nx).
    @param c_cell Heat capacity of every cell (ny, nx), J/K.
    @param cell_mm Cell size (mm).
    @param k0 First row and column of the heated block.
    @param k1 One past the last row and column.
    @param power Step power (W).
    @return Dict time (s) -> mean temperature rise of the block (K) for the times of REPORT.
    """
    ny, nx = gx.shape[0], gy.shape[1]
    n = ny * nx
    idx = np.arange(n).reshape(ny, nx)
    a = np.concatenate([idx[:, :-1].ravel(), idx[:-1, :].ravel()])
    b = np.concatenate([idx[:, 1:].ravel(), idx[1:, :].ravel()])
    g = np.concatenate([gx.ravel(), gy.ravel()])
    diag = np.bincount(a, g, n) + np.bincount(b, g, n) + 2 * cd.H_FACE * (cell_mm * 1e-3) ** 2
    K = sp.coo_matrix((np.concatenate([-g, -g]), (np.concatenate([a, b]), np.concatenate([b, a]))), shape=(n, n)).tocsr() + sp.diags(diag)
    q = np.zeros((ny, nx))
    q[k0:k1, k0:k1] = power / ((k1 - k0) ** 2)
    q = q.ravel()
    C = sp.diags(c_cell.ravel())
    T = np.zeros(n)
    t, out = 0.0, {}
    for dt, steps in SEGMENTS:
        lu = spla.splu((C / dt + K).tocsc())
        for _ in range(steps):
            T = lu.solve(C @ T / dt + q)
            t += dt
            for r in REPORT:
                if abs(t - r) < 1e-9:
                    out[r] = T.reshape(ny, nx)[k0:k1, k0:k1].mean()
    return out


def work(args):
    """!
    @brief The comparison on one window.
    @param args Tuple (key, mask).
    @return List of records (cell mm, method, time s, error %).
    """
    key, mask = args
    S = np.where(mask, A_PHASE, B_PHASE)
    Cp = np.where(mask, C_CU_PHASE, C_LAM_PHASE) * (PIX * 1e-3) ** 2
    hs, he = int(12 / PIX), int(18 / PIX)
    ref = response(cd.harm(S[:, :-1], S[:, 1:]), cd.harm(S[:-1, :], S[1:, :]), Cp, PIX, hs, he)
    out = []
    for c in (0.6, 1.0):
        n = int(round(c / PIX))
        blk = cd.cell_blocks(S, n)
        f = (blk == A_PHASE).mean(axis=(2, 3))
        cc = cd.cell_blocks(Cp, n).sum(axis=(2, 3))                  # arithmetic (volume) average of the capacity
        k0, k1 = int(round(12 / c)), int(round(18 / c))
        cand = {"arithmetic": cd.faces_from_cells(*(2 * [cd.map_power(f, 1.0, A_PHASE, B_PHASE)])),
                "geometric": cd.faces_from_cells(*(2 * [cd.map_power(f, 0.0, A_PHASE, B_PHASE)])),
                "lam 0.5": cd.faces_from_cells(*cd.map_lambda(blk, 0.5)), "dual m=0": cd.dual_faces(S, n, 0)}
        for name, (gx, gy) in cand.items():
            r = response(gx, gy, cc, c, k0, k1)
            out += [(c, name, t, 100 * (r[t] / ref[t] - 1)) for t in REPORT]
    return out


def main():
    """!
    @brief Run two windows per board and print the MAE (bias) per time.
    @return None.
    """
    masks, meta = windows.load()
    seen, tasks = {}, []
    for i, m in enumerate(meta):
        if seen.get(m[0], 0) < 2:
            seen[m[0]] = seen.get(m[0], 0) + 1
            tasks.append((m[0], masks[i]))
    out = []
    with Pool(4) as pool:
        for r in pool.imap_unordered(work, tasks):
            out += r
    print(f"{len(tasks)} windows; MAE of the block-mean temperature error % (bias in brackets) at each time")
    print(f"{'cell':>5s} {'method':12s}" + "".join(f"{t:>16}" for t in REPORT))
    for c in (0.6, 1.0):
        for name in ("arithmetic", "geometric", "lam 0.5", "dual m=0"):
            row = []
            for t in REPORT:
                e = np.array([o[3] for o in out if o[0] == c and o[1] == name and o[2] == t])
                row.append(f"{np.abs(e).mean():5.1f} ({e.mean():+5.1f})")
            print(f"{c:5.1f} {name:12s}" + "".join(f"{x:>16}" for x in row))


if __name__ == "__main__":
    main()
