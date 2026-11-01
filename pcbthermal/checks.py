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

import numpy as np

from . import blocks, convection, lumped, viaconstriction, viawell
from .geometry import coverage_fraction, part_board_share, points_in_polygon, polygon_overlap_area, polygon_area, polygon_centroid, polygon_self_intersects, zone_fill
from .numfmt import num

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


def check_problem(problem, cell_mm=1.0):
    """!
    @brief List the validity warnings of a problem.
    @param problem A Problem (assumed structurally valid, see Problem.validate).
    @param cell_mm Cell size (mm) of the raster used for the geometric checks and the FVM mesh.
    @return List of warning strings (empty when nothing is doubtful).
    """
    b = problem.board
    W, H = b.width, b.height
    nx = max(int(round(W * 1000.0 / cell_mm)), 8)
    ny = max(int(round(H * 1000.0 / cell_mm)), 8)
    dx, dy = W / nx, H / ny
    out = []
    board_cover = b.cover(nx, ny, dx, dy)               # Ones for a rectangular board

    # --- Copper fill of every layer (union of its zones), used by several checks
    fill = zone_fill(problem.zones, b.layers, nx, ny, dx, dy, 4)

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
            _add(out, "heater", k, f"{name}: the smallest side is only {n_across:.1f} cells wide; use a cell size of "
                       f"{min(np.ptp(h.polygon[:, 0]), np.ptp(h.polygon[:, 1])) * 1000 / 4:.2f} mm or less.")
        if cov.sum() > 0:
            f_mean = float((fill[h.layer] * cov).sum() / cov.sum())
            if f_mean < 0.02:
                _add(out, "heater", k, f"{name}: there is no copper under it on layer {h.layer + 1}; the heat can only spread "
                           "through the FR-4 and the part will run very hot.", f"{name}: no copper under it on layer {h.layer + 1}; it will run very hot.")
            elif f_mean < 0.98:
                _add(out, "heater", k, f"{name}: a copper edge or hatching crosses its footprint (copper fill {f_mean:.2f}); the "
                           "Lumped and Analytic models are unreliable here, use the FVM.",
                     f"{name}: a copper edge crosses its footprint (fill {f_mean:.2f}); use the FVM.")

    for i in range(len(problem.heaters)):
        for j in range(i + 1, len(problem.heaters)):
            hi, hj = problem.heaters[i], problem.heaters[j]
            if hi.layer == hj.layer and heater_poly[i] is not None and heater_poly[j] is not None:
                # Exact area of the intersection of the two footprints: the 4 x 4 cover of each cell made neighbours 0.3 mm apart "overlap" when
                # both covers touched the same cell
                overlap = polygon_overlap_area(hi.polygon, hj.polygon)
                small = min(polygon_area(hi.polygon), polygon_area(hj.polygon))
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
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if polygon_overlap_area(items[i][1], items[j][1]) > 1e-10:      # Exact; 1e-10 m2 is 0.0001 mm2 (touching blocks do not overlap)
                    _add(out, None, None, f"{items[i][0]} and {items[j][0]} overlap: in the overlap only the later one is used.")

    if problem.total_power() <= 0:
        _add(out, None, None, "The total heater power is zero: the board stays at ambient temperature.")
    return out


def check_input(problem, models, cell_mm=1.0):
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
    @return List of warning strings (CheckWarning, tagged with the element) in the order validity, model limits, vias.
    """
    models = tuple(models)
    return check_problem(problem, cell_mm) + check_model_limits(problem, models, cell_mm) + check_via_limits(problem, models, cell_mm)


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
        fill = zone_fill(problem.zones, b.layers, nx, ny, dx, dy, 4)
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
                    zone_board = (zp, viaconstriction.ViaSet(kept) if len(kept.vias) >= 2 else None)
                zoned = lumped.will_be_zoned(zone_board[0], zone_board[0].heaters[k], vias=zone_board[1])
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
                       "research/young-omega-tiles 3.8, the review of fix/via-constriction, research/lumped-zones-adoption 8.4); use the FVM.",
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
               too large (research/via-real-board, README 3.1: +12 to +15 % for a via 0.16 mm from the edge at a 1 mm cell);
             * from a 2 mm cell the via is a fraction of a cell and the position of its centre inside the cell moves the answer. Measured on the example
               board (9 vias, the drop of the hottest temperature caused by the vias, 9.6 K at 0.25 mm): FVM -2.9 % at 2 mm, -0.3 % at 0.5 mm, FDM -4.0 % at
               2 mm, -0.2 % at 0.5 mm, and at 3 and 4 mm the error is between -5 and +16 % (FVM) and -22 and -49 % (FDM), by the position of the vias
               (the FDM -41 % first measured at 3 mm had the footprints up to one cell off in y, where dy differs from dx).
    @param problem The Problem.
    @param models Model keys that will run (the cell warning applies to "fvm" and "fdm").
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
    if any(m in ("fvm", "fdm") for m in models):
        # The edge test reads the cells of the FVM/FDM grid; the 3D solid has the same footprint rule, so the warning is for the layered grids and the 3D
        edge = viawell.edge_via_indices(problem, nx, ny, dx, dy, b.cover(nx, ny, dx, dy))
        for k in edge[:5]:
            v = problem.vias[k]
            _add(out, "via", k, f"{v.name or f'Via {k + 1}'}: via touching the board edge (within one cell of the edge). The cut footprint has no image of the edge, so "
                                "its effect can be too large by 12 to 15 % at a 1 mm cell; use a finer cell or read the result near it with care.",
                 f"{v.name or f'Via {k + 1}'}: via within one cell of the board edge; its effect can be 12 to 15 % too large at 1 mm.")
        if len(edge) > 5:
            _add(out, None, None, f"{len(edge) - 5} more vias touch the board edge (see above).")
    if cell_mm >= VIA_COARSE_CELL_MM and any(m in ("fvm", "fdm") for m in models):
        _add(out, None, None, f"The cell ({num(cell_mm, 3)} mm) is coarse for the vias: a via is a fraction of a cell, so the temperature drop they cause is uncertain "
                              "by about 3 to 4 % at 2 mm and by 5 to 50 % at 3 to 4 mm, depending on where each via falls in its cell (example board: 9 vias, "
                              "-3 % FVM and -4 % FDM at 2 mm, within 0.5 % at 0.5 mm). Use 1 mm or finer.",
             f"The cell ({num(cell_mm, 3)} mm) is coarse for the vias (3 to 50 % uncertainty in their effect); use 1 mm or finer.")
    return out
