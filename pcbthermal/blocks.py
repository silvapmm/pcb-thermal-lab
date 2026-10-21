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
         * to the ambient through the exposed surface, G = (h_face + h_extra) A c, and through the sides of the block, G = (h_face + h_extra) t L_edge,
           with L_edge the length of the edge of the block inside the cell (a rectangular block on the grid has the whole length of its outline);
         * the board face under the block no longer loses heat to the air (it is covered): its coefficient is multiplied by 1 - c.

         Nodes with no block get a negligible conductance to the ambient so that the matrix stays regular; their temperature rise is zero.
         The block is taken as perfectly in contact with its pad over the overlap and as an isotropic plate whose temperature does not vary
         across its thickness (valid for the usual thin blocks: the Biot number of the thickness is small).
"""

import copy

import numpy as np

ISOLATED = 1.0e-9            # W/K of a node without block: keeps the matrix regular, changes nothing


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
            g_amb_extra (the part of g_amb that is the extra coefficient), face_scale (factor for the board face coefficient),
            h_total (the exposed coefficient of every node, W/m2K) and names.
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
        S, C, g_link, g_amb, h_tot = (np.zeros((ny, nx)) for _ in range(5))
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
            r_c = max(s.contact_r, 1e-7)
            f = fill[layer]
            g_link = np.where(take, c * area * (f / r_c + (1.0 - f) / (r_c + r_half)), g_link)
            h_tot = np.where(take, h_face + s.h_extra, h_tot)
            side = np.zeros_like(c)                                         # Length of the block edge inside every cell
            pad = np.pad(c, 1)
            for axis, length in ((1, dy), (0, dx)):
                for sgn in (-1, 1):
                    neigh = np.roll(pad, sgn, axis=axis)[1:-1, 1:-1]
                    side += length * np.maximum(c - neigh, 0.0)
            g_amb = np.where(take, h_tot * (area * c + s.thickness * side), g_amb)
        g_amb = np.where(cov > 0, g_amb, ISOLATED)
        out.append({"face": face, "board_layer": layer, "cov": cov, "S": S, "C": C, "g_link": g_link, "g_amb": g_amb,
                    "face_scale": 1.0 - cov, "h_total": h_tot, "names": names})
    return out


def has_blocks(problem):
    """!
    @brief True if the problem has a metal block.
    @param problem A Problem.
    @return Boolean.
    """
    return any(s.is_block() for s in problem.heatsinks)


def plain_equivalent(problem):
    """!
    @brief The problem with every metal block replaced by a plain heatsink, for the models that do not have blocks (lumped, analytic).
    @details A block is replaced by the extra coefficient that gives the same heat through the interface and the exposed surface:
             h_eq = 1 / (R'' + 1 / (h_face + h_extra)) minus the coefficient of the face that the plain heatsink adds to. The spreading in the
             metal, its mass and the copper fill of the contact are not represented.
    @param problem A Problem.
    @return The same Problem if there is no block, otherwise a copy.
    """
    if not has_blocks(problem):
        return problem
    p = copy.deepcopy(problem)
    b = p.board
    for s in p.heatsinks:
        if s.is_block():
            h_face = b.h_top if (s.layer == 0 or b.layers == 1) else b.h_bottom
            h_eq = 1.0 / (max(s.contact_r, 1e-7) + 1.0 / (h_face + s.h_extra))
            s.h_extra, s.thickness = max(h_eq - h_face, 0.0), 0.0
    return p
