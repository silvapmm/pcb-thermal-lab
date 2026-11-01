#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_edge_image.py
@brief Tests of the edge image and the footprint restrictions (`lib/edge_image.py`): pure geometry and lattice algebra, no solver.
"""

import math
import os
import sys

import numpy as np

LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
sys.path.insert(0, LIB)

import edge_image as ei                                                     # noqa: E402
import lattice                                                              # noqa: E402
import viakernel as vk                                                      # noqa: E402


def test_a_cont_equals_the_lattice_kernel_at_integer_offsets():
    """!@brief The interpolated kernel is the exact one on integer offsets and lies between its neighbours elsewhere."""
    for di, dj in ((0, 0), (1, 0), (2, 3), (-4, 1)):
        assert abs(float(ei.a_cont(di, dj)) - float(lattice.a_of(di, dj))) < 1e-12
    mid = float(ei.a_cont(1.5, 0.0))
    assert float(lattice.a_of(1, 0)) < mid < float(lattice.a_of(2, 0))


def test_single_cell_next_to_a_wall_has_the_lattice_image_distance():
    """!@brief A one-cell footprint on the cell next to a wall on its face: the image is one cell away, P_img = a(1, 0) = 1, D_lat = dx exp((pi/2)(1 - kappa))."""
    dx = 1e-3
    w = {(5, 0): 1.0}
    d_lat = math.exp(ei.log_image_distance(w, dx, 0.0, [("x", 0.0)]))
    assert abs(d_lat / dx - math.exp(math.pi / 2.0 * (1.0 - lattice.KAPPA))) < 1e-9


def test_correction_is_small_for_a_via_at_the_cell_centre_and_large_near_the_edge():
    """!@brief c = ln(D_lat / D_true): about zero when the via sits at the centre of the cell next to the wall, ln(D_lat / 0.32 mm) when it is 0.16 mm from it."""
    dx = 1e-3
    w = {(5, 0): 1.0}
    c_centre = ei.well_correction(w, (0.5e-3, 5.5e-3), 0.15e-3, dx, 0.0, [("x", 0.0)])
    c_near = ei.well_correction(w, (0.16e-3, 5.5e-3), 0.15e-3, dx, 0.0, [("x", 0.0)])
    assert abs(c_centre) < 0.1
    assert c_near > 1.0
    assert abs(c_near - (c_centre + math.log(1.0 / 0.32))) < 1e-9


def test_corner_adds_the_diagonal_image():
    """!@brief Two perpendicular walls give three image terms (two single, one diagonal); the single-wall terms are those of the one-wall case."""
    dx = 1e-3
    w = {(0, 0): 1.0}
    c1 = ei.well_correction(w, (0.3e-3, 0.3e-3), 0.15e-3, dx, 0.0, [("x", 0.0)])
    c2 = ei.well_correction(w, (0.3e-3, 0.3e-3), 0.15e-3, dx, 0.0, [("y", 0.0)])
    c12 = ei.well_correction(w, (0.3e-3, 0.3e-3), 0.15e-3, dx, 0.0, [("x", 0.0), ("y", 0.0)])
    assert abs(c1 - c2) < 1e-12                                              # symmetric corner
    # The diagonal image of a one-cell footprint is at the offset (1, 1) cells, where the kernel is 4/pi: ln D_lat = ln dx + (pi/2)(4/pi - kappa)
    diag = math.log(dx) + 2.0 - math.pi / 2.0 * lattice.KAPPA - math.log(2.0 * math.hypot(0.3e-3, 0.3e-3))
    assert abs((c12 - (c1 + c2)) - diag) < 1e-9


def test_no_walls_no_correction_and_infinite_when_the_denominator_is_not_positive():
    """!@brief c = 0 without walls; the well is infinite when ln(r_eff / r_t) + c <= 0 and equals the program's Peaceman well when c = 0."""
    assert ei.well_correction({(1, 1): 1.0}, (1e-3, 1e-3), 1e-4, 1e-3, 0.0, []) == 0.0
    assert math.isinf(ei.well_conductance_image(10.0, 2e-4, 2e-4, -0.1))
    assert abs(ei.well_conductance_image(10.0, 3e-4, 1.5e-4, 0.0) - vk.well_conductance(10.0, 3e-4, 1.5e-4)) < 1e-9


def test_restrict_to_board_drops_cells_off_the_board_and_weights_by_the_cover():
    """!@brief Cells off the grid or with cover 0 are dropped, partial cover scales the weight, the result sums to 1."""
    cover = np.ones((4, 4))
    cover[1, 1] = 0.0
    cover[1, 2] = 0.5
    w = {(1, 1): 0.25, (1, 2): 0.25, (2, 2): 0.25, (-1, 2): 0.25}
    r = ei.restrict_to_board(w, cover, 4, 4)
    assert (1, 1) not in r and (-1, 2) not in r
    assert abs(sum(r.values()) - 1.0) < 1e-12
    assert abs(r[(1, 2)] / r[(2, 2)] - 0.5) < 1e-12
    assert ei.restrict_to_board({(9, 9): 1.0}, None, 4, 4) == {}


def test_fold_moves_the_weight_outside_the_grid_to_the_mirror_cell():
    """!@brief A cell at column -1 goes to column 0, at column nx to nx - 1; the total is preserved."""
    w = {(2, -1): 0.2, (2, 0): 0.3, (2, 4): 0.5}
    r = ei.fold_into_grid(w, 5, 5)
    assert abs(r[(2, 0)] - 0.5) < 1e-12 and abs(r[(2, 4)] - 0.5) < 1e-12
    assert abs(sum(r.values()) - 1.0) < 1e-12
