#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file variants.py
@brief Variants of the zoned Lumped applied on a COPY (monkeypatches of module functions and constants, inside a context manager; `pcbthermal/` is never edited).
@details `patched(**opts)` yields with the changes applied and restores everything on exit: `true_core` replaces the core mask (cells whose CENTRE lies within CORE_R d_nn of a
         via POSITION, not of the cell that contains the via, so the core does not depend on which side of a cell edge a via falls); `core_r`, `max_core`, `zone_cell` set the
         module constants; `ac_scale` multiplies the A-C link resistance (the potential sum of eq. 5.7).
"""

import contextlib

import numpy as np
from scipy import spatial

from pcbthermal import lumped


def _true_core_mask(net, cov, vias):
    """!
    @brief Core mask from the via positions: cells of the footprint whose centre is within CORE_R times the mean nearest-neighbour distance of a via of the group.
    @param net Network or namespace (nx, ny, dx, dy).
    @param cov Footprint coverage (ny, nx).
    @param vias ViaSet or view (x, y, d_nn, group).
    @return bool array (ny, nx) or None.
    """
    if vias is None or len(vias) < 2:
        return None
    foot = cov > 0
    xs = (np.arange(net.nx) + 0.5) * net.dx
    ys = (np.arange(net.ny) + 0.5) * net.dy
    core = np.zeros(foot.shape, bool)
    gx, gy = np.meshgrid(xs, ys)
    pts = np.column_stack([gx[foot], gy[foot]])
    idx_foot = np.flatnonzero(foot.ravel())
    for g in np.unique(vias.group):
        mem = np.flatnonzero(vias.group == g)
        # Members whose position is over the footprint (its box, then the cell it falls in)
        inside = []
        for i in mem:
            cj, ci = int(vias.x[i] // net.dx), int(vias.y[i] // net.dy)
            if 0 <= ci < net.ny and 0 <= cj < net.nx and foot[ci, cj]:
                inside.append(i)
        if len(inside) < 2:
            continue
        r = lumped.CORE_R * float(np.mean([vias.d_nn[i] for i in inside]))
        tree = spatial.cKDTree(np.column_stack([vias.x[inside], vias.y[inside]]))
        d, _ = tree.query(pts)
        core.ravel()[idx_foot[d <= r + 1e-12]] = True
    return core if core.any() else None


@contextlib.contextmanager
def patched(true_core=False, core_r=None, max_core=None, zone_cell=None, ac_scale=1.0):
    """!
    @brief Apply variants of the zoned Lumped for the duration of a with block.
    @param true_core True to use the position-based core mask.
    @param core_r New CORE_R, or None.
    @param max_core New MAX_CORE, or None.
    @param zone_cell New ZONE_CELL_MM in mm, or None.
    @param ac_scale Factor on the A-C link resistance.
    @return None (context manager).
    """
    saved = (lumped._core_mask, lumped.CORE_R, lumped.MAX_CORE, lumped.ZONE_CELL_MM, lumped._mutual_potentials)
    try:
        if true_core:
            lumped._core_mask = _true_core_mask
        if core_r is not None:
            lumped.CORE_R = core_r
        if max_core is not None:
            lumped.MAX_CORE = max_core
        if zone_cell is not None:
            lumped.ZONE_CELL_MM = zone_cell
        if ac_scale != 1.0:
            orig = saved[4]
            lumped._mutual_potentials = lambda *a, **k: ac_scale * orig(*a, **k)
        yield
    finally:
        lumped._core_mask, lumped.CORE_R, lumped.MAX_CORE, lumped.ZONE_CELL_MM, lumped._mutual_potentials = saved
