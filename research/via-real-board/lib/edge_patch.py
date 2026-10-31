#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file edge_patch.py
@brief The recommended via treatment (`mw_disc@eta` of point-via-convergence) with the three additions studied here, installed on in-memory copies of the program: footprint restricted to
       the cells on the board, optional folding of the cut footprint, and the image of the edge in the well; also the point conductance `gz_via` that the Lumped model keeps reading.
@details `program_patch.patched("mw_disc", eta=exp(-1/4))` compiles copies of `fvm.Network.__init__`, `fvm.Network._assemble` and `fdm.Network.__init__` that call a module-level
         `_via_hook`. This module installs the same copies and then replaces the hook by `via_hook_edge`, which differs from `program_patch.via_hook` (mean-potential branch) in:
         * `board_only`  the footprint keeps only the cells with cover > 0 (weighted by the cover), then is renormalised (the prototype keeps every cell inside the grid, so a cell
                         off an outline, pinned to the ambient by g_pin, could be coupled to the barrel);
         * `fold`        the part of the footprint that falls outside the grid is moved to the mirror cell instead of being dropped and renormalised;
         * `image`       the well of every layer is 2 pi S / (ln(r_eff / r_t) + c) with c the edge term of `edge_image.well_correction` (FVM only: the edge nodes of the FDM are half
                         volumes and have no mirror image);
         * `s_mode`      the sheet conductance of the well is that of the cell of the largest weight ("max", the prototype's rule) or the weighted mean ("mean");
         * `gz_via`      `net.gz_via` holds the barrel conductance of every gap at the cell of the via centre, which is exactly what the program's own loop adds to `gz`
                         (the Lumped model sums `gz` over rings and must keep seeing it; the assembled matrix does not use it).
         Every option can be switched off, so the sweep of the studies is one call with different keywords. The files of the program are not edited.
"""

import contextlib
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
POINT_LIB = os.path.join(os.path.dirname(os.path.dirname(HERE)), "point-via-convergence", "lib")
sys.path.insert(0, POINT_LIB)
sys.path.insert(0, HERE)

import edge_image as ei                                                     # noqa: E402
import program_patch as pp                                                  # noqa: E402
import viakernel as vk                                                      # noqa: E402
from pcbthermal.geometry import cell_index_of_point                         # noqa: E402

ETA = math.exp(-0.25)                                                       # target radius / drill radius of the layered idealisation
OPTS = {"board_only": True, "fold": False, "image": True, "s_mode": "max", "wall_cells": 6.0, "eta": ETA}
STATS = {"vias": 0, "edge_vias": 0, "dropped": 0, "inf_wells": 0}            # counters of the last network (reset by `patched_edge`)


def walls_for(problem, v, reach):
    """!
    @brief The straight insulated walls near a via: the edges of the board box, or the axis-parallel segments of the outline, at most one per axis (the nearest).
    @param problem The Problem.
    @param v The Via.
    @param reach Largest distance from the via centre to a wall that is considered, in m.
    @return list of (axis, position) with axis "x" or "y", positions in m (at most two).
    """
    b = problem.board
    cand = {"x": [], "y": []}
    if b.outline is None:
        cand["x"] = [0.0, b.width]
        cand["y"] = [0.0, b.height]
    else:
        pts = [(float(p[0]), float(p[1])) for p in b.outline]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            if abs(x1 - x0) < 1e-12 and min(y0, y1) - reach <= v.y <= max(y0, y1) + reach:
                cand["x"].append(x0)
            elif abs(y1 - y0) < 1e-12 and min(x0, x1) - reach <= v.x <= max(x0, x1) + reach:
                cand["y"].append(y0)
    out = []
    for axis, pos in (("x", v.x), ("y", v.y)):
        near = [(abs(pos - p), p) for p in cand[axis] if abs(pos - p) <= reach]
        if near:
            out.append((axis, min(near)[1]))
    return out


def via_hook_edge(net, problem, gz, d, S, dx, dy, nx, ny, origin):
    """!
    @brief The mean-potential treatment with the options of this module; same contract as `program_patch.via_hook` (it is installed in its place).
    @param net The network being built (`_via_blocks` and `gz_via` are set on it).
    @param problem The Problem.
    @param gz Array (L-1, ny, nx) of vertical conductances of the dielectric (not modified: the vias are couplings in the matrix).
    @param d Gap thicknesses in m.
    @param S Sheet conductances in W/K, shape (L', ny, nx).
    @param dx Cell size in m.
    @param dy Cell size in y in m (equal to dx).
    @param nx Cells (nodes) along x.
    @param ny Cells (nodes) along y.
    @param origin Lower edge of the first cell (0 for the FVM, -dx/2 for the FDM) in m.
    @return None.
    """
    b = problem.board
    m = b.materials
    L = gz.shape[0] + 1
    net._via_blocks = []
    net.gz_via = np.zeros_like(gz)
    cover = getattr(net, "cover", None)
    rt_factor = OPTS["eta"]
    for v in problem.vias:
        STATS["vias"] += 1
        area = v.thermal_area(b.via_plating, m.k_copper)
        gv = m.k_copper * area / d
        rv = v.diameter / 2.0
        rt = rt_factor * rv
        # The point conductance of the program's loop: the Lumped model keeps reading it from gz_via
        # (the program's own index function: `x // dx` differs from floor(x / dx) for a via exactly on a cell line, which the first run of the own via field found)
        ip, jp = cell_index_of_point(v.x - origin, v.y - origin, nx, ny, dx, dy)
        net.gz_via[:, ip, jp] += gv
        w = vk.disc_target_weights(v.x, v.y, rv, rt, dx, origin)           # as program_patch (rule "disc"): identical when every option is off
        n_all = len(w)
        if OPTS["fold"]:
            w = ei.fold_into_grid(w, ny, nx)
        if OPTS["board_only"]:
            w = ei.restrict_to_board(w, cover, ny, nx)
        else:
            w = {k: x for k, x in w.items() if 0 <= k[0] < ny and 0 <= k[1] < nx}
            tot = sum(w.values())
            w = {k: x / tot for k, x in w.items()} if tot > 0 else {}
        if not w:                                                          # the via is off the board: it does nothing
            STATS["dropped"] += 1
            continue
        STATS["dropped"] += int(len(w) < n_all)
        r_f = vk.effective_radius(w, dx)
        keys = list(w.keys())
        wv = np.array([w[k] for k in keys])
        if OPTS["s_mode"] == "mean":
            s_eff = [float(sum(w[k] * S[l, k[0], k[1]] for k in keys)) for l in range(L)]
        else:
            ic, jc = max(w, key=w.get)
            s_eff = [float(S[l, ic, jc]) for l in range(L)]
        c = 0.0
        if OPTS["image"] and origin == 0.0:
            walls = walls_for(problem, v, OPTS["wall_cells"] * dx)
            if walls:
                STATS["edge_vias"] += 1
                c = ei.well_correction(w, (v.x, v.y), rv, dx, origin, walls)
        if c == 0.0:
            g_well = [vk.well_conductance(s_eff[l], r_f, rt) if s_eff[l] > 0 else 0.0 for l in range(L)]
        else:
            g_well = [ei.well_conductance_image(s_eff[l], r_f, rt, c) if s_eff[l] > 0 else 0.0 for l in range(L)]
        STATS["inf_wells"] += int(any(math.isinf(g) for g in g_well))
        net._via_blocks.append((keys, wv, vk.kron_barrel(gv, g_well)))


@contextlib.contextmanager
def patched_edge(**options):
    """!
    @brief Install the copies of the program's network code with `via_hook_edge`; restore the originals on exit.
    @param options Any key of OPTS (board_only, fold, image, s_mode, wall_cells, eta).
    @return Context manager; the counters of the networks built inside are in STATS.
    @throws KeyError If an option is unknown.
    """
    from pcbthermal import fdm, fvm
    for k in options:
        if k not in OPTS:
            raise KeyError(k)
    old_opts = dict(OPTS)
    OPTS.update(options)
    STATS.update(vias=0, edge_vias=0, dropped=0, inf_wells=0)
    try:
        with pp.patched("mw_disc", eta=OPTS["eta"]):
            fvm._via_hook = via_hook_edge                                  # the compiled copies look the hook up by name at call time
            fdm._via_hook = via_hook_edge
            yield
    finally:
        OPTS.clear()
        OPTS.update(old_opts)


@contextlib.contextmanager
def lumped_sees_gz_via():
    """!
    @brief Make the Lumped model read `gz + gz_via` (the proposed `gz_via` of the program): the vias stay in its rings as today while the assembled matrix uses the couplings.
    @details Replaces the name `Network` of `pcbthermal.lumped` by a subclass of `fvm.Network` that adds `gz_via` (set by `via_hook_edge`) to `gz` after the constructor; use it inside
             `patched_edge`. Without this the patched network has no via in `gz` and the Lumped model would lose its vias.
    @return Context manager.
    """
    from pcbthermal import fvm, lumped
    base = fvm.Network

    class LumpedNetwork(base):
        """!@brief fvm.Network whose `gz` includes the point via conductance, for the ring sums of the Lumped model."""

        def __init__(self, *args, **kwargs):
            """!
            @brief Build the network, then add `gz_via` to `gz`.
            @param args Positional arguments of fvm.Network.
            @param kwargs Keyword arguments of fvm.Network.
            @return None.
            """
            base.__init__(self, *args, **kwargs)
            gv = getattr(self, "gz_via", None)
            if gv is not None:
                self.gz = self.gz + gv

    old = lumped.Network
    lumped.Network = LumpedNetwork
    try:
        yield
    finally:
        lumped.Network = old
