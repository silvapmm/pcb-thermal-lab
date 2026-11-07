#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cut_cell_boards.py
@brief The simple boards of the cut-cell tests (copy of research/cut-cell-links/lib/boards.py) and the references that do not need a cut cell: the board in its own frame, the axisymmetric disc, the small T.
@details `edge_board` moves or turns the outline of a square or strip board and leaves the part (and the vias) on the grid, so that only the cut of the edge changes
         and the read-out of the cell-centred peak is the same for every position. `frame_board` is the same continuum problem written in the frame of the board:
         a rectangle aligned with the grid (no outline, no cut cell) whose part (and vias) are turned and shifted by the inverse transformation. Solved at three
         fine cells it is the independent reference (`frame_reference`): nothing of it depends on the cut-cell scheme under test.
"""

import math

import numpy as np

from pcbthermal import Problem

SHAPES = {"square": (10.0, 10.0), "strip": (12.0, 4.0)}          # half width, half height in mm


def rot(x, y, ang, c):
    """!
    @brief Rotate a point about (c, c).
    @param x X in mm.
    @param y Y in mm.
    @param ang Angle in degrees.
    @param c Centre of rotation (both coordinates) in mm.
    @return (x, y) in mm.
    """
    a = math.radians(ang)
    dx, dy = x - c, y - c
    return c + dx * math.cos(a) - dy * math.sin(a), c + dx * math.sin(a) + dy * math.cos(a)


def edge_board(angle=0.0, sx=0.0, sy=0.0, h_side=200.0, shape="square", off=0.0, vias=False, pattern=False, box=30.0, pc=0.0, power=2.0, part=3.0):
    """!
    @brief A two-layer board whose outline is shifted by (sx, sy) and turned about its own centre while the part and the vias stay on the grid.
    @param angle Turn of the board in degrees.
    @param sx Shift of the outline in x in mm.
    @param sy Shift of the outline in y in mm.
    @param h_side Edge coefficient in W/m2K.
    @param shape "square" (20 mm) or "strip" (24 x 8 mm).
    @param off Offset of the part from the box centre along x in mm.
    @param vias True: a 3 x 3 array of 0.3 mm drills at 1 mm pitch centred on the part.
    @param pattern True: the top copper stops 1.2 mm inside the outline (laminate nodes in the cut cells), the bottom layer is full.
    @param box Side of the box in mm.
    @param pc Shift of the part and the vias on both axes in mm (half a coarse cell: the part sits on a cell centre).
    @param power Power in W.
    @param part Side of the square part in mm.
    @return Problem.
    """
    c = box / 2.0
    hw, hh = SHAPES[shape]

    def put(pts):
        return [list(np.array(rot(c + x, c + y, angle, c)) + np.array([sx, sy])) for x, y in pts]

    p = Problem.new(box, box, 2, h_side=h_side)
    if pattern:
        p.add_zone(1, polygon=put([(-hw + 1.2, -hh + 1.2), (hw - 1.2, -hh + 1.2), (hw - 1.2, hh - 1.2), (-hw + 1.2, hh - 1.2)]), fill=1.0)
        p.add_zone(2, polygon=put([(-hw - 1, -hh - 1), (hw + 1, -hh - 1), (hw + 1, hh + 1), (-hw - 1, hh + 1)]), fill=1.0)
    else:
        p.add_full_copper()
    h = part / 2.0
    p.add_heater(1, power, rect=(c + pc + off - h, c + pc - h, c + pc + off + h, c + pc + h), name="U")
    if vias:
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                p.add_via(float(c + pc + off + i), float(c + pc + j), diameter=0.3)
    p.set_outline(put([(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]))
    return p


def frame_board(angle=0.0, sx=0.0, sy=0.0, h_side=200.0, shape="square", off=0.0, vias=False, pattern=False, box=30.0, pc=0.0, power=2.0, part=3.0):
    """!
    @brief The board of `edge_board` written in its own frame: an aligned rectangle with the part (and vias) turned by the opposite angle.
    @param angle Turn of the board in degrees (as `edge_board`).
    @param sx Shift of the outline in x in mm (as `edge_board`).
    @param sy Shift of the outline in y in mm.
    @param h_side Edge coefficient in W/m2K.
    @param shape "square" or "strip".
    @param off Offset of the part from the box centre along x in mm.
    @param vias True: the 3 x 3 via array, turned with the part.
    @param pattern True: the top copper stops 1.2 mm inside the rectangle.
    @param box Side of the box of `edge_board` in mm (only the position of the part relative to the box centre enters).
    @param pc Shift of the part in mm.
    @param power Power in W.
    @param part Side of the part in mm.
    @return Problem: a rectangle of the size of the shape, no outline.
    """
    hw, hh = SHAPES[shape]
    a = math.radians(-angle)
    ca, sa = math.cos(a), math.sin(a)

    def to_frame(dx, dy):
        # A point at (dx, dy) from the box centre, relative to the board centre, turned into the board frame
        vx, vy = dx - sx, dy - sy
        return hw + vx * ca - vy * sa, hh + vx * sa + vy * ca

    p = Problem.new(2 * hw, 2 * hh, 2, h_side=h_side)
    if pattern:
        p.add_zone(1, polygon=[[1.2, 1.2], [2 * hw - 1.2, 1.2], [2 * hw - 1.2, 2 * hh - 1.2], [1.2, 2 * hh - 1.2]], fill=1.0)
        p.add_zone(2, polygon=[[0, 0], [2 * hw, 0], [2 * hw, 2 * hh], [0, 2 * hh]], fill=1.0)
    else:
        p.add_full_copper()
    cx, cy = to_frame(pc + off, pc)
    h = part / 2.0
    pts = [[cx + x * ca - y * sa, cy + x * sa + y * ca] for x, y in ((-h, -h), (h, -h), (h, h), (-h, h))]
    p.add_heater(1, power, polygon=pts, name="U")
    if vias:
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                vx, vy = to_frame(pc + off + i, pc + j)
                p.add_via(float(vx), float(vy), diameter=0.3)
    return p


def frame_reference(solve, kw, cells=(0.125, 0.0625, 0.03125)):
    """!
    @brief Continuum value of the peak of a board from its frame problem: the program's FVM at three fine cells and an extrapolation.
    @details The order is read from the three values when the ratio of the two differences is between 1.5 and 6 (order 0.6 to 2.6); otherwise first order is assumed
             (the film on the node of the aligned edge is first order).
    @param solve Function (problem, cell_mm) -> hottest temperature.
    @param kw Options of `frame_board`.
    @param cells Three fine cells in mm, each half of the previous one.
    @return (reference, uncertainty): the extrapolated value and the size of the last correction (K).
    """
    t1, t2, t3 = (solve(frame_board(**kw), c) for c in cells)
    d12, d23 = t2 - t1, t3 - t2
    r = d12 / d23 if abs(d23) > 1e-12 else float("inf")
    if 1.5 <= r <= 6.0:
        ref = t3 + d23 / (r - 1.0)
    else:
        ref = t3 + d23            # first order (r = 2)
    return ref, abs(ref - t3)


def small_t(a_mm, h_side=10.0):
    """!
    @brief The small T board (30 x 24 mm, 2 W part over the re-entrant corner) with the neck edges at x = a and 30 - a.
    @param a_mm Position of the left neck edge in mm.
    @param h_side Edge coefficient in W/m2K.
    @return Problem.
    """
    b = 30.0 - a_mm
    p = Problem.new(30.0, 24.0, 2, h_side=h_side).add_full_copper()
    p.add_heater(1, 2.0, rect=(9, 10, 12, 14), name="U")
    p.set_outline([[0, 12], [a_mm, 12], [a_mm, 0], [b, 0], [b, 12], [30, 12], [30, 24], [0, 24]])
    return p


def disc_board(diameter_mm, part_radius_mm, h_side, power=2.0, n_sides=128, with_vias=False):
    """!
    @brief A round full-copper two-layer board with a round part at its centre (axisymmetric: the continuum problem has an (r, z) reference).
    @param diameter_mm Diameter in mm.
    @param part_radius_mm Radius of the part in mm.
    @param h_side Edge coefficient in W/m2K.
    @param power Power in W.
    @param n_sides Sides of the polygons that stand for the circles (equal area).
    @param with_vias Unused (kept False).
    @return Problem.
    """
    box = diameter_mm + 2.0
    c = box / 2.0

    def ring(r):
        # Equal-area regular polygon: the polygon area equals the circle area
        rr = r * math.sqrt(2.0 * math.pi / (n_sides * math.sin(2.0 * math.pi / n_sides)))
        return [[c + rr * math.cos(2 * math.pi * k / n_sides), c + rr * math.sin(2 * math.pi * k / n_sides)] for k in range(n_sides)]

    p = Problem.new(box, box, 2, h_side=h_side).add_full_copper()
    p.add_heater(1, power, polygon=ring(part_radius_mm), name="U")
    p.set_outline(ring(diameter_mm / 2.0))
    return p
