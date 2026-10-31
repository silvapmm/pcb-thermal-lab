#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file real_board.py
@brief The boards of study S2: the plated holes of real Gerber boards (read in place from the git-ignored data folder) and of an own synthetic via field, and the Problem the program runs for them.
@details Three sources of vias:
         * `alleg`  a 4-layer Cadence Allegro board of 101.7 x 81.1 mm (tracespace issue 371 through gerbonara's test resources), Excellon file `drill.drl`: 283 plated holes, 241 of them
                    0.30 mm (12 mil) vias; licence "not stated" at the source, so only numbers are quoted from it and no picture of it is committed;
         * `storm`  the Stormduino Rev 2.2 (MIT, https://github.com/Chromico/stormduino), 2 layers, 68.6 x 53.4 mm, 109 plated holes; its figures may be committed;
         * `own`    `own_via_field`: a 4-layer 60 x 50 mm board of ours with a thermal-via field under a 7 x 7 mm pad and a stitching ring, scalable from 100 to thousands of vias.
         The thermal Problem of a real board is deliberately simple: full copper on every layer (the isolated effect of the vias), the holes as vias at their real positions and
         diameters (a component hole counts as a copper barrel too), one source on the densest window of the board. Real copper patterns enter through `gerber-models`
         and are a second stage (README, limits). Files are read with the independent reader of `gerber-import` (`native_gerber.read_drill`, `layer_bbox`); nothing of a third party is stored here.
"""

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paths                                                                # noqa: E402

sys.path.insert(0, str(paths.GERBER_IMPORT / "lib"))
sys.path.insert(0, str(paths.REPO))

import native_gerber as ng                                                  # noqa: E402
from pcbthermal import Problem                                              # noqa: E402
from pcbthermal.model import Materials                                      # noqa: E402

BOARDS = {
    "alleg": {"files": {"drill": "drill.drl", "box": "F.gbr"}, "layers": 4, "licence": "not stated (numbers only)", "origin": "gerbonara test resources (allegro/)"},
    "storm": {"files": {"drill": "drill.drl", "box": "edge.gbr"}, "layers": 2, "licence": "MIT", "origin": "https://github.com/Chromico/stormduino"},
}


def fetch(name):
    """!
    @brief Download a board with the fetch script of `gerber-import` when its files are not there (needs the network).
    @param name Key of BOARDS.
    @return None.
    """
    d = paths.gerber_data() / name
    if all((d / f).exists() for f in BOARDS[name]["files"].values()):
        return
    sys.path.insert(0, str(paths.GERBER_IMPORT / "scripts"))
    import fetch_boards as fb                                               # noqa: E402  (writes into gerber-import/data of this worktree)
    fb.fetch(name)


def holes_of(name):
    """!
    @brief The plated holes of a downloaded board in board coordinates.
    @param name Key of BOARDS.
    @return tuple (holes, width_mm, height_mm) with holes a list of (x, y, d) in mm from the lower left corner of the board box; coincident holes are counted once.
    @throws FileNotFoundError If the board has not been fetched (run `scripts/fetch_boards.py` of gerber-import or `fetch()`).
    """
    d = paths.gerber_data() / name
    spec = BOARDS[name]["files"]
    drill, box_file = d / spec["drill"], d / spec["box"]
    if not drill.exists() or not box_file.exists():
        raise FileNotFoundError(f"board {name!r} not found in {d}: run gerber-import/scripts/fetch_boards.py {name}")
    x0, y0, x1, y1 = ng.layer_bbox(box_file)
    seen, out = set(), []
    for x, y, dia, plated in ng.read_drill(drill):
        if plated is False:
            continue
        key = (round(x, 3), round(y, 3))
        if key in seen or not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        seen.add(key)
        out.append((x - x0, y - y0, max(dia, 0.1)))
    return out, x1 - x0, y1 - y0


def own_via_field(n_side=10, pad_mm=7.0, ring_vias=24, drill_mm=0.3, board_mm=(60.0, 50.0)):
    """!
    @brief The synthetic via field: an n x n thermal-via array under a square pad at the middle of the board plus a ring of stitching vias.
    @param n_side Vias per side of the array (n_side = 10 gives 100 vias; 30 gives 900).
    @param pad_mm Side of the square pad the array fills, in mm.
    @param ring_vias Number of stitching vias on a circle of radius 20 mm round the middle.
    @param drill_mm Drill diameter of all the vias in mm.
    @param board_mm Board width and height in mm.
    @return tuple (holes, width_mm, height_mm) as `holes_of`.
    """
    w, h = board_mm
    cx, cy = w / 2.0, h / 2.0
    pitch = pad_mm / n_side
    holes = []
    for i in range(n_side):
        for j in range(n_side):
            holes.append((cx + (i - (n_side - 1) / 2.0) * pitch, cy + (j - (n_side - 1) / 2.0) * pitch, drill_mm))
    for k in range(ring_vias):
        a = 2.0 * math.pi * k / max(ring_vias, 1)
        holes.append((cx + 20.0 * math.cos(a), cy + 20.0 * math.sin(a), drill_mm))
    return holes, w, h


def via_array_pitch(n_side, pitch_mm=1.5, drill_mm=0.3, margin_mm=10.0):
    """!
    @brief An n x n array of vias at a fixed pitch on a board that grows with it (the scaling case: the number of cells that the vias touch grows with the number of vias, which a fixed pad does not).
    @param n_side Vias per side.
    @param pitch_mm Pitch in mm.
    @param drill_mm Drill diameter in mm.
    @param margin_mm Bare margin round the array in mm.
    @return tuple (holes, width_mm, height_mm).
    """
    side = (n_side - 1) * pitch_mm + 2.0 * margin_mm
    holes = [(margin_mm + i * pitch_mm, margin_mm + j * pitch_mm, drill_mm) for i in range(n_side) for j in range(n_side)]
    return holes, side, side


def densest_window(holes, size_mm, width, height, step_mm=1.0):
    """!
    @brief Centre of the square window with the most holes.
    @param holes List of (x, y, d).
    @param size_mm Side of the window in mm.
    @param width Board width in mm.
    @param height Board height in mm.
    @param step_mm Step of the search in mm.
    @return tuple (cx, cy, count) in mm.
    """
    pts = np.array([(x, y) for x, y, _ in holes])
    best = (width / 2.0, height / 2.0, -1)
    half = size_mm / 2.0
    for cx in np.arange(half, width - half + 1e-9, step_mm):
        for cy in np.arange(half, height - half + 1e-9, step_mm):
            n = int(np.sum((np.abs(pts[:, 0] - cx) <= half) & (np.abs(pts[:, 1] - cy) <= half)))
            if n > best[2]:
                best = (float(cx), float(cy), n)
    return best


def problem_from_holes(holes, width, height, layers=4, power=3.0, source_mm=8.0, center=None, h_face=10.0, fill_k=0.0, thickness_mm=1.6, copper_um=35.0):
    """!
    @brief The program's Problem for a board: full copper on every layer, one via per hole, a square source on the densest window (or at `center`).
    @param holes List of (x, y, d) in mm.
    @param width Board width in mm.
    @param height Board height in mm.
    @param layers Copper layers (4 for the Allegro board and the own field, 2 for the Stormduino).
    @param power Source power in W.
    @param source_mm Side of the square source in mm.
    @param center Source centre (x, y) in mm, or None for the densest window.
    @param h_face Film coefficient of both faces in W/m2K.
    @param fill_k Fill conductivity of the vias in W/mK (0 = open barrel, 385 = copper fill).
    @param thickness_mm Board thickness in mm.
    @param copper_um Copper thickness of every layer in micrometres.
    @return Problem.
    """
    p = Problem.new(width, height, layers, thickness_mm, copper_um, h_top=h_face, h_bottom=h_face, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, width, height))
    cx, cy = center if center is not None else densest_window(holes, source_mm, width, height)[:2]
    s = source_mm / 2.0
    p.add_heater(1, power, rect=(cx - s, cy - s, cx + s, cy + s))
    for x, y, d in holes:
        p.add_via(x, y, d, fill_k=fill_k)
    return p


def hole_statistics(holes, cell_mm, width, height):
    """!
    @brief How the holes meet a grid: the numbers that decide the cost of the via couplings (no solver).
    @param holes List of (x, y, d).
    @param cell_mm Cell in mm.
    @param width Board width in mm.
    @param height Board height in mm.
    @return dict with n, cells, cells_with_via, max_per_cell, share_cells_shared (cells that hold 2 or more vias), pairs_closer_than (number of via pairs whose footprints overlap,
            i.e. closer than d + 2 cells), nearest_mean (mean nearest-neighbour distance in mm), diameters (dict d -> count).
    """
    nx, ny = max(int(round(width / cell_mm)), 1), max(int(round(height / cell_mm)), 1)
    count = np.zeros((ny, nx), int)
    for x, y, _ in holes:
        count[min(int(y / cell_mm), ny - 1), min(int(x / cell_mm), nx - 1)] += 1
    pts = np.array([(x, y) for x, y, _ in holes])
    d2 = ((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1) if len(pts) <= 4000 else None
    pairs, nearest = 0, float("nan")
    if d2 is not None and len(pts) > 1:
        np.fill_diagonal(d2, np.inf)
        nearest = float(np.sqrt(d2.min(axis=1)).mean())
        reach = np.array([[(a[2] + b[2]) / 2.0 + 2.0 * cell_mm for b in holes] for a in holes])
        pairs = int(np.sum(np.sqrt(d2) < reach) // 2)
    diam = {}
    for _, _, d in holes:
        diam[round(d, 3)] = diam.get(round(d, 3), 0) + 1
    return {"n": len(holes), "cells": nx * ny, "cells_with_via": int((count > 0).sum()), "max_per_cell": int(count.max()), "share_cells_shared": float((count > 1).sum() / max((count > 0).sum(), 1)),
            "pairs_closer_than": pairs, "nearest_mean": nearest, "diameters": diam}
