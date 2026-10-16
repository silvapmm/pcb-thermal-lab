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

import copy
import math

import numpy as np

from scipy.special import k0

from . import blocks
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


def _effective_sheet(problem, cell_mm):
    """!
    @brief Effective sheet properties of the uniform multilayer board seen by the heaters.
    @details Per-layer copper fill averaged with the influence of the heaters (see the module description), the sheet
             conductance of every layer, the fin lengths and the validity warnings.
    @param problem A Problem.
    @param cell_mm Cell size (mm) of the sampling grid.
    @return Dict with b, m (board and materials), W, H, L, slab, nx, ny, dx, dy, xs, ys, tc, power, warnings,
            fill, S, lam, h_tot, d_diel and g_diel.
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
    return {"b": b, "m": m, "W": W, "H": H, "L": L, "slab": slab, "nx": nx, "ny": ny, "dx": dx, "dy": dy, "xs": xs,
            "ys": ys, "tc": tc, "power": power, "warnings": warnings, "fill": fill, "S": S, "lam": lam,
            "h_tot": h_tot, "d_diel": d_diel, "g_diel": g_diel}


def _heater_unit_sources(problem, M, N):
    """!
    @brief Cosine projection of every heater for 1 W (the source of a heater is its power times this array).
    @param problem A Problem.
    @param M Modes along x.
    @param N Modes along y.
    @return List of arrays (M, N, L), one per heater.
    """
    b = problem.board
    W, H, L = b.width, b.height, b.layers
    ex = np.where(np.arange(M) == 0, 1.0, 2.0)
    ey = np.where(np.arange(N) == 0, 1.0, 2.0)
    out = []
    for ht in problem.heaters:
        q = np.zeros((M, N, L))
        x1, x2, y1, y2 = _equivalent_rectangle(ht.polygon, W, H)
        q0 = 1.0 / ((x2 - x1) * (y2 - y1))                   # Power density of 1 W (W/m2)
        px = _cos_projection(x1, x2, W, M)
        py = _cos_projection(y1, y2, H, N)
        q[:, :, ht.layer] = q0 * np.outer(ex * px, ey * py) / (W * H)
        out.append(q)
    return out


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
    problem = blocks.plain_equivalent(problem)                   # These models have no metal blocks
    sh = _effective_sheet(problem, cell_mm)
    b, m, W, H, L = sh["b"], sh["m"], sh["W"], sh["H"], sh["L"]
    slab, nx, ny, dx, dy, xs, ys, tc = (sh[k] for k in ("slab", "nx", "ny", "dx", "dy", "xs", "ys", "tc"))
    power, warnings, fill, S, lam = sh["power"], sh["warnings"], sh["fill"], sh["S"], sh["lam"]
    h_tot, d_diel, g_diel = sh["h_tot"], sh["d_diel"], sh["g_diel"]

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
    ex = np.where(np.arange(M) == 0, 1.0, 2.0)
    ey = np.where(np.arange(N) == 0, 1.0, 2.0)
    q_mn = np.zeros((M, N, L))
    for ht, q_unit in zip(problem.heaters, _heater_unit_sources(problem, M, N)):
        q_mn += ht.power * q_unit

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


# ----------------------------------------------------------------------------------- time dependence

def _modal_matrix(problem, sh, n_terms, via_scale, sink_scale=1.0):
    """!
    @brief The (M, N, L, L) matrix A_mn of the modal equations C a' + A a = q (symmetric, tridiagonal in the layer index).
    @param problem A Problem.
    @param sh Dict from _effective_sheet.
    @param n_terms Cosine modes per direction.
    @param via_scale Factor on the smeared via conductance.
    @param sink_scale Factor on the smeared sink coefficient.
    @return Array (M, N, L, L).
    """
    b, m, W, H, L = sh["b"], sh["m"], sh["W"], sh["H"], sh["L"]
    M = N = n_terms
    h_l = np.zeros(L)
    h_l[0] += b.h_top
    h_l[L - 1] += b.h_bottom
    for s in problem.sinks:
        h_l[s.layer] += sink_scale * s.h_extra * polygon_area(s.polygon) / (W * H)
    g = sh["g_diel"]
    if L > 1:
        g += via_scale * m.k_copper * sum(v.copper_area(b.via_plating) for v in problem.vias) / (W * H) / sh["d_diel"]
    k2 = ((np.arange(M) * np.pi / W) ** 2)[:, None] + ((np.arange(N) * np.pi / H) ** 2)[None, :]
    A = np.zeros((M, N, L, L))
    for l in range(L):
        A[:, :, l, l] = sh["S"][l] * k2 + h_l[l]
        if l > 0:
            A[:, :, l, l] += g
            A[:, :, l, l - 1] -= g
        if l < L - 1:
            A[:, :, l, l] += g
            A[:, :, l, l + 1] -= g
    return A


def _modal_dynamics(problem, cell_mm, n_terms, via_scale=1.0, sink_scale=1.0):
    """!
    @brief Modal description of the transient: decay rates, mode shapes and heater source vectors.
    @details Every cosine mode (m, n) obeys C a' + A_mn a = q(t) with C = diag(c_l) the heat capacity per area of the
             layers. With the symmetric matrix C^(-1/2) A C^(-1/2) = V diag(lambda) V^T and b = V^T C^(1/2) a the
             modes decouple: b' = -lambda b + g(t), g = V^T C^(-1/2) q, so a constant power over a step has the exact
             propagator b+ = exp(-lambda dt) b + (1 - exp(-lambda dt)) / lambda g. The transient uses the uniform
             (smeared) vias and sinks, as the steady model does when local corrections are off.
    @param problem A Problem.
    @param cell_mm Cell size (mm) of the sampling grid.
    @param n_terms Cosine modes per direction.
    @param via_scale Factor applied to the smeared via conductance (see _calibrated_dynamics).
    @param sink_scale Factor applied to the smeared sink coefficient (see _calibrated_dynamics).
    @return Dict with the sheet data and lam (M, N, L), back (M, N, L, L), V, G (heaters, M, N, L), U (heaters, M, N, L),
            rth (heaters,), c_l (L,), cos_x (nx, M), cos_y (ny, N), points (heaters, 3) and tau (s).
    """
    sh = _effective_sheet(problem, cell_mm)
    b, m, W, H, L = sh["b"], sh["m"], sh["W"], sh["H"], sh["L"]
    M = N = n_terms
    A = _modal_matrix(problem, sh, n_terms, via_scale, sink_scale)
    fill, tc, slab = sh["fill"], sh["tc"], sh["slab"]
    c_l = fill * m.rho_copper * m.cp_copper * tc + (slab - fill * tc) * m.rho_fr4 * m.cp_fr4      # J/(m2 K)
    cinv = 1.0 / np.sqrt(c_l)
    lam, V = np.linalg.eigh(A * cinv[None, None, :, None] * cinv[None, None, None, :])
    back = cinv[None, None, :, None] * V                    # a = back @ b
    G = np.stack([np.einsum("mnlk,mnl->mnk", back, q) for q in _heater_unit_sources(problem, M, N)])
    cos_x = np.cos(np.outer(sh["xs"], np.arange(M) * np.pi / W))          # (nx, M)
    cos_y = np.cos(np.outer(sh["ys"], np.arange(N) * np.pi / H))          # (ny, N)
    # Own hottest point of every heater: the hottest cell of its unit steady field
    U, points = [], []
    for i in range(len(G)):
        a = np.einsum("mnlk,mnk->mnl", back, G[i] / lam)
        fields = np.stack([cos_y @ a[:, :, l].T @ cos_x.T for l in range(L)])      # (L, ny, nx)
        lay, iy, ix = np.unravel_index(int(np.argmax(fields)), fields.shape)
        wx, wy = np.cos(np.arange(M) * np.pi * sh["xs"][ix] / W), np.cos(np.arange(N) * np.pi * sh["ys"][iy] / H)
        U.append(wx[:, None, None] * wy[None, :, None] * back[:, :, lay, :])            # (M, N, L)
        points.append((lay, iy, ix))
    U = np.stack(U)
    rth = np.einsum("hmnk,hmnk,mnk->h", U, G, 1.0 / lam)
    tau = float(c_l.sum() / max(sh["h_tot"], 1e-9))
    sh.update({"lam": lam, "back": back, "V": V, "G": G, "U": U, "rth": rth, "c_l": c_l, "cos_x": cos_x,
               "cos_y": cos_y, "points": points, "tau": tau, "M": M, "N": N, "via_scale": via_scale,
               "sink_scale": sink_scale})
    return sh


def _smeared_steady_max(problem, sh, A, n_terms):
    """!
    @brief Maximum steady temperature rise of the smeared modal model, A a = q, for the heater powers of the problem.
    @param problem A Problem (heater powers are used).
    @param sh Dict from _effective_sheet.
    @param A Matrix from _modal_matrix.
    @param n_terms Cosine modes per direction.
    @return Maximum rise above ambient in kelvin.
    """
    W, H, L = sh["W"], sh["H"], sh["L"]
    q = sum(h.power * src for h, src in zip(problem.heaters, _heater_unit_sources(problem, n_terms, n_terms)))
    a = np.linalg.solve(A, q[..., None])[..., 0]                         # (M, N, L)
    cx = np.cos(np.outer(sh["xs"], np.arange(n_terms) * np.pi / W))
    cy = np.cos(np.outer(sh["ys"], np.arange(n_terms) * np.pi / H))
    return float(max((cy @ a[:, :, l].T @ cx.T).max() for l in range(L)))


def _calibrated_dynamics(problem, cell_mm, n_terms):
    """!
    @brief Modal dynamics whose smeared vias (or sinks) reproduce the steady maximum of the locally corrected model.
    @details The transient cannot apply the local Green-function corrections of the steady model, so vias and sinks are smeared
             over the board; a smeared via array under a heater has almost no effect (the example board came out 11 degC too hot).
             One factor is chosen (bisection on its logarithm) so that the steady maximum with the actual powers equals the
             steady maximum of solve_steady with local corrections: on the via conductance if the board has vias, otherwise on the
             sink coefficient (scaling the sinks as well would cool the whole board and spoil the dynamics). With it the transient of
             the example board follows the FVM within a few degC at every time (without it by up to 10 degC).
    @param problem A Problem (heater powers are the ones used for the calibration).
    @param cell_mm Cell size (mm) of the sampling grid.
    @param n_terms Cosine modes per direction.
    @return Dict from _modal_dynamics with the extra keys local_max (degC, None if there are no vias or sinks) and scaled
            ("vias", "sinks" or None).
    """
    ambient = problem.board.ambient
    d = _modal_dynamics(problem, cell_mm, n_terms)
    d["local_max"], d["scaled"] = None, None
    if not (problem.vias or problem.sinks) or problem.total_power() <= 0:
        return d
    local = solve_steady(problem, cell_mm=cell_mm, n_terms=n_terms).t_max - ambient
    d["local_max"] = local + ambient
    sh = _effective_sheet(problem, cell_mm)
    which = "vias" if problem.vias else "sinks"

    def steady(scale):
        # Steady maximum of the smeared model with the chosen element scaled
        a = _modal_matrix(problem, sh, n_terms, scale if which == "vias" else 1.0, scale if which == "sinks" else 1.0)
        return _smeared_steady_max(problem, sh, a, n_terms)

    if steady(1.0) <= local:
        return d                                                          # Smeared is already no hotter: keep it
    lo, hi = 0.0, math.log(1.0e4)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if steady(math.exp(mid)) > local:
            lo = mid
        else:
            hi = mid
        if hi - lo < 0.01:
            break
    scale = math.exp(0.5 * (lo + hi))
    d = _modal_dynamics(problem, cell_mm, n_terms, scale if which == "vias" else 1.0, scale if which == "sinks" else 1.0)
    d["local_max"], d["scaled"] = local + ambient, which
    return d


def _point_vector(d, point):
    """!
    @brief Row that evaluates the temperature at a grid point from the modal state of a system.
    @param d Dict from _modal_dynamics.
    @param point Tuple (layer, iy, ix) of the sampling grid.
    @return Array (M, N, L) such that T = sum(vector * b).
    """
    lay, iy, ix = point
    wx = np.cos(np.arange(d["M"]) * np.pi * d["xs"][ix] / d["W"])
    wy = np.cos(np.arange(d["N"]) * np.pi * d["ys"][iy] / d["H"])
    return wx[:, None, None] * wy[None, :, None] * d["back"][:, :, lay, :]


class _ModalSet:
    """!
    @brief The modal system or systems that describe a board for the transient.
    @details Without vias and sinks one system serves every heater. With them each heater gets its own system, calibrated
             (see _calibrated_dynamics) with that heater alone, because a single scale cannot be right both for a heater above
             a via array and for one far from it (on the example board it cooled the distant heater by 18 %). The
             temperature at a heater is then the sum of the contributions of all the systems at its own hottest point.
    """

    def __init__(self, problem, cell_mm, n_terms):
        """!
        @param problem A Problem.
        @param cell_mm Cell size (mm) of the sampling grid.
        @param n_terms Cosine modes per direction.
        """
        nh = len(problem.heaters)
        self.nh = nh
        if (problem.vias or problem.sinks) and nh > 1:
            self.ds, self.serve = [], list(range(nh))
            for j in range(nh):
                solo = copy.deepcopy(problem)
                for k, h in enumerate(solo.heaters):
                    h.power = 1.0 if k == j else 0.0                    # Unit power: only the shape of its response matters
                self.ds.append(_calibrated_dynamics(solo, cell_mm, n_terms))
        else:
            self.ds, self.serve = [_calibrated_dynamics(problem, cell_mm, n_terms)], [0] * nh
        d0 = self.ds[0]
        self.d0 = d0
        self.points = [self.ds[self.serve[k]]["points"][k] for k in range(nh)]          # Own hottest point of every heater
        self.U = [np.stack([_point_vector(d, p) for p in self.points]) for d in self.ds]  # (nh, M, N, L) per system
        # Resistance of every heater to its own point, through the system that serves it
        self.rth = np.array([float(np.sum(self.U[self.serve[k]][k] * self.ds[self.serve[k]]["G"][k]
                                          / self.ds[self.serve[k]]["lam"])) for k in range(nh)])
        self.tau = max(d["tau"] for d in self.ds)
        self.scaled = [(d["scaled"], d["via_scale"] if d["scaled"] == "vias" else d["sink_scale"], d["local_max"])
                       for d in self.ds if d["local_max"] is not None]

    def drive(self, powers):
        """!
        @brief Modal source of every system for the heater powers.
        @param powers Heater powers in watts.
        @return List of arrays (M, N, L), one per system.
        """
        out = []
        for s, d in enumerate(self.ds):
            g = np.zeros_like(d["lam"])
            for k in range(self.nh):
                if self.serve[k] == s and powers[k] != 0.0:
                    g = g + powers[k] * d["G"][k]
            out.append(g)
        return out

    def steady(self, powers):
        """!
        @brief Steady modal state for constant heater powers.
        @param powers Heater powers in watts.
        @return List of modal states, one per system.
        """
        return [g / d["lam"] for g, d in zip(self.drive(powers), self.ds)]

    def points_temperature(self, states):
        """!
        @brief Temperature rise at every heater's own point.
        @param states List of modal states.
        @return Array (n_heaters,) in kelvin above ambient.
        """
        return sum(np.einsum("hmnk,mnk->h", U, b) for U, b in zip(self.U, states))

    def field(self, states):
        """!
        @brief Temperature rise of every layer on the sampling grid.
        @param states List of modal states.
        @return Array (layers, ny, nx) in kelvin above ambient.
        """
        total = 0.0
        for d, b in zip(self.ds, states):
            a = np.einsum("mnlk,mnk->mnl", d["back"], b)
            total = total + np.stack([d["cos_y"] @ a[:, :, l].T @ d["cos_x"].T for l in range(d["L"])])
        return total


def step_responses(problem, cell_mm=1.0, n_terms=300, t_end=None, n_times=100):
    """!
    @brief Unit-step response of every heater's hottest point, in closed form.
    @details Z_i(t) = sum over modes of U g (1 - exp(-lambda t)) / lambda, in the system that serves heater i.
    @param problem A Problem with at least one heater.
    @param cell_mm Cell size (mm) of the sampling grid.
    @param n_terms Cosine modes per direction.
    @param t_end Last time in seconds (default: ten board time constants).
    @param n_times Number of logarithmically spaced times.
    @return Tuple (times, z, rth) as in fvm.step_responses.
    """
    problem = blocks.plain_equivalent(problem)                   # These models have no metal blocks
    ms = _ModalSet(problem, cell_mm, n_terms)
    t_end = t_end or 10.0 * ms.tau
    times = np.geomspace(1e-5, t_end, n_times)
    z = np.empty((ms.nh, n_times))
    for i in range(ms.nh):
        d = ms.ds[ms.serve[i]]
        lam = d["lam"].ravel()
        coef = (ms.U[ms.serve[i]][i] * d["G"][i] / d["lam"]).ravel()
        keep = np.abs(coef) > 1e-13 * np.abs(coef).max()                   # Prune modes that do not matter
        c, lk = coef[keep], lam[keep]
        for k, t in enumerate(times):
            z[i, k] = c @ (1.0 - np.exp(-lk * t))
    return times, z, ms.rth


class _AnalyticAdapter:
    """!
    @brief Adapter that advances the modal model in time (see profiles.run_windows for the interface).
    """

    def __init__(self, problem, cell_mm, n_terms):
        """!
        @param problem A Problem (heater powers equal the averages).
        @param cell_mm Cell size (mm) of the sampling grid.
        @param n_terms Cosine modes per direction.
        """
        self.ms = ms = _ModalSet(problem, cell_mm, n_terms)
        d = ms.d0
        self.ambient = problem.board.ambient
        self.dx, self.dy = d["dx"], d["dy"]
        self.L = d["L"]
        self.p_avg = np.array([h.average_power() for h in problem.heaters])
        self.b_avg = ms.steady(self.p_avg)
        p_init = np.array([h.initial_power() for h in problem.heaters])      # Start state: average, or first power of a one-shot
        self.b_init = self.b_avg if np.allclose(p_init, self.p_avg) else ms.steady(p_init)
        b_peak = ms.steady(np.array([h.peak_power() for h in problem.heaters]))
        self.steady_average_max = float(self.frame(self.b_avg).max())
        self.steady_peak_max = float(self.frame(b_peak).max())
        self.warnings = []
        if ms.scaled:
            what = "via conductance" if ms.scaled[0][0] == "vias" else "sink coefficient"
            scales = ", ".join(f"{sc:.3g}" for _, sc, _ in ms.scaled)
            self.warnings.append(
                f"the analytic transient smears the vias and sinks over the board and, for every heater, scales the {what} "
                f"(factors {scales}) so that its steady response matches the locally corrected steady model; the dynamics near "
                "them are approximate, use the FVM to confirm")

    def prepare(self, dt):
        """!
        @brief Exact propagator of every mode of every system for the time step.
        @param dt Time step in seconds.
        """
        self.E = [np.exp(-d["lam"] * dt) for d in self.ms.ds]
        self.F = [(1.0 - e) / d["lam"] for e, d in zip(self.E, self.ms.ds)]

    def begin(self, options):
        """!
        @brief Initial modal state.
        @param options ProfileOptions.
        @return Tuple (state, reported initial temperature in degC).
        """
        if options.initial == "average":
            return [b.copy() for b in self.b_init], float(self.frame(self.b_init).max())
        t0 = self.ambient - 0.0 if options.initial_c is None else float(options.initial_c)
        states = [np.zeros_like(b) for b in self.b_avg]
        # A uniform field is the (0, 0) mode with the same value on every layer; it lives in the first system
        d = self.ms.ds[0]
        states[0][0, 0, :] = np.einsum("lk,l->k", d["V"][0, 0], np.sqrt(d["c_l"]) * (t0 - self.ambient))
        return states, t0

    def advance(self, states, dt, powers):
        """!
        @brief Exact step of every mode under the constant power of the step.
        @param states List of modal states.
        @param dt Time step in seconds (equal to the prepared one).
        @param powers Power of every heater during the step (W).
        @return New list of modal states.
        """
        drive = self.ms.drive(powers)
        return [e * b + f * g for e, f, b, g in zip(self.E, self.F, states, drive)]

    def observe(self, states):
        """!
        @brief Temperature at every heater's own hottest point.
        @param states List of modal states.
        @return Tuple (hottest degC, per-heater degC).
        """
        pts = self.ms.points_temperature(states) + self.ambient
        return float(pts.max()), pts

    def frame(self, states):
        """!
        @brief Field of every layer on the sampling grid.
        @param states List of modal states.
        @return Array (layers, ny, nx) in degC.
        """
        return self.ms.field(states) + self.ambient

    def peak_values(self, states):
        """!
        @brief The peak map is built from the stored frames, not every step.
        @param states Unused.
        @return None.
        """
        return None


def run_profile(problem, decisions, options, cell_mm=1.0, n_terms=300, progress=None):
    """!
    @brief Time simulation of a problem with power profiles using the analytic modal model.
    @param problem A Problem (heater powers equal the averages).
    @param decisions Decisions from profiles.decide().
    @param options ProfileOptions.
    @param cell_mm Cell size (mm) of the sampling grid.
    @param n_terms Cosine modes per direction.
    @param progress Optional callback progress(message, fraction).
    @return ProfileResult.
    @throws ProfileError If the run is too expensive for options.max_steps.
    """
    problem = blocks.plain_equivalent(problem)                   # These models have no metal blocks
    from . import profiles
    return profiles.run_windows(problem, decisions, options, _AnalyticAdapter(problem, cell_mm, n_terms), "analytic",
                                progress)


def solve_transient(problem, t_end, n_out=40, cell_mm=1.0, n_terms=300, log_times=True):
    """!
    @brief Response to the heater powers switched on at t = 0 on a board at ambient temperature, in closed form.
    @details Every cosine mode follows b(t) = (1 - exp(-lambda t)) / lambda * g, so any time is evaluated directly with no
             time stepping. Vias and sinks are smeared (see _modal_dynamics); use the FVM when they sit under the heaters.
    @param problem A Problem (its heater powers; profiles are ignored, the average power is used).
    @param t_end Final time in seconds.
    @param n_out Number of output frames after t = 0.
    @param cell_mm Cell size (mm) of the sampling grid.
    @param n_terms Cosine modes per direction.
    @param log_times True for logarithmically spaced times (resolves fast and slow parts), False for linear.
    @return TransientResult.
    """
    problem = blocks.plain_equivalent(problem)                   # These models have no metal blocks
    from .results import TransientResult
    problem = problem.steady_copy("average") if problem.has_profiles() else problem
    ad = _AnalyticAdapter(problem, cell_mm, n_terms)
    ms = ad.ms
    if log_times:
        # The same time grid as the FVM transient (the step doubles in ten stages), so that the models can be compared frame by frame
        stages = 10
        per_stage = max(int(np.ceil(n_out / stages)), 1)
        dt0 = t_end / (per_stage * (2 ** stages - 1))
        times = np.concatenate([[0.0], np.cumsum(np.concatenate([np.full(per_stage, dt0 * 2.0 ** j) for j in range(stages)]))])
    else:
        times = np.linspace(0.0, t_end, max(n_out, 1) + 1)
    drive = ms.drive(ad.p_avg)                                         # Modal source of the powers, per system
    frames, t_max, t_mean = [], [], []
    for t in times:
        b = [(1.0 - np.exp(-d["lam"] * t)) / d["lam"] * g for d, g in zip(ms.ds, drive)]
        f = ad.frame(b)
        frames.append(f.astype(np.float32))
        t_max.append(float(f.max()))
        t_mean.append(float(f.mean()))
    return TransientResult(times=times, t_max=np.array(t_max), t_mean=np.array(t_mean), frames=np.array(frames),
                           steady_t_max=ad.steady_average_max, ambient=problem.board.ambient)
