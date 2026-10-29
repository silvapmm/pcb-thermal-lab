"""!
@file zone_rules.py
@brief The rules that combine the zones of one copper layer into the copper fill of a cell, all in one function, so that they can be compared on the same boards.
@details Question answered: when zones of one layer overlap or meet inside a cell, what is the copper fill of the cell? Rules (names used in the README):
         - `max_cell`   : the larger of the zones' own shares of the cell, max_i(cov_i * fill_i). This is the rule of `develop` (fvm.py, fdm.py, solid3d.py, analytic.py, checks.py).
         - `max_point`  : the largest fill at every sub-sample point, then the mean over the cell (the prototype of the branch fix/zone-union, geometry.zone_fill).
         - `prob`       : probabilistic union of independent patterns at every sample point, 1 - prod(1 - fill_i).
         - `sum_clip`   : sum of the fills at every sample point, clipped to 1 (the patterns never coincide).
         - `priority`   : the zone later in the list wins at every sample point (a zone of higher priority knocks out the lower one, as in KiCad and Altium).
         - `additive`   : per cell, min(1, sum_i cov_i * fill_i) (the first idea; rejected in gerber-models 4.39: it double counts overlapping zones).
         The module is numpy-only and uses the program's `points_in_polygon` (even-odd rule). It is used in two ways: imported from research scripts, and copied into a variant of the program
         (lib/variant.py) as `pcbthermal/_zone_rules.py`, where `geometry.zone_fill` calls `combine` with the rule named in the environment variable ZONE_RULE.
         Written for this investigation; the `max_point` rule is a copy of the idea of the prototype on fix/zone-union (geometry.zone_fill), re-typed here with the other rules.
"""

import numpy as np

try:                                                    # inside the variant of the program (pcbthermal/_zone_rules.py)
    from .geometry import points_in_polygon
except ImportError:                                     # imported from a research script
    from pcbthermal.geometry import points_in_polygon

## Names of the rules, in the order of the tables.
RULES = ("max_cell", "max_point", "prob", "sum_clip", "priority", "additive")


def sample_mask(poly, nx, ny, dx, dy, samples):
    """!
    @brief Which sub-samples of the cells in the bounding box of a polygon lie inside it.
    @param poly Polygon vertices (n, 2) in metres.
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param samples Sub-samples per cell side (the lattice is samples x samples, centres of the sub-squares).
    @return None when the polygon touches no cell, else (i0, i1, j0, j1, mask) with mask of shape (ni, samples, nj, samples).
    """
    p = np.asarray(poly, dtype=float)
    # Index range of the cells touched by the bounding box, clipped to the board
    j0 = max(int(np.floor(p[:, 0].min() / dx)), 0)
    j1 = min(int(np.ceil(p[:, 0].max() / dx)), nx)
    i0 = max(int(np.floor(p[:, 1].min() / dy)), 0)
    i1 = min(int(np.ceil(p[:, 1].max() / dy)), ny)
    if j1 <= j0 or i1 <= i0:
        return None
    ni, nj = i1 - i0, j1 - j0
    sub = (np.arange(samples) + 0.5) / samples
    xs = (j0 + (np.arange(nj)[:, None] + sub[None, :])) * dx
    ys = (i0 + (np.arange(ni)[:, None] + sub[None, :])) * dy
    gx, gy = np.meshgrid(xs.reshape(-1), ys.reshape(-1))
    return i0, i1, j0, j1, points_in_polygon(gx, gy, p).reshape(ni, samples, nj, samples)


def combine(zones, layers, nx, ny, dx, dy, samples=4, rule="max_point"):
    """!
    @brief Copper fill of every layer from its zones under one of the rules.
    @param zones Iterable of zones with polygon (metres), layer (0-based) and fill (0 to 1); list order is the priority order for the rule `priority` (later wins).
    @param layers Number of board layers.
    @param nx Number of cells along x.
    @param ny Number of cells along y.
    @param dx Cell width in metres.
    @param dy Cell height in metres.
    @param samples Sub-samples per cell side.
    @param rule One of RULES.
    @return numpy.ndarray Fill of shape (layers, ny, nx), values in [0, 1].
    @throws ValueError For an unknown rule.
    """
    if rule not in RULES:
        raise ValueError(f"unknown zone rule {rule!r}")
    out = np.zeros((layers, ny, nx))
    for layer in range(layers):
        mine = [z for z in zones if z.layer == layer]
        if not mine:
            continue
        if rule in ("max_cell", "additive"):
            acc = np.zeros((ny, nx))
            for z in mine:
                got = sample_mask(z.polygon, nx, ny, dx, dy, samples)
                if got is None:
                    continue
                i0, i1, j0, j1, mask = got
                share = mask.mean(axis=(1, 3)) * z.fill                # the zone's own share of every cell
                window = acc[i0:i1, j0:j1]
                if rule == "max_cell":
                    np.maximum(window, share, out=window)
                else:
                    window += share
            out[layer] = np.minimum(acc, 1.0) if rule == "additive" else acc
            continue
        # Point-level rules: combine the fill of every sample point of the layer, then average over the cell
        fine = np.zeros((ny, samples, nx, samples))
        keep = np.ones((ny, samples, nx, samples))                     # running product of (1 - fill) for the rule prob
        for z in mine:
            got = sample_mask(z.polygon, nx, ny, dx, dy, samples)
            if got is None:
                continue
            i0, i1, j0, j1, mask = got
            f = mask * z.fill
            window = fine[i0:i1, :, j0:j1, :]
            if rule == "max_point":
                np.maximum(window, f, out=window)
            elif rule == "sum_clip":
                window += f
            elif rule == "priority":
                np.copyto(window, f, where=mask)                       # a later zone overrides wherever it has copper (even a hole of fill 0)
            elif rule == "prob":
                keep[i0:i1, :, j0:j1, :] *= (1.0 - f)
        if rule == "prob":
            fine = 1.0 - keep
        out[layer] = np.minimum(fine, 1.0).mean(axis=(1, 3))
    return out
