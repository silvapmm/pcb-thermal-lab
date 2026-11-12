#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_via_well_sheet_order.py
@brief Pins the convention of the via wells: the FVM and the FDM hand to `viawell.build` the sheet conductance of the copper nodes BEFORE the laminate rule moved laminate out of them.
@details The choice was measured in `research/via-well-sheet-order`: reading the reduced sheet instead moves the hottest rise by +0.002 to +0.036 K and is never closer to the resolved 3D
         barrel, so the order is kept (`docs/theory.md` 2.6). The test fails if someone reorders the calls: in the cells the edge band flags the sheet the wells read is larger than the sheet of
         the network's copper nodes (1.3 % on a full 35 um copper plane of a 1.6 mm board).
"""

import numpy as np

from pcbthermal import Problem, fdm, fvm, laminate, viawell
from pcbthermal.model import Materials


def _board():
    """!
    @brief The board of the study: 10 x 10 mm, two copper planes of 35 um, 1.6 mm, an edge film of 200 W/m2K, a 0.5 W source and one 0.3 mm copper via 0.5 mm from the right edge.
    @return Problem.
    """
    p = Problem.new(10.0, 10.0, 2, 1.6, 35.0, h_top=10.0, h_bottom=200.0, h_side=200.0, materials=Materials(k_fr4_inplane=0.3))
    for layer in (1, 2):
        p.add_zone(layer, rect=(0, 0, 10, 10), fill=1.0)
    p.add_heater(1, 0.5, rect=(1, 4, 4, 6))
    p.add_via(9.5, 5.0, 0.3, fill_k=385.0)
    return p


def _spy(build_network):
    """!
    @brief Run a network builder with `viawell.build` replaced by a spy that keeps the sheet it is given.
    @param build_network Function that builds the network and returns it.
    @return tuple (network, sheet given to the wells (L, ny, nx)).
    """
    seen = []
    real = viawell.build

    def spy(problem, d, S, *a, **k):
        seen.append(np.array(S, copy=True))
        return real(problem, d, S, *a, **k)

    viawell.build = spy
    try:
        net = build_network()
    finally:
        viawell.build = real
    return net, seen[0]


def test_the_fvm_wells_read_the_sheet_before_the_rule():
    """!
    @brief In the edge band the laminate leaves the copper nodes, so the sheet the wells read is at least the node's and larger than it by more than 0.5 % somewhere.
    @return None.
    """
    p = _board()
    net, given = _spy(lambda: fvm.Network(p, 20, 20))
    kept = net.S[:2]
    assert np.all(given[:2] >= kept - 1e-18)
    assert (given[:2] > kept * 1.005).any()


def test_the_fdm_wells_read_the_sheet_before_the_rule():
    """!
    @brief The same convention in the node-centred FDM ('as in the FVM'): the sheet of the copper nodes after the rule is read from the result of `laminate.build`.
    @return None.
    """
    p = _board()
    kept = []
    real = laminate.build

    def spy(*a, **k):
        rule = real(*a, **k)
        kept.append(np.array(rule.S[:2], copy=True))
        return rule

    laminate.build = spy
    try:
        _net, given = _spy(lambda: fdm.Network(p, 0.5))
    finally:
        laminate.build = real
    assert np.all(given[:2] >= kept[0] - 1e-18)
    assert (given[:2] > kept[0] * 1.005).any()
