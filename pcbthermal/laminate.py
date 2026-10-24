"""!
@file laminate.py
@brief The laminate of a one-layer board as extra node layers under the copper (FVM, FDM and, through the FVM network, Lumped), and as a series resistance under the bottom film (Analytic).

@details In the layered models a node is a copper layer with the laminate around it. A board with two or more layers has copper on both outer faces, so the films
         act on copper nodes. A one-layer board has copper on the top face only: its single node used to carry the whole laminate, and the bottom film acted on
         that node, so the heat reached the bottom face without crossing the laminate. Against an independent 3D solver this made the FVM 0.9 to 4.4 % low with
         full copper (0.8 to 3.2 mm boards) and 10 % low with a 20 mm pad (research/effective-conductivity, section 4.11).

         The laminate of thickness t_lam = slab - t_cu is now cut into LAMINATE_NODES equal gaps g = t_lam / n, with a node at every gap boundary below the copper,
         the same construction as a board whose lower layers have no copper:

         * the copper node keeps the copper and the upper half gap (slab t_cu + g/2);
         * the inner laminate nodes hold one gap each (slab g), the last one half a gap (slab g/2) and the bottom film;
         * consecutive nodes are joined by k_through A / g; every laminate node conducts sideways with k_inplane times its slab and has its heat capacity.

         Two nodes bring the FVM to -0.0 to -0.3 % with full copper and -2.5 % with the 20 mm pad (three: -1.8 %, four: -1.5 %). The Analytic model keeps one
         node and puts the laminate in series with the bottom film, 1 / (1/h + t_lam / k_through), because extra nodes made its uniform-sheet estimate of a small
         pad worse (-51 % instead of -30 %); with full copper it is then within -0.2 to -1.3 %.
"""

import copy
from dataclasses import dataclass

import numpy as np

LAMINATE_NODES = 2           # Laminate nodes under the copper of a one-layer board (2: within 2.5 % of a 3D solver on a 20 mm pad, 0.3 % with full copper)


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
