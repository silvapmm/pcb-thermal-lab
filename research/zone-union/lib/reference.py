"""!
@file reference.py
@brief The independent reference of the zone-union investigation: the resolved copper of a board (binary polygons on a fine grid) solved by the independent 3D conduction solver.
@details Question answered: what temperature does the board reach when its copper is the geometric union of the polygons, resolved far finer than the cell of the models?
         The copper of every layer is rasterised on a grid of `dx_mm` cells (area fraction of every fine cell by a 4 x 4 lattice, point-in-polygon by matplotlib's Path, not by the program),
         the conductivity of the copper slab of a cell is k_lam + f (k_cu - k_lam), and tests/helpers/layered3d.py (imports nothing of the program) gives the steady rise with the same
         boundary conditions as the program (film on both faces, also under the part, adiabatic edges). Laminate isotropic (k_lam), as in tests/test_layered_vs_3d.py.
         Written for this investigation. The solver is checked against a closed form in tests/test_reference.py.
"""

import numpy as np
from matplotlib.path import Path as MplPath

import layered3d as L3


def raster(polys, nx, ny, dx, samples=4):
    """!
    @brief Area fraction of every cell covered by the union of binary polygons (no density: a polygon is copper or not).
    @param polys List of polygons (n, 2) in metres.
    @param nx Cells along x.
    @param ny Cells along y.
    @param dx Cell size in metres (square cells).
    @param samples Sub-samples per cell side.
    @return numpy.ndarray (ny, nx) of fractions in [0, 1].
    """
    sub = (np.arange(samples) + 0.5) / samples
    xs = ((np.arange(nx)[:, None] + sub[None, :]) * dx).reshape(-1)
    ys = ((np.arange(ny)[:, None] + sub[None, :]) * dx).reshape(-1)
    gx, gy = np.meshgrid(xs, ys)
    pts = np.column_stack([gx.ravel(), gy.ravel()])
    inside = np.zeros(len(pts), dtype=bool)
    for p in polys:
        p = np.asarray(p, dtype=float)
        # Bounding box first: a small polygon touches few of the points
        sel = (pts[:, 0] >= p[:, 0].min()) & (pts[:, 0] <= p[:, 0].max()) & (pts[:, 1] >= p[:, 1].min()) & (pts[:, 1] <= p[:, 1].max())
        if sel.any():
            inside[sel] |= MplPath(p).contains_points(pts[sel])
    m = inside.reshape(ny * samples, nx * samples)
    return m.reshape(ny, samples, nx, samples).mean(axis=(1, 3))


def reference_rise(problem, polys_by_layer, dx_mm, k_lam=0.3, n_gap=4, samples=4):
    """!
    @brief Steady rise of the heater of a problem with resolved copper, in the independent solver.
    @param problem Problem (board data and one rectangular heater; its zones are NOT used).
    @param polys_by_layer Dict layer (0-based) -> list of polygons (n, 2) in metres: the copper that exists (solid).
    @param dx_mm Fine cell size in mm; the board size and the heater edges must be multiples of it.
    @param k_lam Isotropic conductivity of the laminate (W/mK).
    @param n_gap Sub-slabs per dielectric gap.
    @param samples Sub-samples per fine cell side for the area fraction.
    @return dict with max (hottest heater cell, K above ambient), mean (mean over the heater cells) and fill (the fine fill maps per layer).
    @throws ValueError If the board does not fit the fine grid.
    """
    b = problem.board
    dx = dx_mm * 1e-3
    nx, ny = int(round(b.width / dx)), int(round(b.height / dx))
    if abs(nx * dx - b.width) > 1e-9 or abs(ny * dx - b.height) > 1e-9:
        raise ValueError("the board is not a multiple of the fine cell")
    k_cu = b.materials.k_copper
    Lc = b.layers
    maps = {}
    slabs = []
    for k in range(Lc):
        f = raster(polys_by_layer.get(k, []), nx, ny, dx, samples)
        maps[k] = f
        slabs.append((b.copper_thickness[k], k_lam + f * (k_cu - k_lam), 1))
        if k < Lc - 1:
            slabs.append(((b.thickness - sum(b.copper_thickness)) / (Lc - 1), k_lam, n_gap))
    if Lc == 1:
        slabs.append((b.thickness - b.copper_thickness[0], k_lam, 8))
    h = problem.heaters[0]
    x0, y0 = h.polygon.min(axis=0)
    x1, y1 = h.polygon.max(axis=0)
    res = L3.solve(dx, nx, ny, slabs, (x0, y0, x1, y1), h.power, b.h_top, b.h_bottom, film_under_source=True)
    return {"max": res["cell_max_source"], "mean": res["cell_mean_source"], "fill": maps}
