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
model needs uniform properties: copper fill is averaged per layer, vias are smeared over the
board and sinks are averaged over the surface. Local effects (vias under the heater, partial
copper) are only captured by the FVM model.
"""

import numpy as np

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




def solve_steady(problem, cell_mm=1.0, n_terms=300):
    """!
    @brief Analytic steady-state solution of the multilayer fin problem.
    @param problem A Problem.
    @param cell_mm Cell size (mm) of the sampling grid used for the fields and the maxima.
    @param n_terms Number of cosine modes per direction (300 resolves heaters of a few mm).
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

    # --- Per-layer sheet conductance with the mean copper fill of each layer
    fill = np.zeros(L)
    for l in range(L):
        f = np.zeros((ny, nx))
        for z in problem.zones:
            if z.layer == l:
                f = np.maximum(f, coverage_fraction(z.polygon, nx, ny, dx, dy, 4) * z.fill)
        fill[l] = f.mean()
    tc = np.asarray(b.copper_thickness)
    S = fill * m.k_copper * tc + m.k_fr4_inplane * (slab - fill * tc)           # (L,)

    # --- Surface coefficient of every layer (W/m2K); sinks are averaged over the surface
    h_l = np.zeros(L)
    h_l[0] += b.h_top
    h_l[L - 1] += b.h_bottom
    for s in problem.sinks:
        h_l[s.layer] += s.h_extra * polygon_area(s.polygon) / (W * H)

    # --- Vertical conductance per unit area between adjacent layers (dielectric + smeared vias)
    g = 0.0
    if L > 1:
        d = b.dielectric_thickness()
        a_vias = sum(v.copper_area(b.via_plating) for v in problem.vias)
        g = m.k_fr4_through / d + m.k_copper * a_vias / (W * H) / d

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

    # --- Solve the L x L tridiagonal system of every mode at once
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
    a_mn = np.linalg.solve(A, q_mn[..., None])[..., 0]       # (M, N, L)

    # --- Evaluate every layer at the cell centres by two matrix products
    xs = (np.arange(nx) + 0.5) * dx
    ys = (np.arange(ny) + 0.5) * dy
    cx = np.cos(np.outer(xs, np.arange(M) * np.pi / W))      # (nx, M)
    cy = np.cos(np.outer(ys, np.arange(N) * np.pi / H))      # (ny, N)
    theta = np.stack([cy @ a_mn[:, :, l].T @ cx.T for l in range(L)])   # (L, ny, nx)
    T = theta + b.ambient

    l, i, j = np.unravel_index(int(np.argmax(T)), T.shape)
    power = problem.total_power()
    # Heat leaving through the faces: the a_00 mode integrates the field exactly
    p_out = {"top": float(b.h_top * W * H * a_mn[0, 0, 0]),
             "bottom": float(b.h_bottom * W * H * a_mn[0, 0, L - 1]),
             "sinks": float(sum(h_l[k] * W * H * a_mn[0, 0, k] for k in range(L))
                            - b.h_top * W * H * a_mn[0, 0, 0] - b.h_bottom * W * H * a_mn[0, 0, L - 1])}
    h_tot = float(b.h_top + b.h_bottom)
    return SteadyResult(
        model="analytic", ambient=b.ambient, power_in=power, t_max=float(T.max()),
        t_min=float(T.min()), t_mean=float(T.mean()), layer_mean=[float(T[k].mean()) for k in range(L)],
        t_max_location=(int(l), (j + 0.5) * dx, (i + 0.5) * dy), T=T, dx=dx, dy=dy,
        power_out=p_out,
        extras={"fin_length_mm": float(np.sqrt(S.sum() / h_tot) * 1000.0) if h_tot > 0 else float("inf"),
                "sheet_conductance_w_per_k": float(S.sum()),
                "uniform_board_rise_k": power / (h_tot * W * H) if h_tot > 0 else float("inf")},
    )
