#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file laminate.py
@brief The laminate between the copper layers as node layers (FVM and FDM): one rule for every gap and for the laminate under the copper of a one-layer board; the legacy two nodes of a
       one-layer board (Lumped, boards with a metal block) and the series film (Analytic).

@details **The rule** (research/laminate-nodes). A *gap* is the laminate between two copper nodes; for a one-layer board it is the laminate between the copper node and the bottom face
         (so a one-layer board is a board whose bottom layer has no copper and holds the bottom film). A gap of thickness d is cut into n = min(N_MAX, ceil(d / S_MAX)) equal sub-gaps with a
         node at every boundary, **only in the cells where copper is absent next to the gap** (fill below 1 in either layer) **plus a margin** of ceil(d / dx) + 1 cells; in every other cell
         the gap is the single link k_z A / d of the model. In a refined cell:

         * the copper nodes keep the copper and half of their first (last) sub-gap, the n - 1 interior nodes hold (s_j + s_j+1) / 2 of laminate each (lateral conductance k_inplane times
           that, heat capacity rho c times that), consecutive nodes are joined by k_z A / s_j;
         * the vertical path through the gap is lengthened by (1 - f) t_cu / 2 of each adjacent copper layer (the laminate that takes the place of the missing copper), in the first and
           last sub-gap; the same correction applies to the single link of a cell with absent copper outside the mask (a gap too thin to be cut);
         * a cell with copper in both layers is untouched, so **a board with copper in every cell is the model of the earlier versions bit for bit** (except the one-layer board, whose
           laminate was two nodes in every cell and is now one link there).

         Why: where the copper is partly absent the laminate carries the heat sideways across the thickness of the gap, which one node cannot hold; against a resolved 3D solver the error falls
         as 1 / n (1.6 mm window of 6 mm on two layers: -18.4 % with one node, -3.1 % with the rule; one-layer 10 mm pad: -4.1 % with the two nodes of the earlier version, -1.8 %).

         **The face of a part** (face_terms). A part on an outer layer injects its heat at the node, at mid-thickness of the copper layer; where the copper is absent the half layer of laminate
         between the node and the face adds Q t_cu / (2 k_z A). The peak read under a part adds the full term in every cell with absent copper, scaled down for a bare feature narrower than
         SLIVER_THICKNESSES copper thicknesses (the drop over a slot of width w in copper of thickness t is 0.42 of the one-dimensional term at w = t, 0.87 at 2.9 t, 0.98 at 5.7 t); the mean
         under the part adds the term weighted by the bare share of every cell.

         **Limits.** The Analytic and the Lumped have no cells for this (the Lumped keeps the two nodes of a one-layer board of the earlier versions and one link per gap; the Analytic the series film);
         a board with a metal block keeps the treatment of the earlier versions (blocks are not combined with the rule); the simple stack-up of three or more layers gives the outer nodes a
         slab that is not d / 2 of laminate (a separate item). The numbers S_MAX and N_MAX are global constants, not user settings (see parameters()).

         **The legacy one-layer nodes.** Before the rule a one-layer board had LAMINATE_NODES laminate nodes under the copper in every cell: nodes(), extra_layers() and series_bottom_problem()
         below; they are still used by the Lumped, by boards with a metal block and by the Analytic (a series film, because extra nodes made its uniform-sheet estimate of a small pad worse).
"""

import copy
import math
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

S_MAX = 0.4e-3              # Longest sub-gap of the laminate between two nodes in m: n = ceil(d / S_MAX), so gaps of 0.4, 0.8, 1.6, 3.2 mm give 1, 2, 4, 4 sub-gaps
N_MAX = 4                   # Most sub-gaps in one gap (error against the resolved 3D solid falls as 1/n; 4 costs 1.0 to 2.5 times the unknowns, 8 about twice as much again)
SLIVER_THICKNESSES = 4.0    # A bare feature narrower than this many copper thicknesses carries only a share of the face drop (face_terms)
BARE = 1.0 - 1e-12          # A cell has absent copper next to a gap when the fill of either layer is below this

LAMINATE_NODES = 2           # Legacy: laminate nodes under the copper of a one-layer board in every cell (Lumped, boards with a metal block); the rule replaces them in the FVM and FDM


@dataclass
class LaminateNodes:
    """!
    @brief The laminate nodes of a one-layer board.
    """
    count: int               # Number of laminate nodes under the copper
    gap: float               # Thickness of one gap between two nodes (m)
    copper_slab: float       # Thickness represented by the copper node: copper plus half a gap (m)
    slabs: np.ndarray        # Thickness represented by every laminate node, top down (m): g, ..., g, g/2
    k_through: float         # Conductivity of the laminate across its thickness (W/mK)
    k_inplane: float         # Conductivity of the laminate along the plane (W/mK)
    rho_cp: float            # Volumetric heat capacity of the laminate (J/m3K)


def nodes(board, count=None):
    """!
    @brief The laminate nodes of a board, or None when the board does not need them.
    @details Only a one-layer board with a laminate under its copper (simple stack-up: the thickness minus the copper) gets them; boards with two or more
             layers have copper on both faces and keep one node per copper layer.
    @param board A Board.
    @param count Number of laminate nodes (None: LAMINATE_NODES).
    @return LaminateNodes or None.
    """
    count = LAMINATE_NODES if count is None else count
    if board.layers != 1 or count < 1:
        return None
    t_cu = float(np.asarray(board.copper_thickness, dtype=float)[0])
    t_lam = float(board.slab_thicknesses()[0]) - t_cu
    if t_lam <= 0.0:
        return None
    m = board.materials
    g = t_lam / count
    slabs = np.full(count, g)
    slabs[-1] = 0.5 * g                                        # The last node sits on the bottom face and holds half a gap
    return LaminateNodes(count, g, t_cu + 0.5 * g, slabs, m.k_fr4_through, m.k_fr4_inplane, m.rho_fr4 * m.cp_fr4)


def extra_layers(board, lam, area, cover, edge, h_side_cells):
    """!
    @brief The arrays of the laminate node layers of a cell (FVM) or node (FDM) network.
    @param board A Board.
    @param lam LaminateNodes of the board.
    @param area Board area of every cell or node in m2, shape (ny, nx).
    @param cover Board cover of every cell or node (0 to 1), shape (ny, nx).
    @param edge Length of the board edge exposed in every cell or node in m, shape (ny, nx) (zeros without an edge coefficient).
    @param h_side_cells Edge coefficient in W/m2K (0 or None for none).
    @return List of dicts, one per laminate node top down, with S (lateral conductance k t times the cover, W/K), C (J/K), g_link (W/K to the node above),
            g_bottom (W/K to the ambient through the bottom face, last node only) and g_side (W/K through the edge).
    """
    out = []
    hs = h_side_cells or 0.0
    for j, t in enumerate(lam.slabs):
        g_bottom = board.h_bottom * area if j == lam.count - 1 else np.zeros_like(area)
        out.append({"S": lam.k_inplane * t * cover, "C": lam.rho_cp * t * area, "g_link": lam.k_through * area / lam.gap,
                    "g_bottom": g_bottom, "g_side": hs * t * edge})
    return out


def series_bottom_problem(problem):
    """!
    @brief A copy of a one-layer problem whose bottom film is in series with the laminate (the correction of the Analytic model).
    @param problem A Problem.
    @return The same Problem when the board needs no correction, otherwise a copy with h_bottom = 1 / (1/h_bottom + t_lam / k_through).
    """
    lam = nodes(problem.board, 1)
    if lam is None or problem.board.h_bottom <= 0.0:
        return problem
    p = copy.deepcopy(problem)
    t_lam = lam.gap
    p.board.h_bottom = 1.0 / (1.0 / problem.board.h_bottom + t_lam / lam.k_through)
    return p


# ---------------------------------------------------------------------------------------------------------------- the rule
def parameters():
    """!
    @brief The two numbers of the rule: the longest sub-gap and the most sub-gaps.
    @return Tuple (s_max in m, n_max): the constants S_MAX and N_MAX.
    @note They are constants, not Preferences: they are not saved in the project file, so a user setting would make the same project give different numbers on two machines.
          2.5.0 may add them to SolverOptions, which is saved with the run. The function stays as the single place the call sites (and tests) read them from.
    """
    return S_MAX, N_MAX


def uses_rule(problem):
    """!
    @brief Whether the FVM and FDM build the laminate nodes of the rule for a problem: not when a metal block is present (blocks keep the treatment of the earlier versions).
    @param problem A Problem.
    @return True when the rule applies.
    """
    return not any(s.is_block() for s in problem.heatsinks)


def n_for_gap(d, s_max=S_MAX, n_max=N_MAX):
    """!
    @brief Number of sub-gaps of a gap.
    @param d Gap thickness in m.
    @param s_max Longest sub-gap in m.
    @param n_max Most sub-gaps.
    @return int, at least 1.
    """
    return int(min(n_max, max(1, math.ceil(d / s_max - 1e-9))))


def margin_cells(d, dx):
    """!
    @brief Margin around the cells with absent copper that also get the nodes: the laminate carries heat sideways over about its own thickness.
    @param d Gap thickness in m.
    @param dx Cell size in m.
    @return Cells (int).
    """
    return int(math.ceil(d / dx - 1e-9)) + 1


def flag_cells(fill_a, fill_b, d, dx, active):
    """!
    @brief The cells of a gap that get the nodes: absent copper in either layer next to the gap, grown by the margin (Euclidean distance in cells), on the board only.
    @param fill_a Copper fill (ny, nx) of the layer above the gap (0 to 1).
    @param fill_b Copper fill of the layer below, or None for the laminate of a one-layer board (the far side is the bare bottom face).
    @param d Gap thickness in m.
    @param dx Cell size in m.
    @param active Boolean (ny, nx) of the cells on the board.
    @return Boolean array (ny, nx).
    """
    f = fill_a if fill_b is None else np.minimum(fill_a, fill_b)
    bare = f < BARE
    if not bare.any():
        return np.zeros(f.shape, dtype=bool)
    m = margin_cells(d, dx)
    return (ndimage.distance_transform_edt(~bare) <= m + 1e-9) & active


@dataclass
class GapPlan:
    """!
    @brief What the rule decided for one gap.
    """
    gap: int                       # 0-based gap (layers gap and gap + 1; a one-layer board has gap 0 down to the bottom node)
    d: float                       # Thickness in m
    n: int                         # Sub-gaps in the flagged cells (1: the gap is not cut)
    flagged: np.ndarray            # Boolean (ny, nx) of the cells that carry the n - 1 interior nodes


def plan_gaps(board, fill, dx, active, s_max=None, n_max=None):
    """!
    @brief Apply the rule to every gap of a board.
    @param board A Board.
    @param fill Copper fill of every layer (L, ny, nx).
    @param dx Cell size (FVM) or node spacing (FDM) in m.
    @param active Boolean (ny, nx) of the cells or nodes on the board.
    @param s_max Longest sub-gap in m (None: parameters()).
    @param n_max Most sub-gaps (None: parameters()).
    @return List of GapPlan, one per gap (a one-layer board has one).
    """
    if s_max is None or n_max is None:
        ps, pn = parameters()
        s_max, n_max = ps if s_max is None else s_max, pn if n_max is None else n_max
    if board.layers == 1:
        t_lam = float(board.slab_thicknesses()[0]) - float(np.asarray(board.copper_thickness, dtype=float)[0])
        items = [(0, t_lam, fill[0], None)]
    else:
        d_all = board.gap_thicknesses()
        items = [(g, float(d_all[g]), fill[g], fill[g + 1]) for g in range(board.layers - 1)]
    out = []
    for g, d, fa, fb in items:
        n = n_for_gap(d, s_max, n_max)
        flagged = flag_cells(fa, fb, d, dx, active) if n > 1 else np.zeros(fa.shape, dtype=bool)
        if not flagged.any():
            n, flagged = 1, np.zeros(fa.shape, dtype=bool)          # Nothing to refine: the gap stays one link
        out.append(GapPlan(g, d, n, flagged))
    return out


def count_unknowns(board, plans, cells):
    """!
    @brief Unknowns of the network with the rule, counted without building it: the copper nodes, the bottom node of a one-layer board, and the interior nodes of the flagged cells only.
    @param board A Board.
    @param plans List from plan_gaps.
    @param cells Cells (or nodes) of the grid, nx * ny.
    @return Tuple (unknowns, node layers of the dense arrays).
    """
    one = board.layers == 1
    layers = board.layers + (1 if one else 0) + sum(p.n - 1 for p in plans)
    unknowns = (board.layers + (1 if one else 0)) * cells + sum((p.n - 1) * int(p.flagged.sum()) for p in plans)
    return unknowns, layers


@dataclass
class Ladder:
    """!
    @brief Description of the laminate nodes built on a network.
    """
    plans: list                    # GapPlan of every gap
    n_board: int                   # Copper layers
    one_layer: bool                # True: the last node layer is the bottom node of a one-layer board
    drop: np.ndarray               # Boolean (node layers, ny, nx): nodes that no cell uses (interior nodes outside the flagged cells), left out of the direct solve
    bottom_layer: int = -1         # Index of the bottom node layer of a one-layer board (-1 otherwise)

    def refined(self):
        """!
        @brief Whether any gap was cut.
        @return True when interior nodes exist.
        """
        return any(p.n > 1 for p in self.plans)


@dataclass
class LadderBuild:
    """!
    @brief Arrays changed or created by build().
    """
    S: np.ndarray                  # Lateral conductance of the copper nodes (L, ny, nx), W/K
    C: np.ndarray                  # Heat capacity of the copper nodes, J/K
    gz: np.ndarray                 # Vertical conductance between copper layers (L - 1, ny, nx), W/K (zero in the refined cells)
    g_bottom: np.ndarray           # Conductance to the ambient through the bottom face of the copper nodes (L, ny, nx), W/K
    g_side: np.ndarray             # Conductance through the board edge of the copper nodes, W/K
    layers: list = field(default_factory=list)       # New node layers, top down: dicts S, C, g_bottom, g_side, pin (boolean: node unused or off the board)
    links: list = field(default_factory=list)        # (layer a, layer b, conductance (ny, nx)) between new nodes and copper nodes (indices as in the finished network)
    ladder: Ladder = None


def build(board, fill, cell, cover, active, edge, S, C, gz, g_bottom, g_side, plans):
    """!
    @brief Put the laminate nodes of the rule into the arrays of a network.
    @details The caller (fvm.Network, fdm.Network) has built the copper nodes with the whole slab of laminate around them and the single links `gz`; this moves the laminate that belongs
             to the interior nodes out of the copper nodes (S, C, edge conductance), cuts the links in the refined cells, applies the vertical correction to every cell with absent copper,
             and returns the new layers. Their indices follow the copper layers: the interior nodes of gap 0, of gap 1, ..., and for a one-layer board the bottom node after those of its gap.
    @param board A Board.
    @param fill Copper fill (L, ny, nx).
    @param cell Board area of every cell or control volume in m2, (ny, nx).
    @param cover Board share of every cell or node (0 to 1), (ny, nx).
    @param active Boolean (ny, nx) of the cells on the board.
    @param edge Length of board edge exposed in every cell or control volume in m, (ny, nx) (zeros when there is no edge coefficient).
    @param S Lateral conductance of the copper nodes, W/K (L, ny, nx).
    @param C Heat capacity of the copper nodes, J/K (L, ny, nx).
    @param gz Single links between copper layers, W/K (L - 1, ny, nx) (the dielectric alone; the vias are separate).
    @param g_bottom Conductance to the ambient through the bottom face, W/K (L, ny, nx) (a one-layer board: on the copper node, moved to the bottom node here).
    @param g_side Edge conductance of the copper nodes, W/K (L, ny, nx).
    @param plans List from plan_gaps.
    @return LadderBuild (the arrays are copies).
    """
    ny, nx = cell.shape
    L0 = board.layers
    one = L0 == 1
    t_cu = np.asarray(board.copper_thickness, dtype=float)
    hs = float(board.h_side or 0.0)
    kz_g, kxy_g, rcp_g = board.gap_properties()
    m = board.materials
    S, C, g_side, g_bottom = S.copy(), C.copy(), g_side.copy(), g_bottom.copy()
    gz = gz.copy() if L0 > 1 else gz
    out = LadderBuild(S, C, gz, g_bottom, g_side)
    # Share of the requested laminate that every copper node can give up. The rule moves d / 2 - s_0 / 2 of each refined gap out of the copper node on either side;
    # in the advanced stack-up a node holds exactly d / 2 of each adjacent gap, but in the simple stack-up every node holds thickness / layers - t_cu, which for an inner
    # node of a thick three-layer board (3.2 mm: 1.03 mm) is less than the two moves (1.16 mm). Without this share the node was clipped to zero capacity and lateral
    # conductance while the interior nodes still got the full laminate (heat capacity +1.6 % on that board, a negative edge conductance). Where a node is short, its
    # moves are scaled down and the interior nodes of the gap get only what was moved; elsewhere the share is exactly 1 (bit for bit the arrays without it).
    share = np.ones((L0, ny, nx))
    if not one:
        held = board.slab_thicknesses() - t_cu                    # Gap laminate held by every copper node, m
        demand = np.zeros((L0, ny, nx))
        for p in plans:
            want = np.where(p.flagged, p.d / 2.0 - p.d / (2.0 * p.n), 0.0)
            demand[p.gap] += want
            demand[p.gap + 1] += want
        short = demand > held[:, None, None] * (1.0 + 1e-12)
        share = np.where(short, held[:, None, None] / np.where(short, demand, 1.0), 1.0)
    nxt = L0                                                     # Index of the next node layer
    drop = []
    bottom_layer = -1
    for p in plans:
        d, n, F = p.d, p.n, p.flagged
        a = p.gap
        b = None if one else a + 1
        if one:
            kz, kxy, rcp = m.k_fr4_through, m.k_fr4_inplane, m.rho_fr4 * m.cp_fr4
            lam = kz * cell / d                                  # The single link of the cell: copper node to the bottom node
        else:
            kz, kxy, rcp = float(kz_g[a]), float(kxy_g[a]), float(rcp_g[a])
            lam = gz[a].copy()
        s = np.full(n, d / n)
        # Vertical correction: the laminate that stands where the copper of each adjacent layer is absent lengthens the path by (1 - f) t / 2
        ea = (1.0 - fill[a]) * t_cu[a] / 2.0
        eb = (1.0 - fill[b]) * t_cu[b] / 2.0 if b is not None else np.zeros((ny, nx))
        single = np.where(ea + eb > 0, lam * d / (d + ea + eb), lam)        # Unchanged (bit for bit) where both layers have copper
        # Laminate that moves from the copper node(s) into the new nodes, in the flagged cells only
        keep_a = np.where(F, s[0] / 2.0, d / 2.0)
        move_a = (d - keep_a) if one else (d / 2.0 - keep_a) * share[a]    # (the single node of a one-layer board holds the whole laminate)
        # Interior nodes get what the two copper nodes gave up: the two requests are equal, so the scale is the mean of the two shares (exactly 1 where neither is short)
        fill_in = 1.0 if one else np.where((share[a] < 1.0) | (share[b] < 1.0), 0.5 * (share[a] + share[b]), 1.0)
        out.S[a] = np.maximum(out.S[a] - kxy * move_a * cover, 0.0)
        out.C[a] = np.maximum(out.C[a] - rcp * move_a * cell, 0.0)
        out.g_side[a] -= hs * move_a * edge
        first = nxt
        for j in range(1, n):
            th = (s[j - 1] + s[j]) / 2.0
            out.layers.append({"S": np.where(F, kxy * th * cover * fill_in, 0.0), "C": np.where(F, rcp * th * cell * fill_in, 0.0), "g_bottom": np.zeros((ny, nx)),
                               "g_side": np.where(F, hs * th * edge * fill_in, 0.0), "pin": ~F})
            drop.append(~F)
            nxt += 1
        if one:
            keep_b = np.where(F, s[-1] / 2.0, d / 2.0)
            out.layers.append({"S": kxy * keep_b * cover, "C": rcp * keep_b * cell, "g_bottom": board.h_bottom * cell, "g_side": hs * keep_b * edge, "pin": ~active})
            drop.append(np.zeros((ny, nx), dtype=bool))
            end = nxt
            bottom_layer = nxt
            nxt += 1
            out.g_bottom[0] = 0.0                                # The bottom film moves from the copper node to the bottom node
            out.links.append((a, end, np.where(F, 0.0, single)))
        else:
            move_b = (d / 2.0 - np.where(F, s[-1] / 2.0, d / 2.0)) * share[b]
            out.S[b] = np.maximum(out.S[b] - kxy * move_b * cover, 0.0)
            out.C[b] = np.maximum(out.C[b] - rcp * move_b * cell, 0.0)
            out.g_side[b] -= hs * move_b * edge
            end = b
            out.gz[a] = np.where(F, 0.0, single)
        if n > 1:
            chain = [a] + list(range(first, first + n - 1)) + [end]
            for k in range(n):
                ext = (ea if k == 0 else 0.0) + (eb if k == n - 1 else 0.0)
                out.links.append((chain[k], chain[k + 1], np.where(F, lam * d / (s[k] + ext), 0.0)))
    full = np.zeros((nxt, ny, nx), dtype=bool)
    if drop:
        full[L0:] = np.stack(drop)
    out.ladder = Ladder(plans, L0, one, full, bottom_layer)
    return out


def face_terms(board, fill, Q, cell, dx):
    """!
    @brief Rise between the node and the face of a part over absent copper, per cell: the correction of the reported peak and mean of a part on an outer layer.
    @details A part injects its heat at the node of its layer, at mid-thickness of the copper; where the copper is absent the half layer of laminate between the node and the face adds
             Q t_cu / (2 k_z A) (k_z of the gap next to that face; the laminate of a one-layer board). Peak: the full term in every cell with fill below 1, multiplied by min(1, w / (4 t_cu))
             with w = (1 - f) dx the bare width (a bare feature narrower than about four copper thicknesses does not carry the full drop; a cell with no copper at all is bare for its whole
             width). Mean: the term weighted by the bare share (1 - f) of the cell.
    @param board A Board.
    @param fill Copper fill (L, ny, nx).
    @param Q Heat injected in every node, W (at least L layers, ny, nx).
    @param cell Board area of every cell or control volume in m2, (ny, nx).
    @param dx Cell size or node spacing in m.
    @return Tuple (peak, mean) of arrays (L, ny, nx) in K, or None when no outer-layer cell with heat has absent copper.
    """
    L = board.layers
    t_cu = np.asarray(board.copper_thickness, dtype=float)
    kz = board.gap_properties()[0] if L > 1 else np.array([board.materials.k_fr4_through])
    peak, mean = np.zeros(fill.shape), np.zeros(fill.shape)
    found = False
    for l in sorted({0, L - 1}):
        q = Q[l]
        f = fill[l]
        hot = (q > 0) & (f < BARE) & (cell > 0)
        if not hot.any():
            continue
        k = float(kz[0] if l == 0 else kz[-1])
        term = np.where(hot, q * t_cu[l] / (2.0 * k * np.where(cell > 0, cell, 1.0)), 0.0)
        bare = 1.0 - f
        guard = np.where(f <= 1e-9, 1.0, np.minimum(1.0, bare * dx / (SLIVER_THICKNESSES * t_cu[l])))
        peak[l] = term * guard
        mean[l] = term * bare
        found = True
    return (peak, mean) if found else None
