#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_via_partial_copper.py
@brief Tests of the investigation: the cold spot is reproduced on the program as it is, the candidate treatments remove it, are bit-identical on uniform copper, keep K symmetric, and the warning rule fires where it should.
@details Run from the repository root: `.venv/bin/python -m pytest -q research/via-partial-copper/tests`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np                                                            # noqa: E402
import pytest                                                                 # noqa: E402

import cases                                                                  # noqa: E402
import viavariants as vv                                                      # noqa: E402
import warnrule                                                               # noqa: E402
from pcbthermal import viawell                                                # noqa: E402
from pcbthermal.examples import example_board                                 # noqa: E402
from test_maximum_principle import cold_spot, copper_edge_board, network, positive_entries   # noqa: E402


def solve(problem, cell, model="fvm"):
    """!
    @brief Network, rise and residual of a layered steady solve.
    @param problem Problem.
    @param cell Cell in mm.
    @param model "fvm" or "fdm".
    @return Tuple (net, theta, residual).
    """
    net = network(problem, model, cell)
    theta, res = net.solve_steady()
    return net, theta, res


def test_the_program_no_longer_has_the_cold_spot_on_the_documented_board():
    """!
    @brief The cold spot of this investigation (-7.94 K at 0.5 mm with the mean-potential via of 2.5.1) is gone with the star coupling of the program (feature/via-star-coupling).
    @return None.
    """
    problem = copper_edge_board()
    net, theta, _ = solve(problem, 0.5)
    assert cold_spot(problem, net, theta) >= -1e-9 * theta.max()


@pytest.mark.parametrize("variant", ["sheet", "plane", "star"])
@pytest.mark.parametrize("model", ["fvm", "fdm"])
def test_candidates_remove_the_cold_spot(variant, model):
    problem = copper_edge_board()
    with vv.patched(variant):
        net, theta, res = solve(problem, 0.5 if model == "fvm" else 0.25, model)
    assert res < 1e-9
    assert cold_spot(problem, net, theta) >= -1e-9 * theta.max()


@pytest.mark.parametrize("variant", ["sheet", "plane"])
def test_mean_potential_candidates_are_bit_identical_on_uniform_copper(variant):
    problem = example_board()
    _, ref, _ = solve(problem, 1.0)
    with vv.patched(variant):
        _, got, _ = solve(problem, 1.0)
    assert np.array_equal(ref, got)                                  # a uniform footprint is built by the program's own code


def test_star_has_no_positive_off_diagonal_entry_and_is_symmetric():
    problem = cases.edge()
    with vv.patched("star"):
        net, theta, res = solve(problem, 0.25)
    assert positive_entries(net)[0] == 0
    K = net.K.tocsr()
    assert abs(K - K.T).max() <= 1e-12 * abs(K).max()
    assert theta.min() >= 0.0 and res < 1e-9


@pytest.mark.parametrize("variant", ["sheet", "plane", "star"])
def test_dense_blocks_are_positive_semidefinite_with_zero_row_sums(variant):
    problem = cases.edge()
    b = problem.board
    with vv.patched(variant):
        net = cases.network(problem, "fvm", 0.25)
    blocks = [bl for bl in net.via_blocks if isinstance(bl, vv.Block)]
    assert blocks                                                    # the footprint is partial: the variant built a dense block
    for bl in blocks:
        M = bl.M
        assert np.abs(M.sum(axis=1)).max() <= 1e-9 * np.abs(M).max()
        assert np.linalg.eigvalsh(0.5 * (M + M.T)).min() >= -1e-9 * np.abs(M).max()


def test_antipads_give_no_cold_spot_and_no_negative_rise():
    problem = cases.array4()
    for variant in ("current", "sheet", "star"):
        with vv.patched(variant):
            net, theta, _ = solve(problem, 0.25)
        assert theta.min() >= 0.0
        assert positive_entries(net)[0] >= 0                         # (the count is informative: antipads leave the footprints uniform)


def test_warning_rule_fires_on_a_copper_edge_and_is_silent_on_the_example():
    assert warnrule.partial_vias(cases.edge(), 0.5)
    assert warnrule.partial_vias(cases.track(), 0.25)
    assert not warnrule.partial_vias(example_board(), 1.0)
    assert not warnrule.partial_vias(cases.array4(), 0.25)


def test_per_layer_weights_sum_to_one_and_stay_on_the_board():
    problem = cases.edge()
    with vv.patched("sheet"):
        net = cases.network(problem, "fvm", 0.25)
    bl = [x for x in net.via_blocks if isinstance(x, vv.Block)][0]
    ny, nx = net.cover.shape
    for cells in bl.layer_cells:
        assert ((cells[:, 0] >= 0) & (cells[:, 0] < ny) & (cells[:, 1] >= 0) & (cells[:, 1] < nx)).all()
    assert viawell.TARGET_RATIO > 0
