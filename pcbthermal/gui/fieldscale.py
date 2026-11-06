#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file fieldscale.py
@brief What the temperature map on the editor canvas shares with the Results view: the colour limits, the cells that lie on the board and the cases in which the map is
       refused. No Qt widgets here, so the rules can be tested alone.
"""

import numpy as np

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


def inside_mask(board, shape, dx, dy, nodes=False):
    """!
    @brief The cells of a result grid that lie on the board (False outside the outline).
    @param board model.Board whose outline is used (no outline: every cell is on the board).
    @param shape tuple (ny, nx) of the field.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param nodes True when the field holds values at grid points (the first sample sits at 0): the outline is shifted by half a cell so that a node stands for the cell around it.
    @return Boolean array (ny, nx).
    """
    ny, nx = shape
    if not board.has_outline():
        return np.ones((ny, nx), bool)
    poly = board.outline
    if nodes:
        poly = [(x + 0.5 * dx, y + 0.5 * dy) for x, y in poly]
    return np.asarray(coverage_fraction(poly, nx, ny, dx, dy, 8)) > 0.0


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
