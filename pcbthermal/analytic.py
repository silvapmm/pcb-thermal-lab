"""!
@file analytic.py
@brief Closed-form multilayer fin model: exact modal solution for a uniform board.

@details Every layer is a thin sheet with lateral conductance S_l [W/K] (copper fill and FR-4
in-plane share), coupled to its neighbours through the dielectric conductance per unit area
g = (k_fr4_through / d) + smeared vias, and to ambient through h_top (layer 1) and h_bottom
(last layer). With insulated edges the steady rise theta_l(x, y) of layer l obeys

    S_l * laplacian(theta_l) - h_l * theta_l - g * (2*theta_l - theta_{l-1} - theta_{l+1}) = -q_l

(the coupling terms drop at the outer layers). Expanding in cosines

    theta_l = sum_{m,n} a_{l,mn} cos(m pi x / W) cos(n pi y / H)

decouples the equation by mode: for every (m, n) a small tridiagonal L x L system is solved,

    ( diag(S_l * k_mn^2 + h_l) + g * graph_laplacian ) a_mn = q_mn,  k_mn^2 = (m pi/W)^2 + (n pi/H)^2,

where q_mn is the cosine projection of the heaters (analytic for rectangles). The a_00 mode is
the uniform-board limit P / (h W H); the other modes add the lateral spreading penalty. The
model needs laterally uniform properties, with these refinements:

- Copper fill is averaged per layer with a weight equal to the influence of the heaters
  (the fin Green function K0(r / lambda), lambda = sqrt(S / h)), so copper near a heater counts
  more than copper far away.
- Vias and sinks are local. They are removed from the uniform problem and added back through
  a Green-function (Woodbury) correction: the board is cut into tiles of a few millimetres,
  every tile with a via or a sink gets a lumped conductance, and the small dense system
  (I + G C) y = y0 gives the tile temperatures, where G is the modal response of the uniform
  board and C holds the local conductances.
- A validity check adds warnings when the copper is far from uniform around the heaters.
Strongly non-uniform copper is still beyond this model: use the FVM then.
"""

import numpy as np

from scipy.special import k0

from .geometry import coverage_fraction, polygon_area, polygon_centroid
from .results import SteadyResult


def _equivalent_rectangle(poly, width, height):
    """!
    @brief Axis-aligned rectangle with the same area and centroid as a polygon.
    @details The aspect ratio is taken from the polygon bounding box and the rectangle is
             shifted, if needed, to stay inside the board.
    @param poly Polygon vertices (n, 2) in metres.
    @param width Board width in metres.
    @param height Board height in metres.
    @return Tuple (x1, x2, y1, y2) in metres.
    """
    p = np.asarray(poly, dtype=float)
    area = polygon_area(p)
    bw = p[:, 0].max() - p[:, 0].min()
    bh = p[:, 1].max() - p[:, 1].min()
    # Scale the bounding box so that its area equals the polygon area
    s = np.sqrt(area / (bw * bh)) if bw * bh > 0 else 1.0
    w, h = bw * s, bh * s
    cx, cy = polygon_centroid(p)
    x1 = min(max(cx - w / 2, 0.0), width - w)
    y1 = min(max(cy - h / 2, 0.0), height - h)
    return x1, x1 + w, y1, y1 + h


def _cos_projection(lo, hi, length, n_terms):
    """!
    @brief Integral of cos(m pi x / length) over [lo, hi] for m = 0..n_terms-1.
    @param lo Lower bound in metres.
    @param hi Upper bound in metres.
    @param length Domain length in metres.
    @param n_terms Number of cosine modes.
    @return Array of shape (n_terms,).
    """
    m = np.arange(n_terms)
    out = np.empty(n_terms)
    out[0] = hi - lo
    k = m[1:] * np.pi / length
    out[1:] = (np.sin(k * hi) - np.sin(k * lo)) / k
    return out




def _tile_grid(W, H, lam):
    """!
    @brief Tile grid used for the local corrections.
    @param W Board width (m).
    @param H Board height (m).
    @param lam Fin length lambda = sqrt(S / h) (m).
    @return Tuple (ntx, nty, tw, th): tile counts and tile size in metres.
    """
    target = min(max(lam / 4.0, 2.5e-3), 5e-3)            # Tiles between 2.5 and 5 mm, below lambda / 4
    ntx = max(int(np.ceil(W / target)), 1)
    nty = max(int(np.ceil(H / target)), 1)
    return ntx, nty, W / ntx, H / nty


def solve_steady(problem, cell_mm=1.0, n_terms=300, local_corrections=True):
    """!
    @brief Analytic steady-state solution of the multilayer fin problem.
    @param problem A Problem.
    @param cell_mm Cell size (mm) of the sampling grid used for the fields and the maxima.
    @param n_terms Number of cosine modes per direction (300 resolves heaters of a few mm).
    @param local_corrections If True vias and sinks are applied locally (Green-function update);
                             if False they are smeared over the board (the older, cruder model).
    @return SteadyResult with one field per layer, T of shape (layers, ny, nx).
    """
    problem.validate()
    b = problem.board
    m = b.materials
    W, H, L = b.width, b.height, b.layers
    slab = b.thickness / L
    nx = max(int(round(W * 1000.0 / cell_mm)), 2)
    ny = max(int(round(H * 1000.0 / cell_mm)), 2)
    dx, dy = W / nx, H / ny
    xs = (np.arange(nx) + 0.5) * dx
    ys = (np.arange(ny) + 0.5) * dy
    tc = np.asarray(b.copper_thickness)
    power = problem.total_power()
    warnings = []

    # --- Copper fill field of every layer and its heater-influence weighted average
    fill_map = np.zeros((L, ny, nx))
    for z in problem.zones:
        fill_map[z.layer] = np.maximum(fill_map[z.layer],
                                       coverage_fraction(z.polygon, nx, ny, dx, dy, 4) * z.fill)
    h_tot = float(b.h_top + b.h_bottom)
    d_diel = b.dielectric_thickness()
    g_diel = m.k_fr4_through / d_diel if L > 1 else 0.0                   # Vertical conductance per area (W/m2K)
    fill_mean = fill_map.mean(axis=(1, 2))
    S_mean = fill_mean * m.k_copper * tc + m.k_fr4_inplane * (slab - fill_mean * tc)
    lam = float(np.sqrt(S_mean.sum() / h_tot)) if h_tot > 0 else W        # Spreading length of the whole stack
    centres = [(polygon_centroid(h.polygon), np.sqrt(polygon_area(h.polygon) / np.pi), h.power, h.layer)
               for h in problem.heaters if h.power > 0]
    fill = fill_mean.copy()
    if centres:
        # A layer that carries a heater loses heat vertically within a few millimetres, so the copper that matters
        # is much closer than the stack length: use the layer's own length sqrt(S / (h + n_neighbours * g)).
        heater_layers = {c[3] for c in centres}
        spread = np.zeros(L)
        for l in range(L):
            if l in heater_layers:
                n_nb = (l > 0) + (l < L - 1)
                h_surf = (b.h_top if l == 0 else 0.0) + (b.h_bottom if l == L - 1 else 0.0)
                lam_l = float(np.sqrt(S_mean[l] / max(h_surf + n_nb * g_diel, 1e-9)))
            else:
                lam_l = lam
            w = np.zeros((ny, nx))
            for (cx, cy), r0, pw, _ in centres:
                dist = np.maximum(np.hypot(xs[None, :] - cx, ys[:, None] - cy), max(r0, 0.5 * dx))
                w += pw * k0(dist / lam_l)                  # Influence of the heater at this distance
            fill[l] = (fill_map[l] * w).sum() / w.sum()
            spread[l] = np.sqrt(((fill_map[l] - fill[l]) ** 2 * w).sum() / w.sum())
        if spread.max() > 0.25:
            warnings.append(
                f"copper coverage varies strongly around the heaters (spread {spread.max():.2f}); "
                "the uniform-sheet assumption is weak, the FVM result is more reliable")
    S = fill * m.k_copper * tc + m.k_fr4_inplane * (slab - fill * tc)           # (L,)

    # --- Surface coefficients and vertical conductance of the uniform problem
    h_l = np.zeros(L)
    h_l[0] += b.h_top
    h_l[L - 1] += b.h_bottom
    g = g_diel
    if not local_corrections:
        for s in problem.sinks:
            h_l[s.layer] += s.h_extra * polygon_area(s.polygon) / (W * H)
        if L > 1:
            g += m.k_copper * sum(v.copper_area(b.via_plating) for v in problem.vias) / (W * H) / d_diel

    # --- Cosine coefficients of the heaters, one vector entry per layer
    M = N = n_terms
    q_mn = np.zeros((M, N, L))
    ex = np.where(np.arange(M) == 0, 1.0, 2.0)
    ey = np.where(np.arange(N) == 0, 1.0, 2.0)
    for ht in problem.heaters:
        x1, x2, y1, y2 = _equivalent_rectangle(ht.polygon, W, H)
        q0 = ht.power / ((x2 - x1) * (y2 - y1))              # Power density (W/m2)
        px = _cos_projection(x1, x2, W, M)
        py = _cos_projection(y1, y2, H, N)
        q_mn[:, :, ht.layer] += q0 * np.outer(ex * px, ey * py) / (W * H)

    # --- Modal matrices A_mn (L x L) and their inverses
    k2 = ((np.arange(M) * np.pi / W) ** 2)[:, None] + ((np.arange(N) * np.pi / H) ** 2)[None, :]
    A = np.zeros((M, N, L, L))
    for l in range(L):
        A[:, :, l, l] = S[l] * k2 + h_l[l]
        if l > 0:
            A[:, :, l, l] += g
            A[:, :, l, l - 1] -= g
        if l < L - 1:
            A[:, :, l, l] += g
            A[:, :, l, l + 1] -= g
    Ainv = np.linalg.inv(A)                                  # (M, N, L, L)
    a_mn = np.einsum("mnlk,mnk->mnl", Ainv, q_mn)            # (M, N, L)

    # --- Local corrections for vias and sinks through the tile Green-function system
    sink_extraction = 0.0
    if local_corrections and (problem.vias or problem.sinks):
        ntx, nty, tw, th = _tile_grid(W, H, lam)
        c_via = np.zeros((nty, ntx))
        for v in problem.vias:
            a = min(max(int(v.x // tw), 0), ntx - 1)
            bb = min(max(int(v.y // th), 0), nty - 1)
            c_via[bb, a] += m.k_copper * v.copper_area(b.via_plating) / d_diel if L > 1 else 0.0
        g_sink = np.zeros((L, nty, ntx))
        for s in problem.sinks:
            g_sink[s.layer] += s.h_extra * tw * th * coverage_fraction(s.polygon, ntx, nty, tw, th, 8)
        active = np.argwhere((c_via > 0) | (g_sink.sum(axis=0) > 0))        # (Nt, 2) = (row, col)
        Nt = len(active)
        if Nt:
            rect = [(c * tw, (c + 1) * tw, r * th, (r + 1) * th) for r, c in active]
            PX = np.stack([_cos_projection(x1, x2, W, M) for x1, x2, _, _ in rect], axis=1)   # (M, Nt)
            PY = np.stack([_cos_projection(y1, y2, H, N) for _, _, y1, y2 in rect], axis=1)   # (N, Nt)
            Ux, Uy = PX / tw, PY / th                         # Cosine average over each tile
            # Tile averages of the uniform solution
            y0 = np.stack([np.einsum("mr,mn,nr->r", Ux, a_mn[:, :, l], Uy) for l in range(L)], axis=1)  # (Nt, L)
            # Modal response between tiles: G[(r,l),(s,k)] for unit power injected uniformly in tile s, layer k
            Mg, Ng = min(M, 64), min(N, 64)
            Gm = np.zeros((Nt, L, Nt, L))
            for l in range(L):
                for k in range(L):
                    Wm = Ainv[:Mg, :Ng, l, k] * (ex[:Mg, None] * ey[None, :Ng]) / (W * H)
                    acc = np.zeros((Nt, Nt))
                    for n in range(Ng):
                        # Sum over m of Ux_r Ux_s W[m, n], then weight with the y factors of mode n
                        accx = (Ux[:Mg].T * Wm[:, n]) @ Ux[:Mg]
                        acc += accx * np.outer(Uy[n], Uy[n])
                    Gm[:, l, :, k] = acc
            G = Gm.reshape(Nt * L, Nt * L)
            # Local conductance matrix C (W/K): vias couple adjacent layers, sinks go to ambient
            C = np.zeros((Nt * L, Nt * L))
            for r, (row, col) in enumerate(active):
                cv = c_via[row, col]
                for l in range(L - 1):
                    i1, i2 = r * L + l, r * L + l + 1
                    C[i1, i1] += cv
                    C[i2, i2] += cv
                    C[i1, i2] -= cv
                    C[i2, i1] -= cv
                for l in range(L):
                    C[r * L + l, r * L + l] += g_sink[l, row, col]
            y = np.linalg.solve(np.eye(Nt * L) + G @ C, y0.reshape(-1))
            f = -(C @ y).reshape(Nt, L)                       # Heat injected into every tile and layer (W)
            sink_extraction = float(sum(g_sink[l, row, col] * y[r * L + l]
                                        for r, (row, col) in enumerate(active) for l in range(L)))
            # Add the response of the injected heat to the modal coefficients
            Pxf = PX / tw
            Pyf = PY / th
            for k in range(L):
                q_corr = np.einsum("mr,nr->mn", Pxf * f[:, k], Pyf) * (ex[:, None] * ey[None, :]) / (W * H)
                a_mn += np.einsum("mnl,mn->mnl", Ainv[:, :, :, k], q_corr)

    # --- Evaluate every layer at the cell centres by two matrix products
    cx_ = np.cos(np.outer(xs, np.arange(M) * np.pi / W))     # (nx, M)
    cy_ = np.cos(np.outer(ys, np.arange(N) * np.pi / H))     # (ny, N)
    theta = np.stack([cy_ @ a_mn[:, :, l].T @ cx_.T for l in range(L)])     # (L, ny, nx)
    T = theta + b.ambient

    l, i, j = np.unravel_index(int(np.argmax(T)), T.shape)
    # Heat leaving through the faces: the a_00 mode integrates each layer exactly
    p_out = {"top": float(b.h_top * W * H * a_mn[0, 0, 0]),
             "bottom": float(b.h_bottom * W * H * a_mn[0, 0, L - 1]),
             "sinks": float(sink_extraction if local_corrections else
                            sum(h_l[k] * W * H * a_mn[0, 0, k] for k in range(L))
                            - b.h_top * W * H * a_mn[0, 0, 0] - b.h_bottom * W * H * a_mn[0, 0, L - 1])}
    edge_ratio = (b.h_side or 0.0) * 2 * (W + H) * b.thickness / max(h_tot * W * H, 1e-30)
    if edge_ratio > 0.05:
        warnings.append(f"edge convection is about {edge_ratio * 100:.0f} % of the face convection but the "
                        "analytic model assumes insulated edges")
    return SteadyResult(
        model="analytic", ambient=b.ambient, power_in=power, t_max=float(T.max()),
        t_min=float(T.min()), t_mean=float(T.mean()), layer_mean=[float(T[k].mean()) for k in range(L)],
        t_max_location=(int(l), (j + 0.5) * dx, (i + 0.5) * dy), T=T, dx=dx, dy=dy,
        power_out=p_out, warnings=warnings,
        extras={"fin_length_mm": lam * 1000.0, "sheet_conductance_w_per_k": float(S.sum()),
                "uniform_board_rise_k": power / (h_tot * W * H) if h_tot > 0 else float("inf")},
    )
