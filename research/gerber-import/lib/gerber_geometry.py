#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file gerber_geometry.py
@brief Gerber copper layer -> exact vector geometry (shapely) -> centre-sampled copper mask.
@details Research code for the Gerber import (see README.md in this folder). Not part of the program.
         Every Gerber primitive (draw, flash, region) becomes a shapely polygon; the polarity-aware union of a layer keeps the holes
         and the islands exactly. The mask is what a raster of a given pixel size sees: one sample at every pixel centre.
         The parser is gerbonara (Apache-2.0).
"""

import warnings

import numpy as np

warnings.simplefilter("ignore")                       # gerbonara warns about harmless header quirks of some CAD tools

import shapely
from gerbonara import ExcellonFile, GerberFile
from gerbonara import graphic_primitives as gp
from gerbonara.utils import MM
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

ARC_ERROR_MM = 1e-3                           # largest distance (mm) between an arc and the chords that replace it (gerbonara's default is 0.01)

from readers import DATA, board_files        # noqa: E402,F401  (the path helpers live in readers.py, which needs no third-party geometry library)


def primitive_polygon(p):
    """!
    @brief One gerbonara graphic primitive as a shapely polygon.
    @param p A gerbonara primitive (Line, Arc, Circle, Rectangle or ArcPoly), in millimetres.
    @return shapely polygon, or None for a primitive that has no area (or an unknown kind).
    """
    if isinstance(p, gp.Line):
        # A draw is a stroke with round caps; a zero-length draw is a round dot
        if (p.x1, p.y1) == (p.x2, p.y2):
            return Point(p.x1, p.y1).buffer(p.width / 2, quad_segs=16)
        return LineString([(p.x1, p.y1), (p.x2, p.y2)]).buffer(p.width / 2, cap_style=1, quad_segs=16)
    if isinstance(p, gp.Circle):
        return Point(p.x, p.y).buffer(p.r, quad_segs=16)
    if isinstance(p, gp.Rectangle):
        r = box(p.x - p.w / 2, p.y - p.h / 2, p.x + p.w / 2, p.y + p.h / 2)
        return affinity.rotate(r, p.rotation, origin=(p.x, p.y), use_radians=True)
    if isinstance(p, gp.Arc):
        # A stroked arc (a G02/G03 draw): gerbonara describes it as a band between two arcs with round ends; it was ignored here until the pixel
        # comparison of README 4.45 found 123 mm2 of circular tracks missing from the vector reference of our own board
        p = p.to_arc_poly()
    if isinstance(p, gp.ArcPoly):
        try:
            p = p.approximate_arcs(max_error=ARC_ERROR_MM)   # arcs become short chords, at most ARC_ERROR_MM from the true arc
        except Exception:                             # older gerbonara: keep the vertices as they are
            pass
        pts = list(p.outline)
        return Polygon(pts).buffer(0) if len(pts) >= 3 else None    # buffer(0) repairs self-touching rings
    return None


def load_copper(path):
    """!
    @brief Polarity-aware union of the primitives of a Gerber copper file, in file order.
    @details Consecutive primitives of the same polarity are unioned in one batch (much faster than one by one); a polarity change applies the
             batch: dark adds copper, clear removes it, exactly as a photoplotter does.
    @param path Gerber file path.
    @return Tuple (shapely geometry in mm, dict with the number of primitives and of clear primitives).
    """
    layer = GerberFile.open(str(path))
    state = {"cur": None, "batch": [], "dark": True}

    def flush():
        """!@brief Apply the pending batch to the running geometry. @return None."""
        if not state["batch"]:
            return
        u = unary_union(state["batch"])
        state["cur"] = u if state["cur"] is None else (state["cur"].union(u) if state["dark"] else state["cur"].difference(u))
        state["batch"] = []

    n = clear = 0
    for obj in layer.objects:
        for p in obj.to_primitives(unit=MM):
            q = primitive_polygon(p)
            if q is None or q.is_empty:
                continue
            n += 1
            if p.polarity_dark != state["dark"]:
                flush()
                state["dark"] = p.polarity_dark
            clear += not p.polarity_dark
            state["batch"].append(q)
    flush()
    return state["cur"], {"primitives": n, "clear": clear}


def board_bbox(edge_path, fallback):
    """!
    @brief Bounding box of the board outline file, or a fallback when it is missing or empty.
    @param edge_path Path of the outline Gerber (may not exist).
    @param fallback Tuple (x0, y0, x1, y1) in mm used when the outline cannot be read.
    @return Tuple (x0, y0, x1, y1) in mm.
    """
    try:
        (x0, y0), (x1, y1) = GerberFile.open(str(edge_path)).bounding_box(MM)
        if x1 - x0 > 1 and y1 - y0 > 1:
            return x0, y0, x1, y1
    except Exception:
        pass
    return fallback


def sample_mask(geometry, x_left, y_top, width_mm, height_mm, pix_mm, aa=1):
    """!
    @brief Coverage of a window by sampling pixel centres inside the exact geometry (holes handled).
    @param geometry shapely geometry in mm.
    @param x_left X of the left edge of the window (mm).
    @param y_top Y of the top edge of the window (mm; image row 0 is the top).
    @param width_mm Window width (mm).
    @param height_mm Window height (mm).
    @param pix_mm Pixel size (mm).
    @param aa 1 = one sample per pixel (binary); n > 1 = n x n samples per pixel, averaged (anti-aliased coverage in 0..1).
    @return numpy.ndarray (rows, cols) of float in 0..1.
    """
    nx, ny = int(round(width_mm / pix_mm)), int(round(height_mm / pix_mm))
    xs = x_left + (np.arange(nx * aa) + 0.5) * pix_mm / aa
    ys = y_top - (np.arange(ny * aa) + 0.5) * pix_mm / aa
    X, Y = np.meshgrid(xs, ys)
    shapely.prepare(geometry)
    a = shapely.contains_xy(geometry, X.ravel(), Y.ravel()).reshape(X.shape).astype(float)
    if aa > 1:
        a = a.reshape(ny, aa, nx, aa).mean(axis=(1, 3))
    return a


def drill_holes(path):
    """!
    @brief Holes of an Excellon file as (x, y, diameter) in mm; a routed slot is one hole at its middle.
    @param path Excellon file path.
    @return List of tuples.
    """
    out = []
    for o in ExcellonFile.open(str(path)).objects:
        k = 25.4 if getattr(o, "unit", "mm") in ("in", "inch") else 1.0          # gerbonara keeps the unit of the file
        if hasattr(o, "x"):
            out.append((o.x * k, o.y * k, o.tool.diameter * k))
        else:
            out.append(((o.x1 + o.x2) / 2 * k, (o.y1 + o.y2) / 2 * k, o.tool.diameter * k))
    return out
