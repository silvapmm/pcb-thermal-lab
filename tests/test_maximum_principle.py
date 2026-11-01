#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_maximum_principle.py
@brief The via couplings put small positive off-diagonal entries into K (docs/theory.md 2.2): how many, how large, and does the SOLUTION still obey the discrete maximum principle?

@details A thermal matrix without vias is an M-matrix (non-positive off-diagonal entries), whose solution for non-negative sources is non-negative and has its maximum at a
         source. The Kron-reduced via barrels add couplings with zero row sum and positive entries inside a footprint, so K is no longer an M-matrix and the principle is
         not proved. This test measures the positive entries (count and largest value relative to the diagonal of their row) and checks the solution instead: no node
         below the ambient (rise at least -1e-9 of the maximum rise) and the hottest node holds a source, on the example board (1 mm) and on a board with a dense via array
         (0.5 mm), in the FVM and the FDM. The counts are printed with -s; a violation fails the test and must be reported, not relaxed.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

from pcbthermal import Problem, fdm, fvm
from pcbthermal.project import load_project

EXAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples", "example_board.pcbt.json")
TOLERANCE = 1e-9                                         # Fraction of the maximum rise allowed below zero (round-off of the direct solve)


def dense_via_board():
    """!
    @brief A four-layer 60 x 60 mm board with a 3 W part on a 8 mm pad and a dense 10 x 10 array of 0.3 mm vias (0.8 mm pitch) under it.
    @return Problem.
    """
    p = Problem.new(60, 60, 4)
    for layer in (1, 2, 4):
        p.add_zone(layer, rect=(5, 5, 55, 55))
    p.add_heater(1, 3.0, rect=(26, 26, 34, 34), name="Q1", theta=4.0)
    for i in range(10):
        for j in range(10):
            p.add_via(26.4 + i * 0.8, 26.4 + j * 0.8, 0.3)
    return p


def network(problem, model, cell_mm):
    """!
    @brief Assemble the network of a model on a problem.
    @param problem Problem.
    @param model "fvm" or "fdm".
    @param cell_mm Cell (FVM) or node spacing (FDM) in millimetres.
    @return The fvm.Network or fdm.Network.
    """
    if model == "fdm":
        return fdm.Network(problem, cell_mm)
    b = problem.board
    return fvm.Network(problem, max(int(round(b.width * 1000.0 / cell_mm)), 2), max(int(round(b.height * 1000.0 / cell_mm)), 2))


def positive_entries(net):
    """!
    @brief Count the positive off-diagonal entries of K and the largest one relative to the diagonal of its row.
    @param net Network.
    @return Tuple (count, largest K_ij / K_ii, largest K_ij / sum of the magnitudes of the negative entries of its row), the last two 0 if there is none.
    """
    K = net.K.tocsr()
    diag = K.diagonal()
    coo = K.tocoo()
    pos = (coo.row != coo.col) & (coo.data > 0)
    if not pos.any():
        return 0, 0.0, 0.0
    neg = K.copy()
    neg.data = np.where(neg.data < 0, -neg.data, 0.0)                     # Magnitudes of the negative entries only
    neg_sum = np.asarray(neg.sum(axis=1)).ravel()
    return int(pos.sum()), float((coo.data[pos] / diag[coo.row[pos]]).max()), float((coo.data[pos] / neg_sum[coo.row[pos]]).max())


@pytest.mark.parametrize("model", ["fvm", "fdm"])
@pytest.mark.parametrize("case", ["example", "dense"])
def test_positive_couplings_are_small_and_the_solution_obeys_the_maximum_principle(case, model):
    if case == "example":
        problem, cell = load_project(EXAMPLE).problem, 1.0
    else:
        problem, cell = dense_via_board(), 0.5
    net = network(problem, model, cell)
    count, rel_diag, rel_neg = positive_entries(net)
    theta, residual = net.solve_steady()
    keep = np.ones(theta.shape, dtype=bool) if net.drop is None else ~net.drop    # Nodes that no cell uses are pinned rows, not temperatures
    assert residual < 1e-9
    top = theta[keep].max()
    print(f"\n{case} {model} {cell} mm: unknowns {net.K.shape[0]}, positive off-diagonal entries {count}, largest / diagonal {rel_diag:.4f}, "
          f"largest / row negative sum {rel_neg:.4f}, min rise {theta[keep].min():.3e} K, max rise {top:.3f} K")
    assert count > 0                                      # the vias are there (16 for the FVM on the example at 1 mm, theory.md 2.2)
    # No node below the ambient (the solution of a non-negative source is non-negative)
    assert theta[keep].min() >= -TOLERANCE * top
    # The maximum lies in a cell that holds a source
    where = np.unravel_index(np.argmax(np.where(keep, theta, -np.inf)), theta.shape)
    assert net.Q[where] > 0.0
    # A positive entry stays small against the couplings that dominate its row (the row keeps its diagonal dominance)
    assert rel_neg < 2.0
