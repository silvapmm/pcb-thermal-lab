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

import numpy as np

from . import blocks, convection
from .geometry import coverage_fraction, points_in_polygon, polygon_area, polygon_centroid, polygon_self_intersects, zone_fill
from .numfmt import num

# A plate under a source is called thick when the through-thickness drop q'' t / (2 k) exceeds this fraction of the heater's rise
THICK_PLATE_LIMIT = 0.05

# A fin channel is called close when its channel Rayleigh number is below this value: the channel then keeps less than 90 % of the coefficient of the
# isolated plate (phi(90) = 0.90, research/fin-channel)
FIN_CHANNEL_RA_LIMIT = 90.0


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
        inside = float((cov * board_cover).sum() * dx * dy) / area
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

    for k, v in enumerate(problem.vias):
        if not (0.0 <= v.x <= W and 0.0 <= v.y <= H):
            _add(out, "via", k, f"{v.name or f'Via {k + 1}'} is outside the board and is ignored by the solvers.")

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
            out.append(f"{s.name or f'Heatsink {j + 1}'}: the channel between the fins ({num(1000 * gap, 3)} mm wide, about {num(1000 * length, 3)} mm long, block {theta:.0f} K above "
                       f"the air) has a channel Rayleigh number of {ra:.0f}; the air between the fins cools {100 * (1 - phi):.0f} % less than a plate of the same height "
                       f"({phi:.2f} of its coefficient), and the model does not slow it. Use a larger pitch, shorter channels, or the datasheet theta_SA. "
                       "Valid for a vertical board; for a horizontal board the effect is not quantified.")
    return out
