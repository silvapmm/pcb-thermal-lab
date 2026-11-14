#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_lumped_dense_via_group.py
@brief Tests of the tools of the investigation: the barrel area of the independent 3D reference, the 3D reference against the FVM on a board without vias and against the heat balance, the patched variants restore the program.
Usage: python -m pytest research/lumped-dense-via-group/tests -q   (from the repository root)
"""

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import viastudy as v                                                          # noqa: E402
import ref3d                                                                  # noqa: E402
import variants as var                                                        # noqa: E402
from pcbthermal import lumped                                                 # noqa: E402


def test_barrel_area_is_conserved():
    """!
    @brief The sampled copper and core areas of one via add up to the annulus and the disc of the program.
    @return None.
    """
    dx, r, plating = 0.125e-3, 0.15e-3, 25e-6
    n = 40
    f_cu, f_core = ref3d.barrel_shares([(2.5e-3, 2.5e-3, r, False, 0.0)], plating, dx, n)
    area = dx * dx
    assert abs(f_cu.sum() * area - math.pi * (r ** 2 - (r - plating) ** 2)) < 0.01 * math.pi * r ** 2
    assert abs(f_core.sum() * area - math.pi * (r - plating) ** 2) < 0.01 * math.pi * r ** 2


def test_reference_agrees_with_the_fvm_without_vias():
    """!
    @brief On a 40 x 40 mm board without vias the independent 3D peak is within 1.5 % of the rise of the FVM at 0.25 mm (the program's layered idealisation against a 3D solid).
    @return None.
    """
    p = v.board(2, 0, 1.0, 0.3, 8.0, size=(40.0, 40.0))
    p.board.h_side = 0.0
    t = ref3d.solve(p, 0.25)
    f = v.run(p, "fvm", 0.25)
    assert abs(v.pct(f["parts"][0]["peak"], t["peak"], p.board.ambient)) < 1.5


def test_reference_heat_balance():
    """!
    @brief The 3D reference's mean surface temperature lies between the ambient and the peak, and the peak above the mean.
    @return None.
    """
    p = v.board(2, 5, 1.0, 0.3, 8.0, size=(40.0, 40.0))
    p.board.h_side = 0.0
    t = ref3d.solve(p, 0.25)
    assert p.board.ambient < t["mean"] < t["peak"]


def test_patches_restore_the_program():
    """!
    @brief `variants.patched` changes the module and restores every name on exit.
    @return None.
    """
    before = (lumped._core_mask, lumped.CORE_R, lumped.MAX_CORE, lumped.ZONE_CELL_MM, lumped._mutual_potentials)
    with var.patched(true_core=True, core_r=0.5, max_core=0.6, zone_cell=0.25, ac_scale=2.0):
        assert lumped.CORE_R == 0.5 and lumped.MAX_CORE == 0.6 and lumped._core_mask is not before[0]
    assert (lumped._core_mask, lumped.CORE_R, lumped.MAX_CORE, lumped.ZONE_CELL_MM, lumped._mutual_potentials) == before


def test_true_core_is_symmetric():
    """!
    @brief The position-based core of a centred array is symmetric under the board's mirror image (the program's own mask is not, on this raster).
    @return None.
    """
    from pcbthermal import viaconstriction
    from pcbthermal.lumped import Network
    p = v.board(2, 5, 1.0, 0.3, 8.0, size=(40.0, 40.0))
    net = Network(p, 80, 80, assemble=False, with_blocks=True, ladder=False, cut_cells=False)
    cov = lumped._footprint_coverage(net, p.heaters[0])
    core = var._true_core_mask(net, cov, viaconstriction.ViaSet(p))
    assert core is not None and np.array_equal(core, core[::-1]) and np.array_equal(core, core[:, ::-1])
