#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_simple_stackup_physical.py
@brief The simple stack-up and the advanced stack-up with equal gaps are one board: the same node slabs and bit-identical results in every model.
@details Before the fix the simple stack-up gave every layer node T / L, so the outer copper nodes of a board of three or more layers held more laminate than their half gap
         (research/strong-edge-laminate 8.2); the slabs are now copper plus half of each adjacent gap in both stack-ups.
"""

import copy

import numpy as np
import pytest

from pcbthermal import api, examples, model


def _example(h_side=None):
    """!
    @brief The example board (four layers, simple stack-up), optionally with an edge coefficient.
    @param h_side Edge coefficient in W/m2K (None: the board's own).
    @return Problem.
    """
    p = examples.example_board()
    if h_side is not None:
        p.board.h_side = h_side
    return p


def test_slabs_add_up_to_the_thickness_and_equal_the_advanced_ones():
    """!
    @brief The node slabs of the simple stack-up are copper plus half of each gap and equal those of the advanced stack-up with equal gaps.
    """
    for layers in (2, 3, 4, 6):
        b = model.Problem.new(40, 30, layers=layers, thickness_mm=1.6, copper_um=35.0).board
        s = b.slab_thicknesses()
        assert abs(s.sum() - b.thickness) < 1e-12
        t = copy.deepcopy(b)
        t.make_advanced()
        assert np.array_equal(s, t.slab_thicknesses())
    # A one-layer board keeps the whole thickness (the laminate nodes cut it)
    assert model.Problem.new(40, 30, layers=1, thickness_mm=1.6).board.slab_thicknesses()[0] == pytest.approx(1.6e-3)


@pytest.mark.parametrize("h_side", [None, 500.0])
def test_simple_and_equivalent_advanced_boards_give_the_same_result(h_side):
    """!
    @brief Every model gives bit-identical temperatures for the simple stack-up and the advanced one with equal gaps, without and with a cooled edge.
    @param h_side Edge coefficient in W/m2K (None: the board's own).
    """
    simple = _example(h_side)
    adv = copy.deepcopy(simple)
    adv.board.make_advanced()
    opt = api.SolverOptions(cell_mm=2.0)
    for key in ("fvm", "fdm", "lumped", "analytic"):
        opt = api.SolverOptions(cell_mm=2.0, models=(key,))
        a = api.simulate(simple, opt).results[key]
        b = api.simulate(adv, opt).results[key]
        assert np.array_equal(a.T, b.T), key
