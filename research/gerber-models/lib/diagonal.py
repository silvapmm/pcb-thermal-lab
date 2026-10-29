#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file diagonal.py
@brief A nine-point network for the thermal grid: faces to the four diagonal neighbours as well as to the four axial ones, a conductance tensor per cell from local conduction problems, and the stencil that goes with it (research prototype for the diagonal copper of README 4.42).
@details The program's network couples a cell to its four neighbours through one x face and one y face. Heat that follows a track at 30 or 45 degrees must go in a staircase of x and y faces, and each face, computed along its own axis, sees only part of the track.
         Here a cell has a sheet-conductance tensor (kxx, kyy, kxy) in the axes of the array (x = column, y = row). Its nine-point stencil is the standard one that reproduces kxx u_xx + kyy u_yy + 2 kxy u_xy on a square grid:
         axial couplings cx = kxx - |kxy| and cy = kyy - |kxy| (at least 0), one diagonal pair with the conductance |kxy| (the d1 pair, from [i, j] to [i + 1, j + 1], when kxy > 0; the d2 pair, from [i, j + 1] to [i + 1, j], when kxy < 0).
         The tensor of a cell comes from two local conduction problems on its n x n pixels with an affine boundary condition (the potential on the whole boundary is x, then y), the energy of the two fields normalised by that of a uniform cell of S = 1, so a uniform cell gives (S, S, 0).
         The fine reference uses the isotropic nine-point stencil (axial 2/3, diagonal 1/6 of the pixel conductance), which is closer to the continuum than the five-point one on thin tilted copper (README 4.23).
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

import conduction as cd


def _harm(a, b):
    """!
    @brief Harmonic mean of two conductances, 0 where both are 0.
    @param a First array.
    @param b Second array.
    @return numpy.ndarray Series conductance.
    """
    s = a + b
    return np.where(s > 0, 2.0 * a * b / np.where(s > 0, s, 1.0), 0.0)


def solve9(gx, gy, gd1, gd2, cell_mm, power_map, h_face, fixed):
    """!
    @brief Steady temperature rise of a sheet with axial and diagonal faces, fixed cells and a loss through both faces.
    @param gx Conductances between horizontal neighbours (ny, nx - 1), W/K.
    @param gy Conductances between vertical neighbours (ny - 1, nx), W/K.
    @param gd1 Conductances from [i, j] to [i + 1, j + 1] (ny - 1, nx - 1), W/K.
    @param gd2 Conductances from [i, j + 1] to [i + 1, j] (ny - 1, nx - 1), W/K.
    @param cell_mm Cell size (mm), for the loss through the faces.
    @param power_map Heat per cell (ny, nx), W.
    @param h_face Heat transfer coefficient of each face (W/m2K).
    @param fixed Boolean array (ny, nx): cells held at zero rise.
    @return numpy.ndarray (ny, nx) temperature rise (K).
    """
    ny, nx = gx.shape[0], gy.shape[1]
    n = ny * nx
    idx = np.arange(n).reshape(ny, nx)
    a = np.concatenate([idx[:, :-1].ravel(), idx[:-1, :].ravel(), idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel()])
    b = np.concatenate([idx[:, 1:].ravel(), idx[1:, :].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()])
    g = np.concatenate([gx.ravel(), gy.ravel(), gd1.ravel(), gd2.ravel()])
    diag = np.bincount(a, g, n) + np.bincount(b, g, n) + 2 * h_face * (cell_mm * 1e-3) ** 2
    K = sp.coo_matrix((np.concatenate([-g, -g]), (np.concatenate([a, b]), np.concatenate([b, a]))), shape=(n, n)).tocsr() + sp.diags(diag)
    free = ~fixed.ravel()
    T = np.zeros(n)
    T[free] = spla.spsolve(K.tocsc()[free][:, free].tocsc(), power_map.ravel()[free])
    return T.reshape(ny, nx)


def pixel_faces9(S):
    """!
    @brief The isotropic nine-point faces of a pixel sheet-conductance array (axial 2/3, diagonal 1/6 of the harmonic mean of the two pixels).
    @param S Pixel sheet conductances (ny, nx).
    @return tuple (gx, gy, gd1, gd2).
    """
    return (2.0 / 3.0 * cd.harm(S[:, :-1], S[:, 1:]), 2.0 / 3.0 * cd.harm(S[:-1, :], S[1:, :]),
            1.0 / 6.0 * cd.harm(S[:-1, :-1], S[1:, 1:]), 1.0 / 6.0 * cd.harm(S[:-1, 1:], S[1:, :-1]))


def pixel_reference9(S, pix_mm, power_px, h_face, fixed_px):
    """!
    @brief The resolved solution with the nine-point stencil: the mask solved pixel by pixel.
    @param S Pixel sheet conductances (ny, nx).
    @param pix_mm Pixel size (mm).
    @param power_px Heat per pixel (W).
    @param h_face Face heat transfer coefficient (W/m2K).
    @param fixed_px Boolean array of fixed pixels.
    @return numpy.ndarray Temperature rise per pixel (K).
    """
    return solve9(*pixel_faces9(S), pix_mm, power_px, h_face, fixed_px)


def cell_tensor(S, n):
    """!
    @brief The sheet-conductance tensor of every cell from two local problems with an affine boundary condition (the potential on the whole boundary of the cell is x, then y), the nine-point links inside, the energy of the two fields normalised by the energy of a uniform cell of S = 1.
    @details A uniform cell gives (S, S, 0). Unlike four directional solves, a single symmetric tensor cannot report a cross term for an axis-aligned conductor that happens to lie off the centre of the cell.
    @param S Pixel sheet conductances (ny, nx), whole cells of n x n pixels.
    @param n Pixels per cell side.
    @return tuple (kxx, kyy, kxy), each (cy, cx), W/K (x = column, y = row; kxy > 0 when copper runs from [i, j] towards [i + 1, j + 1]).
    """
    blk = cd.cell_blocks(S, n)
    cy, cx = blk.shape[:2]
    flat = np.ascontiguousarray(blk.reshape(-1, n, n))
    N = n * n
    ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    ring = (ii == 0) | (ii == n - 1) | (jj == 0) | (jj == n - 1)
    fields = (jj.astype(float), ii.astype(float))                                # the potentials x and y on the boundary
    pairs = (((slice(None), slice(None), slice(None, -1)), (slice(None), slice(None), slice(1, None)), 2.0 / 3.0),
             ((slice(None), slice(None, -1), slice(None)), (slice(None), slice(1, None), slice(None)), 2.0 / 3.0),
             ((slice(None), slice(None, -1), slice(None, -1)), (slice(None), slice(1, None), slice(1, None)), 1.0 / 6.0),
             ((slice(None), slice(None, -1), slice(1, None)), (slice(None), slice(1, None), slice(None, -1)), 1.0 / 6.0))

    def energies(B):
        """!
        @brief The 2 x 2 energy matrix of the two affine fields for every block.
        @param B Pixel sheet conductances (K, n, n).
        @return numpy.ndarray (K, 3): E_xx, E_yy, E_xy.
        """
        K = B.shape[0]
        base = np.arange(K)[:, None, None] * N + np.arange(n)[None, :, None] * n + np.arange(n)[None, None, :]
        a = np.concatenate([base[s1].ravel() for s1, _, _ in pairs])
        b = np.concatenate([base[s2].ravel() for _, s2, _ in pairs])
        g = np.concatenate([(w * cd.harm(B[s1], B[s2])).ravel() for s1, s2, w in pairs])
        L = sp.coo_matrix((np.concatenate([-g, -g]), (np.concatenate([a, b]), np.concatenate([b, a]))), shape=(K * N, K * N)).tocsr()
        L = L + sp.diags(np.bincount(a, g, K * N) + np.bincount(b, g, K * N))
        fixed = np.tile(ring.ravel(), K)
        free = ~fixed
        vs = []
        for f in fields:
            v = np.tile(np.where(ring, f, 0.0).ravel(), K)
            rhs = -(L @ v)
            v[free] = spla.spsolve(L[free][:, free].tocsc(), rhs[free])
            vs.append(v)
        dx = vs[0][a] - vs[0][b]
        dy = vs[1][a] - vs[1][b]
        blockof = a // N
        return np.stack([np.bincount(blockof, g * dx * dx, K), np.bincount(blockof, g * dy * dy, K), np.bincount(blockof, g * dx * dy, K)], axis=1)

    e = energies(flat)
    u = energies(np.ones((1, n, n)))[0]
    return (e[:, 0] / u[0]).reshape(cy, cx), (e[:, 1] / u[1]).reshape(cy, cx), (e[:, 2] / u[0]).reshape(cy, cx)


def faces_from_tensor(kxx, kyy, kxy):
    """!
    @brief The nine-point faces between cells from the tensor of every cell (harmonic mean of the two cells of a pair).
    @param kxx Cell conductance along x (cy, cx).
    @param kyy Cell conductance along y (cy, cx).
    @param kxy Cell cross term (cy, cx).
    @return tuple (gx, gy, gd1, gd2) with the shapes of `solve9`.
    """
    cxx = np.maximum(kxx - np.abs(kxy), 0.0)
    cyy = np.maximum(kyy - np.abs(kxy), 0.0)
    d1, d2 = np.maximum(kxy, 0.0), np.maximum(-kxy, 0.0)
    return (_harm(cxx[:, :-1], cxx[:, 1:]), _harm(cyy[:-1, :], cyy[1:, :]),
            _harm(d1[:-1, :-1], d1[1:, 1:]), _harm(d2[:-1, 1:], d2[1:, :-1]))


def faces5_as9(gx, gy):
    """!
    @brief Five-point faces in the shape that `solve9` takes (no diagonal faces).
    @param gx Axial x faces (ny, nx - 1).
    @param gy Axial y faces (ny - 1, nx).
    @return tuple (gx, gy, gd1, gd2) with zero diagonals.
    """
    z = np.zeros((gx.shape[0] - 1, gx.shape[1]))
    return gx, gy, z, z.copy()


def hybrid_faces(S, n, alpha=1.0, gate=None):
    """!
    @brief Flow-based axial faces plus the diagonal conduction they miss: the cell tensor gives the conductance along each diagonal, (kxx + kyy) / 2 +- kxy, and the diagonal pair adds what the axial faces do not already deliver along it.
    @details The axial faces are the flow-based ones (the mapping of README 4.4 to 4.13, unchanged); the diagonal pair of a cell has the conductance max(k_diagonal - (cx + cy) / 2, 0) / 2, where cx and cy are the cell values of the flow-based faces (the mean of the two faces of the cell), so an axis-aligned conductor and a uniform cell get no diagonal faces.
    @param S Pixel sheet conductances (ny, nx), whole cells of n x n pixels.
    @param n Pixels per cell side.
    @param alpha Share of the missing diagonal conduction that is added (1 = all of it).
    @param gate Optional function (kxx, kyy, kxy) -> array (cy, cx) of shares in 0..1 that replaces `alpha` cell by cell: the detector of the cells whose diagonal conduction should be added (README 4.47).
    @return tuple (gx, gy, gd1, gd2) with the shapes of `solve9`.
    """
    gx, gy = cd.dual_faces(S, n, 0)
    cy_, cx_ = gy.shape[1], gx.shape[0]
    cxv = np.zeros((cx_, cy_))
    cyv = np.zeros((cx_, cy_))
    cxv[:, :-1] += gx
    cxv[:, 1:] += gx
    cxv[:, 1:-1] /= 2.0                                                # an inner cell has two x faces, a border cell one
    cyv[:-1, :] += gy
    cyv[1:, :] += gy
    cyv[1:-1, :] /= 2.0
    kxx, kyy, kxy = cell_tensor(S, n)
    if gate is not None:
        alpha = gate(kxx, kyy, kxy)
    mean_k = 0.5 * (kxx + kyy)
    base = 0.5 * (cxv + cyv)
    c1 = alpha * np.maximum(mean_k + kxy - base, 0.0) / 2.0
    c2 = alpha * np.maximum(mean_k - kxy - base, 0.0) / 2.0
    return gx, gy, _harm(c1[:-1, :-1], c1[1:, 1:]), _harm(c2[:-1, 1:], c2[1:, :-1])
