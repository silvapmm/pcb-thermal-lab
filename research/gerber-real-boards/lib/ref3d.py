#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file ref3d.py
@brief An independent 3D finite-volume reference for a patterned multilayer board: copper masks per layer at the pixel, the laminate resolved through its thickness in sub-slabs, anisotropic FR-4, optional via barrels. Imports nothing from pcbthermal.
@details Written for the study of the copper mapping with the laminate rule of 2.4.5 ON (README section 10). The program's models put one node on every copper layer and cut the laminate only
         next to absent copper; this solver puts the real slabs on every pixel: copper layer (one slab of the copper thickness, conductivity of copper where the mask is set and of FR-4 where not),
         gap (n_sub equal slabs of FR-4, in-plane k_xy, through k_z), adiabatic sides, a film coefficient on the two faces. The heat is injected in the cells of the top copper slab (the node of the
         program's copper layer) and the temperature is read there, so that the reference and the program are compared at the same place (the face term of the laminate over bare copper is in neither).
         A via is a column of pixels in every gap slab whose through conductivity is raised by the copper of the barrel (k_cu * annulus area / pixels / pixel area): the same copper area the program uses, spread
         over the pixels of the drill disc (it adds no in-plane path, as a thin barrel does not).
         Rows of every array are from the BOTTOM of the board (y up), the convention of the program's fields.
         Tests (`tests/test_ref3d.py`): a series circuit (1D), the energy balance, the isotropic case against tests/helpers/layered3d.py, and convergence in n_sub.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

K_CU = 385.0           # W/mK, the program's copper
PLATING = 25e-6        # m, the program's barrel plating


def build(masks, dx, t_cu, gaps, kxy_lam=0.9, kz_lam=0.3, n_sub=8, k_cu=K_CU, vias=None, h_top=10.0, h_bottom=10.0):
    """!
    @brief The material arrays and the slab thicknesses of the board.
    @param masks List of boolean arrays (ny, nx), one per copper layer, top first, rows from the bottom (True = copper).
    @param dx Pixel size in m (square).
    @param t_cu Copper thickness in m (one value, or one per layer).
    @param gaps Thickness in m of every gap, top down (len(masks) - 1 values).
    @param kxy_lam In-plane conductivity of the laminate in W/mK.
    @param kz_lam Through conductivity of the laminate in W/mK.
    @param n_sub Sub-slabs of every gap.
    @param k_cu Copper conductivity in W/mK.
    @param vias Optional list of (x, y, drill diameter) in m, board coordinates (y up from the bottom edge).
    @param h_top Film coefficient on the top face in W/m2K (stored for solve()).
    @param h_bottom Film coefficient on the bottom face in W/m2K.
    @return dict with dz (nz,), kxy (nz, ny, nx), kz (nz, ny, nx), copper_slabs (index of every copper slab), h_top, h_bottom, dx.
    @throws ValueError If the number of gaps does not match the number of layers.
    """
    L = len(masks)
    if len(gaps) != L - 1:
        raise ValueError("a board of L copper layers has L - 1 gaps")
    tc = np.broadcast_to(np.asarray(t_cu, float), (L,))
    ny, nx = masks[0].shape
    dz, kxy, kz, cu = [], [], [], []
    for l in range(L):
        cu.append(len(dz))
        m = masks[l]
        dz.append(tc[l])
        kxy.append(np.where(m, k_cu, kxy_lam))
        kz.append(np.where(m, k_cu, kz_lam))
        if l < L - 1:
            kzg = np.full((ny, nx), kz_lam)
            if vias:
                # Raise the through conductivity of the pixels of each drill disc by the barrel copper spread over them (the barrel crosses every gap)
                yy, xx = (np.arange(ny) + 0.5) * dx, (np.arange(nx) + 0.5) * dx
                for vx, vy, d in vias:
                    r = d / 2.0
                    inside = (xx[None, :] - vx) ** 2 + (yy[:, None] - vy) ** 2 <= r * r
                    if not inside.any():
                        j, i = int(np.clip(vx // dx, 0, nx - 1)), int(np.clip(vy // dx, 0, ny - 1))
                        inside = np.zeros((ny, nx), bool)
                        inside[i, j] = True
                    a_cu = np.pi * (r * r - max(r - PLATING, 0.0) ** 2)
                    kzg[inside] += k_cu * a_cu / (inside.sum() * dx * dx)
            for _ in range(n_sub):
                dz.append(gaps[l] / n_sub)
                kxy.append(np.full((ny, nx), kxy_lam))
                kz.append(kzg)
    return {"dz": np.array(dz), "kxy": np.array(kxy), "kz": np.array(kz), "copper_slabs": cu, "h_top": h_top, "h_bottom": h_bottom, "dx": dx}


def solve(model, heater_mask, power, method="direct"):
    """!
    @brief Solve the steady rise for a heat source in the cells of the top copper slab.
    @param model Result of build().
    @param heater_mask Boolean (ny, nx) of the pixels that carry the heat (equal share each).
    @param power Heat in W.
    @param method "direct" (SuperLU) or "cg" (conjugate gradients with a Jacobi preconditioner, a check).
    @return dict with T (nz, ny, nx) rise in K, heat_out (W through the two films) and the top copper slab field top (ny, nx).
    """
    dz, kxy, kz, dx = model["dz"], model["kxy"], model["kz"], model["dx"]
    nz, ny, nx = kxy.shape
    A = dx * dx
    n = nz * ny * nx
    idx = np.arange(n).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)

    def link(a, b, g):
        """!
        @brief Add the conductance g (array) between the node arrays a and b.
        @param a Node indices.
        @param b Node indices.
        @param g Conductance in W/K.
        @return None.
        """
        a, b, g = a.ravel(), b.ravel(), np.broadcast_to(g, a.shape).ravel()
        rows.extend([a, b]); cols.extend([b, a]); vals.extend([-g, -g])
        np.add.at(diag, a, g); np.add.at(diag, b, g)

    for k in range(nz):
        a, b = kxy[k][:, :-1], kxy[k][:, 1:]
        link(idx[k, :, :-1], idx[k, :, 1:], dz[k] * 2.0 * a * b / (a + b))      # (face dz * dx) / dx with the harmonic mean of the two half cells
        a, b = kxy[k][:-1, :], kxy[k][1:, :]
        link(idx[k, :-1, :], idx[k, 1:, :], dz[k] * 2.0 * a * b / (a + b))
    for k in range(nz - 1):
        link(idx[k], idx[k + 1], A / (dz[k] / (2 * kz[k]) + dz[k + 1] / (2 * kz[k + 1])))
    # Films: half-cell conduction in series with the film
    g_top = A / (1.0 / model["h_top"] + dz[0] / (2 * kz[0])) if model["h_top"] > 0 else np.zeros((ny, nx))
    g_bot = A / (1.0 / model["h_bottom"] + dz[-1] / (2 * kz[-1])) if model["h_bottom"] > 0 else np.zeros((ny, nx))
    np.add.at(diag, idx[0].ravel(), np.broadcast_to(g_top, (ny, nx)).ravel())
    np.add.at(diag, idx[-1].ravel(), np.broadcast_to(g_bot, (ny, nx)).ravel())
    q = np.zeros(n)
    q[idx[0][heater_mask]] = power / heater_mask.sum()
    K = (sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)) + sp.diags(diag)).tocsr()
    if method == "direct":
        T = spla.splu(K.tocsc(), permc_spec="MMD_AT_PLUS_A").solve(q)
    else:
        dinv = 1.0 / K.diagonal()
        T, info = spla.cg(K, q, rtol=1e-12, atol=0.0, maxiter=200000, M=spla.LinearOperator(K.shape, matvec=lambda x: dinv * x))
        if info != 0:
            raise RuntimeError(f"CG did not converge ({info})")
    T = T.reshape(nz, ny, nx)
    heat_out = float((g_top * T[0]).sum() + (g_bot * T[-1]).sum())
    return {"T": T, "heat_out": heat_out, "top": T[model["copper_slabs"][0]]}


def heater_block(field, dx, x0, y0, x1, y1):
    """!
    @brief Mean and maximum of a field over the pixels whose centres lie in a rectangle.
    @param field Array (ny, nx), rows from the bottom.
    @param dx Pixel size in the same unit as the rectangle.
    @param x0 Left edge.
    @param y0 Bottom edge.
    @param x1 Right edge.
    @param y1 Top edge.
    @return tuple (mean, max).
    """
    ny, nx = field.shape
    xs, ys = (np.arange(nx) + 0.5) * dx, (np.arange(ny) + 0.5) * dx
    m = (xs[None, :] > x0) & (xs[None, :] < x1) & (ys[:, None] > y0) & (ys[:, None] < y1)
    return float(field[m].mean()), float(field[m].max())
