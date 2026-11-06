#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file variants.py
@brief Variants of an imported board for the error decomposition: the same program, the same cell, the imported copper replaced by drawn zones of the same average fill, and the local measures of the copper around a part.
@details The imported masks of the RP2040 (or any library board) are read with the program's own reader. A variant keeps vias, parts and stack-up and swaps only the copper:
         "imported" (faces mapping, as the FVM runs), "fill" (same masks, arithmetic cell fill), "uniform" (one zone per imported layer with the layer-average fill) and
         "tiles" (a zone per square tile of side T mm with the fill of the mask inside the tile). Local measures (fill inside a square of half-side R, distance to the
         nearest copper-free pixel, copper under the part) are read from the same masks. Nothing here edits the program.
"""

import copy
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pcbthermal import copper  # noqa: E402
from pcbthermal.gui.import_session import ImportSession  # noqa: E402


def open_board(name, cell_mm, powers=None):
    """!
    @brief Open a library board in an import session and build its problem with 1 W in every heat source.
    @param name Folder name under PCBT_REAL_BOARDS (rp2040, oswlight, co60, ...).
    @param cell_mm Cell of the import (mm).
    @param powers Optional list of designators to power (None: every part that is a heat source).
    @return (ImportSession, Problem).
    """
    path = Path(os.environ["PCBT_REAL_BOARDS"]) / name
    sx = ImportSession()
    sx.set_files(path)
    sx.load()
    sx.cell_mm = cell_mm
    for p in sx.parts():
        if powers is None or p.designator in powers:
            sx.set_part(p.designator, power=1.0)
    return sx, sx.build_problem()


def only_heater(problem, name):
    """!
    @brief A copy of the problem that keeps one heater (1 W) and drops the others.
    @param problem Problem with all the heaters.
    @param name Heater name (designator).
    @return Problem or None when the name is not a heater.
    """
    q = copy.deepcopy(problem)
    q.heaters = [h for h in q.heaters if h.name == name]
    return q if q.heaters else None


def _layer_zones(q, layer, tile_mm):
    """!
    @brief Replace the zones of one imported layer by tiles of the mask average (tile_mm None: one tile, the whole board).
    @param q Problem (changed in place).
    @param layer 0-based layer.
    @param tile_mm Tile side in mm, or None for the whole board.
    @return None.
    """
    src = copper.CopperSource.of(q)
    ras = src.raster(layer).astype(float) / 255.0
    pix_mm = src.pix * 1e3
    rows, cols = ras.shape
    W, H = q.board.width * 1e3, q.board.height * 1e3
    # Pixels on the board: the whole box, or the inside of the outline (the average must not count the bare space off the board)
    on = np.ones((rows, cols), bool)
    if q.board.has_outline():
        from matplotlib.path import Path as MPath
        xs = (np.arange(cols) + 0.5) * pix_mm
        ys = H - (np.arange(rows) + 0.5) * pix_mm
        X, Y = np.meshgrid(xs, ys)
        on = MPath(np.asarray(q.board.outline) * 1e3).contains_points(np.column_stack([X.ravel(), Y.ravel()])).reshape(rows, cols)
    if tile_mm is None:
        # One zone over the whole box at the mean fill of the mask on the board
        q.add_zone(layer + 1, rect=(0, 0, W, H), fill=float(ras[on].mean()))
        return
    n = max(1, int(round(tile_mm / pix_mm)))
    for r0 in range(0, rows, n):
        for c0 in range(0, cols, n):
            o = on[r0:r0 + n, c0:c0 + n]
            if not o.any():
                continue                                           # Tile off the board
            f = float(ras[r0:r0 + n, c0:c0 + n][o].mean())
            if f <= 0.0:
                continue                                           # No copper in the tile: bare laminate
            # rows run from the top of the board
            x0, x1 = c0 * pix_mm, min((c0 + n) * pix_mm, W)
            y1, y0 = H - r0 * pix_mm, max(H - (r0 + n) * pix_mm, 0.0)
            q.add_zone(layer + 1, rect=(x0, y0, x1, y1), fill=min(f, 1.0))


def variant(problem, kind, tile_mm=None):
    """!
    @brief A copy of the problem with the copper of the imported layers replaced.
    @param problem Problem with imported copper.
    @param kind "imported", "fill", "uniform", "tiles" or "novias" (imported copper, no vias).
    @param tile_mm Tile side for "tiles" (mm).
    @return Problem.
    @throws ValueError For an unknown kind.
    """
    q = copy.deepcopy(problem)
    if kind == "imported":
        return q
    if kind == "novias":
        q.vias = []
        return q
    if kind == "fill":
        q.imported = copy.copy(q.imported)
        q.imported.mapping = "fill"
        return q
    if kind in ("uniform", "tiles"):
        layers = copper.CopperSource.of(q).layers
        for lay in layers:
            _layer_zones(q, lay, None if kind == "uniform" else tile_mm)
        q.imported = None                                           # the zones are now the copper
        return q
    raise ValueError("unknown variant " + kind)


def local_measures(problem, name, radii=(2.0, 5.0, 10.0), layer=0):
    """!
    @brief Local copper measures around a part, read from the mask of one layer.
    @param problem Problem with imported copper and the heater called name.
    @param name Heater name.
    @param radii Half-sides in mm of the squares in which the copper fraction is read.
    @param layer 0-based layer of the mask.
    @return dict: side_mm (sqrt of the area), area_mm2, under (mean coverage inside the polygon), fill_R (per radius), dist_bare_mm (centre to the nearest pixel under 0.5), bottom_under, cx_mm, cy_mm.
    """
    h = next(h for h in problem.heaters if h.name == name)
    src = copper.CopperSource.of(problem)
    ras = src.raster(layer).astype(np.float32) / 255.0
    pix = src.pix * 1e3
    rows, cols = ras.shape
    H = problem.board.height * 1e3
    poly = h.polygon * 1e3
    cx, cy = poly.mean(axis=0)
    out = {"cx_mm": float(cx), "cy_mm": float(cy)}
    x = (np.arange(cols) + 0.5) * pix
    y = H - (np.arange(rows) + 0.5) * pix
    X, Y = np.meshgrid(x, y)

    def square(r):
        m = (abs(X - cx) <= r) & (abs(Y - cy) <= r)
        return m

    # Area of the polygon (shoelace) and the copper inside its bounding box (pads are the part's own copper)
    xs, ys = poly[:, 0], poly[:, 1]
    area = 0.5 * abs(np.dot(xs, np.roll(ys, -1)) - np.dot(ys, np.roll(xs, -1)))
    out["area_mm2"] = float(area)
    out["side_mm"] = float(np.sqrt(area))
    bb = (X >= xs.min()) & (X <= xs.max()) & (Y >= ys.min()) & (Y <= ys.max())
    out["under"] = float(ras[bb].mean()) if bb.any() else float("nan")
    for r in radii:
        m = square(r)
        out["fill_%g" % r] = float(ras[m].mean())
    # Distance to the nearest copper-free pixel (coverage < 0.5), searched in a 15 mm square
    m = square(15.0) & (ras < 0.5)
    out["dist_bare_mm"] = float(np.sqrt((X[m] - cx) ** 2 + (Y[m] - cy) ** 2).min()) if m.any() else 15.0
    # Bottom layer under the part (the other side of the board)
    if len(src.layers) > 1:
        rb = src.raster(src.layers[-1]).astype(np.float32) / 255.0
        out["bottom_5"] = float(rb[square(5.0)].mean())
    return out


def window_and_pad(problem, name, half_mm, layer=0):
    """!
    @brief The coverage window around a part and the pixels of the part's footprint, for the constriction factor.
    @param problem Problem with imported copper and the heater called name.
    @param name Heater name.
    @param half_mm Half side of the square window in mm.
    @param layer 0-based layer of the mask.
    @return (cov, pad): float coverage 0..1 of the window and bool mask of the pixels inside the footprint polygon that carry copper (coverage >= 0.5).
    """
    from matplotlib.path import Path as MPath
    h = next(h for h in problem.heaters if h.name == name)
    src = copper.CopperSource.of(problem)
    ras = src.raster(layer).astype(np.float32) / 255.0
    pix = src.pix * 1e3
    rows, cols = ras.shape
    H = problem.board.height * 1e3
    poly = h.polygon * 1e3
    cx, cy = poly.mean(axis=0)
    c0 = int(round((cx - half_mm) / pix)); c1 = int(round((cx + half_mm) / pix))
    r0 = int(round((H - cy - half_mm) / pix)); r1 = int(round((H - cy + half_mm) / pix))
    c0, r0 = max(c0, 0), max(r0, 0)
    c1, r1 = min(c1, cols), min(r1, rows)
    win = ras[r0:r1, c0:c1]
    x = (np.arange(c0, c1) + 0.5) * pix
    y = H - (np.arange(r0, r1) + 0.5) * pix
    X, Y = np.meshgrid(x, y)
    inside = MPath(poly).contains_points(np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape)
    return win.astype(float), inside & (win >= 0.5)
