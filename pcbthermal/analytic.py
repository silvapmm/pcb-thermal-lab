#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file analytic.py
@brief Closed-form multilayer fin model: exact modal solution for a uniform board.

@details Every layer is a thin sheet with lateral conductance S_l [W/K] (copper fill and FR-4
in-plane share), coupled to its neighbours through the dielectric conductance per unit area
g = (k_fr4_through / d) + smeared vias, and to ambient through h_top (layer 1) and h_bottom
(last layer). The steady rise theta_l(x, y) of layer l obeys

    S_l * laplacian(theta_l) - h_l * theta_l - g * (2*theta_l - theta_{l-1} - theta_{l+1}) = -q_l

(the coupling terms drop at the outer layers) with a convective (Robin) board edge, S_l d theta_l / dn = -h_side s_l theta_l, written with one parameter common to the
layers, beta = h_side sum(s_l) / sum(S_l) (1/m; s_l the layer slab thickness, on a board with an outline the perimeter of the real outline scales h_side), as the
basis of the series; the true parameter of layer l is beta_l = h_side s_l / S_l, and the difference S_l (beta_l - beta) is added back as a modal source and solved
with GMRES around the whole solve (the per-layer edge; layers with the same s_l / S_l skip it and keep the common-beta result bit for bit). The series is in the
eigenfunctions of that edge (Muzychka, Culham and Yovanovich 2003, AIAA 2003-4188, Part II, eqs. 12 to 21): along each direction (length L, half length Lh)

    even  cos(lam u),  lam Lh tan(lam Lh) = beta Lh;    odd  sin(lam u),  lam Lh cot(lam Lh) = -beta Lh,    u = x - L/2,

ordered by lam. Then theta_l = sum_{m,n} a_{l,mn} phi_m(x) phi_n(y) decouples the equation by mode: for every (m, n) a small tridiagonal L x L system is solved,

    ( diag(S_l * k_mn^2 + h_l) + g * graph_laplacian ) a_mn = q_mn,  k_mn^2 = lam_m^2 + lam_n^2,

where q_mn is the projection of the heaters on the eigenfunctions (analytic for rectangles) over their norms. Without an edge coefficient beta = 0, the eigenfunctions are the
cosines cos(m pi x / W) (lam = m pi / W) and the code is the insulated one, bit for bit. The a_00 mode of the insulated board is the uniform-board limit P / (h W H); the
other modes add the lateral spreading penalty. The model needs laterally uniform properties, with these refinements:

- Copper fill is averaged per layer with a weight equal to the influence of the heaters
  (the fin Green function K0(r / lambda_l), lambda_l = sqrt(S_l / g_loss) the layer's own fin length), so copper near a heater counts
  more than copper far away.
- Vias and heatsinks are local. They are removed from the uniform problem and added back through
  a Green-function (Woodbury) correction: the board is cut into tiles of a few millimetres,
  every tile with a via or a heatsink gets a lumped conductance, and the small dense system
  (I + G_mod C_loc) y = y0 gives the tile temperatures, where G_mod is the modal response of the uniform
  board between tiles and C_loc holds the local conductances.
- With vias the tile is min(1 mm, 0.75 of the median nearest-neighbour distance), at least 0.25 mm, the barrel conductance of a via that is alone at the scale of a
  tile is shared bilinearly among the four tiles around it, and the diagonal of G_mod gets a self-term that makes the tile read the temperature at the wall of the barrel
  instead of the tile mean (viaconstriction.py). Boards without vias keep the 2.5 to 5 mm tiles and are unchanged.
- In time the vias and heatsinks stay local too: a coupled modal block of the lowest 16 x 16 modes holds their tile conductances (analytic_local.py), the via couplings
  scaled by one factor fitted to the steady solve; the modes above it are the uniform ones.
- A validity check adds warnings when the copper is far from uniform around the heaters.
Strongly non-uniform copper is still beyond this model: use the FVM then.
"""

import copy
import math

import numpy as np

import scipy.linalg
from scipy.optimize import brentq
from scipy.sparse.linalg import LinearOperator, gmres
from scipy.special import k0

from . import blocks, copper, laminate, viaconstriction
from .analytic_local import FACTOR_BRACKET, LocalSystem
from .fvm import Network
from .geometry import coverage_fraction, polygon_area, polygon_centroid
from .results import SteadyResult
from .numfmt import num

EDGE_MISMATCH_MIN = 1e-9      # Relative spread of the per-layer edge parameters below which the layers count as equal (no loop, the common-beta code bit for bit)
EDGE_GMRES_RTOL = 1e-6        # Relative residual of the per-layer edge loop (GMRES on the modal coefficients; 4 to 9 products measured)
LOCAL_MODES = 16              # Modes per direction of the coupled block of the transient with vias and heatsinks (24 changes the time to 63 % by under 1.5 points)
LOCAL_MAX_UNKNOWNS = 3000     # K x K x L of the block is lowered to stay under this (a dense eigenproblem: 42 MB and about 4 s at 1024)
EDGE_GMRES_RESTART = 30       # GMRES restart length and maximum number of restarts of the per-layer edge loop


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




def _edge_root(k, odd, bl):
    """!
    @brief The k-th root delta = lam Lh of the even (delta tan delta = bl) or odd (delta cot delta = -bl) eigen-equation, for any bl > 0.
    @details Solved in the forms without poles, even g(d) = d sin d - bl cos d on [k pi, k pi + pi/2] and odd g(d) = d cos d + bl sin d on [k pi + pi/2, (k + 1) pi], where g
             changes sign once. When the root is closer to an end of its interval than rounding resolves (a very small or a very large bl) the first-order asymptote of that
             end is used: small bl, even d = sqrt(bl) (k = 0) or k pi + bl / (k pi), odd d = (k + 1/2) pi + bl / ((k + 1/2) pi); large bl, even d = (k + 1/2) pi (1 - 1/bl),
             odd d = (k + 1) pi (1 - 1/bl). The lowest even root below bl of 1e-8 is sqrt(bl) (1 + bl/12) directly (the absolute tolerance of the root finder
             would return 0 there).
    @param k Index of the interval (0, 1, ...).
    @param odd 0 for the even function, 1 for the odd function.
    @param bl Edge parameter times the half length, beta Lh (dimensionless, > 0).
    @return float The root delta (rad).
    """
    if odd:
        lo, hi = k * np.pi + 0.5 * np.pi, (k + 1) * np.pi
        g = lambda d: d * np.cos(d) + bl * np.sin(d)          # noqa: E731
    else:
        lo, hi = k * np.pi, k * np.pi + 0.5 * np.pi
        g = lambda d: d * np.sin(d) - bl * np.cos(d)          # noqa: E731
    if bl < 1e-8 and not odd and k == 0:
        return float(np.sqrt(bl)) * (1.0 + bl / 12.0)       # d sin d = bl for small d (brentq's absolute tolerance would return 0 below d of 1e-15)
    if g(lo) * g(hi) < 0.0:
        return float(brentq(g, lo, hi, xtol=1e-15, rtol=1e-15))
    # No sign change in floating point: the root sits at an end of the interval to rounding, use the asymptote of that end
    if bl < 1.0:
        if odd:
            return lo + bl / lo
        return float(np.sqrt(bl)) if k == 0 else lo + bl / lo
    return hi * (1.0 - 1.0 / bl)


class _EdgeBasis:
    """!
    @brief The first n eigenfunctions of d2/dx2 on [0, L] with a convective edge at both ends, the basis of one direction of the series.
    @details beta = 0 (or too small to matter, beta L below 1e-200) is the cosine basis cos(m pi x / L) of the insulated board, with the same expressions as the program had
             before the edge entered the basis, so that the result is identical bit for bit. Otherwise even cos(lam u) and odd sin(lam u) (u = x - L/2) in the order of lam
             (mode 0 even, 1 odd, ...) with the roots of _edge_root; they are orthogonal for the weight 1.
    """

    def __init__(self, length, beta, n):
        """!
        @param length Length L of the direction in metres.
        @param beta Edge parameter h_side sum(s) / sum(S) in 1/m (0: insulated).
        @param n Number of modes.
        @throws ValueError If beta is not a finite number or is negative.
        """
        if not math.isfinite(beta) or beta < 0.0:
            raise ValueError(f"edge parameter must be finite and not negative, got {beta}")
        self.L, self.beta, self.n = float(length), float(beta), int(n)
        Lh = 0.5 * self.L
        self.cosine = self.beta * self.L < 1e-200
        if self.cosine:
            self.lam = np.arange(self.n) * np.pi / self.L
            self.kind = None
            return
        bl = self.beta * Lh
        self.kind = np.arange(self.n) % 2                          # 0 even (cos in u), 1 odd (sin in u)
        self.lam = np.array([_edge_root(m // 2, m % 2, bl) for m in range(self.n)]) / Lh

    @property
    def eig2(self):
        """!
        @brief Eigenvalues lam^2 (1/m2) that replace (m pi / L)^2 in the modal matrices.
        @return Array (n,).
        """
        return self.lam ** 2

    @property
    def norm(self):
        """!
        @brief Squared norm, integral of phi_m^2 over [0, L], of the unnormalised eigenfunctions.
        @return Array (n,) in metres.
        """
        if self.cosine:
            return np.where(np.arange(self.n) == 0, self.L, 0.5 * self.L)
        Lh = 0.5 * self.L
        s = np.sin(2.0 * self.lam * Lh) / (2.0 * self.lam)
        return np.where(self.kind == 0, Lh + s, Lh - s)

    @property
    def weight(self):
        """!
        @brief L / norm: 1 for the constant mode and 2 for the other cosines (the factor e_m of the cosine series), in general the length over the squared norm.
        @return Array (n,).
        """
        return self.L / self.norm

    def evaluate(self, x):
        """!
        @brief The eigenfunctions at points x.
        @param x Array (p,) of positions in metres from the lower edge.
        @return Array (p, n).
        """
        x = np.asarray(x, dtype=float)
        if self.cosine:
            return np.cos(np.outer(x, self.lam))
        arg = np.outer(x - 0.5 * self.L, self.lam)
        return np.where(self.kind[None, :] == 0, np.cos(arg), np.sin(arg))

    def at(self, x):
        """!
        @brief The eigenfunctions at one point (the cosine basis in the form m pi x / L of the point read-outs, so that the insulated board keeps its last bit).
        @param x Position in metres from the lower edge.
        @return Array (n,).
        """
        if self.cosine:
            return np.cos(np.arange(self.n) * np.pi * x / self.L)
        return self.evaluate([x])[0]

    def project(self, lo, hi):
        """!
        @brief Integral of every eigenfunction over [lo, hi].
        @param lo Lower bound in metres.
        @param hi Upper bound in metres.
        @return Array (n,) in metres.
        """
        if self.cosine:
            return _cos_projection(lo, hi, self.L, self.n)
        ul, uh = lo - 0.5 * self.L, hi - 0.5 * self.L
        lam = self.lam
        even = (np.sin(lam * uh) - np.sin(lam * ul)) / lam
        odd = -(np.cos(lam * uh) - np.cos(lam * ul)) / lam
        return np.where(self.kind == 0, even, odd)


def _bases(sh, n_terms):
    """!
    @brief The bases of the two directions for a sheet (kept in the sheet dict, so that the roots are found once per mode count).
    @param sh Dict from _effective_sheet.
    @param n_terms Modes per direction.
    @return Tuple (basis along x, basis along y).
    """
    key = ("bases", int(n_terms))
    if key not in sh:
        sh[key] = (_EdgeBasis(sh["W"], sh["beta"], n_terms), _EdgeBasis(sh["H"], sh["beta"], n_terms))
    return sh[key]


def _plan_mean(bx, by, a):
    """!
    @brief Mean of the field of one layer over the board plan, given its modal coefficients.
    @param bx Basis along x.
    @param by Basis along y.
    @param a Modal coefficients (M, N) of the layer in K.
    @return float Mean rise over the plan in K (for the cosine basis exactly a_00, so the insulated board is unchanged to the last bit).
    """
    if bx.cosine and by.cosine:
        return float(a[0, 0])
    return float(bx.project(0.0, bx.L) @ a @ by.project(0.0, by.L)) / (bx.L * by.L)


def _edge_loss(bx, by, a, S, beta):
    """!
    @brief Heat of one layer that leaves through the convective edge, beta S times the integral of the rise along the four sides.
    @param bx Basis along x.
    @param by Basis along y.
    @param a Modal coefficients (M, N) of the layer in K.
    @param S Sheet conductance of the layer in W/K.
    @param beta Edge parameter in 1/m.
    @return float Power in W.
    """
    ex, ey = bx.evaluate([0.0, bx.L]), by.evaluate([0.0, by.L])
    along_y = (ex @ a) @ by.project(0.0, by.L)              # rise at x = 0 and x = W integrated over y
    along_x = (ey @ a.T) @ bx.project(0.0, bx.L)            # rise at y = 0 and y = H integrated over x
    return float(beta * S * (along_y.sum() + along_x.sum()))


def _influence(centres, xs, ys, dx, lam_l):
    """!
    @brief Weight of every cell for the heater-influence average of the copper fill, the sum over the heaters of power times K0(distance / lam_l).
    @details K0 underflows to zero when the fin length is far below a cell (an absurd edge or face coefficient); then no cell has weight and the average would be 0/0. In that
             limit the influence is the heater itself, so the cells nearest to a heater get the weight (the limit lam_l -> 0).
    @param centres List of ((cx, cy), r0, power, layer) of the heaters with power.
    @param xs Cell centre abscissae in metres.
    @param ys Cell centre ordinates in metres.
    @param dx Cell size in metres.
    @param lam_l Fin length of the layer in metres.
    @return Array (ny, nx) of weights, with a positive sum.
    """
    w = np.zeros((len(ys), len(xs)))
    dmin = np.full(w.shape, np.inf)
    for (cx, cy), r0, pw, _ in centres:
        dist = np.maximum(np.hypot(xs[None, :] - cx, ys[:, None] - cy), max(r0, 0.5 * dx))
        w += pw * k0(dist / lam_l)
        dmin = np.minimum(dmin, dist)
    if not np.isfinite(w.sum()) or w.sum() <= 0.0:
        w = (dmin <= dmin.min()).astype(float)
    return w


def _tile_grid(W, H, lam):
    """!
    @brief Tile grid used for the local corrections.
    @param W Board width (m).
    @param H Board height (m).
    @param lam Fin length of the whole stack, lambda = sqrt(sum_l S_l / h_tot) (m).
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
            fill, S, lam, h_tot, h_edge (W/m2K per layer: for the lengths and the time constant only), beta (1/m, the edge parameter of the basis), beta_l (1/m, the edge
            parameter of each layer, h_eff s_l / S_l), edge_mismatch (largest |beta_l - beta| / beta), h_eff, d_diel and g_diel.
    """
    problem.validate()
    b = problem.board
    m = b.materials
    W, H, L = b.width, b.height, b.layers
    slab = b.slab_thicknesses()                       # Per layer node (equal in the simple stack-up)
    k_lam, rho_cp_lam = b.layer_laminate()
    nx = max(int(round(W * 1000.0 / cell_mm)), 2)
    ny = max(int(round(H * 1000.0 / cell_mm)), 2)
    dx, dy = W / nx, H / ny
    xs = (np.arange(nx) + 0.5) * dx
    ys = (np.arange(ny) + 0.5) * dy
    tc = np.asarray(b.copper_thickness)
    power = problem.total_power()
    warnings = []

    # --- Copper fill field of every layer and its heater-influence weighted average
    fill_map = copper.problem_fill(problem, nx, ny, dx, dy, 4)
    # Edge conductance per plan area of each layer, h_side * perimeter * slab_l / (W H) (W/m2K): the edge area of the layer node over its plan area (the same split
    # by layer as the edge conductance of the FVM). It is NOT a surface coefficient of the modal matrices (the edge is in the basis, see beta below); it enters the
    # total h_tot that sets the fin lengths and the tile size, and the time constant, so that the copper weighting and the tiles do not move. On a board with an
    # outline the model runs on the rectangle of the same area, so the perimeter is that of the real outline (Problem.equivalent_rectangle keeps it), not the
    # shorter one of the rectangle.
    perimeter = getattr(b, "edge_perimeter", None) or 2.0 * (W + H)
    h_edge = (b.h_side or 0.0) * perimeter * slab / (W * H)
    h_tot = float(b.h_top + b.h_bottom + h_edge.sum())
    d_diel = b.gap_thicknesses()                                          # (L-1,) one per gap
    g_diel = b.gap_properties()[0] / d_diel if L > 1 else np.zeros(0)     # Vertical conductance per area of each gap (W/m2K)
    fill_mean = fill_map.mean(axis=(1, 2))
    S_mean = fill_mean * m.k_copper * tc + k_lam * (slab - fill_mean * tc)
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
                g_adj = sum(g_diel[g] for g in (l - 1, l) if 0 <= g < L - 1)       # Conductance to the neighbouring layers
                h_surf = (b.h_top if l == 0 else 0.0) + (b.h_bottom if l == L - 1 else 0.0) + h_edge[l]
                lam_l = float(np.sqrt(S_mean[l] / max(h_surf + g_adj, 1e-9)))
            else:
                lam_l = lam
            w = _influence(centres, xs, ys, dx, lam_l)             # Influence of the heaters at each cell
            fill[l] = (fill_map[l] * w).sum() / w.sum()
            spread[l] = np.sqrt(((fill_map[l] - fill[l]) ** 2 * w).sum() / w.sum())
            if l in heater_layers:
                # Warning trigger only (the sheet above is not changed): the same spread with the fin length of this layer as full
                # copper. On a thin gap the program's length is about a millimetre, the weights stay under the part and the pad edge is not
                # seen, so the first spread is silent exactly on the boards that are worst (research/analytic-partial-copper, README 9.4).
                S_cu = m.k_copper * tc[l] + k_lam[l] * (slab[l] - tc[l])
                lam_cu = float(np.sqrt(S_cu / max(h_surf + g_adj, 1e-9)))
                w_cu = _influence(centres, xs, ys, dx, lam_cu)
                f_cu = (fill_map[l] * w_cu).sum() / w_cu.sum()
                spread[l] = max(spread[l], float(np.sqrt(((fill_map[l] - f_cu) ** 2 * w_cu).sum() / w_cu.sum())))
        if spread.max() > 0.25:
            warnings.append(
                f"copper coverage varies around the heaters (spread {spread.max():.2f}): the Analytic model spreads the copper of each layer "
                "into one uniform sheet and has no copper edge; on a part over a copper pad or a window it was measured between 76 % too cool "
                "and 9 % too hot against a resolved 3D solution, and the same board entered as one layer or as two (bare second layer) "
                "differed by up to 1.8 times. Use the FVM result for this board.")
    S = fill * m.k_copper * tc + k_lam * (slab - fill * tc)                     # (L,)
    # Edge parameter of the Robin basis (Muzychka, Culham and Yovanovich 2003, Part II eqs. 12 to 21), one for all layers: the sum of the edge conductances per metre of
    # edge over the sum of the sheet conductances. Exact when every layer has the same ratio slab_l / S_l, an approximation otherwise (docs/theory.md 6). h_eff is
    # h_side scaled so that the rectangle has the edge conductance of the real outline. 1/m; zero without h_side (the cosine basis).
    h_eff = (b.h_side or 0.0) * perimeter / (2.0 * (W + H))
    beta = float(h_eff * slab.sum() / S.sum())
    # Edge parameter of each layer, h_eff s_l / S_l: the true Robin condition of layer l. The basis uses the common beta; the steady solve adds the difference as a modal
    # source (solve_steady, per-layer edge). The mismatch is exactly zero for one layer and (to rounding) for layers with the same s_l / S_l, and then the loop is skipped.
    beta_l = h_eff * slab / S
    edge_mismatch = float(np.abs(beta_l - beta).max() / beta) if beta > 0.0 else 0.0
    edge_share = float(h_edge.sum() / h_tot) if h_tot > 0 else 0.0
    spread = float(S.max() / S.min())
    if beta > 0.0 and edge_share > 0.3 and (L == 1 or spread > (1.5 if L == 2 else 2.5)):
        # Calibrated on 54 boards outside the first study (research/analytic-edge-spatial README 8.3): it fires on the boards with a Robin error above 3 % and on none
        # of the 135 uniform ones
        if L == 1:
            warnings.append(
                f"edge convection: the edge takes {edge_share * 100:.0f} % of the loss coefficient and on a one-layer board the laminate edge is given to the copper: "
                "the hottest temperature can be off by up to about 9 % either way (measured cool, up to 9 %, with the copper on the heated layer). "
                "Use the FVM result for this board (itself up to about 15 % low on a thick board with a large edge coefficient: then the 3D solid).")
        else:
            # Per-layer edge (research/analytic-2-6 README 2.3, 2.4 and 6.1; reproduced in docs/validation.md 4.1): what is left is the laminate rule of the FVM
            warnings.append(
                f"edge convection: the edge takes {edge_share * 100:.0f} % of the loss coefficient and the sheet conductances of the layers differ by {spread:.1f} times: "
                "the Analytic model treats the edge of each layer separately and its hottest temperature was measured from about 5 % too cool to 1 % too hot against the "
                "FVM on a sample of 48 boards (the cool side is the laminate of the FVM beside partial copper; a sample, not a bound). "
                "The FVM is itself up to about 15 % low on a thick board with a large edge coefficient: then use the 3D solid.")
    return {"b": b, "m": m, "W": W, "H": H, "L": L, "slab": slab, "nx": nx, "ny": ny, "dx": dx, "dy": dy, "xs": xs,
            "ys": ys, "tc": tc, "power": power, "warnings": warnings, "fill": fill, "S": S, "lam": lam,
            "h_tot": h_tot, "h_edge": h_edge, "beta": beta, "beta_l": beta_l, "edge_mismatch": edge_mismatch, "h_eff": h_eff, "d_diel": d_diel, "g_diel": g_diel, "k_lam": k_lam,
            "rho_cp_lam": rho_cp_lam}


def _heater_unit_sources(problem, bx, by):
    """!
    @brief Modal projection of every heater for 1 W (the source of a heater is its power times this array).
    @param problem A Problem.
    @param bx Basis along x (_EdgeBasis; its n is the number of modes), or the number of cosine modes (the insulated board: the studies that read this function).
    @param by Basis along y, or the number of cosine modes.
    @return List of arrays (M, N, L), one per heater.
    """
    b = problem.board
    W, H, L = b.width, b.height, b.layers
    if not isinstance(bx, _EdgeBasis):
        bx = _EdgeBasis(W, 0.0, bx)
    if not isinstance(by, _EdgeBasis):
        by = _EdgeBasis(H, 0.0, by)
    M, N = bx.n, by.n
    ex, ey = bx.weight, by.weight                            # 1 for the constant cosine and 2 for the others; L over the squared norm for the Robin basis
    out = []
    for ht in problem.heaters:
        q = np.zeros((M, N, L))
        x1, x2, y1, y2 = _equivalent_rectangle(ht.polygon, W, H)
        q0 = 1.0 / ((x2 - x1) * (y2 - y1))                   # Power density of 1 W (W/m2)
        px = bx.project(x1, x2)
        py = by.project(y1, y2)
        q[:, :, ht.layer] = q0 * np.outer(ex * px, ey * py) / (W * H)
        out.append(q)
    return out


def _block_tiles(problem, ntx, nty, tw, th, L):
    """!
    @brief The metal blocks as tile quantities for the Green-function correction (experimental).
    @details The layers of the blocks are built on the tile grid with blocks.extra_layers (the same code the FVM uses). Each block face is a small graph of tiles: lateral
             conductance k t between tiles, contact to the board layer over the copper of the tile, exposed surface to the ambient. Eliminating the block temperatures
             leaves an effective conductance matrix on the board layer, B = D_link - D_link (K_b + D_amb + D_link)^-1 D_link (a Schur complement), which couples the tiles of the
             block to each other: that is what lets the block spread the heat of the pad centre to the whole pad. The board face under the block no longer exchanges heat
             with the air (a negative local conductance).
    @param problem A Problem.
    @param ntx Tiles along x.
    @param nty Tiles along y.
    @param tw Tile width in metres.
    @param th Tile height in metres.
    @param L Number of board layers.
    @return List of dicts with layer (board layer), tiles (array of (row, col)), B (Schur matrix), face (W/K removed per tile), M (matrix to recover the block temperatures),
            g_link, g_amb.
    """
    b = problem.board
    fill_t = copper.problem_fill(problem, ntx, nty, tw, th, 4)
    area_t = np.full((nty, ntx), tw * th)
    out = []
    for ly in blocks.extra_layers(problem, lambda poly, n: coverage_fraction(poly, ntx, nty, tw, th, n), area_t, fill_t, tw, th):
        tiles = np.argwhere(ly["cov"] > 0)
        index = -np.ones((nty, ntx), dtype=int)
        index[tuple(tiles.T)] = np.arange(len(tiles))
        n = len(tiles)
        K = np.zeros((n, n))
        S = ly["S"]
        for axis, face_len, dist in ((1, th, tw), (0, tw, th)):                 # Lateral conduction of the block between neighbouring tiles
            a = S[:, :-1] if axis == 1 else S[:-1, :]
            c = S[:, 1:] if axis == 1 else S[1:, :]
            g = Network._harmonic(a, c) * face_len / dist
            ia = index[:, :-1] if axis == 1 else index[:-1, :]
            ic = index[:, 1:] if axis == 1 else index[1:, :]
            sel = (ia >= 0) & (ic >= 0) & (g > 0)
            for i, j, gg in zip(ia[sel], ic[sel], g[sel]):
                K[i, i] += gg; K[j, j] += gg; K[i, j] -= gg; K[j, i] -= gg
        g_link = ly["g_link"][tuple(tiles.T)]
        g_amb = ly["g_amb"][tuple(tiles.T)]
        M = K + np.diag(g_amb + g_link)
        Dl = np.diag(g_link)
        B = Dl - Dl @ np.linalg.solve(M, Dl)
        h_face = b.h_top if ly["face"] == 0 else b.h_bottom
        face = h_face * tw * th * ly["cov"][tuple(tiles.T)]                      # Face conductance that the block hides
        out.append({"layer": ly["board_layer"], "tiles": tiles, "B": B, "face": face, "side": ly["face"], "M": M, "g_link": g_link, "g_amb": g_amb})
    return out


def _edge_mismatch_source(bx, by, a, S, dbeta):
    """!
    @brief Extra modal source of the edge of unlike layers: the difference between the true edge parameter of each layer and the common one of the basis.
    @details Layer l has the Robin condition S_l dtheta/dn = -h_eff s_l theta, parameter beta_l = h_eff s_l / S_l, while the eigenfunctions have the common beta. By
             Green's identity the weak form of the layer in that basis gets the term S_l (beta_l - beta) closed-integral(theta_l phi_m phi_n). The integral needs only the
             rise on the four sides, and the orthogonality of the eigenfunctions along each side reduces it to two small matrix products:
             qc_l,mn = -S_l (beta_l - beta) [ sum_e phi_m(x_e) / N_m (sum_m' phi_m'(x_e) a_l,m'n) + sum_e phi_n(y_e) / N_n (sum_n' phi_n'(y_e) a_l,mn') ]
             (e the two ends of a direction, N the squared norms; docs/theory.md 6, research/analytic-2-6 README 2.1).
    @param bx Basis along x.
    @param by Basis along y.
    @param a Modal coefficients (M, N, L) in K.
    @param S Sheet conductance of every layer in W/K.
    @param dbeta beta_l - beta of every layer in 1/m.
    @return Array (M, N, L), the extra source in the units of the modal source.
    """
    ex, ey = bx.evaluate([0.0, bx.L]), by.evaluate([0.0, by.L])        # (2, M), (2, N): the eigenfunctions at the two ends of each direction
    ex_n = ex.T / bx.norm[:, None]
    ey_n = ey / by.norm[None, :]
    out = np.empty_like(a)
    for l in range(a.shape[2]):
        al = a[:, :, l]
        out[:, :, l] = -S[l] * dbeta[l] * (ex_n @ (ex @ al) + (al @ ey.T) @ ey_n)
    return out


def _per_layer_edge(respond, q, bx, by, S, dbeta, warnings):
    """!
    @brief Modal coefficients of the board with the true edge of every layer: the fixed point a = respond(q + qc(a)) solved with GMRES.
    @details respond is the whole linear solve of the board (uniform modal solve, and the Green-function step of the vias and heatsinks), so the loop wraps it and the local
             elements are inside it. The operator (I - respond qc) is a small perturbation of the identity (|beta_l - beta| S_l against S_l lambda^2 and the face and gap
             terms): 4 to 9 products measured on 54 boards (research/analytic-2-6 README 2.3, 2.4). At the end one more pass at the converged source gives the
             coefficients and the tile temperatures that belong together.
    @param respond Function (q) -> (a, y): the linear response to a modal source (see solve_steady).
    @param q Modal source of the heaters (M, N, L).
    @param bx Basis along x.
    @param by Basis along y.
    @param S Sheet conductance of every layer in W/K.
    @param dbeta beta_l - beta of every layer in 1/m.
    @param warnings List of warnings, appended to when GMRES does not converge.
    @return Tuple (a (M, N, L), y (tile temperatures or None), number of operator products).
    """
    a0, _ = respond(q)
    shape, count = a0.shape, [0]

    def mv(v):
        count[0] += 1
        x = v.reshape(shape)
        return (x - respond(_edge_mismatch_source(bx, by, x, S, dbeta))[0]).ravel()

    op = LinearOperator((a0.size, a0.size), matvec=mv, dtype=float)
    sol, info = gmres(op, a0.ravel(), x0=a0.ravel(), rtol=EDGE_GMRES_RTOL, restart=EDGE_GMRES_RESTART, maxiter=EDGE_GMRES_RESTART)
    x = sol.reshape(shape)
    if info != 0:
        warnings.append("the per-layer edge iteration of the Analytic model did not reach its tolerance in "
                        f"{count[0]} products: the edge heat of the unlike layers is approximate")
    a, y = respond(q + _edge_mismatch_source(bx, by, x, S, dbeta))
    return a, y, count[0]


def _local_conductances(problem, sh, bx, by):
    """!
    @brief The tile data of the local elements (vias, heatsinks, blocks) shared by the steady Green-function correction and the transient coupled block.
    @details The tile grid (the via plan changes it), the via conductance of every tile across each gap (bilinear weights of a via alone at the scale of a tile), the heatsink
             conductance of every tile, the metal blocks as graphs of tiles, the active tiles (a via, a heatsink or a block), the projections of the basis on them and the
             via part of the local conductance matrix. The heatsink part of that matrix is diagonal and returned as a vector, so that the same sum as the earlier code is made.
    @param problem A Problem.
    @param sh Dict from _effective_sheet.
    @param bx Basis along x.
    @param by Basis along y.
    @return Dict with ntx, nty, tw, th, vs (viaconstriction.ViaSet or None), via_weights, c_via (nty, ntx, L-1), g_heatsink (L, nty, ntx), bt (block graphs), active (Nt, 2) of
            (row, col), PX (M, Nt) and PY (N, Nt) (integrals of the basis over each active tile, not divided by the tile size), Cv (Nt L, Nt L, the vias, W/K) and cs
            (Nt L,): the heatsink conductance of every tile and layer. PX, PY, Cv and cs are None when there is no active tile.
    """
    b, m, W, H, L = sh["b"], sh["m"], sh["W"], sh["H"], sh["L"]
    d_diel = sh["d_diel"]
    ntx, nty, tw, th = _tile_grid(W, H, sh["lam"])
    vs = viaconstriction.ViaSet(problem) if problem.vias and L > 1 else None
    via_weights = None
    if vs is not None:
        # Vias: tile of min(1 mm, 0.75 nearest-neighbour distance) instead of 2.5 to 5 mm, so that the sink has the scale of the barrel (viaconstriction.py)
        via_plan = viaconstriction.plan(problem, vs, (ntx, nty, tw, th), L)
        (ntx, nty, tw, th), via_weights = via_plan["grid"], via_plan["weights"]
    c_via = np.zeros((nty, ntx, max(L - 1, 0)))                    # Via conductance of each tile across each gap
    for iv, v in enumerate(problem.vias if vs is not None else []):
        cond = m.k_copper * v.thermal_area(b.via_plating, m.k_copper) / d_diel
        for (row, col), w in via_weights[iv].items():             # A via alone at the scale of a tile is shared by bilinear weights between four tiles
            c_via[row, col] += w * cond
    g_heatsink = np.zeros((L, nty, ntx))
    for s in problem.heatsinks:
        if s.is_block():
            continue                                       # A block is a graph of tiles of its own (below)
        g_heatsink[s.layer] += s.h_extra * tw * th * coverage_fraction(s.polygon, ntx, nty, tw, th, 8)
    bt = _block_tiles(problem, ntx, nty, tw, th, L) if blocks.has_blocks(problem) else []
    in_block = np.zeros((nty, ntx), dtype=bool)
    for e in bt:
        in_block[tuple(e["tiles"].T)] = True
    active = np.argwhere((c_via.sum(axis=2) > 0) | (g_heatsink.sum(axis=0) > 0) | in_block)        # (Nt, 2) = (row, col)
    out = {"ntx": ntx, "nty": nty, "tw": tw, "th": th, "vs": vs, "via_weights": via_weights, "c_via": c_via, "g_heatsink": g_heatsink, "bt": bt,
           "active": active, "PX": None, "PY": None, "Cv": None, "cs": None}
    Nt = len(active)
    if Nt:
        rect = [(c * tw, (c + 1) * tw, r * th, (r + 1) * th) for r, c in active]
        out["PX"] = np.stack([bx.project(x1, x2) for x1, x2, _, _ in rect], axis=1)   # (M, Nt)
        out["PY"] = np.stack([by.project(y1, y2) for _, _, y1, y2 in rect], axis=1)   # (N, Nt)
        Cv = np.zeros((Nt * L, Nt * L))
        cs = np.zeros(Nt * L)
        for r, (row, col) in enumerate(active):
            for l in range(L - 1):
                cv = c_via[row, col, l]
                i1, i2 = r * L + l, r * L + l + 1
                Cv[i1, i1] += cv
                Cv[i2, i2] += cv
                Cv[i1, i2] -= cv
                Cv[i2, i1] -= cv
            for l in range(L):
                cs[r * L + l] += g_heatsink[l, row, col]
        out["Cv"], out["cs"] = Cv, cs
    return out


def solve_steady(problem, cell_mm=1.0, n_terms=300, local_corrections=True):
    """!
    @brief Analytic steady-state solution of the multilayer fin problem.
    @param problem A Problem.
    @param cell_mm Cell size (mm) of the sampling grid used for the fields and the maxima.
    @param n_terms Number of modes per direction (300 resolves heaters of a few mm; cosines, or the eigenfunctions of the convective edge).
    @param local_corrections If True vias and heatsinks are applied locally (Green-function update);
                             if False they are smeared over the board (the older, cruder model).
    @note With vias the tiles follow the pitch and the vias get the constriction of the heat converging on a barrel (viaconstriction.plan, add_self_terms); the correction
          needs a dense system of (active tiles x layers)^2 entries, kept to 4800 unknowns.
    @note A metal block is a graph of tiles inside the Green-function correction (see _block_tiles) and needs the local corrections. Steady state only; against the FVM it is
          within 1 % on average and 4.5 % at most (docs/validation.md section 17).
    @return SteadyResult with one field per layer, T of shape (layers, ny, nx).
    """
    blocks.require_rectangle(problem)                            # With an outline simulate() solves the rectangle of the same area
    problem = problem.drop_off_board_vias()                      # A via with no board under its drill conducts nothing (as in the grid models)
    problem = laminate.series_bottom_problem(problem)            # One-layer board: the laminate in series with the bottom film (laminate.py)
    forced = blocks.has_blocks(problem) and not local_corrections           # A block is a local correction: it cannot be smeared over the board
    local_corrections = local_corrections or forced
    sh = _effective_sheet(problem, cell_mm)
    b, m, W, H, L = sh["b"], sh["m"], sh["W"], sh["H"], sh["L"]
    slab, nx, ny, dx, dy, xs, ys, tc = (sh[k] for k in ("slab", "nx", "ny", "dx", "dy", "xs", "ys", "tc"))
    power, warnings, fill, S, lam = sh["power"], sh["warnings"], sh["fill"], sh["S"], sh["lam"]
    h_tot, d_diel, g_diel = sh["h_tot"], sh["d_diel"], sh["g_diel"]
    if forced:
        warnings.append("the local corrections are on because a metal block needs them")

    # --- Surface coefficients and vertical conductance of the uniform problem
    h_l = np.zeros(L)
    h_l[0] += b.h_top
    h_l[L - 1] += b.h_bottom
    g = g_diel.copy()                                         # (L-1,) per gap
    if not local_corrections:
        for s in problem.heatsinks:
            h_l[s.layer] += s.h_extra * polygon_area(s.polygon) / (W * H)
        if L > 1:
            g += m.k_copper * sum(v.thermal_area(b.via_plating, m.k_copper) for v in problem.vias) / (W * H) / d_diel

    # --- Modal coefficients of the heaters, one vector entry per layer (the basis has the convective edge in it: beta = 0 is the cosine basis)
    M = N = n_terms
    bx, by = _bases(sh, n_terms)
    ex, ey = bx.weight, by.weight
    q_mn = np.zeros((M, N, L))
    for ht, q_unit in zip(problem.heaters, _heater_unit_sources(problem, bx, by)):
        q_mn += ht.power * q_unit

    # --- Modal matrices A_mn (L x L) and their inverses
    k2 = bx.eig2[:, None] + by.eig2[None, :]
    A = np.zeros((M, N, L, L))
    for l in range(L):
        A[:, :, l, l] = S[l] * k2 + h_l[l]
        if l > 0:
            A[:, :, l, l] += g[l - 1]
            A[:, :, l, l - 1] -= g[l - 1]
        if l < L - 1:
            A[:, :, l, l] += g[l]
            A[:, :, l, l + 1] -= g[l]
    Ainv = np.linalg.inv(A)                                  # (M, N, L, L)

    # --- Local corrections for vias and heatsinks through the tile Green-function system
    heatsink_extraction = 0.0
    block_power = 0.0
    hidden = {"top": 0.0, "bottom": 0.0}                         # Face heat of the area under the blocks, taken off the face totals
    mismatch = bool(b.h_side) and sh["edge_mismatch"] > EDGE_MISMATCH_MIN       # Layers with different s_l / S_l: the per-layer edge loop below
    loc = None
    if local_corrections and (problem.vias or problem.heatsinks):
        lc = _local_conductances(problem, sh, bx, by)
        ntx, nty, tw, th, vs, via_weights = lc["ntx"], lc["nty"], lc["tw"], lc["th"], lc["vs"], lc["via_weights"]
        bt, active = lc["bt"], lc["active"]
        Nt = len(active)
        if Nt:
            PX, PY = lc["PX"], lc["PY"]
            Ux, Uy = PX / tw, PY / th                         # Average of the eigenfunctions over each tile
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
            if vs is not None:
                # The mosaic gives the tile MEAN; the barrel sees its wall: add the response of the tile to its own sink (self-term) to the diagonal
                G = viaconstriction.add_self_terms(G, active, via_weights, vs, tw, th, S)
            # Local conductance matrix C (W/K): vias couple adjacent layers, heatsinks go to ambient (on the diagonal)
            C = lc["Cv"]
            C[np.diag_indices_from(C)] += lc["cs"]
            pos = {(int(row), int(col)): r for r, (row, col) in enumerate(active)}
            for e in bt:                                       # Metal blocks: the Schur matrix couples the tiles of the board layer under the block
                rows_e = np.array([pos[(int(a), int(c))] * L + e["layer"] for a, c in e["tiles"]])
                C[np.ix_(rows_e, rows_e)] += e["B"]
                C[rows_e, rows_e] -= e["face"]                 # ... and the face under it no longer loses heat to the air
            lhs = G @ C
            lhs[np.diag_indices_from(lhs)] += 1.0                  # I + G_mod C_loc in place: the identity matrix and the sum are two more matrices of (Nt L)^2 entries
            if mismatch:
                # The per-layer loop solves with the same matrix many times: keep its LU (the dense matrix is overwritten by the factors, same memory)
                lu = scipy.linalg.lu_factor(lhs, overwrite_a=True, check_finite=False)
                solve_tiles = lambda rhs: scipy.linalg.lu_solve(lu, rhs, check_finite=False)       # noqa: E731
            else:
                solve_tiles = lambda rhs: np.linalg.solve(lhs, rhs)                                 # noqa: E731
            loc = {"C": C, "Ux": Ux, "Uy": Uy, "PX": PX, "PY": PY, "solve": solve_tiles, "Nt": Nt, "pos": pos, "bt": bt, "active": active, "g_hs": lc["g_heatsink"]}

    def respond(q):
        """!
        @brief Modal coefficients of the board (with the local elements) for a modal source: the uniform solution plus the Green-function correction, a linear map of q.
        @param q Modal source (M, N, L) in W per mode unit.
        @return Tuple (a (M, N, L), tile temperatures y (Nt L,) or None without local elements).
        """
        a = np.einsum("mnlk,mnk->mnl", Ainv, q)            # (M, N, L)
        if loc is None:
            return a, None
        Nt = loc["Nt"]
        # Tile averages of the uniform solution
        y0 = np.stack([np.einsum("mr,mn,nr->r", loc["Ux"], a[:, :, l], loc["Uy"]) for l in range(L)], axis=1)  # (Nt, L)
        y = loc["solve"](y0.reshape(-1))
        f = -(loc["C"] @ y).reshape(Nt, L)                    # Heat injected into every tile and layer (W)
        # Add the response of the injected heat to the modal coefficients
        Pxf = loc["PX"] / tw
        Pyf = loc["PY"] / th
        for k in range(L):
            q_corr = np.einsum("mr,nr->mn", Pxf * f[:, k], Pyf) * (ex[:, None] * ey[None, :]) / (W * H)
            a += np.einsum("mnl,mn->mnl", Ainv[:, :, :, k], q_corr)
        return a, y

    # --- Per-layer edge: the basis has the common beta, each layer has its own beta_l; the difference S_l (beta_l - beta) is an extra modal source qc(a), and
    #     a = respond(q + qc(a)) is solved with GMRES on (I - respond qc) a = respond(q). Equal layers: no mismatch, one pass, the code of the common beta bit for bit.
    edge_iterations = 0
    if mismatch:
        a_mn, y, edge_iterations = _per_layer_edge(respond, q_mn, bx, by, S, sh["beta_l"] - sh["beta"], warnings)
    else:
        a_mn, y = respond(q_mn)
    if loc is not None:
        bt, pos = loc["bt"], loc["pos"]
        for e in bt:                                       # Heat taken by the exposed surface of every block
            rows_e = np.array([pos[(int(a), int(c))] * L + e["layer"] for a, c in e["tiles"]])
            phi = np.linalg.solve(e["M"], e["g_link"] * y[rows_e])
            block_power += float((e["g_amb"] * phi).sum())
            # The face under the block does not lose heat to the air; the plan mean below counts the whole face, so this part is taken off it
            hidden["top" if e["side"] == 0 else "bottom"] += float((e["face"] * y[rows_e]).sum())
        g_hs = loc["g_hs"]
        heatsink_extraction = float(sum(g_hs[l, row, col] * y[r * L + l]
                                    for r, (row, col) in enumerate(loc["active"]) for l in range(L)))

    # --- Evaluate every layer at the cell centres by two matrix products
    cx_ = bx.evaluate(xs)                                    # (nx, M)
    cy_ = by.evaluate(ys)                                    # (ny, N)
    theta = np.stack([cy_ @ a_mn[:, :, l].T @ cx_.T for l in range(L)])     # (L, ny, nx)
    T = theta + b.ambient

    l, i, j = np.unravel_index(int(np.argmax(T)), T.shape)
    # Heat leaving through the faces: the mean of each layer over the plan (for the cosine basis exactly a_00)
    mean = [_plan_mean(bx, by, a_mn[:, :, k]) for k in range(L)]
    p_out = {**({"blocks": block_power} if block_power else {}), "top": float(b.h_top * W * H * mean[0]) - hidden["top"],
             "bottom": float(b.h_bottom * W * H * mean[L - 1]) - hidden["bottom"],
             "heatsinks": float(heatsink_extraction if local_corrections else
                            sum(h_l[k] * W * H * mean[k] for k in range(L))
                            - b.h_top * W * H * mean[0] - b.h_bottom * W * H * mean[L - 1])}
    if b.h_side:
        # The edge loss, reported apart under the same key as the FVM: beta S_l times the rise of the layer integrated along the four sides, so the heat balance closes
        # (per layer: beta_l S_l = h_eff s_l; with equal layers the common beta, so the balance of the earlier code is kept bit for bit)
        beta_side = sh["beta_l"] if mismatch else np.full(L, sh["beta"])
        p_out["sides"] = float(sum(_edge_loss(bx, by, a_mn[:, :, k], S[k], beta_side[k]) for k in range(L)))
    return SteadyResult(
        model="analytic", ambient=b.ambient, power_in=power, t_max=float(T.max()),
        t_min=float(T.min()), t_mean=float(T.mean()), layer_mean=[float(T[k].mean()) for k in range(L)],
        t_max_location=(int(l), (j + 0.5) * dx, (i + 0.5) * dy), T=T, dx=dx, dy=dy,
        power_out=p_out, warnings=warnings,
        extras={"fin_length_mm": lam * 1000.0, "sheet_conductance_w_per_k": float(S.sum()),
                "uniform_board_rise_k": power / (h_tot * W * H) if h_tot > 0 else float("inf"),
                "edge_iterations": edge_iterations},
    )


# ----------------------------------------------------------------------------------- time dependence

def _modal_matrix(problem, sh, n_terms, via_scale, heatsink_scale=1.0):
    """!
    @brief The (M, N, L, L) matrix A_mn of the modal equations C a' + A a = q (symmetric, tridiagonal in the layer index).
    @param problem A Problem.
    @param sh Dict from _effective_sheet.
    @param n_terms Modes per direction.
    @param via_scale Factor on the smeared via conductance.
    @param heatsink_scale Factor on the smeared heatsink coefficient.
    @return Array (M, N, L, L).
    """
    b, m, W, H, L = sh["b"], sh["m"], sh["W"], sh["H"], sh["L"]
    M = N = n_terms
    h_l = np.zeros(L)
    h_l[0] += b.h_top
    h_l[L - 1] += b.h_bottom
    for s in problem.heatsinks:
        h_l[s.layer] += heatsink_scale * s.h_extra * polygon_area(s.polygon) / (W * H)
    g = sh["g_diel"].copy()
    if L > 1:
        g += via_scale * m.k_copper * sum(v.thermal_area(b.via_plating, m.k_copper) for v in problem.vias) / (W * H) / sh["d_diel"]
    bx, by = _bases(sh, n_terms)                              # The edge is in the basis (beta = 0: the cosines)
    k2 = bx.eig2[:, None] + by.eig2[None, :]
    A = np.zeros((M, N, L, L))
    for l in range(L):
        A[:, :, l, l] = sh["S"][l] * k2 + h_l[l]
        if l > 0:
            A[:, :, l, l] += g[l - 1]
            A[:, :, l, l - 1] -= g[l - 1]
        if l < L - 1:
            A[:, :, l, l] += g[l]
            A[:, :, l, l + 1] -= g[l]
    return A


def _modal_dynamics(problem, cell_mm, n_terms, via_scale=1.0, heatsink_scale=1.0):
    """!
    @brief Modal description of the transient: decay rates, mode shapes and heater source vectors.
    @details Every cosine mode (m, n) obeys C a' + A_mn a = q(t) with C = diag(c_l) the heat capacity per area of the
             layers. With the symmetric matrix C^(-1/2) A C^(-1/2) = V diag(lambda) V^T and b = V^T C^(1/2) a the
             modes decouple: b' = -lambda b + g(t), g = V^T C^(-1/2) q, so a constant power over a step has the exact
             propagator b+ = exp(-lambda dt) b + (1 - exp(-lambda dt)) / lambda g. The transient uses the uniform
             (smeared) vias and heatsinks, as the steady model does when local corrections are off; _local_dynamics keeps them local instead (a coupled block of the lowest modes) and calls this with both factors zero.
    @param problem A Problem.
    @param cell_mm Cell size (mm) of the sampling grid.
    @param n_terms Modes per direction (cosines, or the eigenfunctions of the convective edge).
    @param via_scale Factor applied to the smeared via conductance (0 for the board without vias, see _local_dynamics).
    @param heatsink_scale Factor applied to the smeared heatsink coefficient (0 for the board without heatsinks).
    @return Dict with the sheet data and lam (M, N, L), back (M, N, L, L), V, G (heaters, M, N, L), U (heaters, M, N, L),
            rth (heaters,), c_l (L,), cos_x (nx, M), cos_y (ny, N), points (heaters, 3) and tau (s).
    """
    sh = _effective_sheet(problem, cell_mm)
    b, m, W, H, L = sh["b"], sh["m"], sh["W"], sh["H"], sh["L"]
    M = N = n_terms
    A = _modal_matrix(problem, sh, n_terms, via_scale, heatsink_scale)
    fill, tc, slab = sh["fill"], sh["tc"], sh["slab"]
    c_l = fill * m.rho_copper * m.cp_copper * tc + (slab - fill * tc) * sh["rho_cp_lam"]      # J/(m2 K)
    cinv = 1.0 / np.sqrt(c_l)
    lam, V = np.linalg.eigh(A * cinv[None, None, :, None] * cinv[None, None, None, :])
    back = cinv[None, None, :, None] * V                    # a = back @ b
    bx, by = _bases(sh, n_terms)
    G = np.stack([np.einsum("mnlk,mnl->mnk", back, q) for q in _heater_unit_sources(problem, bx, by)])
    cos_x = bx.evaluate(sh["xs"])          # (nx, M) values of the eigenfunctions (cosines without an edge coefficient)
    cos_y = by.evaluate(sh["ys"])          # (ny, N)
    # Own hottest point of every heater: the hottest cell of its unit steady field
    U, points = [], []
    for i in range(len(G)):
        a = np.einsum("mnlk,mnk->mnl", back, G[i] / lam)
        fields = np.stack([cos_y @ a[:, :, l].T @ cos_x.T for l in range(L)])      # (L, ny, nx)
        lay, iy, ix = np.unravel_index(int(np.argmax(fields)), fields.shape)
        wx, wy = bx.at(sh["xs"][ix]), by.at(sh["ys"][iy])
        U.append(wx[:, None, None] * wy[None, :, None] * back[:, :, lay, :])            # (M, N, L)
        points.append((lay, iy, ix))
    U = np.stack(U)
    rth = np.einsum("hmnk,hmnk,mnk->h", U, G, 1.0 / lam)
    tau = float(c_l.sum() / max(sh["h_tot"], 1e-9))
    sh.update({"bases": (bx, by), "lam": lam, "back": back, "V": V, "G": G, "U": U, "rth": rth, "c_l": c_l, "cos_x": cos_x,
               "cos_y": cos_y, "points": points, "tau": tau, "M": M, "N": N, "via_scale": via_scale,
               "heatsink_scale": heatsink_scale})
    return sh


def _local_dynamics(problem, cell_mm, n_terms, served=0):
    """!
    @brief Modal dynamics of a board whose vias and heatsinks stay local: a coupled block of the lowest K x K modes inside the uniform system of the board without them.
    @details Without vias and heatsinks this is _modal_dynamics unchanged. With them the tile conductances of the steady model (_local_conductances) enter a coupled modal
             block (analytic_local.LocalSystem), calibrated by one factor on the via couplings so that the steady rise at the own point of the served heater equals that of
             solve_steady for the same heater; the modes outside the block are the uniform ones. The eigenvalues, sources and output rows of the block are stored in the
             (M, N, L) arrays of the uniform modes (the block is K x K x L of them), so that the step responses, the profile propagator and the frames use the same code.
    @param problem A Problem (the heater powers are the ones used for the calibration; with one served heater of several, the others should have zero power).
    @param cell_mm Cell size (mm) of the sampling grid.
    @param n_terms Modes per direction (cosines, or the eigenfunctions of the convective edge).
    @param served Index of the heater whose own point sets the calibration.
    @return Dict from _modal_dynamics with the extra keys local_max (degC, steady temperature at the served point, None without local elements), scaled ("local" or None),
            local (the analytic_local.LocalSystem or None), local_factor (the factor on the via couplings, 1 without) and local_note (text when the factor hit the end of
            its bracket, else None).
    """
    ambient = problem.board.ambient
    has_local = bool(problem.vias or problem.heatsinks)
    if not has_local or problem.total_power() <= 0:
        d = _modal_dynamics(problem, cell_mm, n_terms)                    # No local element, or no power to calibrate with: the uniform (smeared) system as before
        d.update({"local_max": None, "scaled": None, "local": None, "local_factor": 1.0, "local_note": None})
        return d
    d = _modal_dynamics(problem, cell_mm, n_terms, 0.0, 0.0)             # the board without vias and heatsinks
    d.update({"local_max": None, "scaled": None, "local": None, "local_factor": 1.0, "local_note": None})
    bx, by = d["bases"]
    # The steady solve first: its dense matrices are freed before the (also dense) block of the transient is built, so the peak memory is the larger of the two, not the sum
    steady = solve_steady(problem, cell_mm=cell_mm, n_terms=n_terms)
    lc = _local_conductances(problem, _effective_sheet(problem, cell_mm), bx, by)       # (the dict d holds the decay rates under the key lam, the sheet the fin length)
    if not len(lc["active"]):
        return d
    L, W, H = d["L"], d["W"], d["H"]
    K = max(min(LOCAL_MODES, n_terms, int(math.sqrt(LOCAL_MAX_UNKNOWNS / L))), 1)
    tw, th = lc["tw"], lc["th"]
    PX, PY = lc["PX"][:K] / tw, lc["PY"][:K] / th                         # Average of the first K eigenfunctions over each active tile
    A = _modal_matrix(problem, d, n_terms, 0.0, 0.0)[:K, :K]
    ls = LocalSystem(A, d["c_l"], bx.weight[:K], by.weight[:K], PX, PY, lc["Cv"], lc["cs"], W, H)
    lay, iy, ix = d["points"][served]
    wx, wy = bx.at(d["xs"][ix]), by.at(d["ys"][iy])
    q_all = _heater_unit_sources(problem, bx, by)                          # 1 W of every heater
    del lc["Cv"], lc["cs"]                                                 # (now held as projections inside the LocalSystem)
    # Target: the steady rise per watt of the corrected steady model at the own point of the served heater, less what the modes outside the block carry
    power = problem.heaters[served].power
    target = float(steady.T[lay, iy, ix] - ambient) / power
    outside = np.ones((n_terms, n_terms, 1), dtype=bool)
    outside[:K, :K] = False
    rest = float(np.sum(d["U"][served] * d["G"][served] / d["lam"] * outside))
    s, ok = ls.calibrate(q_all[served][:K, :K], ls.output_row(wx[:K], wy[:K], lay), target - rest)
    lam_b = ls.decompose()
    lam = d["lam"].copy()
    lam[:K, :K] = lam_b
    G = d["G"].copy()
    U = d["U"].copy()
    for i, q in enumerate(q_all):
        G[i, :K, :K] = ls.source_row(q[:K, :K])
        l_i, iy_i, ix_i = d["points"][i]
        U[i, :K, :K] = ls.point_row(bx.at(d["xs"][ix_i])[:K], by.at(d["ys"][iy_i])[:K], l_i)
    back = d["back"].copy()
    back[:K, :K] = 0.0                                                   # The block modes reach the field through LocalSystem.coefficients
    d.update({"lam": lam, "G": G, "U": U, "back": back, "local": ls, "local_factor": float(s), "K": K,
              "rth": np.einsum("hmnk,hmnk,mnk->h", U, G, 1.0 / lam), "scaled": "local", "local_max": float(steady.T[lay, iy, ix])})
    if not ok:
        d["local_note"] = (f"the coupling of the vias in the coupled block of the Analytic transient could not reach the steady value of the board with the factor limited "
                           f"to {num(FACTOR_BRACKET[0], 3)} .. {num(FACTOR_BRACKET[1], 3)} (it took {num(s, 3)}): the time behaviour near the vias is approximate")
    return d


def _point_vector(d, point):
    """!
    @brief Row that evaluates the temperature at a grid point from the modal state of a system.
    @param d Dict from _modal_dynamics.
    @param point Tuple (layer, iy, ix) of the sampling grid.
    @return Array (M, N, L) such that T = sum(vector * b).
    """
    lay, iy, ix = point
    bx, by = d["bases"]
    wx, wy = bx.at(d["xs"][ix]), by.at(d["ys"][iy])
    row = wx[:, None, None] * wy[None, :, None] * d["back"][:, :, lay, :]
    ls = d.get("local")
    if ls is not None:
        row[:ls.K, :ls.K] = ls.point_row(wx[:ls.K], wy[:ls.K], lay)       # the coupled block: eigen coordinates are not the modes of the uniform board
    return row


class _ModalSet:
    """!
    @brief The modal system or systems that describe a board for the transient.
    @details Without vias and heatsinks one system serves every heater. With them each heater gets its own system, calibrated
             (see _local_dynamics) with that heater alone, because a single factor cannot be right both for a heater above
             a via array and for one far from it. The temperature at a heater is then the sum of the contributions of all the
             systems at its own hottest point.
    """

    def __init__(self, problem, cell_mm, n_terms):
        """!
        @param problem A Problem.
        @param cell_mm Cell size (mm) of the sampling grid.
        @param n_terms Modes per direction (cosines, or the eigenfunctions of the convective edge).
        """
        nh = len(problem.heaters)
        self.nh = nh
        if (problem.vias or problem.heatsinks) and nh > 1:
            self.ds, self.serve = [], list(range(nh))
            for j in range(nh):
                solo = copy.deepcopy(problem)
                for k, h in enumerate(solo.heaters):
                    h.power = 1.0 if k == j else 0.0                    # Unit power: only the shape of its response matters
                self.ds.append(_local_dynamics(solo, cell_mm, n_terms, j))
        else:
            self.ds, self.serve = [_local_dynamics(problem, cell_mm, n_terms)], [0] * nh
        d0 = self.ds[0]
        self.d0 = d0
        self.points = [self.ds[self.serve[k]]["points"][k] for k in range(nh)]          # Own hottest point of every heater
        self.U = [np.stack([_point_vector(d, p) for p in self.points]) for d in self.ds]  # (nh, M, N, L) per system
        # Resistance of every heater to its own point, through the system that serves it
        self.rth = np.array([float(np.sum(self.U[self.serve[k]][k] * self.ds[self.serve[k]]["G"][k]
                                          / self.ds[self.serve[k]]["lam"])) for k in range(nh)])
        self.tau = max(d["tau"] for d in self.ds)
        self.scaled = [(d["scaled"], d["local_factor"], d["local_max"]) for d in self.ds if d["local_max"] is not None]      # factor on the via couplings of each system
        self.notes = [d["local_note"] for d in self.ds if d["local_note"]]

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
            if d.get("local") is not None:
                a[:d["local"].K, :d["local"].K] += d["local"].coefficients(b[:d["local"].K, :d["local"].K])       # modes of the coupled block
            total = total + np.stack([d["cos_y"] @ a[:, :, l].T @ d["cos_x"].T for l in range(d["L"])])
        return total


def step_responses(problem, cell_mm=1.0, n_terms=300, t_end=None, n_times=100):
    """!
    @brief Unit-step response of every heater's hottest point, in closed form.
    @details Z_i(t) = sum over modes of U g (1 - exp(-lambda t)) / lambda, in the system that serves heater i.
    @param problem A Problem with at least one heater.
    @param cell_mm Cell size (mm) of the sampling grid.
    @param n_terms Modes per direction (cosines, or the eigenfunctions of the convective edge).
    @param t_end Last time in seconds (default: ten board time constants).
    @param n_times Number of logarithmically spaced times.
    @return Tuple (times, z, rth) as in fvm.step_responses.
    """
    blocks.require_no_blocks(problem)                            # These models have no metal blocks
    problem = problem.drop_off_board_vias()                      # A via with no board under its drill conducts nothing (as in the grid models)
    problem = laminate.series_bottom_problem(problem)            # One-layer board: the laminate in series with the bottom film (laminate.py)
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
        @param n_terms Modes per direction (cosines, or the eigenfunctions of the convective edge).
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
        scales = ", ".join(f"{num(sc, 3)}" for _, sc, _ in ms.scaled)
        if problem.heatsinks:
            # Measured on 12 test boards (one 60 x 40 mm family, one 10 x 10 mm part, 2 and 4 layers, 8 with a heatsink; unit-step response and square waves; the FVM at
            # 0.5 mm, converged), research/analytic-2-6 README 6.3 and docs/validation.md 4.1: the time to 63 % of the local coupled block is -8.1 % to +0.5 % (-8.1 % to
            # -0.1 % with a heatsink; the worst is the 4-layer board with vias and a 300 W/m2K heatsink), the smeared transient of 2.5.0 was -66 % to +175 %. Several parts,
            # partial copper, an outline and the profile runs are not in the sample. The Lumped model is no safe alternative with the heatsink beside the part (-38 %).
            self.warnings.append(heatsink_transient_warning(scales if ms.scaled else ""))
        elif ms.scaled:
            self.warnings.append(
                "the analytic transient keeps the vias as couplings in a block of the lowest modes of the board and, for every heater, scales their conductance "
                f"(factors {scales}) so that its steady response matches the locally corrected steady model; the dynamics near them are approximate, use the FVM to confirm")
        self.warnings.extend(ms.notes)

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
        if d.get("local") is None:
            states[0][0, 0, :] = np.einsum("lk,l->k", d["V"][0, 0], np.sqrt(d["c_l"]) * (t0 - self.ambient))
        else:
            K = d["local"].K
            states[0][:K, :K, :] = d["local"].uniform_state(t0 - self.ambient)       # its constant mode is mixed with the others in the block
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


HEATSINK_TRANSIENT_KEY = "-8 % to +1 %"      # The measured range quoted by the heatsink warning (tests and the Results summary look for it)


def heatsink_transient_warning(scales=""):
    """!
    @brief Text of the warning for the Analytic time behaviour of a board with a heatsink (vias and heatsinks are couplings of a block of the lowest modes).
    @param scales Calibration factors of the via couplings of the modal systems as text (empty for none).
    @return str Warning text (measured range of the time to 63 % against the converged FVM, a sample and not a bound).
    """
    return ("the analytic transient keeps the heatsinks as local couplings in a block of the lowest modes of the board: with a heatsink the time to 63 % was, on a sample "
            "of test boards, from about -8 % to +1 % off the converged finite-volume result (the worst, -8 %, a 4-layer board with vias and a strong heatsink, 300 W/m2K); "
            "this is a sample, not a bound (one 60 x 40 mm family, one part; several parts, partial copper and a board outline were not tested); "
            "use the FVM or the FDM to confirm the time behaviour with a heatsink"
            + (f" (via coupling factors {scales})" if scales else ""))


def run_profile(problem, decisions, options, cell_mm=1.0, n_terms=300, progress=None):
    """!
    @brief Time simulation of a problem with power profiles using the analytic modal model.
    @param problem A Problem (heater powers equal the averages).
    @param decisions Decisions from profiles.decide().
    @param options ProfileOptions.
    @param cell_mm Cell size (mm) of the sampling grid.
    @param n_terms Modes per direction (cosines, or the eigenfunctions of the convective edge).
    @param progress Optional callback progress(message, fraction).
    @return ProfileResult.
    @throws ProfileError If the run is too expensive for options.max_steps.
    """
    blocks.require_no_blocks(problem)                            # These models have no metal blocks
    problem = problem.drop_off_board_vias()                      # A via with no board under its drill conducts nothing (as in the grid models)
    problem = laminate.series_bottom_problem(problem)            # One-layer board: the laminate in series with the bottom film (laminate.py)
    from . import profiles
    result = profiles.run_windows(problem, decisions, options, _AnalyticAdapter(problem, cell_mm, n_terms), "analytic", progress)
    # A run with every heater averaged returns before the adapter's warnings are copied, yet the decision used the local step response: say it anyway
    if problem.heatsinks and not any(HEATSINK_TRANSIENT_KEY in w for w in result.warnings):
        result.warnings.append(heatsink_transient_warning())
    return result


def solve_transient(problem, t_end, n_out=40, cell_mm=1.0, n_terms=300, log_times=True):
    """!
    @brief Response to the heater powers switched on at t = 0 on a board at ambient temperature, in closed form.
    @details Every cosine mode follows b(t) = (1 - exp(-lambda t)) / lambda * g, so any time is evaluated directly with no
             time stepping. Vias and heatsinks stay local in a coupled block of the lowest modes (see _local_dynamics); the time behaviour near them is approximate, the FVM confirms it.
    @param problem A Problem (its heater powers; profiles are ignored, the average power is used).
    @param t_end Final time in seconds.
    @param n_out Number of output frames after t = 0.
    @param cell_mm Cell size (mm) of the sampling grid.
    @param n_terms Modes per direction (cosines, or the eigenfunctions of the convective edge).
    @param log_times True for logarithmically spaced times (resolves fast and slow parts), False for linear.
    @return TransientResult (its warnings hold the limits of the model met by the run, prefixed "Analytic (animation)", as the profile runs report them).
    """
    blocks.require_no_blocks(problem)                            # These models have no metal blocks
    problem = problem.drop_off_board_vias()                      # A via with no board under its drill conducts nothing (as in the grid models)
    from .results import TransientResult
    problem = problem.steady_copy("average") if problem.has_profiles() else problem
    problem = laminate.series_bottom_problem(problem)            # One-layer board: the laminate in series with the bottom film (laminate.py)
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
                           steady_t_max=ad.steady_average_max, ambient=problem.board.ambient,
                           warnings=[f"Analytic (animation): {w}" for w in ad.warnings])   # The animation has no Results summary: the GUI status and the CLI show these
