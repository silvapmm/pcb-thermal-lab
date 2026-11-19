#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_rules.py
@brief Closed-form checks of the rules of lib/rules.py on a one-dimensional board (every watt crosses the layer), and of the plate definitions.
"""

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "through-thickness-readout", "lib"))
import plates  # noqa: E402
import rules  # noqa: E402
import solid3d_sublayers  # noqa: E402
import transient as TR  # noqa: E402


def test_solid_rule_on_a_one_dimensional_board_reads_q_t_over_2k():
    # The part covers the whole face, the top is insulated: the flux through the copper is q everywhere, so surface - column = q t / 2k (rule S, one slab)
    case = TR.CASES[0]
    prob = TR.problem(case)
    mod = solid3d_sublayers.load(1)
    net = mod.Solid(prob, 5.0)
    theta, _ = net.solve()
    r = rules.solid_rule(net, theta, 1)
    q = 1.0 / (0.02 * 0.02)
    assert float(r["d_top"][r["mask"]].max()) == pytest.approx(q * 10e-3 / (2 * 385.0), rel=2e-3)


def test_solid_rule_with_slabs_adds_the_half_slab():
    case = TR.CASES[0]
    prob = TR.problem(case)
    mod = solid3d_sublayers.load(4)
    net = mod.Solid(prob, 5.0)
    theta, _ = net.solve()
    r = rules.solid_rule(net, theta, 4)
    q = 1.0 / (0.02 * 0.02)
    # surface = first slab + q dz/2k; column = mean of the 4 slabs; 1D: the first slab is hotter than the mean by 3/8 of the bound plus the half slab 1/8 of it
    assert float(r["d_top"][r["mask"]].max()) == pytest.approx(q * 10e-3 / (2 * 385.0), rel=0.02)


def test_the_plates_have_sources_on_cell_edges_at_half_a_millimetre():
    for spec in plates.PLATES:
        e = np.asarray(plates.rect_mm(spec[4])) / 0.5
        assert np.abs(e - np.round(e)).max() < 1e-9
