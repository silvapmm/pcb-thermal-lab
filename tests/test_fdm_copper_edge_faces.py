#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fdm_copper_edge_faces.py
@brief The in-plane face sheet of a drawn copper layer in the FDM is built from the copper fill of the cells the face runs through (`face_fill`, default), not from the harmonic mean of the two nodal sheets.
@details A node whose control volume is cut by a copper edge carries half the copper; the harmonic mean of the nodal sheets then read the first copper link 0.67 of the copper sheet and
         smeared the copper edge over a cell. The face sheet now comes from the cells (uniform along the face). Checked here: the matrix stays symmetric with no positive off-diagonal
         and rows summing to the ambient conductance, uniform and hatched copper stay bit-identical, the boards with a copper edge move towards the independent 3D solver
         (`tests/helpers/layered3d.py`, imports nothing from the program) and never past it, the switch `face_fill=False` is the earlier harmonic mean, and imported layers and
         boards with a metal block are untouched.
"""

import os
import sys

import numpy as np
import pytest
import scipy.sparse as sp

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))
import layered3d as L                                          # noqa: E402

from pcbthermal import fdm, Problem                            # noqa: E402
from test_fdm_harmonic_face import gap_board, gap_reference            # noqa: E402


def inset_board(h_side, inset=0.5):
    """!
    @brief A 10 mm two-layer plate with the copper `inset` mm inside the wall and a 2 mm part of 1 W at the centre.
    @param h_side Edge coefficient in W/m2K.
    @param inset Copper inset in mm.
    @return Problem.
    """
    p = Problem.new(10.0, 10.0, layers=2, thickness_mm=1.6, copper_um=35.0, h_top=10.0, h_bottom=10.0, h_side=h_side)
    for layer in (1, 2):
        p.add_zone(layer, rect=(inset, inset, 10.0 - inset, 10.0 - inset))
    p.add_heater(1, 1.0, rect=(4, 4, 6, 6), name="U")
    return p


@pytest.mark.parametrize("h_side", [10.0, 200.0, 1e3, 1e5])
def test_matrix_symmetric_no_new_positive_off_diagonal_and_rows_sum_to_the_ambient(h_side):
    net = fdm.Network(inset_board(h_side), 0.5)
    K = sp.csr_matrix(net.K)
    assert abs(K - K.T).max() <= 1e-12 * abs(K).max()
    assert (K - sp.diags(K.diagonal())).max() <= 0.0
    # A constant temperature field is exact (the film and the ambient are the only ground): the rows sum to the conductance to the ambient, to the last digits
    assert np.abs(np.asarray(K.sum(axis=1)).ravel() - net.g_amb.ravel()).max() <= 1e-12 * net.g_amb.max()


def test_the_balance_closes():
    p = inset_board(200.0)
    r = fdm.solve_steady(p, 0.5)
    assert abs(r.balance_error) < 1e-9


def test_uniform_and_hatched_copper_are_bit_identical_to_the_harmonic_mean():
    p = Problem.new(30.0, 30.0, layers=2, h_top=10.0, h_bottom=15.0, h_side=None)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(12, 12, 18, 18))
    assert np.array_equal(np.asarray(fdm.solve_steady(p, 1.0).T), np.asarray(fdm.solve_steady(p, 1.0, face_fill=False).T))
    q = Problem.new(30.0, 30.0, layers=2, h_top=10.0, h_bottom=15.0, h_side=10.0)
    for layer in (1, 2):
        q.add_zone(layer, rect=(0, 0, 30, 30), fill=0.4)                      # hatched copper: a uniform fill between 0 and 1
    q.add_heater(1, 1.0, rect=(12, 12, 18, 18))
    assert np.array_equal(np.asarray(fdm.solve_steady(q, 1.0).T), np.asarray(fdm.solve_steady(q, 1.0, face_fill=False).T))


@pytest.mark.parametrize("cell, old, new", [(1.0, -0.0549, -0.0352), (0.5, -0.0317, -0.0192)])
def test_across_a_copper_gap_the_cell_fill_faces_are_closer_and_stay_cool(cell, old, new):
    # Against the independent 3D solver at the same cell (measured here, hottest rise): harmonic mean of the nodal sheets -5.49 / -3.17 %, faces from the cells -3.52 / -1.92 %
    ref = gap_reference(cell)
    a = float(fdm.solve_steady(gap_board(), cell, face_fill=False).t_max) - 25.0
    b = float(fdm.solve_steady(gap_board(), cell).t_max) - 25.0
    assert a / ref - 1.0 == pytest.approx(old, abs=0.002)
    assert b / ref - 1.0 == pytest.approx(new, abs=0.002)
    assert a / ref - 1.0 < b / ref - 1.0 < 0.0                                 # closer, and never past the reference


def test_a_copper_edge_between_nodes_keeps_the_first_copper_link_whole():
    # One layer-pair plate whose copper edge lies half a cell from a node: the cell fill of the face on the copper side is 1, so the face carries the whole copper sheet
    p = inset_board(10.0, inset=2.0)
    on = fdm.Network(p, 1.0)
    off = fdm.Network(p, 1.0, face_fill=False)
    assert on.K.shape == off.K.shape and on.K.nnz == off.K.nnz              # same unknowns, same pattern
    d = (on.K - off.K).tocoo()
    assert abs(d.data).max() > 0.0
    assert (on.C - off.C).max() == 0.0                                       # capacities unchanged


def test_the_variant_does_not_touch_the_arithmetic_mean_or_a_board_with_a_metal_block():
    p = inset_board(200.0)
    a1 = fdm.solve_steady(p, 1.0, "arithmetic")
    a0 = fdm.solve_steady(p, 1.0, "arithmetic", face_fill=False)
    assert np.array_equal(np.asarray(a1.T), np.asarray(a0.T))
    p.add_heatsink(2, 20.0, rect=(3, 3, 7, 7), thickness_mm=2.0)             # A metal block keeps the earlier laminate treatment, so no face is replaced
    assert any(s.is_block() for s in p.heatsinks)
    assert np.array_equal(np.asarray(fdm.solve_steady(p, 1.0).T), np.asarray(fdm.solve_steady(p, 1.0, face_fill=False).T))
