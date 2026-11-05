#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file tilerule.py
@brief Study S4: the tile of the Analytic via correction as a rule, and the number of modes of the tile Green function, installed on an in-memory copy of the program's `analytic.solve_steady`.
@details `research/lumped-analytic-vias/lib/analytic_patch.py` (read only, imported) adds the self-term of the tile Green function and the bilinear spread of the barrel conductance, and
         lets the tile be refined to a fixed size (`tile_cap`) or to a multiple of the median nearest-neighbour distance (`tile_k`). The tile is the only constant that its review found
         to matter (1 mm good, 1.5 mm up to -40 %, 2 mm +21 %) and the program builds the Green function G of the tile means from `min(M, 64)` cosine modes whatever M is, so the
         number of modes was never tested. This module adds, on top of that patch:
         * a TILE RULE: a function (problem, W, H, lam, t_program) -> t in metres, chosen from `RULES` (fixed size, multiple of the nearest-neighbour distance, multiple of the via radius,
           and combinations), with the cap at `t_program`, a floor, and the coarsening that keeps the active tiles below `max_active`;
         * a MODE RULE: Mg = min(M, max(64, ceil(c W / t))) modes in x (and Ny in y), c = 0 for the program's 64;
         * `cost(problem, rule)`: the tiles, the unknowns of the dense system (active tiles x layers) and the Gauss-Seidel-free estimate of its memory and flops.
         The program is never edited: `patched()` compiles a copy of the source and puts it in place for the duration of the context.
"""

import contextlib
import inspect
import math
import os
import sys
import textwrap

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(RESEARCH)
for p in (ROOT, os.path.join(RESEARCH, "lumped-analytic-vias", "lib"), os.path.join(RESEARCH, "point-via-convergence", "lib")):
    if p not in sys.path:
        sys.path.insert(0, p)

import analytic_patch as ap                                                  # noqa: E402
import constriction as cr                                                    # noqa: E402

RULE = {"kind": "program", "t_mm": 1.0, "k_nn": 0.75, "m_rad": 8.0, "floor_mm": 0.25, "cap_mm": 1.0, "modes_c": 0.0, "max_active": 1200}
_MODE_LINE = "Mg, Ng = min(M, 64), min(N, 64)"


def nn_median(problem):
    """!
    @brief Median nearest-neighbour distance of the vias in metres (inf for fewer than two vias).
    @param problem The Problem.
    @return float.
    """
    d = np.array([ap._nn_distances(problem)[ap.vkey(v)] for v in problem.vias])
    d = d[np.isfinite(d)]
    return float(np.median(d)) if len(d) else float("inf")


def via_target_radius(problem):
    """!
    @brief Target radius a = eta r_v of the (first) via in metres, the radius the self-term works with.
    @param problem The Problem.
    @return float.
    """
    return cr.ETA * float(problem.vias[0].diameter) / 2.0


def tile_by_rule(problem, W, H, t_program, rule=None):
    """!
    @brief The tile in metres that the rule gives for a problem.
    @details kinds: "program" (the program's tile, no refinement), "fixed" (t_mm), "nn" (k_nn times the median nearest-neighbour distance), "radius" (m_rad times the target radius a),
             "nn_radius" (the smaller of the two), "cap_nn" (the smaller of cap_mm and k_nn times the distance: the tile of the reviewed proposal when cap_mm = 1 and k_nn is large).
             The result is capped at the program's tile, floored at floor_mm, and coarsened so that the number of tiles that can hold a via stays below max_active.
    @param problem The Problem.
    @param W Board width in m.
    @param H Board height in m.
    @param t_program The program's tile in m (the smaller side).
    @param rule Dict of the rule (default: RULE).
    @return float Tile in m.
    """
    r = RULE if rule is None else rule
    if not problem.vias or r["kind"] == "program":
        return t_program
    a = via_target_radius(problem)
    dn = nn_median(problem)
    k = r["kind"]
    if k == "fixed":
        t = r["t_mm"] * 1e-3
    elif k == "nn":
        t = r["k_nn"] * dn
    elif k == "radius":
        t = r["m_rad"] * a
    elif k == "nn_radius":
        t = min(r["k_nn"] * dn, r["m_rad"] * a)
    elif k == "cap_nn":
        t = min(r["cap_mm"] * 1e-3, r["k_nn"] * dn)
    else:
        raise ValueError("unknown rule " + k)
    t = max(min(t, t_program), r["floor_mm"] * 1e-3)
    # The dense system has (active tiles x layers)^2 entries: coarsen when too many tiles could hold a via
    est = min(4 * len(problem.vias), (W / t) * (H / t))
    if est > r["max_active"]:
        t *= math.sqrt(est / r["max_active"])
    return min(t, t_program)


def _grid_rule(W, H, lam, problem):
    """!
    @brief Tile grid hook with the same signature as the program's `_tile_grid` plus the problem.
    @param W Board width in m.
    @param H Board height in m.
    @param lam Fin length in m.
    @param problem The Problem.
    @return Tuple (ntx, nty, tw, th).
    """
    from pcbthermal import analytic
    ntx, nty, tw, th = analytic._tile_grid_program(W, H, lam)
    t = tile_by_rule(problem, W, H, min(tw, th))
    if t >= min(tw, th):
        return ntx, nty, tw, th
    ntx, nty = max(int(np.ceil(W / t - 1e-9)), 1), max(int(np.ceil(H / t - 1e-9)), 1)
    return ntx, nty, W / ntx, H / nty


def _g_modes(M, N, W, H, tw, th):
    """!
    @brief Number of cosine modes of the tile Green function G in x and y (hook for the line `Mg, Ng = min(M, 64), min(N, 64)`).
    @param M Modes of the series along x.
    @param N Modes along y.
    @param W Board width in m.
    @param H Board height in m.
    @param tw Tile width in m.
    @param th Tile height in m.
    @return Tuple (Mg, Ng).
    """
    c = RULE["modes_c"]
    if c <= 0:
        return min(M, 64), min(N, 64)
    return min(M, max(64, int(math.ceil(c * W / tw)))), min(N, max(64, int(math.ceil(c * H / th))))


def modes_needed(W, H, t, c=2.0):
    """!
    @brief The modes the rule asks for on a board and a tile.
    @param W Board width in m.
    @param H Board height in m.
    @param t Tile in m.
    @param c Modes per tile pair (2 = resolve one wavelength per two tiles).
    @return Tuple (Mg, Ng) without the cap M.
    """
    return max(64, int(math.ceil(c * W / t))), max(64, int(math.ceil(c * H / t)))


def patch_available():
    """!
    @brief Whether the program's `analytic.solve_steady` still has the lines that `patched` rewrites.
    @details Since `fix/via-constriction` the program holds the tile rule and the via self-term itself, so the prototype patch cannot be installed on it any more (the studies
             of this folder ran on the program before that change).
    @return bool True when every anchor of the old source is found.
    """
    from pcbthermal import analytic
    src = textwrap.dedent(inspect.getsource(analytic.solve_steady))
    return all(needle in src for needle in (ap._ANCHOR, ap._TILE_LINE, ap._VIA_LINE, _MODE_LINE))


@contextlib.contextmanager
def patched(kind="cap_nn", t_mm=1.0, k_nn=0.75, m_rad=8.0, floor_mm=0.25, cap_mm=1.0, modes_c=0.0, max_active=1200, mode="on", eta=cr.ETA, spread="bilinear", iso=0.7, guard=0.5):
    """!
    @brief Install the Analytic steady solution with the self-term, the spread, the tile rule and the mode rule; restore the program's on exit.
    @param kind Tile rule (see `tile_by_rule`).
    @param t_mm Tile of the "fixed" rule in mm.
    @param k_nn Multiple of the nearest-neighbour distance of the "nn", "nn_radius" and "cap_nn" rules.
    @param m_rad Multiple of the target radius of the "radius" and "nn_radius" rules.
    @param floor_mm Smallest tile in mm.
    @param cap_mm Fixed cap of the "cap_nn" rule in mm.
    @param modes_c Modes per tile (0 = the program's 64).
    @param max_active Most active tiles.
    @param mode "off", "on", "krogh" or "log" (the self-term of `analytic_patch`).
    @param eta Target radius over drill radius.
    @param spread "none" or "bilinear".
    @param iso Isolation of a via in tile sizes for the spread.
    @param guard Guard distance of a via outside a heater footprint, in tiles.
    @return Context manager.
    @throws RuntimeError If an anchor of the program's source is not found (the program changed).
    """
    from pcbthermal import analytic
    # The prototype patch rewrites lines of the Analytic that the program no longer has (the tile rule and the via self-term entered it with fix/via-constriction): say so plainly
    if not patch_available():
        raise RuntimeError("the S4 patch cannot be installed: analytic.solve_steady no longer has the lines of the prototype (obsolete since fix/via-constriction; see README, section 'Status of the scripts')")
    orig = analytic.solve_steady
    src0 = textwrap.dedent(inspect.getsource(orig))
    old_rule = dict(RULE)
    with ap.patched(mode, eta=eta, spread=spread, iso=iso, guard=guard):
        k = src0.find(ap._ANCHOR)
        if k < 0:
            raise RuntimeError("anchor of G not found in analytic.solve_steady")
        indent = src0[src0.rfind("\n", 0, k) + 1:k]
        end = src0.find("\n", k) + 1
        src = src0[:end] + indent + "G = _self_terms(G, active, tw, th, S, L, problem)\n" + src0[end:]
        for needle in (ap._TILE_LINE, ap._VIA_LINE, _MODE_LINE):
            if needle not in src:
                raise RuntimeError("line not found in analytic.solve_steady: " + needle)
        src = src.replace(ap._TILE_LINE, "ntx, nty, tw, th = _tile_grid_vias(W, H, lam, problem)", 1)
        src = src.replace(ap._VIA_LINE, "_spread_via(c_via, v, a, bb, tw, th, ntx, nty, m.k_copper * v.thermal_area(b.via_plating, m.k_copper) / d_diel, problem)", 1)
        src = src.replace(_MODE_LINE, "Mg, Ng = _g_modes(M, N, W, H, tw, th)", 1)
        ns = {}
        exec(compile(src, "<patched analytic.solve_steady (tilerule)>", "exec"), analytic.__dict__, ns)
        RULE.update(kind=kind, t_mm=t_mm, k_nn=k_nn, m_rad=m_rad, floor_mm=floor_mm, cap_mm=cap_mm, modes_c=modes_c, max_active=max_active)
        analytic._tile_grid_vias = _grid_rule
        analytic._g_modes = _g_modes
        analytic.solve_steady = ns["solve_steady"]
        try:
            yield
        finally:
            RULE.clear()
            RULE.update(old_rule)
            if hasattr(analytic, "_g_modes"):
                delattr(analytic, "_g_modes")


def cost(problem, rule=None, t_program=5e-3):
    """!
    @brief Size of the dense system of the correction for a problem and a rule: tiles, active tiles (an upper bound), unknowns, memory and the flops of the factorisation and of G.
    @param problem The Problem.
    @param rule Rule dict (default: RULE as set by `patched`).
    @param t_program The program's tile in m (5 mm unless the fin length is below 20 mm).
    @return dict(t_mm, tiles, active, unknowns, mem_mb, flops_solve, flops_G, modes).
    """
    b = problem.board
    W, H, L = b.width, b.height, b.layers
    t = tile_by_rule(problem, W, H, t_program, rule)
    ntx, nty = max(int(np.ceil(W / t - 1e-9)), 1), max(int(np.ceil(H / t - 1e-9)), 1)
    active = min(4 * len(problem.vias), ntx * nty)
    nunk = active * L
    r = RULE if rule is None else rule
    mg, ng = modes_needed(W, H, t, r["modes_c"]) if r["modes_c"] > 0 else (64, 64)
    return {"t_mm": t * 1e3, "tiles": ntx * nty, "active": active, "unknowns": nunk, "mem_mb": 8.0 * nunk * nunk * 3 / 1e6, "flops_solve": (2.0 / 3.0) * nunk ** 3,
            "flops_G": 2.0 * L * L * ng * active * active * mg, "modes": (mg, ng)}
