"""!
@file conduction.py
@brief Conduction solvers and the mappings from a resolved copper mask to the conductances of a coarse square grid.
@details Research code for the Gerber import (README.md in this folder). The physics is the program's layered model reduced to its essence:
         a copper sheet (sheet conductance S_CU) on laminate (S_LAM), heat leaving both faces with the same coefficient H_FACE.
         All conductances are sheet conductances in W/K (a square piece of the sheet), so for square cells they do not depend on the cell size.

         Mappings (a "mask" is a boolean array, True = copper, one value per fine pixel):
           * fill fraction (arithmetic mean, what the program's FVM does today)   -> map_power(f, 1)
           * power mean of exponent p of the two phases (p = 0: geometric mean)     -> map_power(f, p)
           * bounds of Wiener: low (rows in parallel of series chains), up (series of parallel columns) -> map_bounds
           * lambda: low^(1 - lambda) * up^lambda (lambda = 0.5 is the geometric mean of the bounds)    -> map_lambda
           * numerical upscaling of a cell: a local conduction problem on the cell                    -> map_cell_problem
           * flow-based face conductances: a local problem on the window that spans two cell centres   -> dual_faces
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

K_CU, T_CU = 385.0, 35e-6              # copper: W/mK, m (1 oz finished)
K_LAM, T_LAM = 0.9, 1.6e-3             # FR-4 in plane: W/mK, m
S_CU = K_CU * T_CU                     # sheet conductance of the copper (W/K)
S_LAM = K_LAM * T_LAM                  # sheet conductance of the laminate (W/K)
H_FACE = 10.0                          # W/m2K on each face (convection plus radiation, typed)


def harm(a, b):
    """!
    @brief Harmonic mean of two conductances (two half cells in series): the face conductance of the FVM.
    @param a Conductance of one side (scalar or array).
    @param b Conductance of the other side.
    @return Harmonic mean 2ab/(a+b).
    """
    return 2.0 * a * b / (a + b)


# --------------------------------------------------------------------------------------------------------------------------------
# Solvers
# --------------------------------------------------------------------------------------------------------------------------------

def solve_faces(gx, gy, cell_mm, y0, y1, x0, x1, power=1.0, h_face=H_FACE):
    """!
    @brief One conducting sheet on a square grid with given face conductances; power spread over a block of cells.
    @param gx Conductance of the faces between horizontal neighbours, shape (ny, nx - 1), W/K.
    @param gy Conductance of the faces between vertical neighbours, shape (ny - 1, nx), W/K.
    @param cell_mm Cell size (mm), for the loss through the two faces.
    @param y0 First row of the heated block.
    @param y1 One past the last row of the heated block.
    @param x0 First column of the heated block.
    @param x1 One past the last column of the heated block.
    @param power Total power (W), spread uniformly over the block.
    @param h_face Heat transfer coefficient of each face (W/m2K).
    @return numpy.ndarray (ny, nx) temperature rise above the ambient (K).
    """
    ny, nx = gx.shape[0], gy.shape[1]
    n = ny * nx
    idx = np.arange(n).reshape(ny, nx)
    a = np.concatenate([idx[:, :-1].ravel(), idx[:-1, :].ravel()])
    b = np.concatenate([idx[:, 1:].ravel(), idx[1:, :].ravel()])
    g = np.concatenate([gx.ravel(), gy.ravel()])
    diag = np.bincount(a, g, n) + np.bincount(b, g, n) + 2 * h_face * (cell_mm * 1e-3) ** 2     # both faces lose heat
    K = sp.coo_matrix((np.concatenate([-g, -g]), (np.concatenate([a, b]), np.concatenate([b, a]))), shape=(n, n)).tocsr() + sp.diags(diag)
    q = np.zeros((ny, nx))
    q[y0:y1, x0:x1] = power / ((y1 - y0) * (x1 - x0))
    return spla.spsolve(K.tocsc(), q.ravel()).reshape(ny, nx)


def solve_two_layers(gx, gy, gz, cell_mm, rows, cols, power=1.0, h_face=H_FACE):
    """!
    @brief Two stacked sheets (index 0 = top, where the heat enters) joined by a vertical conductance; each outer face loses heat.
    @param gx Face conductances between horizontal neighbours, shape (2, ny, nx - 1), W/K.
    @param gy Face conductances between vertical neighbours, shape (2, ny - 1, nx), W/K.
    @param gz Vertical conductance between the two layers per cell, shape (ny, nx), W/K (dielectric plus plated barrels).
    @param cell_mm Cell size (mm).
    @param rows Array of the rows of the heated block (top layer).
    @param cols Array of the columns of the heated block.
    @param power Total power (W).
    @param h_face Heat transfer coefficient of each outer face (W/m2K).
    @return numpy.ndarray (2, ny, nx) temperature rise (K).
    """
    ny, nx = gy.shape[1] + 1, gx.shape[2] + 1
    m = ny * nx
    n = 2 * m
    A, B, G = [], [], []
    for l in range(2):
        idx = l * m + np.arange(m).reshape(ny, nx)
        A += [idx[:, :-1].ravel(), idx[:-1, :].ravel()]
        B += [idx[:, 1:].ravel(), idx[1:, :].ravel()]
        G += [gx[l].ravel(), gy[l].ravel()]
    a = np.arange(m)
    A.append(a)
    B.append(a + m)
    G.append(gz.ravel())
    A, B, G = np.concatenate(A), np.concatenate(B), np.concatenate(G)
    diag = np.bincount(A, G, n) + np.bincount(B, G, n) + h_face * (cell_mm * 1e-3) ** 2         # one outer face per layer
    K = sp.coo_matrix((np.concatenate([-G, -G]), (np.concatenate([A, B]), np.concatenate([B, A]))), shape=(n, n)).tocsr() + sp.diags(diag)
    q = np.zeros(n)
    q[rows[:, None] * nx + cols[None, :]] = power / (len(rows) * len(cols))
    return spla.spsolve(K.tocsc(), q).reshape(2, ny, nx)


def solve_stack(gx, gy, gz, cell_mm, rows, cols, h_top=H_FACE, h_bottom=H_FACE, power=1.0):
    """!
    @brief A stack of conducting sheets (layer 0 on top, where the heat enters) joined by vertical conductances; the two outer faces lose heat.
    @param gx Face conductances along x, shape (L, ny, nx - 1), W/K.
    @param gy Face conductances along y, shape (L, ny - 1, nx), W/K.
    @param gz Vertical conductances between neighbouring layers, shape (L - 1, ny, nx), W/K (dielectric plus plated barrels).
    @param cell_mm Cell size (mm).
    @param rows Array of the rows of the heated block (in the top layer).
    @param cols Array of the columns of the heated block.
    @param h_top Coefficient of the top face (W/m2K).
    @param h_bottom Coefficient of the bottom face (W/m2K).
    @param power Total power (W).
    @return numpy.ndarray (L, ny, nx) temperature rise (K).
    """
    L, ny, nx = gx.shape[0], gy.shape[1] + 1, gx.shape[2] + 1
    m = ny * nx
    n = L * m
    A, B, G = [], [], []
    for l in range(L):
        idx = l * m + np.arange(m).reshape(ny, nx)
        A += [idx[:, :-1].ravel(), idx[:-1, :].ravel()]
        B += [idx[:, 1:].ravel(), idx[1:, :].ravel()]
        G += [gx[l].ravel(), gy[l].ravel()]
    for l in range(L - 1):
        a = l * m + np.arange(m)
        A.append(a)
        B.append(a + m)
        G.append(gz[l].ravel())
    A, B, G = np.concatenate(A), np.concatenate(B), np.concatenate(G)
    diag = np.bincount(A, G, n) + np.bincount(B, G, n)
    area = (cell_mm * 1e-3) ** 2
    diag[:m] += h_top * area
    diag[n - m:] += h_bottom * area                          # for one layer both faces end up on layer 0 (not used here)
    K = sp.coo_matrix((np.concatenate([-G, -G]), (np.concatenate([A, B]), np.concatenate([B, A]))), shape=(n, n)).tocsr() + sp.diags(diag)
    q = np.zeros(n)
    q[rows[:, None] * nx + cols[None, :]] = power / (len(rows) * len(cols))
    return spla.spsolve(K.tocsc(), q).reshape(L, ny, nx)


def local_flux(Sw, m=0):
    """!
    @brief Effective conductance, left to right, of many windows of pixel sheet conductances (a local conduction problem per window).
    @details Potential 1 on the left face and 0 on the right (half-pixel links, so a uniform window gives exactly its S), top and bottom insulated.
             The flux is counted on the central rows only: the first and last m rows are an oversampling margin that shapes the field but is not counted.
             All windows are solved together as one block-diagonal sparse system.
    @param Sw Array (K, R, C) of pixel sheet conductances (W/K).
    @param m Margin rows at the top and at the bottom of every window (not counted in the flux).
    @return numpy.ndarray (K,) effective conductances (W/K).
    """
    K, R, C = Sw.shape
    N = R * C
    idx = np.arange(K)[:, None, None] * N + np.arange(R)[None, :, None] * C + np.arange(C)[None, None, :]
    a = np.concatenate([idx[:, :, :-1].ravel(), idx[:, :-1, :].ravel()])
    b = np.concatenate([idx[:, :, 1:].ravel(), idx[:, 1:, :].ravel()])
    g = np.concatenate([harm(Sw[:, :, :-1], Sw[:, :, 1:]).ravel(), harm(Sw[:, :-1, :], Sw[:, 1:, :]).ravel()])
    gl, gr = 2 * Sw[:, :, 0], 2 * Sw[:, :, -1]
    il, ir = idx[:, :, 0].ravel(), idx[:, :, -1].ravel()
    diag = np.bincount(a, g, K * N) + np.bincount(b, g, K * N)
    diag[il] += gl.ravel()
    diag[ir] += gr.ravel()
    rhs = np.zeros(K * N)
    rhs[il] = gl.ravel()                                    # unit potential on the left face
    M = sp.coo_matrix((np.concatenate([-g, -g]), (np.concatenate([a, b]), np.concatenate([b, a]))), shape=(K * N, K * N)).tocsr() + sp.diags(diag)
    v = spla.spsolve(M.tocsc(), rhs).reshape(K, R, C)
    return (gr[:, m:R - m] * v[:, m:R - m, -1]).sum(axis=1)


# --------------------------------------------------------------------------------------------------------------------------------
# Mappings
# --------------------------------------------------------------------------------------------------------------------------------

def sheet_of(mask, s_cu=S_CU, s_lam=S_LAM):
    """!
    @brief Pixel sheet conductances of a copper mask.
    @param mask Boolean array, True = copper.
    @param s_cu Sheet conductance of copper (W/K).
    @param s_lam Sheet conductance of the laminate (W/K).
    @return Float array of the same shape.
    """
    return np.where(mask, s_cu, s_lam)


def cell_blocks(a, n):
    """!
    @brief Cut a pixel array into whole blocks of n x n pixels (the last partial row or column is dropped).
    @param a 2D array.
    @param n Pixels per cell side.
    @return Array (cells_y, cells_x, n, n).
    """
    cy, cx = a.shape[0] // n, a.shape[1] // n
    return a[:cy * n, :cx * n].reshape(cy, n, cx, n).transpose(0, 2, 1, 3)


def faces_from_cells(sx, sy):
    """!
    @brief Face conductances as the FVM forms them: the harmonic mean of the two neighbouring cell values (x faces use sx, y faces use sy).
    @param sx Cell sheet conductance for flow along x, shape (cy, cx).
    @param sy Cell sheet conductance for flow along y.
    @return Tuple (gx (cy, cx - 1), gy (cy - 1, cx)).
    """
    return harm(sx[:, :-1], sx[:, 1:]), harm(sy[:-1, :], sy[1:, :])


def map_power(f, p, s_cu=S_CU, s_lam=S_LAM):
    """!
    @brief Power mean of the two phases from the copper fraction alone: (f s_cu^p + (1 - f) s_lam^p)^(1/p).
    @details p = 1 is the arithmetic mean (the fill-fraction model), p = -1 the harmonic mean, p = 0 the geometric mean s_cu^f s_lam^(1 - f).
    @param f Copper fraction of every cell (array, 0..1).
    @param p Exponent.
    @param s_cu Sheet conductance of copper (W/K).
    @param s_lam Sheet conductance of the laminate (W/K).
    @return Array of cell sheet conductances (isotropic).
    """
    if p == 0:
        return s_cu ** f * s_lam ** (1.0 - f)
    return (f * s_cu ** p + (1.0 - f) * s_lam ** p) ** (1.0 / p)


def map_bruggeman(f, s_cu=S_CU, s_lam=S_LAM):
    """!
    @brief Symmetric Bruggeman effective-medium conductance of a two-phase isotropic 2D medium, from the copper fraction alone.
    @details Root of f (a - k)/(a + k) + (1 - f)(b - k)/(b + k) = 0, that is k^2 - (a - b)(2f - 1) k - a b = 0 (2D). At f = 1/2 it is the geometric mean sqrt(a b).
    @param f Copper fraction of every cell (array, 0..1).
    @param s_cu Conductance of the copper phase (W/K).
    @param s_lam Conductance of the laminate phase (W/K).
    @return Array of cell sheet conductances (isotropic).
    """
    d = (s_cu - s_lam) * (2.0 * f - 1.0)
    return 0.5 * (d + np.sqrt(d * d + 4.0 * s_cu * s_lam))


def map_hashin_shtrikman(f, which, s_cu=S_CU, s_lam=S_LAM):
    """!
    @brief Hashin-Shtrikman bound of an isotropic two-phase 2D medium (the tightest bounds that need only the fraction).
    @param f Copper fraction of every cell (array, 0..1).
    @param which "lower" (laminate is the matrix) or "upper" (copper is the matrix).
    @param s_cu Conductance of the copper phase (W/K).
    @param s_lam Conductance of the laminate phase (W/K).
    @return Array of cell sheet conductances (isotropic).
    """
    a, b = s_cu, s_lam
    if which == "lower":
        return b + f / (1.0 / (a - b) + (1.0 - f) / (2.0 * b))
    return a + (1.0 - f) / (1.0 / (b - a) + f / (2.0 * a))


def map_bounds(blocks):
    """!
    @brief The two bounds of Wiener for flow along x and along y in every cell, from the pixel conductances.
    @details low: no cross flow inside the cell (rows in parallel, each row a series chain), a lower bound of the conductance.
             up: equipotential column faces (columns of parallel pixels in series), an upper bound.
    @param blocks Pixel sheet conductances cut in cells, shape (cy, cx, n_rows, n_cols).
    @return Tuple (low_x, low_y, up_x, up_y), each (cy, cx).
    """
    low_x = (1.0 / (1.0 / blocks).mean(axis=3)).mean(axis=2)
    low_y = (1.0 / (1.0 / blocks).mean(axis=2)).mean(axis=2)
    up_x = 1.0 / (1.0 / blocks.mean(axis=2)).mean(axis=2)
    up_y = 1.0 / (1.0 / blocks.mean(axis=3)).mean(axis=2)
    return low_x, low_y, up_x, up_y


def map_lambda(blocks, lam):
    """!
    @brief Directional cell conductances low^(1 - lam) * up^lam (lam = 0.5: the geometric mean of the two bounds).
    @param blocks Pixel sheet conductances cut in cells, shape (cy, cx, n_rows, n_cols).
    @param lam Weight between the lower (0) and the upper (1) bound.
    @return Tuple (sx, sy) of cell conductances for flow along x and along y.
    """
    lx, ly, ux, uy = map_bounds(blocks)
    return lx ** (1.0 - lam) * ux ** lam, ly ** (1.0 - lam) * uy ** lam


def map_cell_problem(blocks):
    """!
    @brief Numerical upscaling: the effective (sx, sy) of every cell from a local conduction problem on the cell itself.
    @param blocks Pixel sheet conductances cut in cells, shape (cy, cx, n, n).
    @return Tuple (sx, sy), each (cy, cx).
    """
    cy, cx, n, _ = blocks.shape
    flat = np.ascontiguousarray(blocks.reshape(-1, n, n))
    sx = local_flux(flat, 0).reshape(cy, cx)
    sy = local_flux(np.ascontiguousarray(flat.transpose(0, 2, 1)), 0).reshape(cy, cx)
    return sx, sy


def dual_faces(S, n, m, batch_pixels=400000):
    """!
    @brief Flow-based face conductances: one local problem per pair of neighbouring cells, on the window from centre to centre.
    @details For two horizontal neighbours the window is n x n pixels (n even) starting at the centre of the left cell; m extra rows above and below
             (taken by reflection at the border) shape the field and are not counted. The face conductance is the effective conductance of that window.
             This is the transmissibility upscaling used for reservoir grids.
    @param S Pixel sheet conductances (rows, cols); only whole cells are used.
    @param n Pixels per cell side (even).
    @param m Margin rows of the oversampling (0 = none).
    @param batch_pixels Pixels of the windows solved together (memory bound; the result does not depend on it).
    @return Tuple (gx (cy, cx - 1), gy (cy - 1, cx)) in W/K.
    """
    from numpy.lib.stride_tricks import sliding_window_view as swv
    cy, cx = S.shape[0] // n, S.shape[1] // n
    S = S[:cy * n, :cx * n]

    def one(Sm):
        """!@brief x faces of an array (rows are the transverse direction). @return array (cells_y, cells_x - 1)."""
        P = np.pad(Sm, ((m, m), (0, 0)), mode="reflect") if m else Sm
        W = swv(P, (n + 2 * m, n))
        ry, rx = Sm.shape[0] // n, Sm.shape[1] // n                  # cells of THIS orientation (the transposed array swaps them)
        rows = np.arange(ry) * n
        cols = np.arange(rx - 1) * n + n // 2
        Wf = W[rows][:, cols].reshape(-1, n + 2 * m, n)
        # The windows are independent: solve them in batches so that the block-diagonal system of a big board stays a few hundred thousand unknowns
        step = max(batch_pixels // ((n + 2 * m) * n), 1)
        flux = np.concatenate([local_flux(np.ascontiguousarray(Wf[k:k + step]), m) for k in range(0, len(Wf), step)])
        return flux.reshape(ry, rx - 1)

    return one(S), one(S.T).T
