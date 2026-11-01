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

from . import blocks, convection, viaconstriction, viawell
from .geometry import BOARD_SAMPLES, coverage_fraction, part_weights, points_in_polygon, polygon_area, polygon_centroid, polygon_self_intersects, zone_fill
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

    @details It is a plain string for every other use (printing, joining, comparing), with two extra attributes.
    """

    kind = None
    index = None


def _add(out, kind, index, text):
    """!
    @brief Append a warning to a list, tagged with the element it is about.
    @param out List of warnings being built.
    @param kind Element kind ("zone", "heater", "heatsink" or "via"), or None for a warning about the whole design.
    @param index 0-based index of the element in its list, or None.
    @param text Warning text.
    """
    w = CheckWarning(text)
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

    heater_cov = []
    for k, h in enumerate(problem.heaters):
        name = h.name or f"Heater {k + 1}"
        if h.role == "source":
            # A pure source has no junction and no package top: these fields (from a file or the API; the interface zeroes them) are not used
            ignored = [label for label, value in (("theta", h.theta), ("theta_jc_top", h.theta_jc_top), ("theta_sa", h.theta_sa), ("interface", h.interface),
                                                  ("contact_area", h.contact_area), ("pad_thickness", h.pad_thickness), ("pad_k", h.pad_k)) if value > 0]
            if ignored:
                _add(out, "heater", k, f"{name}: a heat source ignores {', '.join(ignored)}; they belong to a component (set its type to Component, or clear them).")
        area = polygon_area(h.polygon)
        if area <= 0:
            _add(out, "heater", k, f"{name}: the footprint has zero area.")
            heater_cov.append(None)
            continue
        cov = coverage_fraction(h.polygon, nx, ny, dx, dy, 4)
        heater_cov.append(cov)
        # Area of the part on the board: the part and the outline tested on the same samples (the product of the two covers is wrong on a cell cut by both)
        inside = float((part_weights(h.polygon, b.outline, nx, ny, dx, dy, BOARD_SAMPLES if b.has_outline() else 4) * (board_cover > 0)).sum() * dx * dy) / area
        if inside < 0.98:
            _add(out, "heater", k, f"{name}: {100 * (1 - inside):.0f} % of the footprint is outside the board; its full power "
                       "is applied to the part that is inside.")
        n_across = min(np.ptp(h.polygon[:, 0]), np.ptp(h.polygon[:, 1])) / min(dx, dy)
        if n_across < 3:
            _add(out, "heater", k, f"{name}: the smallest side is only {n_across:.1f} cells wide; use a cell size of "
                       f"{min(np.ptp(h.polygon[:, 0]), np.ptp(h.polygon[:, 1])) * 1000 / 4:.2f} mm or less.")
        if cov.sum() > 0:
            f_mean = float((fill[h.layer] * cov).sum() / cov.sum())
            if f_mean < 0.02:
                _add(out, "heater", k, f"{name}: there is no copper under it on layer {h.layer + 1}; the heat can only spread "
                           "through the FR-4 and the part will run very hot.")
            elif f_mean < 0.98:
                _add(out, "heater", k, f"{name}: a copper edge or hatching crosses its footprint (copper fill {f_mean:.2f}); the "
                           "Lumped and Analytic models are unreliable here, use the FVM.")

    for i in range(len(problem.heaters)):
        for j in range(i + 1, len(problem.heaters)):
            hi, hj = problem.heaters[i], problem.heaters[j]
            if hi.layer == hj.layer and heater_cov[i] is not None and heater_cov[j] is not None:
                overlap = float((np.minimum(heater_cov[i], heater_cov[j])).sum() * dx * dy)
                small = min(polygon_area(hi.polygon), polygon_area(hj.polygon))
                if overlap > 0.05 * small:
                    _add(out, "heater", i, f"{hi.name or f'Heater {i + 1}'} and {hj.name or f'Heater {j + 1}'} overlap on layer "
                               f"{hi.layer + 1}: their power densities add up.")

    # A via is judged by its drill disc against the outline (or the box): no board under it = ignored by every model; less than half = mostly off
    for k, (v, share) in enumerate(zip(problem.vias, problem.via_board_shares())):
        name = v.name or f"Via {k + 1}"
        if share <= 0.0:
            _add(out, "via", k, f"{name}: via outside the board outline and ignored by every model." if b.has_outline()
                 else f"{name} is outside the board and is ignored by the solvers.")
        elif share < 0.5:
            _add(out, "via", k, f"{name}: more than half of the via is outside the board{' outline' if b.has_outline() else ''}; "
                                "only the part on the board is used.")

    for k, z in enumerate(problem.zones):
        cov = coverage_fraction(z.polygon, nx, ny, dx, dy, 2)
        area = polygon_area(z.polygon)
        if area > 0 and float(cov.sum() * dx * dy) / area < 0.5:
            _add(out, "zone", k, f"{z.name or f'Zone {k + 1}'}: more than half of the zone is outside the board.")
        if polygon_self_intersects(z.polygon):
            _add(out, "zone", k, f"{z.name or f'Zone {k + 1}'}: the outline crosses itself; the fill follows the even-odd rule, so the crossed part is left empty. "
                       "Redraw the zone without the crossing.")

    # --- Metal blocks: they only take heat where they overlap copper of their face
    block_cov = {}
    for k, s in enumerate(problem.heatsinks):
        if not s.is_block():
            continue
        name = s.name or f"Heatsink {k + 1}"
        # Measured against the board outline, not only against the box: a block over the cut-away part of a board has no board under it
        cov = coverage_fraction(s.polygon, nx, ny, dx, dy, 4) * board_cover
        area = polygon_area(s.polygon)
        if area > 0 and float(cov.sum() * dx * dy) / area < 0.9:
            _add(out, "heatsink", k, f"{name}: part of the metal block is outside the board" + (" outline" if b.has_outline() else "") +
                       "; the FVM, FDM and 3D solid cut it there and model only the part inside (the Lumped and Analytic models take the block "
                       "whole on the rectangle of the same area).")
        if cov.sum() > 0:
            overlap = float((fill[s.layer] * cov).sum() * dx * dy)
            if overlap < 1e-6:
                _add(out, "heatsink", k, f"{name}: the metal block does not overlap any copper on its face, so it takes almost no heat "
                           "(through the bare laminate only); add a copper pad under it.")
            elif overlap < 0.25 * area:
                _add(out, "heatsink", k, f"{name}: only {100 * overlap / area:.0f} % of the metal block touches copper; the heat enters "
                           "the block through that overlap only.")
        if s.interface_resistance() < 1e-5:
            _add(out, "heatsink", k, f"{name}: an interface resistance below 10.00E-6 m2K/W is a perfect contact; a gap pad or paste is "
                       "usually 100.00E-6 to 1.00E-3 m2K/W (0.5 mm of a 1 to 5 W/mK pad).")
        face = 0 if (s.layer == 0 or b.layers == 1) else 1
        block_cov.setdefault(face, []).append((name, cov))
    for face, items in block_cov.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if float(np.minimum(items[i][1], items[j][1]).sum() * dx * dy) > 1e-7:
                    _add(out, None, None, f"{items[i][0]} and {items[j][0]} overlap: in the overlap only the later one is used.")

    if problem.total_power() <= 0:
        _add(out, None, None, "The total heater power is zero: the board stays at ambient temperature.")
    return out


# Models whose layered idealisation has no vertical path through a bare cell of a gap (research/bare-spot-under-source, INTEGRATION P3)
LAYERED_MODELS = ("fvm", "fdm", "lumped", "analytic")


def check_model_limits(problem, models, cell_mm=1.0):
    """!
    @brief Warnings about the documented limits of the selected models on this input (text only; no result depends on them).
    @details Two groups, each measured in a research folder: a part whose centre sits on bare laminate (the layered models read below a
             resolved 3D solution; research/bare-spot-under-source, INTEGRATION P3) and vias in the Lumped and Analytic models, which carry ring and
             tile means and add the constriction of the heat converging on a barrel (viaconstriction.py; research/lumped-analytic-vias,
             research/young-omega-tiles 3; the numbers are the error of the via effect against the FVM at 0.25 mm on the 29 boards of the
             branch fix/via-constriction and 17 more boards of its review, measured on this program). The Analytic copper-spread warning lives in analytic._effective_sheet, where its weights are computed.
    @note The warning about vias on a coarse cell proposed by research/point-via-convergence is not here: its numbers (3.70 against
          4.20 K) are those of the point-via treatment, not of the program as it is, whose FVM via effect on the example board is
          9.02 / 8.86 / 8.84 K at 2 / 1 / 0.5 mm; it belongs with that fix.
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
                           "the Lumped (-43 to +7 %) and the Analytic (-4 to -63 %) not systematically; use the 3D solid for the final value.")

    if not problem.vias:
        return out

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
        for k, h in enumerate(problem.heaters):
            inside = points_in_polygon(vx, vy, h.polygon) & on_board
            in_any |= inside
            n_in = int(inside.sum())
            if n_in >= 1:
                _add(out, "heater", k, f"{h.name or f'Heater {k + 1}'}: {n_in} via{'s' if n_in > 1 else ''} under the footprint; the Lumped "
                           "model joins the planes through a well and the barrel of each ring, so its via effect was measured from 21 % too small "
                           "(dense arrays under a part: the part too hot) to 22 % too large (sparse arrays, rows: the part too cool), and up to 80 % too "
                           "large for an array across the edge of the footprint (8 to 20 % on average over 46 boards); use the FVM for via design.")
        outside = np.flatnonzero(~in_any & on_board)
        if outside.size:
            # One warning for all of them: a Gerber board can have hundreds of vias away from the parts
            v = problem.vias[int(outside[0])]
            first = v.name or f"Via {int(outside[0]) + 1}"
            _add(out, "via", int(outside[0]), f"{first}{f' and {outside.size - 1} more vias' if outside.size > 1 else ''}: outside the "
                       "footprint of every part; the Lumped model spreads such a via over a ring around the part: the effect of a lone via was "
                       "measured 22 % too small to 65 % too large depending on the distance and the number of rings (an effect of 0.5 to 3 K), "
                       "that of a row 6 to 21 % too large, and that of an array just outside the edge or of vias scattered over the board 19 to "
                       "56 % too large (research/young-omega-tiles 3.8 and the review of fix/via-constriction); use the FVM.")
    if "analytic" in models and on_board.any() and b.layers > 1:
        # The tile of the correction follows the pitch (1 mm at most, 0.25 mm at least) and is enlarged when the dense system would pass MAX_UNKNOWNS;
        # a pitch under 0.45 mm was not tested. The program's tile is 2.5 to 5 mm; the rule never reaches it, the guard can. The guard counts the tiles of the
        # heatsinks and blocks too (viaconstriction.heatsink_tiles); this check uses a 5 mm program tile, the solver its own 2.5 to 5 mm one, so the
        # coarsened tile quoted here can differ from the solver's when the guard goes beyond 2.5 mm.
        vs = viaconstriction.ViaSet(problem)
        nt = (int(math.ceil(W / 5e-3)), int(math.ceil(H / 5e-3)))
        pl = viaconstriction.plan(problem, vs, (nt[0], nt[1], W / nt[0], H / nt[1]), b.layers)
        t_rule, t_final, d_med = pl["t_rule"], pl["t_final"], viaconstriction.median_nn(vs)
        n_unknown = pl["active"] * b.layers
        if t_final > t_rule * (1.0 + 1e-6):
            _add(out, None, None, f"Analytic model: the tile of the via correction was coarsened from {num(t_rule * 1e3, 2)} to {num(t_final * 1e3, 2)} mm "
                                  f"to keep its dense system small (estimate of {viaconstriction.MAX_ACTIVE_TILES} active tiles, at most {viaconstriction.MAX_UNKNOWNS} unknowns counting "
                                  f"the tiles of the heatsinks and metal blocks; {len(vs)} vias); the via effect is less accurate (measured 14 % too small to 3 % "
                                  "too large at tiles of 1.6 to 2.4 mm: 500 and 2000 scattered vias, a heatsink or a block over most of the board; "
                                  "not tested for 400 or more vias at a pitch under 1 mm).")
        if d_med < 0.45e-3:
            _add(out, None, None, f"Analytic model: the median via pitch is {num(d_med * 1e3, 2)} mm, below the 0.45 mm tested; the tile is cut to 0.25 mm at least and the "
                                  "via effect is unverified.")
        if n_unknown > 2400:
            # Peak memory measured by the review: 0.15 GB of the program plus about four dense matrices of n^2 doubles (0.9 GB and 3 s at 4800 unknowns)
            _add(out, None, None, f"Analytic model: the via correction solves a dense system of {n_unknown} unknowns (about {0.15 + 0.75 * (n_unknown / 4800.0) ** 2:.1f} GB "
                                  "and a few seconds; 0.9 GB and 3 s were measured at 4800 unknowns).")
        if len(vs) <= 2:
            _add(out, None, None, "Analytic model: one or two vias beside or under a part were measured up to 16 % too small in the via effect "
                                  "(an effect of 1 to 4 K; the tile is 1 mm and the barrel is read at its scale); use the FVM for the value.")
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
    @details It follows from the composite of Bar-Cohen and Rohsenow (1984), Nu_b = [(24 / Ra_b)^2 + (0.59 Ra_b^(1/4))^(-2)]^(-1/2), divided by the
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
             (Bar-Cohen and Rohsenow 1984, research/fin-channel). Of the 667 cases of the 1080-case study grid whose channel costs 10 % or more of the
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
    if not problem.vias:
        return out
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
                                "its effect can be too large by 12 to 15 % at a 1 mm cell; use a finer cell or read the result near it with care.")
        if len(edge) > 5:
            _add(out, None, None, f"{len(edge) - 5} more vias touch the board edge (see above).")
    if cell_mm >= VIA_COARSE_CELL_MM and any(m in ("fvm", "fdm") for m in models):
        _add(out, None, None, f"The cell ({num(cell_mm, 3)} mm) is coarse for the vias: a via is a fraction of a cell, so the temperature drop they cause is uncertain "
                              "by about 3 to 4 % at 2 mm and by 5 to 50 % at 3 to 4 mm, depending on where each via falls in its cell (example board: 9 vias, "
                              "-3 % FVM and -4 % FDM at 2 mm, within 0.5 % at 0.5 mm). Use 1 mm or finer.")
    return out
