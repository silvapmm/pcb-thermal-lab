#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file viavariants.py
@brief Candidate corrections of the via footprint weights for a plane whose copper covers only part of the footprint: a COPY of the logic of pcbthermal/viawell.py, installed in memory.
@details The program (`pcbthermal/viawell.py`) gives a via on every plane the same geometric footprint weights w_a (the disc of the drill on the cells of the board, enlarged
         until the lattice effective radius is 0.78 r_via) and couples the plane MEAN temperature sum_a w_a T_a to the barrel through a Peaceman well. On a plane whose copper
         covers only part of the footprint the weights sit on cells that cannot supply the heat, and the matrix (positive off-diagonal entries inside the footprint) loses the
         maximum principle: a cold spot. The variants here change only the weights and the form of the coupling; the barrel, the wells and everything else are the program's.
         * `current`  the program's `viawell.build` (reference).
         * `sheet` (a)    per-layer weights w^l_a proportional to w_a times the sheet conductance of the cell in that layer (renormalised); the footprint is enlarged until the
                          effective radius of the WEIGHTED distribution reaches the target; the well uses the weighted mean sheet conductance; mean-potential coupling.
         * `plane` (b)    the same footprint as the program but a cell takes part in a layer only if its sheet conductance is at least 20 % of the largest of the layer
                          (copper present); a layer without such a cell is not coupled to the barrel (antipad); mean-potential coupling.
         * `star` (c)     the weights of `sheet`, but the barrel is an equipotential per layer reached by a conductance g_a = c w_a to every cell (a star), the barrel nodes are
                          eliminated; every off-diagonal entry is then non-positive (the Schur complement of a resistor network is an M-matrix); c is calibrated per layer on the
                          lattice so that the resistance of a lone via in a uniform sheet is the same as the program's, ln(R / r_t) / (2 pi S).
         * `sheet_only_partial`, `star_only_partial`  as `sheet` and `star` but they hand the footprints whose sheet conductance is uniform to the program's own code (bit-identical there).
         The blocks are objects that unpack like the program's 4-tuple (rows, cols, w, G) and carry the dense coupling matrix `M` over the flat list of (layer, cell) pairs.
@note `patched(variant)` replaces `viawell.build`, `matrix_entries` and `unknown_blocks` of the program in memory and restores them on exit; no file of the program is edited.
"""

import contextlib
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np                                                            # noqa: E402
from scipy.optimize import brentq                                             # noqa: E402

from pcbthermal import viawell as vw                                          # noqa: E402
from pcbthermal.geometry import cell_index_of_point                           # noqa: E402

COPPER_PRESENT = 0.2                  # (b): a cell has copper in a layer when its sheet conductance is at least this share of the largest of the layer


class Block:
    """!
    @brief One via: unpacks like the program's 4-tuple and carries a dense coupling over (layer, cell) pairs.
    """

    def __init__(self, rows, cols, w, G, layer_cells, M):
        """!
        @param rows Row indices of the union of the cells (integer array).
        @param cols Column indices of the union of the cells (integer array).
        @param w Weights on the union (informative).
        @param G Layer-to-layer conductances (informative).
        @param layer_cells List over layers of arrays (n_l, 2) of the (row, col) cells coupled in that layer.
        @param M Dense symmetric matrix over the concatenated (layer, cell) pairs, W/K, zero row sums.
        """
        self.rows, self.cols, self.w, self.G, self.layer_cells, self.M = rows, cols, w, G, layer_cells, M

    def __iter__(self):
        """!
        @brief Unpack as (rows, cols, w, G).
        @return iterator.
        """
        return iter((self.rows, self.cols, self.w, self.G))


def dense_from_mean(layer_w, G):
    """!
    @brief Dense matrix of the mean-potential coupling, sum over layer pairs of G[l, m] u u^T with u = e_l (x) w^l - e_m (x) w^m.
    @param layer_w List over layers of weight vectors (possibly empty).
    @param G Array (L, L) of layer-to-layer conductances in W/K.
    @return numpy.ndarray (n, n) over the concatenated cells.
    """
    sizes = [len(x) for x in layer_w]
    off = np.concatenate([[0], np.cumsum(sizes)])
    n = int(off[-1])
    M = np.zeros((n, n))
    for l in range(len(layer_w)):
        for m in range(l + 1, len(layer_w)):
            g = G[l, m]
            if g <= 0 or sizes[l] == 0 or sizes[m] == 0:
                continue
            u = np.zeros(n)
            u[off[l]:off[l + 1]] = layer_w[l]
            u[off[m]:off[m + 1]] = -layer_w[m]
            M += g * np.outer(u, u)
    return M


def lattice_c_matrix(cells, s_bar):
    """!
    @brief C[a, b] = (A(a - b) - kappa) / (4 S): the lattice potential of a unit flux at b at cell a, relative to the far-field logarithm (see the module note).
    @param cells Array (n, 2) of (row, col) indices.
    @param s_bar Sheet conductance in W/K.
    @return numpy.ndarray (n, n).
    """
    d = cells[:, None, :] - cells[None, :, :]
    return (vw.lattice_kernel(d[..., 0], d[..., 1]) - vw.KAPPA) / (4.0 * s_bar)


def star_scale(cells, w, s_bar, h, r_t):
    """!
    @brief Total conductance of the star (g_a = c w_a) so that a lone via in a uniform sheet has the resistance ln(R / r_t) / (2 pi S) of the program.
    @details With unit flux f_a into the star cells, f_a / (c w_a) - sum_b C_ab f_b = D = ln(h / r_t) / (2 pi S) for every a, and sum f = 1; the far-field logarithm cancels.
             The left side decreases with c, so the root is found by bisection on log c; when D is below the value at c = infinity (the footprint alone is already
             resistive enough) the star gets an effectively infinite conductance.
    @param cells Array (n, 2) of cell indices.
    @param w Weights (sum 1).
    @param s_bar Weighted mean sheet conductance in W/K.
    @param h Lattice spacing in m.
    @param r_t Target radius in m.
    @return float c in W/K (total conductance of the star).
    """
    n = len(w)
    D = math.log(h / r_t) / (2.0 * math.pi * s_bar)
    C = lattice_c_matrix(cells, s_bar)

    def delta(c):
        A = np.zeros((n + 1, n + 1))
        A[:n, :n] = np.diag(1.0 / (c * w)) - C
        A[:n, n] = -1.0
        A[n, :n] = 1.0
        rhs = np.zeros(n + 1)
        rhs[n] = 1.0
        return np.linalg.solve(A, rhs)[n]

    lo, hi = math.log(1e-3 * s_bar), math.log(1e9 * s_bar)
    if delta(math.exp(hi)) >= D:
        return 1e9 * s_bar                       # even a perfect star is not resistive enough: nearly equipotential
    if delta(math.exp(lo)) <= D:
        return 1e-3 * s_bar
    return math.exp(brentq(lambda x: delta(math.exp(x)) - D, lo, hi, xtol=1e-10))


def _layer_weights(v, dx, dy, origin, oy, cover, rel, mode, r_via):
    """!
    @brief Footprint weights of one layer: the geometric disc, enlarged until the effective radius of the weighted distribution reaches the target.
    @param v The via.
    @param dx Cell size x in m.
    @param dy Cell size y in m.
    @param origin Lower x edge in m.
    @param oy Lower y edge in m.
    @param cover Board share of the cells.
    @param rel Array (ny, nx): relative sheet conductance of the layer (any scale) used as weight factor; zero where the cell does not take part.
    @param mode "sheet" (weights times rel) or "plane" (weights times 1 where rel > 0).
    @param r_via Drill radius in m.
    @return Tuple (weights dict, r_eff, r_t).
    """
    r_t = vw.TARGET_RATIO * r_via
    h = math.sqrt(dx * dy)
    ny, nx = cover.shape

    def make(radius):
        g = vw.restrict_to_board(vw.disc_weights(v.x, v.y, radius, dx, origin, dy, oy), cover)
        out = {k: x * (float(rel[k]) if mode == "sheet" else (1.0 if rel[k] > 0 else 0.0)) for k, x in g.items()}
        out = {k: x for k, x in out.items() if x > 0}
        tot = sum(out.values())
        return {k: x / tot for k, x in out.items()} if tot > 0 else {}

    w = make(r_via)
    if not w:
        return {}, 0.0, r_t
    r_eff = vw.effective_radius(w, h)
    if r_eff >= r_t:
        return w, r_eff, r_t
    limit = max(cover.shape) * max(dx, dy)
    lo, hi = r_via, 2.0 * r_via
    while True:
        wh = make(hi)
        if (wh and vw.effective_radius(wh, h) >= r_t) or hi >= limit:
            break
        lo, hi = hi, 2.0 * hi
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        wm = make(mid)
        if wm and vw.effective_radius(wm, h) < r_t:
            lo = mid
        else:
            hi = mid
    w = make(hi)
    return w, vw.effective_radius(w, h), r_t


def make_build(variant, uniform_to_program=True):
    """!
    @brief The replacement of viawell.build for a variant.
    @param variant "sheet", "plane" or "star".
    @param uniform_to_program True: a via whose geometric footprint has the same sheet conductance on every cell of every layer is built by the program's code.
    @return Function with the signature of viawell.build.
    """
    original = vw.build

    def build(problem, d, S, cover, dx, dy, nx, ny, origin, active=None):
        blocks0, gz_via = original(problem, d, S, cover, dx, dy, nx, ny, origin, active)
        b = problem.board
        k_cu = b.materials.k_copper
        L = len(d) + 1
        oy = origin * dy / dx
        h = math.sqrt(dx * dy)
        blocks = []
        rel_all = [np.where(cover > 0, S[l] / np.where(cover > 0, cover, 1.0), 0.0) for l in range(L)]       # sheet conductance per unit of board
        k = 0
        for v, share in zip(problem.vias, problem.via_board_shares()):
            if share <= 0.0:
                continue
            w0, r_eff0, r_t = vw.footprint(v.x, v.y, v.diameter / 2.0, dx, origin, cover, dy, oy)
            if not w0:
                continue
            prog_block = blocks0[k]                      # the program's block of this via (same order)
            k += 1
            keys0 = list(w0)
            if uniform_to_program and variant != "star":
                uniform = all(np.ptp([rel_all[l][c] for c in keys0]) <= 1e-9 * max(rel_all[l][keys0[0]], 1e-300) for l in range(L))
                if uniform:
                    blocks.append(prog_block)
                    continue
            gv = k_cu * v.thermal_area(b.via_plating, k_cu) / d
            layer_w, layer_cells, g_well, layer_sbar = [], [], [], []
            for l in range(L):
                rel = rel_all[l]
                if variant == "plane":
                    smax = max(float(rel[c]) for c in keys0)
                    # Copper present: the cells of the program's footprint with at least COPPER_PRESENT of the largest sheet conductance of the layer
                    relb = np.where(rel >= COPPER_PRESENT * float(rel.max()), 1.0, 0.0)
                    w, r_eff, _ = _layer_weights(v, dx, dy, origin, oy, cover, relb, "plane", v.diameter / 2.0)
                    # a plane keeps the program's footprint when it has copper under the whole footprint
                    if w and all(relb[c] > 0 for c in w0):
                        w, r_eff = dict(w0), r_eff0
                else:
                    w, r_eff, _ = _layer_weights(v, dx, dy, origin, oy, cover, rel, "sheet", v.diameter / 2.0)
                if not w:
                    layer_w.append(np.zeros(0))
                    layer_cells.append(np.zeros((0, 2), dtype=int))
                    g_well.append(0.0)
                    layer_sbar.append(0.0)
                    continue
                cells = np.array(list(w), dtype=int)
                wv = np.array([w[c] for c in w])
                sbar = float(sum(w[c] * rel[c] for c in w))
                layer_w.append(wv)
                layer_cells.append(cells)
                layer_sbar.append(sbar)
                g_well.append(vw.well_conductance(sbar, r_eff, r_t) if sbar > 0 else 0.0)
            G = vw.kron_barrel(gv, g_well)
            if variant in ("sheet", "plane"):
                M = dense_from_mean(layer_w, G)
            else:
                # Star: every cell reaches an equipotential barrel node of its layer through g_a = c w_a; the barrel nodes are eliminated
                sizes = [len(x) for x in layer_w]
                off = np.concatenate([[0], np.cumsum(sizes)])
                n = int(off[-1])
                nb = L
                Y = np.zeros((n + nb, n + nb))
                for l in range(L):
                    if sizes[l] == 0:
                        continue
                    c = star_scale(layer_cells[l], layer_w[l], layer_sbar[l], h, r_t)
                    g = c * layer_w[l]
                    ids = np.arange(off[l], off[l + 1])
                    Y[ids, ids] += g
                    Y[n + l, n + l] += g.sum()
                    Y[ids, n + l] -= g
                    Y[n + l, ids] -= g
                for j in range(L - 1):
                    Y[n + j, n + j] += gv[j]
                    Y[n + j + 1, n + j + 1] += gv[j]
                    Y[n + j, n + j + 1] -= gv[j]
                    Y[n + j + 1, n + j] -= gv[j]
                Ycc, Ycb, Ybb = Y[:n, :n], Y[:n, n:], Y[n:, n:]
                M = Ycc - Ycb @ np.linalg.solve(Ybb + 1e-300 * np.eye(nb), Ycb.T)
            allc = {}
            for l in range(L):
                for c in map(tuple, layer_cells[l]):
                    allc[c] = 1
            keys = list(allc)
            blocks.append(Block(np.array([c[0] for c in keys]), np.array([c[1] for c in keys]), np.ones(len(keys)) / len(keys), G, layer_cells, M))
        return blocks, gz_via

    return build


def matrix_entries(blocks, idx):
    """!
    @brief COO entries of the via couplings for program blocks and dense blocks alike.
    @param blocks List from build.
    @param idx Index array (layers, ny, nx) of the unknowns.
    @return Tuple (rows, cols, vals) of lists of arrays.
    """
    rows, cols, vals = [], [], []
    program = []
    for bl in blocks:
        if isinstance(bl, Block):
            flat = np.concatenate([idx[l][c[:, 0], c[:, 1]] if len(c) else np.zeros(0, dtype=int) for l, c in enumerate(bl.layer_cells)])
            n = len(flat)
            rows.append(np.repeat(flat, n))
            cols.append(np.tile(flat, n))
            vals.append(bl.M.ravel())
        else:
            program.append(bl)
    r2, c2, v2 = _ORIG["matrix_entries"](program, idx)
    return rows + r2, cols + c2, vals + v2


def unknown_blocks(blocks, idx, n_layers):
    """!
    @brief Flat unknown indices of the footprints, vias that share a cell merged (the blocks of the block SOR).
    @param blocks List from build.
    @param idx Index array (layers, ny, nx).
    @param n_layers Number of board layers.
    @return List of sorted integer arrays.
    """
    merged = []
    for bl in blocks:
        s = set()
        if isinstance(bl, Block):
            for l, c in enumerate(bl.layer_cells):
                if len(c):
                    s |= set(idx[l][c[:, 0], c[:, 1]].tolist())
        else:
            s = set(idx[:n_layers, bl[0], bl[1]].ravel().tolist())
        for other in [m for m in merged if m & s]:
            s |= other
            merged.remove(other)
        merged.append(s)
    return [np.array(sorted(s)) for s in merged]


_ORIG = {"build": vw.build, "matrix_entries": vw.matrix_entries, "unknown_blocks": vw.unknown_blocks}


@contextlib.contextmanager
def patched(variant):
    """!
    @brief Install a variant in memory for the duration of a with-block.
    @param variant "current", "sheet", "plane" or "star".
    @return context manager.
    """
    if variant == "current":
        yield
        return
    vw.build = make_build(variant)
    vw.matrix_entries = matrix_entries
    vw.unknown_blocks = unknown_blocks
    try:
        yield
    finally:
        vw.build, vw.matrix_entries, vw.unknown_blocks = _ORIG["build"], _ORIG["matrix_entries"], _ORIG["unknown_blocks"]
