#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file rimmask.py
@brief Prototype of the rim test of a via read from the masks of imported copper (a copy of `viawell.rim_copper_shares` with the mask branch), installed by monkeypatch.
@details The program skips the rim test for imported copper (`viawell.rim_copper_shares` returns 1.0 on every layer when `problem.imported` is set). Here the same 48 samples
         on the circle of the drill are looked up in the raster of each imported layer (nearest pixel, coverage 0..255 over 255); a heater of the layer still counts as contact
         (as for drawn boards); a layer without a mask keeps the zone rule. Nothing of the program is edited: `install()` replaces the function in the module for the run and
         `uninstall()` restores it.
"""

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from pcbthermal import viawell, copper   # noqa: E402
from pcbthermal.geometry import points_in_polygon   # noqa: E402

_ORIGINAL = viawell.rim_copper_shares
_CACHE = {}


def rim_shares_masks(problem, v, n_layers, zone_index, threshold=0.5, reach_mm=0.0):
    """!
    @brief Rim share of the drill of a via per layer, imported layers from their masks.
    @param problem The Problem.
    @param v The Via.
    @param n_layers Number of layers.
    @param zone_index As in `viawell._zone_index` (zones and heaters per layer; the zones of an imported layer are ignored, the heaters count).
    @param threshold Coverage (0..1) at or above which a pixel counts as copper at a rim sample.
    @param reach_mm 0: the rim test of the program (a sample counts when the pixel ON the drill circle is copper). Above 0: a sample counts only when the copper is continuous
           along the whole ray from the drill circle out to this distance beyond it (a pad island inside an antipad does not connect the barrel to the plane).
    @return list of L floats in [0, 1].
    """
    src = copper.CopperSource.of(problem)
    if src is None:
        return _ORIGINAL(problem, v, n_layers, zone_index)
    ang = (np.arange(viawell.RIM_SAMPLES) + 0.5) * 2.0 * math.pi / viawell.RIM_SAMPLES
    r = v.diameter / 2.0
    px, py = v.x + r * np.cos(ang), v.y + r * np.sin(ang)
    H = problem.board.height
    out = []
    for l in range(n_layers):
        covered = np.zeros(viawell.RIM_SAMPLES, dtype=bool)
        if l in src.entries:
            ras = src.raster(l)
            rows, cols = ras.shape
            ci = np.clip((px / src.pix).astype(int), 0, cols - 1)
            ri = np.clip(((H - py) / src.pix).astype(int), 0, rows - 1)
            covered |= ras[ri, ci] >= threshold * 255.0
            if reach_mm > 0.0:
                # March outward in steps of one pixel; a ray is copper only if every pixel on it is
                steps = np.arange(1, int(math.ceil(reach_mm * 1e-3 / src.pix)) + 1) * src.pix
                for s_ in steps:
                    qx, qy = v.x + (r + s_) * np.cos(ang), v.y + (r + s_) * np.sin(ang)
                    cj = np.clip((qx / src.pix).astype(int), 0, cols - 1)
                    rj = np.clip(((H - qy) / src.pix).astype(int), 0, rows - 1)
                    covered &= ras[rj, cj] >= threshold * 255.0
        polys, boxes = zone_index[l]
        if len(polys):
            # heaters only for an imported layer (its zones are replaced by the mask); all shapes otherwise
            keep = [h.polygon for h in problem.heaters if h.layer == l] if l in src.entries else list(polys)
            for q in keep:
                covered |= points_in_polygon(px, py, np.asarray(q, dtype=float))
        out.append(float(covered.mean()))
    return out


def install(threshold=0.5, reach_mm=0.0):
    """!
    @brief Replace `viawell.rim_copper_shares` by the mask version.
    @param threshold Coverage threshold at a rim sample.
    @param reach_mm Reach of the ray test in mm (0: the drill circle only).
    @return None.
    """
    viawell.rim_copper_shares = lambda p, v, n, zi: rim_shares_masks(p, v, n, zi, threshold, reach_mm)


def uninstall():
    """!
    @brief Restore the program's function.
    @return None.
    """
    viawell.rim_copper_shares = _ORIGINAL
