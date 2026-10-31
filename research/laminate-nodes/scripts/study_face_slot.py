#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_face_slot.py
@brief Does the face term overshoot when the bare part of a cell is narrow (fill close to 1)? The drop from the face of a bare slot to the copper node level, against the 1D term (review).
@details Question answered: the face term of the rule adds Q (1 - f)^p t / (2 k_z A) to the node of a cell with fill f < 1 (README 3.6). With p = 0 a cell whose bare part is a sliver
         (f = 0.99) gets the whole half-layer drop, as if the bare laminate were wide. The real drop over a bare slot of width w in a copper layer of thickness t is smaller when the
         copper walls of the slot are close: the heat that enters the slot leaves sideways into the copper. A two-dimensional finite-volume model of the slot (face to the node level,
         depth t / 2 of laminate, anisotropic k_x = 0.9, k_z = 0.3 W/mK; the copper walls and the node level held at the node temperature, a uniform flux on the face) gives the peak
         and the mean of the face over the slot divided by the 1D term q t / (2 k_z). Independent of the program and of ref3d.py; a numerical check, not a published case.
         Run: .venv/bin/python research/laminate-nodes/scripts/study_face_slot.py
"""

import _bootstrap  # noqa: F401  (import paths)

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

import report as RP

KX, KZ, T_CU = 0.9, 0.3, 35e-6        # laminate in the plane and across (W/mK), copper thickness (m)


def slot(w, t=T_CU, kx=KX, kz=KZ, nx=200, nz=60):
    """!
    @brief Face temperature over a bare slot, relative to the 1D term.
    @param w Slot width in m.
    @param t Copper thickness in m (the slot depth to the node level is t / 2).
    @param kx Laminate conductivity in the plane (W/mK).
    @param kz Laminate conductivity across (W/mK).
    @param nx Cells across the slot.
    @param nz Cells over the depth t / 2.
    @return tuple (peak / term, mean / term).
    """
    dx, dz = w / nx, (t / 2) / nz
    n = nx * nz
    idx = np.arange(n).reshape(nz, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)
    gx, gz = kx * dz / dx, kz * dx / dz

    def link(a, b, g):
        """!@brief Symmetric conductance g between node arrays a and b. @param a Nodes. @param b Nodes. @param g Conductance (W/K per m of depth). @return None."""
        rows.extend([a, b])
        cols.extend([b, a])
        vals.extend([np.full(a.size, -g)] * 2)
        np.add.at(diag, a, g)
        np.add.at(diag, b, g)

    link(idx[:, :-1].ravel(), idx[:, 1:].ravel(), gx)
    link(idx[:-1, :].ravel(), idx[1:, :].ravel(), gz)
    np.add.at(diag, idx[:, 0], 2 * gx)                 # copper walls at the node temperature (half a cell away)
    np.add.at(diag, idx[:, -1], 2 * gx)
    np.add.at(diag, idx[-1, :], 2 * gz)                # node level at the node temperature
    q = np.zeros(n)
    q[idx[0, :]] = 1.0 * dx                             # unit flux on the face
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr() + sp.diags(diag)
    T = spla.spsolve(K.tocsc(), q).reshape(nz, nx)
    term = t / (2 * kz)
    return float(T[0].max() / term), float(T[0].mean() / term)


def main():
    """!
    @brief Sweep the slot width.
    @return None.
    """
    rows = []
    for w_um in (5, 10, 20, 35, 50, 100, 150, 200, 500):
        pk, mn = slot(w_um * 1e-6)
        rows.append({"w um": w_um, "w / t": (".2f", w_um * 1e-6 / T_CU), "peak / term": (".3f", pk), "mean / term": (".3f", mn),
                     "fill of a 0.5 mm cell with one such slot": (".3f", 1 - w_um * 1e-3 / 0.5)})
    RP.table(rows, list(rows[0]), title="Face over a bare slot in 35 um copper: drop to the node level over the 1D term q t / (2 k_z)")
    RP.save("face_slot", rows)


if __name__ == "__main__":
    main()
