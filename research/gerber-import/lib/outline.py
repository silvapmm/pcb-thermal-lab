#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file outline.py
@brief The board outline from the profile layer (Edge.Cuts) of a Gerber set: the shape of the board as a mask and as a polygon, with the cut-outs, and a check that the contour is closed.
@details The profile layer draws the outline as strokes (a thin aperture along the contour; the fabricator cuts along the centre line of the stroke), so the board is the region the strokes enclose. The independent reader draws the strokes on the pixel grid, and the board is found by the parity of the number of stroke crossings along every row (an even-odd rule: inside one loop is board, inside a loop inside it is a cut-out), which also handles slots and holes without chaining the segments. A contour that is not closed (a gap between two segments, a file that stores a filled polygon, a stray line) cannot be told apart by parity alone, so the mask is compared with the region the strokes fully enclose (holes of the stroke mask filled): where parity says board and the strokes do not enclose it, the contour leaks and the result is flagged. The polygon is the contour of the board mask simplified with the Douglas-Peucker rule.
         Research code (README 4.47); nothing in the program uses it yet.
"""

import re

import numpy as np
from scipy import ndimage

import native_gerber as ng


def prepare(text, pix):
    """!
    @brief Give a zero-width circular aperture a width of one and a half pixel, so that a profile drawn with a zero-size aperture (obsolete but still written by some CAD tools) leaves a visible stroke.
    @param text Gerber text of the profile layer.
    @param pix Pixel size (mm).
    @return str The text with `C,0` apertures widened.
    """
    inch = "%MOIN" in text
    width = 1.5 * pix / (25.4 if inch else 1.0)
    return re.sub(r"(%ADD\d+C,)0(?:\.0*)?(\*%)", lambda m: f"{m.group(1)}{width:.6f}{m.group(2)}", text)


def widths(text):
    """!
    @brief The distinct widths (in the file's unit) of the circular apertures that the file defines.
    @param text Gerber text.
    @return list of float, sorted.
    """
    return sorted({float(m.group(1)) for m in re.finditer(r"%ADD\d+C,([0-9.]+)", text)})


def stroke_mask(text, window, pix):
    """!
    @brief The strokes of a profile layer on the pixel grid.
    @param text Gerber text of the profile layer.
    @param window (x_left, y_top, width, height) in mm.
    @param pix Pixel size (mm).
    @return Boolean array (rows, cols), True where the layer has copper-like ink.
    """
    cv = ng.Canvas(window[0], window[1], window[2], window[3], pix)
    ng.Layer(text).draw(cv)
    return cv.mask


def _parity(strokes):
    """!
    @brief The even-odd region along the rows of a stroke mask: a pixel is inside when an odd number of runs of stroke pixels lie to its left.
    @param strokes Boolean array.
    @return Boolean array, True for background pixels with an odd number of runs to their left.
    """
    starts = strokes & ~np.concatenate([np.zeros((strokes.shape[0], 1), bool), strokes[:, :-1]], axis=1)
    return (np.cumsum(starts, axis=1) % 2 == 1) & ~strokes


def board_mask(strokes):
    """!
    @brief The board region enclosed by the strokes and whether the contour is closed.
    @details The background (pixels without stroke) is split into connected pieces. The piece that reaches the border of the window is the outside. Every other piece is either board or a cut-out, which the even-odd rule tells: along the rows and along the columns, a piece lies inside an odd number of loops when most of its pixels have an odd number of stroke runs on one side. Each of the two directions is wrong only on the few rows (columns) that run along a stroke, so a piece is decided by the votes of both. The contour is closed when almost no pixel that both directions call board is connected to the outside: a gap between two segments, a filled polygon written as a region or a stray line lets the background through.
    @param strokes Boolean array of the strokes.
    @return tuple (board mask without the stroke band, closed flag, number of board-like pixels connected to the outside).
    """
    from_rows, from_cols = _parity(strokes), _parity(strokes.T).T
    lab, n = ndimage.label(~strokes)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    outside = np.isin(lab, border[border > 0])
    both = from_rows & from_cols
    board = np.zeros_like(strokes)
    if n:
        idx = np.arange(1, n + 1)
        votes = ndimage.mean(from_rows.astype(float), lab, idx) + ndimage.mean(from_cols.astype(float), lab, idx)
        is_board = (votes > 1.0) & ~np.isin(idx, border)
        board = np.isin(lab, idx[is_board])
    leaked = int((both & outside).sum())
    closed = bool(board.any()) and leaked < 0.01 * max(int(board.sum()), 1)
    return (board if closed else both), closed, leaked


def simplify(points, tol):
    """!
    @brief Douglas-Peucker simplification of a polyline.
    @param points Array (n, 2).
    @param tol Largest distance (same unit as the points) between the polyline and the result.
    @return numpy.ndarray The kept vertices.
    """
    pts = np.asarray(points, float)
    if len(pts) < 3:
        return pts
    keep = np.zeros(len(pts), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        seg = pts[b] - pts[a]
        norm = np.hypot(*seg)
        idx = np.arange(a + 1, b)
        if idx.size == 0:
            continue
        rel = pts[idx] - pts[a]
        d = np.abs(rel[:, 0] * seg[1] - rel[:, 1] * seg[0]) / norm if norm > 0 else np.hypot(rel[:, 0], rel[:, 1])
        k = int(np.argmax(d))
        if d[k] > tol:
            keep[idx[k]] = True
            stack += [(a, idx[k]), (idx[k], b)]
    return pts[keep]


def polygons(mask, window, pix, tol_px=0.7):
    """!
    @brief The contours of a board mask as polygons in millimetres (the outer contour first, cut-outs after), simplified.
    @param mask Boolean board mask.
    @param window (x_left, y_top, width, height) in mm.
    @param pix Pixel size (mm).
    @param tol_px Simplification tolerance in pixels.
    @return list of numpy arrays (n, 2) of (x, y) in the Gerber axes.
    """
    from contourpy import contour_generator
    lines = contour_generator(z=np.pad(mask.astype(float), 1)).lines(0.5)
    out = []
    for ln in lines:
        s = simplify(ln - 1.0, tol_px)                    # padding removed; contourpy gives (x = column, y = row)
        out.append(np.column_stack([window[0] + (s[:, 0] + 0.5) * pix, window[1] - (s[:, 1] + 0.5) * pix]))
    return sorted(out, key=lambda p: -abs(0.5 * np.sum(p[:-1, 0] * p[1:, 1] - p[1:, 0] * p[:-1, 1])))


def area(poly):
    """!
    @brief Area of a closed polygon.
    @param poly Array (n, 2).
    @return float Area (shoelace), unsigned.
    """
    x, y = poly[:, 0], poly[:, 1]
    return float(abs(0.5 * np.sum(x[:-1] * y[1:] - x[1:] * y[:-1])))
