#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file gaps.py
@brief Distance of the heat sources of a problem to the board sides (the quantity of the warning rule).
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tree  # noqa: E402,F401


def _seg_dist(pts, a, b):
    """!
    @brief Distance of points to a segment.
    @param pts Array (n, 2).
    @param a Segment start (2,).
    @param b Segment end (2,).
    @return Array (n,).
    """
    ab = b - a
    t = np.clip(((pts - a) @ ab) / max(float(ab @ ab), 1e-30), 0.0, 1.0)
    return np.hypot(*(pts - (a + t[:, None] * ab)).T)


def gaps_mm(problem):
    """!
    @brief For every heater with power: (equivalent side, smallest gap to a board side, second gap to a side of the other direction) in mm.
    @details Rectangular board: the gaps from the bounding box of the polygon to the four sides (smallest per axis, then the two smallest overall: g1 <= g2). With an outline: the smallest distance
             of the polygon vertices to the outline segments, and the same for the outline segments not within 20 degrees of the nearest one (g2). The side is sqrt(area).
    @param problem Problem.
    @return List of (side, g1, g2) in mm.
    """
    b = problem.board
    out = []
    for h in problem.heaters:
        if h.power <= 0:
            continue
        poly = np.asarray(h.polygon, dtype=float)
        x0, y0 = poly.min(axis=0)
        x1, y1 = poly.max(axis=0)
        area = 0.5 * abs(np.dot(poly[:, 0], np.roll(poly[:, 1], -1)) - np.dot(poly[:, 1], np.roll(poly[:, 0], -1)))
        if b.has_outline():
            o = np.asarray(b.outline, dtype=float)
            segs = [(o[i], o[(i + 1) % len(o)]) for i in range(len(o))]
            ds = []
            for a, c in segs:
                d = float(_seg_dist(poly, a, c).min())
                ang = np.degrees(np.arctan2(c[1] - a[1], c[0] - a[0])) % 180.0
                ds.append((d, ang))
            ds.sort()
            g1, ang1 = ds[0]
            g2 = next((d for d, ang in ds if min(abs(ang - ang1), 180 - abs(ang - ang1)) > 20.0), g1)
        else:
            gx = sorted([x0, b.width - x1])
            gy = sorted([y0, b.height - y1])
            g1, g2 = sorted([gx[0], gy[0]])
        out.append((float(np.sqrt(area)) * 1e3, g1 * 1e3, g2 * 1e3))
    return out
