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

def _modal_dynamics(problem, cell_mm, n_terms):
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
    @return Dict with the sheet data and lam (M, N, L), back (M, N, L, L), V, G (heaters, M, N, L), U (heaters, M, N, L),
            rth (heaters,), c_l (L,), cos_x (nx, M), cos_y (ny, N), points (heaters, 3) and tau (s).
    """
    sh = _effective_sheet(problem, cell_mm)
    b, m, W, H, L = sh["b"], sh["m"], sh["W"], sh["H"], sh["L"]
    M = N = n_terms
    h_l = np.zeros(L)
    h_l[0] += b.h_top
    h_l[L - 1] += b.h_bottom
    for s in problem.sinks:
        h_l[s.layer] += s.h_extra * polygon_area(s.polygon) / (W * H)
    g = sh["g_diel"]
    if L > 1:
        g += m.k_copper * sum(v.copper_area(b.via_plating) for v in problem.vias) / (W * H) / sh["d_diel"]
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
               "cos_y": cos_y, "points": points, "tau": tau, "M": M, "N": N})
    return sh


def step_responses(problem, cell_mm=1.0, n_terms=300, t_end=None, n_times=100):
    """!
    @brief Unit-step response of every heater's hottest point, in closed form.
    @details Z_i(t) = sum over modes of U g (1 - exp(-lambda t)) / lambda.
    @param problem A Problem with at least one heater.
    @param cell_mm Cell size (mm) of the sampling grid.
    @param n_terms Cosine modes per direction.
    @param t_end Last time in seconds (default: ten board time constants).
    @param n_times Number of logarithmically spaced times.
    @return Tuple (times, z, rth) as in fvm.step_responses.
    """
    d = _modal_dynamics(problem, cell_mm, n_terms)
    t_end = t_end or 10.0 * d["tau"]
    times = np.geomspace(1e-5, t_end, n_times)
    lam = d["lam"].ravel()
    z = np.empty((len(d["G"]), n_times))
    for i in range(len(d["G"])):
        coef = (d["U"][i] * d["G"][i] / d["lam"]).ravel()
        keep = np.abs(coef) > 1e-13 * np.abs(coef).max()                   # Prune modes that do not matter
        c, lk = coef[keep], lam[keep]
        for k, t in enumerate(times):
            z[i, k] = c @ (1.0 - np.exp(-lk * t))
    return times, z, d["rth"]


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
        self.d = d = _modal_dynamics(problem, cell_mm, n_terms)
        self.ambient = problem.board.ambient
        self.dx, self.dy = d["dx"], d["dy"]
        self.L = d["L"]
        self.p_avg = np.array([h.average_power() for h in problem.heaters])
        self.b_avg = np.tensordot(self.p_avg, d["G"] / d["lam"], axes=1)
        b_peak = np.tensordot(np.array([h.peak_power() for h in problem.heaters]), d["G"] / d["lam"], axes=1)
        self.steady_average_max = float(self.frame(self.b_avg).max())
        self.steady_peak_max = float(self.frame(b_peak).max())
        self.warnings = []
        if problem.vias or problem.sinks:
            local = solve_steady(problem.steady_copy("average"), cell_mm=cell_mm, n_terms=n_terms).t_max
            self.warnings.append(
                f"the analytic transient uses vias and sinks smeared over the board: its steady maximum with the average power "
                f"is {self.steady_average_max:.1f} °C, against {local:.1f} °C when they are applied locally (steady analytic "
                "model); use the FVM for boards where vias or sinks sit under the heaters")

    def prepare(self, dt):
        """!
        @brief Exact propagator of every mode for the time step.
        @param dt Time step in seconds.
        """
        self.E = np.exp(-self.d["lam"] * dt)
        self.F = (1.0 - self.E) / self.d["lam"]

    def begin(self, options):
        """!
        @brief Initial modal state.
        @param options ProfileOptions.
        @return Tuple (state, reported initial temperature in degC).
        """
        if options.initial == "average":
            return self.b_avg.copy(), self.steady_average_max
        t0 = self.ambient if options.initial_c is None else float(options.initial_c)
        b = np.zeros_like(self.b_avg)
        # A uniform field is the (0, 0) mode with the same value on every layer
        b[0, 0, :] = np.einsum("lk,l->k", self.d["V"][0, 0], np.sqrt(self.d["c_l"]) * (t0 - self.ambient))
        return b, t0

    def advance(self, b, dt, powers):
        """!
        @brief Exact step of every mode under the constant power of the step.
        @param b Modal state (M, N, L).
        @param dt Time step in seconds (equal to the prepared one).
        @param powers Power of every heater during the step (W).
        @return New modal state.
        """
        return self.E * b + self.F * np.tensordot(powers, self.d["G"], axes=1)

    def observe(self, b):
        """!
        @brief Temperature at every heater's own hottest point.
        @param b Modal state.
        @return Tuple (hottest degC, per-heater degC).
        """
        pts = np.einsum("hmnk,mnk->h", self.d["U"], b) + self.ambient
        return float(pts.max()), pts

    def frame(self, b):
        """!
        @brief Field of every layer on the sampling grid.
        @param b Modal state.
        @return Array (layers, ny, nx) in degC.
        """
        a = np.einsum("mnlk,mnk->mnl", self.d["back"], b)
        return np.stack([self.d["cos_y"] @ a[:, :, l].T @ self.d["cos_x"].T for l in range(self.L)]) + self.ambient

    def peak_values(self, b):
        """!
        @brief The peak map is built from the stored frames, not every step.
        @param b Unused.
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
    from . import profiles
    return profiles.run_windows(problem, decisions, options, _AnalyticAdapter(problem, cell_mm, n_terms), "analytic",
                                progress)
