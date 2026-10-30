#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file analytic_patch.py
@brief In-memory copy of the Analytic steady solution with a self-term of the tile Green function for the vias (the program's `analytic.py` is never edited).
@details In `analytic.solve_steady` the board is cut into tiles of 2.5 to 5 mm, every tile with a via gets the lumped conductance of its vias between the sheets, and the
         small system (I + G C) y = y0 gives the TILE-MEAN temperatures (G = modal response of the tile mean to a unit power injected uniformly in a tile). The via is then
         coupled between tile means: nothing in it knows that the barrel has a radius, and the sink sits uniformly over the tile whatever the position of the via in it.
         The copy changes two things:
         1. (`spread = "bilinear"`) the barrel conductance of a via is shared between the (up to four) tiles whose centres surround it with bilinear weights, which keeps the
            first moment of the sink (its position) instead of moving it to the centre of the tile that holds the via;
         2. right after G is built, a diagonal term D is added to G, so that the temperature the vias see is the one at their wall, y_wall = y_mean + D f. For a tile that
            holds n (possibly fractional) vias of radius a (target radius eta times the drill radius), with the tile radius R = sqrt(A_tile / pi) and the radius of the cell of
            one via r_c = min(R / sqrt(n), nearest-neighbour distance / sqrt(pi)):
              n <= 1: D = [ln(R / (sqrt(n) a)) - 1/4] / (2 pi S n)                 (a point sink read against the response of the tile to its own uniform injection)
              n > 1 : D = [ln(R / r_cl)] / (2 pi S) + Krogh(S, r_c, a) / n,  r_cl = sqrt(n) r_c   (the cluster as one uniform sink of radius r_cl, then the cell of one via).
         Options (`OPTIONS`): `mode` "off" (the program, bit for bit), "on" (the formulas above), "krogh" (D = Krogh(S, R / sqrt(n), a) / n, the first version), "log" (constant `c`);
         `eta`; `spread` "none" or "bilinear".
@note Sheets that are not copper (S = laminate only) get the same formula: their S is the S of the effective sheet of the program.
"""

import contextlib
import inspect
import math
import os
import sys
import textwrap

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import constriction as cr                                                   # noqa: E402

OPTIONS = {"mode": "off", "eta": cr.ETA, "spread": "none", "c": 0.25, "iso": 0.7, "dscale": 1.0, "mscale": 1.0, "tile_k": 0.0, "tile_min": 1.0, "guard": 0.5, "tile_cap": 0.0}
MAX_ACTIVE = 1200                                                           # most tiles of the system that the refinement may create
NN = {}                                                                     # vkey(via) -> nearest-neighbour distance of the problem being solved


def vkey(v):
    """!
    @brief Key of a via in the nearest-neighbour cache: its position (two vias at the same point are the same sink).
    @param v The via.
    @return tuple (x, y) in m.
    """
    return (float(v.x), float(v.y))


def _content_key(problem):
    """!
    @brief Content key of the geometry the cache depends on (via positions and heater footprints).
    @details The first version keyed the cache by id(problem): CPython reuses the id of a freed object, so a new problem could
             meet the cache of an old one (a KeyError in tests/test_stackup.py with the patches installed, found by the review, or
             silently stale distances when the via objects were also reallocated at the same addresses).
    @param problem The Problem.
    @return tuple Hashable key.
    """
    return (tuple(vkey(v) for v in problem.vias), tuple(tuple(map(tuple, h.polygon)) for h in problem.heaters))


def _nn_distances(problem):
    """!
    @brief Nearest-neighbour distance of every via of a problem and its distance to the nearest heater (cached by the content of the problem).
    @param problem The Problem.
    @return dict vkey(via) -> distance in m (inf for a lone via) and ("heater", vkey(via)) -> distance to the nearest footprint in m.
    """
    key = _content_key(problem)
    if NN.get("_for") != key:
        NN.clear()
        NN["_for"] = key
        pts = np.array([(v.x, v.y) for v in problem.vias])
        if len(pts) > 1:
            from scipy.spatial import cKDTree
            d = cKDTree(pts).query(pts, k=2)[0][:, 1]
        else:
            d = np.full(len(pts), np.inf)
        for v, dv in zip(problem.vias, d):
            NN[vkey(v)] = float(dv)
            NN[("heater", vkey(v))] = _heater_distance(problem, v)
    return NN


def _heater_distance(problem, v):
    """!
    @brief Distance of a via to the nearest heater footprint (0 inside it), in m.
    @param problem The Problem.
    @param v The via.
    @return float Distance in m (inf without heaters).
    """
    from pcbthermal.geometry import points_in_polygon
    best = float("inf")
    for h in problem.heaters:
        poly = list(h.polygon)
        if bool(points_in_polygon(np.array([v.x]), np.array([v.y]), poly)[0]):
            return 0.0
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
            dx, dy = x1 - x0, y1 - y0
            t = 0.0 if dx == dy == 0 else min(max(((v.x - x0) * dx + (v.y - y0) * dy) / (dx * dx + dy * dy), 0.0), 1.0)
            best = min(best, math.hypot(v.x - (x0 + t * dx), v.y - (y0 + t * dy)))
    return best


def _weights(v, tw, th, ntx, nty, d_nn=float("inf"), d_heater=0.0):
    """!
    @brief Weights of a via on the tiles.
    @param v The via.
    @param tw Tile width in m.
    @param th Tile height in m.
    @param ntx Tiles along x.
    @param nty Tiles along y.
    @param d_nn Nearest-neighbour distance of the via in m.
    @param d_heater Distance of the via to the nearest heater footprint in m (0 inside).
    @return dict {(row, col): weight}, the weights add to 1: all on the tile of the centre ("none", or a via with a neighbour closer than `iso` tiles) or bilinear between the centres of the four nearest tiles.
    """
    c0 = min(max(int(v.x // tw), 0), ntx - 1)
    r0 = min(max(int(v.y // th), 0), nty - 1)
    # Only a via that is alone at the scale of a tile is spread; the vias of a cluster stay on their tile (their positions average out and the tile formulas for n vias apply)
    size = math.sqrt(tw * th)
    # A via outside the footprints but closer than `guard` tiles to one cannot be spread: its tiles would reach under the source (the mosaic cannot resolve it)
    if OPTIONS["spread"] != "bilinear" or d_nn < OPTIONS["iso"] * size or 0.0 < d_heater < OPTIONS["guard"] * size:
        return {(r0, c0): 1.0}
    fx, fy = v.x / tw - 0.5, v.y / th - 0.5
    cl, rl = math.floor(fx), math.floor(fy)
    tx, ty = fx - cl, fy - rl
    out = {}
    for dr, wy in ((0, 1 - ty), (1, ty)):
        for dc, wx in ((0, 1 - tx), (1, tx)):
            r = min(max(rl + dr, 0), nty - 1)                              # outside the board the weight goes to the nearest tile
            c = min(max(cl + dc, 0), ntx - 1)
            out[(r, c)] = out.get((r, c), 0.0) + wx * wy
    return {k: w for k, w in out.items() if w > 1e-12}


def _spread_via(c_via, v, a, bb, tw, th, ntx, nty, cond, problem):
    """!
    @brief Hook that replaces the line of the program that puts the whole conductance of a via in one tile.
    @param c_via (nty, ntx, L-1) array of the via conductance of every tile and gap, W/K (modified).
    @param v The via.
    @param a Column of the tile of the centre (unused).
    @param bb Row of the tile of the centre (unused).
    @param tw Tile width in m.
    @param th Tile height in m.
    @param ntx Tiles along x.
    @param nty Tiles along y.
    @param cond Conductance of the barrel per gap, array (L-1,) in W/K.
    @param problem The Problem (for the nearest-neighbour distances).
    @return None.
    """
    for (r, c), w in _weights(v, tw, th, ntx, nty, _nn_distances(problem)[vkey(v)], _nn_distances(problem)[("heater", vkey(v))]).items():
        c_via[r, c] += w * cond


def _self_terms(G, active, tw, th, S, L, problem):
    """!
    @brief Add the self-terms of the vias to the tile response matrix.
    @param G (Nt*L, Nt*L) response of the tile means to the heat injected in the tiles (K/W).
    @param active (Nt, 2) array of (row, col) of the tiles of the system.
    @param tw Tile width in m.
    @param th Tile height in m.
    @param S (L,) sheet conductance of the layers in W/K.
    @param L Number of layers.
    @param problem The Problem.
    @return numpy.ndarray G plus the diagonal terms (a new array).
    """
    if OPTIONS["mode"] == "off" or not problem.vias:
        return G
    b = problem.board
    pos = {(int(r), int(c)): i for i, (r, c) in enumerate(active)}
    ntx = int(round(b.width / tw))
    nty = int(round(b.height / th))
    pts = np.array([(v.x, v.y) for v in problem.vias])
    if len(pts) > 1:
        from scipy.spatial import cKDTree
        d_nn = cKDTree(pts).query(pts, k=2)[0][:, 1]
    else:
        d_nn = np.full(len(pts), np.inf)
    # Effective number of vias of every tile, the sum of their weights times radius, and of their nearest-neighbour distances
    n_eff, rsum, dsum = {}, {}, {}
    for iv, v in enumerate(problem.vias):
        for key, w in _weights(v, tw, th, ntx, nty, d_nn[iv], _nn_distances(problem)[("heater", vkey(v))]).items():
            n_eff[key] = n_eff.get(key, 0.0) + w
            rsum[key] = rsum.get(key, 0.0) + w * v.diameter / 2.0
            dsum[key] = dsum.get(key, 0.0) + w * d_nn[iv]
    area = tw * th
    G = G.copy()
    for key, n in n_eff.items():
        if key not in pos:
            continue
        a = OPTIONS["eta"] * rsum[key] / n
        r_tile = math.sqrt(area / math.pi)
        for l in range(L):
            if S[l] <= 0:
                continue
            s = S[l]
            if OPTIONS["mode"] == "krogh":
                rc = cr.krogh(s, math.sqrt(area / (math.pi * n)), a) / n
            elif OPTIONS["mode"] == "log":
                r_cell = math.sqrt(area / (math.pi * n))
                rc = (max(math.log(r_cell / a) - OPTIONS["c"], 0.0) / (2.0 * math.pi * s) if r_cell > a else 0.0) / n
            elif n <= 1.0:
                # A (fraction of a) via: a point sink read against the response of the block of tiles over which it is spread
                r_blk = r_tile / math.sqrt(n)
                rc = max(math.log(r_blk / a) - 0.25, 0.0) / (2.0 * math.pi * s) / n if r_blk > a else 0.0
            else:
                r_c = min(r_tile / math.sqrt(n), (dsum[key] / n) / math.sqrt(math.pi))
                r_cl = math.sqrt(n) * r_c
                rc = OPTIONS["mscale"] * (math.log(r_tile / r_cl) / (2.0 * math.pi * s) if r_tile > r_cl else 0.0) + cr.krogh(s, r_c, a) / n
            i = pos[key] * L + l
            G[i, i] += rc * OPTIONS["dscale"]
    return G


def _tile_grid_vias(W, H, lam, problem):
    """!
    @brief Tile grid of the patched model: the program's rule, refined to `tile_k` times the median nearest-neighbour distance of the vias when that is smaller (never below `tile_min` mm).
    @param W Board width in m.
    @param H Board height in m.
    @param lam Fin length in m.
    @param problem The Problem.
    @return Tuple (ntx, nty, tw, th) as the program's `_tile_grid`.
    """
    from pcbthermal import analytic
    ntx, nty, tw, th = analytic._tile_grid_program(W, H, lam)
    if (OPTIONS["tile_k"] <= 0 and OPTIONS["tile_cap"] <= 0) or not problem.vias:
        return ntx, nty, tw, th
    t = min(tw, th)
    d = np.array(list(_nn_distances(problem)[vkey(v)] for v in problem.vias))
    d = d[np.isfinite(d)]
    if OPTIONS["tile_k"] > 0 and len(d):
        t = min(t, max(OPTIONS["tile_min"] * 1e-3, OPTIONS["tile_k"] * float(np.median(d))))
    if OPTIONS["tile_cap"] > 0:
        t = min(t, max(OPTIONS["tile_cap"], OPTIONS["tile_min"]) * 1e-3)
    # The dense system has (active tiles x layers)^2 entries: with many vias the tiles are coarsened so that at most MAX_ACTIVE are used
    est = min(4 * len(problem.vias), (W / t) * (H / t))
    if est > MAX_ACTIVE:
        t *= math.sqrt(est / MAX_ACTIVE)
    if t >= min(tw, th):
        return ntx, nty, tw, th
    ntx, nty = max(int(np.ceil(W / t - 1e-9)), 1), max(int(np.ceil(H / t - 1e-9)), 1)
    return ntx, nty, W / ntx, H / nty


_TILE_LINE = "ntx, nty, tw, th = _tile_grid(W, H, lam)"
_VIA_LINE = "c_via[bb, a] += m.k_copper * v.thermal_area(b.via_plating, m.k_copper) / d_diel"
_ANCHOR = "G = Gm.reshape(Nt * L, Nt * L)"


def _compile_solver():
    """!
    @brief Compile the copy of `analytic.solve_steady` with the two hooks.
    @return The new function.
    @throws RuntimeError If an anchor is not found (the program changed).
    """
    from pcbthermal import analytic
    src = textwrap.dedent(inspect.getsource(analytic.solve_steady))
    k = src.find(_ANCHOR)
    if k < 0:
        raise RuntimeError("anchor of G not found in analytic.solve_steady")
    indent = src[src.rfind("\n", 0, k) + 1:k]
    end = src.find("\n", k) + 1
    src = src[:end] + indent + "G = _self_terms(G, active, tw, th, S, L, problem)\n" + src[end:]
    if _TILE_LINE not in src:
        raise RuntimeError("tile line not found in analytic.solve_steady")
    src = src.replace(_TILE_LINE, "ntx, nty, tw, th = _tile_grid_vias(W, H, lam, problem)", 1)
    k = src.find(_VIA_LINE)
    if k < 0:
        raise RuntimeError("via line not found in analytic.solve_steady")
    src = src.replace(_VIA_LINE, "_spread_via(c_via, v, a, bb, tw, th, ntx, nty, m.k_copper * v.thermal_area(b.via_plating, m.k_copper) / d_diel, problem)", 1)
    ns = {}
    exec(compile(src, "<patched analytic.solve_steady>", "exec"), analytic.__dict__, ns)
    analytic._self_terms = _self_terms
    analytic._spread_via = _spread_via
    analytic._tile_grid_vias = _tile_grid_vias
    analytic._tile_grid_program = analytic.__dict__.get('_tile_grid_program', analytic._tile_grid)
    return ns["solve_steady"]


@contextlib.contextmanager
def patched(mode="on", eta=cr.ETA, spread="none", c=0.25, iso=0.7, dscale=1.0, mscale=1.0, tile_k=0.0, tile_min=1.0, guard=0.5, tile_cap=0.0):
    """!
    @brief Install the Analytic steady solution with the self-terms of the vias; restore the original on exit.
    @param mode "off", "on", "krogh" or "log".
    @param eta r_t / r_v.
    @param spread "none" (the tile that holds the centre) or "bilinear".
    @param c Constant of the "log" mode.
    @param tile_k Refine the tiles to this many times the median nearest-neighbour distance of the vias (0 keeps the program's tiles).
    @param guard A via outside the heater footprints and closer than this many tiles to one is not spread (0 = always spread).
    @param tile_cap Largest tile in mm in a board with vias (0 = no cap).
    @param tile_min Smallest tile in mm of the refinement.
    @param iso A via is spread only if its nearest neighbour is at least this many tile sizes away.
    @return Context manager.
    """
    from pcbthermal import analytic
    old = analytic.solve_steady
    old_opts = dict(OPTIONS)
    OPTIONS.update(mode=mode, eta=eta, spread=spread, c=c, iso=iso, dscale=dscale, mscale=mscale, tile_k=tile_k, tile_min=tile_min, guard=guard, tile_cap=tile_cap)
    NN.clear()
    try:
        analytic.solve_steady = _compile_solver()
        yield
    finally:
        analytic.solve_steady = old
        OPTIONS.clear()
        OPTIONS.update(old_opts)
        for name in ("_self_terms", "_spread_via", "_tile_grid_vias", "_tile_grid_program"):
            if hasattr(analytic, name):
                delattr(analytic, name)
