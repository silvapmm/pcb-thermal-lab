#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file edge_reference.py
@brief The resolved reference of a via next to an insulated or weakly cooled board edge: the layered model of the program written again on a fine grid (`sheets2d`, which imports nothing
       of the program) with the barrel drawn at its real size, plus the board and via builders of study S1.
@details Reference = the same layered idealisation as the program (sheets, vertical conductances, films) solved at 1/16 mm (and 1/32 mm for a check), the barrel conductance of
         every gap spread over the cells of the true disc by area (it converges to the continuum as the cell shrinks, `point-via-convergence` 3.1/4.1). The numbers it takes from the
         program are only the layer parameters (`program_cases.layer_parameters`). Edge cooling (`Board.h_side`) is added per layer like the program (`h_side * slab * edge length`);
         a cut at `x_cut` removes the cells beyond it (S = 0, pinned) like an outline, with the cooling of the new edge. Independent check of the idealisation itself (layered model
         against the 3D barrel): `point-via-convergence` 3.2, not repeated here.
         Boards (all four copper planes of FR-4 0.3 W/mK, 35 um, h 10 / 200 W/m2K, a 0.5 W source of 3 x 2 mm on the top layer):
         * `edge_board`  a 10 x 10 mm board, the source at (1..4, 4..6) mm, one via of 0.3 mm copper-filled at a given distance from the right edge (x = 10 mm or the outline at x_cut);
         * `corner_board` the same with the via near the corner (x = 10 mm, y = 10 mm).
"""

import copy
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
POINT_LIB = os.path.join(os.path.dirname(os.path.dirname(HERE)), "point-via-convergence", "lib")
sys.path.insert(0, POINT_LIB)

import program_cases as pc                                                  # noqa: E402
import resolved_boards as rb                                                # noqa: E402
import sheets2d                                                             # noqa: E402
from pcbthermal import Problem                                              # noqa: E402
from pcbthermal.model import Materials                                      # noqa: E402

W_MM = 10.0                                                                 # side of the test board in mm


def edge_board(distance_mm=0.16, with_via=True, x_cut_mm=None, h_side=None, diameter_mm=0.3, fill_k=385.0, corner=False, power=0.5):
    """!
    @brief The test board of study S1.
    @param distance_mm Distance of the via centre from the edge (the right edge, or the outline at x_cut) in mm.
    @param with_via False: the board without the via.
    @param x_cut_mm None: the right edge is the box edge (x = 10 mm); a number: an outline that cuts the box at that x (cells beyond are off the board).
    @param h_side Edge film coefficient in W/m2K (None: insulated edges).
    @param diameter_mm Drill diameter in mm.
    @param fill_k Fill conductivity in W/mK (385: copper-filled).
    @param corner True: the via also sits `distance_mm` from the top edge (y = 10 mm).
    @param power Source power in W.
    @return Problem.
    """
    w = W_MM
    p = Problem.new(w, w, 4, 1.6, 35.0, h_top=10.0, h_bottom=200.0, h_side=h_side, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, 5):
        p.add_zone(layer, rect=(0, 0, w, w))
    edge = w
    if x_cut_mm is not None:
        p.set_outline([(0, 0), (x_cut_mm, 0), (x_cut_mm, w), (0, w)])
        edge = x_cut_mm
    p.add_heater(1, power, rect=(1, 4, 4, 6))
    if with_via:
        p.add_via(edge - distance_mm, (w - distance_mm) if corner else 5.0, diameter_mm, fill_k=fill_k)
    return p


def reference_rise(problem, dx_mm=1.0 / 16.0, with_via=True, x_cut_mm=None):
    """!
    @brief Maximum top-layer rise of the resolved layered model of a square board.
    @param problem A Problem built by `edge_board` (with its via; the layer parameters are read from it).
    @param dx_mm Fine cell in mm (must divide the board side, the source edges and x_cut).
    @param with_via False: leave the barrel out (the board without the via).
    @param x_cut_mm The outline cut of the board (None: the box).
    @return float rise over the ambient in K.
    @throws ValueError If the board is not square or the cell does not divide the dimensions.
    """
    b = problem.board
    if abs(b.width - b.height) > 1e-12:
        raise ValueError("square boards only")
    par = pc.layer_parameters(problem)
    dx = dx_mm * 1e-3
    n = int(round(b.width / dx))
    if abs(n * dx - b.width) > 1e-9:
        raise ValueError("the fine cell must divide the board side")
    vias = [(x, y, k) for k, (x, y) in enumerate(par["xy"])] if with_via else []
    S, gz, g_amb = rb._arrays(par, n, dx, vias, par["r_via"][0] if par["r_via"] else 1e-4, 0.0, None)
    L = S.shape[0]
    slab = b.slab_thicknesses()
    if b.h_side:                                                              # the program's edge film: h_side * slab * edge length per layer
        for l in range(L):
            g = b.h_side * slab[l] * dx
            g_amb[l, :, 0] += g
            g_amb[l, :, -1] += g
            g_amb[l, 0, :] += g
            g_amb[l, -1, :] += g
    jc = n
    if x_cut_mm is not None:
        jc = int(round(x_cut_mm * 1e-3 / dx))
        if abs(jc * dx - x_cut_mm * 1e-3) > 1e-9:
            raise ValueError("the fine cell must divide x_cut")
        if b.h_side:                                                          # the new edge is cooled like the box edge (the cells beyond are removed below)
            for l in range(L):
                g_amb[l, :, jc - 1] += b.h_side * slab[l] * dx
        S[:, :, jc:] = 0.0
        gz[:, :, jc:] = 0.0
        g_amb[:, :, jc:] = 1.0                                                # removed cells pinned to the ambient with no source, like the program's g_pin
    h = problem.heaters[0]
    x0, y0 = h.polygon.min(axis=0)
    x1, y1 = h.polygon.max(axis=0)
    j0, j1, i0, i1 = (int(round(v / dx)) for v in (x0, x1, y0, y1))
    Q = np.zeros((L, n, n))
    Q[0, i0:i1, j0:j1] = h.power / ((i1 - i0) * (j1 - j0))
    T = sheets2d.solve(S, gz, g_amb, Q, dx)
    return float(T[0].max())


def via_effect_reference(problem_with_via, dx_mm=1.0 / 16.0, x_cut_mm=None):
    """!
    @brief E = T_max(no via) - T_max(via) of the resolved model.
    @param problem_with_via Problem with the via.
    @param dx_mm Fine cell in mm.
    @param x_cut_mm The outline cut, or None.
    @return float E in K.
    """
    return reference_rise(problem_with_via, dx_mm, False, x_cut_mm) - reference_rise(problem_with_via, dx_mm, True, x_cut_mm)


def deepcopy_without_via(problem):
    """!
    @brief A copy of a Problem with no vias.
    @param problem A Problem.
    @return Problem.
    """
    q = copy.deepcopy(problem)
    q.vias = []
    return q


__all__ = ["edge_board", "reference_rise", "via_effect_reference", "deepcopy_without_via", "W_MM", "math"]
