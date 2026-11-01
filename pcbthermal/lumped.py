#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
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
  top, bottom, heatsinks and edges);
- vias: the barrels are kept apart from the dielectric. In every ring that holds vias, each plane reaches the barrel through a well (the constriction
  resistance of the heat converging on a barrel in a sheet whose temperature is a ring mean: the Krogh cell of one via, plus, for a group of two or more vias,
  the group as one disc whose radius is capped at 0.75 fin lengths); the barrel nodes are eliminated and the rings get couplings between all their planes
  (viaconstriction.py, docs/theory.md section 6.1). Without vias the network is the one described above, bit for bit.

- zones: when a dense group of vias covers part of a larger footprint, the footprint has two nodes per layer instead of one (the rest A and the core C of the vias,
  _zone_network): the heat of the rest has to travel sideways to the core, in parallel with its own vertical paths, which one node cannot show (the via effect came out up to
  60 % too small). The link A-C is the logarithmic-potential resistance of the real shapes, the source is split by area, the hottest point is the largest of the hottest point of
  A, the core plus the rim of the cell of one via, and the core with the bump of a hotter core. A footprint whose core fills more than 92 % of it (on the grid or on a 0.1 mm
  grid), has no group of vias, or sits on a one-layer board keeps the one-node network, line for line (_one_node_network). The raster of a board with a zoned part is 0.5 mm
  (cell_for). Docs: docs/theory.md 5, research/lumped-zones-adoption.

Each heater gives a small dense linear system, solved exactly. Because the problem is linear, the
temperature at any point is the sum of the rises caused by every heater (mutual heating comes from
interpolating the radial profile of one heater at the distance of the other). The peak inside a
footprint adds (phi_mean - phi_min) Q_lateral / (2 pi S), also from the logarithmic potential.
"""

import logging
import math
import time
from types import SimpleNamespace

import numpy as np
from scipy import ndimage
from scipy.linalg import lu_factor, lu_solve
from scipy.special import ive, k0

from . import profiles, viaconstriction
from .fvm import Network, board_time_constant

RING_MIN_WIDTH = 1.0        # Minimum width of a ring in cells: thinner rings are merged (0 keeps the edges of the geometric series as they are)
from . import blocks
from .geometry import cell_index_of_point, coverage_fraction, polygon_centroid
from .results import SteadyResult

log = logging.getLogger(__name__)

_MAX_POTENTIAL_CELLS = 900          # Footprint cells above which the potential integrals aggregate the cells in blocks

# --- The zone model (a footprint over a dense group of vias is cut into the rest A and the core C; docs/theory.md 5; research/lumped-zones-adoption)
ZONES = True                        # False keeps every footprint as one node (an internal switch for the tests, not a user setting)
CORE_R = 0.7071                     # Radius of the core around a via in nearest-neighbour distances: 1 / sqrt(2) covers a square lattice (assumed, README 4.1)
MAX_CORE = 0.92                     # Largest share of the footprint the core may cover before the footprint stays one node (assumed; with 94 to 99 % the zones read the part 6 to 14 % hot, README 9.7)
FINE_MM = 0.1                       # Cell of the fine grid on which the share of the core is counted for the decision (mm): it does not depend on the user's raster
ZONE_CELL_MM = 0.5                  # Lumped raster of a board that has a zoned part (mm): the core must be a handful of cells across (README 4.3)
MAX_ZONE_CELLS = 700                # Points kept per zone in the potential integrals (blocks of k x k cells above it)


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
    if len(idx) > _MAX_POTENTIAL_CELLS:
        return _footprint_potentials_blocks(cov, idx, w, boundary, dx, dy)
    # Up to the limit every footprint cell is a source (no decimation: the numbers are the exact sums)
    pos = np.column_stack([idx[:, 1] * dx, idx[:, 0] * dy])
    d = np.hypot(pos[:, None, 0] - pos[None, :, 0], pos[:, None, 1] - pos[None, :, 1])
    np.fill_diagonal(d, 0.447 * np.sqrt(dx * dy))     # Mean log distance inside a cell
    phi = (np.log(d) * w[None, :]).sum(axis=1) / w.sum()
    phi_mean = float((phi * w).sum() / w.sum())
    phi_bnd = float(phi[boundary].mean()) if boundary.any() else phi_mean
    return phi_mean, phi_bnd, float(phi.min())


def _footprint_potentials_blocks(cov, idx, w, boundary, dx, dy):
    """!
    @brief Footprint potentials of a large footprint: the cells are aggregated in k x k blocks instead of keeping every step-th cell.
    @details Keeping every step-th cell in row order aliases when the footprint width is a multiple of the step (the same columns
             are always kept and the last one is never read: the mean-to-boundary term came out 4 % short on a 20 mm square and
             11 % on a 30 mm one at 0.5 mm). A block takes the weighted centroid of its cells, the sum of their weights and the
             self distance 0.447 sqrt(area of its cells); k is the smallest integer that leaves at most _MAX_POTENTIAL_CELLS blocks.
             The boundary cells keep their own positions (a block centroid lies half a block inside the edge) and are read against
             the block sources, with the distance never below the self distance of the block; the minimum is read the same way at
             the cells of the nine lowest blocks. Against the sum over every cell: link term within 0.1 %, peak term within 0.15 %
             (squares, a disc, an L, a square ring, footprints cut by the board edge; tests/test_lumped_footprint.py).
    @param cov Array (ny, nx) of footprint coverage in [0, 1].
    @param idx Array (n, 2) of the (row, column) indices of the footprint cells.
    @param w Coverage of those cells, array (n,).
    @param boundary Boolean array (n,), True for the cells on the exchange boundary.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @return Tuple (phi_mean, phi_boundary, phi_min) as _footprint_potentials.
    """
    nx = cov.shape[1]
    k = max(int(np.ceil(np.sqrt(len(idx) / _MAX_POTENTIAL_CELLS))), 1)
    # Block of every cell, and the sums of weight, weight * x, weight * y and cell count per block
    key = (idx[:, 0] // k) * ((nx + k - 1) // k) + idx[:, 1] // k
    _, inv = np.unique(key, return_inverse=True)
    wb = np.bincount(inv, weights=w)
    xb = np.bincount(inv, weights=w * idx[:, 1]) / wb
    yb = np.bincount(inv, weights=w * idx[:, 0]) / wb
    nb = np.bincount(inv).astype(float)
    pos = np.column_stack([xb * dx, yb * dy])
    db = 0.447 * np.sqrt(nb * dx * dy)
    d = np.hypot(pos[:, None, 0] - pos[None, :, 0], pos[:, None, 1] - pos[None, :, 1])
    d[np.arange(len(pos)), np.arange(len(pos))] = db
    phi = (np.log(d) * wb[None, :]).sum(axis=1) / wb.sum()
    phi_mean = float((phi * wb).sum() / wb.sum())

    def at_cells(sel):
        # Potential at the own positions of the selected cells against the block sources (never closer than a block's self distance)
        cp = np.column_stack([idx[sel, 1] * dx, idx[sel, 0] * dy])
        dd = np.hypot(cp[:, None, 0] - pos[None, :, 0], cp[:, None, 1] - pos[None, :, 1])
        return (np.log(np.maximum(dd, db[None, :])) * wb[None, :]).sum(axis=1) / wb.sum()

    phi_bnd = float(at_cells(boundary).mean()) if boundary.any() else phi_mean
    # The minimum (hottest point) is read at the cells of the lowest blocks, not at a block centroid: a centroid can lie between
    # cells or off the hot centre (a footprint of an odd number of cells, partial blocks at the edge), which made the peak term
    # up to 1.3 % short; at the cells it is within 0.15 % of the sum over every cell
    low = np.argsort(phi)[:9]
    phi_min = float(at_cells(np.isin(inv, low)).min())
    return phi_mean, phi_bnd, phi_min


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


def ring_edges(rho_max, dx, dy, rings, min_width=None):
    """!
    @brief Outer distances of the rings around a footprint: a geometric series from rho1 to the farthest cell, with edges closer than the minimum width merged.
    @details rho1 = max(1.5 cells, 0.04 rho_max), at most rho_max / 2; then rho1 (rho_max / rho1)^(k / (rings - 1)). A ring thinner than the raster holds a
             count of cells that does not match its width, so its contour length (area / width) and its resistance come out wrong (the result grew with the
             ring count: +3 to +13 % with 40 rings); edges closer than min_width cells are merged, so asking for more rings than the raster can show changes nothing.
    @param rho_max Distance of the farthest cell from the footprint in m.
    @param dx Cell size along x in m.
    @param dy Cell size along y in m.
    @param rings Number of rings requested.
    @param min_width Minimum ring width in cells (None: RING_MIN_WIDTH).
    @return Array of edges [0, rho1, ..., rho_max (slightly enlarged)].
    """
    rho1 = max(1.5 * min(dx, dy), 0.04 * rho_max)
    rho1 = min(rho1, rho_max * 0.5)
    edges = np.concatenate([[0.0], rho1 * (rho_max / rho1) ** (np.arange(rings) / max(rings - 1, 1))])
    edges[-1] = rho_max * 1.0000001
    w_min = (RING_MIN_WIDTH if min_width is None else min_width) * max(dx, dy)
    if w_min > 0 and len(edges) > 2:
        kept = [0.0, edges[1]]
        for e in edges[2:-1]:
            if e - kept[-1] >= w_min:
                kept.append(e)
        if edges[-1] - kept[-1] < w_min and len(kept) > 2:
            kept.pop()
        edges = np.array(kept + [edges[-1]])
    return edges


def _one_node_network(net, cov, layer, power, rings, vias=None):
    """!
    @brief Build and solve the offset-contour network of one heater with the footprint as ONE node per layer (the network of every release up to 2.4.5).
    @note This is the body of the former _heater_network moved unchanged: the heaters that the zone model does not split run exactly these lines
          (bit-identical results, INTEGRATION 11.2 of research/lumped-zones-adoption).
    @param net Network (per-cell arrays) of the problem.
    @param cov Footprint coverage of the heater, array (ny, nx).
    @param layer 0-based heater layer.
    @param power Heater power (W).
    @param rings Number of rings outside the footprint.
    @param vias ViaSet of the problem (viaconstriction.py) or None for a board without vias; the barrels then join the sheets through a well each
           (constriction of the heat converging on the barrel), also between non-adjacent sheets.
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
        edges = ring_edges(rho_max, net.dx, net.dy, rings)
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
    nb = net.n_board                                    # Board layers; a metal block adds layers after them
    g_block = np.array([ring_sum(net.g_block[l]) for l in range(L)])
    far = {}                                            # Couplings between non-adjacent sheets (only with vias): (l, m) -> array (R,)
    if vias is not None and len(vias) and nb > 1:
        # The barrels are not in the dielectric gz: each ring and group of vias gets wells (constriction) in series with the barrel, Kron reduced
        gz_diel = np.array([ring_sum(net.gz[l]) for l in range(nb - 1)])
        coupling = viaconstriction.ring_couplings(vias, net, idx, R, cnt, S, g_top, g_bot, gz_diel, nb)
        gz = np.array([coupling[(l, l + 1)] for l in range(nb - 1)])
        far = {key: g for key, g in coupling.items() if key[1] > key[0] + 1}
    else:
        # The rings read the barrel as a point conductance (gz_via); the FVM matrix holds it as mean-potential couplings instead
        gz = np.array([ring_sum(net.gz[l] + net.gz_via[l]) for l in range(nb - 1)]) if nb > 1 else np.zeros((0, R))
    links = [(a, b, ring_sum(g)) for a, b, g in net.extra_links]       # Contact of a block with its board face
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
            # Thermal resistance between the area-mean temperatures of rings k and k+1 in layer l (K/W); infinite where the layer (a block) has no material
            if S[l, k] <= 0 or S[l, k + 1] <= 0:
                return np.inf
            half_k1 = 0.5 * thick[k + 1] / (S[l, k + 1] * length[k + 1])
            if k == 0:
                return f_r[l] * max(phi_bnd - phi_mean, 1e-3) / (2.0 * np.pi * S[l, 0]) + half_k1
            return 0.5 * thick[k] / (S[l, k] * length[k]) + half_k1

        for l in range(L):
            for k in range(R - 1):
                r_link = link_resistance(l, k)
                if np.isfinite(r_link):
                    couple(l * R + k, l * R + k + 1, 1.0 / r_link)
            if l < nb - 1:
                for k in range(R):
                    couple(l * R + k, (l + 1) * R + k, gz[l, k])
        for (l_a, l_b), g_ab in far.items():                 # Barrel couplings across several gaps (the reduced star of the vias)
            for k in range(R):
                if g_ab[k] != 0.0:
                    couple(l_a * R + k, l_b * R + k, g_ab[k])
        for a, b, g in links:
            for k in range(R):
                if g[k] > 0:
                    couple(a * R + k, b * R + k, g[k])
        diag = (g_top + g_bot + g_heatsink + g_side + g_block).ravel()
        K[np.arange(n), np.arange(n)] += np.where(diag > 0, diag, 0.0)
        Q = np.zeros(n)
        Q[layer * R] = power
        # A block layer that does not reach a ring has no coupling at all: pin that node to zero so the matrix stays regular
        iso = np.diag(K) <= 0
        K[iso, iso] = 1.0
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
            loss = (g_top[l, 0] + g_bot[l, 0] + g_heatsink[l, 0] + g_side[l, 0] + g_block[l, 0]) * th[l, 0]
            if l < nb - 1:
                loss += gz[l, 0] * (th[l, 0] - th[l + 1, 0])
            if l > 0 and l < nb:
                loss += gz[l - 1, 0] * (th[l, 0] - th[l - 1, 0])
            for (l_a, l_b), g_ab in far.items():                   # Barrel couplings across several gaps
                if l_a == l:
                    loss += g_ab[0] * (th[l, 0] - th[l_b, 0])
                elif l_b == l:
                    loss += g_ab[0] * (th[l, 0] - th[l_a, 0])
            for a, b, g in links:                                  # Contact with a block: heat leaving this layer towards the block (or arriving)
                if a == l:
                    loss += g[0] * (th[a, 0] - th[b, 0])
            g_eff[l] = max(loss, 0.0) / (max(th[l, 0], 1e-9) * A_foot)
        f_r, f_p = _interior_factors(a_eq * np.sqrt(np.maximum(g_eff, 1e-12) / np.maximum(S[:, 0], 1e-12)))

    # --- Peak inside the footprint from the lateral outflow of ring 0 (logarithmic potential)
    lat = (th[layer, 0] - th[layer, 1]) / link_resistance(layer, 0) if R > 1 else 0.0
    peak_extra = max(lat, 0.0) * f_p[layer] * (phi_mean - phi_min) / (2.0 * np.pi * S[layer, 0])
    r01 = link_resistance(layer, 0) if R > 1 else np.inf
    return {"theta": th, "rho": rho_mean, "dist": dist, "peak_extra": peak_extra,
            "K": K, "C": cap.ravel(), "R": R, "layer": layer, "r01": r01,
            "peak_coef": f_p[layer] * (phi_mean - phi_min) / (2.0 * np.pi * S[layer, 0]),
            "out": {"top": float((g_top * th).sum()), "bottom": float((g_bot * th).sum()),
                    "heatsinks": float((g_heatsink * th).sum()), "sides": float((g_side * th).sum())}
                   | ({"blocks": float((g_block * th).sum())} if net.block_info else {}),
            "residual": float(np.linalg.norm(K @ theta - Q) / np.linalg.norm(Q))}


# ------------------------------------------------------------------------------------------------ the zone model

def _core_mask(net, cov, vias):
    """!
    @brief The cells of the footprint that the dense groups of vias cover (the core).
    @details For every group of vias (single linkage, viaconstriction.via_groups) with two or more vias in the footprint, the cells within CORE_R times the mean
             nearest-neighbour distance of those vias of one of them; only footprint cells count.
    @param net Network (grid: nx, ny, dx, dy).
    @param cov Footprint coverage, array (ny, nx).
    @param vias ViaSet or a view with x, y, d_nn and group (positions in the frame of the grid), or None.
    @return numpy.ndarray bool (ny, nx), or None when no group of two or more vias lies in the footprint.
    """
    if vias is None or len(vias) < 2:
        return None
    foot = cov > 0
    core = np.zeros(foot.shape, bool)
    for g in np.unique(vias.group):
        mem = np.flatnonzero(vias.group == g)
        cells = []
        for i in mem:
            ci, cj = cell_index_of_point(vias.x[i], vias.y[i], net.nx, net.ny, net.dx, net.dy)
            if foot[ci, cj]:
                cells.append((ci, cj, i))
        if len(cells) < 2:
            continue
        seed = np.zeros(foot.shape, bool)
        for ci, cj, _ in cells:
            seed[ci, cj] = True
        r = CORE_R * float(np.mean([vias.d_nn[i] for _, _, i in cells]))
        dist = ndimage.distance_transform_edt(~seed, sampling=(net.dy, net.dx))
        core |= (dist <= r) & foot
    return core if core.any() else None


class _ViaView:
    """!
    @brief The positions, nearest-neighbour distances and groups of some vias in another frame (what _core_mask reads).
    """

    def __init__(self, x, y, d_nn, group):
        """!
        @param x x of the vias in m.
        @param y y of the vias in m.
        @param d_nn Nearest-neighbour distance of every via in m.
        @param group Group label of every via.
        """
        self.x, self.y, self.d_nn, self.group = x, y, d_nn, group

    def __len__(self):
        """!
        @brief Number of vias.
        @return int.
        """
        return len(self.x)


def _fine_core_share(net, cov, vias):
    """!
    @brief The share of the footprint covered by the core, counted on a grid of about FINE_MM so that it does not depend on the raster.
    @details The Lumped cell is split by an integer factor (at most 600 fine cells a side over the box of the footprint) and the footprint mask is replicated, weighted by the
             coverage. The vias outside the box of the footprint are dropped, not clipped onto its border: cell_index_of_point clips, which would move them onto border cells
             that belong to the footprint of a rectangle (second review, README 10.4).
    @param net Network or namespace with nx, ny, dx, dy of the Lumped raster.
    @param cov Footprint coverage on the raster (ny, nx).
    @param vias ViaSet.
    @return float share in [0, 1] (0 when there is no core).
    """
    h = FINE_MM * 1e-3
    k = max(int(round(net.dx / h)), 1)
    if k == 1:
        core = _core_mask(net, cov, vias)
        return 0.0 if core is None else float(core.sum() / (cov > 0).sum())
    ys, xs = np.nonzero(cov > 0)
    i0, i1, j0, j1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    k = min(k, max(int(600 // max(i1 - i0, j1 - j0)), 1))
    cov_f = np.kron(cov[i0:i1, j0:j1], np.ones((k, k)))
    net_f = SimpleNamespace(nx=(j1 - j0) * k, ny=(i1 - i0) * k, dx=net.dx / k, dy=net.dy / k)
    x, y = vias.x - j0 * net.dx, vias.y - i0 * net.dy
    keep = (x >= 0.0) & (x < net_f.nx * net_f.dx) & (y >= 0.0) & (y < net_f.ny * net_f.dy)
    if keep.sum() < 2:
        return 0.0
    view = _ViaView(x[keep], y[keep], np.asarray(vias.d_nn)[keep], np.asarray(vias.group)[keep])
    core = _core_mask(net_f, cov_f, view)
    # Weighted by the coverage: the replicated cells of a partly covered raster cell at the footprint edge count by their share, not whole
    return 0.0 if core is None else float((core * cov_f).sum() / cov_f.sum())


def _block_points(w, dx, dy, max_cells):
    """!
    @brief The cells of a region aggregated in blocks of k x k cells, k the smallest that keeps at most about max_cells blocks (no aliasing, unlike every step-th cell).
    @param w Weights of the cells (ny, nx), zero outside the region.
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param max_cells Largest number of blocks wanted.
    @return Tuple (positions (n, 2) in m, weights (n,), self distances (n,) in m): the weighted centroid of every block that holds part of the region, its summed weight and
            the mean log distance inside it, 0.447 sqrt(area of its cells) (for k = 1 the cell term of _footprint_potentials).
    """
    n = int((w > 0).sum())
    k = max(int(math.ceil(math.sqrt(n / max_cells))), 1)
    ny, nx = w.shape
    big_y, big_x = -(-ny // k), -(-nx // k)
    wp = np.zeros((big_y * k, big_x * k))
    wp[:ny, :nx] = w
    yy, xx = np.mgrid[0:big_y * k, 0:big_x * k]

    def block_sum(a):
        # Sum of the k x k cells of every block
        return a.reshape(big_y, k, big_x, k).sum(axis=(1, 3))
    wb, xb, yb, nb = block_sum(wp), block_sum(wp * xx), block_sum(wp * yy), block_sum((wp > 0).astype(float))
    m = wb > 0
    return np.column_stack([xb[m] / wb[m] * dx, yb[m] / wb[m] * dy]), wb[m], 0.447 * np.sqrt(nb[m] * dx * dy)


def _mean_log(p, wp, dp, q, wq, same, floor):
    """!
    @brief Weighted mean of ln(distance) between two point sets.
    @param p Positions (n, 2) in m.
    @param wp Weights (n,).
    @param dp Self distances (n,) in m, used on the diagonal when same.
    @param q Positions (m, 2) in m.
    @param wq Weights (m,).
    @param same True when the two sets are the same set (the diagonal gets the self distance).
    @param floor Smallest distance between different points in m (the cell term).
    @return float (dimensionless).
    """
    d = np.hypot(p[:, None, 0] - q[None, :, 0], p[:, None, 1] - q[None, :, 1])
    if same:
        d[np.arange(len(p)), np.arange(len(p))] = dp
    else:
        d = np.maximum(d, floor)
    return float((np.log(d) * wp[:, None] * wq[None, :]).sum() / (wp.sum() * wq.sum()))


def _mutual_potentials(w_a, w_c, dx, dy, max_cells=MAX_ZONE_CELLS):
    """!
    @brief 2 phi_AC - phi_AA - phi_CC: the mean logarithmic distances between two uniform distributions of heat on the grid (the lossless link of two regions of a sheet, any shapes).
    @details A uniform source on A and a uniform sink on C of equal strength Q on an infinite sheet give T_A - T_C = Q (2 phi_AC - phi_AA - phi_CC) / (2 pi S), phi_XY the
             mean of ln|x - y| over x in X, y in Y. For concentric discs it is the Krogh resistance of the annulus plus 1 / (8 pi S) of the core.
    @param w_a Weights of the cells of A (ny, nx).
    @param w_c Weights of the cells of C (ny, nx).
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param max_cells Points kept per region (blocks above it).
    @return float (dimensionless).
    """
    pa, wa, da = _block_points(w_a, dx, dy, max_cells)
    pc, wc, dc = _block_points(w_c, dx, dy, max_cells)
    floor = 0.447 * math.sqrt(dx * dy)
    return 2.0 * _mean_log(pa, wa, da, pc, wc, False, floor) - _mean_log(pa, wa, da, pa, wa, True, floor) - _mean_log(pc, wc, dc, pc, wc, True, floor)


def _peak_fields(wa, wc, s_a, dx, dy, lam, max_cells=MAX_ZONE_CELLS):
    """!
    @brief The field of A over its points for a unit heat sent to C and a unit heat sent to ring 1 (mean removed), and the coefficient of the bump of a core hotter than A.
    @details t(x) = [(q_in + q_out) phi_A(x) - q_in phi_C(x)] / (2 pi S) with phi_X(x) the mean of K(|x - y|) over y in X and K = K0(d / lambda) (a lossy sheet) or -ln d.
    @param wa Weights of the cells of A (ny, nx).
    @param wc Weights of the cells of C.
    @param s_a Sheet conductance of A in the source layer in W/K.
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param lam Fin length of the source layer under A in m (None: lossless).
    @param max_cells Points kept per zone.
    @return Tuple (matrix (n, 2) in K per W of q_in and of q_out, bump: the hottest point of the lossless potential of C above its mean, dimensionless, to be divided by 2 pi S).
    """
    pa, w_a, d_a = _block_points(wa, dx, dy, max_cells)
    pc, w_c, d_c = _block_points(wc, dx, dy, max_cells)
    floor = 0.447 * math.sqrt(dx * dy)

    def kernel(d):
        # -ln d (lossless) or K0(d / lambda); the same sign so that one formula serves both
        return -np.log(d) if lam is None else k0(d / lam)

    def phi(p, q, wq, dq, same):
        d = np.hypot(p[:, None, 0] - q[None, :, 0], p[:, None, 1] - q[None, :, 1])
        if same:
            d[np.arange(len(p)), np.arange(len(p))] = dq
        else:
            d = np.maximum(d, floor)
        return (kernel(d) * wq[None, :]).sum(axis=1) / wq.sum()
    f_a = phi(pa, pa, w_a, d_a, True)
    f_c = phi(pa, pc, w_c, d_c, False)
    cols = np.column_stack([f_a - f_c, f_a]) / (2.0 * math.pi * s_a)
    mean = (cols * w_a[:, None]).sum(axis=0) / w_a.sum()
    # The bump of a core hotter than A: the lossless potential of C heated uniformly with its net lateral outflow, hottest point above the mean
    pcc = np.hypot(pc[:, None, 0] - pc[None, :, 0], pc[:, None, 1] - pc[None, :, 1])
    pcc[np.arange(len(pc)), np.arange(len(pc))] = d_c
    f_cc = (-np.log(pcc) * w_c[None, :]).sum(axis=1) / w_c.sum()
    return cols - mean[None, :], float(f_cc.max() - (f_cc * w_c).sum() / w_c.sum())


class _ZonePeak:
    """!
    @brief The hottest point of the source layer of a zoned heater network as a function of the node temperatures (linear pieces precomputed, so that the transient can call it at every step).
    @details The largest of three candidates: the hottest point of A (the field of A), the core mean plus the micro peak (the rim of the cell of one via above the mean of
             the core), and the core mean plus the micro peak plus the bump of a core hotter than A. The bump is essential: without it the maximum of the via effect jumped
             from 9.1 to 20.1 % (README 4.1). All three are relative to node A, as the program's peak is relative to node 0.
    """

    def __init__(self, layer, r_ac, r_a2, fields, bump, micro):
        """!
        @param layer Source layer (0-based).
        @param r_ac Resistance A-C of the source layer in K/W.
        @param r_a2 Resistance A-ring 1 of the source layer in K/W, or None when there is no ring.
        @param fields Matrix (n, 2) of the field of A in K per W of q_in and of q_out (mean removed).
        @param bump Coefficient of the core bump in K per W of heat sent from C to A.
        @param micro Dict {via_gz, n, rim} (barrel-only couplings, vias in C, rim minus mean in K/W per via) or None.
        """
        self.layer, self.r_ac, self.r_a2 = layer, r_ac, r_a2
        self.fields, self.bump, self.micro = fields, bump, micro

    def micro_rise(self, th):
        """!
        @brief Rise of the rim of the cell of a via above the mean of the core: the heat of one via times the rim-to-mean resistance of its cell.
        @param th Node temperatures (L, R) in K.
        @return float K.
        """
        if self.micro is None:
            return 0.0
        i_tot = 0.0
        for (l_a, l_b), g in self.micro["via_gz"].items():
            if l_a == self.layer:
                i_tot += g[1] * (th[self.layer, 1] - th[l_b, 1])
            elif l_b == self.layer:
                i_tot += g[1] * (th[self.layer, 1] - th[l_a, 1])
        return max(i_tot, 0.0) / self.micro["n"] * self.micro["rim"]

    def extra(self, th):
        """!
        @brief Peak of the source layer above the temperature of node A.
        @param th Node temperatures (L, R) in K.
        @return float K (not negative).
        """
        l = self.layer
        q_in = (th[l, 0] - th[l, 1]) / self.r_ac if np.isfinite(self.r_ac) else 0.0
        q_out = (th[l, 0] - th[l, 2]) / self.r_a2 if self.r_a2 is not None and np.isfinite(self.r_a2) else 0.0
        excess = 0.0
        if q_in + q_out > 0:
            excess = float(np.max(self.fields @ np.array([q_in, q_out])))
        bump = 0.0
        if th[l, 1] > th[l, 0] and np.isfinite(self.r_ac):
            bump = (th[l, 1] - th[l, 0]) / self.r_ac * self.bump
        return max(excess, th[l, 1] + self.micro_rise(th) + bump - th[l, 0], 0.0)

    def __call__(self, th):
        """!
        @brief Temperature rise of the hottest point of the source layer.
        @param th Node temperatures (L, R) in K.
        @return float K.
        """
        return float(th[self.layer, 0] + self.extra(th))


def _zone_network(net, cov, layer, power, rings, vias, core):
    """!
    @brief The offset-contour network of one heater with the footprint cut into the rest A (node 0) and the core C (node 1); the rings follow from node 2.
    @details Same construction as _one_node_network (rings, sums by node, wells of the vias) with these differences (INTEGRATION 11.2 of research/lumped-zones-adoption):
             the vias in the core get their wells at node C (the cluster-well term is kept in every node, with the cap of 0.75 fin lengths); the link A-C of every layer is
             (2 phi_AC - phi_AA - phi_CC) / (2 pi S) of the real shapes; A to ring 1 is the annulus resistance from the core radius to the footprint radius (equal areas)
             plus the half ring, without the Bessel factor; the source of the layer is split between A and C by the coverage; the capacities are sums of cell capacities.
    @param net Network (per-cell arrays) of the problem.
    @param cov Footprint coverage of the heater, array (ny, nx).
    @param layer 0-based heater layer.
    @param power Heater power (W).
    @param rings Number of rings outside the footprint.
    @param vias ViaSet of the problem.
    @param core Boolean mask (ny, nx) of the core cells from _core_mask (a proper part of the footprint).
    @return Dict as _one_node_network with theta of shape (L, R) (R counts A and C), rho[0] = 0 and rho[1] = 1e-9 (kept increasing; the profile outside the footprint
            leaves C out and starts at A, _radial), and the keys
            source, peak, nz, core, core_across.
    """
    L, ny, nx = net.nl, net.ny, net.nx
    cell = net.dx * net.dy
    foot = cov > 0
    dist = ndimage.distance_transform_edt(~foot, sampling=(net.dy, net.dx))
    outside = ~foot
    rho_max = float(dist.max()) if outside.any() else 0.0
    if rho_max > 0:
        edges = ring_edges(rho_max, net.dx, net.dy, rings)
        idx = np.where(foot, 0, 1 + np.minimum(np.searchsorted(edges[1:], dist, side="left"), len(edges) - 2))
    else:
        edges, idx = np.array([0.0]), np.zeros((ny, nx), dtype=int)
    cnt0 = np.bincount(idx.ravel(), minlength=idx.max() + 1)
    used = np.flatnonzero(cnt0 > 0)
    remap = np.full(len(cnt0), -1)
    remap[used] = np.arange(len(used))
    idx = remap[idx]
    R0 = len(used)
    # Node index: A = 0, C = 1, the rings from 2
    idx2 = np.where(idx == 0, np.where(core, 1, 0), idx + 1)
    R = R0 + 1
    cnt = np.bincount(idx2.ravel(), minlength=R)
    flat = idx2.ravel()

    def ring_sum(a):
        # Sum of a per-cell array over the nodes
        return np.bincount(flat, weights=a.ravel(), minlength=R)

    rho_mean = ring_sum(dist) / cnt
    thick = np.zeros(R)
    for k in range(1, R0):
        lo, hi = edges[used[k] - 1], edges[used[k]]
        thick[k + 1] = max(min(hi, rho_max) - lo, 0.5 * min(net.dx, net.dy))
    length = np.where(thick > 0, cnt * cell / np.maximum(thick, 1e-12), 0.0)

    S = np.array([ring_sum(net.S[l]) / cnt for l in range(L)])
    g_top = np.array([ring_sum(net.g_top[l]) for l in range(L)])
    g_bot = np.array([ring_sum(net.g_bottom[l]) for l in range(L)])
    g_heatsink = np.array([ring_sum(net.g_heatsink[l]) for l in range(L)])
    g_side = np.array([ring_sum(net.g_side[l]) for l in range(L)])
    nb = net.n_board
    g_block = np.array([ring_sum(net.g_block[l]) for l in range(L)])
    gz_diel = np.array([ring_sum(net.gz[l]) for l in range(nb - 1)])
    gz, via_gz, seen = viaconstriction.ring_couplings(vias, net, idx2, R, cnt, S, g_top, g_bot, gz_diel, nb, want_barrel=True)
    links = [(a, b, ring_sum(g)) for a, b, g in net.extra_links]
    cap = np.array([ring_sum(net.C[l]) for l in range(L)])               # Heat capacity of every node (J/K): a sum of cells, the zones too

    # Source of the layer split between A and C by the coverage
    cov_a, cov_c = float((cov * (idx2 == 0)).sum()), float((cov * (idx2 == 1)).sum())
    frac_c = cov_c / (cov_a + cov_c)
    source = np.zeros(L * R)
    source[layer * R + 0], source[layer * R + 1] = 1.0 - frac_c, frac_c
    r_c = math.sqrt(cnt[1] * cell / math.pi)
    a_f = math.sqrt((cnt[0] + cnt[1]) * cell / math.pi)
    pot = _mutual_potentials(cov * (idx2 == 0), cov * (idx2 == 1), net.dx, net.dy)

    def lateral(l):
        # (node a, node b, resistance in K/W) of the lateral links of layer l
        out = []
        if S[l, 0] > 0 and S[l, 1] > 0:
            out.append((0, 1, pot / (2.0 * math.pi * S[l, 0])))
        if R > 2 and S[l, 0] > 0 and S[l, 2] > 0:
            out.append((0, 2, viaconstriction.annulus_out_resistance(S[l, 0], r_c, a_f) + 0.5 * thick[2] / (S[l, 2] * length[2])))
        for k in range(2, R - 1):
            if S[l, k] > 0 and S[l, k + 1] > 0:
                out.append((k, k + 1, 0.5 * thick[k] / (S[l, k] * length[k]) + 0.5 * thick[k + 1] / (S[l, k + 1] * length[k + 1])))
        return out

    n = L * R
    K = np.zeros((n, n))

    def couple(a, b, g):
        K[a, a] += g
        K[b, b] += g
        K[a, b] -= g
        K[b, a] -= g
    for l in range(L):
        for a, b, r in lateral(l):
            couple(l * R + a, l * R + b, 1.0 / r)
    for (l_a, l_b), g_ab in gz.items():
        for k in range(R):
            if g_ab[k] != 0.0:
                couple(l_a * R + k, l_b * R + k, g_ab[k])
    for a, b, g in links:
        for k in range(R):
            if g[k] > 0:
                couple(a * R + k, b * R + k, g[k])
    diag = (g_top + g_bot + g_heatsink + g_side + g_block).ravel()
    K[np.arange(n), np.arange(n)] += np.where(diag > 0, diag, 0.0)
    Q = power * source
    iso = np.diag(K) <= 0                                       # A block layer that does not reach a node: pin it to zero so the matrix stays regular
    K[iso, iso] = 1.0
    theta = np.linalg.solve(K, Q)
    th = theta.reshape(L, R)

    # --- The peak of the source layer
    lat = lateral(layer)
    r_ac = next((r for a, b, r in lat if (a, b) == (0, 1)), np.inf)
    r_a2 = next((r for a, b, r in lat if (a, b) == (0, 2)), None)
    # Fin length of the source layer under A for the kernel of the peak: films plus the dielectric to the neighbours
    area_a = cnt[0] * cell
    g_loss = (g_top[layer, 0] + g_bot[layer, 0]) / area_a
    for m in (layer - 1, layer):
        if 0 <= m < nb - 1:
            g_loss += gz_diel[m, 0] / area_a
    lam = math.sqrt(S[layer, 0] / g_loss) if g_loss > 0 else None
    fields, bump = _peak_fields(cov * (idx2 == 0), cov * (idx2 == 1), S[layer, 0], net.dx, net.dy, lam)
    micro = None
    n_v = sum(s["n"] for s in seen if s["node"] == 1)
    if n_v:
        rim = sum(s["n"] * viaconstriction.rim_minus_mean(S[layer, 1], s["r_cell"], s["a"]) for s in seen if s["node"] == 1) / n_v
        micro = {"via_gz": via_gz, "n": n_v, "rim": rim}
    peak = _ZonePeak(layer, r_ac, r_a2, fields, bump / (2.0 * math.pi * S[layer, 1]), micro)
    rho = rho_mean.copy()
    rho[0], rho[1] = 0.0, 1e-9
    cy, cx = np.nonzero(core)
    return {"theta": th, "rho": rho, "dist": dist, "peak_extra": peak.extra(th),
            "K": K, "C": cap.ravel(), "R": R, "layer": layer, "r01": r_a2 if r_a2 is not None else np.inf,
            "peak_coef": 0.0, "source": source, "peak": peak, "nz": 2, "core": core,
            "core_across": int(min(cx.max() - cx.min() + 1, cy.max() - cy.min() + 1)),
            "out": {"top": float((g_top * th).sum()), "bottom": float((g_bot * th).sum()),
                    "heatsinks": float((g_heatsink * th).sum()), "sides": float((g_side * th).sum())}
                   | ({"blocks": float((g_block * th).sum())} if net.block_info else {}),
            "residual": float(np.linalg.norm(K @ theta - Q) / np.linalg.norm(Q))}


def _heater_network(net, cov, layer, power, rings, vias=None, zone_ok=None):
    """!
    @brief Build and solve the network of one heater: the footprint is one node per layer, or two (the rest A and the core C of a dense via group) when the zone model applies.
    @details The zone model applies when (i) the footprint holds a group of two or more vias, (ii) the core they define covers less than all of the footprint and at most
             MAX_CORE of it, counted on the Lumped grid AND on a fine grid of FINE_MM (the second count does not jump with the raster, the first keeps cells for A), and (iii) the
             board has more than one layer. Otherwise the function runs _one_node_network, the network of release 2.4.5, line for line (bit-identical).
    @param net Network (per-cell arrays) of the problem.
    @param cov Footprint coverage of the heater, array (ny, nx).
    @param layer 0-based heater layer.
    @param power Heater power (W).
    @param rings Number of rings outside the footprint.
    @param vias ViaSet of the problem (viaconstriction.py) or None for a board without vias.
    @param zone_ok The fine-grid decision made before the grid existed (will_be_zoned, counted on the fixed ZONE_CELL_MM raster), or None to count the fine share on this
           grid. solve_steady and the transients pass it: the fine share counted on the user's raster is not raster-free (the footprint of the fine grid is the replicated
           support of the coarse cells), and at 0.75 mm it chose the zones on boards that will_be_zoned keeps one node, a step of up to 4.5 % of the rise (review).
    @return Dict as _one_node_network; a zoned network has theta of shape (L, R + 1) and the extra keys source (unit source vector), peak (_ZonePeak), nz (2), core (mask),
            core_across (smaller side of the box of the core, in cells).
    """
    if ZONES and zone_ok is not False and vias is not None and len(vias) >= 2 and net.n_board > 1:
        core = _core_mask(net, cov, vias)
        if core is not None:
            n_foot, n_core = int((cov > 0).sum()), int(core.sum())
            # The grid count keeps cells in A (a handful of A cells made the zones read the part 6 to 14 % hot); the fine count is the raster-free one (README 9.7)
            if n_core < n_foot and n_core <= MAX_CORE * n_foot and (zone_ok or _fine_core_share(net, cov, vias) <= MAX_CORE):
                return _zone_network(net, cov, layer, power, rings, vias, core)
    return _one_node_network(net, cov, layer, power, rings, vias)


def will_be_zoned(problem, heater, cell_mm=ZONE_CELL_MM, vias=None):
    """!
    @brief Whether the zone model will split the footprint of a heater, decided before the Lumped grid exists (the count of the fine grid only).
    @details The count is made on the fine grid of the fixed raster cell_mm, so the decision does not depend on the cell of the run. A board with an outline is decided on its
             equivalent rectangle, which is the board the Lumped model solves (api._run_model): the via positions scale with the box, and with them the core.
    @param problem A Problem (its vias with no board under them are ignored).
    @param heater The Heater (one of problem.heaters).
    @param cell_mm Lumped raster on which the footprint and the core are drawn, in mm (ZONE_CELL_MM: the one the zone model uses).
    @param vias ViaSet of the problem when the caller already has it (solve_steady), or None to build it.
    @return bool: True when the footprint holds a group of two or more vias and the core covers at most MAX_CORE of it on the fine grid.
    """
    if not ZONES or len(problem.vias) < 2 or problem.board.layers < 2:
        return False
    if problem.board.has_outline():
        # The Lumped model solves the rectangle of the same area: decide on the heater as it is placed there
        k = next(i for i, h in enumerate(problem.heaters) if h is heater)
        problem, _ = problem.equivalent_rectangle()
        heater, vias = problem.heaters[k], None
    problem = problem.drop_off_board_vias()
    if len(problem.vias) < 2:
        return False
    b = problem.board
    ns = SimpleNamespace(nx=max(int(round(b.width * 1000.0 / cell_mm)), 8), ny=max(int(round(b.height * 1000.0 / cell_mm)), 8))
    ns.dx, ns.dy = b.width / ns.nx, b.height / ns.ny
    share = _fine_core_share(ns, _footprint_coverage(ns, heater), vias if vias is not None else viaconstriction.ViaSet(problem))
    return 0.0 < share <= MAX_CORE


def cell_for(problem, cell_mm):
    """!
    @brief The Lumped raster of a run: ZONE_CELL_MM when a heater will be zoned, else the requested cell clipped to 0.5 to 1.0 mm (the clip of every release up to 2.4.5).
    @details The raster is one per board, so one zoned part moves the whole board to 0.5 mm and the other parts' results move by the raster. A part that falls back to
             one node keeps the clip: a part without vias or with one via per footprint loses nothing at 1.0 mm, and the example board stays bit-identical.
    @param problem A Problem.
    @param cell_mm Cell size requested in the options, in mm.
    @return float cell in mm.
    """
    clipped = min(max(cell_mm, 0.5), 1.0)
    if ZONES and len(problem.vias) >= 2 and problem.board.layers >= 2:
        for k, h in enumerate(problem.heaters):
            if will_be_zoned(problem, h):
                log.info("Lumped raster %.2f mm instead of %.2f mm: %s has a dense group of vias under its footprint (zone model); the raster is one per board",
                         ZONE_CELL_MM, clipped, h.name or f"heater {k + 1}")
                return ZONE_CELL_MM
    return clipped


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
    @note A metal block is one more layer of the ring network: the block layer of the FVM network (conductance k t, contact to the board layer over the copper, exposed surface
          with the fins) is aggregated into rings like the board layers. Steady state only; against the FVM it is within 2 % on average and 5 % at most (docs/validation.md section 17).
    @return SteadyResult with an approximate temperature field T of shape (layers, ny, nx).
    """
    blocks.require_rectangle(problem)                            # With an outline simulate() solves the rectangle of the same area
    problem = problem.drop_off_board_vias()                      # A via with no board under its drill conducts nothing (as in the grid models)
    problem.validate()
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 8)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 8)
    net = Network(problem, nx, ny, assemble=False, with_blocks=True, ladder=False)       # A metal block is one more layer of the network; no laminate nodes of the rule (the Lumped keeps one link per gap)
    L = net.nl
    nbl = net.n_board
    power = problem.total_power()
    xs = (np.arange(nx) + 0.5) * net.dx
    ys = (np.arange(ny) + 0.5) * net.dy
    vias = viaconstriction.ViaSet(problem) if problem.vias else None       # Nearest neighbours and groups, once for all the heaters

    theta_field = np.zeros((L, ny, nx))
    nets = []
    out = {"top": 0.0, "bottom": 0.0, "heatsinks": 0.0, "sides": 0.0, **({"blocks": 0.0} if net.block_info else {})}
    res = 0.0
    zone_rows = []                                               # Per heater of the problem: (1 if its footprint is zoned, cells across its core), for the post-run warnings
    for h in problem.heaters:
        if h.power <= 0:
            zone_rows.append((0.0, 0.0))
            continue
        zone_ok = will_be_zoned(problem, h, vias=vias) if vias is not None else False     # the raster-free decision, the same as cell_for's
        rn = _heater_network(net, _footprint_coverage(net, h), h.layer, h.power, rings, vias, zone_ok)
        rn["centroid"] = polygon_centroid(h.polygon)
        nets.append((h, rn))
        zone_rows.append((1.0, float(rn["core_across"])) if "core" in rn else (0.0, 0.0))
        for l in range(L):
            # Profile versus distance to the footprint, interpolated at every cell (constant at both ends)
            prof = _radial(rn, rn["dist"], rn["theta"][l])
            if "core" in rn:
                prof[rn["core"]] = rn["theta"][l, 1]             # The map paints the core with node C: the footprint is not one temperature (the zone statistics and the hot spots read the field)
            theta_field[l] += prof
        for k in out:
            out[k] += rn["out"].get(k, 0.0)
        res = max(res, rn["residual"])

    bottom_face = float(theta_field[net.laminate_layers[-1]].mean() + b.ambient) if net.laminate_layers else None
    theta_field = theta_field[:nbl]                              # The block layers and the laminate nodes are not part of the board field
    L = nbl
    T = theta_field + b.ambient
    # --- Peaks: own footprint peak plus the rise caused by the other heaters at its centroid
    t_peak, where = float(T.max()), None
    for j, (hj, rj) in enumerate(nets):
        theta_j = rj["theta"][hj.layer, 0] + rj["peak_extra"]
        cj = rj["centroid"]
        ij = (min(max(int(cj[1] // net.dy), 0), ny - 1), min(max(int(cj[0] // net.dx), 0), nx - 1))
        for i, (hi, ri) in enumerate(nets):
            if i != j:
                theta_j += _radial(ri, ri["dist"][ij], ri["theta"][hj.layer])
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
                "peak_correction_k": float(max((r["peak_extra"] for _, r in nets), default=0.0)),
                **({"bottom_face_mean": bottom_face} if bottom_face is not None else {})},
        arrays={"zoned_heaters": np.array(zone_rows, dtype=float).reshape(-1, 2)},
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
    net = Network(problem, nx, ny, assemble=False, with_blocks=False, ladder=False)
    systems = []
    vias = viaconstriction.ViaSet(problem) if problem.vias else None
    for h in problem.heaters:
        zone_ok = will_be_zoned(problem, h, vias=vias) if vias is not None else False     # the raster-free decision, the same as in solve_steady
        rn = _heater_network(net, _footprint_coverage(net, h), h.layer, 1.0, rings, vias, zone_ok)
        rn["centroid"] = polygon_centroid(h.polygon)
        systems.append(rn)
    return net, systems


def _own_point(system, theta):
    """!
    @brief Temperature rise at the hottest point of a heater's own footprint, from its network state.
    @param system System dict of the heater.
    @param theta State vector (layers * rings,).
    @return Rise in degC (footprint-ring value plus the peak correction of the instantaneous lateral flow; for a zoned footprint the zone peak).
    """
    peak = system.get("peak")
    if peak is not None:
        return peak(np.asarray(theta).reshape(-1, system["R"]))   # A zoned footprint: the hottest point of A, the core and its bump
    R, layer = system["R"], system["layer"]
    t0 = theta[layer * R]
    if R < 2:
        return float(t0)
    lat = (t0 - theta[layer * R + 1]) / system["r01"]
    return float(t0 + max(lat, 0.0) * system["peak_coef"])


def _unit_source(system):
    """!
    @brief Source vector of a heater network for 1 W: the whole power on the node of the footprint, or split between A and C for a zoned footprint.
    @details Putting the whole power of a zoned heater on node A drove the part 5 to 17 % hot at the end of a constant-power run (second review of research/lumped-zones-adoption, 10.1).
    @param system System dict of the heater (see _heater_network).
    @return numpy.ndarray (layers * nodes,) in W per W.
    """
    if "source" in system:
        return system["source"]
    src = np.zeros(len(system["C"]))
    src[system["layer"] * system["R"]] = 1.0
    return src


def _radial(system, dist, values):
    """!
    @brief The radial profile of a heater network at some distances from its footprint: the node values interpolated against the mean distance of the nodes.
    @details For a zoned footprint the core C (node 1) is left out: it lies inside the footprint, and the profile outside starts at the edge of the footprint, which is A
             (with C in the list every cell outside, and the other heaters' centroids, interpolated from C instead of A; review of feature/lumped-zones).
    @param system System dict of the heater (rho, and nz = 2 for a zoned footprint).
    @param dist Distance(s) to the footprint in m (scalar or array).
    @param values Node values of one layer (R,).
    @return Interpolated value(s), same shape as dist.
    """
    if system.get("nz") == 2:
        return np.interp(dist, np.delete(system["rho"], 1), np.delete(values, 1))
    return np.interp(dist, system["rho"], values)


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
    blocks.require_no_blocks(problem)                            # These models have no metal blocks
    problem = problem.drop_off_board_vias()                      # A via with no board under its drill conducts nothing (as in the grid models)
    net, systems = _unit_networks(problem, rings, cell_mm)
    if t_end is None:
        t_end = 10.0 * board_time_constant(net)
    dt0 = t_end / (per_stage * (ratio ** stages - 1.0) / (ratio - 1.0))
    times, z = [], []
    rth = np.array([_own_point(s, s["theta"].ravel()) for s in systems])
    for system in systems:
        n = len(system["C"])
        src = _unit_source(system)
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
            out.append(self.steppers[i].advance(states[i], dt, powers[i] * _unit_source(s)))
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
                    val += _radial(self.systems[i], self.cross[i][j], states[i].reshape(self.L, self.systems[i]["R"])[lay])
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
                prof = _radial(self.systems[i], self.systems[i]["dist"], th[l])
                if "core" in self.systems[i]:
                    prof[self.systems[i]["core"]] = th[l, 1]                 # the core painted with node C, as in the steady map
                f[l] += prof
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
    blocks.require_no_blocks(problem)                            # These models have no metal blocks
    problem = problem.drop_off_board_vias()                      # A via with no board under its drill conducts nothing (as in the grid models)
    return profiles.run_windows(problem, decisions, options, _LumpedAdapter(problem, rings, cell_mm), "lumped", progress)
