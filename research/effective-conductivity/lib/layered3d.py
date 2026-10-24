"""!
@file layered3d.py
@brief A small independent 3D finite-volume conduction solver for a laminated block (layers of different conductivity, convection on the two faces, adiabatic sides).
@details Written to repeat the test coupons of the literature (Culham and Yovanovich, Lee) without using any model of the program: a structured grid of nx x ny cells in the
         plane and the given slabs through the thickness, conductivity uniform in a slab (isotropic), harmonic mean of the half-cell resistances between neighbours, heat flux
         applied to a rectangle of the top face, convection (a film coefficient) on the rest of the top face and on the bottom face, the four sides insulated.
         Temperatures are rises over the ambient.
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def solve(dx, nx, ny, slabs, source, power, h_top, h_bottom, film_under_source=False):
    """!
    @brief Solve the steady temperature rise of a laminated block with a flux on a rectangle of the top face.
    @param dx Cell size in the plane in m (square cells).
    @param nx Cells along x.
    @param ny Cells along y.
    @param slabs List of (thickness in m, conductivity in W/mK, number of sub-slabs) from the top down.
    @param source Tuple (x0, y0, x1, y1) of the heated rectangle on the top face in m, measured from the corner; its edges must lie on cell edges. A list of such tuples is accepted too (several sources).
    @param power Heat flowing into the source rectangle in W (a list with one value per rectangle when `source` is a list).
    @param h_top Film coefficient on the top face outside the source in W/m2K (0 = insulated).
    @param h_bottom Film coefficient on the bottom face in W/m2K.
    @param film_under_source True: the film coefficient also acts on the top face under the source (as the program does); False: the source area is insulated (as in the papers).
    @return dict with T (array nz x ny x nx, rise in K), dz (list), area_source, mask_source (ny x nx bool), mean_source, max_source, mean_wall.
    @throws ValueError If the source does not fit in the block.
    """
    dz, kz = [], []
    for t, k, n in slabs:
        dz += [t / n] * n
        kz += [k] * n
    dz, kz = np.array(dz), np.array(kz)
    nz = len(dz)
    xs = (np.arange(nx) + 0.5) * dx
    ys = (np.arange(ny) + 0.5) * dx
    multi = isinstance(source[0], (tuple, list))
    rects = list(source) if multi else [source]
    powers = list(power) if multi else [power]
    masks = [(xs[None, :] > r[0]) & (xs[None, :] < r[2]) & (ys[:, None] > r[1]) & (ys[:, None] < r[3]) for r in rects]
    mask = np.logical_or.reduce(masks)
    if not mask.any():
        raise ValueError("the source rectangle covers no cell")
    area = dx * dx
    n = nz * ny * nx
    idx = np.arange(n).reshape(nz, ny, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)

    def link(a, b, g):
        """!
        @brief Add the conductance g between the node arrays a and b (symmetric).
        @param a Node indices.
        @param b Node indices.
        @param g Conductance (scalar or array) in W/K.
        @return None.
        """
        g = np.broadcast_to(g, a.shape)
        rows.extend([a.ravel(), b.ravel()]); cols.extend([b.ravel(), a.ravel()]); vals.extend([-g.ravel(), -g.ravel()])
        np.add.at(diag, a.ravel(), g.ravel()); np.add.at(diag, b.ravel(), g.ravel())

    for k in range(nz):                                          # in-plane links of every slab (uniform k)
        g = kz[k] * dz[k]                                         # k * dz * dy / dx with dy = dx
        link(idx[k, :, :-1], idx[k, :, 1:], g)
        link(idx[k, :-1, :], idx[k, 1:, :], g)
    for k in range(nz - 1):                                      # vertical links: half-cell resistances in series
        r = dz[k] / (2 * kz[k] * area) + dz[k + 1] / (2 * kz[k + 1] * area)
        link(idx[k], idx[k + 1], 1.0 / r)
    q = np.zeros(n)
    top, bot = idx[0], idx[-1]
    with np.errstate(divide="ignore"):
        gt = 0.0 if h_top <= 0 else 1.0 / (dz[0] / (2 * kz[0] * area) + 1.0 / (h_top * area))
        gb = 0.0 if h_bottom <= 0 else 1.0 / (dz[-1] / (2 * kz[-1] * area) + 1.0 / (h_bottom * area))
    free_top = np.ones_like(mask) if film_under_source else ~mask
    np.add.at(diag, top[free_top], gt)
    np.add.at(diag, bot.ravel(), gb)
    qcell = np.zeros(mask.shape)
    for m, pw in zip(masks, powers):
        qcell[m] += pw / m.sum()                                 # the power of each source spread uniformly over its cells
    q[top[mask]] = qcell[mask]
    K = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr() + sp.diags(diag)
    T = spla.spsolve(K.tocsc(), q).reshape(nz, ny, nx)
    # surface temperatures: the cell-centre value corrected by the half-cell resistance (heated cells) or divided between the half cell and the film (convecting cells)
    rh_top = dz[0] / (2 * kz[0] * area)
    rh_bot = dz[-1] / (2 * kz[-1] * area)
    t_src = T[0][mask] + qcell[mask] * rh_top
    walls = []
    heat_out = 0.0                                                # heat leaving through the films, for the energy balance
    if h_top > 0:
        walls.append(T[0][free_top] * (1.0 / (h_top * area)) / (rh_top + 1.0 / (h_top * area)))
        heat_out += float((h_top * area * walls[-1]).sum())
    if h_bottom > 0:
        walls.append(T[-1].ravel() * (1.0 / (h_bottom * area)) / (rh_bot + 1.0 / (h_bottom * area)))
        heat_out += float((h_bottom * area * walls[-1]).sum())
    return {"T": T, "dz": list(dz), "area_source": mask.sum() * area, "mask_source": mask, "mean_source": float(t_src.mean()),
            "max_source": float(t_src.max()), "cell_mean_source": float(T[0][mask].mean()), "cell_max_source": float(T[0][mask].max()), "per_source": [{"mean": float((T[0][m] + qcell[m] * rh_top).mean()), "cell_mean": float(T[0][m].mean())} for m in masks], "surface_top": T[0] + qcell * rh_top, "heat_out": heat_out, "mean_wall": float(np.concatenate(walls).mean()) if walls else 0.0}


def solid_resistance(res, power):
    """!
    @brief Solid-body resistance of Culham and Yovanovich: (mean source temperature - mean wall temperature) / power.
    @param res Result of solve().
    @param power Heat in W.
    @return float Resistance in K/W.
    """
    return (res["mean_source"] - res["mean_wall"]) / power


def effective_conductivity(dx, nx, ny, total_thickness, source, power, h_top, h_bottom, target, n_sub=8, lo=0.05, hi=2000.0):
    """!
    @brief Conductivity of a single-layer block of the same thickness and boundary conditions that has the same solid-body resistance (the definition of the paper).
    @param dx Cell size in m.
    @param nx Cells along x.
    @param ny Cells along y.
    @param total_thickness Thickness of the block in m.
    @param source Source rectangle (see solve()).
    @param power Heat in W.
    @param h_top Film coefficient on the top face in W/m2K.
    @param h_bottom Film coefficient on the bottom face in W/m2K.
    @param target Solid-body resistance of the laminate in K/W.
    @param n_sub Sub-slabs through the single layer.
    @param lo Lower bracket of the conductivity in W/mK.
    @param hi Upper bracket of the conductivity in W/mK.
    @return float Effective conductivity in W/mK (bisection on the logarithm of k; the resistance falls as k grows).
    """
    a, b = np.log(lo), np.log(hi)
    for _ in range(40):
        m = 0.5 * (a + b)
        r = solid_resistance(solve(dx, nx, ny, [(total_thickness, float(np.exp(m)), n_sub)], source, power, h_top, h_bottom), power)
        if r > target:
            a = m                                                # too resistive: a larger conductivity is needed
        else:
            b = m
    return float(np.exp(0.5 * (a + b)))
