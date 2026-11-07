#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file contact.py
@brief Candidate via couplings for a plane with copper over part of the footprint that use the CONTACT of the barrel with the copper: a COPY of the logic of pcbthermal/viawell.py in memory.
@details The mean-potential via (viawell.py) couples a layer to the barrel through the mean temperature of a footprint of cells and a Peaceman well of the sheet conductance
         at the via. Two things are wrong when the copper covers only part of the footprint: the weights sit on cells that cannot supply the heat (the cold spot) and the
         well is that of a full plane although the barrel may touch copper over a part of its rim only, or not at all. The variants change those two things and nothing else:
         * `sheet`        weights by the sheet conductance of the cell (research/via-partial-copper, variant a): the footprint weights of lib/viavariants.py.
         * `contact`      the weights of `sheet`, and the well of a layer multiplied by the share f of the rim of the drill (the circle of radius phi / 2, 48 samples) that lies on
                          copper of that layer; f = 0 leaves the layer uncoupled. The coupling stays a mean-potential coupling (a weighted mean and a well), no star.
         * `contact_geo`  the program's geometric weights with the same f on the well (separates the effect of the weights from that of the contact).
         The copper of a layer is the union of its zones (Zone.fill taken as the share of copper); a layer with imported copper masks counts as f = 1 (not modelled here).
         A via whose footprint is uniform and fully on copper is handed to the program's own code (bit-identical), as in lib/viavariants.py.
@note `patched(variant)` replaces viawell.build, matrix_entries and unknown_blocks in memory and restores them on exit; no file of the program is edited. It may be
      combined with lib/barrel.py (the barrel rule) by nesting the two with-blocks (barrel outside).
"""

import contextlib
import math

import numpy as np

import viavariants as vv
from pcbthermal import viawell as vw
from pcbthermal.geometry import points_in_polygon

N_RIM = 48                      # samples on the rim of the drill (a multiple of 4 and offset by half a step, so that none lies on an axis-parallel copper edge through the centre)


def rim_copper_share(problem, v, layer):
    """!
    @brief Share of the rim of the drill that touches copper of one layer.
    @param problem The Problem.
    @param v The via.
    @param layer 0-based layer.
    @return float in [0, 1].
    """
    if problem.imported is not None:
        return 1.0                                   # imported masks are not read here (stated limit)
    ang = (np.arange(N_RIM) + 0.5) * 2.0 * math.pi / N_RIM
    px, py = v.x + 0.5 * v.diameter * np.cos(ang), v.y + 0.5 * v.diameter * np.sin(ang)
    cu = np.zeros(N_RIM)
    for z in problem.zones:
        if z.layer == layer:
            inside = points_in_polygon(px, py, z.polygon)
            cu = np.maximum(cu, np.where(inside, z.fill, 0.0))
    return float(cu.mean())


def make_build(variant):
    """!
    @brief The replacement of viawell.build for a contact variant.
    @param variant "contact" or "contact_geo".
    @return Function with the signature of viawell.build.
    """
    original = vw.build

    def build(problem, d, S, cover, dx, dy, nx, ny, origin, active):
        blocks0, gz_via = original(problem, d, S, cover, dx, dy, nx, ny, origin, active)
        b = problem.board
        k_cu = b.materials.k_copper
        L = len(d) + 1
        oy = origin * dy / dx
        blocks = []
        rel_all = [np.where(cover > 0, S[l] / np.where(cover > 0, cover, 1.0), 0.0) for l in range(L)]
        k = 0
        for v, share in zip(problem.vias, problem.via_board_shares()):
            if share <= 0.0:
                continue
            w0, r_eff0, r_t = vw.footprint(v.x, v.y, v.diameter / 2.0, dx, origin, cover, dy, oy)
            if not w0:
                continue
            prog_block = blocks0[k]
            k += 1
            keys0 = list(w0)
            f = [rim_copper_share(problem, v, l) for l in range(L)]
            uniform = all(np.ptp([rel_all[l][c] for c in keys0]) <= 1e-9 * max(rel_all[l][keys0[0]], 1e-300) for l in range(L))
            if uniform and all(x >= 1.0 - 1e-12 for x in f):
                blocks.append(prog_block)
                continue
            gv = k_cu * v.thermal_area(b.via_plating, k_cu) / d
            layer_w, layer_cells, g_well = [], [], []
            for l in range(L):
                rel = rel_all[l]
                if variant == "contact":
                    w, r_eff, _ = vw_layer(v, dx, dy, origin, oy, cover, rel)
                else:
                    w, r_eff = dict(w0), r_eff0
                if not w or f[l] <= 0.0:
                    layer_w.append(np.zeros(0))
                    layer_cells.append(np.zeros((0, 2), dtype=int))
                    g_well.append(0.0)
                    continue
                cells = np.array(list(w), dtype=int)
                wv = np.array([w[c] for c in w])
                sbar = float(sum(w[c] * rel[c] for c in w))
                layer_w.append(wv)
                layer_cells.append(cells)
                g_well.append(f[l] * vw.well_conductance(sbar, r_eff, r_t) if sbar > 0 else 0.0)
            G = vw.kron_barrel(gv, g_well)
            M = vv.dense_from_mean(layer_w, G)
            allc = {}
            for l in range(L):
                for c in map(tuple, layer_cells[l]):
                    allc[c] = 1
            keys = list(allc)
            blocks.append(vv.Block(np.array([c[0] for c in keys]), np.array([c[1] for c in keys]), np.ones(len(keys)) / len(keys), G, layer_cells, M))
        return blocks, gz_via

    return build


def vw_layer(v, dx, dy, origin, oy, cover, rel):
    """!
    @brief Sheet-conductance weights of one layer (the footprint enlarged until the weighted effective radius reaches the target).
    @param v The via.
    @param dx Cell size x in m.
    @param dy Cell size y in m.
    @param origin Lower x edge in m.
    @param oy Lower y edge in m.
    @param cover Board share of the cells.
    @param rel Relative sheet conductance of the cells of the layer.
    @return Tuple (weights, r_eff, r_t).
    """
    return vv._layer_weights(v, dx, dy, origin, oy, cover, rel, "sheet", v.diameter / 2.0)


@contextlib.contextmanager
def patched(variant):
    """!
    @brief Install a variant in memory for the duration of a with-block.
    @param variant "current", "sheet", "contact" or "contact_geo" (the first two are those of lib/viavariants.py).
    @return context manager.
    """
    if variant in ("current", "sheet"):
        with vv.patched(variant):
            yield
        return
    vw.build = make_build(variant)
    vw.matrix_entries = vv.matrix_entries
    vw.unknown_blocks = vv.unknown_blocks
    try:
        yield
    finally:
        vw.build, vw.matrix_entries, vw.unknown_blocks = vv._ORIG["build"], vv._ORIG["matrix_entries"], vv._ORIG["unknown_blocks"]
