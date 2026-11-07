#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file strip2d.py
@brief Independent two-dimensional finite-volume solver for a homogeneous slab with a strip on its top face (isoflux or isothermal), films on the two faces and insulated ends.
@details The half cell of the papers: a strip of half-width `w` at the corner of a slab of half-width `L` and thickness `t` (the ends x = 0 and x = L are insulated by symmetry).
         Cell-centred finite volumes on a graded grid (cells refined towards the strip edge and the heated face), the conductance between two cells is the series of the two
         half-cell resistances, the top face is a prescribed flux (isoflux strip) or a prescribed temperature (isothermal strip, through the half-cell conductance) on the strip and a
         film `h_top` elsewhere, the bottom face a film `h_bottom` or a fixed temperature (`h_bottom = None`). Imports nothing from the program. Results are per unit depth
         (W/m for a flux, K for a temperature).
"""

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


def graded_edges(length, h_min, focus, ratio=1.15, h_max=None):
    """!
    @brief Cell edges on [0, length] with the smallest cell h_min at `focus` and cells growing by `ratio` away from it.
    @param length Length of the interval in m.
    @param h_min Smallest cell in m.
    @param focus Position of the refinement in m (0 <= focus <= length); it is always an edge.
    @param ratio Growth ratio of consecutive cells (> 1).
    @param h_max Largest allowed cell in m (default length / 20).
    @return numpy.ndarray Increasing array of edges from 0 to `length`.
    """
    h_max = h_max or length / 20.0
    pts = {0.0, float(focus), float(length)}
    for sign, stop in ((1.0, length), (-1.0, 0.0)):             # cells grow away from the focus, to the right and to the left
        x, h = focus, h_min
        while (x - stop) * sign < -1e-15:
            x = x + sign * h
            x = min(x, stop) if sign > 0 else max(x, stop)
            pts.add(float(x))
            h = min(h * ratio, h_max)
    e = np.array(sorted(pts))
    keep = [e[0]]
    for v in e[1:]:                                              # drop slivers produced by the clipping at the ends
        if v - keep[-1] > 1e-6 * h_min:
            keep.append(v)
    return np.array(keep)


def solve(xe, ze, k, strip_w, mode, value, h_top, h_bottom, film_under_strip=False):
    """!
    @brief Solve the slab.
    @param xe Cell edges along x in m (x = 0 under the strip's symmetry end, x = xe[-1] the far end); strip_w must be one of them.
    @param ze Cell edges along z in m, z = 0 the top face, z = ze[-1] the bottom face.
    @param k Conductivity in W/mK (isotropic).
    @param strip_w Width of the strip in m (x from 0 to strip_w).
    @param mode "flux" (value = flux in W/m2 into the strip) or "temp" (value = strip temperature in K above the sink).
    @param value Flux in W/m2 or temperature in K.
    @param h_top Film coefficient on the top face outside the strip in W/m2K (0 = insulated).
    @param h_bottom Film coefficient on the bottom face in W/m2K, or None for a bottom held at 0 K (Biot infinite).
    @param film_under_strip True: the top film also acts on the strip (the case (a) of Lemczyk and others, and the program); False: the strip area is insulated apart from the strip itself.
    @return dict with T (nz x nx, K), q_strip (W/m entering through the strip), q_total (W/m: q_strip plus the film under the strip), t_face_mean (strip face temperature, mean over the strip), x, z, dx, dz.
    @throws ValueError If strip_w is not a cell edge.
    """
    if not np.any(np.isclose(xe, strip_w, rtol=0, atol=1e-12)):
        raise ValueError("strip_w must be a cell edge")
    dx, dz = np.diff(xe), np.diff(ze)
    nx, nz = len(dx), len(dz)
    xc = 0.5 * (xe[:-1] + xe[1:])
    zc = 0.5 * (ze[:-1] + ze[1:])
    idx = np.arange(nz * nx).reshape(nz, nx)
    rows, cols, vals = [], [], []
    diag = np.zeros(nz * nx)
    rhs = np.zeros(nz * nx)

    def link(a, b, g):
        """!
        @brief Add the symmetric conductance g between the node index arrays a and b.
        @param a Node indices.
        @param b Node indices.
        @param g Conductance in W/mK x m (per unit depth).
        @return None.
        """
        a, b, g = a.ravel(), b.ravel(), np.asarray(g).ravel()
        rows.extend([a, b]); cols.extend([b, a]); vals.extend([-g, -g])
        np.add.at(diag, a, g); np.add.at(diag, b, g)

    link(idx[:, :-1], idx[:, 1:], k * (dz[:, None] / (0.5 * (dx[:-1] + dx[1:]))[None, :]))   # across x
    link(idx[:-1, :], idx[1:, :], k * (dx[None, :] / (0.5 * (dz[:-1] + dz[1:]))[:, None]))   # across z
    on = xc < strip_w                                            # cells whose top face is the strip
    top = idx[0]
    half_top = k * dx / (0.5 * dz[0])                            # centre-to-face conductance of the top cells
    h_t = max(h_top, 0.0)
    g_film = np.where(h_t > 0, 1.0 / (1.0 / half_top + 1.0 / (max(h_t, 1e-300) * dx)), 0.0)   # centre-to-ambient through half a cell and the film
    if mode == "flux":
        rhs[top[on]] += value * dx[on]
        diag[top] += np.where(on, g_film if film_under_strip else 0.0, g_film)
    else:
        diag[top] += np.where(on, half_top, 0.0)                 # the strip face is held at `value`
        rhs[top] += np.where(on, half_top * value, 0.0)
        diag[top] += np.where(on, g_film if film_under_strip else 0.0, g_film)
        # the film under the strip cools the strip face (held at `value`), not the cell centre: its heat is added to q_total below, not to the matrix
        if film_under_strip:
            diag[top] -= np.where(on, g_film, 0.0)
    bot = idx[-1]
    half_bot = k * dx / (0.5 * dz[-1])
    if h_bottom is None:
        diag[bot] += half_bot
    elif h_bottom > 0:                                           # h_bottom = 0: an insulated bottom
        diag[bot] += 1.0 / (1.0 / half_bot + 1.0 / (h_bottom * dx))
    mat = sp.coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nz * nx,) * 2).tocsr() + sp.diags(diag)
    T = spla.spsolve(mat.tocsc(), rhs).reshape(nz, nx)
    if mode == "flux":
        face = T[0] + np.where(on, value * dz[0] / (2 * k), 0.0)
        q_strip = float(value * dx[on].sum())
        t_face = float((face[on] * dx[on]).sum() / dx[on].sum())
        film_strip = 0.0
        if film_under_strip and h_t > 0:                         # film over the strip: heat leaves the strip face at its own temperature
            film_strip = float((h_t * face[on] * dx[on]).sum())
        q_total = q_strip                                        # the power injected is q_strip; the film under it is part of the loss, not an addition
    else:
        q_strip = float((half_top * (value - T[0]))[on].sum())
        t_face = float(value)
        film_strip = float(h_t * value * dx[on].sum()) if film_under_strip else 0.0
        q_total = q_strip + film_strip
    return {"T": T, "q_strip": q_strip, "q_total": q_total, "film_strip": film_strip, "t_face_mean": t_face, "x": xc, "z": zc, "dx": dx, "dz": dz}
