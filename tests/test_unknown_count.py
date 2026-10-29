"""!
@file test_unknown_count.py
@brief The number of unknowns shown next to the cell size is the number the models really have.
@details The panel counted nx x ny x copper layers; a one-layer board has laminate nodes under the copper and a metal block adds a layer, so the
         shown number was too small (2400 shown for 9600 on a one-layer board of 60 x 40 mm at 1 mm with a block).
"""

import pytest

from pcbthermal import Problem, fdm, fvm
from pcbthermal.examples import example_block_board, example_board


def one_layer_with_block():
    """!
    @brief A one-layer 60 x 40 mm board with a metal block on its face.
    @return Problem.
    """
    p = Problem.new(60, 40, 1).add_full_copper()
    p.add_heater(1, 1.0, rect=(25, 15, 35, 25))
    p.add_heatsink(1, 10.0, rect=(20, 10, 40, 30), thickness_mm=3.0)
    return p


def boards():
    """!
    @brief Boards that exercise every kind of layer: plain, laminate nodes, one block, two block faces.
    @return List of (name, Problem).
    """
    two_faces = example_board()
    two_faces.add_heatsink(1, 10.0, rect=(10, 10, 30, 30), thickness_mm=2.0)
    two_faces.add_heatsink(4, 10.0, rect=(50, 20, 80, 50), thickness_mm=2.0)
    return [("two layers", Problem.new(60, 40, 2).add_full_copper()), ("one layer", Problem.new(60, 40, 1).add_full_copper()),
            ("one layer, block", one_layer_with_block()), ("example", example_board()), ("example, bottom block", example_block_board()),
            ("example, two block faces", two_faces)]


@pytest.mark.parametrize("cell", [1.0, 2.0, 2.5])
def test_fvm_count_equals_the_unknowns_of_the_network(cell):
    for name, p in boards():
        n, layers, nx, ny = fvm.unknowns(p, cell)
        net = fvm.Network(p, nx, ny)
        assert layers == net.nl, name
        assert n == net.nl * net.nx * net.ny, name


@pytest.mark.parametrize("cell", [1.0, 2.0, 2.5])
def test_fdm_count_equals_the_unknowns_of_the_network(cell):
    for name, p in boards():
        n, layers, nx, ny = fdm.unknowns(p, cell)
        net = fdm.Network(p, cell)
        assert layers == net.nl, name
        assert n == net.nl * net.nx * net.ny, name


def test_the_old_count_missed_three_quarters_of_a_one_layer_board_with_a_block():
    p = one_layer_with_block()
    old = max(int(round(p.board.width * 1000 / 1.0)), 2) * max(int(round(p.board.height * 1000 / 1.0)), 2) * p.board.layers
    assert old == 2400
    assert fvm.unknowns(p, 1.0)[0] > 2 * old                   # Copper node, the laminate nodes and the block layer
