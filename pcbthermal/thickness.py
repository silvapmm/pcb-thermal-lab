#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file thickness.py
@brief The surface read-out of the outer copper faces: the temperature of a face from the node (the column mean) and the heat fluxes that enter through the faces. Always computed, for every steady FVM/FDM result.
@details The layered models keep ONE temperature per copper layer, the mean through the thickness (the COLUMN read-out, docs/theory.md 1.2). Where a flux crosses a layer of
         thickness t and conductivity k the face is hotter or cooler than that mean. A layer whose temperature varies slowly in the plane satisfies k t laplace(T_m) = -(q_top + q_bot)
         (q_top and q_bot the heat flux ENTERING through the two faces, z downwards), so the profile through the thickness is a parabola with T_z(0) = -q_top / k and T_z(t) = q_bot / k:
             T_top - T_m = t (2 q_top - q_bot) / (6 k),    T_bottom - T_m = t (2 q_bot - q_top) / (6 k).
         A column fed at the top and cooled at the bottom (q_bot = -q_top) gives the familiar q t / (2 k); heat that spreads sideways (q_bot = 0) gives q t / (3 k). The parabola is
         within 7 % of an independent 3D solution up to t/a = 0.5 (a the side of the source) and an UPPER estimate beyond (research/through-thickness-readout 4.2, validation 55.6).
         The surface is ALWAYS a second number beside the column, never a mode: no option, no project key (decision of the maintainer, releases/2.8.0/fem-model/SURFACE_DECISIONS.md).
         `attach` is called by the FVM and the FDM for EVERY steady result, with NO thickness or size threshold (the former 105 um limit and the 'worth showing' test are gone:
         the cost is 0 to 3 ms and no number of any model sees the arrays); the result holds (absolute temperatures in degC, NaN off the board and on a face that is not computed)
             arrays["T_surface"] (2, ny, nx)       top face of layer 1 and bottom face of the last layer, the HOTTEST value in the cell;
             arrays["T_surface_mean"] (2, ny, nx)  the same with the area mean of a partly filled cell;
             arrays["T_surface_flag"] (2, ny, nx)  bool, true under a part with t/a above UPPER_RATIO (the value is an upper estimate);
             extras["t_max_surface_top"], ["t_max_surface_bottom"], ["surface_excess_k"].
         The face fluxes: the heat of a part and the films on the outer face, the sum of the conductances to the other layers (laminate, inner copper, via couplings) on the inner face,
         the heat into a block on its face; the sideways flow is not a face flux. Partly filled cells: the copper term c uses the fluxes of the cell; the mean is f c plus the
         laminate face term of laminate.face_terms (already weighted by the bare share), the PEAK the larger of c and the laminate peak, never their sum (research README 7.1).
         Nothing here is read by the part rows' t_max, Tj, the margin, the power limit, the top-path split, the power coefficient, the Power Calculator or the calibration: they stay on the
         column (tests/test_thickness.py holds them bit-identical with and without the arrays).
         VALIDITY PER LAYER TYPE. Outer copper (top of layer 1, bottom of the last layer; both faces of a one-layer board): the formula applies at every thickness; on 35 um copper it is
         correct and tiny (0.4 to 5.6 mK on the harness boards). Inner copper: no outer face and no flux to define one (its faces are interfaces with the laminate, where the temperature is
         continuous), so the surface IS the column ('equal'); no array is made for it. Laminate: resolved through its thickness by the sub-gap nodes, so its face is a node (nothing to
         estimate). Metal blocks: ONE node through the block's thickness (blocks.py), so the block face is NOT resolved and has no surface read-out (the thick-plate warning
         gives its bound); the heat into a block is a face flux of the copper layer it sits on.
         CONTRACT FOR ANOTHER MODEL (the FEM of feature/fem-model will fill these): a SteadyResult with T (layers, ny, nx) in degC may carry arrays["T_surface"],
         ["T_surface_mean"] (float, shape (2, ny, nx), degC, face 0 the top of layer 1 and face 1 the bottom of the last layer, NaN off the board and on a face not computed),
         ["T_surface_flag"] (bool, (2, ny, nx), True where the value is an upper estimate; a computed face has none) and extras["t_max_surface_top"], ["t_max_surface_bottom"]
         (float degC, the nanmax of each finite face, absent for a face not computed) and ["surface_excess_k"] (float K). Every reader (analysis.surface_stats, api.surface_report_lines,
         plots.draw_surface, the Layer box, the part table, Simulation.save) needs only these names and shapes, so a model that fills them gets the whole display.
         THE THIN-COPPER TRAP: on a patterned board the surface under a source over ABSENT copper includes the rise across the bare laminate (the face term of laminate.face_terms):
         the surface can be 1 to 4 K above the node maximum on 35 um copper although the copper term is milli-kelvin. The part rows already include that term in their 'column' maximum,
         so there surface minus column is the copper term only. Never gate anything on the board-level difference (surface_excess_k).
         NOT modelled: the Lumped and the Analytic (no per-cell face flux and no face term today), the 3D solid (its own branch), blocks, the transient and the profiles (steady state only).
"""

import numpy as np

from .geometry import points_in_polygon, polygon_area

UPPER_RATIO = 0.5                          # t / a above this: the parabola overshoots, the surface is an upper estimate (research README 4.2)


def offsets(t, k, q_top, q_bot):
    """!
    @brief Surface-minus-column-mean temperature of the two faces of a layer (parabolic profile through the thickness).
    @param t Layer thickness in m.
    @param k Through-thickness conductivity of the layer in W/mK.
    @param q_top Net heat flux entering through the top face in W/m2 (positive in; scalar or array).
    @param q_bot Net heat flux entering through the bottom face in W/m2 (a face that loses heat has a negative value).
    @return Tuple (d_top, d_bottom) in K, shaped like the fluxes.
    """
    q_top, q_bot = np.asarray(q_top, dtype=float), np.asarray(q_bot, dtype=float)
    return t * (2.0 * q_top - q_bot) / (6.0 * k), t * (2.0 * q_bot - q_top) / (6.0 * k)


def column_bound(t, k, q):
    """!
    @brief The bound q t / (2 k) of the thick-plate warning (a column fed at the top and cooled at the bottom).
    @param t Layer thickness in m.
    @param k Conductivity in W/mK.
    @param q Flux through the layer in W/m2.
    @return Temperature difference in K.
    """
    return np.abs(q) * t / (2.0 * k)


def _couplings_out(net, theta, layer):
    """!
    @brief Heat leaving the nodes of one layer through its couplings to nodes of OTHER layers, split into the blocks (by face) and everything else.
    @details Reads the off-diagonal entries of the conductance matrix K of the network, so that the laminate sub-nodes, the inner copper, the contact of a block and the
             couplings of the vias are all counted, whatever their arrangement. The couplings to nodes of the same layer are the sideways flow and are left out.
    @param net A fvm.Network or fdm.Network with the matrix K built.
    @param theta Rise of all node layers, shape (layers, ny, nx), in kelvin.
    @param layer Index of the node layer.
    @return Tuple (inner, block_top, block_bottom) of arrays (ny, nx) in W (positive: heat leaves the node).
    """
    ny, nx = theta.shape[1:]
    n = ny * nx
    sub = net.K.tocsr()[layer * n:(layer + 1) * n].tocoo()
    th = theta.ravel()
    col_layer = sub.col // n
    off = col_layer != layer
    r, c, g = sub.row[off], sub.col[off], -sub.data[off]
    heat = g * (th[layer * n + r] - th[c])
    block_face = {bi["layer"]: bi["face"] for bi in net.block_info}
    is_block = np.isin(col_layer[off], list(block_face)) if block_face else np.zeros(len(r), dtype=bool)
    inner = np.bincount(r[~is_block], weights=heat[~is_block], minlength=n).reshape(ny, nx)
    out_block = [np.zeros(n), np.zeros(n)]
    for lay, face in block_face.items():
        sel = is_block & (col_layer[off] == lay)
        out_block[face] += np.bincount(r[sel], weights=heat[sel], minlength=n)
    return inner, out_block[0].reshape(ny, nx), out_block[1].reshape(ny, nx)


def _upper_flags(problem, res, faces):
    """!
    @brief Cells under a part whose source is wide against the plate it sits on the wrong way round: t / a above UPPER_RATIO, where the parabola is an upper estimate.
    @param problem The Problem.
    @param res SteadyResult (gives the sample positions).
    @param faces List [(face index 0 or 1, layer index)] of the outer faces that were computed.
    @return Boolean array (2, ny, nx).
    """
    ny, nx = res.T.shape[1:]
    flag = np.zeros((2, ny, nx), dtype=bool)
    xs, ys = res.coords()
    X, Y = np.meshgrid(xs, ys)
    b = problem.board
    for face, layer in faces:
        t = float(b.copper_thickness[layer])
        for h in problem.heaters:
            on_face = (h.layer == layer) if b.layers > 1 else True
            a = float(np.sqrt(max(polygon_area(h.polygon), 0.0)))
            if on_face and a > 0 and t / a > UPPER_RATIO:
                flag[face] |= points_in_polygon(X.ravel(), Y.ravel(), h.polygon).reshape(X.shape)
    return flag


def _finish(res, problem, d, fill, faces, area):
    """!
    @brief Turn the copper terms of the outer faces into the arrays of the result (the FVM and the FDM; written so that a model without partial cells can pass fill None).
    @param res SteadyResult.
    @param problem The Problem.
    @param d Dict {face: copper term in K per cell}, faces 0 (top of layer 1) and 1 (bottom of the last layer).
    @param fill Copper fill of the layers (layers, ny, nx), or None for a uniform sheet (no partial cells).
    @param faces List of (face, layer) to fill.
    @param area Board area of every cell (ny, nx) in m2; cells with no board get no offset.
    """
    ny, nx = res.T.shape[1:]
    surf, surf_mean = np.zeros((2, ny, nx)), np.zeros((2, ny, nx))
    on = area > 0
    for face, layer in faces:
        c = np.where(on, d[face], 0.0)
        T = res.T[layer]
        if fill is None:
            peak, mean = c, c
        else:
            f = fill[layer]
            fp = res.arrays["face_peak"][layer] if "face_peak" in res.arrays else np.zeros_like(c)
            fm = res.arrays["face_mean"][layer] if "face_mean" in res.arrays else np.zeros_like(c)
            c_cu = np.where(f > 0, c, 0.0)
            # The hottest point of a partly filled cell is over the bare laminate: the larger of the two terms; where the laminate term is absent the copper term is the peak
            # (and a cell without copper and without a laminate term has no offset: the copper term of an empty cell has no meaning, as in the mean f c)
            peak = np.where(fp > 0, np.maximum(c_cu, fp), c_cu)
            mean = f * c + fm
        surf[face], surf_mean[face] = T + peak, T + mean
    for face in (0, 1):                                                       # A face that is not computed, or off the board, has no surface value
        if face not in {f for f, _ in faces}:
            surf[face], surf_mean[face] = np.nan, np.nan
        surf[face][~on], surf_mean[face][~on] = np.nan, np.nan
    res.arrays["T_surface"] = surf
    res.arrays["T_surface_mean"] = surf_mean
    res.arrays["T_surface_flag"] = _upper_flags(problem, res, faces)
    exc = [float(np.nanmax(np.abs(surf[f] - res.T[ly]))) for f, ly in faces]
    res.extras["surface_excess_k"] = max(exc)
    # Extras are plain numbers that go to JSON: a face that was not computed has no entry
    for face, key in ((0, "t_max_surface_top"), (1, "t_max_surface_bottom")):
        if np.isfinite(surf[face]).any():
            res.extras[key] = float(np.nanmax(surf[face]))


def attach(res, net, theta, cell, problem):
    """!
    @brief Add the surface arrays of the outer copper faces to the result of the FVM or the FDM (every board, every thickness).
    @details Called with the solved rise of ALL node layers; nothing that exists is changed. The face fluxes are those of the module docstring; the heat of a part enters the
             face it sits on (layer 1: top, the last layer: bottom, a one-layer board: top).
    @param res SteadyResult of the board (T on the board layers, arrays face_peak and face_mean when the laminate rule made them).
    @param net The Network (fvm or fdm) with K, Q, g_top, g_bottom, g_heatsink, fill and block_info.
    @param theta Rise of all node layers (board first, then laminate and block nodes) in kelvin.
    @param cell Board area of every cell or node (ny, nx) in m2.
    @param problem The Problem that was solved.
    """
    b = problem.board
    L = b.layers
    t_cu = np.asarray(b.copper_thickness, dtype=float)
    k_cu = b.materials.k_copper
    area = np.where(cell > 0, cell, 1.0)
    d, faces = {}, []
    # (layer, face of its heat source and of its outer film); a one-layer board has both faces on layer 0
    plan = [(0, 0)] if L == 1 else [(0, 0), (L - 1, 1)]
    for layer, face in plan:
        inner, blk_top, blk_bot = _couplings_out(net, theta, layer)
        th = theta[layer]
        q = net.Q[layer]
        film_top = (net.g_top[layer] + (net.g_heatsink[layer] if face == 0 else 0.0)) * th
        film_bot = (net.g_bottom[layer] + (net.g_heatsink[layer] if face == 1 else 0.0)) * th
        src_top, src_bot = (q, 0.0) if face == 0 else (0.0, q)
        # Heat entering through the faces, W per cell: the part and the films on the outer face, the other layers on the inner face, the block on its face
        if face == 0:
            q_top = src_top - film_top - blk_top
            q_bot = -inner - film_bot - blk_bot
        else:
            q_top = -inner - film_top - blk_top
            q_bot = src_bot - film_bot - blk_bot
        if L == 1:
            q_top = src_top - film_top - blk_top
            q_bot = -inner - film_bot - blk_bot
        d_top, d_bot = offsets(t_cu[layer], k_cu, q_top / area, q_bot / area)
        d[face] = d_top if face == 0 else d_bot
        faces.append((face, layer))
        if L == 1:
            d[1] = d_bot
            faces.append((1, 0))
    _finish(res, problem, d, net.fill, faces, cell)
