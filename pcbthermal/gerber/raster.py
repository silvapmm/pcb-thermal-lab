#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file raster.py
@brief Rasterisation of a Gerber layer to one-byte copper coverage (0 to 255) at a chosen pixel, one layer and one tile at a time.
@details The layer is drawn on a boolean canvas at a sub-pixel (pixel / supersample) and every block of supersample x supersample sub-pixels is averaged to the
         coverage of its pixel, so the area of a feature thinner than a pixel is kept. The window is cut into tiles of at most TILE_SUBPIXELS sub-pixels per side, and for
         every tile only the operations whose box meets it are drawn, so the working memory is a constant (a few hundred MB at most) whatever the board and the pixel;
         the only memory that grows with the board is the result, one byte per pixel and layer. The caller draws one layer at a time and keeps the bytes.
         The sample spacing (pixel / supersample) must be finer than the thinnest feature: a line thinner than the spacing is lost or inflated by up to 25 % depending on
         where the samples fall (measured in research/gerber-real-boards README 4.6); `check_sample_spacing` returns the warning and `suggest_pixel_mm` proposes the pixel.
"""

import math
from typing import NamedTuple

import numpy as np


TILE_SUBPIXELS = 2048          # side of a tile in sub-pixels (4 M booleans; the float coordinate grids of a stroke are about 8 times that per array)
DEFAULT_SUPERSAMPLE = 4
BYTES_PER_OP = 600             # measured resident bytes per parsed operation (tuple, aperture reference, attribute id), see tests and the report
WORKING_BYTES_PER_SUBPIXEL = 90  # boolean canvas plus the float64 grids and temporaries of the largest stroke in a tile (measured: CO60 at 0.05 mm peaks at 433 MB resident, 78 MB of it the interpreter)


class Window(NamedTuple):
    """!@brief A rectangle of the board in the Gerber axes: left edge, top edge, width and height (mm). Rows of the raster run from the top edge downwards."""
    x_left: float
    y_top: float
    width: float
    height: float


class RasterEstimate(NamedTuple):
    """!@brief Estimated memory of rasterising layers: the pixels, the bytes that stay (the coverage bytes) and the transient working bytes."""
    pixels_per_layer: int
    held_bytes: int
    working_bytes: int
    peak_bytes: int


def pixel_counts(window, pixel_mm):
    """!
    @brief The number of pixel rows and columns that cover a window.
    @param window   Window (mm).
    @param pixel_mm Pixel size (mm).
    @return tuple (rows, columns), each at least 1.
    """
    return max(int(math.ceil(window.height / pixel_mm - 1e-9)), 1), max(int(math.ceil(window.width / pixel_mm - 1e-9)), 1)


def estimate_raster_bytes(window, pixel_mm, n_layers=1, supersample=DEFAULT_SUPERSAMPLE, n_ops=0):
    """!
    @brief Memory needed to rasterise copper layers, to be checked by the memory guard before anything is drawn.
    @details The coverage is one byte per pixel and layer and stays; the working memory of a tile is constant; a parsed layer costs BYTES_PER_OP per operation
             (pass the operation count of the largest layer, or 0 when it is not known yet).
    @param window      Window (mm).
    @param pixel_mm    Pixel size of the result (mm).
    @param n_layers    Number of layers whose coverage is held at the same time.
    @param supersample Sub-pixels per pixel side.
    @param n_ops       Operations of the largest parsed layer.
    @return RasterEstimate in bytes.
    """
    rows, cols = pixel_counts(window, pixel_mm)
    held = rows * cols * n_layers
    side = min(TILE_SUBPIXELS, max(rows, cols) * supersample)
    working = side * min(TILE_SUBPIXELS, min(rows, cols) * supersample) * WORKING_BYTES_PER_SUBPIXEL
    return RasterEstimate(rows * cols, held, working, held + working + n_ops * BYTES_PER_OP)


def suggest_pixel_mm(thinnest_mm, supersample=DEFAULT_SUPERSAMPLE):
    """!
    @brief The coarsest pixel whose sample spacing is half the thinnest feature (the area of a line is then kept within about 25 % even in the worst alignment).
    @param thinnest_mm Thinnest feature (mm), from `Layer.thinnest_feature_mm`.
    @param supersample Sub-pixels per pixel side.
    @return float Pixel size (mm), or None when the layer has no feature with a width.
    """
    if not thinnest_mm:
        return None
    return supersample * thinnest_mm / 2.0


def check_sample_spacing(layer, pixel_mm, supersample=DEFAULT_SUPERSAMPLE):
    """!
    @brief Warn when the thinnest feature of the layer is not wider than the sample spacing.
    @param layer       Parsed Layer.
    @param pixel_mm    Pixel size (mm).
    @param supersample Sub-pixels per pixel side.
    @return str The warning text (feature, spacing, the pixel that avoids it), or None when the layer is safe.
    """
    thin = layer.thinnest_feature_mm()
    if thin is None:
        return None
    spacing = pixel_mm / supersample
    if thin > spacing:
        return None
    return (f"{layer.name or 'layer'}: the thinnest feature is {thin:.4g} mm, not wider than the sample spacing {spacing:.4g} mm "
            f"(pixel {pixel_mm:.4g} mm / {supersample}); its area is lost or inflated by up to 25 % depending on where the samples fall; "
            f"use a pixel of {suggest_pixel_mm(thin, supersample):.4g} mm or finer")


class Canvas:
    """!@brief A boolean mask of a window of the board that objects are drawn onto (dark adds, clear removes)."""

    def __init__(self, x_left, y_top, nx, ny, pix_mm, col0=0, row0=0):
        """!
        @brief Create an empty canvas.
        @details The sample coordinates are x_left + (global column + 0.5) pix, with the global column = local column + col0, so a tile samples exactly the
                 same points as the whole window would (a sample on an edge falls on the same side whatever the tiling).
        @param x_left X of the left edge of the whole window (mm).
        @param y_top  Y of the top edge of the whole window (mm).
        @param nx     Columns of this canvas (sub-pixels).
        @param ny     Rows of this canvas (sub-pixels).
        @param pix_mm Sub-pixel size (mm).
        @param col0   Global column of the first column of this canvas.
        @param row0   Global row of the first row of this canvas.
        """
        self.x0, self.y0, self.pix = x_left, y_top, pix_mm
        self.nx, self.ny = nx, ny
        self.col0, self.row0 = col0, row0
        self.mask = np.zeros((ny, nx), bool)

    def _window(self, xmin, xmax, ymin, ymax):
        """!
        @brief Pixel index ranges and centre coordinates of a bounding box clipped to the canvas.
        @param xmin Left of the box (mm).
        @param xmax Right of the box (mm).
        @param ymin Bottom of the box (mm).
        @param ymax Top of the box (mm).
        @return None when the box is outside, else (row slice, column slice, X centres, Y centres) with X and Y as 2D arrays.
        """
        j0 = max(int(math.floor((xmin - self.x0) / self.pix - 0.5)) - self.col0, 0)
        j1 = min(int(math.ceil((xmax - self.x0) / self.pix - 0.5)) + 1 - self.col0, self.nx)
        i0 = max(int(math.floor((self.y0 - ymax) / self.pix - 0.5)) - self.row0, 0)
        i1 = min(int(math.ceil((self.y0 - ymin) / self.pix - 0.5)) + 1 - self.row0, self.ny)
        if j0 >= j1 or i0 >= i1:
            return None
        xs = self.x0 + (np.arange(j0, j1) + self.col0 + 0.5) * self.pix
        ys = self.y0 - (np.arange(i0, i1) + self.row0 + 0.5) * self.pix
        X, Y = np.meshgrid(xs, ys)
        return slice(i0, i1), slice(j0, j1), X, Y

    def _apply(self, sl, inside, dark):
        """!
        @brief Add or remove the pixels of a shape.
        @param sl     Tuple (row slice, column slice).
        @param inside Boolean array of the shape on that window.
        @param dark   True to add copper, False to clear.
        """
        view = self.mask[sl[0], sl[1]]
        if dark:
            view |= inside
        else:
            view &= ~inside

    def flash(self, ap, x, y, dark):
        """!
        @brief Draw an aperture at a point.
        @param ap   Aperture.
        @param x    X (mm).
        @param y    Y (mm).
        @param dark Polarity.
        """
        r = ap.radius
        w = self._window(x - r, x + r, y - r, y + r)
        if w:
            self._apply(w[:2], ap.inside(w[2] - x, w[3] - y), dark)

    def stroke(self, ap, x0, y0, x1, y1, dark):
        """!
        @brief Draw a straight line with an aperture (round aperture: a capsule; other apertures: the convex hull of the two positions).
        @param ap   Aperture.
        @param x0   Start X (mm).
        @param y0   Start Y (mm).
        @param x1   End X (mm).
        @param y1   End Y (mm).
        @param dark Polarity.
        """
        r = ap.radius
        w = self._window(min(x0, x1) - r, max(x0, x1) + r, min(y0, y1) - r, max(y0, y1) + r)
        if not w:
            return
        X, Y = w[2], w[3]
        if ap.kind == "C":
            dx, dy = x1 - x0, y1 - y0
            L2 = dx * dx + dy * dy
            t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L2, 0.0, 1.0) if L2 > 0 else np.zeros_like(X)
            inside = (X - (x0 + t * dx)) ** 2 + (Y - (y0 + t * dy)) ** 2 <= r * r
        else:
            # Convex hull of the aperture at both ends: sample the segment densely and take the union of the apertures
            n = max(int(math.hypot(x1 - x0, y1 - y0) / (self.pix * 0.5)) + 1, 2)
            inside = np.zeros(X.shape, bool)
            for s in np.linspace(0.0, 1.0, n):
                inside |= ap.inside(X - (x0 + s * (x1 - x0)), Y - (y0 + s * (y1 - y0)))
        self._apply(w[:2], inside, dark)

    def polygon(self, pts, dark):
        """!
        @brief Fill a closed polygon (even-odd rule, which equals the non-zero rule for the simple contours of a Gerber region).
        @param pts  Array (n, 2) of vertices (mm).
        @param dark Polarity.
        """
        pts = np.asarray(pts, float)
        if len(pts) < 3:
            return
        w = self._window(pts[:, 0].min(), pts[:, 0].max(), pts[:, 1].min(), pts[:, 1].max())
        if not w:
            return
        rows, cols = w[0], w[1]
        nrow, ncol = rows.stop - rows.start, cols.stop - cols.start
        x_a, y_a = pts[:, 0], pts[:, 1]
        x_b, y_b = np.roll(x_a, -1), np.roll(y_a, -1)
        keep = y_a != y_b
        x_a, y_a, x_b, y_b = x_a[keep], y_a[keep], x_b[keep], y_b[keep]
        lo, hi = np.minimum(y_a, y_b), np.maximum(y_a, y_b)
        yc = self.y0 - (np.arange(rows.start, rows.stop) + self.row0 + 0.5) * self.pix
        # Only the edges that overlap the rows of this window matter (a big pour has thousands of edges, a tile a few)
        near = (hi >= yc.min()) & (lo <= yc.max())
        x_a, y_a, x_b, y_b, lo, hi = x_a[near], y_a[near], x_b[near], y_b[near], lo[near], hi[near]
        inside = np.zeros((nrow, ncol), bool)
        for k in range(nrow):                                  # Scanline: crossings of the row centre with the edges, then fill between pairs
            sel = (lo <= yc[k]) & (yc[k] < hi)
            if not sel.any():
                continue
            xs = np.sort(x_a[sel] + (yc[k] - y_a[sel]) * (x_b[sel] - x_a[sel]) / (y_b[sel] - y_a[sel]))
            if len(xs) % 2:
                xs = xs[:-1]
            j = np.ceil((xs - self.x0) / self.pix - 0.5).astype(int) - self.col0 - cols.start        # first pixel centre at or right of every crossing
            j = np.clip(j, 0, ncol)
            diff = np.zeros(ncol + 1, int)
            np.add.at(diff, j[0::2], 1)
            np.add.at(diff, j[1::2], -1)
            inside[k] = np.cumsum(diff[:ncol]) > 0
        self._apply((rows, cols), inside, dark)


def draw_ops(layer, canvas, indices):
    """!
    @brief Draw selected operations of a layer on a canvas, in file order.
    @param layer   Parsed Layer.
    @param canvas  Canvas.
    @param indices Sorted operation indices to draw.
    """
    ops = layer.ops
    for k in indices:
        kind, dark, a = ops[k]
        if kind == "flash":
            canvas.flash(a[0], a[1], a[2], dark)
        elif kind == "stroke":
            canvas.stroke(a[0], a[1], a[2], a[3], a[4], dark)
        else:
            canvas.polygon(a, dark)


def rasterize(layer, window, pixel_mm, supersample=DEFAULT_SUPERSAMPLE, nets=None):
    """!
    @brief Copper coverage of a layer on a window: one byte per pixel, 0 (no copper) to 255 (full pixel).
    @details Drawn tile by tile at the sub-pixel pixel_mm / supersample (pixel centres sampled), then every supersample x supersample block is averaged. The window is
             pixel_counts(window, pixel_mm) pixels; its last row and column are drawn up to the pixel edge, copper beyond the window is clipped. An image polarity
             IPNEG inverts the picture inside the window.
    @param layer      Parsed Layer.
    @param window     Window (mm), rows from the top edge downwards.
    @param pixel_mm   Pixel size (mm).
    @param supersample Sub-pixels per pixel side (1 gives the binary pixel-centre mask scaled to 0 or 255).
    @param nets       Optional collection of net names (TO.N): only the dark objects of those nets are drawn, clear objects always (an approximation).
    @return numpy.ndarray uint8 array (rows, columns).
    """
    rows, cols = pixel_counts(window, pixel_mm)
    out = np.zeros((rows, cols), np.uint8)
    if not layer.ops:
        return out
    boxes = layer.op_boxes()
    keep = None
    if nets is not None:
        wanted = set(nets)
        nets_of = np.array([layer.attr_table[a].net in wanted for a in layer.attr_ids])
        dark = np.array([op[1] for op in layer.ops])
        keep = ~dark | nets_of
    sub = pixel_mm / supersample
    tile_px = max(TILE_SUBPIXELS // supersample, 1)
    scale = 255.0 / (supersample * supersample)
    for i0 in range(0, rows, tile_px):
        i1 = min(i0 + tile_px, rows)
        for j0 in range(0, cols, tile_px):
            j1 = min(j0 + tile_px, cols)
            x_left = window.x_left + j0 * pixel_mm              # box of the tile, for choosing the operations
            y_top = window.y_top - i0 * pixel_mm
            x_right = window.x_left + j1 * pixel_mm
            y_bottom = window.y_top - i1 * pixel_mm
            # Operations whose box meets the tile (kept in file order: the order decides dark and clear)
            hit = (boxes[:, 0] <= x_right) & (boxes[:, 2] >= x_left) & (boxes[:, 1] <= y_top) & (boxes[:, 3] >= y_bottom)
            if keep is not None:
                hit &= keep
            idx = np.nonzero(hit)[0]
            if idx.size == 0 and not layer.negative:
                continue
            cv = Canvas(window.x_left, window.y_top, (j1 - j0) * supersample, (i1 - i0) * supersample, sub, j0 * supersample, i0 * supersample)
            draw_ops(layer, cv, idx)
            if layer.negative:                                                       # image polarity: negative
                cv.mask = ~cv.mask
            m = cv.mask
            if supersample > 1:
                counts = m.reshape(i1 - i0, supersample, j1 - j0, supersample).sum(axis=(1, 3), dtype=np.uint16)
            else:
                counts = m.astype(np.uint16)
            out[i0:i1, j0:j1] = np.rint(counts * scale).astype(np.uint8)
    return out


def coverage_area_mm2(coverage, pixel_mm):
    """!
    @brief The copper area of a coverage raster.
    @param coverage Coverage array (uint8, 0 to 255).
    @param pixel_mm Pixel size (mm).
    @return float Area in mm2 (sum of the coverage over 255 times the pixel area).
    """
    return float(coverage.sum(dtype=np.float64)) / 255.0 * pixel_mm * pixel_mm


def window_of(bbox, margin_mm=0.0):
    """!
    @brief A window that covers a bounding box.
    @param bbox      Tuple (xmin, ymin, xmax, ymax) in mm.
    @param margin_mm Margin added on every side (mm).
    @return Window.
    @throws ValueError If the bounding box is None.
    """
    if bbox is None:
        raise ValueError("the layer draws nothing: no window")
    x0, y0, x1, y1 = bbox
    return Window(x0 - margin_mm, y1 + margin_mm, (x1 - x0) + 2 * margin_mm, (y1 - y0) + 2 * margin_mm)
