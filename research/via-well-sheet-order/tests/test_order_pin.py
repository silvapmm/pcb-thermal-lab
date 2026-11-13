#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_order_pin.py
@brief Pins the chosen convention: the via wells of the FVM and FDM read the sheet of the copper nodes BEFORE the laminate rule, and the other order moves the result by a stated, small amount.
@details Run: `.venv/bin/python -m pytest -q research/via-well-sheet-order/tests`.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import cases                                                                # noqa: E402
import order_patch                                                          # noqa: E402
from pcbthermal import fvm, viawell                                         # noqa: E402


def _well_sheet(problem, cell_mm):
    """!
    @brief The sheet handed to viawell.build by a real FVM network and the sheet of the copper nodes the network keeps.
    @param problem Problem.
    @param cell_mm Cell in mm.
    @return tuple (S given to the wells, S of the network's copper nodes), each (L, ny, nx).
    """
    seen = []
    real = viawell.build

    def spy(problem_, d, S, *a, **k):
        seen.append(np.array(S, copy=True))
        return real(problem_, d, S, *a, **k)

    viawell.build = spy
    try:
        n = int(round(cases.W_MM / cell_mm))
        net = fvm.Network(problem, n, n)
    finally:
        viawell.build = real
    L = problem.board.layers
    return seen[0][:L], net.S[:L]


def test_wells_read_the_sheet_before_the_rule():
    """!
    @brief With an edge film the band moves laminate out of the copper nodes, so the sheet the wells read is larger than the node's (1.3 % on full 35 um copper of a two-layer 1.6 mm board).
    @return None.
    """
    p = cases.board(2, 1.0, 200.0, 0.5)
    given, kept = _well_sheet(p, 0.5)
    assert np.all(given >= kept - 1e-18)
    assert (given > kept * 1.005).any()                      # edge-band cells: the convention is the sheet before the rule


def test_the_other_order_moves_the_result_by_less_than_a_twentieth_of_a_kelvin():
    """!
    @brief Reading the sheet after the rule changes the hottest rise by at most 0.05 K and 0.1 % of the rise (measured: 0.036 K, 0.044 %), the FDM by less than the FVM.
    @return None.
    """
    for model in ("fvm", "fdm"):
        p = cases.board(2, 0.2, 10.0, 3.0)
        b = cases.rise(p, 1.0, model, "before")
        a = cases.rise(p, 1.0, model, "after")
        assert 0.0 < a - b < 0.05 and (a - b) / b < 1e-3
    # the patch leaves the program as it was when the block ends
    assert viawell.build.__module__ == "pcbthermal.viawell"
    p = cases.board(2, 1.0, 10.0, 1.0)
    assert cases.rise(p, 1.0, "fvm", "before") == cases.rise(p, 1.0, "fvm", "before")
    assert not order_patch.PENDING
