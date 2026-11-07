#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file viaconstriction.py
@brief Constriction resistance of the heat that converges on a via barrel, for the two reduced models (Lumped rings and Analytic tiles).

@details The Lumped model carries the area-mean temperature of a ring and the Analytic model the area-mean temperature of a tile of its Green-function mosaic. The temperature
the barrel sees is the one at its wall, and the difference is a thermal resistance (the heat converging on a disc in a sheet) that both models left out: they joined the planes
through the barrel conductance alone, so the effect of a copper-filled via was overstated by 35 to 60 % (example board: 6.3 to 6.8 K against 4.2 K of the FVM with the point-via
treatment). The closed forms here are those of research/lumped-analytic-vias, research/lumped-via-groups and research/young-omega-tiles:

* `krogh(S, R, a)`: sink disc of radius a at the centre of a circular cell of radius R with a uniform source and an insulated rim (the Wigner-Seitz cell of a lattice of vias):
  area mean minus wall temperature per watt, (1 / (2 pi S)) [b^4 ln b / (b^2 - 1)^2 - b^2 / (2 (b^2 - 1)) - 1/4], b = R / a (K/W).
* LUMPED, per ring and group of vias (`ring_couplings`): the well of the plane l is `Krogh(S_l, r_c, a) + N_g Krogh(S_l, R_macro, r_cl)` (the second term only for a group of two or
  more vias): r_c the radius of the cell of one via, min(sqrt(A_ring / (pi n)), d_nn / sqrt(pi)); r_cl = sqrt(N_g) r_c the disc the group covers; R_macro the radius of the disc of the
  rings it touches, capped at 0.75 fin lengths sqrt(S_l / g_loss) of the plane (the cluster draws heat from within a few fin lengths only). The barrel nodes and the wells are
  eliminated (Kron reduction, `viawell.kron_barrel`), which gives couplings G[l, m] between the sheets of the ring (also between non-adjacent sheets).
* ANALYTIC, per tile (`tile_grid`, `spread_weights`, `add_self_terms`): the tile is min(1 mm, 0.75 d_nn) (floor 0.25 mm, never above the program's tile, coarsened when the estimate
  of the active tiles passes 1200, and enlarged by `plan` until the active tiles times the layers are at most 4800: that last guard is beyond the tested rule); the barrel conductance of a via alone at the scale of a tile is shared among the four tiles around it with bilinear weights; the diagonal of the tile response G gets
  the self-term that makes the tile read the wall temperature: for n <= 1 vias per tile `[ln(R_blk / a) - 1/4] / (2 pi S n)`, R_blk = R_tile / sqrt(n); for n > 1
  `ln(R_tile / r_cl) / (2 pi S) + Krogh(S, r_c, a) / n`.

The target radius of a via is a = e^(-1/4) r_via (`viawell.TARGET_RATIO`, the radius of the uniform sink density over the disc of the barrel).
Constants that are assumed, not derived: linkage of a group at twice the nearest-neighbour distance, isolation 0.7 tiles for the spread, guard 0.5 tiles from a footprint, the 0.75 of
the macro cap, the 1200 estimated tiles and the 4800 unknowns (via, heatsink and block tiles together). Boards without vias do not call any of this.
"""

import math

import numpy as np

from . import viawell
from .geometry import cell_index_of_point, coverage_fraction, points_in_polygon

ETA = viawell.TARGET_RATIO       # target radius over drill radius of a via (dimensionless)
MACRO_CAP = 0.75                 # largest radius of the macro disc of a cluster, in fin lengths of the plane
TILE_CAP = 1.0e-3                # largest Analytic tile on a board with vias, m
TILE_FLOOR = 0.25e-3             # smallest Analytic tile, m (a guard, not a tuned value)
TILE_NN = 0.75                   # tile in units of the median nearest-neighbour distance of the vias (dimensionless)
MAX_ACTIVE_TILES = 1200          # estimate of the active tiles above which the tile is coarsened (memory grows as the square of tiles x layers)
MAX_UNKNOWNS = 4800              # most unknowns (active tiles x layers) of the dense system: 0.9 GB peak and 3 s at this size (500 to 2000 scattered vias, 100 x 80 mm, measured by the review)
ISOLATION = 0.7                  # a via is spread over four tiles only if its neighbour is at least this many tiles away
GUARD = 0.5                      # a via outside every footprint but closer than this many tiles to one is not spread


def krogh(s_sheet, r_cell, a):
    """!
    @brief Mean-to-wall resistance of a circular cell with a uniform source and a sink disc at the centre (insulated rim).
    @param s_sheet Sheet conductance in W/K.
    @param r_cell Cell radius in m.
    @param a Radius of the sink disc in m.
    @return float Resistance in K/W (area mean of the annulus minus wall temperature, per watt taken by the via); 0 if r_cell <= a.
    """
    if r_cell <= a or s_sheet <= 0.0:
        return 0.0
    b2 = (r_cell / a) ** 2
    return (b2 * b2 * 0.5 * math.log(b2) / (b2 - 1.0) ** 2 - b2 / (2.0 * (b2 - 1.0)) - 0.25) / (2.0 * math.pi * s_sheet)


def annulus_out_resistance(s_sheet, r_in, r_out):
    """!
    @brief Mean-to-outer-wall resistance of an annulus with a uniform source whose heat leaves only through the outer wall (the inner side is insulated).
    @details The link from the zone A of a footprint (the footprint outside the core of the vias) to the first ring: T(r) - T(r_out) = q / (2 S) [(r_out^2 - r^2) / 2 - r_in^2 ln(r_out / r)] per unit
             generation q, averaged over the annulus and divided by the heat generated, q pi (r_out^2 - r_in^2) (docs/theory.md 5, research/lumped-zones-adoption).
    @param s_sheet Sheet conductance in W/K.
    @param r_in Inner radius in m (the core).
    @param r_out Outer radius in m (the footprint of the same area).
    @return float Area mean temperature minus outer-wall temperature per watt generated in the annulus, K/W; 0 if r_out <= r_in.
    """
    if r_out <= r_in:
        return 0.0
    i1 = r_out * r_out * (r_out * r_out - r_in * r_in) / 4.0 - (r_out ** 4 - r_in ** 4) / 8.0
    i2 = r_in * r_in * (r_out * r_out / 4.0 - r_in * r_in / 2.0 * math.log(r_out / r_in) - r_in * r_in / 4.0)
    mean = (i1 - i2) / ((r_out * r_out - r_in * r_in) / 2.0) / (2.0 * s_sheet)
    return mean / (math.pi * (r_out * r_out - r_in * r_in))


def rim_minus_mean(s_sheet, r_cell, a):
    """!
    @brief Temperature of the rim of the Krogh cell above the area mean of the cell, per watt taken by the via (the micro peak of the zone model).
    @param s_sheet Sheet conductance in W/K.
    @param r_cell Cell radius in m.
    @param a Radius of the sink disc (target radius of the via) in m.
    @return float K/W: [b^2 ln b / (b^2 - 1) - 1/2] / (2 pi S), b = r_cell / a, minus the Krogh mean-to-wall resistance; 0 if r_cell <= a.
    """
    if r_cell <= a:
        return 0.0
    b = r_cell / a
    rim = (b * b * math.log(b) / (b * b - 1.0) - 0.5) / (2.0 * math.pi * s_sheet)
    return rim - krogh(s_sheet, r_cell, a)


def nearest_neighbour(points):
    """!
    @brief Distance from every point to its nearest neighbour.
    @param points Array (n, 2) of positions in m.
    @return numpy.ndarray (n,) in m; infinite when there is a single point.
    """
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    if len(pts) < 2:
        return np.full(len(pts), np.inf)
    from scipy.spatial import cKDTree
    return cKDTree(pts).query(pts, k=2)[0][:, 1]


def via_groups(points, d_nn):
    """!
    @brief Groups of vias by single linkage: two vias are joined when their distance is at most twice the larger of their nearest-neighbour distances.
    @param points Array (n, 2) of positions in m.
    @param d_nn Nearest-neighbour distance of every via in m.
    @return numpy.ndarray (n,) of integer group labels.
    """
    n = len(points)
    if n < 2:
        return np.zeros(n, dtype=int)
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    tree = cKDTree(points)
    rows, cols = [], []
    # A pair (i, j) is joined when dist <= 2 max(d_i, d_j), i.e. j lies within 2 d_i of i or i within 2 d_j of j: one ball query per via covers both
    for i, nbrs in enumerate(tree.query_ball_point(points, 2.0 * d_nn * (1.0 + 1e-12))):
        for j in nbrs:
            if j != i:
                rows.append(i)
                cols.append(j)
    if not rows:
        return np.arange(n)
    _, label = connected_components(coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n)), directed=False)
    return label


class ViaSet:
    """!
    @brief The vias of a problem with the data both reduced models need: positions, target radii, barrel conductance of every gap, nearest neighbours and groups.
    """

    def __init__(self, problem):
        """!
        @param problem A Problem with at least one via.
        """
        b = problem.board
        k_cu = b.materials.k_copper
        d = b.gap_thicknesses()
        self.x = np.array([v.x for v in problem.vias])
        self.y = np.array([v.y for v in problem.vias])
        self.r_via = np.array([v.diameter / 2.0 for v in problem.vias])
        # Barrel conductance of every via and gap in W/K (copper of the barrel plus the fill at its conductivity), shape (n, layers - 1)
        d_barrel = viawell.barrel_length(b, d)       # barrel over the gap plus half the copper thickness (viawell.BARREL_COPPER_FRACTION)
        self.g_gap = np.array([k_cu * v.thermal_area(b.via_plating, k_cu) / d_barrel for v in problem.vias]).reshape(len(problem.vias), len(d))
        pts = np.column_stack([self.x, self.y])
        self.d_nn = nearest_neighbour(pts)
        self.group = via_groups(pts, self.d_nn)

    def __len__(self):
        """!
        @brief Number of vias.
        @return int.
        """
        return len(self.x)


def ring_couplings(vs, net, idx, n_rings, cnt, s_ring, g_top, g_bot, gz_diel, nb, want_barrel=False):
    """!
    @brief Couplings between the sheets of every ring of a Lumped network, with the constriction of the vias (micro well plus capped cluster well, Kron reduced).
    @param vs ViaSet of the problem.
    @param net Network of the problem (grid size and cell size).
    @param idx (ny, nx) ring index of every cell.
    @param n_rings Number of rings R.
    @param cnt (R,) cells per ring.
    @param s_ring (L, R) mean sheet conductance of every ring in W/K.
    @param g_top (L, R) conductance to the ambient through the top face of the rings in W/K.
    @param g_bot (L, R) the same through the bottom face in W/K.
    @param gz_diel (nb - 1, R) dielectric conductance of every gap and ring in W/K (the barrels are not in it).
    @param nb Number of board layers.
    @param want_barrel True to return also the barrel-only couplings and the vias of every node (what the micro peak of the zone model reads); False (default) is the
           function of release 2.4.5, bit for bit.
    @return Dict {(l, m): array (R,)} of conductances in W/K between the sheets l < m of every ring; the adjacent pairs carry the dielectric plus the reduced barrel.
            With want_barrel the tuple (gz, via_gz, seen): via_gz has the same keys and holds the reduced barrels only (no dielectric), seen is a list of dicts
            {node, n, r_cell, a} (vias of a group in a node, Wigner-Seitz radius of their cell in m, target radius in m).
    """
    gz = {(l, l + 1): gz_diel[l].astype(float).copy() for l in range(nb - 1)}
    via_gz, seen = {}, []
    nv = len(vs)
    if nv == 0 or nb < 2:
        return (gz, via_gz, seen) if want_barrel else gz
    cell = net.dx * net.dy
    ring_of = np.array([int(idx[cell_index_of_point(vs.x[i], vs.y[i], net.nx, net.ny, net.dx, net.dy)]) for i in range(nv)])
    n_ring = np.bincount(ring_of, minlength=n_rings)             # vias in every ring
    for g in np.unique(vs.group):
        members = np.flatnonzero(vs.group == g)
        n_g = len(members)
        rings_g = np.unique(ring_of[members])
        a_touched = float(sum(cnt[k] * cell for k in rings_g))   # area of the rings that the group touches
        r_cell_g = float(np.mean(vs.d_nn[members])) / math.sqrt(math.pi)     # Wigner-Seitz radius from the spacing of the group (inf for a lone via)
        r_macro = math.sqrt(a_touched / math.pi)
        for k in rings_g:
            mem = members[ring_of[members] == k]
            n = len(mem)
            a = ETA * float(np.mean(vs.r_via[mem]))
            r_ring = math.sqrt(cnt[k] * cell / (math.pi * n_ring[k]))        # Wigner-Seitz radius from the ring: its area per via
            r_cell = min(r_ring, r_cell_g)
            r_cl = math.sqrt(n_g) * r_cell                        # radius of the disc that the group covers
            g_gap = vs.g_gap[mem].sum(axis=0) / n                 # barrel conductance per via and gap
            g_well = np.full(nb, np.inf)
            area_k = cnt[k] * cell
            for l in range(nb):
                s_l = s_ring[l, k]
                if s_l <= 0:
                    g_well[l] = 0.0
                    continue
                # Loss of the sheet per area: the faces plus the dielectric couplings to the neighbours; its fin length caps the cluster
                loss = (g_top[l, k] + g_bot[l, k]) / area_k
                for m in (l - 1, l + 1):
                    if 0 <= m < nb:
                        loss += gz_diel[min(l, m), k] / area_k
                rc = krogh(s_l, r_cell, a)
                if n_g > 1:
                    rm = min(r_macro, MACRO_CAP * math.sqrt(s_l / loss)) if loss > 0 else r_macro
                    if rm > r_cl:
                        rc += n_g * krogh(s_l, rm, r_cl)          # the group as one disc: its n_g vias in parallel share the resistance
                g_well[l] = math.inf if rc <= 0 else 1.0 / rc
            reduced = viawell.kron_barrel(g_gap, g_well) * n      # the n vias of this group in this ring in parallel
            for l in range(nb):
                for m in range(l + 1, nb):
                    if reduced[l, m] != 0.0:
                        if (l, m) not in gz:
                            gz[(l, m)] = np.zeros(n_rings)
                        gz[(l, m)][k] += reduced[l, m]
                        if want_barrel:
                            if (l, m) not in via_gz:
                                via_gz[(l, m)] = np.zeros(n_rings)
                            via_gz[(l, m)][k] += reduced[l, m]
            if want_barrel:
                seen.append({"node": int(k), "n": n, "r_cell": r_cell, "a": a})
    return (gz, via_gz, seen) if want_barrel else gz


# ------------------------------------------------------------------------------------------------ Analytic tiles

def median_nn(vs):
    """!
    @brief Median nearest-neighbour distance of the vias.
    @param vs ViaSet.
    @return float in m (infinite for fewer than two vias).
    """
    d = vs.d_nn[np.isfinite(vs.d_nn)]
    return float(np.median(d)) if len(d) else math.inf


def tile_size(vs, width, height):
    """!
    @brief Tile of the Analytic via correction before the cap at the program's tile: min(1 mm, 0.75 d_nn), floor 0.25 mm, coarsened above 1200 active tiles.
    @param vs ViaSet.
    @param width Board width in m.
    @param height Board height in m.
    @return Tuple (rule, final) of the tile in m by the rule and after the coarsening (equal unless more than MAX_ACTIVE_TILES tiles could hold a via).
    """
    t = max(min(TILE_CAP, TILE_NN * median_nn(vs)), TILE_FLOOR)
    # The dense system has (active tiles x layers)^2 entries: with many vias the tile grows so that at most MAX_ACTIVE_TILES can hold a via
    est = min(4 * len(vs), (width / t) * (height / t))
    return t, (t * math.sqrt(est / MAX_ACTIVE_TILES) if est > MAX_ACTIVE_TILES else t)


def _grid_for(width, height, t, grid):
    """!
    @brief Tile grid of tile size t, or the program's grid when t is not smaller than its tile.
    @param width Board width in m.
    @param height Board height in m.
    @param t Wanted tile in m.
    @param grid The program's tile grid (ntx, nty, tw, th).
    @return Tuple (ntx, nty, tw, th).
    """
    if t >= min(grid[2], grid[3]):
        return grid
    ntx, nty = max(int(np.ceil(width / t - 1e-9)), 1), max(int(np.ceil(height / t - 1e-9)), 1)
    return ntx, nty, width / ntx, height / nty


def tile_grid(vs, width, height, grid):
    """!
    @brief Tile grid of the Analytic via correction (see `tile_size`), never coarser than the program's tile.
    @param vs ViaSet.
    @param width Board width in m.
    @param height Board height in m.
    @param grid The program's tile grid (ntx, nty, tw, th) from analytic._tile_grid (returned unchanged when the rule does not refine it).
    @return Tuple (ntx, nty, tw, th) of the tile counts and sizes.
    """
    return _grid_for(width, height, tile_size(vs, width, height)[1], grid)


def heatsink_tiles(problem, g):
    """!
    @brief Tiles that the heatsinks and metal blocks make active in the Analytic correction on a tile grid (the same system as the vias).
    @details A plain heatsink is active where it covers a tile and has a coefficient (`analytic.solve_steady`, g_heatsink > 0); a metal block on every tile it covers
             (`analytic._block_tiles`, cover > 0). Both share the dense system with the vias, so the guard of `plan` must count them: a 60 x 50 mm block at the 1 mm via
             tile is 3000 tiles, 12000 unknowns on four layers (the example board with a block took 25 s and 5 GB instead of 0.2 s and 130 MB).
    @param problem The Problem.
    @param g Tile grid (ntx, nty, tw, th).
    @return set of (row, col).
    """
    out = set()
    for s in problem.heatsinks:
        if not (s.is_block() or s.h_extra > 0):
            continue
        cov = coverage_fraction(s.polygon, g[0], g[1], g[2], g[3], 8)
        out.update((int(r), int(c)) for r, c in np.argwhere(cov > 0))
    return out


def plan(problem, vs, grid, n_layers):
    """!
    @brief Tile grid and via weights of the Analytic correction, with the dense system kept under MAX_UNKNOWNS.
    @details The tile of `tile_size` is used first. The estimate behind its coarsening (min(4 n, tiles)) does not count the tiles that the bilinear spread really touches, which
             for scattered lone vias is several times more (500 vias on 100 x 80 mm: 2000 tiles, 8000 unknowns, 1.4 GB and 6 s against 0.2 s and 160 MB before the correction),
             nor the tiles of the heatsinks and metal blocks, which the finer tile multiplies (`heatsink_tiles`); the tile is then enlarged until all the active tiles
             times the layers are at most MAX_UNKNOWNS. This guard is not part of the tested rule: it acts only beyond it.
    @param problem The Problem (for the footprints and the heatsinks).
    @param vs ViaSet.
    @param grid The program's tile grid (ntx, nty, tw, th).
    @param n_layers Number of board layers.
    @return Dict with grid (ntx, nty, tw, th), weights (list per via of {(row, col): weight}), active (tiles of the system: those that hold a via or a heatsink), t_rule and
            t_final (m, before and after the guard).
    """
    width, height = grid[0] * grid[2], grid[1] * grid[3]
    d_heater = heater_distance(problem, vs)
    t_rule, t = tile_size(vs, width, height)
    for _ in range(40):
        g = _grid_for(width, height, t, grid)
        weights = tile_weights(vs, d_heater, g[2], g[3], g[0], g[1])
        # Every tile of the dense system counts: the via tiles and those of the heatsinks and blocks on the same grid
        active = len({key for wd in weights for key in wd} | heatsink_tiles(problem, g))
        if active * n_layers <= MAX_UNKNOWNS or g == grid:
            break
        t = min(g[2], g[3]) * max(math.sqrt(active * n_layers / MAX_UNKNOWNS) * 1.01, 1.03)       # the count falls slower than 1 / t^2 once saturated
    return {"grid": g, "weights": weights, "active": active, "t_rule": t_rule, "t_final": min(g[2], g[3])}


def heater_distance(problem, vs):
    """!
    @brief Distance of every via to the nearest heater footprint (0 inside it).
    @param problem The Problem.
    @param vs ViaSet.
    @return numpy.ndarray (n,) in m (infinite without heaters).
    """
    out = np.full(len(vs), np.inf)
    for h in problem.heaters:
        poly = np.asarray(h.polygon, dtype=float)
        # Only the vias that this footprint can bring closer are measured: the distance to the bounding box of the footprint is a lower bound of the
        # distance to the footprint, so a via whose bound is not below its distance so far keeps it (min() would not change it). Exact, and with
        # hundreds of parts most vias are skipped after the first parts (500 parts and 8000 vias: 0.30 s to 0.05 s in the live check). The bound is
        # lowered by a relative 1e-9 and 1 pm so that the rounding of the projection below (a + t e can land an ulp outside the box) never skips a via
        bx = np.maximum(np.maximum(poly[:, 0].min() - vs.x, vs.x - poly[:, 0].max()), 0.0)
        by = np.maximum(np.maximum(poly[:, 1].min() - vs.y, vs.y - poly[:, 1].max()), 0.0)
        cand = np.flatnonzero(np.hypot(bx, by) * (1.0 - 1e-9) - 1e-12 < out)
        if cand.size == 0:
            continue
        inside = points_in_polygon(vs.x[cand], vs.y[cand], poly)
        out[cand[inside]] = 0.0
        a, c = poly, np.roll(poly, -1, axis=0)
        e = c - a
        len2 = np.maximum((e ** 2).sum(axis=1), 1e-300)
        idx = cand[~inside]
        # Vectorised over the vias in blocks (a loop over the vias took 1.2 s for 8500 vias and 20 parts, and the input checks run it live at every edit);
        # the same elementwise operations in the same order as the per-via loop, so the distances are bit-identical
        for s in range(0, idx.size, 4096):
            i = idx[s:s + 4096]
            px, py = vs.x[i][:, None], vs.y[i][:, None]
            # Distance to every edge of the polygon (projection clamped to the segment), the smallest one
            t = np.clip(((px - a[:, 0]) * e[:, 0] + (py - a[:, 1]) * e[:, 1]) / len2, 0.0, 1.0)
            out[i] = np.minimum(out[i], np.hypot(px - (a[:, 0] + t * e[:, 0]), py - (a[:, 1] + t * e[:, 1])).min(axis=1))
    return out


def spread_weights(x, y, tw, th, ntx, nty, d_nn, d_heater):
    """!
    @brief Weights of a via on the tiles: all on the tile of its centre, or bilinear between the centres of the four nearest tiles.
    @details Only a via that is alone at the scale of a tile is spread (the vias of a cluster stay on their tile, their positions average out), and one outside the footprints but
             closer than half a tile to one is not (its tiles would reach under the source). Spreading keeps the first moment of the sink, its position.
    @param x X of the via in m.
    @param y Y of the via in m.
    @param tw Tile width in m.
    @param th Tile height in m.
    @param ntx Tiles along x.
    @param nty Tiles along y.
    @param d_nn Nearest-neighbour distance of the via in m.
    @param d_heater Distance of the via to the nearest footprint in m (0 inside).
    @return dict {(row, col): weight} adding to 1.
    """
    c0 = min(max(int(x // tw), 0), ntx - 1)
    r0 = min(max(int(y // th), 0), nty - 1)
    size = math.sqrt(tw * th)
    if d_nn < ISOLATION * size or 0.0 < d_heater < GUARD * size:
        return {(r0, c0): 1.0}
    fx, fy = x / tw - 0.5, y / th - 0.5
    cl, rl = math.floor(fx), math.floor(fy)
    tx, ty = fx - cl, fy - rl
    out = {}
    for dr, wy in ((0, 1 - ty), (1, ty)):
        for dc, wx in ((0, 1 - tx), (1, tx)):
            r = min(max(rl + dr, 0), nty - 1)                     # outside the board the weight goes to the nearest tile
            c = min(max(cl + dc, 0), ntx - 1)
            out[(r, c)] = out.get((r, c), 0.0) + wx * wy
    return {k: w for k, w in out.items() if w > 1e-12}


def tile_weights(vs, d_heater, tw, th, ntx, nty):
    """!
    @brief Weights of every via on the tiles.
    @param vs ViaSet.
    @param d_heater Distance of every via to the nearest footprint in m.
    @param tw Tile width in m.
    @param th Tile height in m.
    @param ntx Tiles along x.
    @param nty Tiles along y.
    @return List (one per via) of dicts {(row, col): weight}.
    """
    return [spread_weights(vs.x[i], vs.y[i], tw, th, ntx, nty, vs.d_nn[i], d_heater[i]) for i in range(len(vs))]


def add_self_terms(g_mat, active, weights, vs, tw, th, s_layers):
    """!
    @brief Add the self-terms of the vias to the tile response matrix, so that the vias see the wall temperature instead of the tile mean.
    @param g_mat (Nt L, Nt L) response of the tile means to the heat injected in the tiles (K/W); ordering tile-major, layer-minor. Modified in place.
    @param active (Nt, 2) array of (row, col) of the tiles of the system.
    @param weights Result of `tile_weights`.
    @param vs ViaSet.
    @param tw Tile width in m.
    @param th Tile height in m.
    @param s_layers (L,) sheet conductance of the layers in W/K.
    @return numpy.ndarray g_mat itself, with the diagonal terms added in place (a copy of a matrix of several thousand unknowns costs hundreds of MB).
    """
    pos = {(int(r), int(c)): i for i, (r, c) in enumerate(active)}
    n_layers = len(s_layers)
    n_eff, r_sum, d_sum = {}, {}, {}
    # Effective number of vias of every tile, the weighted sum of their radii and of their nearest-neighbour distances
    for i, wd in enumerate(weights):
        for key, w in wd.items():
            n_eff[key] = n_eff.get(key, 0.0) + w
            r_sum[key] = r_sum.get(key, 0.0) + w * vs.r_via[i]
            d_sum[key] = d_sum.get(key, 0.0) + w * vs.d_nn[i]
    area = tw * th
    r_tile = math.sqrt(area / math.pi)
    out = g_mat
    for key, n in n_eff.items():
        if key not in pos:
            continue
        a = ETA * r_sum[key] / n
        for l in range(n_layers):
            s = s_layers[l]
            if s <= 0:
                continue
            if n <= 1.0:
                # A (fraction of a) via: a point sink read against the response of the block of tiles over which it is spread
                r_blk = r_tile / math.sqrt(n)
                rc = max(math.log(r_blk / a) - 0.25, 0.0) / (2.0 * math.pi * s) / n if r_blk > a else 0.0
            else:
                r_c = min(r_tile / math.sqrt(n), (d_sum[key] / n) / math.sqrt(math.pi))
                r_cl = math.sqrt(n) * r_c
                rc = (math.log(r_tile / r_cl) / (2.0 * math.pi * s) if r_tile > r_cl else 0.0) + krogh(s, r_c, a) / n
            i = pos[key] * n_layers + l
            out[i, i] += rc
    return out
