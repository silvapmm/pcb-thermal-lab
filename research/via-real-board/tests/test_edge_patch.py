#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_edge_patch.py
@brief Tests of the patched network (`lib/edge_patch.py`): identity with the options off, vias as pure couplings, symmetry, `gz_via` for the Lumped model, walls, and the image only where a wall is near.
"""

import math
import os
import sys

import numpy as np
import pytest

LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
sys.path.insert(0, LIB)

import edge_patch as ep                                                     # noqa: E402
import edge_reference as er                                                 # noqa: E402
import matrix_stats as ms                                                   # noqa: E402
import program_cases as pc                                                  # noqa: E402
import program_patch as pp                                                  # noqa: E402
import runs                                                                 # noqa: E402
from pcbthermal import fvm                                                  # noqa: E402
from pcbthermal.examples import example_board                               # noqa: E402

ETA = math.exp(-0.25)


@pytest.fixture(autouse=True)
def libraries():
    """!@brief Load the shipped libraries so that the boards behave as in the application."""
    pc.load_libraries()


def _grid(problem, cell_mm):
    """!
    @brief Cells of a problem for a cell size.
    @param problem A Problem.
    @param cell_mm Cell in mm.
    @return tuple (nx, ny).
    """
    return int(round(problem.board.width * 1000.0 / cell_mm)), int(round(problem.board.height * 1000.0 / cell_mm))


def test_options_off_reproduce_the_prototype_matrix_bit_for_bit():
    """!@brief With board_only, fold and image off the hook builds the same matrix as program_patch's mw_disc."""
    p = pc.array_board()
    nx, ny = _grid(p, 0.5)
    with pp.patched("mw_disc", eta=ETA):
        ref = fvm.Network(p, nx, ny).K
    with ep.patched_edge(**runs.MW_PROTOTYPE):
        new = fvm.Network(p, nx, ny).K
    assert abs(ref - new).max() == 0.0


def test_vias_are_pure_couplings_symmetric_with_zero_row_sum():
    """!@brief The matrix of a board with vias minus the matrix of the same board without them is symmetric and has zero row sums (no heat created or lost by the vias)."""
    p = pc.array_board()
    nx, ny = _grid(p, 0.5)
    with ep.patched_edge(**runs.MW_BOARD):
        k1 = fvm.Network(p, nx, ny).K
    k0 = fvm.Network(runs.without_vias(p), nx, ny).K
    d = (k1 - k0).tocsr()
    assert abs(d - d.T).max() < 1e-9 * abs(k1).max()
    assert np.abs(np.asarray(d.sum(axis=1))).max() < 1e-9 * abs(k1).max()


def test_gz_via_is_the_programs_own_via_term():
    """!@brief gz + gz_via of the patched network equals the gz of the program, so the Lumped model sees the same vias as today; the patched gz alone has none of them."""
    p = example_board()
    nx, ny = _grid(p, 1.0)
    old = fvm.Network(p, nx, ny, assemble=False)
    with ep.patched_edge(**runs.MW_BOARD):
        new = fvm.Network(p, nx, ny, assemble=False)
    assert np.abs(old.gz - (new.gz + new.gz_via)).max() == 0.0
    assert np.abs(new.gz - old.gz).max() > 0.0


def test_gz_via_matches_on_vias_that_sit_on_cell_lines():
    """!@brief Regression (first run of study_lumped_gzvia.py: 1.7e-2 W/K off on the own via field): the vias of an array that fall exactly on a cell line go to the same cell as in the program."""
    import real_board as rbd
    holes, w, h = rbd.own_via_field(10)
    p = rbd.problem_from_holes(holes, w, h, layers=4)
    nx, ny = _grid(p, 1.0)
    old = fvm.Network(p, nx, ny, assemble=False)
    with ep.patched_edge(**runs.MW_BOARD):
        new = fvm.Network(p, nx, ny, assemble=False)
    assert np.abs(old.gz - (new.gz + new.gz_via)).max() == 0.0


def test_a_via_far_from_every_wall_is_not_changed_by_the_image():
    """!@brief The 3 x 3 array board has its vias far from the edges: the image option leaves the matrix identical and counts no edge via."""
    p = pc.array_board()
    nx, ny = _grid(p, 0.5)
    with ep.patched_edge(**runs.MW_BOARD):
        a = fvm.Network(p, nx, ny).K
    with ep.patched_edge(**runs.MW_IMAGE):
        b = fvm.Network(p, nx, ny).K
        assert ep.STATS["edge_vias"] == 0
    assert abs(a - b).max() == 0.0


def test_a_via_near_the_edge_gets_a_different_well():
    """!@brief A via 0.16 mm from the edge of the 10 mm board: the image changes the matrix and is counted."""
    p = er.edge_board(0.16)
    nx, ny = _grid(p, 1.0)
    with ep.patched_edge(**runs.MW_BOARD):
        a = fvm.Network(p, nx, ny).K
    with ep.patched_edge(**runs.MW_IMAGE):
        b = fvm.Network(p, nx, ny).K
        assert ep.STATS["edge_vias"] == 1
    assert abs(a - b).max() > 0.0


def test_walls_for_a_box_and_an_outline():
    """!@brief walls_for returns the nearest box edge per axis within reach, and for an outline only the axis-parallel segments."""
    p = er.edge_board(0.3)
    v = p.vias[0]
    walls = ep.walls_for(p, v, 2e-3)
    assert walls == [("x", p.board.width)]
    assert ep.walls_for(p, v, 0.1e-3) == []
    q = er.edge_board(0.3, x_cut_mm=7.0)
    assert ep.walls_for(q, q.vias[0], 2e-3) == [("x", pytest.approx(7e-3))]


def test_options_are_restored_and_unknown_options_refused():
    """!@brief The module options return to their defaults after the context, and a misspelt option raises."""
    before = dict(ep.OPTS)
    with ep.patched_edge(image=False):
        assert ep.OPTS["image"] is False
    assert ep.OPTS == before
    with pytest.raises(KeyError):
        with ep.patched_edge(imge=True):
            pass


def test_a_board_without_vias_is_unchanged_by_the_patch():
    """!@brief No vias, no change: the patched and the original matrices are identical."""
    p = runs.without_vias(pc.array_board())
    nx, ny = _grid(p, 1.0)
    k0 = fvm.Network(p, nx, ny).K
    with ep.patched_edge(**runs.MW_IMAGE):
        k1 = fvm.Network(p, nx, ny).K
    assert abs(k0 - k1).max() == 0.0


def test_reference_cut_must_lie_on_the_fine_grid():
    """!@brief Regression (the first run of study_edge_outline.py crashed on a cut at 7.03125 mm): the reference refuses a cut the 1/16 mm grid cannot represent, and the defaults of the study are on it."""
    q = er.edge_board(0.5, x_cut_mm=7.03125)
    with pytest.raises(ValueError):
        er.reference_rise(q, 1.0 / 16.0, True, 7.03125)
    sys.path.insert(0, os.path.join(os.path.dirname(LIB), "scripts"))
    import study_edge_outline as so
    assert all(abs(c * 16 - round(c * 16)) < 1e-9 for c in so.DEFAULT_CUTS)


def test_block_structure_counts_overlapping_footprints_as_one_block():
    """!@brief Two vias one cell apart merge into one block; two far apart stay two (the structure the block SOR depends on)."""
    from pcbthermal import Problem
    p = Problem.new(10, 10, 2, 1.6, 35.0, h_top=10.0, h_bottom=10.0)
    for layer in (1, 2):
        p.add_zone(layer, rect=(0, 0, 10, 10))
    p.add_heater(1, 1.0, rect=(4, 4, 6, 6))
    p.add_via(2.0, 2.0, 0.3)
    p.add_via(2.5, 2.0, 0.3)
    p.add_via(8.0, 8.0, 0.3)
    net = ms.build(p, 0.5, "mw", board_only=True, image=False)
    assert ms.block_structure(net)["blocks"] == 2
