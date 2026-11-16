#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file viastudy.py
@brief Synthetic boards of a part over a dense group of thermal vias, and the readings of the Lumped, the FVM and the 3D solid on them with their definitions spelled out.
@details Every board is ours: a 100 x 80 mm board with a full copper plane on every layer, one part on the top layer over a regular array of vias (optionally a second
         part nearby). `run` returns, per model, the three readings that the study compares (peak under the footprint, footprint mean, board maximum) and, for the Lumped,
         the nodes A and C and the peak term, so that "node", "peak" and "mean" are never mixed.
"""

import os
import sys
import math

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pcbthermal import Problem, fvm, lumped, solid3d                         # noqa: E402
from pcbthermal import analysis                                              # noqa: E402


def board(layers=2, n=5, pitch=1.0, drill=0.3, part=8.0, power=3.0, h=10.0, filled=False, offset=(0.0, 0.0), second=None, thickness=1.6, size=(100.0, 80.0)):
    """!
    @brief The synthetic board.
    @param layers Copper layers (a full plane on each).
    @param n Vias per side of the square array (n x n); 0 gives a board with no via.
    @param pitch Via pitch in mm.
    @param drill Drill diameter in mm.
    @param part Side of the square part in mm (top layer).
    @param power Power of the part in W.
    @param h Film coefficient on the two faces in W/m2K.
    @param filled True for copper-filled vias.
    @param offset (dx, dy) in mm of the part centre from the array centre (the array stays at the board centre).
    @param second None or (dx, dy, side, power): a second part, centre offset from the board centre, side and power.
    @param thickness Board thickness in mm.
    @param size (width, height) in mm.
    @return Problem.
    """
    w, hgt = size
    p = Problem.new(w, hgt, layers, thickness_mm=thickness, h_top=h, h_bottom=h)
    for l in range(1, layers + 1):
        p.add_zone(l, rect=(0, 0, w, hgt))
    cx, cy = w / 2.0, hgt / 2.0
    px, py = cx + offset[0], cy + offset[1]
    p.add_heater(1, power, rect=(px - part / 2, py - part / 2, px + part / 2, py + part / 2), name="U1")
    if second is not None:
        sx, sy, ss, sp = second
        p.add_heater(1, sp, rect=(cx + sx - ss / 2, cy + sy - ss / 2, cx + sx + ss / 2, cy + sy + ss / 2), name="U2")
    for i in range(n):
        for j in range(n):
            p.add_via(cx + (i - (n - 1) / 2.0) * pitch, cy + (j - (n - 1) / 2.0) * pitch, drill, filled)
    return p


def _rows(res, p):
    """!
    @brief Peak, footprint mean and board maximum of every part of a result, the way the Results rows read them.
    @param res SteadyResult.
    @param p Problem.
    @return List of dicts {peak, mean} per heater plus the board maximum in key 'board'.
    """
    st = analysis.heater_stats(res, p)
    return [{"peak": s["t_max"], "mean": s["t_mean"]} for s in st], float(res.t_max)


def run(p, model, cell=1.0):
    """!
    @brief One model on one problem.
    @param p Problem.
    @param model 'fvm', 'solid3d', 'lumped' (zoned as the program) or 'lumped1' (one node: zones switched off).
    @param cell Cell in mm (the Lumped uses its own raster: lumped.cell_for).
    @return dict amb, parts (list of {peak, mean}), board (board maximum, degC) and, for the Lumped, extras (A, C, peak_extra, field_max_under_footprint).
    """
    amb = p.board.ambient
    if model == "fvm":
        res = fvm.solve_steady(p, cell)
        parts, bmax = _rows(res, p)
        return {"amb": amb, "parts": parts, "board": float(res.T[0].max()), "board_model": bmax}
    if model == "solid3d":
        res = solid3d.solve_steady(p, cell)
        parts, bmax = _rows(res, p)
        return {"amb": amb, "parts": parts, "board": float(res.T[0].max()), "board_model": bmax}
    old = lumped.ZONES
    lumped.ZONES = (model == "lumped")
    try:
        c = lumped.cell_for(p, cell)
        res = lumped.solve_steady(p, cell_mm=c)
    finally:
        lumped.ZONES = old
    parts, bmax = _rows(res, p)
    return {"amb": amb, "parts": parts, "board": bmax, "board_model": bmax, "cell": c, "heater_peak": res.arrays["heater_peak"].tolist(),
            "zoned": res.arrays["zoned_heaters"].tolist(), "res": res}


def pct(x, ref, amb):
    """!
    @brief Error of a reading against a reference, in percent of the reference's rise over the ambient.
    @param x Reading in degC.
    @param ref Reference in degC.
    @param amb Ambient in degC.
    @return float percent.
    """
    return 100.0 * (x - ref) / (ref - amb)


def core_info(p, k=0, cell=0.5):
    """!
    @brief The geometry of the zone decision of heater k on the Lumped raster: footprint cells, core cells, core share, whether the zones apply, and the via array's reach.
    @param p Problem.
    @param k Heater index.
    @param cell Lumped raster in mm.
    @return dict n_foot, n_core, share (core cells / footprint cells; nan when there is no group), zoned (bool), vias_in (vias with their centre in the footprint), d_nn (mm, mean nearest-neighbour distance of those vias).
    """
    from pcbthermal import viaconstriction
    from pcbthermal.lumped import Network
    from pcbthermal.geometry import points_in_polygon
    b = p.board
    nx, ny = int(round(b.width * 1000 / cell)), int(round(b.height * 1000 / cell))
    net = Network(p, nx, ny, assemble=False, with_blocks=True, ladder=False, cut_cells=False)
    h = p.heaters[k]
    cov = lumped._footprint_coverage(net, h)
    out = {"n_foot": int((cov > 0).sum()), "n_core": 0, "share": float("nan"), "zoned": False, "vias_in": 0, "d_nn": float("nan")}
    if not p.vias:
        return out
    vs = viaconstriction.ViaSet(p)
    core = lumped._core_mask(net, cov, vs)
    inside = points_in_polygon(np.array([x.x for x in p.vias]), np.array([x.y for x in p.vias]), h.polygon)
    out["vias_in"] = int(inside.sum())
    if core is not None:
        out["n_core"] = int(core.sum())
        out["share"] = out["n_core"] / out["n_foot"]
        out["zoned"] = bool(lumped.will_be_zoned(p, h, vias=vs))
        out["d_nn"] = float(np.mean(vs.d_nn[inside])) * 1000 if inside.any() else float("nan")
    return out
