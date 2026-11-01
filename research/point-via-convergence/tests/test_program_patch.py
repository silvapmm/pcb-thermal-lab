#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_program_patch.py
@brief Tests of the in-memory via treatments applied to the program's FVM and FDM (copies): identity, energy balance, symmetry and the convergence of the copper-fill gain.
"""

import math
import os
import sys

import numpy as np
import pytest

LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
sys.path.insert(0, LIB)

import program_cases as pc                                                  # noqa: E402
import program_patch as pp                                                  # noqa: E402
import resolved_boards as rb                                                # noqa: E402
from pcbthermal import fdm, fvm                                             # noqa: E402

ETA = math.exp(-0.25)


def setup_module(module):
    """!
    @brief Load the program's libraries once.
    @param module Unused.
    @return None.
    """
    pc.load_libraries()


# Maximum rise (K) of the 3 x 3 copper-filled array board at 1 mm, measured on the program as it was at commit f2d5c03 (the point via: the barrel conductance in the
# cell of the via centre), the last commit before the mean-potential via of `fix/point-via`; the program no longer has this treatment, the "point" copy does
FROZEN_POINT = {"fvm": 35.61075071681979, "fdm": 35.962234905460555}
# Copper-fill gain (K) of the same program, fvm, cells 1, 0.5, 0.25 and 0.125 mm
FROZEN_GAIN = {1.0: -4.780266035987886, 0.5: -4.3815425436297915, 0.25: -3.979922806922353, 0.125: -3.6422609750418857}


@pytest.mark.parametrize("model", ["fvm", "fdm"])
def test_the_point_patch_is_the_program_of_f2d5c03(model):
    """!
    @brief The "point" copy gives the temperatures (to 1e-9) that the program gave at `f2d5c03`, before the mean-potential via (values frozen from that commit).
    @param model fvm or fdm.
    @return None.
    """
    p = pc.array_board(385.0)
    base = pc.max_rise(p, model, 1.0)
    with pp.patched("point"):
        assert pc.max_rise(p, model, 1.0) == pytest.approx(FROZEN_POINT[model], rel=1e-9)
    assert pc.max_rise(p, model, 1.0) == base                                # the program's current treatment is back


def test_the_patch_is_removed_on_exit():
    """!
    @brief After the context the constructors of the program are the originals.
    @return None.
    """
    from pcbthermal import fdm
    a, b = fvm.Network.__init__, fdm.Network.__init__
    with pp.patched("mw_disc", eta=ETA):
        assert fvm.Network.__init__ is not a
    assert (fvm.Network.__init__, fdm.Network.__init__) == (a, b)


@pytest.mark.parametrize("name", ["mw_disc", "mw_area", "area", "peaceman"])
def test_a_board_without_vias_is_bit_identical(name):
    """!
    @brief No vias, no change.
    @param name Treatment.
    @return None.
    """
    p = pc.array_board(0.0)
    p.vias = []
    base = pc.max_rise(p, "fvm", 0.5)
    with pp.patched(name, eta=ETA):
        assert pc.max_rise(p, "fvm", 0.5) == base


@pytest.mark.parametrize("cell", [1.0, 0.25])
def test_energy_balance_and_symmetry_with_mean_couplings(cell):
    """!
    @brief With the mean-potential via couplings the matrix stays symmetric, the heat that leaves equals the power, and the via adds no loss to the ambient.
    @param cell Cell in mm.
    @return None.
    """
    p = pc.array_board(385.0)
    nx = int(round(p.board.width / (cell * 1e-3)))
    with pp.patched("mw_disc", eta=ETA):
        net = fvm.Network(p, nx, nx)
        theta, res = net.solve_steady()
    K = net.K
    assert abs(K - K.T).max() < 1e-12 * abs(K).max()
    out = float((net.g_amb * theta).sum())
    assert out == pytest.approx(float(net.Q.sum()), rel=1e-9)
    # Row sums of K are the conductances to the ambient: the via couplings conserve heat
    assert np.allclose(np.asarray(K.sum(axis=1)).ravel(), net.g_amb.ravel(), rtol=1e-9, atol=1e-12)
    assert res < 1e-9


def test_copper_fill_gain_converges_to_the_resolved_reference():
    """!
    @brief The regression test asked by the roadmap: the copper-fill gain of the via-array board is within 0.3 K of the fine-grid reference from 1 to 0.125 mm
           with the mean-potential treatment; the point via of `f2d5c03` (frozen) leaves that band below 0.5 mm and the program since `fix/point-via` is inside it.
    @return None.
    """
    par0, par1 = pc.layer_parameters(pc.array_board(0.0)), pc.layer_parameters(pc.array_board(385.0))
    ref = rb.array_quadrant(par1, 1 / 16 * 1e-3, 2.0, 5e-3) - rb.array_quadrant(par0, 1 / 16 * 1e-3, 2.0, 5e-3)
    assert ref == pytest.approx(-4.51, abs=0.05)
    for cell in (1.0, 0.5, 0.25, 0.125):
        with pp.patched("point"):
            point = pc.max_rise(pc.array_board(385.0), "fvm", cell) - pc.max_rise(pc.array_board(0.0), "fvm", cell)
        assert point == pytest.approx(FROZEN_GAIN[cell], rel=1e-9)         # the point via of f2d5c03, reproduced by the copy
    assert abs(FROZEN_GAIN[0.125] - ref) > 0.5                               # the point via at 0.125 mm was outside the band: the test fails on the old code
    program = pc.max_rise(pc.array_board(385.0), "fvm", 0.125) - pc.max_rise(pc.array_board(0.0), "fvm", 0.125)
    assert abs(program - ref) < 0.3                                          # the program since fix/point-via is inside it
