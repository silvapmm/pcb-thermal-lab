"""!
@file readers.py
@brief One interface for the Gerber and Excellon reading used by the studies: the independent NumPy reader (default) or gerbonara + shapely (to cross-check).
@details Choose with the environment variable GERBER_READER = "native" (default, no third-party geometry library) or "shapely" (needs gerbonara and shapely).
         The studies only call render(), box() and holes(); the numbers of the README are produced with the default reader.
"""

import os
from pathlib import Path

import native_gerber as ng

from paths import DATA                                            # downloaded boards (see scripts/fetch_boards.py); git-ignored

READER = os.environ.get("GERBER_READER", "native")
_geometry = {}                                        # shapely route: the union of a layer, computed once per file


def render(path, x_left, y_top, width_mm, height_mm, pix_mm):
    """!
    @brief Copper mask of a window of a Gerber layer (pixel centres sampled).
    @param path Gerber file path.
    @param x_left X of the left edge of the window (mm).
    @param y_top Y of the top edge of the window (mm).
    @param width_mm Window width (mm).
    @param height_mm Window height (mm).
    @param pix_mm Pixel size (mm).
    @return Boolean array (rows, cols).
    """
    if READER == "native":
        return ng.render(path, x_left, y_top, width_mm, height_mm, pix_mm)
    import gerber_geometry as gg
    key = str(path)
    if key not in _geometry:
        _geometry[key] = gg.load_copper(path)[0]
    return gg.sample_mask(_geometry[key], x_left, y_top, width_mm, height_mm, pix_mm) > 0.5


def box(edge_path, copper_path):
    """!
    @brief Board box: the outline layer when there is one, else the box of the copper layer.
    @param edge_path Outline Gerber path or None.
    @param copper_path Copper Gerber path (fallback).
    @return Tuple (x0, y0, x1, y1) in mm.
    """
    if READER == "native":
        for p in (edge_path, copper_path):
            if p is not None:
                b = ng.layer_bbox(p)
                if b and b[2] - b[0] > 1 and b[3] - b[1] > 1:
                    return b
        raise ValueError("no usable board outline")
    import gerber_geometry as gg
    key = str(copper_path)
    if key not in _geometry:
        _geometry[key] = gg.load_copper(copper_path)[0]
    return gg.board_bbox(edge_path, _geometry[key].bounds) if edge_path else _geometry[key].bounds


def holes(path):
    """!
    @brief Drilled holes of an Excellon file as (x, y, diameter) in mm.
    @param path Excellon file path.
    @return List of tuples.
    """
    if READER == "native":
        return [(x, y, d) for x, y, d, _ in ng.read_drill(path)]
    import gerber_geometry as gg
    return gg.drill_holes(path)


def board_files(name):
    """!
    @brief Paths of a downloaded board (see fetch_boards.py).
    @param name Board key (for example "storm").
    @return Dict role -> Path for the files that exist: "F" (top copper), "L2".."L5" (inner layers, in stack order), "B" (bottom copper), "edge", "drill".
    """
    d = DATA / name
    roles = (("F", "F.gbr"), ("L2", "L2.gbr"), ("L3", "L3.gbr"), ("L4", "L4.gbr"), ("L5", "L5.gbr"), ("B", "B.gbr"), ("edge", "edge.gbr"), ("drill", "drill.drl"))
    return {role: d / f for role, f in roles if (d / f).exists()}
