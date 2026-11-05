#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file copper.py
@brief Imported copper: the masks of an import turned into the cell fill and the in-plane face conductances of the FVM and FDM grids, and the import itself (Gerber rasters to a Problem).
@details The program draws copper as zones with a fill fraction; a real board is a coverage mask per layer (one byte per pixel, `pcbthermal.gerber.raster`). The arithmetic fill
         fraction of a cell reads 10 to 30 % too cool on real copper (README 4.1 of `research/gerber-real-boards`), because the heat flows in the copper, not in the average of
         copper and laminate. The default mapping here is the flow-based FACES (transmissibility upscaling): for every pair of neighbouring cells a local conduction problem
         on the pixels between the two cell centres gives the face conductance.
         Order of the construction (it is part of the design, tested): (1) the network is built from the cell fill, so the laminate rule (`laminate.py`) plans its interior
         laminate nodes on the real copper fraction of every cell and moves a sheet conductance dS out of the copper node of the flagged cells; (2) dS is taken off every pixel
         of the cell, copper or bare, because the node no longer carries that laminate; (3) the faces are computed from that REDUCED sheet. Faces built from the unreduced sheet
         count the laminate twice in the flagged cells and are worse than the rule off (README 10, 4.6 against 3.9 % on two layers).
         The vertical coupling between the layers and the copper heat capacity come from the cell fill by the program's own formulas (the rule included), so the transient needs
         nothing else; the vias and the sources are the program's.
         Mappings: "faces" (default), "lambda" (the geometric mean of the Wiener bounds of every cell, much faster, better on 45 degree tracks at about ten pixels per cell),
         "fill" (the arithmetic fill, the program's old path, kept for comparison).
         Units: SI (m, W/K); the Gerber side (`import_copper`) works in mm.
"""

import base64
import functools
import logging
import math
import zlib
from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from .geometry import zone_fill
from .numfmt import num

log = logging.getLogger(__name__)

MAPPINGS = ("faces", "lambda", "fill")           # The mappings of ImportedCopper.mapping
DEFAULT_MAPPING = "faces"
MAX_PIXELS_PER_CELL = 24                         # Most pixels per cell side in the face problems (even); a finer raster is averaged down to it (time grows as its square)
WINDOW_BATCH_PIXELS = 50_000                    # Pixels of the local problems solved together (memory bound; the result does not depend on it)
CACHE_LAYERS = 8                                 # Unpacked masks kept (a copy of a Problem shares the packed text, so the arrays are made once)
ZLIB_LEVEL = 6                                   # Deflate level of the packed masks
MASK_KINDS = ("coverage", "binary")
COARSE_RASTER_PIXELS = 8.0                       # Pixels per cell below which the face problems are too coarse to resolve the copper (warned)
MAX_MASK_PIXELS = 400_000_000                    # Most pixels of one mask read from a file (the cap of the rasteriser, gerber.raster.MAX_RASTER_PIXELS)
EXTENT_TOLERANCE = 0.002                         # Share of the board side (plus one and a half pixels) by which the masks may differ from the board box


# ------------------------------------------------------------------------------------------------ packed masks
def pack_coverage(cov, kind="coverage"):
    """!
    @brief Pack a coverage mask for the project file: one byte per pixel (or one bit for a binary mask), deflated, base64 text.
    @param cov 2D array: uint8 coverage 0..255 (kind "coverage"), or boolean / 0..255 (kind "binary", True where the coverage is above half).
    @param kind "coverage" or "binary".
    @return dict {"kind", "shape": [rows, cols], "data": text}; the text stays a string in every copy of the record.
    @throws ValueError For an unknown kind or an array that is not 2D.
    """
    a = np.asarray(cov)
    if a.ndim != 2:
        raise ValueError("a mask is a 2D array")
    if kind == "coverage":
        raw = a.astype(np.uint8, copy=False).tobytes() if a.dtype != bool else (a.astype(np.uint8) * 255).tobytes()
    elif kind == "binary":
        raw = np.packbits(a if a.dtype == bool else a >= 128, axis=None).tobytes()
    else:
        raise ValueError(f"unknown mask kind {kind!r}; known: {', '.join(MASK_KINDS)}")
    return {"kind": kind, "shape": [int(a.shape[0]), int(a.shape[1])], "data": base64.b64encode(zlib.compress(raw, ZLIB_LEVEL)).decode("ascii")}


@functools.lru_cache(maxsize=CACHE_LAYERS)
def _unpack(data, rows, cols, kind):
    """!
    @brief Unpack a mask (cached on the text, so every copy of a record that shares the string shares the array).
    @details A project file is hostile input: the shape is checked first (positive, at most MAX_MASK_PIXELS), the text is decoded strictly, and the deflated
             stream is inflated with a cap of the bytes the shape needs plus one, so a small text that inflates to gigabytes (a zip bomb) is refused after
             at most that many bytes instead of filling the memory.
    @param data Base64 text of the deflated bytes.
    @param rows Rows of the mask.
    @param cols Columns of the mask.
    @param kind "coverage" or "binary".
    @return uint8 array (rows, cols), read-only.
    @throws ValueError If the shape is not valid, the text is not base64 or deflate data, or the data do not fit the shape.
    """
    if kind not in MASK_KINDS:
        raise ValueError(f"unknown mask kind {kind!r}")
    if not (rows > 0 and cols > 0 and rows * cols <= MAX_MASK_PIXELS):
        raise ValueError(f"a mask of {rows} x {cols} pixels is not a valid shape (positive, at most {MAX_MASK_PIXELS} pixels)")
    need = rows * cols if kind == "coverage" else (rows * cols + 7) // 8
    try:
        packed = base64.b64decode(data, validate=True)
        z = zlib.decompressobj()
        raw = z.decompress(packed, need + 1)          # Never more than one byte beyond what the shape needs
    except (ValueError, zlib.error) as exc:           # (binascii.Error is a ValueError)
        raise ValueError(f"the packed mask is damaged ({exc})") from exc
    if len(raw) != need or z.unconsumed_tail:
        raise ValueError(f"a {kind} mask of {rows} x {cols} pixels needs {need} bytes, the data hold "
                         + (f"{len(raw)}" if len(raw) <= need and not z.unconsumed_tail else f"more than {need}"))
    if kind == "binary":
        a = np.unpackbits(np.frombuffer(raw, np.uint8), count=rows * cols).reshape(rows, cols) * np.uint8(255)
    else:
        a = np.frombuffer(raw, np.uint8).reshape(rows, cols).copy()
    a.setflags(write=False)
    return a


def unpack_coverage(mask):
    """!
    @brief The coverage array of a packed mask.
    @param mask Dict written by pack_coverage (after a JSON round trip).
    @return uint8 array (rows, cols) (0 or 255 for a binary mask), read-only and shared.
    @throws ValueError If the mask is malformed (shape, kind, text) or damaged (see _unpack).
    """
    try:
        rows, cols = (int(v) for v in mask["shape"])
        data, kind = str(mask["data"]), str(mask.get("kind", "coverage"))
    except (KeyError, TypeError, ValueError) as exc:     # A hand-edited record: a message, not a traceback
        raise ValueError(f"a packed mask needs a shape [rows, cols] and its data ({exc!r})") from exc
    return _unpack(data, rows, cols, kind)


def clear_cache():
    """!
    @brief Release the unpacked masks that are kept.
    @return None.
    """
    _unpack.cache_clear()


def has_mask(entry):
    """!
    @brief Whether a layer entry of an ImportedCopper holds a packed mask the models can read (a placeholder or a reference-only layer does not).
    @param entry Dict of the layer.
    @return bool.
    """
    m = entry.get("mask") if isinstance(entry, dict) else None
    return isinstance(m, dict) and "data" in m and "shape" in m


# ------------------------------------------------------------------------------------------------ resampling
def _average_matrix(n_src, src_origin, src_pix, n_out, out_pix):
    """!
    @brief The sparse matrix that averages a piecewise-constant signal over equal output intervals (the box filter, exact for the area).
    @details Output interval i is [i out_pix, (i + 1) out_pix]; source interval k is [src_origin + k src_pix, src_origin + (k + 1) src_pix]. A row holds the overlap
             lengths over out_pix, so a constant signal stays constant where the source covers the interval and the part of the interval beyond the source counts as 0.
    @param n_src Source intervals.
    @param src_origin Coordinate of the first source edge (m).
    @param src_pix Source interval (m).
    @param n_out Output intervals.
    @param out_pix Output interval (m).
    @return scipy.sparse.csr_matrix (n_out, n_src).
    """
    a = np.arange(n_out) * out_pix
    b = a + out_pix
    k0 = np.floor((a - src_origin) / src_pix + 1e-9).astype(np.int64)
    m = int(math.ceil(out_pix / src_pix)) + 2
    ks = k0[:, None] + np.arange(m)[None, :]
    lo = np.maximum(a[:, None], src_origin + ks * src_pix)
    hi = np.minimum(b[:, None], src_origin + (ks + 1) * src_pix)
    w = np.maximum(hi - lo, 0.0) / out_pix
    ok = (ks >= 0) & (ks < n_src) & (w > 1e-12)
    rows = np.broadcast_to(np.arange(n_out)[:, None], ks.shape)[ok]
    return sp.csr_matrix((w[ok], (rows, ks[ok])), shape=(n_out, n_src))


def resample_coverage(raster, pix, width, height, n_rows, n_cols):
    """!
    @brief Average a coverage raster onto a regular grid of the board.
    @details The raster is anchored at the top-left corner of the board box (row 0 is the top edge, y = height); the grid is n_rows x n_cols equal cells covering
             [0, width] x [0, height], rows from the BOTTOM. Copper beyond the board is cut, a board beyond the raster has no copper there.
    @param raster uint8 coverage (rows from the top), 0..255.
    @param pix Raster pixel (m).
    @param width Board width (m).
    @param height Board height (m).
    @param n_rows Rows of the output grid.
    @param n_cols Columns of the output grid.
    @return float32 array (n_rows, n_cols) of the copper fraction 0..1, rows from the bottom.
    """
    rows, cols = raster.shape
    flipped = raster[::-1]                                       # rows from the bottom of the raster, which is at y = height - rows * pix
    ry = _average_matrix(rows, height - rows * pix, pix, n_rows, height / n_rows)
    rx = _average_matrix(cols, 0.0, pix, n_cols, width / n_cols)
    out = ry @ flipped.astype(np.float32)                        # (n_rows, cols)
    out = (rx @ out.T).T                                         # (n_rows, n_cols)
    return np.clip(out / np.float32(255.0), 0.0, 1.0).astype(np.float32, copy=False)


def sample_coverage(raster, pix, width, height, n_rows, n_cols):
    """!
    @brief Sample a coverage raster at the centres of a regular grid of the board that is at least as fine as the raster (nearest neighbour).
    @details The face problems need the copper on a grid of n x n pixels per cell, and a cell is almost never a whole number of raster pixels (the cell is the
             board side over a whole number of cells). Averaging the raster onto that grid (resample_coverage) turns every pixel that a copper edge crosses into a
             partial coverage, and the two-phase sheet of a partial pixel is the parallel mixture of copper and laminate: a clearance of two or three pixels between
             two copper areas becomes a bridge of half copper, and the faces read cool (1.4 to 3.9 % of the rise on twelve real windows at cells of 0.92 and 1.09 mm,
             against 0 to 1.2 % at whole numbers of pixels; 11 to 22 % on a checker and on islands 0.3 mm apart). Sampling keeps every output pixel a pixel of the
             raster, so the clearances and the tracks keep their topology (a feature moves by at most one output pixel); the copper area of a cell then differs from
             the exact fraction by about one row of pixels, which is why the cell fill (vertical links, capacity) stays the box average of resample_coverage.
    @param raster uint8 coverage (rows from the top), 0..255.
    @param pix Raster pixel (m).
    @param width Board width (m).
    @param height Board height (m).
    @param n_rows Rows of the output grid.
    @param n_cols Columns of the output grid.
    @return float32 array (n_rows, n_cols) of the copper fraction 0..1, rows from the bottom; zero where the grid lies beyond the raster.
    """
    rows, cols = raster.shape
    yc = (np.arange(n_rows) + 0.5) * (height / n_rows)                     # Centres of the output pixels, from the bottom
    xc = (np.arange(n_cols) + 0.5) * (width / n_cols)
    ri = np.floor((height - yc) / pix).astype(np.int64)                     # Raster rows run from the top edge of the box
    ci = np.floor(xc / pix).astype(np.int64)
    okr = (ri >= 0) & (ri < rows)
    okc = (ci >= 0) & (ci < cols)
    out = (raster[np.clip(ri, 0, rows - 1)][:, np.clip(ci, 0, cols - 1)] / 255.0).astype(np.float32)
    out[~okr, :] = 0.0                                                      # A board beyond the raster has no copper there
    out[:, ~okc] = 0.0
    return out


# ------------------------------------------------------------------------------------------------ local conduction problems
def _window_flux(sw):
    """!
    @brief Effective conductance, left to right, of many windows of pixel sheet conductances.
    @details Potential 1 on the left face and 0 on the right (half-pixel links, so a uniform square window gives exactly its S), top and bottom insulated. Windows with one
             value skip the solve. All the others are solved together as one block-diagonal sparse system; a tiny diagonal term keeps the pixels that nothing connects (a cell off
             an outline has no sheet) regular without changing the flux.
    @param sw Array (K, R, C) of pixel sheet conductances in W/K (float64).
    @return numpy.ndarray (K,) of effective conductances in W/K.
    """
    k, r, c = sw.shape
    flux = np.zeros(k)
    lo, hi = sw.min(axis=(1, 2)), sw.max(axis=(1, 2))
    uniform = (hi - lo) <= 1e-9 * np.maximum(hi, 1e-300)
    flux[uniform] = hi[uniform] * r / c
    todo = np.flatnonzero(~uniform & (hi > 0))
    if todo.size == 0:
        return flux
    w = sw[todo]
    kk = len(w)
    n = r * c
    idx = np.arange(kk)[:, None, None] * n + np.arange(r)[None, :, None] * c + np.arange(c)[None, None, :]
    a = np.concatenate([idx[:, :, :-1].ravel(), idx[:, :-1, :].ravel()])
    b = np.concatenate([idx[:, :, 1:].ravel(), idx[:, 1:, :].ravel()])
    p, q = w[:, :, :-1], w[:, :, 1:]
    s1 = p + q
    gh = np.divide(2.0 * p * q, s1, out=np.zeros_like(s1), where=s1 > 0)
    p, q = w[:, :-1, :], w[:, 1:, :]
    s2 = p + q
    gv = np.divide(2.0 * p * q, s2, out=np.zeros_like(s2), where=s2 > 0)
    g = np.concatenate([gh.ravel(), gv.ravel()])
    gl, gr = 2.0 * w[:, :, 0], 2.0 * w[:, :, -1]
    il, ir = idx[:, :, 0].ravel(), idx[:, :, -1].ravel()
    diag = np.bincount(a, g, kk * n) + np.bincount(b, g, kk * n) + 1e-12 * float(hi.max())
    diag[il] += gl.ravel()
    diag[ir] += gr.ravel()
    rhs = np.zeros(kk * n)
    rhs[il] = gl.ravel()                                          # unit potential on the left face
    m = sp.coo_matrix((np.concatenate([-g, -g]), (np.concatenate([a, b]), np.concatenate([b, a]))), shape=(kk * n, kk * n)).tocsr() + sp.diags(diag)
    v = spla.spsolve(m.tocsc(), rhs).reshape(kk, r, c)
    flux[todo] = (gr * v[:, :, -1]).sum(axis=1)
    return flux


def _harmonic(a, b):
    """!
    @brief Harmonic mean of two conductances (zero where both are zero).
    @param a First array.
    @param b Second array.
    @return Array 2ab/(a+b).
    """
    s = a + b
    return np.divide(2.0 * a * b, s, out=np.zeros_like(s), where=s > 0)


def face_conductances(sheet, n, mapping="faces"):
    """!
    @brief Face conductances between neighbouring cells from the pixel sheet conductance (the cell grid is n x n pixels per cell).
    @details "faces": one local conduction problem per pair of neighbouring cells on the n x n pixels between the two cell centres (n even, flux along the pair), the
             transmissibility upscaling used for reservoir grids. "lambda": the geometric mean of the Wiener bounds of every cell for flow along x and y (per cell), joined by
             the harmonic mean of the two cells, as the FVM forms its faces.
    @param sheet Pixel sheet conductance in W/K, array (ny n, nx n), float32 or float64, rows from the bottom; the faces are in W/K for square pixels.
    @param n Pixels per cell side (even, at least 2).
    @param mapping "faces" or "lambda".
    @return Tuple (gx (ny, nx - 1), gy (ny - 1, nx)) in W/K.
    @throws ValueError For an odd n or an unknown mapping.
    """
    if n < 2 or n % 2:
        raise ValueError("the face problems need an even number of pixels per cell")
    ny, nx = sheet.shape[0] // n, sheet.shape[1] // n
    if mapping == "lambda":
        return _lambda_faces(sheet, n, ny, nx)
    if mapping != "faces":
        raise ValueError(f"unknown mapping {mapping!r}")
    gx = np.zeros((ny, nx - 1))
    gy = np.zeros((ny - 1, nx))
    h = n // 2
    if nx > 1:
        sx = sheet[: ny * n, h: h + (nx - 1) * n].reshape(ny, n, nx - 1, n).transpose(0, 2, 1, 3)        # windows from cell centre to cell centre
        step = max(WINDOW_BATCH_PIXELS // (n * n * (nx - 1)), 1)
        for i0 in range(0, ny, step):
            win = np.ascontiguousarray(sx[i0:i0 + step], dtype=np.float64).reshape(-1, n, n)
            gx[i0:i0 + step] = _window_flux(win).reshape(-1, nx - 1)
    if ny > 1:
        sy = sheet[h: h + (ny - 1) * n, : nx * n].reshape(ny - 1, n, nx, n).transpose(0, 2, 3, 1)         # flow along y: the window is turned so that y runs left to right
        step = max(WINDOW_BATCH_PIXELS // (n * n * nx), 1)
        for i0 in range(0, ny - 1, step):
            win = np.ascontiguousarray(sy[i0:i0 + step], dtype=np.float64).reshape(-1, n, n)
            gy[i0:i0 + step] = _window_flux(win).reshape(-1, nx)
    return gx, gy


def _lambda_faces(sheet, n, ny, nx):
    """!
    @brief The lambda 0.5 faces: per cell the geometric mean of the Wiener lower and upper bounds for flow along each axis, joined by the harmonic mean.
    @param sheet Pixel sheet conductance (ny n, nx n) in W/K.
    @param n Pixels per cell side.
    @param ny Cell rows.
    @param nx Cell columns.
    @return Tuple (gx, gy) in W/K.
    """
    sx = np.zeros((ny, nx))
    sy = np.zeros((ny, nx))
    step = max(WINDOW_BATCH_PIXELS // (n * n * nx), 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        for i0 in range(0, ny, step):
            blk = sheet[i0 * n:(i0 + step) * n, : nx * n].astype(np.float64)
            m = blk.shape[0] // n
            blk = blk.reshape(m, n, nx, n).transpose(0, 2, 1, 3)                  # (cells y, cells x, rows, cols)
            inv = 1.0 / blk
            low_x = (1.0 / inv.mean(axis=3)).mean(axis=2)
            low_y = (1.0 / inv.mean(axis=2)).mean(axis=2)
            up_x = 1.0 / (1.0 / blk.mean(axis=2)).mean(axis=2)
            up_y = 1.0 / (1.0 / blk.mean(axis=3)).mean(axis=2)
            sx[i0:i0 + m] = np.sqrt(np.nan_to_num(low_x * up_x))
            sy[i0:i0 + m] = np.sqrt(np.nan_to_num(low_y * up_y))
    return _harmonic(sx[:, :-1], sx[:, 1:]), _harmonic(sy[:-1, :], sy[1:, :])


# ------------------------------------------------------------------------------------------------ the source of the models
class CopperSource:
    """!
    @brief The imported copper of a problem as the models read it: the cell fill of every imported layer and its in-plane face conductances.
    @details Built from `Problem.imported` (`CopperSource.of`). The FVM and FDM take it as the `faces` argument of their networks.
    """

    def __init__(self, copper, n_layers, width=None, height=None):
        """!
        @param copper model.ImportedCopper.
        @param n_layers Copper layers of the board.
        @param width Board width in m (None: the extent of the masks is not checked).
        @param height Board height in m (None: not checked).
        @throws ValueError If a layer index is outside the board, appears twice, the pixel is not a positive finite number, or a mask does not cover the board box
                (its rows times the pixel, its columns times the pixel, within one and a half pixels plus EXTENT_TOLERANCE of the side): a board resized after the
                import, or a damaged record, would otherwise put the copper in the wrong place or leave part of the board bare without a word.
        """
        if copper.mapping not in MAPPINGS:
            raise ValueError(f"unknown copper mapping {copper.mapping!r}; known: {', '.join(MAPPINGS)}")
        if not (math.isfinite(copper.pix_mm) and copper.pix_mm > 0):
            raise ValueError("the pixel of the imported copper must be a positive finite number")
        self.mapping = copper.mapping
        self.reduce_sheet = True                                                   # False only to show that the unreduced sheet counts the laminate twice (a test)
        self.pix = copper.pix_mm * 1e-3
        self.entries = {}
        for k, e in enumerate(copper.layers):
            if not has_mask(e):
                continue                                                           # a reference-only layer (embed False) or a placeholder: no copper to give
            i = int(e.get("index", k))                                             # (an entry without an index is the k-th copper layer, top first)
            if not 0 <= i < n_layers:
                raise ValueError(f"imported copper layer {e.get('name', '')!r} has index {i}, but the board has {n_layers} copper layers")
            if i in self.entries:
                raise ValueError(f"two imported masks for copper layer {i + 1}")
            if width is not None and height is not None:
                try:
                    rows, cols = (int(v) for v in e["mask"]["shape"])
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"imported copper layer {e.get('name', '')!r}: the mask has no valid shape ({exc!r})") from exc
                for side, n_px, what in ((width, cols, "width"), (height, rows, "height")):
                    tol = 1.5 * self.pix + EXTENT_TOLERANCE * side
                    if abs(n_px * self.pix - side) > tol:
                        raise ValueError(f"imported copper layer {e.get('name', '')!r}: its mask covers {n_px * self.pix * 1e3:.3f} mm of the board {what}, the board is "
                                         f"{side * 1e3:.3f} mm (was the board resized after the import, or the record damaged?); import the copper again")
            self.entries[i] = e

    @staticmethod
    def of(problem):
        """!
        @brief The source of a problem, or None when it has no imported copper with masks.
        @param problem A Problem.
        @return CopperSource or None.
        """
        c = getattr(problem, "imported", None)
        if c is None or not c.layers:
            return None
        src = CopperSource(c, problem.board.layers, problem.board.width, problem.board.height)
        return src if src.entries else None

    @property
    def layers(self):
        """!
        @brief The copper layer indices (0 = top) that have a mask.
        @return Sorted list of int.
        """
        return sorted(self.entries)

    def raster(self, layer):
        """!
        @brief The unpacked coverage of a layer.
        @param layer Copper layer index (0 = top).
        @return uint8 array (rows from the top, columns), shared and read-only.
        """
        return unpack_coverage(self.entries[layer]["mask"])

    def fill(self, layer, ny, nx, width, height):
        """!
        @brief The copper fraction of every cell of a layer.
        @param layer Copper layer index (0 = top).
        @param ny Cell rows.
        @param nx Cell columns.
        @param width Board width in m.
        @param height Board height in m.
        @return float32 array (ny, nx), rows from the bottom, 0..1.
        """
        return resample_coverage(self.raster(layer), self.pix, width, height, ny, nx)

    def pixels_per_cell(self, dx, dy):
        """!
        @brief The even number of pixels per cell side used by the face problems: the raster pixels per cell rounded UP to an even number, so that the grid of
               the face problems is never coarser than the raster (it is then sampled, see sample_coverage), and at most MAX_PIXELS_PER_CELL (a finer raster is averaged).
        @details Rounding to the nearest even number (Python rounds 2.5 to 2) gave 4 for five pixels per cell, which averaged a 0.1 mm raster onto 0.125 mm pixels.
        @param dx Cell width in m.
        @param dy Cell height in m.
        @return int, at least 2 and at most MAX_PIXELS_PER_CELL.
        """
        r = 0.5 * (dx + dy) / self.pix
        return int(min(max(2 * math.ceil(r / 2.0 - 1e-9), 2), MAX_PIXELS_PER_CELL))

    def lateral(self, layer, a_full, b_bare, reduction, cover, ny, nx, width, height, nodes=False):
        """!
        @brief The in-plane face conductances of one imported layer on the reduced sheet.
        @details The pixel sheet is b + coverage (a - b) (the program's two-phase formula per pixel), minus `reduction` (the sheet conductance per area that the laminate rule took
                 out of the copper node of the cell, the same on every pixel of the cell), times the board cover of the cell. For the node-centred FDM (`nodes` True) the pixels
                 are the cells of the plan grid, padded by half a cell on every side, so that the windows centre on the nodes; the faces of the edge rows are half (the control
                 volume of an edge node is half a cell wide).
        @param layer Copper layer index (0 = top).
        @param a_full Sheet conductance of a pixel with copper (W/K).
        @param b_bare Sheet conductance of a pixel without copper (W/K).
        @param reduction Array (rows, cols) of the sheet conductance per area removed from the copper node by the rule (W/K), rows from the bottom; rows, cols are the cells
               (ny, nx) of the grid, or the nodes (ny + 1, nx + 1) when `nodes`.
        @param cover Array like `reduction`: share of the cell (node) that is board.
        @param ny Plan cell rows.
        @param nx Plan cell columns.
        @param width Board width in m.
        @param height Board height in m.
        @param nodes True for the FDM node grid.
        @return Tuple (gx, gy) of W/K for square cells: shapes (rows, cols - 1) and (rows - 1, cols).
        """
        dx, dy = width / nx, height / ny
        n = self.pixels_per_cell(dx, dy)
        # A grid at least as fine as the raster samples it (the clearances stay bare); a raster finer than MAX_PIXELS_PER_CELL per cell is averaged down
        fine_enough = max(dx, dy) / n <= self.pix * (1.0 + 1e-9)
        cov = (sample_coverage if fine_enough else resample_coverage)(self.raster(layer), self.pix, width, height, ny * n, nx * n)       # (ny n, nx n) float32
        if nodes:
            h = n // 2
            cov = np.pad(cov, ((h, h), (h, h)), mode="symmetric")                  # mirror at the board edge: half control volumes
        s = cov
        s *= np.float32(a_full - b_bare)
        s += np.float32(b_bare)
        rows, cols = reduction.shape
        s4 = s.reshape(rows, n, cols, n)
        if self.reduce_sheet:
            s4 -= reduction.astype(np.float32)[:, None, :, None]                  # the laminate the copper node no longer carries
        np.maximum(s, 0.0, out=s)
        s4 *= cover.astype(np.float32)[:, None, :, None]
        gx, gy = face_conductances(s, n, self.mapping)
        gx *= dy / dx                                                               # the pixel problems are for square pixels; the cell may not be
        gy *= dx / dy
        if nodes:
            gx[0, :] *= 0.5
            gx[-1, :] *= 0.5
            gy[:, 0] *= 0.5
            gy[:, -1] *= 0.5
        return gx, gy


def resolve(faces, problem):
    """!
    @brief The source a network builder uses: the argument, or the problem's own imported copper.
    @param faces None (take the problem's imported copper, if any), False (ignore the imported copper), or a CopperSource.
    @param problem A Problem.
    @return CopperSource or None.
    """
    if faces is False:
        return None
    if faces is None:
        return CopperSource.of(problem)
    return faces


def override_fill(fill, source, ny, nx, width, height):
    """!
    @brief Replace, in place, the copper fraction of the imported layers by the cell fraction of their masks.
    @details An imported layer replaces the zones of that layer (the copper of an import is the whole copper of the layer).
    @param fill Array (layers, ny, nx) from `geometry.zone_fill`, rows from the bottom; changed in place.
    @param source CopperSource or None (nothing is changed).
    @param ny Cell rows.
    @param nx Cell columns.
    @param width Board width in m.
    @param height Board height in m.
    @return The same array.
    """
    if source is not None:
        for layer in source.layers:
            fill[layer] = source.fill(layer, ny, nx, width, height)
    return fill


def problem_fill(problem, nx, ny, dx, dy, samples=4, source=None):
    """!
    @brief The copper fraction of every cell of every layer: the union of the zones, with the imported layers taken from their masks.
    @details Every model that reads the copper of a problem and does not build a network of its own (the 3D solid, the Lumped and Analytic, the checks) goes through this
             function, so a problem without imported copper gets exactly `geometry.zone_fill`.
    @param problem A Problem.
    @param nx Cell columns.
    @param ny Cell rows.
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param samples Samples per cell side of the zone union.
    @param source A CopperSource (None: the problem's own, or False to ignore it).
    @return Array (layers, ny, nx), rows from the bottom.
    """
    b = problem.board
    f = zone_fill(problem.zones, b.layers, nx, ny, dx, dy, samples)
    return override_fill(f, resolve(source, problem), ny, nx, b.width, b.height)


def has_imported(problem):
    """!
    @brief Whether a problem carries imported copper that the models will read.
    @param problem A Problem.
    @return bool.
    """
    return CopperSource.of(problem) is not None


def imported_from_rasters(rasters, pix_mm, mapping=DEFAULT_MAPPING, names=None, roles=None, indices=None, kind="coverage", thickness_um=None):
    """!
    @brief The ImportedCopper record of coverage rasters (packed as text).
    @param rasters List of uint8 coverage arrays (rows from the top edge of the board box), one per copper layer, top layer first unless `indices` says otherwise.
    @param pix_mm Pixel of the rasters in mm.
    @param mapping "faces" (default), "lambda" or "fill".
    @param names Optional layer names.
    @param roles Optional layer roles ("top", "inner", "bottom").
    @param indices Optional copper layer index (0 = top) of every raster; default 0, 1, 2, ...
    @param kind "coverage" (one byte per pixel) or "binary" (one bit per pixel).
    @param thickness_um Optional copper thickness of every layer in micrometres, stored with the layer.
    @return model.ImportedCopper.
    @throws ValueError For an unknown mapping.
    """
    from .model import ImportedCopper
    if mapping not in MAPPINGS:
        raise ValueError(f"unknown copper mapping {mapping!r}; known: {', '.join(MAPPINGS)}")
    layers = []
    for k, r in enumerate(rasters):
        e = {"name": (names[k] if names else f"copper {k + 1}"), "role": (roles[k] if roles else ""), "index": int(indices[k] if indices is not None else k),
             "mask": pack_coverage(r, kind)}
        if thickness_um is not None:
            e["thickness_um"] = float(thickness_um[k])
        layers.append(e)
    return ImportedCopper(float(pix_mm), True, layers, mapping)


# ------------------------------------------------------------------------------------------------ the import
@dataclass
class ImportedBoard:
    """!
    @brief What an import of Gerber copper produced: the masks (packed), the board box and outline in board coordinates, the plated holes and the warnings.
    @details Board coordinates are millimetres with the origin at the lower-left corner of the outline box (x to the right, y up). `copper` is the ImportedCopper record
             (the masks as packed text); `to_problem` makes the Problem to run and `record` the ImportRecord of the project file (format 2).
    """
    copper: object                                         # model.ImportedCopper
    width_mm: float                                        # Board width (outline box) in mm
    height_mm: float                                       # Board height in mm
    box_mm: tuple                                          # (xmin, ymin, xmax, ymax) of the outline box in the Gerber file coordinates, mm
    outline_mm: object = None                              # Array (n, 2) of the outline in board coordinates (mm), or None for a rectangle
    holes: list = field(default_factory=list)              # [{"x_mm", "y_mm", "d_mm", "kind": "via"}, ...] in board coordinates
    warnings: list = field(default_factory=list)           # Warnings of the import (text)
    pixel_mm: float = 0.0                                  # Pixel of the masks in mm
    shape: tuple = (0, 0)                                  # (rows, columns) of every mask
    thickness_um: float = 35.0                             # Copper thickness assumed for every layer in micrometres (the Gerber files do not carry it)

    def to_problem(self, thickness_mm=1.6, copper_um=None, name="imported board", **board_options):
        """!
        @brief The Problem of the imported board: its size, copper layers, outline, one via per plated hole and the imported copper; no heater (the caller adds the parts).
        @param thickness_mm Board thickness in mm (the Gerber copper files do not carry it; a job file or the user does).
        @param copper_um Copper thickness of every layer in micrometres (None: the thickness of the import).
        @param name Project name.
        @param board_options Any other Board field (ambient, h_top, h_bottom, h_side, ...).
        @return model.Problem with `imported` set.
        """
        from .model import Problem
        n = len(self.copper.layers)
        p = Problem.new(self.width_mm, self.height_mm, layers=max(n, 1), thickness_mm=thickness_mm,
                        copper_um=self.thickness_um if copper_um is None else copper_um, name=name, **board_options)
        if self.outline_mm is not None:
            p.board.outline = np.asarray(self.outline_mm, float) / 1000.0
        for h in self.holes:
            p.add_via(h["x_mm"], h["y_mm"], diameter=h["d_mm"])
        p.imported = self.copper
        return p

    def record(self, name="imported board"):
        """!
        @brief The ImportRecord of the project file for this import (without source files, parts or settings: the caller fills them).
        @param name Name of the record.
        @return model.ImportRecord.
        """
        from .model import ImportRecord
        return ImportRecord(name=name, box_mm=[float(v) for v in self.box_mm], copper=self.copper, warnings=list(self.warnings), holes=[dict(h) for h in self.holes])


def _inside_mask(polygons, window, pixel_mm, rows, cols):
    """!
    @brief Which pixel centres lie on the board (inside a polygon, outside its cut-outs).
    @param polygons List of outline.OutlinePolygon in the Gerber axes (mm).
    @param window gerber.Window of the raster.
    @param pixel_mm Pixel in mm.
    @param rows Raster rows.
    @param cols Raster columns.
    @return Boolean array (rows, cols).
    """
    from .geometry import points_in_polygon
    out = np.zeros((rows, cols), bool)
    xs = window.x_left + (np.arange(cols) + 0.5) * pixel_mm
    step = max(4_000_000 // max(cols, 1), 1)
    for i0 in range(0, rows, step):
        i1 = min(i0 + step, rows)
        yy = window.y_top - (np.arange(i0, i1) + 0.5) * pixel_mm
        gx, gy = np.meshgrid(xs, yy)
        m = np.zeros(gx.shape, bool)
        for poly in polygons:
            inside = points_in_polygon(gx, gy, poly.outer)
            for hole in poly.holes:
                inside &= ~points_in_polygon(gx, gy, hole)
            m |= inside
        out[i0:i1] = m
    return out


def import_copper(layers, outline=None, drills=(), pixel_mm=None, cell_mm=2.0, supersample=4, mapping=DEFAULT_MAPPING, names=None, thickness_um=35.0,
                  fraction=None, ram=None, base=None):
    """!
    @brief Import the copper of a Gerber set: rasterise every copper layer to a coverage mask, pack it, and collect the board box, the outline and the plated holes.
    @details No GUI. Layers are drawn one at a time and only the packed text is kept (one byte per pixel of working memory beyond the layer being drawn). The memory guard
             is asked BEFORE anything is drawn (`memory.check_import`): the raster is about 1 byte per pixel and layer, and the face construction of the run adds its own term.
             The box of the board is the bounding box of the outline (or, without one, of the copper); the raster is anchored at its top-left corner. With a non-rectangular outline
             the copper outside it is cleared. Panels (several boards in the outline) are refused: import one board.
    @param layers List of gerber.Layer, the copper layers from the top layer down.
    @param outline gerber.Outline of the board, or None to use the box of the copper.
    @param drills Iterable of gerber.DrillFile; plated, round holes become vias (a slot, an unplated or unknown-plating hole is left out and said in the warnings).
    @param pixel_mm Pixel of the masks in mm (None: a quarter of the thinnest feature times the supersampling, and at most a tenth of the cell).
    @param cell_mm Cell of the thermal grid the board is meant for, in mm (only to choose the pixel and to size the memory estimate).
    @param supersample Sub-pixels per pixel side of the coverage.
    @param mapping "faces" (default), "lambda" or "fill".
    @param names Optional layer names (default: the names of the files).
    @param thickness_um Copper thickness assumed for every layer in micrometres.
    @param fraction Share of the physical memory the import may use (None: the default of memory.py).
    @param ram Physical memory in bytes (None: read it); for tests.
    @param base Resident bytes of the process (None: read it); for tests.
    @return ImportedBoard.
    @throws ValueError For no layer, an outline of several boards, or a board box with no area.
    @throws memory.MemoryGuardError If the raster would not fit in memory (the message names the pixel that fits).
    """
    from . import gerber, memory
    from .model import ImportedCopper
    layers = list(layers)
    if not layers:
        raise ValueError("an import needs at least one copper layer")
    if mapping not in MAPPINGS:
        raise ValueError(f"unknown copper mapping {mapping!r}; known: {', '.join(MAPPINGS)}")
    # The tolerances the reader used on a layer (a non-conformant macro name) go into the record of the import, so that the window and the saved project show them
    warnings = [w for lay in layers for w in getattr(lay, "warnings", [])]
    boxes = [lay.bbox() for lay in layers if lay.bbox() is not None]
    if outline is not None:
        if len(outline.polygons) != 1:
            raise ValueError(f"the outline holds {len(outline.polygons)} boards (a panel); import one board")
        x0, y0, x1, y1 = outline.bbox
    else:
        if not boxes:
            raise ValueError("the copper layers draw nothing: no board box")
        x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
        x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
        warnings.append("no outline: the board box is the bounding box of the copper")
    width, height = x1 - x0, y1 - y0
    if not (width > 0 and height > 0):
        raise ValueError("the board box has no area")
    if pixel_mm is None:
        thin = [t for t in (lay.thinnest_feature_mm() for lay in layers) if t]
        # A quarter of the thinnest feature per sample spacing rule (supersample * thinnest / 4), and at most a tenth of the cell: the faces need about ten pixels per cell
        # (COARSE_RASTER_PIXELS), the pixel the studies used; the memory guard proposes a coarser pixel when this one does not fit
        pixel_mm = min(supersample * min(thin) / 4.0, cell_mm / 10.0) if thin else cell_mm / 10.0
    window = gerber.Window(x0, y1, width, height)
    rows, cols = gerber.pixel_counts(window, pixel_mm)
    memory.check_import(rows, cols, len(layers), cell_mm, fraction=fraction, ram=ram, base=base, pixel_mm=pixel_mm)
    inside = None
    if outline is not None and abs(outline.area_mm2 - width * height) > 1e-3 * width * height:
        inside = _inside_mask(outline.polygons, window, pixel_mm, rows, cols)
        if any(p.holes for p in outline.polygons):
            warnings.append("the outline has cut-outs: the copper inside them is cleared, but the plan grid still treats those cells as board")
    packed = []
    for lay in layers:
        msg = gerber.check_sample_spacing(lay, pixel_mm, supersample)
        if msg:
            warnings.append(msg)
        cov = gerber.rasterize(lay, window, pixel_mm, supersample)
        if inside is not None:
            cov[~inside] = 0
        packed.append(pack_coverage(cov))                                          # keep the text, free the array before the next layer is drawn
        del cov
    n = len(layers)
    roles = ["top"] + ["inner"] * max(n - 2, 0) + (["bottom"] if n > 1 else [])
    entries = [{"name": (names[k] if names else (layers[k].name or f"copper {k + 1}")), "role": roles[k], "index": k, "mask": packed[k], "thickness_um": float(thickness_um)}
               for k in range(n)]
    copper_rec = ImportedCopper(float(pixel_mm), True, entries, mapping)
    holes = []
    skipped = {"slot": 0, "unplated": 0}
    for df in drills:
        for h in df.holes:
            plated = h.plated if h.plated is not None else df.plated
            if h.is_slot:
                skipped["slot"] += 1
            elif not plated:
                skipped["unplated"] += 1
            elif x0 <= h.x <= x1 and y0 <= h.y <= y1:
                holes.append({"x_mm": float(h.x - x0), "y_mm": float(h.y - y0), "d_mm": float(max(h.diameter, 0.1)), "kind": "via"})
    if skipped["slot"]:
        warnings.append(f"{skipped['slot']} routed slots are not modelled")
    if skipped["unplated"]:
        warnings.append(f"{skipped['unplated']} holes are not plated (or their plating is unknown) and are left out")
    outline_mm = None
    if inside is not None:
        outline_mm = np.asarray(outline.polygons[0].outer, float) - np.array([x0, y0])
    return ImportedBoard(copper_rec, float(width), float(height), (float(x0), float(y0), float(x1), float(y1)), outline_mm, holes, warnings,
                         float(pixel_mm), (int(rows), int(cols)), float(thickness_um))


# ------------------------------------------------------------------------------------------------ warnings
FILL_NOTE = ("the copper of this board is an import and the models read it as a cell mapping, not as drawn zones: the finite-volume and finite-difference models use flow-based face "
             "conductances (on 24 mm windows of real two-layer boards with a 4 mm part they read within 1.7 % of the program's network on the pixels at a 0.5 mm cell, "
             "up to 4.3 % too hot at 1 mm and 7 to 10 % too hot at 2 mm; the program's own grid error under a part two cells wide is +2.2 % with drawn full copper and +11.8 % "
             "on bare laminate at 2 mm, and the imported overshoot lies between the two; no measurement on a physical board exists)")
COARSE_CELL_MM = 1.0                             # Cell above which the note on the faces adds the coarse-cell warning (README 10 of research/gerber-real-boards, review)
SCREENING_CELL_MM = 1.5                          # Cell above which the warning calls the result a screening estimate
COARSE_CELL_WARNING = ("imported copper at a cell above 1 mm: on 24 mm windows of real two-layer boards the face conductances read up to 4.3 % too hot at a 1 mm cell and 7 to 10 % "
                       "too hot at a 2 mm cell for a 4 mm part (on the safe side; the program's grid error under a part two cells wide is +0.5 % and +2.2 % at 1 and 2 mm with drawn "
                       "full copper, +3.7 % and +11.8 % on bare laminate, and the imported overshoot lies between the two; the share of the copper inside a cell was not separated); "
                       "use a cell of 1 mm or less for the result")
SCREENING_WARNING = ("imported copper at a cell above 1.5 mm: treat the result as a screening estimate (7 to 10 % too hot at 2 mm in the windows measured), not as a figure to design to")
REDUCED_MODEL_WARNING = ("imported copper on the Lumped / Analytic model: it sees only the copper fraction of every cell, and in the study of 24 windows it read 1 to 16 % too "
                         "cool (6 % on average) against the pixel network; use the finite-volume model for the result")
SOLID3D_WARNING = ("imported copper in the 3D solid: it reads the copper fraction of every cell as an average conductivity, the fill-fraction mapping, which reads thin copper cooler "
                   "than the flow-based faces of the layered models (see the finite-volume model for the reference)")


def model_warnings(problem, model, cell_mm=None):
    """!
    @brief The warnings that a model owes when the board carries imported copper.
    @param problem A Problem.
    @param model "fvm", "fdm", "lumped", "analytic" or "solid3d".
    @param cell_mm Cell of the run in mm (None: the pixel-per-cell check is left out).
    @return list of str (empty without imported copper).
    """
    src = CopperSource.of(problem)
    if src is None:
        return []
    out = []
    if model in ("lumped", "analytic"):
        out.append(REDUCED_MODEL_WARNING)
    elif model == "solid3d":
        out.append(SOLID3D_WARNING)
    else:
        out.append(FILL_NOTE if src.mapping != "fill" else
                   "imported copper with the 'fill' mapping: the arithmetic copper fraction of every cell reads 10 to 30 % too cool on thin copper; choose 'faces' for a result")
        if cell_mm is not None and src.mapping != "fill" and cell_mm > COARSE_CELL_MM + 1e-9:
            out.append(COARSE_CELL_WARNING)
            if cell_mm > SCREENING_CELL_MM + 1e-9:
                out.append(SCREENING_WARNING)
        if cell_mm is not None and src.mapping != "fill":
            per_cell = cell_mm * 1e-3 / src.pix
            if per_cell < COARSE_RASTER_PIXELS:
                out.append(f"the masks have {num(per_cell, 1)} pixels per cell ({num(src.pix * 1e3, 2)} mm pixel, {num(cell_mm, 2)} mm cell): below about {COARSE_RASTER_PIXELS:g} the "
                           "face conductances cannot resolve the copper (2 to 5 % of the rise in the tests at 4 pixels per cell, under 1 % at 10 or more); use a finer pixel "
                           "(import again) or a coarser cell")
    return out


def auto_cell_cap(problem, cell_mm):
    """!
    @brief The cell that Auto may propose for a board with imported copper: at most COARSE_CELL_MM.
    @param problem A Problem.
    @param cell_mm Cell chosen from the parts (mm).
    @return float cell in mm (unchanged without imported copper or with the 'fill' mapping, which has its own warning).
    """
    src = CopperSource.of(problem)
    if src is None or src.mapping == "fill":
        return float(cell_mm)
    return float(min(cell_mm, COARSE_CELL_MM))


def auto_cell_note(problem, cell_mm):
    """!
    @brief The sentence to show when Auto had to leave the 1 mm cap of an imported board because of the memory.
    @param problem A Problem.
    @param cell_mm Cell that Auto returned (mm).
    @return str, or "" when there is no imported copper or the cell is within the cap.
    """
    src = CopperSource.of(problem)
    if src is None or src.mapping == "fill" or cell_mm <= COARSE_CELL_MM + 1e-9:
        return ""
    return (f"Auto: the board has imported copper, which wants a cell of {num(COARSE_CELL_MM, 1)} mm or less, but the memory limit needs {num(cell_mm, 2)} mm; "
            "the result is a screening estimate" if cell_mm > SCREENING_CELL_MM else
            f"Auto: the cell was enlarged to {num(cell_mm, 2)} mm by the memory limit, above the {num(COARSE_CELL_MM, 1)} mm that imported copper wants")
