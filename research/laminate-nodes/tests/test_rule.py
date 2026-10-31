#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_rule.py
@brief Tests of lib/rule.py: the law for n, the cut of a gap, the mask with its margin and the counts of unknowns (no solver is run).
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))

import rule as RU  # noqa: E402


def test_n_law():
    """!
    @brief n = ceil(d / s_max) between n_min and n_max; n_fixed overrides it.
    @return None.
    """
    r = RU.Rule()
    got = {d: RU.n_for_gap(r, d * 1e-3) for d in (0.1, 0.2, 0.4, 0.8, 1.0, 1.565, 1.6, 3.2)}
    assert got[0.1] == got[0.2] == got[0.4] == 1
    assert got[0.8] == 2 and got[1.0] == 3 and got[1.6] == 4 and got[3.2] == 4
    assert RU.n_for_gap(RU.Rule(n_fixed=7), 0.1e-3) == 7


def test_sub_gaps():
    """!
    @brief The sub-gaps sum to d, are symmetric, equal for ratio 1 and 1:2:2:1 for n = 4 and ratio 2.
    @return None.
    """
    d = 1.6e-3
    for n in (1, 2, 3, 4, 8):
        for ratio in (1.0, 1.5, 2.0):
            s = RU.sub_gaps(d, n, ratio)
            assert abs(s.sum() - d) < 1e-15 and np.allclose(s, s[::-1])
    assert np.allclose(RU.sub_gaps(d, 4, 1.0), d / 4)
    assert np.allclose(RU.sub_gaps(d, 4, 2.0), d * np.array([1, 2, 2, 1]) / 6)


def test_mask_and_margin():
    """!
    @brief No bare cell: empty mask. One bare cell: it is flagged, the margin grows it by the cells within the distance, never outside the board.
    @return None.
    """
    fill = np.ones((21, 21))
    assert not RU.flag_cells(RU.Rule(), fill, fill, 1.6e-3, 0.5e-3).any()
    fill[10, 10] = 0.0
    r0 = RU.Rule(margin="none")
    assert RU.flag_cells(r0, fill, fill, 1.6e-3, 0.5e-3).sum() == 1
    m = RU.flag_cells(RU.Rule(margin="2", shape="disc"), fill, fill, 1.6e-3, 0.5e-3)
    assert m[10, 12] and m[12, 10] and not m[12, 12] and m.sum() == 13
    md = RU.flag_cells(RU.Rule(margin="2", shape="diamond"), fill, fill, 1.6e-3, 0.5e-3)
    assert md.sum() == 13                                   # the diamond of radius 2 and the disc of radius 2 are the same cells
    ms = RU.flag_cells(RU.Rule(margin="2", shape="square"), fill, fill, 1.6e-3, 0.5e-3)
    assert ms.sum() == 25
    active = np.ones_like(fill, dtype=bool)
    active[:, 11:] = False
    assert not (RU.flag_cells(RU.Rule(margin="2"), fill, fill, 1.6e-3, 0.5e-3, active) & ~active).any()


def test_gap_margin_rule():
    """!
    @brief The default margin is a gap thickness plus a cell.
    @return None.
    """
    assert RU.margin_cells(RU.Rule(), 1.6e-3, 0.5e-3) == 5
    assert RU.margin_cells(RU.Rule(), 0.8e-3, 1.0e-3) == 2


def test_unknown_counts():
    """!
    @brief Ragged and dense counts of a two-layer board with n = 4 in 100 of 1000 cells, and of a one-layer board.
    @return None.
    """
    u = RU.unknowns(2, 1000, [100], [4])
    assert u["program"] == 2000 and u["ragged"] == 2300 and u["dense"] == 5000
    u1 = RU.unknowns(1, 1000, [100], [2], one_layer=True)
    assert u1["program"] == 3000 and u1["ragged"] == 2100 and u1["dense"] == 3000
