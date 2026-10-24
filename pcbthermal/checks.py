"""!
@file checks.py
@brief Model-validity checks: warnings about inputs that make a result physically doubtful.

@details These checks never stop a simulation. They catch situations in which the solvers would silently do
something the user probably did not intend, for example moving the power of a heater that sticks out of the
board onto the part that is inside, or placing a heater where there is no copper to spread the heat. The text
of every warning says what is wrong and what to do.
"""

import numpy as np

from .geometry import coverage_fraction, points_in_polygon, polygon_area, polygon_centroid

# A plate under a source is called thick when the through-thickness drop q'' t / (2 k) exceeds this fraction of the heater's rise
THICK_PLATE_LIMIT = 0.05


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
    fill = np.zeros((b.layers, ny, nx))
    for z in problem.zones:
        fill[z.layer] = np.maximum(fill[z.layer], coverage_fraction(z.polygon, nx, ny, dx, dy, 4) * z.fill)

    for k, s in enumerate(problem.heatsinks):
        if s.has_fins() and b.air_speed == 0 and s.fin_pitch - s.fin_thickness < 4e-3:
            out.append(f"{s.name or f'Heatsink {k + 1}'}: the air gap between the fins is {1000 * (s.fin_pitch - s.fin_thickness):.1f} mm; in still air fins closer than about "
                       "4 to 6 mm choke the natural convection and the model (which does not slow the air between the fins) overestimates the cooling: use a larger pitch or the datasheet theta_SA.")

    heater_cov = []
    for k, h in enumerate(problem.heaters):
        name = h.name or f"Heater {k + 1}"
        area = polygon_area(h.polygon)
        if area <= 0:
            out.append(f"{name}: the footprint has zero area.")
            heater_cov.append(None)
            continue
        cov = coverage_fraction(h.polygon, nx, ny, dx, dy, 4)
        heater_cov.append(cov)
        inside = float((cov * board_cover).sum() * dx * dy) / area
        if inside < 0.98:
            out.append(f"{name}: {100 * (1 - inside):.0f} % of the footprint is outside the board; its full power "
                       "is applied to the part that is inside.")
        n_across = min(np.ptp(h.polygon[:, 0]), np.ptp(h.polygon[:, 1])) / min(dx, dy)
        if n_across < 3:
            out.append(f"{name}: the smallest side is only {n_across:.1f} cells wide; use a cell size of "
                       f"{min(np.ptp(h.polygon[:, 0]), np.ptp(h.polygon[:, 1])) * 1000 / 4:.2f} mm or less.")
        if cov.sum() > 0:
            f_mean = float((fill[h.layer] * cov).sum() / cov.sum())
            if f_mean < 0.02:
                out.append(f"{name}: there is no copper under it on layer {h.layer + 1}; the heat can only spread "
                           "through the FR-4 and the part will run very hot.")
            elif f_mean < 0.98:
                out.append(f"{name}: a copper edge or hatching crosses its footprint (copper fill {f_mean:.2f}); the "
                           "Lumped and Analytic models are unreliable here, use the FVM.")

    for i in range(len(problem.heaters)):
        for j in range(i + 1, len(problem.heaters)):
            hi, hj = problem.heaters[i], problem.heaters[j]
            if hi.layer == hj.layer and heater_cov[i] is not None and heater_cov[j] is not None:
                overlap = float((np.minimum(heater_cov[i], heater_cov[j])).sum() * dx * dy)
                small = min(polygon_area(hi.polygon), polygon_area(hj.polygon))
                if overlap > 0.05 * small:
                    out.append(f"{hi.name or f'Heater {i + 1}'} and {hj.name or f'Heater {j + 1}'} overlap on layer "
                               f"{hi.layer + 1}: their power densities add up.")

    for k, v in enumerate(problem.vias):
        if not (0.0 <= v.x <= W and 0.0 <= v.y <= H):
            out.append(f"{v.name or f'Via {k + 1}'} is outside the board and is ignored by the solvers.")

    for k, z in enumerate(problem.zones):
        cov = coverage_fraction(z.polygon, nx, ny, dx, dy, 2)
        area = polygon_area(z.polygon)
        if area > 0 and float(cov.sum() * dx * dy) / area < 0.5:
            out.append(f"{z.name or f'Zone {k + 1}'}: more than half of the zone is outside the board.")

    # --- Metal blocks: they only take heat where they overlap copper of their face
    block_cov = {}
    for k, s in enumerate(problem.heatsinks):
        if not s.is_block():
            continue
        name = s.name or f"Heatsink {k + 1}"
        cov = coverage_fraction(s.polygon, nx, ny, dx, dy, 4)
        area = polygon_area(s.polygon)
        if area > 0 and float(cov.sum() * dx * dy) / area < 0.9:
            out.append(f"{name}: part of the metal block is outside the board; only the part inside is modelled.")
        if cov.sum() > 0:
            overlap = float((fill[s.layer] * cov).sum() * dx * dy)
            if overlap < 1e-6:
                out.append(f"{name}: the metal block does not overlap any copper on its face, so it takes almost no heat "
                           "(through the bare laminate only); add a copper pad under it.")
            elif overlap < 0.25 * area:
                out.append(f"{name}: only {100 * overlap / area:.0f} % of the metal block touches copper; the heat enters "
                           "the block through that overlap only.")
        if s.interface_resistance() < 1e-5:
            out.append(f"{name}: an interface resistance below 1e-5 m2K/W is a perfect contact; a gap pad or paste is "
                       "usually 1e-4 to 1e-3 m2K/W (0.5 mm of a 1 to 5 W/mK pad).")
        face = 0 if (s.layer == 0 or b.layers == 1) else 1
        block_cov.setdefault(face, []).append((name, cov))
    for face, items in block_cov.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                if float(np.minimum(items[i][1], items[j][1]).sum() * dx * dy) > 1e-7:
                    out.append(f"{items[i][0]} and {items[j][0]} overlap: in the overlap only the later one is used.")

    if problem.total_power() <= 0:
        out.append("The total heater power is zero: the board stays at ambient temperature.")
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
                out.append(f"{row['name'] or 'Heater'}: {what} ({1000 * t:.3g} mm, {k:g} W/mK) is thick and poorly conducting for the heat flux under the part: the surface "
                           f"under the source can be hotter than the model shows by up to {drop:.1f} K ({100 * drop / rise:.0f} % of its rise of {rise:.1f} K){note}; the models "
                           "keep one temperature through the thickness. The value is a bound, not added to the results.")
    return out
