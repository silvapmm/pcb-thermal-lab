#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file stack3d.py
@brief Independent 3D finite-volume reference for a rectangular stack of slabs with ANISOTROPIC cells, a heat source in one slab, films on the outer faces and on the open side walls (imports nothing from pcbthermal).
@details Written for the interface pad of a metal block (`fix/solid3d-pad-inplane`): the pad stands for a contact resistance, so it conducts across only. Here a slab has a conductivity along the
         plane `kx`, one across `kz` and a thickness `dz`; a cell with `kz` = 0 is void. The pad of the program is `dz` = R'' (m2K/W) times 1 W/mK with `kz` = 1 W/mK and `kx` = 0 here, the exact contact
         resistance with no spreading. Cell-centred finite volumes, harmonic mean of the half-cell resistances between neighbours (in the plane and across), the film of the outer face of every column
         in series with half its top (or bottom) cell, and the film of the open side walls (a void neighbour or the edge of the grid) of the slabs flagged `wall` (the metal of a block: the film acts on
         the whole wall height, with no conduction in series, as the program's blocks). Temperatures are rises over the ambient. `tests/test_solid3d_pad_inplane.py` certifies it against
         `tests/helpers/layered3d.py` (a stack without a pad or a block) before it is used.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def solve(dx, dy, slabs, source_slab, source_mask, power, h_top, h_bottom):
    """!
    @brief Steady rise of a stack of slabs with a power injected in one slab.
    @param dx Cell size along x in m.
    @param dy Cell size along y in m.
    @param slabs List from the top down of dicts: `dz` (m), `kx` and `kz` (W/mK, a number or an array (ny, nx); `kz` = 0 marks a void cell), optional `wall` (film coefficient in W/m2K on the open side walls of the slab, 0 or absent: none).
    @param source_slab Index of the slab that receives the power.
    @param source_mask Boolean array (ny, nx) of the cells that receive it (equal shares).
    @param power Power in W.
    @param h_top Film of the top face of the first existing cell of every column in W/m2K.
    @param h_bottom Film of the bottom face of the last existing cell of every column in W/m2K.
    @return dict with T (array (nz, ny, nx), rise in K, NaN in void cells), heat_out (W lost to the ambient, balance check).
    """
    ny, nx = source_mask.shape
    nz = len(slabs)
    kx = np.array([np.broadcast_to(np.asarray(s["kx"], float), (ny, nx)) for s in slabs])
    kz = np.array([np.broadcast_to(np.asarray(s["kz"], float), (ny, nx)) for s in slabs])
    dz = np.array([float(s["dz"]) for s in slabs])
    alive = kz > 0
    idx = np.arange(nz * ny * nx).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(nz * ny * nx)

    def link(i, j, g):
        rows.append(i)
        cols.append(j)
        vals.append(g)

    # Lateral links: a pad (kx = 0) has none; two metal or board cells join by the harmonic mean of the half-cell conductances
    for axis, d, w in ((1, dx, dy), (0, dy, dx)):
        a = np.take(kx, range(0, kx.shape[axis + 1] - 1), axis=axis + 1)
        b = np.take(kx, range(1, kx.shape[axis + 1]), axis=axis + 1)
        ia = np.take(idx, range(0, idx.shape[axis + 1] - 1), axis=axis + 1)
        ib = np.take(idx, range(1, idx.shape[axis + 1]), axis=axis + 1)
        ok = (a > 0) & (b > 0)
        with np.errstate(divide="ignore", invalid="ignore"):
            g = np.where(ok, dz[:, None, None] * w * 2.0 * a * b / ((a + b) * d), 0.0)
        link(ia[ok], ib[ok], g[ok])
    # Links across: half-cell resistances in series
    area = dx * dy
    for s in range(nz - 1):
        ok = alive[s] & alive[s + 1]
        with np.errstate(divide="ignore", invalid="ignore"):
            g = np.where(ok, area / (dz[s] / (2.0 * kz[s]) + dz[s + 1] / (2.0 * kz[s + 1])), 0.0)
        link(idx[s][ok], idx[s + 1][ok], g[ok])
    # Films of the outer faces: the first and last existing cell of every column
    for j in range(ny):
        for i in range(nx):
            ids = np.nonzero(alive[:, j, i])[0]
            if ids.size == 0:
                continue
            for s, h in ((ids[0], h_top), (ids[-1], h_bottom)):
                if h > 0:
                    diag[idx[s, j, i]] += area / (1.0 / h + dz[s] / (2.0 * kz[s, j, i]))
    # Open side walls of the flagged slabs: film on the whole wall height, no conduction in series
    for s, sl in enumerate(slabs):
        h = float(sl.get("wall", 0.0))
        if h <= 0:
            continue
        a = alive[s]
        pad = np.pad(a, 1, constant_values=False)
        for axis, length in ((1, dy), (0, dx)):
            for sgn in (-1, 1):
                open_ = a & ~np.roll(pad, sgn, axis=axis)[1:-1, 1:-1]
                diag[idx[s][open_]] += h * dz[s] * length
    off = sp.coo_matrix((np.concatenate(vals), (np.concatenate([r for r in rows]), np.concatenate(cols))), shape=(idx.size, idx.size))
    off = off + off.T
    d = np.asarray(off.sum(axis=1)).ravel() + diag
    d = np.where(alive.ravel(), d, 1.0)                       # void cells: identity row, they carry nothing
    mat = (sp.diags(d) - off).tocsc()
    q = np.zeros(idx.size)
    q[idx[source_slab][source_mask]] = power / source_mask.sum()
    t = spla.spsolve(mat, q)
    heat_out = float((diag[alive.ravel()] * t[alive.ravel()]).sum())
    t = np.where(alive.ravel(), t, np.nan).reshape(nz, ny, nx)
    return {"T": t, "heat_out": heat_out}
