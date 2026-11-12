#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fieldscale.py
@brief What the temperature map on the editor canvas shares with the Results view: the colour limits, the cells that lie on the board and the cases in which the map is
       refused. No Qt widgets here, so the rules can be tested alone.
"""

import numpy as np

from ..analysis import extreme_points  # noqa: F401  (moved to the GUI-free analysis module; the editor overlay and the Results maps share it)
from ..geometry import coverage_fraction


def colour_limits(field, auto=True, vmin=None, vmax=None):
    """!
    @brief The colour limits of a field, as the Results view applies them.
    @details With Auto range the limits are the extremes of the field (NaN ignored); otherwise the typed values, with the lower one kept below the upper one, so the Results
             view and the overlay show the same colour for the same temperature.
    @param field Array of temperatures in degC.
    @param auto True for the automatic range.
    @param vmin Typed lower limit in degC (used when `auto` is False).
    @param vmax Typed upper limit in degC (used when `auto` is False).
    @return tuple (low, high) in degC with high > low.
    """
    if auto or vmin is None or vmax is None:
        lo, hi = float(np.nanmin(field)), float(np.nanmax(field))
    else:
        lo, hi = float(vmin), float(vmax)
    if hi <= lo:
        hi = lo + 1e-9                                    # A flat field still has a scale
    return lo, hi


def results_limits(field, problem, dx, dy, auto=True, vmin=None, vmax=None):
    """!
    @brief The colour limits that the Results Temperature tab gives a field of this problem.
    @details With Auto range the Results view takes the extremes of the samples whose centre lies on the board (`plots._off_board` blanks the others): on a board with
             an outline the cells off it are held at the ambient and would otherwise pull the lower limit down to it, so the overlay would colour the same
             temperature differently from the tab. Typed limits are used as they are.
    @param field Array (ny, nx) of temperatures in degC (cells or grid points).
    @param problem model.Problem shown (its outline).
    @param dx Spacing along x in metres.
    @param dy Spacing along y in metres.
    @param auto True for the automatic range.
    @param vmin Typed lower limit in degC (used when `auto` is False).
    @param vmax Typed upper limit in degC (used when `auto` is False).
    @return tuple (low, high) in degC with high > low.
    """
    from ..plots import _off_board                       # The rule of the Results map itself, so the two can never drift apart

    if auto or vmin is None or vmax is None:
        on = _off_board(field, problem, dx, dy)
        if np.isfinite(on).any():                         # A board so small that no sample centre is on it keeps the whole field
            field = on
        return colour_limits(field)
    return colour_limits(field, False, vmin, vmax)


def inside_mask(problem, shape, dx, dy):
    """!
    @brief The cells of a result grid that the Results map draws (False where it leaves them blank).
    @details It is the rule of the Results Temperature tab itself, `plots._off_board`: a sample is on the board when its CENTRE lies inside the outline, so a cell that
             the outline cuts through a rounded corner but whose centre is outside is blank in both views (the overlay used to paint any cell with a coverage above zero).
             Node fields (one more sample than cells per axis) are recognised by their shape as the Results map does.
    @param problem model.Problem shown (its board outline).
    @param shape tuple (ny, nx) of the field.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @return Boolean array (ny, nx).
    """
    from ..plots import _off_board                       # One rule for the two views, so they cannot drift apart

    return np.isfinite(_off_board(np.zeros(shape), problem, dx, dy))


def nice_ticks(lo, hi, n=4):
    """!
    @brief Round tick values for a colour bar.
    @details The step is 1, 2 or 5 times a power of ten, chosen to give about `n` intervals, and the values are multiples of it inside [lo, hi].
    @param lo Lower limit in the unit of the field.
    @param hi Upper limit in the unit of the field.
    @param n Wanted number of intervals (at least 1).
    @return tuple (values, step): list of floats and the step used (same unit).
    """
    span = max(float(hi) - float(lo), 1e-12)
    raw = span / max(int(n), 1)
    mag = 10.0 ** np.floor(np.log10(raw))
    step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw * 0.999)
    first = np.ceil(lo / step - 1e-9)
    vals = []
    k = first
    while k * step <= hi + 1e-9 * span:
        vals.append(round(float(k * step), 12))
        k += 1
    return vals, float(step)


def tick_label(value, step):
    """!
    @brief Text of one colour bar tick: plain decimals with only the digits the step needs (one at most for steps of 0.1 and more), the project's number rules outside 0.01 to 10000.
    @param value Tick value in the unit of the field.
    @param step Tick step in the same unit.
    @return str.
    """
    from ..numfmt import num

    a = abs(value)
    if value != 0 and (a < 0.01 or a >= 10000):
        return num(value)                                  # Engineering notation of the project outside the plain window
    decimals = 0 if step >= 1 - 1e-9 else int(min(2, max(1, np.ceil(-np.log10(step) - 1e-9))))
    text = f"{value:.{decimals}f}"
    return "0" if float(text) == 0 else text               # No "-0.0"


def place_colourbar(view, board, avoid, size, margin=8):
    """!
    @brief Where the colour bar goes in the view so that it does not cover the board.
    @details Candidates are tried in order (right column, left column, each from the top, the middle and the bottom); the first that touches neither the board rectangle
             nor the rectangles in `avoid` (rulers, scale bar) wins. When the board fills the view (zoomed in) the candidate that covers the least board is used.
    @param view tuple (width, height) of the viewport in pixels.
    @param board tuple (x, y, w, h) of the board on screen in pixels.
    @param avoid list of tuples (x, y, w, h) in pixels to keep clear (the rulers and the scale bar).
    @param size tuple (w, h) of the bar with its labels in pixels.
    @param margin Gap to the view border in pixels.
    @return tuple (x, y, w, h, covers_board): the box in pixels and True when it still overlaps the board.
    """
    vw, vh = view
    w, h = size

    def inter(a, b):
        dx = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
        dy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
        return max(dx, 0) * max(dy, 0)

    ruler = 18
    ys = (ruler + margin, max((vh - h) / 2.0, ruler + margin), vh - h - margin)
    xs = (vw - w - margin, ruler + margin)
    cands = [(x, y, w, h) for x in xs for y in ys]
    best = None
    for c in cands:
        over_board = inter(c, board)
        over_other = sum(inter(c, a) for a in avoid)
        score = (over_other > 0, over_board, over_other)
        if best is None or score < best[0]:
            best = (score, c)
        if over_board == 0 and over_other == 0:
            break
    c = best[1]
    return (float(c[0]), float(c[1]), float(w), float(h), inter(c, board) > 0)


def overlay_refusal(result, problem):
    """!
    @brief Why a result cannot be painted on the editor canvas, or None when it can.
    @details The Lumped and Analytic models of a board with an outline run on the rectangle of the same area and their field is stretched back onto the box; the editor draws
             the real board, so the field would sit in the wrong place (see the Equiv. rect. box of the Results view). Such a map is refused instead of drawn wrong.
    @param result results.SteadyResult shown.
    @param problem model.Problem that is open in the editor.
    @return str with the note for the status bar, or None.
    """
    if problem.board.has_outline() and getattr(result, "equivalent_scale", None) is not None:
        return "The overlay is not drawn for the stretched map of a board with an outline (Lumped or Analytic): choose the FVM or FDM result, or see the Results tab."
    return None


MODEL_SHORT = {"fvm": "FVM", "fdm": "FDM", "lumped": "Lumped", "analytic": "Analytic", "solid3d": "3D solid"}   # Title of the card of the map on the board
