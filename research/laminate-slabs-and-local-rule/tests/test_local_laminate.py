#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_local_laminate.py
@brief Tests of the prototype of research/laminate-slabs-and-local-rule: the local rule is the program's rule where it does not fire, the global fine rule where it fires everywhere, and conserves the heat.
@details Run: .venv/bin/python -m pytest -q research/laminate-slabs-and-local-rule/tests (from the repository root; small boards, a few seconds).
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


def test_edge_margin_zero_is_the_ring_only():
    """!
    @brief Review regression: edge_margin 0 flags the cells of the board border only (scipy's binary_dilation with iterations 0 floods the mask, which made "margin 0" equal to nodes everywhere).
    @return None
    """
    import cases
    import numpy as np
    from pcbthermal import fvm
    p, _ = cases.board(30, 20, 2, 3.2, 200.0, "corner")
    with LL.local_rule(p, trigger=1e9, edge=True, edge_margin=0):
        net = fvm.Network(p, 30, 20, assemble=False)
    flagged = net.ladder.plans[0].flagged
    assert int(flagged.sum()) == 2 * 30 + 2 * 20 - 4
    assert not flagged[1:-1, 1:-1].any()


def test_level_transition_keeps_two_thirds_of_the_lateral_laminate():
    """!
    @brief Review: the lateral laminate conductance across a face between a cell of level 2n and one of level n is about 0.68 of the slab's (harmonic mean of nodes of unequal
           thickness; the odd depths of the fine cell have no neighbour). Recorded as a limit of the prototype (README 7.2); a conservative transition would raise it to 1 and must update this test.
    @return None
    """
    import numpy as np
    from pcbthermal import fvm
    c = B.case(2.0, 3.2, W=20.0)
    p = B.problem_of(c, False)
    with LL.local_rule(p, trigger=0.05, target=0.05, n_cap=16):
        net = fvm.Network(p, 80, 80, assemble=False)
    S = net.S
    gx = fvm.Network._harmonic(S[:, :, :-1], S[:, :, 1:]).sum(axis=0)[40]
    tot = S.sum(axis=0)[40]
    ratio = gx / (0.5 * (tot[:-1] + tot[1:]))
    off = ratio[40:][np.abs(ratio[40:] - 1.0) > 1e-3]
    assert len(off) == 2 and np.all((off > 0.6) & (off < 0.75))


def test_edge_band_boundary_keeps_two_fifths_of_the_lateral_laminate():
    """!
    @brief Review: across the face between a flagged cell (4 sub-gaps) and a cell without interior nodes the lateral laminate conductance is 0.40 of the slab's (the copper nodes hold
           d/8 against d/2; the interior nodes have no neighbour). The same face exists in the program's rule at the edge of every flagged region (README 7.2); copper is taken out of S here.
    @return None
    """
    import numpy as np
    import cases
    from pcbthermal import fvm
    p, _ = cases.board(60, 40, 2, 3.2, 200.0, "corner")
    p.board.materials.k_copper = 1e-9
    with LL.local_rule(p, trigger=1e9, edge=True, edge_margin=1):
        net = fvm.Network(p, 120, 80, assemble=False)
    S = net.S
    gx = fvm.Network._harmonic(S[:, :, :-1], S[:, :, 1:]).sum(axis=0)[40]
    tot = S.sum(axis=0)[40]
    ratio = gx / (0.5 * (tot[:-1] + tot[1:]))
    off = ratio[np.abs(ratio - 1.0) > 1e-3]
    assert len(off) == 2 and np.allclose(off, 0.4, atol=1e-3)
