#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cases.py
@brief Clean test boards where the copper of a plane covers only PART of the footprint of a via (copper edge, track end, pad island, antipad), and the run helpers.
@details All boards are 2-layer, 1.6 mm, 35 um copper, insulated edges, one 0.3 mm drill via (25 um plating, program default) unless stated, with a
         heater of 2 W on the top layer. The via sits at the centre of the board in the plan (`C` mm). The cases:
         * `edge`    the top copper ends through the via (x <= C + delta), the heater beside it; the bottom is a full plane. (The case of tests/test_maximum_principle.py,
                     on a smaller board.)
         * `track`   a 3 x 3 mm heater pad, a track of width w and length l to the via, no other top copper; the bottom is a full plane.
         * `island`  the heater sits on a square pad (side s) around the via, no other top copper; the bottom is a full plane.
         * `antipad` full planes on both layers, the bottom plane has a square clearance (side a) centred on the via (the via touches only the top plane).
         * `antipad_land` the same with a round (square here) land of side s_land at the bottom end of the via, isolated from the plane.
         * `bare`    a small heater on bare laminate over half the via footprint (copper ends at the via centre, heater outside the copper), the bottom is a full plane.
@note The functions import the program (`pcbthermal`) and change nothing in it.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import numpy as np                                                            # noqa: E402

from pcbthermal import Problem, fdm, fvm, solid3d                             # noqa: E402

C = 5.0                                                                       # via centre in mm (board 10 x 10 mm)
W = 10.0                                                                      # board side in mm


def _base(h=50.0):
    """!
    @brief Empty 10 x 10 mm two-layer board with insulated edges.
    @param h Heat transfer coefficient of both faces in W/m2K.
    @return Problem.
    """
    return Problem.new(W, W, 2, 1.6, 35.0, h_top=h, h_bottom=h, h_side=None)


def frame(p, layer, hole, cx=C, cy=C):
    """!
    @brief Copper plane of a layer with a square hole (four rectangles around it).
    @param p Problem.
    @param layer 1-based layer.
    @param hole Side of the square hole in mm.
    @param cx Hole centre x in mm.
    @param cy Hole centre y in mm.
    @return None.
    """
    a = hole / 2.0
    p.add_zone(layer, rect=(0, 0, W, cy - a))
    p.add_zone(layer, rect=(0, cy + a, W, W))
    p.add_zone(layer, rect=(0, cy - a, cx - a, cy + a))
    p.add_zone(layer, rect=(cx + a, cy - a, W, cy + a))


def edge(delta=0.0, power=0.5, d=0.3, h=50.0, with_via=True):
    """!
    @brief The top copper ends at x = C + delta; the heater (3 x 3 mm) beside the edge; full bottom plane.
    @param delta Edge position relative to the via centre in mm (0 = through the centre).
    @param power Heater power in W.
    @param d Drill diameter in mm.
    @param h Face coefficient in W/m2K.
    @param with_via False leaves the via out (the reference without a via).
    @return Problem.
    """
    p = _base(h)
    p.add_zone(2, rect=(0, 0, W, W))
    xe = C + delta
    p.add_zone(1, rect=(1, 1, xe, W - 1))
    p.add_heater(1, power, rect=(xe - 2.0, C - 1.0, xe, C + 1.0), name="Q")
    if with_via:
        p.add_via(C, C, d)
    return p


def track(width=0.4, length=2.0, power=0.5, d=0.3, h=50.0, with_via=True):
    """!
    @brief A heater pad, a thin track to the via, no other top copper; full bottom plane.
    @param width Track width in mm.
    @param length Track length in mm (from the pad edge to the via centre).
    @param power Heater power in W.
    @param d Drill diameter in mm.
    @param h Face coefficient in W/m2K.
    @param with_via False leaves the via out.
    @return Problem.
    """
    p = _base(h)
    p.add_zone(2, rect=(0, 0, W, W))
    x_pad = C - length
    p.add_zone(1, rect=(x_pad - 2.0, C - 1.0, x_pad, C + 1.0))                   # the pad
    p.add_zone(1, rect=(x_pad, C - width / 2, C, C + width / 2))                  # the track, ending at the via centre
    p.add_heater(1, power, rect=(x_pad - 2.0, C - 1.0, x_pad, C + 1.0), name="Q")
    if with_via:
        p.add_via(C, C, d)
    return p


def island(side=1.2, power=0.1, d=0.3, h=50.0, with_via=True):
    """!
    @brief A heater on a square copper pad around the via, no other top copper; full bottom plane.
    @param side Pad side in mm (also the heater side).
    @param power Heater power in W.
    @param d Drill diameter in mm.
    @param h Face coefficient in W/m2K.
    @param with_via False leaves the via out.
    @return Problem.
    """
    p = _base(h)
    p.add_zone(2, rect=(0, 0, W, W))
    a = side / 2
    p.add_zone(1, rect=(C - a, C - a, C + a, C + a))
    p.add_heater(1, power, rect=(C - a, C - a, C + a, C + a), name="Q")
    if with_via:
        p.add_via(C, C, d)
    return p


def antipad(hole=1.0, land=0.0, power=0.5, d=0.3, h=50.0, with_via=True):
    """!
    @brief Full top plane with the heater, bottom plane with a square clearance around the via (the via is not connected to the bottom plane).
    @param hole Side of the clearance in mm.
    @param land Side of an isolated square land at the bottom end of the via in mm (0 = none).
    @param power Heater power in W (3 x 3 mm heater beside the via, centre 2 mm away).
    @param d Drill diameter in mm.
    @param h Face coefficient in W/m2K.
    @param with_via False leaves the via out.
    @return Problem.
    """
    p = _base(h)
    p.add_zone(1, rect=(0, 0, W, W))
    frame(p, 2, hole)
    if land > 0:
        a = land / 2
        p.add_zone(2, rect=(C - a, C - a, C + a, C + a))
    p.add_heater(1, power, rect=(C - 3.0, C - 1.0, C - 1.0, C + 1.0), name="Q")
    if with_via:
        p.add_via(C, C, d)
    return p


def bare(power=0.1, d=0.3, h=50.0, with_via=True):
    """!
    @brief A small heater on bare laminate over the via; the top copper is a half plane ending at the via centre; full bottom plane.
    @param power Heater power in W.
    @param d Drill diameter in mm.
    @param h Face coefficient in W/m2K.
    @param with_via False leaves the via out.
    @return Problem.
    """
    p = _base(h)
    p.add_zone(2, rect=(0, 0, W, W))
    p.add_zone(1, rect=(0, 0, C, W))
    p.add_heater(1, power, rect=(C - 0.5, C - 0.5, C + 0.5, C + 0.5), name="Q")
    if with_via:
        p.add_via(C, C, d)
    return p


def array4(antipad_side=0.8, power=1.0, pitch=1.2, n=3, d=0.3, h=50.0, with_via=True):
    """!
    @brief A stand-in for a thermal-via array on a real board: four layers on a 12 x 12 mm board, a 6 x 6 mm top pad with a 4 x 4 mm heater, n x n vias, a GND plane on layer 2
           that the vias touch, a plane on layer 3 with a square antipad (clearance) around every via (the vias do NOT touch it) and a full plane on layer 4.
    @param antipad_side Side of the antipad squares on layer 3 in mm (0 = solid plane, every via touches it).
    @param power Heater power in W.
    @param pitch Via pitch in mm.
    @param n Vias per side.
    @param d Drill diameter in mm.
    @param h Face coefficient in W/m2K.
    @param with_via False leaves the vias out.
    @return Problem.
    """
    wb, c = 12.0, 6.0
    p = Problem.new(wb, wb, 4, 1.6, 35.0, h_top=h, h_bottom=h, h_side=None)
    p.add_zone(1, rect=(c - 3, c - 3, c + 3, c + 3))
    p.add_zone(2, rect=(0, 0, wb, wb))
    p.add_zone(4, rect=(0, 0, wb, wb))
    pts = [(c + (i - (n - 1) / 2) * pitch, c + (j - (n - 1) / 2) * pitch) for i in range(n) for j in range(n)]
    if antipad_side <= 0:
        p.add_zone(3, rect=(0, 0, wb, wb))
    else:
        # plane with square holes: horizontal bands between the rows of holes and the pieces between the holes of one row
        a = antipad_side / 2
        ys = sorted({y for _, y in pts})
        edges = [0.0]
        for y in ys:
            edges += [y - a, y + a]
        edges.append(wb)
        for k in range(0, len(edges), 2):
            y0, y1 = edges[k], edges[k + 1]
            if y1 - y0 > 1e-9:
                p.add_zone(3, rect=(0, y0, wb, y1))                                  # a band with no hole
        for y in ys:
            xs = sorted({x for x, yy in pts if abs(yy - y) < 1e-9})
            xe = [0.0]
            for x in xs:
                xe += [x - a, x + a]
            xe.append(wb)
            for k in range(0, len(xe), 2):
                if xe[k + 1] - xe[k] > 1e-9:
                    p.add_zone(3, rect=(xe[k], y - a, xe[k + 1], y + a))             # the copper between the holes of this row
    p.add_heater(1, power, rect=(c - 2, c - 2, c + 2, c + 2), name="Q")
    if with_via:
        for x, y in pts:
            p.add_via(x, y, d)
    return p


CASES = {"edge": edge, "track": track, "island": island, "antipad": antipad, "bare": bare, "array4": array4}


def network(problem, model, cell_mm):
    """!
    @brief Assemble the network of a layered model.
    @param problem Problem.
    @param model "fvm" or "fdm".
    @param cell_mm Cell size in mm.
    @return fvm.Network or fdm.Network.
    """
    if model == "fdm":
        return fdm.Network(problem, cell_mm)
    b = problem.board
    return fvm.Network(problem, max(int(round(b.width * 1000.0 / cell_mm)), 2), max(int(round(b.height * 1000.0 / cell_mm)), 2))


def local_cold_spot(problem, theta, grid):
    """!
    @brief Deepest cold spot around the via: on each plane, in a window of +-1.5 mm around the via, the window minimum minus the minimum on the window rim (negative = a cold spot).
    @param problem Problem.
    @param theta Rise array (planes, ny, nx) in K.
    @param grid "cell" (cell-centred) or "node" (node-centred) positions.
    @return float cold spot in K (<= 0 when there is one, 0 when the minimum is on the rim).
    """
    _, ny, nx = theta.shape
    b = problem.board
    if grid == "node":
        xs, ys = np.arange(nx) * b.width / (nx - 1), np.arange(ny) * b.height / (ny - 1)
    else:
        xs, ys = (np.arange(nx) + 0.5) * b.width / nx, (np.arange(ny) + 0.5) * b.height / ny
    m = 1.5e-3
    ix = np.abs(xs - C * 1e-3) <= m                        # the via position is fixed (C), also in the runs without a via
    iy = np.abs(ys - C * 1e-3) <= m
    worst = 0.0
    for plane in theta:
        w = plane[np.ix_(iy, ix)]
        rim = np.concatenate([w[0], w[-1], w[:, 0], w[:, -1]])
        worst = min(worst, float(w.min() - rim.min()))
    return worst


def run(problem, model, cell_mm):
    """!
    @brief Solve a problem with one model and return the numbers of the study.
    @param problem Problem.
    @param model "fvm", "fdm" or "solid3d".
    @param cell_mm Cell size in mm.
    @return dict: tmax (max rise over the ambient over the copper, K), tmin (min rise, K), cold (local cold spot, K), balance (heat out / heat in).
    """
    amb = problem.board.ambient
    if model == "solid3d":
        r = solid3d.solve_steady(problem, cell_mm)
        theta = r.T - amb
        return dict(tmax=float(theta.max()), tmin=float(theta.min()), cold=local_cold_spot(problem, theta, "cell"),
                    balance=sum(r.power_out.values()) / r.power_in)
    net = network(problem, model, cell_mm)
    theta, _ = net.solve_steady()
    keep = np.ones(theta.shape, dtype=bool) if net.drop is None else ~net.drop
    cu = theta[:problem.board.layers]
    return dict(tmax=float(cu.max()), tmin=float(theta[keep].min()), cold=local_cold_spot(problem, theta, "node" if model == "fdm" else "cell"),
                balance=float("nan"))
