#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file checks.py
@brief Model-validity checks: warnings about inputs that make a result physically doubtful.

@details These checks never stop a simulation. They catch situations in which the solvers would silently do
something the user probably did not intend, for example moving the power of a heater that sticks out of the
board onto the part that is inside, or placing a heater where there is no copper to spread the heat. The text
of every warning says what is wrong and what to do.
"""

import math
import time

import numpy as np
from scipy import ndimage

from . import blocks, convection, copper, laminate, lumped, solid3d, stackimpedance, viaconstriction, viawell
from .geometry import OUTLINE_MAX_CROSSINGS, outline_crossings, coverage_fraction, part_board_share, points_in_polygon, polygon_overlap_area, bbox_overlap_pairs, polygon_area, polygon_centroid, polygon_self_intersects
from .numfmt import num
from .uicontext import cell_where, laminate_where, using_ui

# Where to change the cell, appended to every warning that tells the user to use another cell size: uicontext.cell_where() names the control of the window or the option of the command line

# The finest cell that Auto (api.suggest_cell_mm, lo=0.25) gives: the cell warning of an imported board must not recommend a finer one
IMPORTED_CELL_FLOOR_MM = 0.25

# A plate under a source is called thick when the through-thickness drop q'' t / (2 k) exceeds this fraction of the heater's rise
THICK_PLATE_LIMIT = 0.05

# A fin channel is called close when its channel Rayleigh number is below this value: the channel then keeps less than 90 % of the coefficient of the
# isolated plate (phi(90) = 0.90, research/fin-channel)
FIN_CHANNEL_RA_LIMIT = 90.0
FIN_CHANNEL_RA_BOUND = 14.0    # Below it the loss is given as an upper bound


class CheckWarning(str):
    """!
    @brief A warning text that also knows which element it is about, so the interface can select that element when the warning is clicked.

    @details It is a plain string (the full text) for every other use (printing, joining, comparing), with three extra attributes: kind, index and
             short, the one-line form that the live list under Run shows (the full text is its tooltip). See line().
    """

    kind = None
    index = None
    short = None                                   # One-line form of the text for the live list; None when the text is already one line


def line(w):
    """!
    @brief The one-line form of a warning for the live list: its short text, or the full text when it has none.
    @param w A warning (CheckWarning or plain string).
    @return str One-line text.
    """
    return getattr(w, "short", None) or str(w)


TITLE_MAX = 64                                   # Characters of a warning title (the accordion row of the interface)
TITLE_COLON_WORDS = 7                            # A colon ends the title only after a first clause of this many words ("Analytic model:", "Via 3 and 1 more vias:" are prefixes)
_SEVERE_WORDS = ("will not run", "cannot", "refus", "unsafe", "did not converge", "too hot", "very hot", "heats nothing", "runaway", "unreliable",
                 "not valid", "wrong")


def warning_title(w):
    """!
    @brief A short clean title for a warning (the closed row of the accordion): its first clause, at most TITLE_MAX characters, with a capital first letter.
    @details The checks return plain sentences, so this is a classifier on the text and not a stored field: the first clause ends at the first semicolon, at
             the first full stop, at a parenthesis after the first 20 characters, or at a colon that closes a first clause of at least TITLE_COLON_WORDS
             words (four words for a clause that follows a prefix), whichever comes first. A shorter text before a colon is a prefix (a part name "U1:", a model "Analytic model:", "lumped:", "Via 3 and 1 more
             vias:") and stays in the title with the clause that follows it (the review found titles that were only "Analytic model" or "Lumped and Analytic").
    @param w A warning (CheckWarning or plain string).
    @return str The title, without a final full stop.
    """
    text = " ".join(line(w).split())
    cuts = [len(text)]
    for token, minimum in ((";", 0), (". ", 0), (" (", 20)):
        at = text.find(token, minimum)
        if at > 0:
            cuts.append(at)
    at, start = text.find(": "), 0
    while 0 < at < min(cuts):                    # The first colon that closes a whole clause (not a prefix) ends the title
        # A first clause needs TITLE_COLON_WORDS words; a clause after a prefix ("lumped: the board has an outline:") needs four
        if len(text[start:at].split()) >= (TITLE_COLON_WORDS if start == 0 else 4):
            cuts.append(at)
            break
        start, at = at + 2, text.find(": ", at + 2)
    title = text[:min(cuts)].rstrip(" .,;:")
    if len(title) > TITLE_MAX:
        title = title[:TITLE_MAX].rsplit(" ", 1)[0].rstrip(" .,;:") + "…"
    title = title or text[:TITLE_MAX]
    return title[:1].upper() + title[1:]


def warning_severity(w):
    """!
    @brief The severity of a warning for the interface: "high" for a result that is wrong, refused or unsafe, otherwise "note".
    @param w A warning (CheckWarning or plain string).
    @return str "high" or "note".
    """
    text = str(w).lower()
    return "high" if any(word in text for word in _SEVERE_WORDS) else "note"


def _add(out, kind, index, text, short=None):
    """!
    @brief Append a warning to a list, tagged with the element it is about.
    @param out List of warnings being built.
    @param kind Element kind ("zone", "heater", "heatsink" or "via"), or None for a warning about the whole design.
    @param index 0-based index of the element in its list, or None.
    @param text Full warning text (what the Results summary shows and the tooltip of the live list).
    @param short One-line form for the live list under Run (None: the full text is already short).
    """
    w = CheckWarning(text)
    w.short = short
    w.kind = kind
    w.index = index
    out.append(w)


def check_problem(problem, cell_mm=1.0, models=None):
    """!
    @brief List the validity warnings of a problem.
    @param problem A Problem (assumed structurally valid, see Problem.validate).
    @param cell_mm Cell size (mm) of the raster used for the geometric checks and the FVM mesh.
    @param models  Model keys that will run, or None (every model): the warning about a copper edge across a footprint concerns only the Lumped and Analytic models.
    @return List of warning strings (empty when nothing is doubtful).
    """
    b = problem.board
    W, H = b.width, b.height
    nx = max(int(round(W * 1000.0 / cell_mm)), 8)
    ny = max(int(round(H * 1000.0 / cell_mm)), 8)
    dx, dy = W / nx, H / ny
    out = []
    board_cover = b.cover(nx, ny, dx, dy)               # Ones for a rectangular board

    # --- Copper fill of every layer (union of its zones, the imported layers from their masks), used by several checks
    try:
        fill = copper.problem_fill(problem, nx, ny, dx, dy, 4)
        imported_layers = set(copper.CopperSource.of(problem).layers) if copper.has_imported(problem) else set()
    except ValueError as exc:
        # Damaged or mismatched imported copper: every run would refuse it, so say why here and check the rest on the drawn zones
        _add(out, None, None, f"The imported copper cannot be used: {exc}.", "The imported copper cannot be used (see the details).")
        fill = copper.problem_fill(problem, nx, ny, dx, dy, 4, source=False)
        imported_layers = set()

    heater_poly = []                                    # Footprint of every heater with an area (None otherwise), for the exact overlap test
    for k, h in enumerate(problem.heaters):
        name = h.name or f"Heater {k + 1}"
        if h.role == "source":
            # A pure source has no junction and no package top: these fields (from a file or the API; the interface zeroes them) are not used
            ignored = [label for label, value in (("theta", h.theta), ("theta_jc_top", h.theta_jc_top), ("theta_sa", h.theta_sa), ("interface", h.interface),
                                                  ("contact_area", h.contact_area), ("pad_thickness", h.pad_thickness), ("pad_k", h.pad_k)) if value > 0]
            if ignored:
                _add(out, "heater", k, f"{name}: a heat source ignores {', '.join(ignored)}; they belong to a component (set its type to Component, or clear them).",
                 f"{name}: a heat source ignores {', '.join(ignored)}.")
        area = polygon_area(h.polygon)
        if area <= 0:
            _add(out, "heater", k, f"{name}: the footprint has zero area.")
            heater_poly.append(None)
            continue
        cov = coverage_fraction(h.polygon, nx, ny, dx, dy, 4)
        heater_poly.append(h.polygon)
        # Share of the part on the board from the geometry itself (exact clip to the box; a lattice on the part for an outline), not from the cell
        # raster: the 4 x 4 samples per cell read a part under about two cells as partly outside although it was inside
        inside = part_board_share(h.polygon, W, H, b.outline if b.has_outline() else None)
        if inside <= 0.0:
            # Nothing of the part is on the board: there is no "part that is inside" to take the power
            _add(out, "heater", k, f"{name}: the whole footprint is outside the board, so the part heats nothing; move it onto the board.",
                 f"{name}: the footprint is entirely outside the board.")
        elif inside < 0.98:
            _add(out, "heater", k, f"{name}: {100 * (1 - inside):.0f} % of the footprint is outside the board; its full power "
                       "is applied to the part that is inside.", f"{name}: {100 * (1 - inside):.0f} % of the footprint is outside the board.")
        n_across = min(np.ptp(h.polygon[:, 0]), np.ptp(h.polygon[:, 1])) / min(dx, dy)
        if n_across < 3:
            side_mm = min(np.ptp(h.polygon[:, 0]), np.ptp(h.polygon[:, 1])) * 1000.0
            if not imported_layers:
                _add(out, "heater", k, f"{name}: the smallest side is only {n_across:.1f} cells wide; use a cell size of "
                           f"{side_mm / 4:.2f} mm or less ({cell_where()}).")
            elif cell_mm > IMPORTED_CELL_FLOOR_MM + 1e-9:
                # Auto never goes below 0.25 mm, so a finer cell is not offered for imported copper (the masks and the memory grow with 1 / cell^2)
                rec = max(side_mm / 4, IMPORTED_CELL_FLOOR_MM)
                note = (" " + copper.SMALL_PART_CELL_NOTE_TEXT + ".") if cell_mm >= 1.0 - 1e-9 else ""
                _add(out, "heater", k, f"{name}: the smallest side is only {n_across:.1f} cells wide; use a cell size of {rec:.2f} mm "
                           f"(the finest cell that Auto gives for imported copper; {cell_where()}).{note}",
                     f"{name}: the smallest side is only {n_across:.1f} cells wide; use a cell size of {rec:.2f} mm.")
            else:
                _add(out, "heater", k, f"{name}: the smallest side is only {n_across:.1f} cells wide even at the finest cell that Auto gives for imported copper "
                           f"({IMPORTED_CELL_FLOOR_MM:g} mm); the reference moved 3 to 30 % between 0.5 and 0.25 mm for the small parts measured, so read this part "
                           "with care (a sample, not a bound).",
                     f"{name}: the smallest side is only {n_across:.1f} cells wide at the finest Auto cell; read it with care.")
        if cov.sum() > 0:
            f_mean = float((fill[h.layer] * cov).sum() / cov.sum())
            if f_mean < 0.02:
                _add(out, "heater", k, f"{name}: there is no copper under it on layer {h.layer + 1}; the heat can only spread "
                           "through the FR-4 and the part will run very hot.", f"{name}: no copper under it on layer {h.layer + 1}; it will run very hot.")
            elif f_mean < 0.98 and h.layer not in imported_layers and (models is None or {"lumped", "analytic"} & set(models)):
                # Only the reduced models are unreliable here, and an imported layer has its own, stronger warning (the gaps between the pins of a QFN
                # already read as an edge): so no message on an FVM-only run or on imported copper
                _add(out, "heater", k, f"{name}: a copper edge or hatching crosses its footprint (copper fill {f_mean:.2f}); the "
                           "Lumped and Analytic models are unreliable here, use the FVM.",
                     f"{name}: a copper edge crosses its footprint (fill {f_mean:.2f}); use the FVM.")

    # Only the pairs whose bounding boxes overlap can overlap (polygon_overlap_area returns 0 for the others at once), found by a sweep so that
    # a board with hundreds of parts does not pay for every pair; the pairs come in the order of the double loop, so the warnings keep their order
    areas = [polygon_area(h.polygon) if p is not None else 0.0 for h, p in zip(problem.heaters, heater_poly)]
    for i, j in bbox_overlap_pairs(heater_poly):
        hi, hj = problem.heaters[i], problem.heaters[j]
        if hi.layer == hj.layer:
            # Exact area of the intersection of the two footprints: the 4 x 4 cover of each cell made neighbours 0.3 mm apart "overlap" when
            # both covers touched the same cell
            overlap = polygon_overlap_area(hi.polygon, hj.polygon)
            small = min(areas[i], areas[j])
            if overlap > 0.05 * small:
                _add(out, "heater", i, f"{hi.name or f'Heater {i + 1}'} and {hj.name or f'Heater {j + 1}'} overlap on layer "
                           f"{hi.layer + 1} ({100 * overlap / small:.0f} % of the smaller footprint): their power densities add up.", f"{hi.name or f'Heater {i + 1}'} and {hj.name or f'Heater {j + 1}'} overlap "
                           f"({100 * overlap / small:.0f} % of the smaller).")

    # A via is judged by its drill disc against the outline (or the box): no board under it = ignored by every model; less than half = mostly off
    for k, (v, share) in enumerate(zip(problem.vias, problem.via_board_shares())):
        name = v.name or f"Via {k + 1}"
        if share <= 0.0:
            _add(out, "via", k, f"{name}: via outside the board outline and ignored by every model." if b.has_outline()
                 else f"{name} is outside the board and is ignored by every model.")
        elif share < 0.5:
            _add(out, "via", k, f"{name}: more than half of the via is outside the board{' outline' if b.has_outline() else ''}; "
                                "the models still count its whole barrel, on the part that is on the board.",
                 f"{name}: more than half of the via is outside the board.")

    for k, z in enumerate(problem.zones):
        area = polygon_area(z.polygon)
        # Share on the board from the geometry (exact clip to the box, a lattice on the zone for an outline): the 2 x 2 samples per cell read a small
        # zone inside the board as mostly outside, and the raster ignored the outline
        if area > 0 and part_board_share(z.polygon, W, H, b.outline if b.has_outline() else None) < 0.5:
            _add(out, "zone", k, f"{z.name or f'Zone {k + 1}'}: more than half of the zone is outside the board.")
        if polygon_self_intersects(z.polygon):
            _add(out, "zone", k, f"{z.name or f'Zone {k + 1}'}: the outline crosses itself; the fill follows the even-odd rule, so the crossed part is left empty. "
                       "Redraw the zone without the crossing.", f"{z.name or f'Zone {k + 1}'}: the outline crosses itself.")
        if z.layer in imported_layers:
            # copper.override_fill: the masks of an imported layer are the whole copper of that layer, so a zone drawn there changes nothing
            _add(out, "zone", k, f"{z.name or f'Zone {k + 1}'}: copper layer {z.layer + 1} is imported, and its masks replace the drawn zones of that layer: "
                                 "this zone is ignored by every model.", f"{z.name or f'Zone {k + 1}'}: ignored, its layer is imported.")

    # --- Metal blocks: they only take heat where they overlap copper of their face
    block_cov = {}
    for k, s in enumerate(problem.heatsinks):
        if not s.is_block():
            continue
        name = s.name or f"Heatsink {k + 1}"
        # Measured against the board outline, not only against the box: a block over the cut-away part of a board has no board under it
        cov = coverage_fraction(s.polygon, nx, ny, dx, dy, 4) * board_cover
        area = polygon_area(s.polygon)
        # Same geometric share as the parts: a 3 mm block on a 2.5 mm cell read as partly outside at 2 of 10 positions with the cell cover
        if area > 0 and part_board_share(s.polygon, W, H, b.outline if b.has_outline() else None) < 0.9:
            _add(out, "heatsink", k, f"{name}: part of the metal block is outside the board" + (" outline" if b.has_outline() else "") +
                       "; the FVM, FDM and 3D solid cut it there and model only the part inside (the Lumped and Analytic models take the block "
                       "whole on the rectangle of the same area).", f"{name}: part of the metal block is outside the board.")
        if cov.sum() > 0:
            overlap = float((fill[s.layer] * cov).sum() * dx * dy)
            if overlap < 1e-6:
                _add(out, "heatsink", k, f"{name}: the metal block does not overlap any copper on its face, so it takes almost no heat "
                           "(through the bare laminate only); add a copper pad under it.",
                     f"{name}: the metal block touches no copper; add a copper pad under it.")
            elif overlap < 0.25 * area:
                _add(out, "heatsink", k, f"{name}: only {100 * overlap / area:.0f} % of the metal block touches copper; the heat enters "
                           "the block through that overlap only.", f"{name}: only {100 * overlap / area:.0f} % of the metal block touches copper.")
        if s.interface_resistance() < 1e-5:
            _add(out, "heatsink", k, f"{name}: an interface resistance below 10.00E-6 m2K/W is a perfect contact; a gap pad or paste is "
                       "usually 100.00E-6 to 1.00E-3 m2K/W (0.5 mm of a 1 to 5 W/mK pad).",
                     f"{name}: an interface resistance below 10.00E-6 m2K/W is a perfect contact.")
        face = 0 if (s.layer == 0 or b.layers == 1) else 1
        block_cov.setdefault(face, []).append((name, s.polygon))
    for face, items in block_cov.items():
        for i, j in bbox_overlap_pairs([np.asarray(it[1], dtype=float) for it in items]):
            if polygon_overlap_area(items[i][1], items[j][1]) > 1e-10:      # Exact; 1e-10 m2 is 0.0001 mm2 (touching blocks do not overlap)
                _add(out, None, None, f"{items[i][0]} and {items[j][0]} overlap: in the overlap only the later one is used.")

    if problem.total_power() <= 0:
        _add(out, None, None, "The total heater power is zero: the board stays at ambient temperature.")
    return out


def check_input(problem, models, cell_mm=1.0, live=False, ui=None):
    """!
    @brief Every warning that can be known before a run: the validity checks, the documented limits of the selected models and the via checks.
    @details The one list that the application shows live under the Run button (at every edit and change of the models or the cell, after a short pause)
             and that api.simulate puts at the head of the warnings of a run, so the Results summary holds the same warnings in the same order (the window checks at a
             cell of at least 0.5 mm, so below that cell the texts that quote cells can differ) and adds after them only what a run knows. The text of a warning is
             the full measured one (Results summary, tooltip of the live list); its attribute short is the one-line form that the live list shows (see line()). Only cheap geometry is
             used (rasters of the board at the cell, point-in-polygon tests, the tile plan of the Analytic correction, no solve: about 0.2 s for 8500 vias and 20 parts,
             0.5 s on an outline); the warnings that need a run (thick plates, close fins, the zone model of the Lumped, the models' own notes) are only in the Results.
    @param problem A Problem (assumed structurally valid).
    @param models Iterable of model keys that will run.
    @param cell_mm Cell size (mm) of the raster used for the geometric tests.
    @param live True for the list under the Run button: the partial-copper via pass then stops after PARTIAL_COPPER_BUDGET_S seconds and the warning says "at least N"
           (the run's own list, live False, has the whole count).
    @param ui 'gui' (texts name the controls of the window), 'cli' (texts name the command-line options) or None for the context in force (uicontext; 'cli' by default).
    @return List of warning strings (CheckWarning, tagged with the element) in the order validity, model limits, vias.
    """
    models = tuple(models)
    with using_ui(ui):
        return _check_input(problem, models, cell_mm, live)


def _outline_warning(text):
    """!
    @brief A whole-design warning about the board outline.
    @param text Full warning text.
    @return CheckWarning tagged with no element.
    """
    out = []
    _add(out, None, None, text, "The board outline is too complex for this cell (see the details).")
    return out[0]


def _check_input(problem, models, cell_mm, live=False):
    """!
    @brief Body of check_input, run in the context of the caller.
    @param problem A Problem.
    @param models Tuple of model keys.
    @param cell_mm Cell size in mm.
    @param live True for the live list (time cap of the partial-copper pass).
    @return List of warnings.
    """
    # An outline of very many long edges is refused by the grid models (cut-cell links, edge distance) before any memory is taken: say so here, in plain words,
    # and run no other check on it (the checks below sample the outline and the warning would only repeat the refusal)
    b = problem.board
    if b.has_outline():
        try:
            crossings = outline_crossings(np.asarray(b.outline, dtype=float), cell_mm * 1e-3)
        except ValueError as exc:
            return [_outline_warning(f"{exc}.")]
        if crossings > OUTLINE_MAX_CROSSINGS:
            return [_outline_warning(f"The board outline has {len(b.outline)} edges that cross about {crossings / 1e6:.0f} million grid lines at this cell, more than the "
                                     f"{OUTLINE_MAX_CROSSINGS // 1_000_000} million the grid models accept, so the run would be refused. Simplify the outline (fewer or shorter edges) "
                                     "or use a coarser cell.")]
    return (check_problem(problem, cell_mm, models) + check_model_limits(problem, models, cell_mm) + check_lumped_near_edge(problem, models)
            + check_lumped_small_part(problem, models, cell_mm) + check_via_limits(problem, models, cell_mm)
            + check_via_partial_copper(problem, models, cell_mm, PARTIAL_COPPER_BUDGET_S if live else None) + check_via_uncoupled(problem, models)
            + check_fast_wave(problem))


# The fast-wave warnings (docs/validation.md 37): the frequency from which a wave on bare laminate is warned about (1 Hz: the review measured 0.73 to 0.78 of the 3D
# reference at 1 Hz for bare laminate and for copper under half the part, 0.91 to 0.97 at 0.3 Hz and below; the research had proposed 3 Hz), and the slowest wave (period in s) for which a part near
# a board edge is warned about
FAST_BARE_HZ = 1.0
EDGE_WAVE_PERIOD_S = 1.0


def check_fast_wave(problem):
    """!
    @brief Warnings about power waves that the closed form of the fast-wave ripple does not cover (plain text, live).
    @details The closed-form impedance of the stack under a part (stackimpedance, docs/theory.md 10.5) replaces the node swing of the layered models for a fast repeating profile
             (square wave or table) where there is copper under the part. Four cases are warned, one line per case and heater:
             (a) bare laminate under the part (fill below stackimpedance.MIN_FILL) and a wave of FAST_BARE_HZ or faster: the closed form does not apply and the program's swing is
                 0.73 at 1 Hz and up to 2.2 times too small between 3 and 50 Hz, while the face term makes it up to 2.4 times too large at 1 kHz (docs/validation.md 37.2);
             (b) a part whose gap to the nearest side of the board (or of its outline) is shorter than the radius of its disc, for a wave slower than 1 Hz: the closed form treats
                 the board as infinite and reads 0.61 of the truth at 0.1 Hz for a 5 mm part 1 mm from two sides (the program is also low there);
             (c) a metal block on the board and a stretch shorter than profiles.fast_stretch_limit: the closed form is switched off and the node structure is kept, which
                 understates a short stretch (not measured with a block);
             (d) a one-shot table with a stretch shorter than that limit: a one-shot profile is always time-stepped by the node structure (no closed form for it).
    @note The thresholds are measured on rectangular boards of 1.6 mm with equal gaps; an outline enters only through the gap to its nearest side.
    @param problem A Problem.
    @return List of warnings (CheckWarning, tagged with the heater).
    """
    from . import profiles                                           # Local import: lumped (imported here) imports profiles, so a module-level import could be circular
    out = []
    limit = profiles.fast_stretch_limit(problem.board.layers)
    for k, h in enumerate(problem.heaters):
        w = h.profile
        if w is None:
            continue
        name = h.name or f"Heater {k + 1}"
        square = getattr(w, "kind", "") == "square"
        if square and (w.p_on <= w.p_off or not 0.0 < w.duty < 1.0):
            continue                                                  # No swing of the power: nothing to warn about
        if not square and float(np.ptp(np.asarray(w.powers, dtype=float))) <= 0.0:
            continue
        if not w.repeat:
            if w.shortest_feature() < limit:
                _add(out, "heater", k,
                     f"{name}: its power table runs once and has a stretch of {num(w.shortest_feature(), 3)} s, shorter than {num(limit)} s. A table that runs once is simulated "
                     "step by step with one temperature per copper layer, which reads the swing of so short a stretch too small (2 to 3 times at 1 to 3 Hz, up to 12 times above "
                     "50 Hz on a repeating wave). Take the swing as a lower estimate, or make the table repeat if the load is periodic.",
                     f"{name}: a one-shot table with a short stretch; its swing is a lower estimate.")
            continue
        freq = 1.0 / w.period
        col, status = stackimpedance.column_for_heater(problem, k)
        if status == "bare" and freq >= FAST_BARE_HZ:
            _add(out, "heater", k,
                 f"{name}: the part has no copper under it on its layer and its power wave repeats {num(freq, 3)} times a second. The layered models cannot follow a wave that fast over "
                 "bare laminate: at 1 Hz the temperature swing they compute is about 0.75 of the true one and between 3 and 50 Hz up to 2.2 times too small, and from about 300 Hz the allowance for the laminate over bare "
                 "copper makes it too large (2.4 times at 1 kHz). Take the swing as an estimate, or put copper under the part.",
                 f"{name}: a fast wave on bare laminate; the swing is not reliable (2.2 times too small near 10 Hz, 2.4 times too large at 1 kHz).")
        elif status == "block" and w.shortest_feature() < limit:
            _add(out, "heater", k,
                 f"{name}: its power changes within {num(w.shortest_feature(), 3)} s and the board has a metal block. The closed form that corrects the swing of fast waves is not "
                 "used on a board with a metal block, so the swing is the one of the layered models, which reads a stretch this short too small (2 to 12 times on a board without "
                 "a block). Take the swing as a lower estimate.",
                 f"{name}: a fast wave on a board with a metal block; the swing is a lower estimate.")
        elif col is not None and w.period > EDGE_WAVE_PERIOD_S:
            side, gap = heater_side_gap(problem, h.polygon)
            if gap < col.radius:
                _add(out, "heater", k,
                     f"{name}: the part is {num(gap * 1e3, 3)} mm from a side of the board and its power wave is slower than 1 Hz. The closed form used for the swing of a wave "
                     "treats the board as infinite, so near a side it reads too low (0.61 of the true swing at 0.1 Hz for a 5 mm part 1 mm from two sides, 0.88 at 1 Hz), and the "
                     "layered model is low there too. Take the swing as a lower estimate.",
                     f"{name}: a slow wave near a side of the board; the swing is a lower estimate.")
    return out


# Models whose layered idealisation has no vertical path through a bare cell of a gap (research/bare-spot-under-source, INTEGRATION P3)
LAYERED_MODELS = ("fvm", "fdm", "lumped", "analytic")


# Thresholds of the edge rule: centroid offset in units of the smaller footprint side, and the footprint side ratio (research/lumped-zones-adoption 8.4)
VIA_OFFSET_FRACTION = 0.1
VIA_SIDE_RATIO = 1.5


def _board_via_groups(vx, vy, on_board):
    """!
    @brief Group label and nearest-neighbour distance of every via, by the single-linkage rule of the via constriction (vias with no board under them get
           the label -1 and an infinite distance).
    @param vx x of the vias in m.
    @param vy y of the vias in m.
    @param on_board Boolean array, True for a via with board under it.
    @return tuple (labels, d_nn): numpy.ndarray of int labels and numpy.ndarray of nearest-neighbour distances in m, one per via.
    """
    labels = -np.ones(len(vx), dtype=int)
    d_nn = np.full(len(vx), np.inf)
    idx = np.flatnonzero(on_board)
    if idx.size:
        pts = np.column_stack([vx[idx], vy[idx]])
        d_nn[idx] = viaconstriction.nearest_neighbour(pts)
        labels[idx] = viaconstriction.via_groups(pts, d_nn[idx])
    return labels, d_nn


def _lumped_via_cases(polygon, vx, vy, inside, groups, d_nn):
    """!
    @brief The three geometric cases in which the Lumped model reads a part with a via group too cool: the group continues past the edge of the footprint,
           its vias stand off the footprint centre, the footprint is elongated. Only a group of two or more vias with at least one under the footprint counts.
    @param polygon Footprint polygon, sequence of (x, y) in m.
    @param vx x of all the vias in m.
    @param vy y of all the vias in m.
    @param inside Boolean array, True for the vias (with board under them) inside the footprint.
    @param groups Group label of every via (-1 for none), from _board_via_groups.
    @param d_nn Nearest-neighbour distance of every via in m, from _board_via_groups.
    @return Tuple (across, off_centre, elongated) of bool; all False when no group qualifies.
    @note The reach of the "across" case: a via of the group outside the footprint counts only when it lies within twice the median nearest-neighbour distance of the
          group's vias in the footprint (the pitch of the array) of one of them, and within the smaller footprint side. The single linkage alone joins any via to its
          nearest neighbour, however far, so a few vias scattered over a board chained every centred thermal array into a group that "crossed" the edge.
    """
    poly = np.asarray(polygon, dtype=float)
    side_x, side_y = np.ptp(poly[:, 0]), np.ptp(poly[:, 1])
    small, large = min(side_x, side_y), max(side_x, side_y)
    if small <= 0.0:
        return False, False, False
    centroid = np.asarray(polygon_centroid(polygon))
    elongated = large / small > VIA_SIDE_RATIO
    any_across = any_offset = qualifies = False
    for g in np.unique(groups[inside]):
        members = groups == g
        if members.sum() < 2:
            continue
        qualifies = True
        mine = members & inside
        out_idx = np.flatnonzero(members & ~inside)
        if out_idx.size and not any_across:
            # Distance of every outside member to the nearest member in the footprint (brute force in blocks keeps the memory bounded)
            reach = min(2.0 * float(np.median(d_nn[mine])), small)
            xi, yi = vx[mine], vy[mine]
            for s in range(0, out_idx.size, 2048):
                j = out_idx[s:s + 2048]
                d2 = (vx[j, None] - xi[None, :]) ** 2 + (vy[j, None] - yi[None, :]) ** 2
                if bool((d2.min(axis=1) <= reach * reach * (1.0 + 1e-12)).any()):
                    any_across = True
                    break
        offset = float(np.hypot(vx[mine].mean() - centroid[0], vy[mine].mean() - centroid[1]))
        any_offset = any_offset or offset > VIA_OFFSET_FRACTION * small
    return any_across, any_offset, bool(elongated and qualifies)


def lumped_via_cool_warning(polygon, vx, vy, inside, groups, d_nn):
    """!
    @brief Text of the warning for a part that the Lumped model can read too cool because of its vias, or None. The rule: a via group of two or more vias,
           at least one under the footprint, that (i) continues outside the footprint (a via of the group outside the footprint lies within the reach of
           the array, see the note), or (ii) whose vias in the footprint have their centroid farther than 0.1 of the smaller footprint side from the
           centroid of the footprint, or (iii) a footprint whose side ratio exceeds 1.5.
    @param polygon Footprint polygon, sequence of (x, y) in m.
    @param vx x of all the vias in m.
    @param vy y of all the vias in m.
    @param inside Boolean array, True for the vias (with board under them) inside the footprint.
    @param groups Group label of every via (-1 for none), from _board_via_groups.
    @param d_nn Nearest-neighbour distance of every via in m, from _board_via_groups.
    @return str or None.
    @note The sides are those of the bounding box of the footprint; the thresholds are the zone model's and were not optimised for the program.
          The reach of (i): a via of the group outside the footprint counts only when it lies within twice the median nearest-neighbour distance of
          the group's vias in the footprint (the pitch of the array) of one of them, and within the smaller footprint side. The single linkage alone
          joins any via to its nearest neighbour, however far, so a few vias scattered over a board chained every centred thermal array into a group
          that "crossed" the edge, and the warning fired on nearly every part of a board with scattered vias (review of fix/lumped-via-warning-limits).
    """
    if not any(_lumped_via_cases(polygon, vx, vy, inside, groups, d_nn)):
        return None
    # The numbers are those of research/lumped-zones-adoption 8.4, reproduced by the review of this branch against a 1/8 mm reference: the via effect of
    # the 5 x 5 copper array shifted 7 mm under a 12 mm part 220 % too large (3.2 times), 10.8 K = 26 % of the rise in the error of the effect and 10.3 K =
    # 25 % in the hottest temperature (hence "about 11 K, a quarter"); the symmetry board 6.3 K = 17.5 % of the rise in the hottest temperature
    return ("the Lumped model can read this part too cool, unsafe for a design: its vias form an array that continues past the edge of the footprint, "
            "stands off its centre, or lies under an elongated footprint (side ratio above 1.5), where the rings overstate the via effect (measured up to "
            "3.2 times the reference: the part up to about 11 K, a quarter of its rise, too cool for an array across the edge of a 12 mm footprint; "
            "6.3 K, 17.5 % of its rise, for a 5 x 5 array 1.5 mm off the centre of a 12 x 8 mm part); use the FVM for via design.")


def check_lumped_zones(problem, result):
    """!
    @brief Warnings after a Lumped run about the parts over a group of vias, from the network of the run (which footprint was zoned is known only then).
    @details Per heater with at least one via under its footprint. A part the zone model splits (result.arrays["zoned_heaters"]): a group that continues past the edge
             of the footprint is read up to 16 % of the rise too cool (measured 1 to 16 % of the rise on a 5 x 5 array across the edge, steady state and profile), a group off
             the centre or under an elongated footprint 1 to 5 % and 2 to 4 % (research/lumped-zones-adoption 8.4, 10.1); a core across fewer than ten raster cells has its via
             effect up to 20 % too small. A part that stays one node (the core fills more than 92 % of the footprint on the fine grid or on the grid) keeps the text of
             lumped_via_cool_warning, which check_model_limits leaves out for the parts that the fine count says will be zoned: for those (the fine count says zoned, the
             count on the raster keeps one node) the text comes here, after a note that the footprint was kept as one node.
    @param problem A Problem.
    @param result The SteadyResult of the Lumped model (arrays["zoned_heaters"], one row per heater: zoned flag, cells across the core), or None.
    @return List of warning strings (CheckWarning, tagged with the heater).
    """
    out = []
    if result is None or "zoned_heaters" not in result.arrays or not problem.vias:
        return out
    rows = np.asarray(result.arrays["zoned_heaters"])
    vx = np.array([v.x for v in problem.vias])
    vy = np.array([v.y for v in problem.vias])
    on_board = np.array([share > 0.0 for share in problem.via_board_shares()])
    groups = d_nn = None
    for k, h in enumerate(problem.heaters):
        if k >= len(rows) or h.power <= 0:
            continue
        inside = points_in_polygon(vx, vy, h.polygon) & on_board
        if not inside.any():
            continue
        if groups is None:
            groups, d_nn = _board_via_groups(vx, vy, on_board)
        name = h.name or f"Heater {k + 1}"
        zoned = bool(rows[k, 0])
        if not zoned:
            if lumped.will_be_zoned(problem, h):                       # The pre-run check left this part out: the grid count kept it one node
                # Measured on four such boards (4 x 4 and 5 x 5 arrays whose core fills 82 to 92 % of the footprint on the fine grid, 93 to 94 % on the raster): the one
                # node at 0.5 mm within +0.1 to +0.9 % of the rise of the FVM at 0.25 mm (review of feature/lumped-zones)
                _add(out, "heater", k, f"{name}: the core of the vias covers more than {100 * lumped.MAX_CORE:.0f} % of the footprint on the 0.5 mm raster of the Lumped model, "
                                       "so the footprint was kept as one node (the pre-run note about the split does not apply)")
                msg = lumped_via_cool_warning(h.polygon, vx, vy, inside, groups, d_nn)
                if msg:
                    _add(out, "heater", k, f"{name}: {msg}")
            continue
        across, off_centre, elongated = _lumped_via_cases(h.polygon, vx, vy, inside, groups, d_nn)
        if across:
            _add(out, "heater", k, f"{name}: the Lumped model splits this footprint into the vias' core and the rest, but its vias form an array that continues past the edge "
                                   "of the footprint, which the split does not resolve: the part can be read too cool, up to 16 % of its rise (measured 1 to 16 % of the rise "
                                   "for a 5 x 5 array across the edge, steady state and power profile); use the FVM for via design.")
        elif off_centre or elongated:
            _add(out, "heater", k, f"{name}: the Lumped model splits this footprint into the vias' core and the rest; its vias stand off the centre of the footprint or the "
                                   "footprint is elongated (side ratio above 1.5): the part can be read too cool, measured 1 to 5 % of its rise (off centre) and 2 to 4 % "
                                   "(elongated) against 17 % without the split; use the FVM for via design.")
        if rows[k, 1] < 10:
            _add(out, "heater", k, f"{name}: the core of the vias is {int(rows[k, 1])} raster cells across, coarser than a tenth of the core: the via effect of this part "
                                   "can be 20 % too small (the part too hot); use the FVM for via design.")
    return out


# Rule of the Lumped near-edge warning (research/lumped-near-edge 6.2 and 10.5): a heat source whose gap to the nearest board side is at most
# max(NEAR_EDGE_SIDES equivalent sides, NEAR_EDGE_FLOOR_MM) is flagged (57 of 58 bad cases on the sweep, 35 of 37 on random boards)
NEAR_EDGE_SIDES = 1.0
NEAR_EDGE_FLOOR_MM = 5.0
NEAR_EDGE_TOLERANCE_M = 1e-9      # Slack on the threshold: a gap of exactly 5 mm typed in mm is 0.005000000000000001 m


def _segments_distance(a0, a1, b0, b1):
    """!
    @brief Smallest distance between every segment a and every segment b (zero where they cross or touch).
    @param a0 Start points of the segments a, array (n, 2) in m.
    @param a1 End points of the segments a, array (n, 2) in m.
    @param b0 Start points of the segments b, array (m, 2) in m.
    @param b1 End points of the segments b, array (m, 2) in m.
    @return float smallest distance in m.
    """
    def point_segment(p, s0, s1):
        # p (n, 2) against s0, s1 (m, 2): distances (n, m)
        d = s1 - s0
        den = np.maximum((d * d).sum(axis=1), 1e-300)
        t = np.clip(((p[:, None, :] - s0[None]) * d[None]).sum(axis=2) / den[None], 0.0, 1.0)
        q = s0[None] + t[..., None] * d[None]
        return np.hypot(*(p[:, None, :] - q).transpose(2, 0, 1))

    def orient(p, q, r):
        return (q[..., 0] - p[..., 0]) * (r[..., 1] - p[..., 1]) - (q[..., 1] - p[..., 1]) * (r[..., 0] - p[..., 0])

    # A proper crossing has the endpoints of each segment on opposite sides of the other
    A0, A1, B0, B1 = a0[:, None, :], a1[:, None, :], b0[None], b1[None]
    cross = (orient(A0, A1, B0) * orient(A0, A1, B1) < 0.0) & (orient(B0, B1, A0) * orient(B0, B1, A1) < 0.0)
    if bool(cross.any()):
        return 0.0
    return float(min(point_segment(a0, b0, b1).min(), point_segment(a1, b0, b1).min(),
                     point_segment(b0, a0, a1).min(), point_segment(b1, a0, a1).min()))


def heater_side_gaps(problem, polygons, reaches=None):
    """!
    @brief Equivalent side of every heat source and its exact gap to the nearest side of the board, for many sources at once.
    @details Rectangular board: the distance from the polygon to the four sides of the box (zero when it reaches or crosses one). Board with an outline: the distance from the
             polygon to the outline (zero when the polygon crosses it or lies outside it), not to the equivalent rectangle the Lumped solves. The inside test of every vertex is
             one call for all the polygons (it loops over the outline edges in Python, so a call per part cost seconds on an outline of thousands of points), and with a reach
             only the outline segments whose box comes within the reach of the polygon's box are measured: a gap beyond the reach is returned as infinity.
    @param problem A Problem.
    @param polygons Sequence of footprint polygons, each a sequence of (x, y) in m.
    @param reaches None (exact gaps), or one distance per polygon in m beyond which the exact gap is not needed.
    @return list of tuples (side, gap) in m; side is the square root of the polygon area.
    """
    polys = [np.asarray(p, dtype=float) for p in polygons]
    sides = [math.sqrt(max(polygon_area(p), 0.0)) for p in polys]
    b = problem.board
    if not b.has_outline():
        out = []
        for p, side in zip(polys, sides):
            x0, y0 = p.min(axis=0)
            x1, y1 = p.max(axis=0)
            out.append((side, max(0.0, min(x0, b.width - x1, y0, b.height - y1))))
        return out
    if not polys:
        return []
    o0 = np.asarray(b.outline, dtype=float)
    o1 = np.roll(o0, -1, axis=0)
    lo, hi = np.minimum(o0, o1), np.maximum(o0, o1)              # Box of every outline segment
    allv = np.concatenate(polys)
    inside = points_in_polygon(allv[:, 0], allv[:, 1], o0)
    ends = np.cumsum([len(p) for p in polys])
    res = []
    for k, (p, side) in enumerate(zip(polys, sides)):
        if not bool(np.all(inside[ends[k] - len(p):ends[k]])):
            res.append((side, 0.0))
            continue
        r = math.inf if reaches is None else float(reaches[k])
        # A segment within r of the polygon has a point in the polygon's box grown by r, so its own box overlaps that grown box
        sel = np.all(hi >= p.min(axis=0) - r, axis=1) & np.all(lo <= p.max(axis=0) + r, axis=1)
        if not bool(sel.any()):
            res.append((side, math.inf))
            continue
        res.append((side, _segments_distance(p, np.roll(p, -1, axis=0), o0[sel], o1[sel])))
    return res


def heater_side_gap(problem, polygon):
    """!
    @brief Equivalent side of a heat source and its exact gap to the nearest side of the board (see heater_side_gaps).
    @param problem A Problem.
    @param polygon Footprint polygon, sequence of (x, y) in m.
    @return tuple (side, gap) in m; side is the square root of the polygon area.
    """
    return heater_side_gaps(problem, [polygon])[0]


def check_lumped_near_edge(problem, models):
    """!
    @brief Warning, for the Lumped model only, about heat sources close to a side or a corner of the board (one aggregated line).
    @details The ring network of a part sees neither the mirror image of an insulated side nor the radial flux that the side pushes away, so the hottest temperature of a part near
             a side or a corner reads too cool: -7.4 % of the rise on average and -22.0 % at worst over 180 cases (2 to 10 mm parts, gaps 0 to 30 mm, edge film 10 to 200 W/m2K, boards
             40 x 40 and 100 x 80 mm) against the FVM at 0.5 mm, -8.2 % on average over the 120 of them that the rule flags (-3.3 % over the other 60), and -8.3 % over the 59
             flagged of 120 random boards (-3.6 % over the other 61). These were measured with the capped first ring of the 2.6.0 integration; on develop at 2.5.2
             (without it) the same cases read -9.4 % (sweep, flagged) and -8.5 % (random, flagged), and the rule catches 68 of the 86 sweep cases beyond -8 % (16 of the 18 missed
             are a 2 mm part on the 100 x 80 mm board 10 to 30 mm from a side, the other two a 5 mm part 10 mm from a corner: the small-part deficit of the rings, not the side) and 34 of 38 random ones. The text
             quotes the flagged means of both trees (8 to 9.5 %), since those are the parts it is shown for. A source is flagged when its gap to the nearest side is at most
             max(its equivalent side, 5 mm); the rule catches 57 of the 58 cases more than 8 % too cool on the sweep and 35 of 37 on the random boards (research/lumped-near-edge 6.1).
             Only geometry is used, so the warning is live. A board with an outline also gets the run's note about the equivalent rectangle (one line each).
    @param problem A Problem (structurally valid).
    @param models Iterable of model keys that will run.
    @return List with at most one warning (CheckWarning, tagged with the nearest flagged heater).
    """
    if "lumped" not in set(models):
        return []
    flagged = []
    ks = [k for k, h in enumerate(problem.heaters) if h.power > 0.0 and polygon_area(h.polygon) > 0.0]
    polys = [problem.heaters[k].polygon for k in ks]
    # The threshold of each part, passed as the reach so that only the outline segments near the part are measured
    limits = [max(NEAR_EDGE_SIDES * math.sqrt(polygon_area(p)), NEAR_EDGE_FLOOR_MM * 1e-3) + NEAR_EDGE_TOLERANCE_M for p in polys]
    for k, lim, (side, gap) in zip(ks, limits, heater_side_gaps(problem, polys, limits)):
        if gap <= lim:
            h = problem.heaters[k]
            flagged.append((gap, k, h.name or f"Heater {k + 1}"))
    if not flagged:
        return []
    flagged.sort()
    gap, k, name = flagged[0]
    why = ("the Lumped model reads a part near a side or a corner of the board too cool, because its rings around the part do not see the side that sends the heat back: "
           "on test boards the hottest temperature of a part this close to a side read 8 to 9.5 % of the rise too cool on average (120 cases of a sweep and 59 parts of "
           "120 random boards) and up to 22 % at a corner; a sample, not a bound; use the FVM or the FDM.")
    if len(flagged) == 1:
        out = []
        _add(out, "heater", k, f"{name}: the part is {gap * 1e3:.1f} mm from a side of the board; {why}",
             f"{name}: near a side of the board; the Lumped model reads it too cool (up to 22 % of the rise at a corner); use the FVM.")
        return out
    names = ", ".join(n for _, _, n in flagged[:3]) + (f" and {len(flagged) - 3} more" if len(flagged) > 3 else "")
    out = []
    _add(out, "heater", k, f"{len(flagged)} parts ({names}) are within one side of the part (and at least 5 mm) of a side of the board (the nearest, {name}, {gap * 1e3:.1f} mm); {why}",
         f"{len(flagged)} parts are near a side of the board; the Lumped model reads them too cool (up to 22 % of the rise at a corner); use the FVM.")
    return out


def check_lumped_small_part(problem, models, cell_mm=1.0):
    """!
    @brief Warning, for the Lumped model only, when a heat source is smaller than two cells of its raster and the run cannot refine the raster (memory bound or a zoned part).
    @details lumped.cell_for refines the raster to half the side of the smallest source (not below 0.125 mm) when that fits in lumped.SMALL_PART_MAX_BYTES and in the memory-guard
             limit and no part of the board is zoned (a zoned board keeps the 0.5 mm raster of the zone model); otherwise the run keeps the 0.5 to 1 mm raster and this warning
             says that such a part reads -19 to +6 % of the rise depending on where it sits in its cell. The equivalent rectangle and the zone test are built only when a source
             is small enough to be refined (the heaters keep their size on the equivalent rectangle, so the smallest side is that of the problem).
    @param problem A Problem (structurally valid).
    @param models Iterable of model keys that will run.
    @param cell_mm Cell size requested in the options, in mm.
    @return List with at most one warning.
    """
    if "lumped" not in set(models):
        return []
    clipped = min(max(cell_mm, 0.5), 1.0)
    side = lumped._smallest_side_mm(problem)
    if side is None or side >= lumped.SMALL_PART_CELLS * clipped or max(side / lumped.SMALL_PART_CELLS, lumped.SMALL_PART_MIN_CELL_MM) >= clipped:
        return []                                                # No source the run would refine
    # With an outline the Lumped solves the rectangle of the same area (the heaters keep their size, the box is smaller)
    p = problem.equivalent_rectangle()[0] if problem.board.has_outline() else problem
    zoned = None
    if lumped.ZONES and len(p.vias) >= 2 and p.board.layers >= 2:
        kept = p.drop_off_board_vias()
        if len(kept.vias) >= 2:
            vs = viaconstriction.ViaSet(kept)
            # The same test as lumped.cell_for (every heater, as there), on the board the Lumped solves
            zoned = next((h for h in kept.heaters if lumped.will_be_zoned(kept, h, vias=vs, prepared=True)), None)
    head = ("a heat source is smaller than two cells of the Lumped raster; a part that small is spread over the whole cells it touches, so its hottest temperature "
            "read -19 to +6 % of the rise off the resolved value depending on where it sits in its cell (sides of 0.1 to 0.5 mm at a 0.5 mm raster); ")
    if zoned is not None:
        if side >= lumped.SMALL_PART_CELLS * lumped.ZONE_CELL_MM:
            return []                                            # Two cells of the zone raster or more: the part is not small there
        why = (f"the finer raster that removes this (half the side of the part) is not used on this board, because {zoned.name or 'a part'} has a dense group of vias under "
               "it and the zone model of the Lumped keeps the 0.5 mm raster; use the FVM for the small part.")
    elif lumped.small_part_cell(p, clipped) is None:
        why = ("the finer raster that removes this (half the side of the part) does not fit in the memory bound of this board, so the run keeps the coarser one; "
               "use the FVM for the part.")
    else:
        return []                                                # The run refines the raster
    out = []
    _add(out, None, None, head + why, "a heat source is under two cells of the Lumped raster; it reads -19 to +6 % off; use the FVM.")
    return out


def check_model_limits(problem, models, cell_mm=1.0):
    """!
    @brief Warnings about the documented limits of the selected models on this input (text only; no result depends on them).
    @details Two groups, each measured in a research folder: a part whose centre sits on bare laminate (the layered models read below a
             resolved 3D solution; research/bare-spot-under-source, INTEGRATION P3) and vias in the Lumped and Analytic models, which carry ring and
             tile means and add the constriction of the heat converging on a barrel (viaconstriction.py; research/lumped-analytic-vias,
             research/young-omega-tiles 3; the numbers are the error of the via effect against the FVM at 0.25 mm on the 29 boards of the
             branch fix/via-constriction and 17 more boards of its review, measured on this program). The Analytic copper-spread warning lives in analytic._effective_sheet, where its weights are computed.
    @note The warnings about vias on a coarse cell and near the board edge (FVM and FDM) are in check_via_limits, which came with the
          mean-potential via of viawell.py.
    @param problem A Problem (structurally valid).
    @param models Iterable of model keys that will run ("fvm", "fdm", "lumped", "analytic", "solid3d").
    @param cell_mm Cell size (mm) of the raster used for the geometric tests.
    @return List of warning strings (CheckWarning, tagged with the heater or via) in input order.
    """
    out = []
    models = set(models)
    layered = sorted(models & set(LAYERED_MODELS))
    b = problem.board
    W, H = b.width, b.height
    nx = max(int(round(W * 1000.0 / cell_mm)), 8)
    ny = max(int(round(H * 1000.0 / cell_mm)), 8)
    dx, dy = W / nx, H / ny

    # --- A part on bare laminate. The proposal tests the fill of the hottest cell under the part; before the run that cell is not known,
    # so the cells under the central half of the footprint (its polygon shrunk by two about the centroid) stand for it, and the smallest
    # fill there is compared with 0.5. The mean fill of the whole footprint is not used: a 2 or 4 mm window under a 6 mm part has a mean
    # fill of 0.89 or 0.56 and a window as large as the part a fill of 0, and those are the boards where the FVM was 10 to 23 % low.
    if layered:
        fill = copper.problem_fill(problem, nx, ny, dx, dy, 4)
        any_copper = bool(fill.max() > 0.0)                     # A board with no copper at all has its own warnings and was not measured
        for k, h in enumerate(problem.heaters):
            if not any_copper or polygon_area(h.polygon) <= 0:
                continue
            c = np.asarray(polygon_centroid(h.polygon))
            core = coverage_fraction(c + 0.5 * (np.asarray(h.polygon) - c), nx, ny, dx, dy, 4) > 0
            if not core.any():
                core = coverage_fraction(h.polygon, nx, ny, dx, dy, 4) > 0
            if not core.any():
                continue                                         # Off the board: check_problem says so
            f_core = float(fill[h.layer][core].min())
            if f_core < 0.5:
                _add(out, "heater", k, f"{h.name or f'Heater {k + 1}'}: the centre of the part sits on bare laminate (copper fill "
                           f"{f_core:.2f} on layer {h.layer + 1}); the layered models ({', '.join(layered)}) read lower than a resolved 3D "
                           "solution there: the FVM (which cuts the laminate there into sub-gaps) 0 to 3 % on 4- and 6-layer stack-ups and 0.8 to 1.6 mm two-layer boards, "
                           "up to 10 % on a 3.2 mm laminate or under a window narrower than the laminate is thick, the FDM 2 to 20 %, "
                           "the Lumped (-43 to +7 %) and the Analytic (-4 to -63 %) not systematically; use the 3D solid for the final value.",
                     f"{h.name or f'Heater {k + 1}'}: the part sits on bare laminate (fill {f_core:.2f}); the layered models read low (the FVM up to 10 %); "
                     "use the 3D solid.")

    out.extend(check_small_part_laminate(problem, models, cell_mm))
    out.extend(check_edge_laminate(problem, models))
    out.extend(check_reduced_edge_laminate(problem, models))

    if not problem.vias or b.layers < 2:
        return out                                              # A one-layer board has no gap: its vias join nothing and change no model

    # --- Vias in the Lumped and Analytic models: both carry area means (a ring, a tile) and add the constriction of the heat converging on a barrel
    # (viaconstriction.py). The numbers are the error of the via effect (drop of the hottest temperature caused by the vias) against the FVM at 0.25 mm
    # on the 29 boards of the branch fix/via-constriction (examples with 9, 25 and 49 vias, arrays of 4 to 576 vias at 1.0 to 3.5 mm, rows, lone vias, pads)
    # and 17 boards of its review that were not used to build the model (6 and 2 layers, 30 to 80 mm boards, an array across or just outside the edge of a
    # footprint, mixed drills, outlines, a heatsink, metal blocks, 500 and 2000 scattered vias), cells 0.5 and 1 mm (research/lumped-analytic-vias,
    # research/young-omega-tiles 3). Lumped: 8 % mean on the first set, 20 % on the second (-21 to +80 %); Analytic: 1.8 % and 2.9 % (-14 to +8 %).
    vx = np.array([v.x for v in problem.vias])
    vy = np.array([v.y for v in problem.vias])
    on_board = np.array([share > 0.0 for share in problem.via_board_shares()])   # A via with no board under it is ignored (check_problem says so)
    if "lumped" in models:
        in_any = np.zeros(len(problem.vias), dtype=bool)
        groups = d_nn = None                                     # Via groups and nearest neighbours, built once and only when a part has vias under it
        zone_board = None                                        # Board and ViaSet of lumped.will_be_zoned, built once (not per part: 0.8 s with 8500 vias and 20 parts, live)
        for k, h in enumerate(problem.heaters):
            inside = points_in_polygon(vx, vy, h.polygon) & on_board
            in_any |= inside
            n_in = int(inside.sum())
            if n_in >= 1:
                if zone_board is None:
                    # What will_be_zoned builds by itself for every part: the equivalent rectangle of an outline (the board the Lumped model solves) and the vias on the board
                    zp = problem.equivalent_rectangle()[0] if b.has_outline() else problem
                    kept = zp.drop_off_board_vias()
                    zone_board = (kept, viaconstriction.ViaSet(kept) if len(kept.vias) >= 2 else None)
                zoned = lumped.will_be_zoned(zone_board[0], zone_board[0].heaters[k], vias=zone_board[1], prepared=True)
                if zoned:
                    # The numbers of the zone model (research/lumped-zones-adoption INTEGRATION 0.1: 36 family and 26 held-out boards against 1/8 mm references)
                    _add(out, "heater", k, f"{h.name or f'Heater {k + 1}'}: {n_in} via{'s' if n_in > 1 else ''} under the footprint; the Lumped "
                               "model splits this footprint into the core of the vias and the rest of the footprint (zone model, 0.5 mm raster): its via effect was "
                               "measured 4.0 to 4.6 % off on average (up to 21 %) and the hottest temperature 1.6 to 2.6 % of the rise off on average (up to 7.6 %) "
                               "over 62 boards; "
                               "use the FVM for via design.",
                         f"{h.name or f'Heater {k + 1}'}: {n_in} via{'s' if n_in > 1 else ''} under the footprint; the Lumped model is approximate here "
                         "(via effect up to 21 % off); use the FVM.")
                else:
                    _add(out, "heater", k, f"{h.name or f'Heater {k + 1}'}: {n_in} via{'s' if n_in > 1 else ''} under the footprint; the Lumped "
                               "model joins the planes through a well and the barrel of each ring, so its via effect was measured from 21 % too small "
                               "(the part too hot) to 33 % too large (the part too cool by up to 14 % of its rise: dense arrays that cover a quarter or less "
                               "of a large footprint, sparse arrays and rows; 8 to 20 % on average over 46 boards, 11 % over 36 more); use the FVM for via design.",
                         f"{h.name or f'Heater {k + 1}'}: {n_in} via{'s' if n_in > 1 else ''} under the footprint; the Lumped model is approximate here "
                         "(-21 to +33 % of the via effect); use the FVM.")
                if groups is None:
                    groups, d_nn = _board_via_groups(vx, vy, on_board)
                # A part that the zone model will split gets its text after the run, from the network (check_lumped_zones)
                msg = None if zoned else lumped_via_cool_warning(h.polygon, vx, vy, inside, groups, d_nn)
                if msg:
                    _add(out, "heater", k, f"{h.name or f'Heater {k + 1}'}: {msg}",
                         # The rule has three triggers (array past the edge, off centre, elongated footprint): the short form names none of them alone
                         f"{h.name or f'Heater {k + 1}'}: the Lumped model can read this part too cool, unsafe for a design (up to about 11 K, a quarter "
                         "of its rise); use the FVM.")
        outside = np.flatnonzero(~in_any & on_board)
        if outside.size:
            # One warning for all of them: a Gerber board can have hundreds of vias away from the parts
            v = problem.vias[int(outside[0])]
            first = v.name or f"Via {int(outside[0]) + 1}"
            _add(out, "via", int(outside[0]), f"{first}{f' and {outside.size - 1} more vias' if outside.size > 1 else ''}: outside the "
                       "footprint of every part; the Lumped model spreads such a via over a ring around the part: the effect of a lone via was "
                       "measured 22 % too small to 65 % too large depending on the distance and the number of rings (an effect of 0.5 to 3 K), "
                       "that of a row 6 to 21 % too large, that of vias scattered over the board 19 to 56 % too large, and that of an array just "
                       "outside the edge of a footprint up to 2.3 times the reference (the part up to 4 K, 9 % of its rise, too cool; "
                       "measured on 29 boards, and 17 more, against the FVM at 0.25 mm; a sample, not a bound; see docs/theory.md section 5); use the FVM.",
                 f"{first}{f' and {outside.size - 1} more vias' if outside.size > 1 else ''}: outside every footprint; the Lumped model is approximate here "
                 "(effect 22 % too small to 65 % too large, an array just beside a part up to 2.3 times); use the FVM.")
    if "analytic" in models and on_board.any() and b.layers > 1:
        # The tile of the correction follows the pitch (1 mm at most, 0.25 mm at least) and is enlarged when the dense system would pass MAX_UNKNOWNS;
        # a pitch under 0.45 mm was not tested. The program's tile is 2.5 to 5 mm; the rule never reaches it, the guard can. The guard counts the tiles of the
        # heatsinks and blocks too (viaconstriction.heatsink_tiles); this check uses a 5 mm program tile, the solver its own 2.5 to 5 mm one, so the
        # coarsened tile quoted here can differ from the solver's when the guard goes beyond 2.5 mm.
        vs = viaconstriction.ViaSet(problem.drop_off_board_vias())     # The Analytic model drops the vias with no board under them (analytic.solve_steady)
        nt = (int(math.ceil(W / 5e-3)), int(math.ceil(H / 5e-3)))
        pl = viaconstriction.plan(problem, vs, (nt[0], nt[1], W / nt[0], H / nt[1]), b.layers)
        t_rule, t_final, d_med = pl["t_rule"], pl["t_final"], viaconstriction.median_nn(vs)
        n_unknown = pl["active"] * b.layers
        if t_final > t_rule * (1.0 + 1e-6):
            _add(out, None, None, f"Analytic model: the tile of the via correction was coarsened from {num(t_rule * 1e3, 2)} to {num(t_final * 1e3, 2)} mm "
                                  f"to keep its dense system small (estimate of {viaconstriction.MAX_ACTIVE_TILES} active tiles, at most {viaconstriction.MAX_UNKNOWNS} unknowns counting "
                                  f"the tiles of the heatsinks and metal blocks; {len(vs)} vias); the via effect is less accurate (measured 14 % too small to 3 % "
                                  "too large at tiles of 1.6 to 2.4 mm: 500 and 2000 scattered vias, a heatsink or a block over most of the board; "
                                  "not tested for 400 or more vias at a pitch under 1 mm).",
                 f"Analytic model: via tile coarsened to {num(t_final * 1e3, 2)} mm; the via effect is less accurate (14 % too small to 3 % too large).")
        if d_med < 0.45e-3:
            _add(out, None, None, f"Analytic model: the median via pitch is {num(d_med * 1e3, 2)} mm, below the 0.45 mm tested; the tile is cut to 0.25 mm at least and the "
                                  "via effect is unverified.", f"Analytic model: median via pitch {num(d_med * 1e3, 2)} mm, below the 0.45 mm tested.")
        if n_unknown > 2400:
            # Peak memory measured by the review: 0.15 GB of the program plus about four dense matrices of n^2 doubles (0.9 GB and 3 s at 4800 unknowns)
            _add(out, None, None, f"Analytic model: the via correction solves a dense system of {n_unknown} unknowns (about {0.15 + 0.75 * (n_unknown / 4800.0) ** 2:.1f} GB "
                                  "and a few seconds; 0.9 GB and 3 s were measured at 4800 unknowns).",
                 f"Analytic model: the via correction solves {n_unknown} unknowns (about {0.15 + 0.75 * (n_unknown / 4800.0) ** 2:.1f} GB and a few seconds).")
        if len(vs) <= 2:
            _add(out, None, None, "Analytic model: one or two vias beside or under a part were measured up to 16 % too small in the via effect "
                                  "(an effect of 1 to 4 K; the tile is 1 mm and the barrel is read at its scale); use the FVM for the value.",
                 "Analytic model: one or two vias were measured up to 16 % too small in the via effect; use the FVM.")
    return out


SMALL_PART_RATIO = 0.15       # Bare laminate under the part: a sub-layer thicker than this times the side of the part reads it too cool by more than about 4 % (research/paper-case-studies 16.3; review)
SMALL_PART_RATIO_PAD = 0.10   # A copper pad of the part's size under it: the error of the layered rule is larger at the same ratio and passes about 4 % near 0.1 (review, FVM 0.25 mm in air)
SMALL_PART_AGGREGATE = 3      # More parts than this in one group give one aggregated message


def _spread_side(fill_layer, foot, side, dx, dist=None):
    """!
    @brief The side of the region through which the heat of a part enters the laminate: the part itself on bare laminate, or the part grown by the copper around it.
    @details The heat of a part over a copper pad or plane first spreads in that copper, so the length that the sub-layer must resolve is the copper around the part, not the
             part (review: a 2 mm part on a 3 mm or 4 mm pad reads the same error as a 3 mm or 4 mm part on its own pad; under a full plane the error is 0.02 %). The copper
             cells are those of fill 0.5 or more on the layer of the part; r is the smallest distance from a cell of the footprint to a cell without copper, less 1.5 cells so
             that a coarse raster does not grow a pad that has the size of the part (the error of the rounding falls on the side of a warning).
    @param fill_layer Copper fill (ny, nx) of the layer of the part.
    @param foot Boolean (ny, nx) of the cells of the footprint (mostly covered).
    @param side Smaller side of the part in m.
    @param dx Cell size of the raster in m.
    @param dist Distance transform of the copper cells of the layer (computed when None; the caller keeps one per layer).
    @return float Side in m (at least side).
    """
    cu = fill_layer >= 0.5
    if not cu.any() or not (foot & cu).any():
        return side
    if cu.all():
        return math.inf                                          # A plane over the whole board: nothing limits the spread
    dist = ndimage.distance_transform_edt(cu) if dist is None else dist   # Cells from every copper cell to the nearest cell without copper
    r = max(0.0, float(dist[foot & cu].min()) - 1.5) * dx
    return side + 2.0 * r


def small_part_ratios(problem, models, cell_mm=1.0):
    """!
    @brief For every part that sits on a laminate sub-layer thick against its size: the ratio of the sub-layer to the side through which the heat enters the laminate, for the layered FVM/FDM rule and for the 3D solid.
    @details The sub-layer of the FVM and FDM is s = d / n with n = min(laminate_n_max, ceil(d / laminate_s_max_mm)) (laminate.n_for_gap, the options in force) and counts only when the rule
             cuts the gap under the part: some cell of the footprint is flagged by laminate.flag_cells (copper absent next to the gap, plus its margin; the raster is that of the check,
             so the margin can differ from the run's by a cell) and the board has no metal block (which keeps the earlier treatment). The sub-layer of the 3D solid is d / n with n the slabs of the gap by the rule of solid3d.slab_rule (0.2 mm, 4 to 16: at most 0.2 mm) and
             is always present. d is the gap on each side of the layer of the part; the larger ratio is kept. The side is the smaller extent of the bounding box of the footprint, grown by
             the copper around the part on its layer (_spread_side): a part over a plane is silent. The limit is SMALL_PART_RATIO on bare laminate (the centre of the footprint without copper,
             as in the bare-laminate warning) and, for the layered rule over copper, SMALL_PART_RATIO_PAD; the 3D solid uses SMALL_PART_RATIO in both cases. The limit was set with the four fixed
             slabs of the earlier solid (4 against 16 slabs: +3.5 % bare, +4.1 % pad at 0.15) and holds for the slabs by thickness: the error of the slabs alone, against the same solid
             extrapolated in its slabs, follows the ratio and not the thickness (review, 1.6 and 3.2 mm, parts of 1 to 4 mm: +0.7 to +1.0 % at 0.05, +2.0 to +2.6 % at 0.10, +3.0 to +3.6 %
             at 0.13, +4.9 to +5.7 % at 0.19 to 0.20, bare and pad); a sub-layer is at most 0.2 mm, so the warning is for parts under about 1.3 mm.
    @param problem A Problem (structurally valid).
    @param models Iterable of model keys that will run.
    @param cell_mm Cell size (mm) of the raster used for the geometric tests.
    @return List of tuples (heater index, model group "layered" or "solid3d", sub-layer in m, side in m, ratio, limit) for the ratios above their limit.
    """
    models = set(models)
    layered = bool(models & {"fvm", "fdm"}) and laminate.uses_rule(problem)
    solid = "solid3d" in models
    b = problem.board
    if not (layered or solid) or not problem.heaters:
        return []
    L = b.layers
    if L == 1:
        gaps = [(0, float(b.slab_thicknesses()[0]) - float(np.asarray(b.copper_thickness, dtype=float)[0]))]
    else:
        gaps = list(enumerate(float(d) for d in b.gap_thicknesses()))
    s_max, n_max = laminate.parameters()
    W, H = b.width, b.height
    nx = max(int(round(W * 1000.0 / cell_mm)), 8)
    ny = max(int(round(H * 1000.0 / cell_mm)), 8)
    dx, dy = W / nx, H / ny
    low = min(SMALL_PART_RATIO, SMALL_PART_RATIO_PAD)
    fill = None                                                  # Copper fill of every layer, built only when a part passes the cheap ratio test
    flagged_of, dist_of = {}, {}                                 # Per gap and per layer: computed once for all the parts (a Gerber board has hundreds)
    found = []
    for k, h in enumerate(problem.heaters):
        poly = np.asarray(h.polygon, dtype=float)
        if len(poly) < 3 or polygon_area(h.polygon) <= 0:
            continue
        side = float(min(np.ptp(poly[:, 0]), np.ptp(poly[:, 1])))
        if side <= 0:
            continue
        # The gaps next to the layer of the part (a one-layer board: its laminate)
        near = [g for g in gaps if L == 1 or g[0] in (h.layer - 1, h.layer)]
        subs = {"layered": [(g, d, laminate.n_for_gap(d, s_max, n_max)) for g, d in near] if layered else [],
                "solid3d": [(g, d, solid3d.slab_rule(d)) for g, d in near] if solid else []}
        # Cheap test first: the side only grows with the copper and the lowest limit is `low`, so a part below it for every gap needs no raster
        if not any(d / n > low * side * (1.0 + 1e-9) for v in subs.values() for _, d, n in v):
            continue
        if fill is None:
            fill = copper.problem_fill(problem, nx, ny, dx, dy, 4)
        cov = coverage_fraction(h.polygon, nx, ny, dx, dy, 4)
        foot = cov > 0
        if not foot.any():
            continue                                             # Off the board: check_problem says so
        c = np.asarray(polygon_centroid(h.polygon))
        core = coverage_fraction(c + 0.5 * (poly - c), nx, ny, dx, dy, 4) > 0
        if not core.any():
            core = foot
        over_copper = float(fill[h.layer][core].min()) >= 0.5   # The same test as the bare-laminate warning
        mostly = cov >= 0.5
        eff = side
        if over_copper:
            cu = fill[h.layer] >= 0.5
            if h.layer not in dist_of and cu.any() and not cu.all():
                dist_of[h.layer] = ndimage.distance_transform_edt(cu)
            eff = _spread_side(fill[h.layer], mostly if mostly.any() else foot, side, dx, dist_of.get(h.layer))
        for model in ("layered", "solid3d"):
            limit = SMALL_PART_RATIO_PAD if (model == "layered" and over_copper) else SMALL_PART_RATIO
            best = None
            for g, d, n in subs[model]:
                sub = d / n
                if sub <= limit * eff * (1.0 + 1e-9):
                    continue
                if model == "layered":
                    if n < 2:
                        continue
                    if g not in flagged_of:
                        fb = None if L == 1 else fill[g + 1]
                        flagged_of[g] = laminate.flag_cells(fill[g], fb, d, dx, np.ones((ny, nx), dtype=bool))
                    if not (flagged_of[g] & foot).any():
                        continue                                  # The gap stays one link under this part: the rule does not apply
                if best is None or sub > best[0]:
                    best = (sub, d)
            if best is not None:
                found.append((k, model, best[0], eff, best[0] / eff, limit))
    return found


def check_small_part_laminate(problem, models, cell_mm=1.0):
    """!
    @brief Warnings for a small part over a thick insulating layer: the layered FVM/FDM laminate rule reads it too cool and the 3D solid, with its slabs of at most 0.2 mm, still a little too hot (text only).
    @details Measured against an extrapolated 3D reference and, on bare laminate, the closed form of Muzychka, Yovanovich and Culham (research/paper-case-studies 11.3, 16.3, 16.4;
             FVM at 0.25 mm). Layered rule, error against the ratio of the sub-gap s = d / n to the side of the part (always too cool, only where the gap is cut under the part):
             0.15 to 0.2: -4 to -9 % bare, -6 to -14 % with a copper pad; 0.3 to 0.4: -12 to -20 % bare, -14 to -24 % pad; the review measured the part's rise in air
             (20 mm two-layer board, h 10 / 15 W/m2K, against the FVM extrapolated in its sub-gaps): bare -3.4 % at 0.14, -4.1 to -4.3 % at 0.16, pad -4.3 to -4.8 % at 0.08 to 0.09,
             -5.4 % at 0.10 and -6.3 to -7.4 % at 0.12 to 0.14, so the limit over copper is 0.10. A pad larger than the part counts by its own size; a plane under the part is silent.
             With the default rule it fires on bare laminate for parts under about 2.5 mm on a 1.6 mm board and 5.2 mm on a 3.2 mm board, over a pad of the part's size under 3.8 and 7.8 mm.
             A smaller laminate_s_max_mm or a larger laminate_n_max reduces it ((0.2, 8): 1.4 to 4.6 times the time and 1.2 to 3 times the memory).
             The 3D solid cuts every gap into ceil(d / 0.2 mm) slabs, 4 to 16 (before: a fixed four, which read a 2 mm part +20 % bare and +27 % pad hot on 3.2 mm and +5.5 and +14.7 % on 1.6 mm);
             with them the same 2 mm part reads +3.9 % bare and +7.9 % pad hot on 3.2 mm (16 slabs) and +4.1 and +9.0 % on 1.6 mm (8 slabs), at a 0.25 mm cell (research/laminate-slabs-and-local-rule 5.1),
             of which about +2 to +2.6 % are the slabs and the rest the plan cell (+7 to +16 % in all at 0.5 mm, +17 to +30 % at 1 mm; review). The test is d / n against 0.15 of the side
             (the slabs alone +3 to +4 % there), so it fires only for parts under about 1.3 mm; the cell is the warning of check_problem (a part under three cells). No result depends on it.
    @param problem A Problem (structurally valid).
    @param models Iterable of model keys that will run.
    @param cell_mm Cell size (mm) of the raster used for the geometric tests.
    @return List of warnings (CheckWarning, tagged with the heater): one per part and model group, or one for the whole group (kind None, the five worst named) when more than SMALL_PART_AGGREGATE parts qualify.
    """
    out = []
    found = small_part_ratios(problem, models, cell_mm)
    # More than SMALL_PART_AGGREGATE parts of one group (a Gerber board can have hundreds over pads): one message for the group, worst first
    for model in ("layered", "solid3d"):
        group = [f for f in found if f[1] == model]
        if len(group) <= SMALL_PART_AGGREGATE:
            continue
        group.sort(key=lambda f: -f[4])
        worst = ", ".join(f"{problem.heaters[f[0]].name or f'Heater {f[0] + 1}'} ({f[4]:.2f})" for f in group[:5])
        limit = min(f[5] for f in group)
        if model == "layered":
            s_max, n_max = laminate.parameters()
            what = (f"the layered FVM and FDM read them too cool (4 to 24 % of the thermal resistance, more over a pad); a smaller {laminate_where('sub-gap')} (now {num(s_max * 1e3, 2)} mm) "
                    f"or a larger {laminate_where('sub-gaps')} (now {n_max}) reduces it, at 1.4 to 4.6 times the time and 1.2 to 3 times the memory for (0.2 mm, 8)")
            short_what = f"the FVM and FDM read them too cool (4 to 24 %); reduce {laminate_where('sub-gap')}"
        else:
            what = ("the 3D solid, with slabs of at most 0.2 mm per insulating layer, reads them too hot: its slabs alone add about +3 to +4 % at a ratio of 0.15 and +5 to +6 % at 0.2 "
                    "(a 1 mm part), and a part only a few cells wide adds the error of the plan cell")
            short_what = "the 3D solid reads them too hot (+3 to +6 % from its slabs, more at a coarse cell)"
        _add(out, None, None, f"{len(group)} parts are small against the sub-layer of laminate under them (ratio above {limit:.2f}; the worst, with their ratios: {worst}); {what}.",
             f"{len(group)} small parts over a thick laminate (worst: {worst}); {short_what}.")
    found = [f for f in found if sum(1 for g in found if g[1] == f[1]) <= SMALL_PART_AGGREGATE]
    for k, model, sub, side, ratio, limit in found:
        h = problem.heaters[k]
        name = h.name or f"Heater {k + 1}"
        size = f"{num(side * 1e3, 2)} mm" if math.isfinite(side) else "large"
        if model == "layered":
            s_max, n_max = laminate.parameters()
            over = "over a copper pad" if limit == SMALL_PART_RATIO_PAD else "on bare laminate"
            _add(out, "heater", k, f"{name}: the part is small ({size}, {over}) against the sub-layer of laminate under it ({num(sub * 1e3, 2)} mm, ratio {ratio:.2f} "
                       f"above {limit:.2f}); the layered FVM and FDM read it too cool: measured -4 to -9 % of the thermal resistance bare and -6 to -14 % over a copper pad "
                       "at a ratio of 0.15 to 0.2, -12 to -24 % at 0.3 to 0.4 (over a pad already -5 % at 0.1). A smaller "
                       f"{laminate_where('sub-gap')} (now {num(s_max * 1e3, 2)} mm) or a larger {laminate_where('sub-gaps')} (now {n_max}) reduces it, at 1.4 to 4.6 times the time and 1.2 to 3 times the memory for (0.2 mm, 8). "
                       "The 3D solid, with its slabs of at most 0.2 mm per insulating layer, reads such a part a few per cent too hot instead (a 2 mm part about +4 % bare and +8 to +9 % over a pad at a 0.25 mm cell, more at a coarser cell).",
                 f"{name}: small part over a thick laminate; the FVM and FDM read it too cool (ratio {ratio:.2f}, about 4 to 24 %); "
                 f"reduce {laminate_where('sub-gap')}.")
        else:
            _add(out, "heater", k, f"{name}: the part is small ({size}) against the slabs of the 3D solid ({num(sub * 1e3, 2)} mm, ratio {ratio:.2f} "
                       f"above {limit:.2f}); the solid reads it too hot: its slabs alone were measured +3 to +4 % at a ratio of 0.13 to 0.15 and +5 to +6 % at 0.2, bare and over a "
                       "pad of the part's size, and the plan cell adds its own hot error for a part only a few cells wide (a 2 mm part read +4 to +9 % in all at a 0.25 mm cell, "
                       "+7 to +16 % at 0.5 mm and +17 to +30 % at 1 mm). The slabs are at most 0.2 mm thick (4 to 16 per insulating layer).",
                 f"{name}: small part on a thick laminate; the 3D solid reads it too hot (+3 to +6 % from its slabs, more at a coarse cell).")
    return out


# Edge coefficient above which the laminate at the board edge is under-resolved by the sub-gaps (W/m2K); a PCB in air has 5 to 50
EDGE_LAMINATE_H = 200.0


def check_edge_laminate(problem, models):
    """!
    @brief Warning for a board edge cooled by a large coefficient: the laminate along the edge is cut into too few sub-gaps and the layered FVM and FDM read it too cool (text only).
    @details Along the edge the gap is cut into sub-gaps in a band (laminate.edge_band), so the edge film acts on the laminate nodes. What remains is the 1 / n error of the sub-gaps, which
             grows with the edge coefficient (research/laminate-edge-band 11.2, 11.5, against a converged 3D reference, 2-layer 30 x 20 mm boards, 3.2 mm, cell 0.25 mm): with four sub-gaps
             about -2.4 % at 200 W/m2K, -5.5 % at 500 and -16 % at 2000, with eight -2 % at 500 and with sixteen -2.8 % at 2000 W/m2K. On a thin board (0.8 mm) at 2000 W/m2K with a cell larger than the
             gap and eight sub-gaps the FVM reads 7 % too hot instead (the half cell of the edge film is larger than the gap). It needs two or more copper layers, an edge coefficient above
             EDGE_LAMINATE_H, the layered FVM or FDM and a gap that the rule cuts.
    @param problem A Problem (structurally valid).
    @param models Iterable of model keys that will run.
    @return List with at most one warning (CheckWarning, about the whole design).
    """
    b = problem.board
    if not ({"fvm", "fdm"} & set(models)) or b.layers < 2 or not (b.h_side or 0.0) > EDGE_LAMINATE_H or not laminate.uses_rule(problem):
        return []
    s_max, n_max = laminate.parameters()
    if not any(laminate.n_for_gap(float(d), s_max, n_max) > 1 for d in b.gap_thicknesses()):
        return []                                               # no gap is cut: nothing to resolve
    out = []
    _add(out, None, None,
         f"The edge coefficient ({num(b.h_side, 2)} W/m2K) is above {EDGE_LAMINATE_H:g} W/m2K: the laminate along the board edge is cut into too few sub-gaps and the layered FVM and FDM "
         "read the board too cool (measured on 3.2 mm two-layer boards at a 0.25 mm cell: about -2.4 % of the rise at 200 W/m2K, -5.5 % at 500 and -16 % at 2000 with the four sub-gaps; "
         "-2 % at 500 with eight; -2.8 % at 2000 W/m2K even with sixteen). A larger "
         f"{laminate_where('sub-gaps')} (now {n_max}) and a smaller {cell_where()} reduce it; on a board of 1 mm or less with a cell larger than the gap, many sub-gaps can over-correct "
         "(+7 % at 2000 W/m2K, 0.8 mm board, 1 mm cell, eight sub-gaps). A board in air has an edge coefficient of 5 to 50 W/m2K, where the error is within 3 %.",
         f"Edge coefficient above {EDGE_LAMINATE_H:g} W/m2K: the edge laminate is under-resolved and the FVM and FDM read too cool (-5.5 % at 500, -16 % at 2000 W/m2K); raise {laminate_where('sub-gaps')} and refine the cell.")
    return out


# Product of the edge coefficient and the board thickness (W/m2K times mm) from which the Lumped and Analytic models, which keep the edge film at the copper temperature, can read
# about 3 % too cool or more (two-layer boards, a part near the edge): 1.6 mm at about 100 W/m2K, 3.2 mm at about 50, 0.8 mm at about 200
REDUCED_EDGE_HT = 150.0


def check_reduced_edge_laminate(problem, models):
    """!
    @brief Warning for the Lumped and Analytic models on a board whose edge is cooled strongly for its thickness: they put the edge film of the laminate at the copper temperature.
    @details The FVM and FDM cut the laminate along the edge into nodes (laminate.edge_band), so their edge film acts on the laminate, which is cooler than the copper. The Lumped and
             the Analytic have no such nodes: their edge loses heat as if the whole slab were at the copper temperature, as the FVM did before the band, and they read cool where
             much of the heat leaves through the edge. Measured against the FVM with the band at 0.5 mm (two-layer boards with full copper, 10 mm part, faces 10 W/m2K, 30 x 20 and
             60 x 40 mm; the FVM itself within 0.6 % of a converged independent 3D solver on the 60 x 40 mm board at 50 and 200 W/m2K, docs/validation.md 36.3): Analytic, part in a
             corner of the 30 x 20 mm board, -2.0 / -3.1 / -4.1 % at 200 / 100 / 50 W/m2K on 0.8 / 1.6 / 3.2 mm (product 160), -6.2 % at 200 on 1.6 mm and -13.3 % at 200 on 3.2 mm;
             a centred part -5.5 % and -9.6 % there; the Lumped the same or more. The warning fires when h_side times the thickness in mm reaches REDUCED_EDGE_HT.
    @param problem A Problem (structurally valid).
    @param models Iterable of model keys that will run.
    @return List with at most one warning (CheckWarning, about the whole design).
    """
    b = problem.board
    reduced = [m for m in ("lumped", "analytic") if m in set(models)]
    hs = float(b.h_side or 0.0)
    t_mm = float(b.thickness) * 1000.0
    if not reduced or b.layers < 2 or hs * t_mm < REDUCED_EDGE_HT:
        return []
    names = " and ".join({"lumped": "Lumped", "analytic": "Analytic"}[m] for m in reduced)
    out = []
    _add(out, None, None,
         f"The {names} {'models keep' if len(reduced) > 1 else 'model keeps'} the edge film of the laminate at the copper temperature (no laminate nodes along the edge), so with an "
         f"edge coefficient of {num(hs, 2)} W/m2K on a {num(t_mm, 2)} mm board {'they read' if len(reduced) > 1 else 'it reads'} the board too cool where much of the heat leaves "
         "through the edge (two-layer boards against the FVM, a 10 mm part in a corner of a 30 x 20 mm board: about -3 % at 100 W/m2K on 1.6 mm or 50 W/m2K on 3.2 mm, -6 % at "
         "200 W/m2K on 1.6 mm, -13 % at 200 W/m2K on 3.2 mm; less for a part far from the edge or a large board). Use the FVM or the FDM for such a board.",
         f"{names}: edge coefficient {num(hs, 2)} W/m2K on {num(t_mm, 2)} mm, the edge laminate is held at the copper temperature and the board reads cool (-3 to -13 %); use the FVM or FDM.")
    return out


def thick_plate_bound(power, area, thickness, k):
    """!
    @brief Upper bound of how much hotter the surface under a source can be than the through-thickness mean the layered models keep: q'' t / (2 k).
    @details The bound is reached when all the heat crosses the plate with a uniform flux q'' = power / area (a linear profile through the thickness);
             with sideways spreading the measured gradient is 0.6 to 0.8 of it (research/effective-conductivity, README 4.6). It is a bound, never a correction.
    @param power Heat crossing the plate in W.
    @param area Area it crosses in m2.
    @param thickness Thickness of the plate (a copper layer or a metal block) in m.
    @param k Conductivity of the plate in W/mK.
    @return Temperature difference in K (0 for a degenerate input).
    """
    if area <= 0 or k <= 0 or thickness <= 0:
        return 0.0
    return 0.5 * abs(power) / area * thickness / k


def _block_flux_under(result, heater, face):
    """!
    @brief Largest heat flux into the metal blocks of one face under the footprint of a heater, from a solved result.
    @param result SteadyResult with arrays block_flux and block_face (FVM, FDM), or None.
    @param heater The Heater.
    @param face Face of the blocks (0 top, 1 bottom).
    @return Flux in W/m2, or None when the result does not carry the flux into the blocks (Lumped, Analytic, 3D solid).
    """
    if result is None or "block_flux" not in result.arrays or result.T is None:
        return None
    faces = list(np.asarray(result.arrays["block_face"]))
    if face not in faces:
        return None
    flux = result.arrays["block_flux"][faces.index(face)]
    ny, nx = flux.shape
    # Cell centres (FVM) or nodes (FDM) in metres; the cells or nodes whose position lies inside the footprint
    off = 0.0 if getattr(result, "grid", "cells") == "nodes" else 0.5
    x, y = (np.arange(nx) + off) * result.dx, (np.arange(ny) + off) * result.dy
    X, Y = np.meshgrid(x, y)
    inside = points_in_polygon(X, Y, heater.polygon)
    if not inside.any():
        # A footprint smaller than a cell: the cell or node nearest its centre
        cx, cy = polygon_centroid(heater.polygon)
        inside = np.zeros_like(inside)
        inside[min(max(int(round(cy / result.dy - off)), 0), ny - 1), min(max(int(round(cx / result.dx - off)), 0), nx - 1)] = True
    return float(flux[inside].max())


def check_thick_plates(problem, rows, result=None):
    """!
    @brief Post-run warnings for a heater on a thick, poorly conducting plate (its copper layer or a metal block under its footprint).
    @details The layered models keep one temperature per copper layer and per block, the mean through the thickness. Where a flux q'' crosses a plate of
             thickness t and conductivity k, its surface can be hotter than that mean by up to q'' t / (2 k); the warning appears when that bound exceeds
             THICK_PLATE_LIMIT (5 %) of the rise of the heater. For the copper layer of the heater q'' is the heat of the heater over its footprint (the
             heat enters the copper there). For a metal block it is the largest flux that actually enters the block under the footprint in the solved
             result (FVM or FDM): a block under the board is fed through the laminate and its copper, which spread the heat, and the flux of the footprint
             would overstate it 5 to 70 times (a 3 x 3 mm, 2 W part over 3 mm of steel: 9 % with the footprint flux, 0.26 % with the flux into the block,
             no measurable effect in the 3D solid). With a model that does not give that flux (Lumped, Analytic, 3D solid alone) the footprint flux is used,
             an overestimate. The dielectric gaps are not checked: a gap is a series resistance between two nodes, not a node with a mean temperature, so its
             through-thickness drop is already in the model. Measured over the 74 metal-block cases of research/block-and-fins: median 0.07 % and maximum
             0.34 % of the rise, and 35 um of copper is of the order of 1e-4 K, so the check does not fire on the boards the program is built for. The bound
             is never added to the result.
    @param problem The Problem that was solved.
    @param rows Heater rows of the reference model (Simulation.heater_rows(): name, power_board_w, t_max), one per heater in order.
    @param result The reference SteadyResult that produced the rows (gives the flux into the blocks), or None.
    @return List of warning strings (empty when no plate is thick).
    """
    out = []
    b = problem.board
    for h, row in zip(problem.heaters, rows):
        rise = row["t_max"] - b.ambient
        area = polygon_area(h.polygon)
        if rise <= 0 or area <= 0:
            continue
        power = row["power_board_w"]
        footprint_flux = abs(power) / area
        # Plates under the source: its own copper layer and every metal block whose polygon holds the centre of the footprint
        plates = [(f"the copper of layer {h.layer + 1}", b.copper_thickness[h.layer], b.materials.k_copper, footprint_flux, "")]
        cx, cy = polygon_centroid(h.polygon)
        for j, s in enumerate(problem.heatsinks):
            if s.is_block() and bool(points_in_polygon(np.array([cx]), np.array([cy]), s.polygon)[0]):
                face = 0 if (s.layer == 0 or b.layers == 1) else 1          # The face rule of blocks.block_faces
                q = _block_flux_under(result, h, face)
                note = "" if q is not None else " (heat flux of the footprint: this model does not give the flux into the block, so the bound is high)"
                plates.append((s.name or f"Heatsink {j + 1}", s.thickness, s.k, footprint_flux if q is None else q, note))
        for what, t, k, q, note in plates:
            drop = thick_plate_bound(q, 1.0, t, k)
            if drop > THICK_PLATE_LIMIT * rise:
                out.append(f"{row['name'] or 'Heater'}: {what} ({num(1000 * t, 3)} mm, {num(k)} W/mK) is thick and poorly conducting for the heat flux under the part: the surface "
                           f"under the source can be hotter than the model shows by up to {drop:.1f} K ({100 * drop / rise:.0f} % of its rise of {rise:.1f} K){note}; the models "
                           "keep one temperature through the thickness. The value is a bound, not added to the results.")
    return out


def fin_channel_fraction(ra_b):
    """!
    @brief Fraction of the isolated-plate coefficient that a vertical fin channel keeps, phi = [1 + (14.16 / Ra_b^(3/4))^2]^(-1/2).
    @details It follows from the composite of Bar-Cohen and Rohsenow (1984), read as printed in equation 21 (p 83) of Teertstra, Culham and Yovanovich, J. Electronics Manufacturing 7 (2) (1997) 79-92, Nu_b = [(24 / Ra_b)^2 + (0.59 Ra_b^(1/4))^(-2)]^(-1/2), divided by the
             isolated-plate term 0.59 Ra_b^(1/4); 14.16 = 24 x 0.59. It is used only to word the warning, never to change a result.
    @param ra_b Channel Rayleigh number (dimensionless, positive).
    @return Number between 0 and 1.
    """
    return (1.0 + (24.0 * 0.59 / ra_b ** 0.75) ** 2) ** -0.5


def fin_channel_rayleigh(gap, length, theta, ambient):
    """!
    @brief Channel Rayleigh number Ra_b = g beta theta b^4 Pr / (nu^2 L) of the air between two fins.
    @details The air properties are taken at the film temperature ambient + theta / 2 (convection.air_properties) and beta = 1 / T_film.
    @param gap Air gap between two fins (pitch minus thickness) in m.
    @param length Length of the channel in m.
    @param theta Mean excess temperature of the block over the ambient air in K.
    @param ambient Ambient air temperature in degC.
    @return Ra_b, dimensionless (0 for a degenerate input).
    """
    if gap <= 0 or length <= 0 or theta <= 0:
        return 0.0
    air = convection.air_properties(ambient + theta / 2.0)
    return convection.G * air["beta"] * theta * gap ** 4 * air["pr"] / (air["nu"] ** 2 * length)


def _block_excess(result, problem, block):
    """!
    @brief Mean excess temperature of one metal block over the ambient air, from a solved result.
    @param result SteadyResult with arrays block_T (FVM, FDM, 3D solid), or None.
    @param problem The Problem that was solved.
    @param block The Heatsink (a block).
    @return Mean excess in K over the cells or nodes inside the block polygon, weighted by the covered fraction of the block (block_cov), or None when the
            result does not carry the block temperatures.
    """
    if result is None or "block_T" not in result.arrays:
        return None
    b = problem.board
    face = 0 if (block.layer == 0 or b.layers == 1) else 1
    faces = blocks.block_faces(problem)             # The order of the block layers of the result
    T = np.asarray(result.arrays["block_T"])
    if face not in faces or T.shape[0] != len(faces):
        return None
    field = T[faces.index(face)]
    ny, nx = field.shape
    off = 0.0 if getattr(result, "grid", "cells") == "nodes" else 0.5
    X, Y = np.meshgrid((np.arange(nx) + off) * result.dx, (np.arange(ny) + off) * result.dy)
    inside = points_in_polygon(X, Y, block.polygon).astype(float)
    # Weight by the covered fraction: a block cut at the board outline has cells inside its polygon but off the board, which hold the ambient
    # temperature (block_T is ambient where there is no block); an unweighted mean counted them and read an L-shaped board 25 % too cool
    if "block_cov" in result.arrays and np.asarray(result.arrays["block_cov"]).shape == T.shape:
        inside = inside * np.asarray(result.arrays["block_cov"])[faces.index(face)]
    if inside.sum() <= 0:
        return None
    return float(((field - b.ambient) * inside).sum() / inside.sum())


def check_fin_channels(problem, result=None):
    """!
    @brief Post-run warning for plate fins so close that the air between them is slowed (the model gives one coefficient to every face).
    @details For every finned block in still air the check computes the channel Rayleigh number Ra_b = g beta theta b^4 Pr / (nu^2 L) with b the air gap
             (pitch minus thickness), L the longer side of the bounding box of the block (the program has no fin direction; the longer side is the
             conservative choice; for a block cut at the board outline it is still the side of the drawn polygon), theta the mean excess of the block over the
             ambient air from the solved result (weighted by the covered fraction of the block), the air at ambient + theta / 2 and
             beta = 1 / T_film. It warns when Ra_b < FIN_CHANNEL_RA_LIMIT (90): the channel keeps less than 90 % of the coefficient of an isolated plate
             (Bar-Cohen and Rohsenow 1984, read as printed in equation 21, p 83, of Teertstra, Culham and Yovanovich, J. Electronics Manufacturing 7 (2) (1997) 79-92; research/fin-channel). The review takes beta = 1 / T_0 (the inlet air): the Ra_b here is about 5 % lower at a 30 K excess, a 4 % shift of the threshold; the low-Ra branch of a finite array is the lower bound of the coefficient (Martin, Raithby and Yovanovich 1991, p 904), so the warning errs on the safe side (research/theory-sources 9.3). Of the 667 cases of the 1080-case study grid whose channel costs 10 % or more of the
             finned-face conductance, the threshold missed 1 (the old rule, a gap below 4 mm, missed 367). The text gives the fraction phi and the loss of
             the finned face; nothing is added to the results. Forced air (air speed above zero) gets through narrow channels and is not checked. Without
             block temperatures in the result (Lumped, Analytic) the check says nothing: api runs an auxiliary FVM, as for the thick-plate check, so the
             warning still rests on a simulation.
    @param problem The Problem that was solved.
    @param result The SteadyResult that carries arrays block_T, or None.
    @return List of warning strings (empty when no channel is close).
    """
    out = []
    b = problem.board
    if b.air_speed > 0:
        return out
    for j, s in enumerate(problem.heatsinks):
        if not s.has_fins():
            continue
        theta = _block_excess(result, problem, s)
        if theta is None or theta <= 0:
            continue
        xs, ys = [p[0] for p in s.polygon], [p[1] for p in s.polygon]
        length = max(max(xs) - min(xs), max(ys) - min(ys))
        gap = s.fin_pitch - s.fin_thickness
        ra = fin_channel_rayleigh(gap, length, theta, b.ambient)
        if ra < FIN_CHANNEL_RA_LIMIT:
            phi = fin_channel_fraction(ra)
            loss = 100 * (1 - phi)
            # Below Ra_b 14 the closed-channel model is far too pessimistic for arrays open in front (research/fin-channel-sources), so the loss is a bound
            loss_text = (f"up to {loss:.0f} % less (a bound: arrays open in front lose less)" if ra < FIN_CHANNEL_RA_BOUND
                         else f"{loss:.0f} % less")
            if b.orientation == "vertical":
                where = "Valid for a vertical board."
            elif s.layer == 0:
                where = ("Fins up on a horizontal board: measured arrays (one paper, six arrays) lose about as much; "
                         "the effect is not otherwise quantified.")
            else:
                where = "Fins down on a horizontal board: the effect is not quantified (no measurement was found)."
            out.append(f"{s.name or f'Heatsink {j + 1}'}: the channel between the fins ({num(1000 * gap, 3)} mm wide, about {num(1000 * length, 3)} mm long, block {theta:.0f} K above "
                       f"the air) has a channel Rayleigh number of {ra:.0f}; the air between the fins cools {loss_text} than a plate of the same height "
                       f"({phi:.2f} of its coefficient), and the model does not slow it. Use a larger pitch, shorter channels, or the datasheet theta_SA. "
                       + where)
    return out


# Face Rayleigh number below which the natural-convection coefficient of a vertical board is called uncertain (research/plate-h-level INTEGRATION.md 2,
# "Warnings"): a face about 10 mm high at a 10 K excess. The 2D numerical plate of that study covers Ra 1e4 to 3e7 only; below 1e3 the boundary layer is not
# thin compared with the plate (the pure boundary-layer value is 15 % below the laminar form at 1e3, README 4) and the two forms of Churchill and Chu
# differ by up to 4 to 6 % (+4.3 % at 1e3, -5.8 % at 10); the air drawn in at the sides of a small 3D board is not in either form
LOW_RAYLEIGH_LIMIT = 1.0e3


def check_low_rayleigh(board, info):
    """!
    @brief Post-run warning for a vertical board whose face Rayleigh number is so low that the coefficient of natural convection is uncertain.
    @details The Rayleigh number is that of the board height and the mean face-to-air excess at the film temperature (convection.h_natural_vertical,
             as returned by convection.board_h); a face about 10 mm high at a 10 K excess has Ra 1e3. Below LOW_RAYLEIGH_LIMIT no study of the program checks
             the coefficient (research/plate-h-level: the numerical plate starts at 1e4), the layer is not thin compared with the face, and the plate
             correlation does not count the air drawn in at the sides; the two forms of Churchill and Chu agree to 4 to 6 % there, so the warning is about
             the correlation itself, not about the choice of form. A face where forced convection is at least the natural one is not counted (the natural
             term hardly enters the blend of convection.board_h). Horizontal boards are not checked here (their range warning, Ra 1e4 to 1e11 on the top
             face, is in api._solve_computed_h; research/plate-h-level did not study them) and neither are boards with typed coefficients.
             Called once per simulation, from the reference model (api._part_warnings), so that five models do not give five copies.
    @param board Board with orientation, h_mode and height (m).
    @param info Dict of convection.board_h: per face "top" / "bottom" the "rayleigh" number (dimensionless) and the "natural" and "forced" coefficients (W/m2K).
    @return List of warning strings (empty when the Rayleigh number is not low or the board is not vertical in computed mode).
    """
    if board.orientation != "vertical" or board.h_mode != "computed":
        return []
    # Faces where natural convection is the larger part of the convection
    ras = [info[f]["rayleigh"] for f in ("top", "bottom") if info[f]["natural"] > info[f]["forced"]]
    if not ras or min(ras) >= LOW_RAYLEIGH_LIMIT:
        return []
    return [f"the face Rayleigh number {num(min(ras), 2)} of the vertical board ({num(board.height * 1000.0, 3)} mm high) is below {num(LOW_RAYLEIGH_LIMIT, 2)}: "
            "the face is too small or too little heated for a thin boundary layer, and the natural-convection coefficient is not checked there "
            "(the plate correlation does not count the air drawn in at the sides; the general and laminar forms differ by 4 to 6 %); treat the "
            "convection as uncertain and, where it matters, fit it to a measurement (convection multiplier) or type the coefficients"]


# Cell size (mm) from which the via effect of the FVM and FDM is called uncertain: at 2 mm the via is a fraction of a cell
VIA_COARSE_CELL_MM = 2.0


def check_via_limits(problem, models, cell_mm):
    """!
    @brief Warnings about the vias on the grid: a via touching the edge of the board, and a cell too coarse for the vias (FVM and FDM).
    @details The mean-potential via of the FVM and FDM (viawell.py) converges as the cell shrinks, but
             * its kernel has no image of the board edge, so a via within one cell of the edge of the box or of the outline is clipped and its effect is
               too large (research/via-real-board, README 3.1: +12 to +15 % for a via 0.16 mm from the edge at a 1 mm cell). The FVM now adds the mirror image
               of a straight edge (viawell.edge_term; research/via-edge-image: +14.5 % becomes +0.7 %), so the warning stays only for what it does not
               cover cleanly (a slanted, curved or short outline side or a reflex corner within six cells, where the image is partial or left out and
               the via effect was measured -6 to +12 % off at 1 mm, docs/validation.md 28.1; a cell of 2 mm or more, where the image is applied but
               the via is a fraction of a cell, +3 to +4 % at 2 mm; a via centre within its radius of the edge) and for the FDM (-4.5 to -10 % at
               1 mm) and the 3D solid (about +19 points), which have no image;
             * from a 2 mm cell the via is a fraction of a cell and the position of its centre inside the cell moves the answer. Measured on the example
               board (9 vias, the drop of the hottest temperature caused by the vias, 9.6 K at 0.25 mm): FVM -2.9 % at 2 mm, -0.3 % at 0.5 mm, FDM -4.0 % at
               2 mm, -0.2 % at 0.5 mm, and at 3 and 4 mm the error is between -5 and +16 % (FVM) and -22 and -49 % (FDM), by the position of the vias
               (the FDM -41 % first measured at 3 mm had the footprints up to one cell off in y, where dy differs from dx).
    @param problem The Problem.
    @param models Model keys that will run (the cell warning applies to "fvm" and "fdm", the edge warning to "fvm", "fdm" and "solid3d").
    @param cell_mm Cell size in mm.
    @return List of warning strings (empty when nothing is doubtful).
    """
    out = []
    if not problem.vias or problem.board.layers < 2:
        return out                                              # A one-layer board has no gap: its vias join nothing and change no model
    b = problem.board
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 8)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 8)
    dx, dy = b.width / nx, b.height / ny
    if any(m in ("fvm", "fdm", "solid3d") for m in models):
        # The edge test reads the cells of the FVM/FDM grid (the 3D solid has the same footprint rule). The FVM gives the via the mirror image of a straight
        # edge (viawell.edge_term, at every cell); the warning is dropped only for a clean neighbourhood at a cell finer than VIA_COARSE_CELL_MM, and the
        # FDM and the 3D solid keep it.
        edge = viawell.edge_via_indices(problem, nx, ny, dx, dy, b.cover(nx, ny, dx, dy))
        others = bool({"fdm", "solid3d"} & set(models))
        todo = []
        for k in edge:
            v = problem.vias[k]
            covered = False
            if "fvm" in models and cell_mm < VIA_COARSE_CELL_MM:
                walls, clean = viawell.edge_walls(problem, v, viawell.EDGE_REACH_CELLS * max(dx, dy))
                # A via whose centre is within its own radius of the wall is cut by the edge: the image is taken at the radius, not at the centre
                covered = bool(walls) and clean and all(abs((v.x if a == "x" else v.y) - q) >= v.diameter / 2.0 for a, q in walls)
            if others or ("fvm" in models and not covered):
                todo.append((k, covered))
        for k, covered in todo[:5]:
            v = problem.vias[k]
            name = v.name or f"Via {k + 1}"
            if "fvm" in models and not covered:
                _add(out, "via", k, f"{name}: via touching the board edge (within one cell of the edge). The FVM corrects the cut footprint with the mirror image of a straight "
                                    "edge of the board (or of an axis-parallel side of an outline), but here the correction is partial: a slanted, curved or short side or a "
                                    "reflex corner is near, the via centre is within its radius of the edge, or the cell is 2 mm or more. The via effect can be off by about "
                                    "-6 to +15 % at a 1 mm cell; use a finer cell (" + cell_where() + ") or read the result near it with care.",
                     f"{name}: via within one cell of the board edge; its effect can be off by -6 to +15 % at 1 mm.")
            else:
                _add(out, "via", k, f"{name}: via touching the board edge (within one cell of the edge). The FVM treats it with the mirror image of the edge, but the FDM "
                                    "(half-volume edge nodes) has no image and reads the via effect 4 to 10 % too small at a 1 mm cell, and the 3D solid has none and reads it about "
                                    "19 points too large; use the FVM, or a finer cell (" + cell_where() + "), for the part near it.",
                     f"{name}: via within one cell of the board edge; FDM and 3D solid have no image of the edge (effect 4 to 10 % too small and about 19 points too large at 1 mm).")
        if len(todo) > 5:
            _add(out, None, None, f"{len(todo) - 5} more vias touch the board edge (see above).")
    if cell_mm >= VIA_COARSE_CELL_MM and any(m in ("fvm", "fdm") for m in models):
        _add(out, None, None, f"The cell ({num(cell_mm, 3)} mm) is coarse for the vias: a via is a fraction of a cell, so the temperature drop they cause is uncertain "
                              "by about 3 to 4 % at 2 mm and by 5 to 50 % at 3 to 4 mm, depending on where each via falls in its cell (example board: 9 vias, "
                              "-3 % FVM and -4 % FDM at 2 mm, within 0.5 % at 0.5 mm). Use 1 mm or finer (" + cell_where() + ").",
             f"The cell ({num(cell_mm, 3)} mm) is coarse for the vias (3 to 50 % uncertainty in their effect); use 1 mm or finer ({cell_where()}).")
    return out


PARTIAL_MIN_SHARE = 0.05    # A footprint cell takes part in the partial-copper test when it holds at least this share of the largest footprint weight (research/via-partial-copper, lib/warnrule.py)
PARTIAL_RATIO = 0.5         # A footprint is partial in a layer when the smallest sheet conductance of the taking-part cells is below this share of the largest


PARTIAL_COPPER_BUDGET_S = 0.3   # Wall time of the partial-copper via pass of the live list (a synthetic board of 8500 vias on 1 mm stripes took 2.3 s at 0.5 mm); patchable by the tests


def partial_copper_vias(problem, cell_mm):
    """!
    @brief The vias whose footprint on the grid of a run covers a copper layer with copper over only part of it, with the worst layer of each.
    @details The footprint is the one the FVM would use (viawell.footprint: the disc of the drill enlarged to the target radius, on the cells of the run). A footprint is
             partial in a layer when, among the cells that hold at least PARTIAL_MIN_SHARE of the largest weight, the smallest sheet conductance per unit of board is
             below PARTIAL_RATIO times the largest (a copper edge or a track end inside the footprint, a clearance wider than a cell). The sheet is that of the layer node
             before the laminate rule (copper plus the in-plane FR-4 of the rest of the slab), as the cell fill gives it; it is not read from a network, so the check is
             cheap enough for the live list. The sheet after the rule (lower in the bare cells) flags the same vias and 0 to 6 more per board on seven imported boards
             (validation 30.2), so the rule errs on the silent side by those few. Near a straight board edge the FVM of feature/via-edge-image enlarges the footprint
             further; this check keeps the plain footprint.
             Why it matters (research/via-partial-copper): the via draws heat from each footprint cell in proportion to a fixed weight, so on a partial footprint the
             bare cells cannot supply it (a cold spot under the barrel in the FVM) and the via effect is misread: 15 to 85 % low at a copper corner or a track end (FVM and FDM, cells of 1 to 0.25 mm)
             (31 to 68 % before the rim rule of viawell.build), and for a via just outside a copper edge lost (drawn copper) or, on imported copper, 3 to 4 times high at 0.5 mm or coarser.
    @param problem The Problem.
    @param cell_mm Cell size in mm.
    @return Tuple (partial, n_checked): partial is a list of (via index, layer index, ratio of the smallest to the largest sheet conductance), one entry per via
            (its layer of the smallest ratio); n_checked is the number of vias with a footprint on the board.
    """
    partial, n_checked, _ = partial_copper_scan(problem, cell_mm)
    return partial, n_checked


def partial_copper_scan(problem, cell_mm, budget_s=None):
    """!
    @brief partial_copper_vias with an optional time cap, for the live list.
    @param problem The Problem.
    @param cell_mm Cell size in mm.
    @param budget_s Wall time in seconds after which the pass stops (None: no cap); the clock is read before each exact via test.
    @return Tuple (partial, n_checked, truncated): as partial_copper_vias, and True when the cap stopped the pass (the counts are then those of the vias reached, "at least").
    """
    t_start = time.perf_counter()
    b = problem.board
    if not problem.vias or b.layers < 2:
        return [], 0, False                                           # A one-layer board has no gap: its vias join nothing
    nx = max(int(round(b.width * 1000.0 / cell_mm)), 2)          # The grid of fvm.solve: the footprint must be that of the run (the floor of 8 of the other checks gave a 5 mm board 0.625 mm cells at 1 mm)
    ny = max(int(round(b.height * 1000.0 / cell_mm)), 2)
    dx, dy = b.width / nx, b.height / ny
    try:
        fill = copper.problem_fill(problem, nx, ny, dx, dy, 4)
    except ValueError:
        return [], 0, False                                     # Damaged imported copper: check_problem already says so
    cover = b.cover(nx, ny, dx, dy)
    # Sheet conductance per unit of board of every layer node (the S of fvm.Network divided by the cover): copper plus the in-plane FR-4 of the rest of the slab
    t_cu = np.asarray(b.copper_thickness, dtype=float)[:, None, None]
    k_lam, _ = b.layer_laminate()
    slab = b.slab_thicknesses()[:, None, None]
    rel = fill * b.materials.k_copper * t_cu + k_lam[:, None, None] * (slab - fill * t_cu)
    # Cheap prefilter: the footprint search (a bisection on the radius) costs 0.3 ms per via at a fine cell, 2.5 s for 8500 vias at 0.5 mm. A via can fire only when the sheet
    # conductance varies by more than the ratio inside a window that contains its footprint: the disc grows to the target radius, which stays within about the drill
    # radius plus a cell, so a window of twice the drill radius in cells plus three covers it (checked against the exact test on the study boards and the imported windows).
    # The vias are then tested exactly only where such a window exists.
    reach = int(math.ceil(max(v.diameter for v in problem.vias) / 2.0 / min(dx, dy))) * 2 + 3
    size = 2 * reach + 1
    maybe = np.zeros((ny, nx), dtype=bool)
    on = cover > 0
    for l in range(b.layers):
        lo = ndimage.minimum_filter(np.where(on, rel[l], np.inf), size=size, mode="nearest")
        hi = ndimage.maximum_filter(np.where(on, rel[l], -np.inf), size=size, mode="nearest")
        maybe |= lo < PARTIAL_RATIO * hi
    partial, n_checked = [], 0
    for k, (v, share) in enumerate(zip(problem.vias, problem.via_board_shares())):
        if share <= 0.0:
            continue                                            # No board under the drill disc: ignored by every model
        if not maybe[min(max(int(v.y / dy), 0), ny - 1), min(max(int(v.x / dx), 0), nx - 1)]:
            n_checked += 1                                      # Uniform neighbourhood: counted, cannot fire (the exact test would give a footprint)
            continue
        if budget_s is not None and time.perf_counter() - t_start > budget_s:
            return partial, n_checked, True                     # The cap: the vias not reached are not counted, the warning says "at least"
        w, _, _ = viawell.footprint(v.x, v.y, v.diameter / 2.0, dx, 0.0, cover, dy, 0.0)
        if not w:
            continue
        n_checked += 1
        wmax = max(w.values())
        cells = [c for c, x in w.items() if x >= PARTIAL_MIN_SHARE * wmax]
        rows = np.array([c[0] for c in cells])
        cols = np.array([c[1] for c in cells])
        vals = rel[:, rows, cols]                               # (layers, cells)
        ratio = vals.min(axis=1) / vals.max(axis=1)
        layer = int(np.argmin(ratio))
        if ratio[layer] < PARTIAL_RATIO:
            partial.append((k, layer, float(ratio[layer])))
    return partial, n_checked, False


PARTIAL_LISTED = 3          # Vias named in the partial-copper warning (the worst by the ratio); the rest are counted


def check_via_partial_copper(problem, models, cell_mm, budget_s=None):
    """!
    @brief Warning for the vias whose footprint covers a copper layer with copper over only part of it (FVM and FDM): one aggregated message with the count, the worst few and the rule.
    @details The rule and its measurements are those of partial_copper_vias (research/via-partial-copper: 0 false alarms on the five frozen boards with vias at 2, 1 and 0.5 mm; on
             seven imported boards it fires on 2 to 43 % of the vias, so it is a live line with the share, not a property of every via). The text does not say which way the via effect
             is misread because it goes both ways (research/via-contact-geometry 7.2: at the corner of a copper region or the end of a track the via effect reads 15 to 85 % low (FVM and FDM, cells of 1 to 0.25 mm, against the 3D solid and an independent resolved 3D reference), the part
             up to 11 % of the rise too hot, safe side; a drawn via just outside a copper edge is uncoupled from that layer by the rim rule of viawell and loses its effect, up to
             1.2 K or 1.4 % of the rise too hot; on imported copper the rim is not tested and the old 3 to 4 times high at 0.5 mm or coarser remains), and the cold spot below the
             barrel is a numerical artefact of the fixed footprint weights.
    @param problem The Problem.
    @param models Model keys that will run (the warning applies to "fvm" and "fdm").
    @param cell_mm Cell size in mm.
    @param budget_s Time cap in seconds of the pass (the live list; None for none). When it stops the pass the text says "at least N of the M vias examined" and that the
           whole count is in the Results of the run.
    @return List of warning strings (empty or one message).
    """
    out = []
    if not any(m in ("fvm", "fdm") for m in models):
        return out
    partial, n_checked, truncated = partial_copper_scan(problem, cell_mm, budget_s)
    if not partial:
        return out
    worst = sorted(partial, key=lambda t: t[2])[:PARTIAL_LISTED]
    names = "; ".join(f"{problem.vias[k].name or f'Via {k + 1}'} (layer {layer + 1}, smallest sheet {num(100.0 * ratio, 2)} % of the largest)" for k, layer, ratio in worst)
    more = f" and {len(partial) - len(worst)} more" if len(partial) > len(worst) else ""
    n = len(partial)
    # Time cap hit: only the vias reached are counted
    lead = f"At least {n} of the {n_checked} vias examined so far have" if truncated else f"{n} of {n_checked} via{'s have' if n > 1 else ' has'}"
    cap_note = " The live check stopped early to stay fast; the Results of the run hold the full count." if truncated else ""
    _add(out, "via", worst[0][0],
         f"{lead} copper over only part of {'their footprint' if n > 1 else 'its footprint'} on a copper layer "
         f"(the smallest sheet conductance among the footprint cells that count is below {num(PARTIAL_RATIO, 1)} of the largest: a copper edge or a track end inside the footprint, "
         f"or a clearance wider than a cell). Worst: {names}{more}. The via effect may be misread, higher or lower. A via at the corner of a copper region or at the end of a track "
         "is not solved: its effect reads 15 to 85 % low and the part up to 11 % of its rise too hot, the safe side (measured at cells of 1 to 0.25 mm). A drawn via just outside a copper edge, not under a part, is "
         "left uncoupled from that layer and loses its effect (about 1.2 K, 1.4 % of the rise, too hot, on the board measured); on imported copper that contact is not tested, and there the effect can read "
         "3 to 4 times high at a cell of 0.5 mm or coarser. The cold spot that the FVM can show below the barrel is a numerical artefact of the footprint weights. Use a finer cell (" + cell_where() + ") or check the via with the 3D solid." + cap_note,
         f"{lead} copper over only part of {'their footprint' if n > 1 else 'its footprint'}; the via effect may be misread "
         "(higher or lower); use a finer cell (" + cell_where() + ") or the 3D solid.")
    return out


def uncoupled_vias(problem):
    """!
    @brief The vias whose drill rim touches no copper and no part on a layer (the rim rule of viawell), with those layers.
    @param problem The Problem (imported copper counts as full contact, as in viawell).
    @return List of (via index, list of 0-based layer indices), only the vias with at least one such layer and board under the drill disc.
    """
    b = problem.board
    if not problem.vias or b.layers < 2:
        return []                                               # A one-layer board has no gap: its vias join nothing
    zone_index = viawell._zone_index(problem, b.layers)
    out = []
    for k, (v, share) in enumerate(zip(problem.vias, problem.via_board_shares())):
        if share <= 0.0:
            continue                                            # Ignored by every model
        layers = [l for l, f in enumerate(viawell.rim_copper_shares(problem, v, b.layers, zone_index)) if f <= 0.0]
        if layers:
            out.append((k, layers))
    return out


def _layers_text(layers):
    """!
    @brief "layer 1", "layers 1 and 3" or "layers 1, 2 and 3" from 0-based layer indices.
    @param layers Non-empty list of 0-based layer indices.
    @return Text with 1-based numbers.
    """
    nums = [str(l + 1) for l in layers]
    if len(nums) == 1:
        return f"layer {nums[0]}"
    return "layers " + ", ".join(nums[:-1]) + " and " + nums[-1]


def check_via_uncoupled(problem, models):
    """!
    @brief Warning for the vias that touch no copper on a layer and are therefore not connected to it (FVM and FDM): one aggregated message naming up to three.
    @details The safe-side explanation (the effect is lost, the part reads too hot) is in the partial-copper warning, not repeated here.
    @param problem The Problem.
    @param models Model keys that will run (the warning applies to "fvm" and "fdm").
    @return List of warning strings (empty or one message).
    """
    out = []
    if not any(m in ("fvm", "fdm") for m in models):
        return out
    found = uncoupled_vias(problem)
    if not found:
        return out
    names = [(problem.vias[k].name or f"Via {k + 1}", layers) for k, layers in found]
    n = len(found)
    if n == 1:
        name, layers = names[0]
        text = f"{name} touches no copper on {_layers_text(layers)} and is not connected there; draw its pad or plane if it is connected."
    else:
        listed = ", ".join(f"{nm} on {_layers_text(ly)}" for nm, ly in names[:PARTIAL_LISTED])
        more = f", and {n - PARTIAL_LISTED} more" if n > PARTIAL_LISTED else ""
        text = f"{n} vias touch no copper on a layer and are not connected there ({listed}{more}); draw their pads or planes if they are connected."
    _add(out, "via", found[0][0], text)
    return out
