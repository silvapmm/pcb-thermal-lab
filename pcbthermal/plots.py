#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file plots.py
@brief Matplotlib figures shared by the command line tool and the GUI.

@details Every `draw_*` function renders into a Figure it is given (no pyplot, no global state), so
the GUI can embed the figure in a Qt canvas and the command line can save it to a file. The
`plot_*` and `save_*` wrappers create an off-screen Figure and write a PNG or GIF.
"""

import functools
import math
from dataclasses import dataclass, field as dc_field

import numpy as np
from matplotlib import ticker
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.cm import ScalarMappable
from matplotlib.colors import LightSource, Normalize
from matplotlib.figure import Figure
from scipy import ndimage

from .geometry import points_in_polygon, zone_fill
from .numfmt import PLAIN_MAX, PLAIN_MIN, eng, num
from .results import model_label

CMAPS = ("inferno", "hot", "viridis", "plasma", "magma", "turbo", "coolwarm")

# Ways of drawing a map (the "View" combo of the Results tabs); "current" is the cells as solved and the only mode of the files and the report
VIEW_MODES = ("current", "smooth", "terrain")
VIEW_LABELS = {"current": "Current", "smooth": "Smooth", "terrain": "Terrain"}
COPPER_IMAGE_PIXELS = 640            # Longest side of the copper picture under the map (zones are rasterised on it; masks are reduced to it)
UPSAMPLE_PIXELS = 1_500_000          # Most pixels of the upsampled field of Terrain and of the contours (the factor shrinks to fit)
MAX_CONTOURS = 60                    # A contour step that would draw more lines than this is made larger


def engineering_ticks(fig):
    """!
    @brief Write the tick labels of every numeric axis of a figure with the number format of the program (plain decimal in the window, engineering notation outside it).
    @param fig Matplotlib figure (axes and colour bars included).
    @return The figure.
    @note Category axes (the labels of a bar chart) keep their own labels; the unit stays in the axis label.
    """
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            if isinstance(axis.get_major_formatter(), (ticker.ScalarFormatter, ticker.LogFormatter)):
                axis.set_major_formatter(_ProgramFormatter())
                if axis.get_scale() == "log":
                    lo, hi = axis.get_view_interval()
                    if lo > 0 and np.log10(hi / lo) > 6.0:
                        # A tick per decade, written 10.00E-6, 100.00E-6, 1.00E-3, ..., crowds the axis: one every three decades is the step of the notation
                        axis.set_major_locator(ticker.LogLocator(base=1000.0, numticks=20))
    return fig


class _ProgramFormatter(ticker.Formatter):
    """!
    @brief Tick formatter with the number format of the program that keeps the labels of an axis distinct.

    @note A fixed four significant digits wrote the same label on several ticks of a narrow range (85.300 to 85.320 gave
          "85.3" four times, 25.0000 to 25.0004 gave "25" on every tick), where the default formatter uses an offset.
          The digits grow until the labels differ.
    """

    def __call__(self, value, pos=None):
        """!
        @brief Label of one value (also the cursor read-out).
        @param value Tick value.
        @param pos Tick position (unused).
        @return str Label.
        """
        return num(value, 4)

    def format_ticks(self, values):
        """!
        @brief Labels of all the ticks of an axis, with as many digits as needed for them to differ.
        @param values Tick values.
        @return list of str.
        """
        values = list(values)
        distinct = len(set(values))
        for digits in range(4, 13):
            labels = [num(v, digits) for v in values]
            if len(set(labels)) == distinct:
                return labels
        for decimals in range(3, 10):                    # A narrow range outside the plain window: more decimals in the mantissa
            labels = [eng(v, decimals) if v != 0 and not PLAIN_MIN <= abs(v) < PLAIN_MAX else num(v, 12) for v in values]
            if len(set(labels)) == distinct:
                return labels
        return labels


def _with_engineering_ticks(draw):
    """!
    @brief Decorator of the draw_* functions: after drawing, give the axes the number format of the program.
    @param draw A function whose first argument is the figure.
    @return The wrapped function with the same name, documentation and result.
    """
    @functools.wraps(draw)
    def wrapper(fig, *args, **kwargs):
        """!
        @brief Draw, then format the ticks.
        @param fig Figure.
        @param args Positional arguments of the drawing function.
        @param kwargs Keyword arguments of the drawing function.
        @return What the drawing function returns.
        """
        result = draw(fig, *args, **kwargs)
        engineering_ticks(fig)
        return result
    return wrapper


def new_figure(width=7.0, height=4.5):
    """!
    @brief Create an off-screen figure that can be saved without a display.
    @param width Width in inches.
    @param height Height in inches.
    @return Figure with an Agg canvas attached.
    """
    fig = Figure(figsize=(width, height), layout="constrained")
    FigureCanvasAgg(fig)
    return fig


def _off_board(field, problem, dx, dy):
    """!
    @brief The field with the samples that lie off a non-rectangular board replaced by NaN (drawn blank).
    @param field Array (ny, nx) of cell or node values.
    @param problem The Problem (board outline).
    @param dx Spacing along x in metres.
    @param dy Spacing along y in metres.
    @return The same array for a rectangular board, a copy with NaN outside the outline otherwise.
    """
    b = problem.board
    if not b.has_outline():
        return field
    xs, ys, _ = _field_axes(field, problem, dx, dy)
    X, Y = np.meshgrid(xs / 1000.0, ys / 1000.0)
    return np.where(points_in_polygon(X, Y, b.outline), field, np.nan)


def _outline(ax, problem, layer):
    """!
    @brief Draw heater, heatsink, zone and via outlines of one layer on an axis (coordinates in mm).
    @param ax Matplotlib axis.
    @param problem The Problem that owns the elements.
    @param layer 0-based layer index.
    """
    if problem.board.has_outline():
        o = np.vstack([problem.board.outline, problem.board.outline[:1]]) * 1000.0
        ax.plot(o[:, 0], o[:, 1], color="white", lw=1.4)
    for z in problem.zones:
        if z.layer == layer:
            p = np.vstack([z.polygon, z.polygon[:1]]) * 1000.0
            ax.plot(p[:, 0], p[:, 1], color="#7ee787", lw=0.8, ls="-", alpha=0.6)
    for h in problem.heaters:
        if h.layer == layer:
            p = np.vstack([h.polygon, h.polygon[:1]]) * 1000.0
            ax.plot(p[:, 0], p[:, 1], color="white", lw=1.2, ls="--")
    for s in problem.heatsinks:
        if s.layer == layer:
            p = np.vstack([s.polygon, s.polygon[:1]]) * 1000.0
            ax.plot(p[:, 0], p[:, 1], color="cyan", lw=1.2, ls=":")
    if problem.vias:
        ax.plot([v.x * 1000.0 for v in problem.vias], [v.y * 1000.0 for v in problem.vias], "k.", ms=3)


EQUIVALENT_LABEL = "rectangle solved (same area as the outline"


def _solved_view(problem, dx, dy, scale):
    """!
    @brief The geometry that the Lumped and Analytic models really solved for a board with an outline.
    @details They solve `Problem.equivalent_rectangle` (box, positions, zones, vias and heatsinks scaled by s about the origin, parts of the
             same size moved to the scaled centre) and the result is stretched back by 1/s onto the real box (`api._run_model`). Drawing the
             field on its solved spacing (dx s, dy s) with the elements of that rectangle puts the field, the parts and the dashed edge in one
             frame, so the drawn rectangle has the size its legend gives.
    @param problem The Problem with an outline.
    @param dx Spacing along x of the stretched field in metres.
    @param dy Spacing along y of the stretched field in metres.
    @param scale s of `Problem.equivalent_rectangle` (0 < s <= 1).
    @return Tuple (rectangular Problem as solved, dx_solved, dy_solved).
    """
    q, _ = problem.equivalent_rectangle()
    return q, dx * scale, dy * scale


def _equivalent_lines(ax, problem, solved, color):
    """!
    @brief Draw the edge of the solved rectangle (dashed, `color`) and the real outline (thin grey) for comparison.
    @param ax Matplotlib axis (coordinates in mm).
    @param problem The Problem with the real outline.
    @param solved The rectangular Problem that was solved (`_solved_view`).
    @param color Colour of the dashed edge.
    @return List of the two Line2D (for a legend).
    """
    W, H = solved.board.width * 1000.0, solved.board.height * 1000.0
    rect, = ax.plot([0, W, W, 0, 0], [0, 0, H, H, 0], color=color, lw=1.8, ls=(0, (6, 3)), clip_on=False, zorder=5,
                    label=f"{EQUIVALENT_LABEL}, {W:.1f} x {H:.1f} mm)")
    o = np.vstack([problem.board.outline, problem.board.outline[:1]]) * 1000.0
    real, = ax.plot(o[:, 0], o[:, 1], color="#9a9a9a", lw=1.0, ls=":", zorder=4, label="real outline")
    return [rect, real]


def _field_axes(field, problem, dx, dy):
    """!
    @brief Sample positions and image extent of a field that holds either cell values or values at grid points.
    @details A node field (finite-difference model) has one more sample than the board has cells along each axis.
    @param field Array (ny, nx).
    @param problem The Problem (board size).
    @param dx Spacing along x in metres.
    @param dy Spacing along y in metres.
    @return Tuple (xs_mm, ys_mm, extent_mm) with extent = [x0, x1, y0, y1] of the image.
    """
    ny, nx = field.shape
    b = problem.board
    nodes = nx == int(round(b.width / dx)) + 1 and ny == int(round(b.height / dy)) + 1
    off = 0.0 if nodes else 0.5
    xs, ys = (np.arange(nx) + off) * dx * 1000.0, (np.arange(ny) + off) * dy * 1000.0
    if nodes:
        ext = [-0.5 * dx * 1000.0, b.width * 1000.0 + 0.5 * dx * 1000.0, -0.5 * dy * 1000.0, b.height * 1000.0 + 0.5 * dy * 1000.0]
    else:
        ext = [0.0, b.width * 1000.0, 0.0, b.height * 1000.0]
    return xs, ys, ext


@dataclass
class MapView:
    """!
    @brief How a field map is drawn: the mode of the View combo and its settings (display only, the solver result is never touched).
    @details `mode` "current" is the map exactly as it always was (the cells as solved, nearest neighbour). "smooth" interpolates the cells bicubically
             (cosmetic: the data below the cell do not exist). "terrain" shades the upsampled field as a relief (matplotlib LightSource) and draws
             contour lines every `contour_step`, labelled every second one. `show_copper` (any mode) draws the copper of the layer, grey on a darker
             laminate, under the field, which then has `opacity`.
    """
    mode: str = "current"                       # One of VIEW_MODES
    contour_step: float = 5.0                   # Distance between contour lines in the unit of the field (K); 0 or less picks a round step by itself
    show_copper: bool = False                   # Draw the copper of the layer under the field
    opacity: float = 0.7                        # Opacity of the field over the copper when show_copper is on (0 to 1)
    copper_rgb: tuple = (0.75, 0.76, 0.79)      # Colour of the copper under the map (the GUI passes the theme token)
    laminate_rgb: tuple = (0.30, 0.30, 0.30)    # Colour of the bare laminate under the map
    contour_color: str = "#ffffff"              # Colour of the contour lines
    cache: dict = dc_field(default_factory=dict)  # {layer: copper image}; the owner keeps it as long as the problem is the same


def copper_image(problem, layer, max_px=COPPER_IMAGE_PIXELS):
    """!
    @brief The copper of one layer as a picture for the copper under the map: the imported mask of the layer if it has one, else the zones.
    @details Rows run from the bottom of the board, like the field maps. An imported mask (rows from the top) is reduced by a whole factor so its
             longest side is at most `max_px` (block mean, the part of a block left over at the far edge is dropped); zones are rasterised with
             `geometry.zone_fill` on at most `max_px` cells along the longest side (2 x 2 samples per cell), so the hatch fill of a zone shows as grey.
    @param problem The Problem.
    @param layer 0-based copper layer.
    @param max_px Longest side of the picture in pixels.
    @return float32 array (ny, nx) with the copper fraction 0 to 1 (all zero for a layer without copper).
    """
    from . import copper                                    # Local import: copper.py reads the model, plots.py is imported first by the CLI

    src = copper.CopperSource.of(problem)
    if src is not None and layer in src.entries:
        cov = src.raster(layer)
        f = max(1, int(math.ceil(max(cov.shape) / float(max_px))))
        r, c = (cov.shape[0] // f) * f, (cov.shape[1] // f) * f
        if f > 1 and r > 0 and c > 0:
            cov = (cov[:r, :c].reshape(r // f, f, c // f, f).sum(axis=(1, 3), dtype=np.uint32) // (f * f)).astype(np.uint8)
        return np.ascontiguousarray(cov[::-1], dtype=np.float32) / np.float32(255.0)
    b = problem.board
    step = max(b.width, b.height) / float(max_px)
    nx, ny = max(1, int(round(b.width / step))), max(1, int(round(b.height / step)))
    return zone_fill(problem.zones, b.layers, nx, ny, b.width / nx, b.height / ny, samples=2)[layer].astype(np.float32)


def _nice_step(span, target=8):
    """!
    @brief A round contour step (1, 2, 5 or 10 times a power of ten) that gives about `target` lines over `span`.
    @param span Range of the field (largest minus smallest value).
    @param target Wanted number of lines.
    @return Step in the unit of the field (1.0 when the span is not positive).
    """
    if not np.isfinite(span) or span <= 0:
        return 1.0
    raw = span / target
    mag = 10.0 ** math.floor(math.log10(raw))
    return min((m * mag for m in (1, 2, 5, 10) if m * mag >= raw), default=raw)


def _upsampled(field, ext, factor_max=4):
    """!
    @brief The field resampled on a finer lattice (cubic spline) for the relief and the contour lines, with its cell-centre coordinates.
    @details NaN samples (cells off an outline) are filled with the nearest value before the spline, so they do not spread, and blanked again afterwards.
    @param field Array (ny, nx), NaN allowed.
    @param ext Image extent [x0, x1, y0, y1] in mm.
    @param factor_max Largest upsampling factor (the factor shrinks so that the result has at most UPSAMPLE_PIXELS pixels).
    @return Tuple (z, xs, ys) with z of shape (ny*k, nx*k) (NaN where the source was NaN, values kept inside the range of the field) and the
            coordinates of its columns and rows in mm.
    """
    ny, nx = field.shape
    k = int(max(1, min(factor_max, math.sqrt(UPSAMPLE_PIXELS / max(1, nx * ny)))))
    bad = np.isnan(field)
    if bad.all():
        z = np.full((ny * k, nx * k), np.nan)
    else:
        src = field
        if bad.any():
            idx = ndimage.distance_transform_edt(bad, return_distances=False, return_indices=True)
            src = field[tuple(idx)]
        z = ndimage.zoom(src, k, order=3 if k > 1 else 0, mode="nearest")
        z = np.clip(z, np.nanmin(field), np.nanmax(field))         # The spline overshoots the cell values a little: keep the range
        if bad.any():
            z = np.where(ndimage.zoom(bad.astype(np.uint8), k, order=0) > 0, np.nan, z)
    xs = ext[0] + (np.arange(z.shape[1]) + 0.5) * (ext[1] - ext[0]) / z.shape[1]
    ys = ext[2] + (np.arange(z.shape[0]) + 0.5) * (ext[3] - ext[2]) / z.shape[0]
    return z, xs, ys


def _contour_lines(ax, z, xs, ys, view, thin=False):
    """!
    @brief Contour lines every `view.contour_step`, those at a multiple of twice the step thicker and labelled.
    @param ax Matplotlib axis.
    @param z Array (len(ys), len(xs)) of the upsampled field.
    @param xs Column coordinates in mm.
    @param ys Row coordinates in mm.
    @param view MapView (step and colour).
    @param thin If True draw the lines a little lighter (over the copper).
    @return None.
    """
    if np.isnan(z).all():
        return
    lo, hi = float(np.nanmin(z)), float(np.nanmax(z))
    if not hi > lo:
        return
    step = view.contour_step if view.contour_step and view.contour_step > 0 else _nice_step(hi - lo)
    step = max(step, (hi - lo) / MAX_CONTOURS)                   # A tiny step on a wide range would draw hundreds of lines
    levels = np.arange(math.ceil(lo / step) * step, hi, step)
    if len(levels) == 0:
        return
    ax.contour(xs, ys, z, levels=levels, colors=view.contour_color, linewidths=0.4 if thin else 0.5, alpha=0.75)
    # Every second line is thicker and carries its value (the multiples of twice the step)
    major = np.array([lv for lv in levels if int(round(lv / step)) % 2 == 0])
    if len(major):
        cs = ax.contour(xs, ys, z, levels=major, colors=view.contour_color, linewidths=0.9)
        ax.clabel(cs, fmt="%g", fontsize=6, inline=True)


def _draw_map(ax, field, problem, dx, dy, layer, cmap, vmin, vmax, view, solved_view=False):
    """!
    @brief Paint a field on an axis in the mode of `view` and return the object for the colour bar.
    @details "current" is the original `imshow` call, argument for argument. The other modes only add: a bicubic image, a shaded relief with
             contour lines, or the field at `view.opacity` over the copper of the layer. No mode changes the data or the colour limits.
    @param ax Matplotlib axis (coordinates in mm).
    @param field Array (ny, nx) already blanked off the outline.
    @param problem The Problem that gives the frame of the field (the rectangle as solved for a Lumped or Analytic result on an outline).
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param layer 0-based layer (copper under the map).
    @param cmap Colormap name.
    @param vmin Lower colour limit (None: smallest value).
    @param vmax Upper colour limit (None: largest value).
    @param view MapView or None (None is "current").
    @param solved_view True when the frame is the equivalent rectangle: the copper is then not drawn there (masks and zones are on the real board).
    @return The AxesImage or ScalarMappable to give to `Figure.colorbar`.
    """
    xs, ys, ext = _field_axes(field, problem, dx, dy)
    lo = np.nanmin(field) if vmin is None else vmin
    hi = np.nanmax(field) if vmax is None else vmax
    mode = "current" if view is None else view.mode
    copper_on = view is not None and view.show_copper
    if mode == "current" and not copper_on:
        return ax.imshow(field, origin="lower", cmap=cmap, extent=ext, vmin=lo, vmax=hi)
    alpha = float(view.opacity) if copper_on else None
    if copper_on:
        _draw_copper(ax, problem, layer, view, solved_view)
    if mode == "current":
        return ax.imshow(field, origin="lower", cmap=cmap, extent=ext, vmin=lo, vmax=hi, alpha=alpha)
    if mode == "smooth":
        return ax.imshow(field, origin="lower", cmap=cmap, extent=ext, vmin=lo, vmax=hi, interpolation="bicubic", interpolation_stage="data", alpha=alpha)
    z, zx, zy = _upsampled(field, ext)
    norm = Normalize(lo, hi)
    mappable = ScalarMappable(norm, cmap)
    # Terrain: hillshade of the cubic upsampling, the field itself is the relief (overlay blend keeps the colour map readable)
    ls = LightSource(azdeg=315, altdeg=40)
    zz = np.where(np.isnan(z), 0.0 if np.isnan(z).all() else np.nanmin(z), z)
    rgb = np.array(ls.shade(zz, cmap=mappable.cmap, norm=norm, blend_mode="overlay", vert_exag=2.5,
                            dx=(ext[1] - ext[0]) / z.shape[1], dy=(ext[3] - ext[2]) / z.shape[0]))
    rgb[..., 3] = np.where(np.isnan(z), 0.0, 1.0 if alpha is None else alpha)       # Cells off the outline stay blank
    ax.imshow(rgb, origin="lower", extent=ext, interpolation="bilinear")
    _contour_lines(ax, z, zx, zy, view, thin=copper_on)
    return mappable


def _draw_copper(ax, problem, layer, view, solved_view):
    """!
    @brief Draw the copper of a layer (grey) on a darker laminate as the background of a map.
    @param ax Matplotlib axis (coordinates in mm).
    @param problem The Problem.
    @param layer 0-based layer.
    @param view MapView (colours and the picture cache).
    @param solved_view True for the equivalent rectangle of a Lumped or Analytic result on an outline: plain laminate and a note.
    @return None.
    """
    b = problem.board
    box = [0.0, b.width * 1000.0, 0.0, b.height * 1000.0]
    if solved_view:
        base = np.zeros((1, 1, 4), np.float32)
        base[0, 0] = (*view.laminate_rgb, 1.0)
        ax.text(0.01, 0.01, "copper not drawn on the solved rectangle", transform=ax.transAxes, fontsize=6, color=view.contour_color, va="bottom", zorder=6)
    else:
        cov = view.cache.get(layer)
        if cov is None:
            cov = view.cache[layer] = copper_image(problem, layer)
        c = np.clip(cov, 0.0, 1.0)[..., None]
        base = np.empty(cov.shape + (4,), dtype=np.float32)
        base[..., :3] = np.asarray(view.laminate_rgb, np.float32) * (1 - c) + np.asarray(view.copper_rgb, np.float32) * c
        base[..., 3] = 1.0
        if b.has_outline():                                         # Nothing is drawn where there is no board
            X, Y = np.meshgrid((np.arange(cov.shape[1]) + 0.5) * b.width / cov.shape[1], (np.arange(cov.shape[0]) + 0.5) * b.height / cov.shape[0])
            base[..., 3] = points_in_polygon(X, Y, b.outline)
    ax.imshow(base, origin="lower", extent=box, interpolation="nearest")


@_with_engineering_ticks
def draw_field(fig, field, problem, dx, dy, title="", cmap="inferno", vmin=None, vmax=None,
               layer=0, outline=True, marker=None, hotspot=None, label="Temperature (°C)", equivalent_scale=None, equivalent_color="#ffb000", view=None):
    """!
    @brief Draw one layer of a scalar field over the board, with outlines and a colour bar.
    @param fig Target Figure (cleared first).
    @param field Array (ny, nx) of the layer to show.
    @param problem The Problem (board size and outlines).
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param title Axes title.
    @param cmap Matplotlib colormap name.
    @param vmin Lower colour limit (default: field minimum).
    @param vmax Upper colour limit (default: field maximum).
    @param layer 0-based layer used for the outlines.
    @param outline If True draw zones, heaters, heatsinks and vias.
    @param marker Optional (x_m, y_m) of a marker, for example the hottest point.
    @param hotspot Optional temperature; the contour at that level is drawn in magenta.
    @param label Colour bar label.
    @param equivalent_scale Scale s of the equivalent rectangle (`SteadyResult.equivalent_scale`) of a Lumped or Analytic result on a board with
           an outline: the field is drawn as solved, on the rectangle of the same area with its parts, the rectangle dashed and the real outline
           dotted, with a legend; None (or a board without an outline) draws the field stretched onto the real box as usual.
    @param equivalent_color Colour of that dashed line.
    @param view Optional MapView (Smooth, Terrain, copper under the map); None or mode "current" without copper is the original picture.
    @return The axes.
    """
    fig.clear()
    ax = fig.add_subplot(111)
    b = problem.board
    real = problem
    solved_view = equivalent_scale is not None and b.has_outline()
    if solved_view:
        problem, dx, dy = _solved_view(problem, dx, dy, equivalent_scale)   # One frame: the solved field, its parts and its edge
        if marker is not None:
            marker = (marker[0] * equivalent_scale, marker[1] * equivalent_scale)
    field = _off_board(field, problem, dx, dy)
    xs, ys, ext = _field_axes(field, problem, dx, dy)
    im = _draw_map(ax, field, problem, dx, dy, layer, cmap, vmin, vmax, view, solved_view)
    if hotspot is not None and np.nanmax(field) > hotspot > np.nanmin(field):
        ax.contour(xs, ys, field, levels=[hotspot], colors="#ff00cc", linewidths=1.2)
    if outline:
        _outline(ax, problem, layer)
    if marker is not None:
        ax.plot(marker[0] * 1000, marker[1] * 1000, "c+", ms=12, mew=1.5)
    if solved_view:
        lines = _equivalent_lines(ax, real, problem, equivalent_color)
        fig.legend(handles=lines, loc="outside lower center", fontsize=7, ncols=1, framealpha=0.7)
    ax.set_xlim(0, b.width * 1000)
    ax.set_ylim(0, b.height * 1000)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=10)
    fig.colorbar(im, ax=ax, label=label, shrink=0.85)
    return ax


@_with_engineering_ticks
def draw_block(fig, result, problem, face, cmap="inferno"):
    """!
    @brief Temperature of the metal block of one face (where there is no block the board map is not shown).
    @param fig Target Figure (cleared first).
    @param result A SteadyResult with block temperatures (FVM or FDM).
    @param problem The Problem.
    @param face 0 for the block on the top face, 1 for the bottom face.
    @param cmap Colormap name.
    """
    tag = "top" if face == 0 else "bottom"
    names = [k for k in ("block_top_max", "block_bottom_max") if k in result.extras]
    which = [k.split("_")[1] for k in names].index(tag) if f"block_{tag}_max" in result.extras else None
    fig.clear()
    ax = fig.add_subplot(111)
    if which is None:
        ax.text(0.5, 0.5, "This model has no metal block", ha="center", va="center", transform=ax.transAxes)
        return
    field = np.where(result.arrays["block_cov"][which] > 0, result.arrays["block_T"][which], np.nan)
    draw_field(fig, field, problem, result.dx, result.dy, cmap=cmap, layer=0 if face == 0 else problem.board.layers - 1,
               title=f"{result.model.upper()} - metal block ({tag} face): mean {result.extras[f'block_{tag}_mean']:.1f} °C, "
                     f"max {result.extras[f'block_{tag}_max']:.1f} °C", label="Block temperature (°C)")


@_with_engineering_ticks
def draw_fields(fig, result, problem, cmap="inferno", show_equivalent=True, equivalent_color="#ffb000", view=None, grid=False):
    """!
    @brief All layers side by side (or in a grid of two columns) with a shared colour scale.
    @param fig Target Figure (cleared first).
    @param result A SteadyResult with a field.
    @param problem The Problem.
    @param cmap Colormap name.
    @param show_equivalent If True and the result ran on the equivalent rectangle of an outline board (`result.equivalent_scale`), draw every
           layer as solved (the rectangle of the same area with its parts, dashed, the real outline dotted; one legend below the figure);
           False draws the field stretched onto the real box.
    @param equivalent_color Colour of that dashed line.
    @param view Optional MapView (Smooth, Terrain, copper under the maps); None draws the cells as solved.
    @param grid If True the layers are in a grid of two columns (2 x 2 for four layers) instead of one row.
    """
    fig.clear()
    b = problem.board
    real = problem
    s = result.equivalent_scale
    solved_view = show_equivalent and s is not None and b.has_outline()
    dx, dy = result.dx, result.dy
    if solved_view:
        problem, dx, dy = _solved_view(problem, dx, dy, s)                  # One frame for the field, the parts and the dashed edge
    T = np.stack([_off_board(t, problem, dx, dy) for t in result.T])
    L = T.shape[0]
    vmin, vmax = float(np.nanmin(T)), float(np.nanmax(T))
    if grid:
        ncol = 2 if L > 1 else 1
        flat = fig.subplots(int(math.ceil(L / ncol)), ncol, squeeze=False).ravel()
        for ax in flat[L:]:
            ax.set_visible(False)                                            # An odd layer count leaves one empty cell
        axes = flat[:L]
    else:
        ncol = L
        axes = fig.subplots(1, L, squeeze=False)[0]
    im, lines = None, None
    for l, ax in enumerate(axes):
        im = _draw_map(ax, T[l], problem, dx, dy, l, cmap, vmin, vmax, view, solved_view)
        ax.set_xlim(0, b.width * 1000)
        ax.set_ylim(0, b.height * 1000)
        _outline(ax, problem, l)
        if solved_view:
            lines = _equivalent_lines(ax, real, problem, equivalent_color)
        ax.set_title(f"Layer {l + 1}  (mean {result.layer_mean[l]:.1f} °C)", fontsize=9)
        ax.set_xlabel("x (mm)")
        ax.set_aspect("equal")
        if l % ncol == 0:
            ax.set_ylabel("y (mm)")
    loc = result.t_max_location
    if loc is not None and loc[0] < L:
        f = s if solved_view else 1.0                                       # The location is stored on the real box (stretched back)
        axes[loc[0]].plot(loc[1] * 1000 * f, loc[2] * 1000 * f, "c+", ms=10)
    fig.colorbar(im, ax=list(axes), label="Temperature (°C)", shrink=0.9)
    if lines:
        # One legend for the figure, below the maps: inside the first small axis it squeezed the layout of every layer
        fig.legend(handles=lines, loc="outside lower center", fontsize=7, ncols=1, framealpha=0.7)
    fig.suptitle(f"{result.model.upper()}: Tmax {result.t_max:.1f} °C, Rθ {result.r_theta:.2f} K/W, "
                 f"power balance {num(result.balance_error, sign=True)}", fontsize=10)


@_with_engineering_ticks
def draw_profile(fig, results, problem, layer=0, axis="x", position_mm=None):
    """!
    @brief Temperature along a line through the board for every model.
    @param fig Target Figure (cleared first).
    @param results Dict {model: SteadyResult}.
    @param problem The Problem.
    @param layer 0-based layer.
    @param axis "x" for a horizontal cut at y = position, "y" for a vertical cut at x = position.
    @param position_mm Cut position in mm (default: the hottest point of the reference model).
    """
    fig.clear()
    ax = fig.add_subplot(111)
    b = problem.board
    ref = results.get("fvm") or next(iter(results.values()))
    if position_mm is None and ref.t_max_location is not None:
        position_mm = (ref.t_max_location[2] if axis == "x" else ref.t_max_location[1]) * 1000.0
    position_mm = position_mm if position_mm is not None else (b.height if axis == "x" else b.width) * 500.0
    for name, r in results.items():
        if r.T is None:
            continue
        T = _off_board(r.T[min(layer, r.T.shape[0] - 1)], problem, r.dx, r.dy)
        xs, ys = r.coords()
        if axis == "x":
            i = int(np.argmin(np.abs(ys * 1000.0 - position_mm)))
            ax.plot(xs * 1000, T[i], label=name)
        else:
            j = int(np.argmin(np.abs(xs * 1000.0 - position_mm)))
            ax.plot(ys * 1000, T[:, j], label=name)
    ax.set_xlabel(("x" if axis == "x" else "y") + " (mm)")
    ax.set_ylabel(f"Layer {layer + 1} temperature (°C)")
    ax.set_title(f"Cut along {axis} at {'y' if axis == 'x' else 'x'} = {position_mm:.1f} mm", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend()


@_with_engineering_ticks
def draw_comparison(fig, results):
    """!
    @brief Bar chart comparing the maximum and mean temperature of the models.
    @param fig Target Figure (cleared first).
    @param results Dict {model: SteadyResult}.
    """
    fig.clear()
    ax = fig.add_subplot(111)
    names = list(results)
    x = np.arange(len(names))
    ax.bar(x - 0.2, [results[n].t_max for n in names], 0.4, label="Tmax")
    ax.bar(x + 0.2, [results[n].t_mean for n in names], 0.4, label="Tmean")
    for k, n in enumerate(names):
        ax.text(k - 0.2, results[n].t_max + 0.5, f"{results[n].t_max:.1f}", ha="center", fontsize=8)
        ax.text(k + 0.2, results[n].t_mean + 0.5, f"{results[n].t_mean:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([model_label(n) for n in names])        # "Lumped (LPTN)", as the tables, not the key `lumped`
    ax.set_ylabel("Temperature (°C)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)


@_with_engineering_ticks
def draw_bars(fig, labels, series, ylabel="Temperature (°C)", title=""):
    """!
    @brief Grouped bar chart, for example heater or zone temperatures.
    @param fig Target Figure (cleared first).
    @param labels Category names.
    @param series Dict {series name: list of values (nan allowed)}.
    @param ylabel Y axis label.
    @param title Chart title.
    """
    fig.clear()
    ax = fig.add_subplot(111)
    n = max(len(series), 1)
    x = np.arange(len(labels))
    width = 0.8 / n
    for k, (name, vals) in enumerate(series.items()):
        vals = [np.nan if v is None else v for v in vals]
        ax.bar(x + (k - (n - 1) / 2) * width, vals, width, label=name)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8)


@_with_engineering_ticks
def draw_convergence(fig, rows):
    """!
    @brief Maximum temperature versus FVM cell size.
    @param fig Target Figure (cleared first).
    @param rows List of (cell_mm, t_max, seconds).
    """
    fig.clear()
    ax = fig.add_subplot(111)
    rows = sorted(rows)
    ax.plot([r[0] for r in rows], [r[1] for r in rows], "o-")
    ax.invert_xaxis()
    ax.set_xlabel("Cell size (mm)")
    ax.set_ylabel("Tmax (°C)")
    ax.set_title("FVM grid convergence")
    ax.grid(alpha=0.3)


@_with_engineering_ticks
def draw_transient(fig, tr):
    """!
    @brief Maximum and mean temperature versus time with the steady-state level.
    @param fig Target Figure (cleared first).
    @param tr A TransientResult.
    """
    fig.clear()
    ax = fig.add_subplot(111)
    t = tr.times[1:]
    ax.semilogx(t, tr.t_max[1:], label="Tmax")
    ax.semilogx(t, tr.t_mean[1:], label="Tmean")
    ax.axhline(tr.steady_t_max, color="gray", ls="--", label="steady Tmax")
    tau = tr.time_constant()
    if np.isfinite(tau):
        ax.axvline(tau, color="C3", ls=":", label=f"63 % at {tau:.1f} s")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Temperature (°C)")
    ax.grid(alpha=0.3, which="both")
    ax.legend()


@_with_engineering_ticks
def draw_profile_series(fig, result, problem, limit_c=None):
    """!
    @brief Temperature of the last window versus time: the hottest point of the board and under every heater, a part at its face (the node plus the drop over the laminate where its copper is absent).
    @param fig Target Figure (cleared first).
    @param result A ProfileResult with a time simulation.
    @param problem The Problem (heater names).
    @param limit_c Optional temperature limit drawn as a line.
    """
    fig.clear()
    ax = fig.add_subplot(111)
    t = result.times - result.times[0]
    ax.plot(t, result.t_max, color="#888888", lw=4.0, alpha=0.5, zorder=1, label="hottest of the board (nodes and part faces)")
    for j, h in enumerate(problem.heaters):
        if h.profile is not None or len(problem.heaters) > 1:
            ax.plot(t, result.t_heaters[j], lw=1.0, label=h.name or f"Heater {j + 1}")
    ax.axhline(result.steady_average_max, color="#2a9d8f", ls="--", lw=1.0, label="steady, average power")
    ax.axhline(result.steady_peak_max, color="#e63946", ls=":", lw=1.0, label="steady, peak power (bound)")
    if limit_c is not None:
        ax.axhline(limit_c, color="#ff00cc", lw=1.2, label=f"limit {num(limit_c)} °C")
    ax.set_xlabel("Time in the last window (s)")
    ax.set_ylabel("Temperature (°C)")
    ax.set_title(f"{result.model.upper()}: peak {result.peak:.1f} °C, minimum {result.minimum:.1f} °C, "
                 f"oscillation {result.oscillation:.1f} °C", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)


@_with_engineering_ticks
def draw_peak_map(fig, result, problem, layer=0, cmap="inferno"):
    """!
    @brief Highest temperature reached at every point during the last window.
    @param fig Target Figure (cleared first).
    @param result A ProfileResult with a time simulation.
    @param problem The Problem.
    @param layer 0-based layer.
    @param cmap Colormap name.
    """
    draw_field(fig, result.peak_map[layer], problem, result.dx, result.dy, cmap=cmap, layer=layer,
               title=f"{result.model.upper()} - layer {layer + 1}: peak temperature during the cycle "
                     f"(max {float(result.peak_map[layer].max()):.1f} °C)", label="Peak temperature (°C)")


@_with_engineering_ticks
def draw_waveforms(fig, problem, cycles=2.0):
    """!
    @brief Power of every heater with a profile over a few periods of the slowest one.
    @param fig Target Figure (cleared first).
    @param problem The Problem.
    @param cycles Number of periods of the longest wave shown.
    """
    fig.clear()
    ax = fig.add_subplot(111)
    waves = [(i, h) for i, h in enumerate(problem.heaters) if h.profile is not None]
    if not waves:
        ax.text(0.5, 0.5, "No heater has a power profile", ha="center", va="center", transform=ax.transAxes)
        return
    # Show a few periods of the slowest repeating profile, or the whole length of a one-shot profile
    longest = max(h.profile.period for _, h in waves)
    span = (cycles if any(h.profile.repeat for _, h in waves) else 1.05) * longest
    t = np.linspace(0.0, span, 4000, endpoint=False)
    for i, h in waves:
        w = h.profile
        label = f"{h.name or f'Heater {i + 1}'}: average {w.average():.2f} W"
        iv = w.intervals()
        lo, hi = min(p for _, _, p in iv), max(p for _, _, p in iv)
        if w.repeat and span / w.period > 40:
            # Too many cycles to draw: show the swing as a band and the average as a line
            line, = ax.plot(t, np.full_like(t, w.average()), lw=1.4, label=label + f" (repeats at {num(1.0 / w.period)} Hz)")
            ax.fill_between(t, lo, hi, color=line.get_color(), alpha=0.18)
            continue
        edges = np.array([a for a, _, _ in iv])
        values = np.array([p for _, _, p in iv])
        phase = t % w.period if w.repeat else np.minimum(t, w.period - 1e-12)
        p = values[np.clip(np.searchsorted(edges, phase, side="right") - 1, 0, len(values) - 1)]
        if not w.repeat:
            p = np.where(t > w.period, values[-1], p)                       # The last power is held after the end
        ax.step(t, p, where="post", lw=1.4, label=label + ("" if w.repeat else " (one-shot)"))
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Power (W)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)


# ------------------------------------------------------------------ file wrappers

def plot_profile_series(result, problem, path):
    """!
    @brief Save the temperature-versus-time plot of a time simulation.
    @param result A ProfileResult.
    @param problem The Problem.
    @param path Output PNG path.
    """
    fig = new_figure(7.5, 4.5)
    draw_profile_series(fig, result, problem)
    _save(fig, path)


def plot_peak_map(result, problem, path):
    """!
    @brief Save the peak-temperature map of the top layer.
    @param result A ProfileResult.
    @param problem The Problem.
    @param path Output PNG path.
    """
    fig = new_figure(6.5, 5.0)
    draw_peak_map(fig, result, problem)
    _save(fig, path)


def _save(fig, path, dpi=150):
    """!
    @brief Save a figure as PNG.
    @param fig Figure with an Agg canvas.
    @param path Output path.
    @param dpi Resolution.
    """
    fig.savefig(path, dpi=dpi)


def plot_fields(result, problem, path):
    """!
    @brief Save the all-layers temperature map.
    @param result A SteadyResult with a field.
    @param problem The Problem.
    @param path Output PNG path.
    """
    fig = new_figure(4.6 * result.T.shape[0] + 1.2, 4.6)
    draw_fields(fig, result, problem)
    _save(fig, path)


def plot_profiles(results, problem, path):
    """!
    @brief Save the temperature profile through the hottest row of the top layer.
    @param results Dict {model: SteadyResult}.
    @param problem The Problem.
    @param path Output PNG path.
    """
    fig = new_figure(7, 4)
    draw_profile(fig, results, problem)
    _save(fig, path)


def plot_comparison(results, path):
    """!
    @brief Save the model comparison bars.
    @param results Dict {model: SteadyResult}.
    @param path Output PNG path.
    """
    fig = new_figure(6, 4)
    draw_comparison(fig, results)
    _save(fig, path)


def plot_convergence(rows, path):
    """!
    @brief Save the grid convergence plot.
    @param rows List of (cell_mm, t_max, seconds).
    @param path Output PNG path.
    """
    fig = new_figure(6, 4)
    draw_convergence(fig, rows)
    _save(fig, path)


def plot_transient(tr, path):
    """!
    @brief Save the transient curves.
    @param tr A TransientResult.
    @param path Output PNG path.
    """
    fig = new_figure(7, 4)
    draw_transient(fig, tr)
    _save(fig, path)


def frame_spacing(tr, problem):
    """!
    @brief Sample spacing of the frames of a transient: cells for the FVM and Analytic, grid points for the FDM.
    @param tr A TransientResult.
    @param problem The Problem (board size).
    @return Tuple (dx, dy) in metres.
    """
    ny, nx = tr.frames.shape[2], tr.frames.shape[3]
    if tr.grid == "nodes":
        return problem.board.width / (nx - 1), problem.board.height / (ny - 1)
    return problem.board.width / nx, problem.board.height / ny


def save_transient_gif(tr, problem, path, layer=0, fps=8, cmap="inferno"):
    """!
    @brief Animated GIF of the temperature evolution of one layer in physical time.
    @details Frames come from the transient FVM solution (implicit time stepping of the same
             matrices as the steady solution), so the time shown is real time, not solver iterations.
    @param tr A TransientResult.
    @param problem The Problem.
    @param path Output GIF path.
    @param layer 0-based layer shown.
    @param fps Frames per second.
    @param cmap Colormap name.
    """
    from matplotlib.animation import PillowWriter

    vmin, vmax = tr.ambient, float(tr.frames[:, layer].max())
    fig = new_figure(6.2, 5.0)
    dx, dy = frame_spacing(tr, problem)
    writer = PillowWriter(fps=fps)
    with writer.saving(fig, path, dpi=90):
        for k in range(len(tr.times)):
            draw_field(fig, tr.frames[k, layer], problem, dx, dy, cmap=cmap, vmin=vmin, vmax=vmax,
                       layer=layer, title=f"Layer {layer + 1}  t = {tr.times[k]:.2f} s  "
                                          f"Tmax = {tr.t_max[k]:.1f} °C")
            writer.grab_frame()
