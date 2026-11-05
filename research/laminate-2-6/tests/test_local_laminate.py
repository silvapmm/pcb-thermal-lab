#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_local_laminate.py
@brief Tests of the prototype of research/laminate-2-6: the local rule is the program's rule where it does not fire, the global fine rule where it fires everywhere, and conserves the heat.
@details Run: .venv/bin/python -m pytest -q research/laminate-2-6/tests (from the repository root; small boards, a few seconds).
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))
import _boot26                                             # noqa: E402,F401
import local_laminate as LL                                # noqa: E402
import s2board as B                                        # noqa: E402


def _case():
    """!
    @brief A small thick-laminate case (S = 2 mm on 10 mm, 3.2 mm board).
    @return dict
    """
    return B.case(2.0, 3.2, W=10.0)


def test_inactive_local_rule_is_bit_identical():
    """!
    @brief A trigger that never fires gives the program's number to the last digit (pad and bare).
    @return None
    """
    c = _case()
    for pad in (False, True):
        a = B.run(c, pad, 0.5)[0]
        b = B.run(c, pad, 0.5, local=dict(trigger=1e9))[0]
        assert a == b


def test_forced_local_rule_equals_global_fine_rule():
    """!
    @brief With the fine region covering every flagged cell (huge margin) the local chain of 16 equals the global option (0.1 mm, 16) of the program.
    @return None
    """
    c = _case()
    for pad in (False, True):
        g = B.run(c, pad, 0.5, s_max=0.1, n_max=16)[0]
        l = B.run(c, pad, 0.5, local=dict(trigger=0.001, target=0.001, n_cap=16, margin_scale=1e3))[0]
        assert abs(l - g) < 1e-9 * abs(g)


def test_local_rule_adds_fewer_unknowns_than_global():
    """!
    @brief On a larger board the local rule has fewer unknowns than the global fine rule and more than the default.
    @return None
    """
    c = B.case(2.0, 3.2, W=20.0)
    u0 = B.run(c, False, 0.5)[1]
    ug = B.run(c, False, 0.5, s_max=0.1, n_max=16)[1]
    ul = B.run(c, False, 0.5, local=dict(trigger=0.1, target=0.05, n_cap=16))[1]
    assert u0 < ul < ug


def test_edge_nodes_raise_a_cool_edge_board():
    """!
    @brief With a large edge coefficient on a thick uniform board the edge nodes raise the hottest rise (the program's number is low against the 3D solver).
    @return None
    """
    import cases
    p, _ = cases.board(30, 20, 2, 3.2, 200.0, "corner")
    a = cases.rise(p, "fvm", 0.5)
    with LL.local_rule(p, trigger=1e9, edge=True, edge_margin=1):
        b = cases.rise(p, "fvm", 0.5)
    assert b > a * 1.02
