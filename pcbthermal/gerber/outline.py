#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file outline.py
@brief The board outline from the profile layer (Edge.Cuts) as closed polygons with holes, with a clear refusal when the contour is not closed.
@details The profile layer draws the outline as lines and arcs; the fabricator cuts along the centre line of the stroke, so the contour is the chain of the stroke
         segments (arcs are already cut into short segments by the parser, chord error below ARC_TOLERANCE), and the width of the aperture does not matter (a zero-width
         aperture is fine). The endpoints are joined when they are closer than a tolerance (default 0.01 mm); every joint must connect exactly two segments, otherwise the
         contour is open (a gap), branches or touches itself, and the reader raises an `OutlineError` that names the file, the joint coordinates and the gap, instead of guessing.
         A region (G36/G37) in the profile layer is taken as a closed contour of its own. Loops are nested by the even-odd rule: a loop inside a board is a cut-out, a loop inside
         a cut-out is another board (a panel). The polygons are returned counter-clockwise for the board and clockwise for the holes, in millimetres, in the Gerber axes.
         Not checked: two loops that cross each other without a shared joint.
"""

import math
from typing import List, NamedTuple

import numpy as np
from scipy.spatial import cKDTree

from .errors import OutlineError
from .parser import Layer


class OutlinePolygon(NamedTuple):
    """!@brief One board: the outer contour (counter-clockwise array (n, 2)) and its cut-outs (clockwise arrays), in mm."""
    outer: np.ndarray
    holes: List[np.ndarray]


class Outline(NamedTuple):
    """!@brief The profile of a board set: the boards (more than one for a panel), the bounding box and the area (mm2)."""
    polygons: List[OutlinePolygon]
    bbox: tuple
    area_mm2: float


def signed_area(poly):
    """!
    @brief Signed area of a polygon (positive when counter-clockwise).
    @param poly Array (n, 2) of vertices, the first not repeated at the end.
    @return float Area in mm2.
    """
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def point_in_polygon(px, py, poly):
    """!
    @brief Whether a point is inside a polygon (even-odd ray casting).
    @param px   X of the point (mm).
    @param py   Y of the point (mm).
    @param poly Array (n, 2) of vertices.
    @return bool True when inside.
    """
    x0, y0 = poly[:, 0], poly[:, 1]
    x1, y1 = np.roll(x0, -1), np.roll(y0, -1)
    cross = ((y0 <= py) != (y1 <= py)) & (px < x0 + (py - y0) * (x1 - x0) / np.where(y1 == y0, 1.0, y1 - y0))
    return bool(cross.sum() % 2)


def chain_segments(segments, tol_mm, name=""):
    """!
    @brief Chain line segments into closed loops.
    @param segments Array (m, 4) of (x0, y0, x1, y1) in mm.
    @param tol_mm   Endpoints closer than this (mm) are the same joint.
    @param name     File name, for the message.
    @return list of arrays (n, 2), one per closed loop (the first vertex is not repeated).
    @throws OutlineError If a joint does not connect exactly two segments.
    """
    # A segment not longer than the tolerance would put both of its ends in one joint, which would then count four ends and look like a branch (a CAD tool
    # that writes a spline as many tiny pieces, the last chord of a short arc): such segments are contracted, their two ends become one joint and they leave the chain
    short = np.hypot(segments[:, 2] - segments[:, 0], segments[:, 3] - segments[:, 1]) <= tol_mm
    tiny = segments[short]
    segments = segments[~short]
    if len(segments) == 0:
        return []
    m = len(segments)
    ends = np.vstack([segments[:, 0:2], segments[:, 2:4]])             # row k: start of segment k; row m + k: its end
    nt = len(tiny)
    # The ends of the contracted segments take part in the joints (rows 2m ...), so that a chain of tiny pieces joins the two long segments it connects
    allpts = np.vstack([ends, tiny[:, 0:2], tiny[:, 2:4]]) if nt else ends
    tree = cKDTree(allpts)
    parent = list(range(len(allpts)))

    def find(a):
        """!@brief Union-find root with path halving. @param a Node. @return Root."""
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for i, j in tree.query_pairs(tol_mm):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj
    for k in range(nt):                                                 # the two ends of a contracted segment are one joint
        ri, rj = find(2 * m + k), find(2 * m + nt + k)
        if ri != rj:
            parent[ri] = rj
    node = np.array([find(i) for i in range(2 * m)])
    degree = {}
    for n in node:
        degree[n] = degree.get(n, 0) + 1
    bad = [n for n, d in degree.items() if d != 2]
    if bad:
        pts = [(float(ends[np.nonzero(node == n)[0][0]][0]), float(ends[np.nonzero(node == n)[0][0]][1]), degree[n]) for n in bad[:3]]
        where = "; ".join(f"({x:.4f}, {y:.4f}) mm with {d} segment end(s)" for x, y, d in pts)
        ones = [n for n in bad if degree[n] == 1]
        gap = ""
        if len(ones) >= 2:
            p = np.array([ends[np.nonzero(node == n)[0][0]] for n in ones])
            d = cKDTree(p).query(p, k=2)[0][:, 1]
            gap = f"; the closest pair of loose ends is {float(d.min()):.4f} mm apart (tolerance {tol_mm} mm)"
        raise OutlineError(f"{name + ': ' if name else ''}the board outline is not a closed contour: {len(bad)} joint(s) do not connect exactly two segments, at {where}{gap}")
    at_node = {}
    for k in range(m):
        at_node.setdefault(node[k], []).append(k)
        at_node.setdefault(node[m + k], []).append(k)
    used = np.zeros(m, bool)
    loops = []
    for first in range(m):
        if used[first]:
            continue
        verts = []
        k, forward = first, True
        while True:
            used[k] = True
            start = segments[k, 0:2] if forward else segments[k, 2:4]
            verts.append(start)
            tail = node[m + k] if forward else node[k]
            nxt = [s for s in at_node[tail] if s != k]
            if not nxt:                                                    # a segment closing on itself (both ends one joint)
                break
            k = nxt[0]
            if used[k]:
                break
            forward = node[k] == tail
        loops.append(np.array(verts))
    return loops


def outline_from_layer(layer, tol_mm=0.01):
    """!
    @brief The closed polygons (boards and cut-outs) of a parsed profile layer.
    @param layer  Parsed Layer of the profile (Edge.Cuts).
    @param tol_mm Endpoints closer than this (mm) are joined.
    @return Outline (boards with their holes, bounding box, area).
    @throws OutlineError If the layer draws no contour or the contour is not closed.
    """
    segs, loops = [], []
    for kind, dark, a in layer.ops:
        if not dark:
            continue
        if kind == "stroke":
            if math.hypot(a[3] - a[1], a[4] - a[2]) > 1e-9:
                segs.append((a[1], a[2], a[3], a[4]))
        elif kind == "region" and len(a) >= 3:
            loops.append(np.array(a, float))
    if segs:
        loops += chain_segments(np.array(segs, float), tol_mm, layer.name)
    loops = [p for p in loops if len(p) >= 3 and abs(signed_area(p)) > 1e-12]
    if not loops:
        raise OutlineError(f"{layer.name + ': ' if layer.name else ''}the profile layer draws no closed contour")
    # Nest by containment: parent = the smallest loop that contains the first vertex of this one
    areas = [abs(signed_area(p)) for p in loops]
    order = sorted(range(len(loops)), key=lambda i: -areas[i])
    parent = {}
    for pos, i in enumerate(order):
        cands = [j for j in order[:pos] if point_in_polygon(loops[i][0][0], loops[i][0][1], loops[j])]
        parent[i] = min(cands, key=lambda j: areas[j]) if cands else None
    depth = {}
    for i in order:
        depth[i] = 0 if parent[i] is None else depth[parent[i]] + 1
    polys = {}
    for i in order:
        if depth[i] % 2 == 0:
            p = loops[i] if signed_area(loops[i]) > 0 else loops[i][::-1]
            polys[i] = OutlinePolygon(p, [])
    for i in order:
        if depth[i] % 2 == 1:
            p = loops[i] if signed_area(loops[i]) < 0 else loops[i][::-1]
            polys[parent[i]].holes.append(p)
    result = [polys[i] for i in order if i in polys]
    allpts = np.vstack([p.outer for p in result])
    area = sum(abs(signed_area(p.outer)) - sum(abs(signed_area(h)) for h in p.holes) for p in result)
    return Outline(result, (float(allpts[:, 0].min()), float(allpts[:, 1].min()), float(allpts[:, 0].max()), float(allpts[:, 1].max())), float(area))


def read_outline(text, name="", tol_mm=0.01):
    """!
    @brief Parse a profile layer and return its outline.
    @param text   Gerber content of the profile layer.
    @param name   File name, for the messages.
    @param tol_mm Endpoints closer than this (mm) are joined.
    @return Outline.
    @throws OutlineError If the contour is not closed.
    """
    return outline_from_layer(Layer(text, name), tol_mm)
