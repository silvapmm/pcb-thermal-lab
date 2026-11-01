#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_lumped_footprint.py
@brief Tests of the footprint potentials of the Lumped model (block aggregation above 900 cells instead of a stride).
"""

import numpy as np
import pytest

from pcbthermal import lumped


def _old_potentials(cov, dx, dy, limit=900):
    """!
    @brief The footprint potentials as they were before the fix (every step-th cell in row order above the limit), kept as the reference.
    @param cov Footprint coverage (ny, nx).
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param limit Cells kept at most.
    @return Tuple (phi_mean, phi_boundary, phi_min).
    """
    idx = np.argwhere(cov > 0)
    w = cov[cov > 0]
    boundary = np.zeros(len(idx), dtype=bool)
    ny, nx = cov.shape
    for k, (i, j) in enumerate(idx):
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < ny and 0 <= b < nx and cov[a, b] == 0:
                boundary[k] = True
                break
    step = max(int(np.ceil(len(idx) / limit)), 1)
    src, sw = idx[::step], w[::step]
    pos = np.column_stack([src[:, 1] * dx, src[:, 0] * dy])
    d = np.hypot(pos[:, None, 0] - pos[None, :, 0], pos[:, None, 1] - pos[None, :, 1])
    np.fill_diagonal(d, 0.447 * np.sqrt(dx * dy) * (step ** 0.5))
    phi = (np.log(d) * sw[None, :]).sum(axis=1) / sw.sum()
    bnd = boundary[::step]
    phi_mean = float((phi * sw).sum() / sw.sum())
    return phi_mean, float(phi[bnd].mean()) if bnd.any() else phi_mean, float(phi.min())


def _exact_potentials(cov, dx, dy, chunk=500):
    """!
    @brief The potentials summed over every footprint cell (no decimation), in chunks of rows to bound the memory.
    @param cov Footprint coverage (ny, nx).
    @param dx Cell width in m.
    @param dy Cell height in m.
    @param chunk Rows of the distance matrix computed at a time.
    @return Tuple (phi_mean, phi_boundary, phi_min).
    """
    idx = np.argwhere(cov > 0)
    w = cov[cov > 0]
    pos = np.column_stack([idx[:, 1] * dx, idx[:, 0] * dy])
    foot = cov > 0
    pad = np.pad(foot, 1, constant_values=True)      # The board edge is adiabatic: not a boundary
    edge = ~pad[2:, 1:-1] | ~pad[:-2, 1:-1] | ~pad[1:-1, 2:] | ~pad[1:-1, :-2]
    bnd = (edge & foot)[cov > 0]
    phi = np.empty(len(idx))
    for s in range(0, len(idx), chunk):
        d = np.hypot(pos[s:s + chunk, None, 0] - pos[None, :, 0], pos[s:s + chunk, None, 1] - pos[None, :, 1])
        d[np.arange(d.shape[0]), np.arange(s, s + d.shape[0])] = 0.447 * np.sqrt(dx * dy)
        phi[s:s + chunk] = (np.log(d) * w[None, :]).sum(axis=1) / w.sum()
    return float((phi * w).sum() / w.sum()), float(phi[bnd].mean()), float(phi.min())


def _square(side_mm, cell_mm, margin=4):
    """!
    @brief Coverage array of a square footprint on a board a few cells larger.
    @param side_mm Side of the square in mm.
    @param cell_mm Cell size in mm.
    @param margin Cells of board around the square.
    @return Tuple (cov, cell size in m).
    """
    n = int(round(side_mm / cell_mm))
    cov = np.zeros((n + 2 * margin, n + 2 * margin))
    cov[margin:margin + n, margin:margin + n] = 1.0
    return cov, cell_mm * 1e-3


@pytest.mark.parametrize("side,cell", [(10, 1.0), (20, 1.0), (30, 1.0), (14, 0.5), (15, 0.5)])
def test_small_footprint_is_bit_identical(side, cell):
    """!
    @brief Up to 900 cells there is no decimation: the numbers equal the previous code bit for bit.
    @param side Side of the square in mm.
    @param cell Cell size in mm.
    @return None.
    """
    cov, d = _square(side, cell)
    assert (cov > 0).sum() <= 900
    assert lumped._footprint_potentials(cov, d, d) == _old_potentials(cov, d, d)


@pytest.mark.parametrize("side", [20, 30, 31])
def test_link_term_matches_exact_sum_at_half_millimetre(side):
    """!
    @brief The mean-to-boundary term (the link of the footprint to ring 1) is within 1 % of the sum over every cell, the peak term within 0.3 %.
    @param side Side of the square in mm.
    @return None.
    """
    cov, d = _square(side, 0.5)
    assert (cov > 0).sum() > 900
    new, ex = lumped._footprint_potentials(cov, d, d), _exact_potentials(cov, d, d)
    assert (new[1] - new[0]) == pytest.approx(ex[1] - ex[0], rel=0.01)
    assert (new[0] - new[2]) == pytest.approx(ex[0] - ex[2], rel=0.003)


def _shape(kind, cell_mm):
    """!
    @brief Coverage array of a footprint that is not a centred square: an L, a square ring (a hole), a rectangle of an odd number of cells, one cut by the board edge.
    @param kind "L", "ring", "odd" or "edge".
    @param cell_mm Cell size in mm.
    @return Tuple (cov, cell size in m).
    """
    n = int(round(1.0 / cell_mm))                 # cells per mm
    cov = np.zeros((60 * n, 60 * n))
    if kind == "L":
        cov[10 * n:50 * n, 10 * n:25 * n] = 1.0
        cov[10 * n:25 * n, 10 * n:50 * n] = 1.0
    elif kind == "ring":
        cov[10 * n:50 * n, 10 * n:50 * n] = 1.0
        cov[20 * n:40 * n, 20 * n:40 * n] = 0.0
    elif kind == "odd":
        cov[20 * n:20 * n + 20, 5 * n:5 * n + 51] = 1.0           # 20 x 51 cells: block centroids fall off the hot centre
    else:
        cov[10 * n:35 * n, 0:25 * n] = 1.0                       # touches the board edge (adiabatic there: not a boundary)
    return cov, cell_mm * 1e-3


@pytest.mark.parametrize("kind", ["L", "ring", "odd", "edge"])
def test_blocks_on_other_shapes(kind):
    """!
    @brief Above 900 cells, a footprint that is not convex, has a hole, has an odd number of cells or touches the board edge: both terms within 0.3 % of the sum over every cell.
    @details The minimum read at a block centroid (the first version of the fix) was 1.1 % short on the 20 x 51 rectangle and 1.3 % on the ring at 1 mm.
    @param kind Footprint kind of _shape.
    @return None.
    """
    for cell in (1.0, 0.5):
        cov, d = _shape(kind, cell)
        if (cov > 0).sum() <= 900:
            continue
        new, ex = lumped._footprint_potentials(cov, d, d), _exact_potentials(cov, d, d)
        assert (new[1] - new[0]) == pytest.approx(ex[1] - ex[0], rel=0.003)
        assert (new[0] - new[2]) == pytest.approx(ex[0] - ex[2], rel=0.003)


def test_no_jump_across_the_limit():
    """!
    @brief A 30 x 30 footprint (900 cells, every cell) and the same with one cell more (901, blocks) give terms within 0.1 % of each other's exact sums.
    @return None.
    """
    d = 0.5e-3
    for extra in (0, 1):
        cov = np.zeros((38, 38))
        cov[4:34, 4:34] = 1.0
        cov[34, 4:4 + extra] = 1.0
        new, ex = lumped._footprint_potentials(cov, d, d), _exact_potentials(cov, d, d)
        assert (new[1] - new[0]) == pytest.approx(ex[1] - ex[0], rel=0.001)
        assert (new[0] - new[2]) == pytest.approx(ex[0] - ex[2], rel=0.001)


def test_old_stride_failed_this_check():
    """!
    @brief The aliasing of the previous code is real: on a 30 mm square at 0.5 mm its link term is more than 5 % short.
    @return None.
    """
    cov, d = _square(30, 0.5)
    old, ex = _old_potentials(cov, d, d), _exact_potentials(cov, d, d)
    assert (old[1] - old[0]) < 0.95 * (ex[1] - ex[0])


def test_energy_balance_with_large_footprint():
    """!
    @brief A large heater on a board: the heat that leaves by the convective paths equals the power (Lumped).
    @return None.
    """
    from pcbthermal import Problem, SolverOptions, simulate
    p = Problem.new(80, 80, 2).add_zone(1, rect=(0, 0, 80, 80)).add_heater(1, 20.0, rect=(25, 25, 55, 55))
    r = simulate(p, SolverOptions(models=("lumped",), cell_mm=0.5)).results["lumped"]
    assert abs(r.balance_error) < 1e-9
