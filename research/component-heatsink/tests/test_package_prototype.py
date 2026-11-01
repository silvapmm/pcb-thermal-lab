#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_package_prototype.py
@brief Tests of the frozen package prototype: the guard against a ladder network and the agreement with the program on a small board.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research" / "component-heatsink" / "scripts"))
import package_prototype as pp                                 # noqa: E402
from pcbthermal import fvm, SolverOptions, simulate            # noqa: E402


def _small():
    """!
    @brief A small datasheet-style board (pad 8 mm) for fast tests.
    @return Problem from package_prototype.board.
    """
    return pp.board(8.0)


def test_guard_raises_on_ladder_network():
    """!
    @brief The guard raises a clear RuntimeError on a network with the laminate nodes of the rule, instead of letting spsolve hang.
    @return None.
    """
    net = fvm.Network(_small(), 38, 38, ladder=True)
    if net.ladder is None:
        pytest.skip("the rule does not apply to this board in this version")
    with pytest.raises(RuntimeError, match="ladder=False"):
        pp.check_frozen(net)


def test_frozen_network_passes_guard():
    """!
    @brief The frozen network passes the guard.
    @return None.
    """
    pp.check_frozen(pp.make_network(_small(), 38, 38))


def test_offset_matches_program_on_small_board():
    """!
    @brief The frozen prototype (offset model, constant h) matches the program's FVM board maximum on the same board.
    @return None.
    """
    p = _small()
    p.add_full_copper()          # Full copper on both layers: no absent-copper cell, so the laminate rule of 2.4.5 changes nothing
    p.board.h_mode = "computed"
    p.heaters[0].power = 1.0
    ref = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"].t_max
    r = pp.solve(p, 1.0, 0.0, "offset", cell_mm=1.0)
    # The prototype recomputes h by iteration; a loose bound is enough to catch a wrong matrix
    assert abs(r["board_max"] - ref) < 3.0
