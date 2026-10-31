#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file rotsq.py
@brief The test boards of the rotated-square investigation (a square board turned by an angle, a square part turned or not) and loaders of
       variants of the program's 3D solid made on a copy of its source in memory.
@details Nothing in `pcbthermal/` is edited: `variant_solid3d` reads the source of `pcbthermal/solid3d.py`, replaces one expression of the edge
         conductance (the replacement text and the reason are in `VARIANTS`), checks that the text was found exactly once and executes the result as
         a module of the package (`pcbthermal.solid3d_<variant>`), so that its relative imports work. The program on disk is never changed.
"""

import importlib
import math
import os
import sys
import types

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)                                                  # the patched module imports cutcell

from pcbthermal import Problem                                                # noqa: E402

# The single expression of solid3d.py that gives the edge conductance of a board cell on a non-rectangular outline
EDGE_LINE = 'vs[s][on] += 1.0 / (1.0 / (b.h_side * length * dz) + (0.25 * (dx + dy)) / (kx * length * dz))'

KX_LINE = 'slabs[-1]["kx"] = np.maximum(slabs[-1]["kx"] * bcov, K_FLOOR * 1e-3)'
COVER_LINE = '        bcov = b.cover(nx, ny, dx, dy)\n'
LINK_LINES = (
    '            k, dz = sl["kx"], sl["dz"]\n'
    '            g = np.minimum(dz[:, :-1], dz[:, 1:]) * dy * 2.0 * k[:, :-1] * k[:, 1:] / ((k[:, :-1] + k[:, 1:]) * dx)\n'
    '            link(idx[s][:, :-1], idx[s][:, 1:], g)\n'
    '            g = np.minimum(dz[:-1], dz[1:]) * dx * 2.0 * k[:-1] * k[1:] / ((k[:-1] + k[1:]) * dy)\n'
    '            link(idx[s][:-1], idx[s][1:], g)\n')

# the strip form of the edge term (physical conductivity, half the depth of the board strip behind the outline)
STRIP_EDGE = ('vs[s][on] += 1.0 / (1.0 / (b.h_side * length * dz) + (0.5 * np.minimum(self.cover[on] * dx * dy / length, max(dx, dy))) / '
              '({kx} * length * dz))')

# cut-cell links: the aperture of the face over the distance between the centroids of the two board parts, resistances in series
CUT_LINKS = (
    '            k, dz = sl["kx"], sl["dz"]\n'
    '            if _geo is not None and "bcov" in sl:\n'
    '                xc, yc = _geo["xc"], _geo["yc"]\n'
    '                xf = (np.arange(1, nx) * dx)[None, :]\n'
    '                r = np.maximum(xf - xc[:, :-1], 1e-3 * dx) / k[:, :-1] + np.maximum(xc[:, 1:] - xf, 1e-3 * dx) / k[:, 1:]\n'
    '                g = np.minimum(dz[:, :-1], dz[:, 1:]) * dy * _geo["ax"] / r\n'
    '                link(idx[s][:, :-1], idx[s][:, 1:], g)\n'
    '                yf = (np.arange(1, ny) * dy)[:, None]\n'
    '                r = np.maximum(yf - yc[:-1], 1e-3 * dy) / k[:-1] + np.maximum(yc[1:] - yf, 1e-3 * dy) / k[1:]\n'
    '                g = np.minimum(dz[:-1], dz[1:]) * dx * _geo["ay"] / r\n'
    '                link(idx[s][:-1], idx[s][1:], g)\n'
    '                continue\n'
    '            g = np.minimum(dz[:, :-1], dz[:, 1:]) * dy * 2.0 * k[:, :-1] * k[:, 1:] / ((k[:, :-1] + k[:, 1:]) * dx)\n'
    '            link(idx[s][:, :-1], idx[s][:, 1:], g)\n'
    '            g = np.minimum(dz[:-1], dz[1:]) * dx * 2.0 * k[:-1] * k[1:] / ((k[:-1] + k[1:]) * dy)\n'
    '            link(idx[s][:-1], idx[s][1:], g)\n')
CUT_COVER = ('        import cutcell as _cutcell\n'
             '        _geo = _cutcell.cut_geometry(b.outline, nx, ny, dx, dy) if b.has_outline() else None\n'
             '        bcov = np.where(_geo["cover"] >= 0.01, _geo["cover"], 0.0) if _geo is not None else b.cover(nx, ny, dx, dy)\n'
             '        if _geo is not None:\n'
             '            _geo["ax"] = _geo["ax"] * ((bcov[:, :-1] > 0) & (bcov[:, 1:] > 0))   # a cell taken as off the board has no link\n'
             '            _geo["ay"] = _geo["ay"] * ((bcov[:-1] > 0) & (bcov[1:] > 0))\n')

CUT_LINKS_FLOOR = CUT_LINKS.replace("1e-3 * dx", "0.25 * dx").replace("1e-3 * dy", "0.25 * dy")

# The footprint of a part. Frozen history (the program moved, 2.4.5): the 3D solid used to weight a cell by `cover(h.polygon, 4) * self.active`
# (4 x 4 samples, the part's cover of the whole cell); the review of this folder found the 4 x 4 lattice short on a turned part and the
# weight wrong where a part crosses the outline. Both are fixed in the program (`fix/board-cover-8x8` and `fix/part-across-outline`:
# `geometry.part_weights`, samples `geometry.BOARD_SAMPLES` = 8, scaled to the board cover of the cell), so the variants that patched that
# line ("program_src8", "program_part_on_board", the heater edit of "cutcell_src8") now ARE the program and carry no edit. The numbers
# in the README that were measured with the old line are the numbers of the program before 2.4.5 and are not reproduced by these names.
# For the 4 x 4 lattice itself the test builds the old sampling from `geometry.coverage_fraction`.

# name -> list of (old text, new text); an empty list is the program as it is
VARIANTS = {
    "program": [],
    # the half-cell resistance with the physical in-plane conductivity: `kx` of a board slab is multiplied by the cover of the cell, which the
    # edge term should not see (the distance to the edge is not made longer by a cell that is only partly on the board)
    "kx_physical": [(EDGE_LINE, 'vs[s][on] += 1.0 / (1.0 / (b.h_side * length * dz) + (0.25 * (dx + dy)) / ((kx / (sl["bcov"][on] if "bcov" in sl else 1.0)) * length * dz))')],
    # only the film h L dz, as the FVM does (no conduction through half a cell)
    "film_only": [(EDGE_LINE, 'vs[s][on] += b.h_side * length * dz')],
    # the half-cell distance is the half depth of the strip of board inside the cell, cover * dx * dy / length (a full edge cell: half a cell,
    # as the program has it; a cell cut across its middle by a slanted side: much less), with the physical conductivity
    "strip": [(EDGE_LINE, STRIP_EDGE.format(kx='(kx / (sl["bcov"][on] if "bcov" in sl else 1.0))'))],
    # cut cells: strip distance to the edge AND links through the face aperture between the centroids of the board parts (kx not scaled by cover)
    "cutcell": [(KX_LINE, 'slabs[-1]["kx"] = np.maximum(slabs[-1]["kx"], K_FLOOR * 1e-3)'),
                (COVER_LINE, CUT_COVER), (LINK_LINES, CUT_LINKS), (EDGE_LINE, STRIP_EDGE.format(kx="kx"))],
    # the same with a floor of a quarter of a cell on each half distance (the centroid of a thin sliver can sit almost on the face)
    "cutcell_floor": [(KX_LINE, 'slabs[-1]["kx"] = np.maximum(slabs[-1]["kx"], K_FLOOR * 1e-3)'),
                      (COVER_LINE, CUT_COVER), (LINK_LINES, CUT_LINKS_FLOOR), (EDGE_LINE, STRIP_EDGE.format(kx="kx"))],
    # (review) the power of a part crossing the outline over the board part of each cell only: the program weights a cell by the part's cover
    # times 1 (active), so a cut cell gets the power of its whole area and the board part of it 1 / cover of the power density
    # (2.4.5) the program now does this itself (geometry.part_weights): no edit
    "program_part_on_board": [],
    # (review) the program with the footprint of a part sampled on 8 x 8 points per cell, as the FVM does
    # (2.4.5) the program samples the footprint 8 x 8 itself: no edit
    "program_src8": [],
    # (review) the cut-cell copy with the same 8 x 8 footprint
    "cutcell_src8": [(KX_LINE, 'slabs[-1]["kx"] = np.maximum(slabs[-1]["kx"], K_FLOOR * 1e-3)'),
                     (COVER_LINE, CUT_COVER), (LINK_LINES, CUT_LINKS), (EDGE_LINE, STRIP_EDGE.format(kx="kx"))],
}

_CACHE = {}


def variant_solid3d(name):
    """!
    @brief A copy of the program's 3D solid module whose edge conductance is the variant `name`, built in memory from the source on disk.
    @param name Key of VARIANTS ("program" returns the module of the program itself).
    @return Module object with the same names as `pcbthermal.solid3d` (use `.solve` and `.Network`).
    @throws ValueError If the expression to replace is not found exactly once in the source (the program changed).
    """
    if name == "program":
        return importlib.import_module("pcbthermal.solid3d")
    if name in _CACHE:
        return _CACHE[name]
    path = os.path.join(ROOT, "pcbthermal", "solid3d.py")
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in VARIANTS[name]:
        if src.count(old) != 1:
            raise ValueError("an expression of solid3d.py was not found exactly once; the variants need updating: " + old[:60])
        src = src.replace(old, new)
    mod = types.ModuleType("pcbthermal.solid3d_" + name)
    mod.__package__ = "pcbthermal"
    mod.__file__ = path
    sys.modules[mod.__name__] = mod
    exec(compile(src, path + "#" + name, "exec"), mod.__dict__)
    _CACHE[name] = mod
    return mod


def fvm_part_on_board():
    """!
    @brief The FVM with the power of a part spread over the board part of each cell. Since 2.4.5 this is the program's own FVM
           (`geometry.part_weights`, fix/part-across-outline), so the former in-memory copy is gone and the program module is returned; the
           columns "FVM" and "FVM, power on the board part" of `study_part_across_outline.py` are now equal.
    @return Module object `pcbthermal.fvm` (use `.solve_steady`).
    """
    return importlib.import_module("pcbthermal.fvm")


def turned_square(side_mm, angle_deg, centre=(30.0, 30.0)):
    """!
    @brief Corners of a square turned about its centre.
    @param side_mm Side in mm.
    @param angle_deg Turn in degrees (counter-clockwise).
    @param centre Centre (x, y) in mm.
    @return List of four [x, y] in mm.
    """
    a = math.radians(angle_deg)
    h = side_mm / 2.0
    out = []
    for x, y in ((-h, -h), (h, -h), (h, h), (-h, h)):
        out.append([centre[0] + x * math.cos(a) - y * math.sin(a), centre[1] + x * math.sin(a) + y * math.cos(a)])
    return out


def board(angle_deg, h_side, side_mm=40.0, box_mm=60.0, part_mm=6.0, part_angle_deg=0.0, power=2.0, layers=2, copper="full", shift_mm=(0.0, 0.0), **opts):
    """!
    @brief A square board (full copper on both faces) turned inside a larger box, with a square part at its centre.
    @param angle_deg Turn of the board outline in degrees.
    @param h_side Edge coefficient in W/m2K.
    @param side_mm Side of the board in mm.
    @param box_mm Side of the box (the bounding box of the Problem) in mm.
    @param part_mm Side of the square part in mm.
    @param part_angle_deg Turn of the part in degrees (0 = aligned with the grid).
    @param power Power of the part in W.
    @param layers Copper layers.
    @param copper "full" (a plane on every layer) or "none" (bare laminate).
    @param shift_mm (dx, dy) shift of the board and the part together relative to the middle of the box, in mm (moves the edge against the grid).
    @param opts More Board options (for example h_top, h_bottom).
    @return Problem.
    """
    c = box_mm / 2.0
    cx, cy = c + shift_mm[0], c + shift_mm[1]
    p = Problem.new(box_mm, box_mm, layers, h_side=h_side, **opts)
    if copper == "full":
        p.add_full_copper()
    if part_angle_deg == 0.0:
        p.add_heater(1, power, rect=(cx - part_mm / 2, cy - part_mm / 2, cx + part_mm / 2, cy + part_mm / 2), name="U")
    else:
        p.add_heater(1, power, polygon=turned_square(part_mm, part_angle_deg, (cx, cy)), name="U")
    p.set_outline(turned_square(side_mm, angle_deg, (cx, cy)))
    return p


def edge_conductance_3d(net, h_side):
    """!
    @brief Total edge conductance of a built 3D network (sum of the side conductances over every cell and slab), in W/K.
    @param net solid3d.Network.
    @param h_side Edge coefficient (unused except to document the unit: the conductance already holds it).
    @return Float in W/K.
    """
    return float(net.g_side.sum())


def perimeter_mm(poly):
    """!
    @brief Perimeter of a closed polygon.
    @param poly Array-like (n, 2).
    @return Perimeter in the unit of the polygon.
    """
    o = np.asarray(poly, dtype=float)
    return float(np.sum(np.hypot(*(np.roll(o, -1, axis=0) - o).T)))


def equal_area_polygon(radius_mm, centre, n_sides):
    """!
    @brief A regular polygon with the area of a circle of the given radius (the program's outlines and parts are polygons).
    @param radius_mm Radius of the circle in mm.
    @param centre (x, y) in mm.
    @param n_sides Number of sides.
    @return List of [x, y] in mm.
    """
    rc = radius_mm * math.sqrt(2.0 * math.pi / (n_sides * math.sin(2.0 * math.pi / n_sides)))
    return [[centre[0] + rc * math.cos(2.0 * math.pi * k / n_sides), centre[1] + rc * math.sin(2.0 * math.pi * k / n_sides)] for k in range(n_sides)]


def disc_board(diameter_mm, part_radius_mm, h_side, box_mm=None, power=2.0, layers=2, n_sides=128, **opts):
    """!
    @brief A round full-copper board with a round part at its centre (axisymmetric: the continuum problem has an (r, z) reference).
    @param diameter_mm Diameter of the board in mm.
    @param part_radius_mm Radius of the part in mm.
    @param h_side Edge coefficient in W/m2K.
    @param box_mm Side of the box (default: the diameter plus 2 mm).
    @param power Power in W.
    @param layers Copper layers.
    @param n_sides Sides of the polygons that stand for the circles.
    @param opts More Board options.
    @return Problem.
    """
    box = box_mm or diameter_mm + 2.0
    c = box / 2.0
    p = Problem.new(box, box, layers, h_side=h_side, **opts).add_full_copper()
    p.add_heater(1, power, polygon=equal_area_polygon(part_radius_mm, (c, c), 64), name="U")
    p.set_outline(equal_area_polygon(diameter_mm / 2.0, (c, c), n_sides))
    return p
