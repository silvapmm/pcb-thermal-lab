#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_variant.py
@brief Tests of the face fill of the FDM: the switchless copy is the program, the prototype of this folder (`lib/fdm_variant.py`) equals the code adopted in the program
       (`fdm.Network(face_fill=True)`), and the face fill keeps the invariants and moves the copper-edge boards as measured against the harmonic mean (`face_fill=False`).
@details Run from the repository root: `.venv/bin/python -m pytest -q research/fdm-inset-edge/tests`.
"""

import os
import sys

import numpy as np
import pytest
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(1, os.path.join(HERE, "..", "scripts"))
sys.path.insert(2, os.path.join(HERE, "..", "..", "..", "tests", "helpers"))

import boards as B                                            # noqa: E402
import fdm_variant                                            # noqa: E402
from pcbthermal import Problem, fdm                           # noqa: E402

FACE = fdm_variant.load(face_fill=True)                      # the prototype of this folder (program face path off)
HARM = fdm_variant.harmonic()                                # the program with face_fill=False


def test_the_switchless_copy_is_the_program_bit_for_bit():
    p = B.plate(200.0, 0.5)
    a = fdm.solve_steady(p, 0.5)
    b = fdm_variant.load().solve_steady(p, 0.5)
    assert np.array_equal(np.asarray(a.T), np.asarray(b.T))


def test_uniform_copper_does_not_move():
    p = Problem.new(30.0, 30.0, layers=2, h_top=10.0, h_bottom=15.0, h_side=None)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(12, 12, 18, 18))
    a, b = fdm.solve_steady(p, 1.0), FACE.solve_steady(p, 1.0)
    assert np.array_equal(np.asarray(a.T), np.asarray(b.T))


def test_the_matrix_stays_symmetric_with_no_positive_off_diagonal_and_the_balance_closes():
    p = B.plate(200.0, 0.5)
    net = FACE.Network(p, 0.5)
    K = sp.csr_matrix(net.K)
    assert abs(K - K.T).max() <= 1e-12 * abs(K).max()
    assert (K - sp.diags(K.diagonal())).max() <= 0.0
    assert abs(FACE.solve_steady(p, 0.5).balance_error) < 1e-9


@pytest.mark.parametrize("h, cell, lo, hi", [(200.0, 0.25, -1.9, -1.1), (1000.0, 0.25, -3.4, -2.6)])
def test_the_inset_plate_is_closer_to_the_finite_element_limit(h, cell, lo, hi):
    # Measured (README 3): FDM harmonic -3.47 / -7.65 %, face fill -1.48 / -2.97 % against the finite-element limits 41.826 / 33.906 K
    p = B.plate(h, 0.5)
    ref = B.FEM_PLATE_INSET[h]
    old = B.err(B.read(HARM, p, cell), ref)
    new = B.err(B.read(fdm, p, cell), ref)
    assert lo < new < hi
    assert abs(new) < 0.6 * abs(old)


def test_a_plain_rectangle_and_the_same_rectangle_as_an_outline_agree_to_a_fifth_of_a_point():
    # README 3.3: the cut-cell treatment of the outline is not the cause (aligned square, copper 1.2 mm in)
    fem = B.FEM_SQUARE_INSET[200.0]
    a = B.err(B.read(HARM, B.square(200.0, 1.2, False), 0.6, "mean"), fem)
    b = B.err(B.read(HARM, B.square(200.0, 1.2, True), 0.6, "mean"), fem)
    assert abs(a - b) < 0.2


def test_the_wall_case_is_untouched():
    # copper to the wall: no copper edge inside the board, the variant equals the program to 1e-3 K
    p = B.plate(200.0, 0.0)
    assert abs(B.read(HARM, p, 0.5) - B.read(fdm, p, 0.5)) < 1e-3


def test_it_stays_on_the_cool_side_of_the_independent_solver_and_closer_to_it():
    import study_independent_3d as S
    ref = S.gap_ref(1.0)
    p = S.gap_board()
    old = float(HARM.solve_steady(p, 1.0).t_max) - 25.0
    new = float(fdm.solve_steady(p, 1.0).t_max) - 25.0
    assert old < new < ref
    assert abs(new / ref - 1.0) < abs(old / ref - 1.0)


@pytest.mark.parametrize("board", ["plate", "square", "gap"])
def test_the_prototype_of_this_folder_is_the_code_adopted_in_the_program(board):
    # The face fill was adopted as fdm.Network(face_fill=True); the prototype (program face path off) must give the same field.
    # The program replaces only the faces where a nodal fill differs from the face fill, the prototype every copper face; where the fills agree the two sheets
    # differ only by the mean of unequal bare sheets (laminate rule, outline cover): measured 5.5e-7, 1.7e-4 and 5.5e-6 K on rises of 32, 58 and 154 K.
    import study_independent_3d as S
    p = {"plate": lambda: B.plate(1000.0, 0.5), "square": lambda: B.square(200.0, 1.2, True), "gap": S.gap_board}[board]()
    a = np.asarray(fdm.solve_steady(p, 0.5).T)
    b = np.asarray(FACE.solve_steady(p, 0.5).T)
    assert np.max(np.abs(a - b)) < 1e-5 * np.max(np.abs(a - 25.0))
