"""!
@file lumped.py
@brief Lumped-parameter thermal network (LPTN): one offset-contour network per heater, superposed.

@details The model is a reduction of the same per-cell network the FVM solver uses. For every
heater the board cells are grouped in "rings" by their distance to the heater footprint:

- ring 0 is the footprint itself (the cells the heater covers),
- ring k >= 1 holds the cells whose distance to the footprint lies in (E_{k-1}, E_k]; the edges E_k
  grow geometrically from a few cell sizes up to the farthest board cell.

Because the rings follow the real footprint and the real board outline, a long thin heater, an
L-shaped one or one close to an edge all get the correct contour lengths: no circular
approximation is made. For every layer and ring the real geometry is aggregated:

- lateral conduction: heat crosses the offset contours, whose length is L_k = area_k / thickness_k,
  so the resistance between the mean temperatures of rings k and k+1 is
  R = thickness_k / (2 S_k L_k) + thickness_{k+1} / (2 S_{k+1} L_{k+1}), S being the sheet conductance,
- from the footprint to ring 1 an interior term is added: the resistance between the mean
  temperature of the footprint and its boundary, computed from the logarithmic potential of the
  uniformly heated footprint, R = (phi_boundary - phi_mean) / (2 pi S) with phi = mean ln(distance),
  which is 1 / (8 pi S) for a disc. When the layer loses heat vertically under the footprint (fin length
  lambda = sqrt(S / g) not much larger than the footprint radius a) the disc solution with losses,
  expressed with the modified Bessel functions I0 and I1 of x = a / lambda, scales this term by
  4 (I0 - 2 I1 / x) / (x I1) and the peak term by 4 (2 / x^2 - 1 / (x I1)); both factors are 1 for x -> 0,
- vertical conduction and conductance to ambient: the sums of the cell values of the ring (dielectric,
  vias, top, bottom, heatsinks and edges).

Each heater gives a small dense linear system, solved exactly. Because the problem is linear, the
temperature at any point is the sum of the rises caused by every heater (mutual heating comes from
interpolating the radial profile of one heater at the distance of the other). The peak inside a
footprint adds (phi_mean - phi_min) Q_lateral / (2 pi S), also from the logarithmic potential.
"""

import math
import time

import numpy as np
from scipy import ndimage
from scipy.linalg import lu_factor, lu_solve
from scipy.special import ive

from . import profiles
from .fvm import Network
from . import blocks
from .geometry import coverage_fraction, polygon_centroid
from .results import SteadyResult

_MAX_POTENTIAL_CELLS = 900          # Footprint cells used (evenly decimated) for the potential integrals


def _footprint_potentials(cov, dx, dy):
    """!
    @brief Logarithmic potentials of a uniformly heated footprint on an infinite sheet.
    @details For a source spread over the footprint cells, the temperature at cell i is
             T_i = -(Q / (2 pi S)) * phi_i + const, with phi_i the mean of ln(distance) from cell i to the
             source cells (the self term of a square cell is ln(0.447 * cell size)).
    @param cov Array (ny, nx) of footprint coverage in [0, 1].
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @return Tuple (phi_mean, phi_boundary, phi_min): mean over the footprint, mean over its boundary
            cells, and the minimum (the hottest point).
    """
    idx = np.argwhere(cov > 0)
    w = cov[cov > 0]
    boundary = np.zeros(len(idx), dtype=bool)
    ny, nx = cov.shape
    for k, (i, j) in enumerate(idx):
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < ny and 0 <= b < nx and cov[a, b] == 0:      # Exchange boundary only; board edges are adiabatic
                boundary[k] = True
                break
    # Decimate evenly when the footprint is large, keeping weights consistent
    step = max(int(np.ceil(len(idx) / _MAX_POTENTIAL_CELLS)), 1)
    src = idx[::step]
    sw = w[::step]
    pos = np.column_stack([src[:, 1] * dx, src[:, 0] * dy])
    # phi_i for every (decimated) cell against the decimated sources
    d = np.hypot(pos[:, None, 0] - pos[None, :, 0], pos[:, None, 1] - pos[None, :, 1])
    np.fill_diagonal(d, 0.447 * np.sqrt(dx * dy) * (step ** 0.5))     # Mean log distance inside a cell
    phi = (np.log(d) * sw[None, :]).sum(axis=1) / sw.sum()
    bnd = boundary[::step]
    phi_mean = float((phi * sw).sum() / sw.sum())
    phi_bnd = float(phi[bnd].mean()) if bnd.any() else phi_mean
    return phi_mean, phi_bnd, float(phi.min())


def _interior_factors(x):
    """!
    @brief Corrections of the uniform-disc interior relations for vertical losses (fin length lambda).
    @details For a disc of radius a heated uniformly on a sheet that also loses heat vertically,
             theta(r) = q/g + A I0(r / lambda). Written with the lateral outflow Q_lat the mean-to-boundary
             and peak-to-mean differences are Q_lat / (2 pi S) times 1/4 * fR(x) and 1/4 * fP(x), where
             x = a / lambda.
    @param x Ratio of the equivalent footprint radius to the fin length (array or float, >= 0).
    @return Tuple (fR, fP) of factors equal to 1 for x -> 0 and decreasing for large x.
    """
    x = np.maximum(np.asarray(x, dtype=float), 1e-6)
    i0, i1 = ive(0, x), ive(1, x)                       # Exponentially scaled: e^{-x} I(x), no overflow
    f_r = 4.0 * (i0 - 2.0 * i1 / x) / (x * i1)          # The e^{-x} scaling cancels in this ratio
    f_p = 4.0 * (2.0 / x ** 2 - np.exp(-x) / (x * i1))
    small = x < 1e-2
    return np.where(small, 1.0, f_r), np.where(small, 1.0, f_p)


def _heater_network(net, cov, layer, power, rings):
    """!
    @brief Build and solve the offset-contour network of one heater.
    @param net Network (per-cell arrays) of the problem.
    @param cov Footprint coverage of the heater, array (ny, nx).
    @param layer 0-based heater layer.
    @param power Heater power (W).
    @param rings Number of rings outside the footprint.
    @return Dict with theta (L, R), rho (R) mean distance of every ring, dist (ny, nx) map of the distance to the
            footprint, peak_extra, and the heat leaving by each path.
    """
    L, ny, nx = net.nl, net.ny, net.nx
    cell = net.dx * net.dy
    foot = cov > 0
    # Distance of every cell to the footprint (metres); zero inside it
    dist = ndimage.distance_transform_edt(~foot, sampling=(net.dy, net.dx))
    outside = ~foot
    rho_max = float(dist.max()) if outside.any() else 0.0

    # --- Ring membership: 0 = footprint, 1..rings = geometric offsets from the footprint
    if rho_max > 0:
        rho1 = max(1.5 * min(net.dx, net.dy), 0.04 * rho_max)
        rho1 = min(rho1, rho_max * 0.5)
        edges = np.concatenate([[0.0], rho1 * (rho_max / rho1) ** (np.arange(rings) / max(rings - 1, 1))])
        edges[-1] = rho_max * 1.0000001
        idx = np.where(foot, 0, 1 + np.minimum(np.searchsorted(edges[1:], dist, side="left"), len(edges) - 2))
    else:
        edges, idx = np.array([0.0]), np.zeros((ny, nx), dtype=int)
    cnt = np.bincount(idx.ravel(), minlength=idx.max() + 1)
    used = np.flatnonzero(cnt > 0)                      # Drop rings that received no cell
    remap = np.full(len(cnt), -1)
    remap[used] = np.arange(len(used))
    idx = remap[idx]
    R = len(used)
    cnt = cnt[used]
    flat = idx.ravel()

    def ring_sum(a):
        # Sum of a per-cell array over the cells of every ring
        return np.bincount(flat, weights=a.ravel(), minlength=R)

    rho_mean = ring_sum(dist) / cnt                     # Mean distance to the footprint of every ring (ring 0: 0)
    # Ring thickness (distance range actually spanned) and contour length from the ring area
    thick = np.zeros(R)
    for k in range(1, R):
        lo, hi = edges[used[k] - 1], edges[used[k]]
        thick[k] = max(min(hi, rho_max) - lo, 0.5 * min(net.dx, net.dy))
    length = np.where(thick > 0, cnt * cell / np.maximum(thick, 1e-12), 0.0)

    S = np.array([ring_sum(net.S[l]) / cnt for l in range(L)])           # Mean sheet conductance (W/K)
    g_top = np.array([ring_sum(net.g_top[l]) for l in range(L)])
    g_bot = np.array([ring_sum(net.g_bottom[l]) for l in range(L)])
    g_heatsink = np.array([ring_sum(net.g_heatsink[l]) for l in range(L)])
    g_side = np.array([ring_sum(net.g_side[l]) for l in range(L)])
    gz = np.array([ring_sum(net.gz[l]) for l in range(L - 1)]) if L > 1 else np.zeros((0, R))
    cap = np.array([ring_sum(net.C[l]) for l in range(L)])               # Heat capacity of every ring (J/K)

    phi_mean, phi_bnd, phi_min = _footprint_potentials(cov, net.dx, net.dy)
    a_eq = np.sqrt(cnt[0] * cell / np.pi)
    A_foot = cnt[0] * cell

    def solve(f_r):
        # Assemble and solve the network for the given interior factors (one per layer)
        n = L * R
        K = np.zeros((n, n))

        def couple(a, b, g):
            K[a, a] += g
            K[b, b] += g
            K[a, b] -= g
            K[b, a] -= g

        def link_resistance(l, k):
            # Thermal resistance between the area-mean temperatures of rings k and k+1 in layer l (K/W)
            half_k1 = 0.5 * thick[k + 1] / (S[l, k + 1] * length[k + 1])
            if k == 0:
                return f_r[l] * max(phi_bnd - phi_mean, 1e-3) / (2.0 * np.pi * S[l, 0]) + half_k1
            return 0.5 * thick[k] / (S[l, k] * length[k]) + half_k1

        for l in range(L):
            for k in range(R - 1):
                couple(l * R + k, l * R + k + 1, 1.0 / link_resistance(l, k))
            if l < L - 1:
                for k in range(R):
                    couple(l * R + k, (l + 1) * R + k, gz[l, k])
        K[np.arange(n), np.arange(n)] += (g_top + g_bot + g_heatsink + g_side).ravel()
        Q = np.zeros(n)
        Q[layer * R] = power
        theta = np.linalg.solve(K, Q)
        return theta, K, Q, link_resistance

    # The disc relations with vertical loss need an effective loss conductance per area under the footprint.
    # It is taken from the solution itself (heat leaving the footprint of a layer towards the neighbouring layers
    # and ambient, divided by its temperature rise) and the network is solved again: three passes converge.
    f_r = np.ones(L)
    f_p = np.ones(L)
    for _ in range(3):
        theta, K, Q, link_resistance = solve(f_r)
        th = theta.reshape(L, R)
        g_eff = np.zeros(L)
        for l in range(L):
            loss = (g_top[l, 0] + g_bot[l, 0] + g_heatsink[l, 0] + g_side[l, 0]) * th[l, 0]
            if l < L - 1:
                loss += gz[l, 0] * (th[l, 0] - th[l + 1, 0])
            if l > 0:
                loss += gz[l - 1, 0] * (th[l, 0] - th[l - 1, 0])
            g_eff[l] = max(loss, 0.0) / (max(th[l, 0], 1e-9) * A_foot)
        f_r, f_p = _interior_factors(a_eq * np.sqrt(np.maximum(g_eff, 1e-12) / S[:, 0]))

    # --- Peak inside the footprint from the lateral outflow of ring 0 (logarithmic potential)
    lat = (th[layer, 0] - th[layer, 1]) / link_resistance(layer, 0) if R > 1 else 0.0
    peak_extra = max(lat, 0.0) * f_p[layer] * (phi_mean - phi_min) / (2.0 * np.pi * S[layer, 0])
    r01 = link_resistance(layer, 0) if R > 1 else np.inf
    return {"theta": th, "rho": rho_mean, "dist": dist, "peak_extra": peak_extra,
            "K": K, "C": cap.ravel(), "R": R, "layer": layer, "r01": r01,
            "peak_coef": f_p[layer] * (phi_mean - phi_min) / (2.0 * np.pi * S[layer, 0]),
            "out": {"top": float((g_top * th).sum()), "bottom": float((g_bot * th).sum()),
                    "heatsinks": float((g_heatsink * th).sum()), "sides": float((g_side * th).sum())},
            "residual": float(np.linalg.norm(K @ theta - Q) / np.linalg.norm(Q))}


def _footprint_coverage(net, heater):
    """!
    @brief Coverage of a heater footprint on the network grid (the centroid cell if the footprint is smaller than a cell).
    @param net Network (grid information).
    @param heater The Heater.
    @return Array (ny, nx) in [0, 1] with a positive sum.
    """
    cov = coverage_fraction(heater.polygon, net.nx, net.ny, net.dx, net.dy, 4)
    if cov.sum() <= 0:
        cx, cy = polygon_centroid(heater.polygon)
        cov[min(max(int(cy // net.dy), 0), net.ny - 1), min(max(int(cx // net.dx), 0), net.nx - 1)] = 1.0
    return cov


def solve_steady(problem, rings=10, cell_mm=1.0):
    """!
    @brief Steady-state solution of the offset-contour networks (one per heater) with superposition.
    @param problem A Problem.
    @param rings Number of rings outside each footprint (more rings = finer radial resolution).
    @param cell_mm Raster size (mm) used to aggregate the real geometry into rings.
    @return SteadyResult with an approximate temperature field T of shape (layers, ny, nx).
    """
    problem = blocks.plain_equivalent(problem)                   # These models have no metal blocks
    problem.validate()
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 8)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 8)
    net = Network(problem, nx, ny, assemble=False, with_blocks=False)
    L = net.nl
    power = problem.total_power()
    xs = (np.arange(nx) + 0.5) * net.dx
    ys = (np.arange(ny) + 0.5) * net.dy

    theta_field = np.zeros((L, ny, nx))
    nets = []
    out = {"top": 0.0, "bottom": 0.0, "heatsinks": 0.0, "sides": 0.0}
    res = 0.0
    for h in problem.heaters:
        if h.power <= 0:
            continue
        rn = _heater_network(net, _footprint_coverage(net, h), h.layer, h.power, rings)
        rn["centroid"] = polygon_centroid(h.polygon)
        nets.append((h, rn))
        for l in range(L):
            # Profile versus distance to the footprint, interpolated at every cell (constant at both ends)
            theta_field[l] += np.interp(rn["dist"], rn["rho"], rn["theta"][l])
        for k in out:
            out[k] += rn["out"][k]
        res = max(res, rn["residual"])

    T = theta_field + b.ambient
    # --- Peaks: own footprint peak plus the rise caused by the other heaters at its centroid
    t_peak, where = float(T.max()), None
    for j, (hj, rj) in enumerate(nets):
        theta_j = rj["theta"][hj.layer, 0] + rj["peak_extra"]
        cj = rj["centroid"]
        ij = (min(max(int(cj[1] // net.dy), 0), ny - 1), min(max(int(cj[0] // net.dx), 0), nx - 1))
        for i, (hi, ri) in enumerate(nets):
            if i != j:
                theta_j += np.interp(ri["dist"][ij], ri["rho"], ri["theta"][hj.layer])
        if theta_j + b.ambient > t_peak or where is None:
            t_peak = max(t_peak, float(theta_j + b.ambient))
            where = (hj.layer, cj[0], cj[1])
    if where is None:
        l, i, j = np.unravel_index(int(np.argmax(T)), T.shape)
        where = (int(l), float(xs[j]), float(ys[i]))

    return SteadyResult(
        model="lumped", ambient=b.ambient, power_in=power, t_max=t_peak, t_min=float(T.min()),
        t_mean=float(T.mean()), layer_mean=[float(T[l].mean()) for l in range(L)],
        t_max_location=where, T=T, dx=net.dx, dy=net.dy, power_out=out, residual=res,
        extras={"heater_networks": float(len(nets)), "rings": float(rings),
                "peak_correction_k": float(max((r["peak_extra"] for _, r in nets), default=0.0))},
    )


# ----------------------------------------------------------------------------------- time dependence

def _unit_networks(problem, rings, cell_mm):
    """!
    @brief Per-heater networks solved for 1 W (the response scales linearly with power).
    @param problem A Problem with at least one heater.
    @param rings Rings outside each footprint.
    @param cell_mm Raster size in millimetres.
    @return Tuple (net, systems): the Network and a list of system dicts (see _heater_network plus "centroid").
    """
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 8)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 8)
    net = Network(problem, nx, ny, assemble=False, with_blocks=False)
    systems = []
    for h in problem.heaters:
        rn = _heater_network(net, _footprint_coverage(net, h), h.layer, 1.0, rings)
        rn["centroid"] = polygon_centroid(h.polygon)
        systems.append(rn)
    return net, systems


def _own_point(system, theta):
    """!
    @brief Temperature rise at the hottest point of a heater's own footprint, from its network state.
    @param system System dict of the heater.
    @param theta State vector (layers * rings,).
    @return Rise in degC (footprint-ring value plus the peak correction of the instantaneous lateral flow).
    """
    R, layer = system["R"], system["layer"]
    t0 = theta[layer * R]
    if R < 2:
        return float(t0)
    lat = (t0 - theta[layer * R + 1]) / system["r01"]
    return float(t0 + max(lat, 0.0) * system["peak_coef"])


class _Stepper:
    """!
    @brief Dense implicit time stepper of one small network with cached factorisations per step size.
    """

    def __init__(self, system, theta):
        """!
        @param system System dict of the heater.
        @param theta 0.5 (Crank-Nicolson) or 1.0 (implicit Euler).
        """
        self.K, self.C, self.theta = system["K"], system["C"], theta
        self.cache = {}

    def advance(self, x, dt, source):
        """!
        @brief One implicit step.
        @param x State (layers * rings,).
        @param dt Step in seconds.
        @param source Source vector (W per node) held during the step.
        @return New state.
        """
        key = round(dt, 14)
        if key not in self.cache:
            A = np.diag(self.C / dt) + self.theta * self.K
            B = np.diag(self.C / dt) - (1.0 - self.theta) * self.K
            self.cache[key] = (lu_factor(A), B)
        lu, B = self.cache[key]
        return lu_solve(lu, B @ x + source)


def step_responses(problem, rings=10, cell_mm=1.0, t_end=None, ratio=3.0, per_stage=4, stages=18, theta_scheme=0.5):
    """!
    @brief Unit-step response of every heater's hottest point with the thermal-network model.
    @param problem A Problem with at least one heater.
    @param rings Rings outside each footprint.
    @param cell_mm Raster size in millimetres.
    @param t_end Last time in seconds (default: ten board time constants).
    @param ratio Growth factor of the time step between stages.
    @param per_stage Steps per stage.
    @param stages Number of stages.
    @param theta_scheme 0.5 (Crank-Nicolson) or 1.0 (implicit Euler).
    @return Tuple (times, z, rth) as in fvm.step_responses.
    """
    problem = blocks.plain_equivalent(problem)                   # These models have no metal blocks
    net, systems = _unit_networks(problem, rings, cell_mm)
    if t_end is None:
        t_end = 10.0 * float(net.C.sum() / net.g_amb.sum())
    dt0 = t_end / (per_stage * (ratio ** stages - 1.0) / (ratio - 1.0))
    times, z = [], []
    rth = np.array([_own_point(s, s["theta"].ravel()) for s in systems])
    for system in systems:
        n = len(system["C"])
        src = np.zeros(n)
        src[system["layer"] * system["R"]] = 1.0
        stepper, x, t, row, tt = _Stepper(system, theta_scheme), np.zeros(n), 0.0, [], []
        for j in range(stages):
            dt = dt0 * ratio ** j
            for _ in range(per_stage):
                x = stepper.advance(x, dt, src)
                t += dt
                tt.append(t)
                row.append(_own_point(system, x))
        times, z = tt, z + [row]
    return np.asarray(times), np.asarray(z), rth


class _LumpedAdapter:
    """!
    @brief Adapter that advances the thermal-network model in time (see profiles.run_windows for the interface).
    """

    def __init__(self, problem, rings, cell_mm):
        """!
        @param problem A Problem (heater powers equal the averages).
        @param rings Rings outside each footprint.
        @param cell_mm Raster size in millimetres.
        """
        self.ambient = problem.board.ambient
        self.net, self.systems = _unit_networks(problem, rings, cell_mm)
        self.dx, self.dy = self.net.dx, self.net.dy
        self.nh, self.L = len(self.systems), self.net.nl
        self.p_avg = np.array([h.average_power() for h in problem.heaters])
        self.p_init = np.array([h.initial_power() for h in problem.heaters])   # Start state: average, or first power of a one-shot
        self.steady_average_max = solve_steady(problem.steady_copy("average"), rings, cell_mm).t_max
        self.steady_peak_max = solve_steady(problem.steady_copy("peak"), rings, cell_mm).t_max
        self.initial_max = self.steady_average_max
        if not np.allclose(self.p_init, self.p_avg):
            start = problem.steady_copy("average")
            for h, p in zip(start.heaters, self.p_init):
                h.power = float(p)
            self.initial_max = solve_steady(start, rings, cell_mm).t_max
        ny, nx = self.net.ny, self.net.nx
        cidx = [(min(max(int(s["centroid"][1] // self.net.dy), 0), ny - 1),
                 min(max(int(s["centroid"][0] // self.net.dx), 0), nx - 1)) for s in self.systems]
        # Distance from every heater's footprint to every heater's centroid (cross-heating terms)
        self.cross = [[self.systems[i]["dist"][cidx[j]] for j in range(self.nh)] for i in range(self.nh)]

    def prepare(self, dt):
        """!
        @brief Nothing to factorise up front (factorisations are cached per step size).
        @param dt Time step in seconds.
        """
        self.dt = dt

    def begin(self, options):
        """!
        @brief Initial state: one vector per heater network.
        @param options ProfileOptions.
        @return Tuple (state list, reported initial temperature in degC).
        """
        self.steppers = [_Stepper(s, options.theta) for s in self.systems]
        if options.initial == "average":
            return [self.systems[i]["theta"].ravel() * self.p_init[i] for i in range(self.nh)], self.initial_max
        t0 = self.ambient if options.initial_c is None else float(options.initial_c)
        states = [np.zeros(len(s["C"])) for s in self.systems]
        states[0] = np.full(len(self.systems[0]["C"]), t0 - self.ambient)      # The uniform start field lives in network 0
        return states, t0

    def advance(self, states, dt, powers):
        """!
        @brief One implicit step of every heater's network.
        @param states List of state vectors.
        @param dt Time step in seconds.
        @param powers Power of every heater during the step (W).
        @return New list of states.
        """
        out = []
        for i, s in enumerate(self.systems):
            src = np.zeros(len(s["C"]))
            src[s["layer"] * s["R"]] = powers[i]
            out.append(self.steppers[i].advance(states[i], dt, src))
        return out

    def observe(self, states):
        """!
        @brief Hottest temperature under every heater (own footprint plus the other heaters' rise at its centroid).
        @param states List of state vectors.
        @return Tuple (hottest degC, per-heater degC).
        """
        pts = np.empty(self.nh)
        for j in range(self.nh):
            lay = self.systems[j]["layer"]
            val = _own_point(self.systems[j], states[j])
            for i in range(self.nh):
                if i != j:
                    val += np.interp(self.cross[i][j], self.systems[i]["rho"],
                                     states[i].reshape(self.L, self.systems[i]["R"])[lay])
            pts[j] = val + self.ambient
        return float(pts.max()), pts

    def frame(self, states):
        """!
        @brief Approximate field: the sum of the heaters' radial profiles.
        @param states List of state vectors.
        @return Array (layers, ny, nx) in degC.
        """
        f = np.zeros((self.L, self.net.ny, self.net.nx))
        for i in range(self.nh):
            th = states[i].reshape(self.L, self.systems[i]["R"])
            for l in range(self.L):
                f[l] += np.interp(self.systems[i]["dist"], self.systems[i]["rho"], th[l])
        return f + self.ambient

    def peak_values(self, states):
        """!
        @brief The peak map is built from the stored frames, not every step.
        @param states Unused.
        @return None.
        """
        return None


def run_profile(problem, decisions, options, rings=10, cell_mm=1.0, progress=None):
    """!
    @brief Time simulation of a problem with power profiles using the thermal-network model.
    @details One small network per heater, each stepped with its own power; the temperature at a heater is its own
             footprint temperature plus the rise caused by the other heaters at its centroid, as in the steady model.
             The peak map is the maximum over the stored frames of the last window.
    @param problem A Problem (heater powers equal the averages).
    @param decisions Decisions from profiles.decide().
    @param options ProfileOptions.
    @param rings Rings outside each footprint.
    @param cell_mm Raster size in millimetres.
    @param progress Optional callback progress(message, fraction).
    @return ProfileResult.
    @throws ProfileError If the run is too expensive for options.max_steps.
    """
    problem = blocks.plain_equivalent(problem)                   # These models have no metal blocks
    return profiles.run_windows(problem, decisions, options, _LumpedAdapter(problem, rings, cell_mm), "lumped", progress)
