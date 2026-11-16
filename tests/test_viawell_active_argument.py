#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_viawell_active_argument.py
@brief The deprecated `active` argument of `viawell.build` is ignored: results are bit-identical with and without it, and the FVM and FDM no longer pass it.
@details The argument stays only so that research code that still passes it keeps working (`docs/versions.md`, housekeeping).
"""

import numpy as np

from pcbthermal import Problem, fdm, fvm, viawell


def _board():
    """!
    @brief A 10 x 10 mm two-layer board with a source and two copper vias.
    @return Problem.
    """
    p = Problem.new(10.0, 10.0, 2, 1.6, 35.0, h_top=10.0, h_bottom=200.0)
    for layer in (1, 2):
        p.add_zone(layer, rect=(0, 0, 10, 10), fill=1.0)
    p.add_heater(1, 0.5, rect=(1, 4, 4, 6))
    p.add_via(5.0, 5.0, 0.3, fill_k=385.0)
    p.add_via(8.0, 3.0, 0.3, fill_k=385.0)
    return p


def _calls(build_network):
    """!
    @brief Build a network with `viawell.build` wrapped to record the arguments of every call.
    @param build_network Function that builds the network.
    @return list of (args, kwargs) of the calls.
    """
    calls = []
    real = viawell.build

    def spy(*a, **k):
        calls.append((a, k))
        return real(*a, **k)

    viawell.build = spy
    try:
        build_network()
    finally:
        viawell.build = real
    return calls


def test_callers_do_not_pass_active_and_the_result_ignores_it():
    """!
    @brief The FVM and FDM call build with nine positional arguments and no `active`; adding it (all true, all false) changes nothing.
    @return None.
    """
    p = _board()
    calls = _calls(lambda: fvm.Network(p, 10, 10)) + _calls(lambda: fdm.Network(p, 10, 10))
    assert calls
    for a, k in calls:
        assert len(a) == 9 and "active" not in k
        ref_blocks, ref_gz = viawell.build(*a)
        ny, nx = a[7], a[6]
        for act in (np.ones((ny, nx), bool), np.zeros((ny, nx), bool), None):
            blocks, gz = viawell.build(*a, active=act)
            assert np.array_equal(gz, ref_gz)
            assert len(blocks) == len(ref_blocks)
            for b, r in zip(blocks, ref_blocks):
                for x, y in zip(b, r):
                    assert np.array_equal(np.asarray(x), np.asarray(y))
