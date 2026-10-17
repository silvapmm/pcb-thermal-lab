"""!
@file checks.py
@brief Model-validity checks: warnings about inputs that make a result physically doubtful.

@details These checks never stop a simulation. They catch situations in which the solvers would silently do
something the user probably did not intend, for example moving the power of a heater that sticks out of the
board onto the part that is inside, or placing a heater where there is no copper to spread the heat. The text
of every warning says what is wrong and what to do.
"""

import numpy as np

from .geometry import coverage_fraction, polygon_area


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

    # --- Copper fill of every layer (union of its zones), used by several checks
    fill = np.zeros((b.layers, ny, nx))
    for z in problem.zones:
        fill[z.layer] = np.maximum(fill[z.layer], coverage_fraction(z.polygon, nx, ny, dx, dy, 4) * z.fill)

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
        inside = float(cov.sum() * dx * dy) / area
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
        if s.contact_r < 1e-5:
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
