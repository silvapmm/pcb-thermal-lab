#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_solid3d_via_spread.py
@brief The copper of a via larger than a cell of the 3D solid is spread over the cells of its disc, not clipped to one cell.
@details A 0.5 mm copper-filled via has a copper-equivalent area of 0.19 mm2 at 0.25 mm cells of 0.0625 mm2: the old rule gave that cell a fraction of 1 and
         lost two thirds of the copper (it kept 32 %). The spread conserves the copper of the barrel.
"""

import math

import pytest

from pcbthermal import Problem, solid3d


def board(diameter_mm, fill_k=385.0):
    """!
    @brief A 20 x 20 mm two-layer board with one via at its centre.
    @param diameter_mm Drill diameter in mm.
    @param fill_k Conductivity of the fill in W/mK (385 = copper).
    @return Problem.
    """
    p = Problem.new(20, 20, 2).add_full_copper()
    p.add_heater(1, 1.0, rect=(8, 8, 12, 12))
    p.add_via(10, 10, diameter_mm)
    p.vias[0].fill_k = fill_k
    return p


@pytest.mark.parametrize("cell", [0.25, 0.5])
def test_the_copper_of_a_large_via_is_conserved(cell):
    p = board(0.5)
    net = solid3d.Solid(p, cell)
    want = p.vias[0].thermal_area(p.board.via_plating, p.board.materials.k_copper)
    got = float(net.via_frac.sum()) * net.dx * net.dy
    assert got == pytest.approx(want, rel=0.02)
    assert float(net.via_frac.max()) <= 1.0 + 1e-9
    if cell == 0.25:
        assert want > net.dx * net.dy                          # A case where the old rule clipped: one cell of 0.0625 mm2 held 32 % of 0.196 mm2
        assert int((net.via_frac > 0).sum()) > 1               # The copper is spread over several cells


def test_a_small_via_is_not_touched():
    p = board(0.3, fill_k=0.0)
    net = solid3d.Solid(p, 1.0)
    want = p.vias[0].thermal_area(p.board.via_plating, p.board.materials.k_copper)
    assert float(net.via_frac.sum()) * net.dx * net.dy == pytest.approx(want, rel=1e-12)
    assert int((net.via_frac > 0).sum()) == 1                  # One cell, as before
