#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file blocks.py
@brief Metal blocks attached to the outer faces of the board: the extra thermal nodes they add to a cell or node network.

@details A heatsink with a thickness (model.Heatsink.is_block) is a plate of metal pressed on an outer face of the board through an interface.
         For every face that carries blocks the network gets **one extra layer** of nodes, one per cell or grid point:

         * lateral conductance  S = k t c   (c = fraction of the cell covered by the block), joined with the harmonic mean like the board;
         * heat capacity        C = rho cp t A c;
         * contact to the board layer of that face, G = c A [ f / R'' + (1 - f) / (R'' + d / k) ]  with f the copper fill of the board layer there:
           the heat enters the block through the interface of resistance R'' (m2K/W) mostly where it overlaps copper (the intersection of the two
           planes); over bare laminate it has to cross half a layer slab d of FR-4 as well, a much larger resistance;
         * to the ambient through the exposed surface, G = h_exp A c, with h_exp = h_face x fin ratio + h_extra (fin_ratio: plate fins with their
           efficiency, on the face only; 1 for a plain plate), and through the sides of the block, G = h_wall t L_edge, with h_wall = h_face + h_extra
           (the fins stand on the exposed face, not on the sides, so the sides see the plain coefficient),
           with L_edge the length of the edge of the block inside the cell (a rectangular block on the grid has the whole length of its outline);
         * the board face under the block no longer loses heat to the air (it is covered): its coefficient is multiplied by 1 - c.

         Nodes with no block get a negligible conductance to the ambient so that the matrix stays regular; their temperature rise is zero.
         The block is taken as perfectly in contact with its pad over the overlap and as an isotropic plate whose temperature does not vary
         across its thickness (valid for the usual thin blocks: the Biot number of the thickness is small).
"""

import copy

import numpy as np

ISOLATED = 1.0e-9            # W/K of a node without block: keeps the matrix regular, changes nothing


def fin_ratio(h, s):
    """!
    @brief Ratio of the heat given by the finned face of a block to that of the plain plate, for the same coefficient h on the metal.
    @details Plate fins perpendicular to the base, thin fins with an adiabatic tip at the corrected height Hc = H + t/2: efficiency
             eta = tanh(m Hc) / (m Hc), m = sqrt(2 h / (k t)); per unit of base area the free base is 1 - t/p and the fins add 2 Hc eta / p, with t the
             fin thickness and p the pitch. The air between close fins is not slowed down in this model (see checks.py for the warning).
    @param h Heat transfer coefficient on the metal in W/m2K.
    @param s A Heatsink (block).
    @return Ratio >= 1 (1 for a block without fins).
    """
    if not s.has_fins():
        return 1.0
    t, p, hc = s.fin_thickness, s.fin_pitch, s.fin_height + 0.5 * s.fin_thickness
    m = np.sqrt(2.0 * max(h, 1e-12) / (s.k * t))
    eta = np.tanh(m * hc) / (m * hc)
    return float((1.0 - t / p) + 2.0 * hc * eta / p)


def exposed_h(s, h_face):
    """!
    @brief Coefficient of the exposed surface of a block, per unit of base area: the face coefficient times the fin ratio plus the extra h.
    @param s A Heatsink (block).
    @param h_face Coefficient of the board face the block is on, in W/m2K.
    @return W/m2K.
    """
    return h_face * fin_ratio(h_face, s) + s.h_extra


def wall_h(s, h_face):
    """!
    @brief Coefficient of the side walls of a block: the plain face coefficient plus the extra h, with no fin ratio (the fins are on the exposed face).
    @param s A Heatsink (block).
    @param h_face Coefficient of the board face the block is on, in W/m2K.
    @return W/m2K.
    """
    return h_face + s.h_extra


def block_faces(problem):
    """!
    @brief The outer faces that carry metal blocks.
    @param problem A Problem.
    @return Sorted list of face indices: 0 for the top face, 1 for the bottom face (the top face for a one-layer board).
    """
    n = problem.board.layers
    faces = set()
    for s in problem.heatsinks:
        if s.is_block():
            faces.add(0 if (s.layer == 0 or n == 1) else 1)
    return sorted(faces)


def extra_layers(problem, cover, area, fill, dx, dy):
    """!
    @brief Build the arrays of the extra block layers of a network.
    @param problem A Problem.
    @param cover Function cover(polygon, samples) giving the covered fraction of every cell or node, shape (ny, nx).
    @param area Area represented by every cell or node in m2, shape (ny, nx).
    @param fill Copper fill of the board layers, shape (layers, ny, nx).
    @param dx Spacing of the cells or nodes along x in metres (length of the side faces seen from x).
    @param dy Spacing along y in metres.
    @return List of dicts, one per face with blocks, with keys face (0 top, 1 bottom), board_layer, cov, S, C, g_link, g_amb,
            face_scale (factor for the board face coefficient), h_total (the coefficient of the exposed face of every node, with the fin ratio,
            W/m2K; the sides use h_wall instead), h_wall (the coefficient of the side walls, W/m2K; named so because Board.h_side is the board edge coefficient) and names.
    """
    b = problem.board
    L = b.layers
    slabs, k_gap = b.slab_thicknesses(), b.gap_properties()[0]
    def half_slab_resistance(layer):
        # Half a layer slab of the dielectric next to the face (m2K/W); the face's own gap when there is one
        k = k_gap[0 if layer == 0 else L - 2] if L > 1 else b.materials.k_fr4_through
        return slabs[layer] / 2.0 / k
    out = []
    for face in block_faces(problem):
        layer = 0 if face == 0 else L - 1
        r_half = half_slab_resistance(layer)
        h_face = b.h_top if face == 0 else b.h_bottom
        ny, nx = area.shape
        cov = np.zeros((ny, nx))
        S, C, g_link, g_amb, h_tot, h_sd = (np.zeros((ny, nx)) for _ in range(6))
        names = []
        for s in problem.heatsinks:
            if not s.is_block() or (0 if (s.layer == 0 or L == 1) else 1) != face:
                continue
            c = cover(s.polygon, 4)
            take = c > 0
            names.append(s.name)
            cov = np.where(take, np.maximum(cov, c), cov)                  # Overlapping blocks: the later one wins in the overlap
            S = np.where(take, s.k * s.thickness * c, S)
            C = np.where(take, s.rho_cp * s.thickness * area * c, C)
            # Contact only over the copper (fill) inside the block; a zero resistance is limited to avoid an unbounded conductance
            r_c = max(s.interface_resistance(), 1e-7)
            f = fill[layer]
            g_link = np.where(take, c * area * (f / r_c + (1.0 - f) / (r_c + r_half)), g_link)
            h_tot = np.where(take, exposed_h(s, h_face), h_tot)
            h_sd = np.where(take, wall_h(s, h_face), h_sd)                    # No fin ratio on the side walls
            side = np.zeros_like(c)                                         # Length of the block edge inside every cell
            pad = np.pad(c, 1)
            for axis, length in ((1, dy), (0, dx)):
                for sgn in (-1, 1):
                    neigh = np.roll(pad, sgn, axis=axis)[1:-1, 1:-1]
                    side += length * np.maximum(c - neigh, 0.0)
            g_amb = np.where(take, h_tot * area * c + h_sd * s.thickness * side, g_amb)
        g_amb = np.where(cov > 0, g_amb, ISOLATED)
        out.append({"face": face, "board_layer": layer, "cov": cov, "S": S, "C": C, "g_link": g_link, "g_amb": g_amb,
                    "face_scale": 1.0 - cov, "h_total": h_tot, "h_wall": h_sd, "names": names})
    return out


def has_blocks(problem):
    """!
    @brief True if the problem has a metal block.
    @param problem A Problem.
    @return Boolean.
    """
    return any(s.is_block() for s in problem.heatsinks)


def require_rectangle(problem):
    """!
    @brief Refuse a board with an outline polygon in the models that need a rectangle (lumped, analytic).
    @details `simulate` solves the rectangle of the same area for them (`Problem.equivalent_rectangle`); calling the model directly on an outline is an error.
    @param problem A Problem.
    @return The same Problem.
    @throws ValueError If the board has an outline polygon.
    """
    if problem.board.has_outline():
        raise ValueError("this model needs a rectangular board: the board has an outline polygon (use the FVM, FDM or the 3D solid)")
    return problem


def require_no_blocks(problem):
    """!
    @brief Refuse a problem with a metal block in the calculations that cannot represent one: the transients of the lumped and analytic models (their steady states do represent it).
    @details The steady states of the lumped model (block layer in the ring network) and of the analytic model (graph of tiles in the Green-function correction) have the block;
             their time simulations do not (the capacity of the block layer was never tested there), so they refuse it.
    @param problem A Problem.
    @return The same Problem.
    @throws ValueError If the problem has a metal block, or an outline polygon (these models need a rectangular board; `simulate` solves the rectangle of the same area).
    """
    require_rectangle(problem)
    if has_blocks(problem):
        raise ValueError("this calculation does not support a metal block (the transient of the lumped and analytic models): use the FVM, FDM or the 3D solid")
    return problem
