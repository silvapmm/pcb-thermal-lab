#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_layered.py
@brief Regression tests of the copy of the layered FVM with refined gaps (lib/layered.py, lib/treatments.py): the program is reproduced, a fully covered board is bit-identical under every treatment, an exact series circuit, and a bare window is warmer with more nodes.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))

import cases as C                                                           # noqa: E402
import layered as LY                                                        # noqa: E402
import treatments as TR                                                     # noqa: E402


def _setup(case, cell):
    """!
    @brief Problem, network (with its matrix) and the gap data of a case.
    @param case Case.
    @param cell Cell in mm.
    @return tuple (problem, net, gaps, kz, kxy).
    """
    p = C.problem(case)
    net = LY.network(p, cell)
    net.K = net._assemble()
    gaps, kz, kxy = LY.gap_data(p)
    return p, net, gaps, kz, kxy


def test_one_sub_gap_is_the_program():
    """!
    @brief With no refinement the copy reproduces the program's FVM peak and field to 1e-9 K, for a bare window and a typical 4 layer stack-up.
    @return None.
    """
    for case in (C.Case("a", layers=2, size=12.0, part=4.0, window=C.centred_window(4, 12.0)), C.Case("b", layers=4, stack="template", size=12.0, part=4.0, window=C.centred_window(4, 12.0))):
        p, net, gaps, kz, kxy = _setup(case, 1.0)
        th, _ = net.solve_steady()
        r = LY.solve(net, gaps, kz, kxy, [None] * (case.layers - 1), [None] * (case.layers - 1))
        assert abs(r["peak"] - th.max()) < 1e-9
        assert np.abs(r["top"] - th[0]).max() < 1e-9


def test_full_copper_is_bit_identical_under_every_treatment():
    """!
    @brief A board fully covered by copper has no flagged cell, so the nodes and skin treatments give exactly the program's result.
    @return None.
    """
    case = C.Case("c", layers=4, stack="template", size=12.0, part=4.0)
    p, net, gaps, kz, kxy = _setup(case, 1.0)
    base = TR.run(p, net, {"kind": "none"}, gaps, kz, kxy)["peak"]
    for t in ({"kind": "nodes", "n": 4}, {"kind": "skin", "alpha": 0.25}):
        r = TR.run(p, net, t, gaps, kz, kxy)
        assert r["peak"] == base and r["unknowns"] == 4 * 144 and sum(r["flagged"]) == 0


def test_refined_gap_is_a_series_circuit():
    """!
    @brief Cutting the gap of a board whose copper is everywhere into 5 sub-gaps and refining every cell leaves the 1D column unchanged (series of equal links, no lateral gradient).
    @return None.
    """
    case = C.Case("d", layers=2, size=6.0, part=6.0)
    p, net, gaps, kz, kxy = _setup(case, 1.0)
    one = LY.solve(net, gaps, kz, kxy, [None], [None])["peak"]
    five = LY.solve(net, gaps, kz, kxy, [np.full(5, gaps[0] / 5)], [np.ones((net.ny, net.nx), bool)])["peak"]
    assert abs(one - five) < 1e-9


def test_more_nodes_warm_a_bare_window_towards_the_reference():
    """!
    @brief Over a bare window the program is cool and each doubling of the nodes raises the peak (monotone towards the resolved reference).
    @return None.
    """
    case = C.Case("e", layers=2, size=12.0, part=4.0, window=C.centred_window(4, 12.0))
    p, net, gaps, kz, kxy = _setup(case, 0.5)
    peaks = [TR.run(p, net, t, gaps, kz, kxy)["peak"] for t in ({"kind": "none"}, {"kind": "nodes", "n": 2}, {"kind": "nodes", "n": 4})]
    assert peaks[0] < peaks[1] < peaks[2]
    ref = C.reference(case, 0.25, 8, p)["max"]
    assert abs(peaks[2] - ref) < abs(peaks[0] - ref)
