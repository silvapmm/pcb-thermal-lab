#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file program_cases.py
@brief The test boards of the studies built for the program (Problem objects) and the run helpers: gain of a copper fill against the cell, for any model and treatment.
@details Boards (all four copper planes unless stated, FR-4 0.3 W/mK, copper 35 um, drill diameter as given, plating 25 um):
         * `array_board`   the 21 x 21 mm board of research/via-fill (3 x 3 vias of 0.3 mm at 3.5 mm pitch under a 10 x 10 mm source, 2 W, h 10 / 200 W/m2K, insulated edges);
         * `unit_cell_board`  one via at the centre of a square p x p board that is heated everywhere on the top copper: the periodic unit cell of a via lattice (insulated edges);
         * `lone_via_board`  one via at the centre of a large board heated by a small source next to it (the lone via of Peaceman's well);
         * `example_board`  the 100 x 80 mm example of the program (9 vias under U1).
         `max_rise` runs one model of the program and returns the maximum rise over the ambient of the top layer.
"""

import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)                                                  # the program

from pcbthermal import Problem, SolverOptions, simulate                      # noqa: E402
from pcbthermal import model as pmodel                                       # noqa: E402
from pcbthermal.examples import example_board                                # noqa: E402
from pcbthermal.model import Materials                                       # noqa: E402

K_CU = 385.0                                                                  # program's copper conductivity in W/mK


def array_board(fill_k=0.0, diameter_mm=0.3, pitch_mm=3.5, n=3):
    """!
    @brief The via-array board of research/via-fill.
    @param fill_k Fill conductivity in W/mK (0 = open barrel, 385 = copper fill).
    @param diameter_mm Via drill diameter in mm.
    @param pitch_mm Via pitch in mm.
    @param n Vias per side (odd).
    @return Problem.
    """
    w = 21.0
    c = w / 2
    p = Problem.new(w, w, 4, 1.6, 35.0, h_top=10.0, h_bottom=200.0, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, 5):
        p.add_zone(layer, rect=(0, 0, w, w))
    p.add_heater(1, 2.0, rect=(c - 5, c - 5, c + 5, c + 5))
    h = (n - 1) / 2
    for i in range(n):
        for j in range(n):
            p.add_via(c + (i - h) * pitch_mm, c + (j - h) * pitch_mm, diameter_mm, fill_k=fill_k)
    return p


def unit_cell_board(pitch_mm, diameter_mm, fill_k=0.0, layers=2, thickness=1.6, offset=(0.0, 0.0), h_bottom=200.0):
    """!
    @brief Periodic unit cell of a square via lattice: a p x p board, full copper on every layer, a source over the whole top copper, insulated edges, one via at the centre.
    @param pitch_mm Via pitch (board side) in mm.
    @param diameter_mm Via drill diameter in mm.
    @param fill_k Fill conductivity in W/mK.
    @param layers Copper layers.
    @param thickness Board thickness in mm.
    @param offset Shift of the via from the centre in mm (to test the position inside a cell).
    @param h_bottom Bottom film coefficient in W/m2K.
    @return Problem.
    """
    p = Problem.new(pitch_mm, pitch_mm, layers, thickness, 35.0, h_top=0.0, h_bottom=h_bottom, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, pitch_mm, pitch_mm))
    p.add_heater(1, 1.0, rect=(0, 0, pitch_mm, pitch_mm))
    p.add_via(pitch_mm / 2 + offset[0], pitch_mm / 2 + offset[1], diameter_mm, fill_k=fill_k)
    return p


def lone_via_board(side_mm=30.0, diameter_mm=0.3, fill_k=0.0, layers=2, source_mm=3.0, distance_mm=3.0, h_bottom=200.0, h_top=10.0):
    """!
    @brief A large board with one via and a small source at a given distance (the via drains the source through the planes).
    @param side_mm Board side in mm.
    @param diameter_mm Via drill diameter in mm.
    @param fill_k Fill conductivity in W/mK.
    @param layers Copper layers.
    @param source_mm Side of the square source in mm.
    @param distance_mm Distance from the via to the source centre in mm.
    @param h_bottom Bottom film coefficient in W/m2K.
    @param h_top Top film coefficient in W/m2K.
    @return Problem.
    """
    c = side_mm / 2
    p = Problem.new(side_mm, side_mm, layers, 1.6, 35.0, h_top=h_top, h_bottom=h_bottom, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, side_mm, side_mm))
    p.add_heater(1, 1.0, rect=(c + distance_mm - source_mm / 2, c - source_mm / 2, c + distance_mm + source_mm / 2, c + source_mm / 2))
    p.add_via(c, c, diameter_mm, fill_k=fill_k)
    return p


def row_board(n=1, pitch_mm=1.5, diameter_mm=0.3, fill_k=0.0, side_mm=16.0, layers=2, source_mm=3.0, gap_mm=1.0, h_bottom=200.0, h_top=10.0, none=False):
    """!
    @brief A square board, full copper, a square source in the middle and a row of n vias to its right (n = 1 is the lone via).
    @param n Number of vias in the row (along x, at the height of the source centre).
    @param pitch_mm Pitch of the row in mm.
    @param diameter_mm Via drill diameter in mm.
    @param fill_k Fill conductivity in W/mK.
    @param side_mm Board side in mm.
    @param layers Copper layers.
    @param source_mm Side of the square source in mm.
    @param gap_mm Distance from the source edge to the first via centre in mm.
    @param h_bottom Bottom film in W/m2K.
    @param h_top Top film in W/m2K.
    @param none True: build the board without vias (the reference without vias).
    @return Problem.
    """
    c = side_mm / 2
    p = Problem.new(side_mm, side_mm, layers, 1.6, 35.0, h_top=h_top, h_bottom=h_bottom, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, side_mm, side_mm))
    p.add_heater(1, 0.5, rect=(c - source_mm / 2, c - source_mm / 2, c + source_mm / 2, c + source_mm / 2))
    if not none:
        for i in range(n):
            p.add_via(c + source_mm / 2 + gap_mm + i * pitch_mm, c, diameter_mm, fill_k=fill_k)
    return p


def max_rise(problem, model="fvm", cell_mm=1.0):
    """!
    @brief Maximum temperature rise over the ambient of one model of the program.
    @param problem The Problem.
    @param model Model key (fvm, fdm, solid3d, lumped, analytic).
    @param cell_mm Cell size in mm.
    @return float Maximum rise in K.
    """
    res = simulate(problem, SolverOptions(models=(model,), cell_mm=cell_mm)).results
    return float(res[model].t_max - problem.board.ambient)


def load_libraries():
    """!
    @brief Load the shipped libraries of the program (via fills and so on) so that the boards behave as in the application.
    @return None.
    """
    pmodel.reload_libraries()


def layer_parameters(problem):
    """!
    @brief Per-area parameters of the layered model of a uniform board (full copper on every layer, no heatsink), read from the program's own network of a copy without vias.
    @details Only numbers leave the program (sheet conductances, dielectric conductance per area, film coefficients, barrel conductances); the independent solvers of the
             studies take them as input and do not import the program.
    @param problem A Problem whose layers are full copper (uniform).
    @return dict with S (L,), gz_area (L-1,) in W/m2K, h_top, h_bottom, d (gaps), gv (list of (L-1,) arrays, one per via), r_via (list), xy (list) and the board size.
    """
    import copy
    from pcbthermal import fvm
    q = copy.deepcopy(problem)
    q.vias = []
    b = q.board
    nx, ny = int(round(b.width / 1e-3)), int(round(b.height / 1e-3))
    net = fvm.Network(q, nx, ny, assemble=False)
    cell = net.dx * net.dy
    d = b.gap_thicknesses()
    gv = [b.materials.k_copper * v.thermal_area(b.via_plating, b.materials.k_copper) / d for v in problem.vias]
    return {"S": net.S[:, ny // 2, nx // 2].copy(), "gz_area": net.gz[:, ny // 2, nx // 2] / cell, "h_top": float(net.g_top[0, ny // 2, nx // 2] / cell),
            "h_bottom": float(net.g_bottom[b.layers - 1, ny // 2, nx // 2] / cell), "d": d, "gv": gv, "r_via": [v.diameter / 2 for v in problem.vias],
            "xy": [(v.x, v.y) for v in problem.vias], "fill_k": [v.fill_k for v in problem.vias], "k_cu": b.materials.k_copper,
            "t_cu": float(b.copper_thickness[0]), "plating": b.via_plating, "k_gap": float(b.gap_properties()[0][0]), "width": b.width, "height": b.height, "layers": b.layers}


__all__ = ["array_board", "unit_cell_board", "lone_via_board", "row_board", "max_rise", "layer_parameters", "example_board", "load_libraries", "math"]
