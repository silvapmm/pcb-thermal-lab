#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_maximum_principle.py
@brief The via couplings put positive off-diagonal entries into K (docs/theory.md 2.2): how many, how large, and where the solution keeps or loses the maximum principle.

@details A thermal matrix without vias is an M-matrix (non-positive off-diagonal entries), whose solution for non-negative sources is non-negative and has no
         interior minimum below its surroundings. The Kron-reduced via barrels add couplings with zero row sum and positive entries between the cells of one
         footprint on one plane (the via takes heat from each cell in proportion to its weight times the difference of the plane MEANS), so K is no longer an
         M-matrix and the principle is not proved. The check used here is local, because the global minimum of a board lies far from its vias and would hide a
         cold spot: on every plane, inside a window around the vias, no temperature may lie below the lowest temperature on the edge of the window (a cold spot
         under a via has no physical cause: no sink is there).
         - On copper that covers the footprints (the example board at 1 mm, a dense 10 x 10 array of 0.3 mm vias at 0.5 and 0.25 mm) the field has no cold spot.
         - Where the copper of a plane covers only part of a footprint (a copper edge through the via, a part on bare laminate over a via) the fixed weights take
           heat from cells that cannot supply it, and the FVM shows a cold spot of 8 to 14 K at 0.5 to 0.25 mm on a 2 W part (tens of K, even below the ambient,
           in the reviewer's sweeps); that limit is recorded in docs/theory.md 2.2 and is tested below as a strict expected failure, so that a correction of the
           via weights must update this test.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

from pcbthermal import Problem, fdm, fvm
from pcbthermal.project import load_project

EXAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples", "example_board.pcbt.json")
TOLERANCE = 1e-9                                         # Fraction of the maximum rise allowed as a cold spot (round-off of the direct solve)


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


def copper_edge_board():
    """!
    @brief A two-layer 30 x 30 mm board, h = 10 W/m2K, with the edge of the top copper through a 0.3 mm via and a 2 W, 3 x 3 mm part beside it on that edge.
    @return Problem.
    """
    p = Problem.new(30, 30, 2, h_top=10.0, h_bottom=10.0)
    p.add_zone(2, rect=(1, 1, 29, 29))
    p.add_zone(1, rect=(5, 5, 15.0, 25))                 # The copper ends at x = 15 mm, the centre of the via
    p.add_heater(1, 2.0, rect=(12.0, 13.5, 15.0, 16.5), name="Q")
    p.add_via(15.0, 15.0, 0.3)
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


def cold_spot(problem, net, theta, margin_mm=1.0):
    """!
    @brief The deepest cold spot around the vias: on each plane, the lowest temperature inside the box of the via centres enlarged by a margin, minus the lowest
           temperature on the edge of that box (0 or more when the field has no interior minimum there).
    @param problem Problem (its vias give the box).
    @param net Network (FVM cells are centred, FDM nodes lie on the grid lines).
    @param theta Temperature rise, array (planes, ny, nx), in K.
    @param margin_mm Margin around the via centres in mm.
    @return float Deepest cold spot in K (negative: a cold spot).
    """
    _, ny, nx = theta.shape
    b = problem.board
    if isinstance(net, fdm.Network):
        xs, ys = np.arange(nx) * b.width / (nx - 1), np.arange(ny) * b.height / (ny - 1)
    else:
        xs, ys = (np.arange(nx) + 0.5) * b.width / nx, (np.arange(ny) + 0.5) * b.height / ny
    vx = np.array([v.x for v in problem.vias])
    vy = np.array([v.y for v in problem.vias])
    m = margin_mm * 1e-3
    ix = (xs >= vx.min() - m) & (xs <= vx.max() + m)
    iy = (ys >= vy.min() - m) & (ys <= vy.max() + m)
    worst = np.inf
    for plane in theta:
        w = plane[np.ix_(iy, ix)]
        edge = np.concatenate([w[0], w[-1], w[:, 0], w[:, -1]])
        worst = min(worst, float(w.min() - edge.min()))
    return worst


@pytest.mark.parametrize("model", ["fvm", "fdm"])
@pytest.mark.parametrize("case", ["example", "dense", "dense fine"])
def test_positive_couplings_and_no_cold_spot_on_copper(case, model):
    if case == "example":
        problem, cell = load_project(EXAMPLE).problem, 1.0
    else:
        problem, cell = dense_via_board(), (0.5 if case == "dense" else 0.25)
    net = network(problem, model, cell)
    count, rel_diag, rel_neg = positive_entries(net)
    theta, residual = net.solve_steady()
    keep = np.ones(theta.shape, dtype=bool) if net.drop is None else ~net.drop    # Nodes that no cell uses are pinned rows, not temperatures
    assert residual < 1e-9
    top = theta[keep].max()
    spot = cold_spot(problem, net, theta)
    print(f"\n{case} {model} {cell} mm: unknowns {net.K.shape[0]}, positive off-diagonal entries {count}, largest / diagonal {rel_diag:.4f}, "
          f"largest / row negative sum {rel_neg:.4f}, min rise {theta[keep].min():.3e} K, max rise {top:.3f} K, deepest cold spot {spot:+.3e} K")
    assert count > 0                                      # the vias are there (16 for the FVM on the example at 1 mm, theory.md 2.2)
    assert theta[keep].min() >= -TOLERANCE * top           # no node below the ambient
    assert spot >= -TOLERANCE * top                        # and no cold spot around the vias
    where = np.unravel_index(np.argmax(np.where(keep, theta, -np.inf)), theta.shape)
    assert net.Q[where] > 0.0                              # the maximum lies in a cell that holds a source


@pytest.mark.parametrize("cell", [0.5, 0.25])
@pytest.mark.xfail(strict=True, reason="known limit (docs/theory.md 2.2): fixed footprint weights on a plane whose copper covers only part of the footprint "
                                       "make a cold spot under the via")
def test_no_cold_spot_where_the_copper_ends_inside_a_footprint(cell):
    problem = copper_edge_board()
    net = network(problem, "fvm", cell)
    theta, _ = net.solve_steady()
    spot = cold_spot(problem, net, theta)
    print(f"\ncopper edge fvm {cell} mm: deepest cold spot {spot:+.3f} K, max rise {theta.max():.3f} K")
    assert spot >= -TOLERANCE * theta.max()
