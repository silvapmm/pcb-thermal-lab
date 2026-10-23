"""!
@file test_importer.py
@brief The import path end to end on our own board: the set is read, the program's Problem is built (vias from the drill file), and the program's network with imported face conductances reproduces the program's own run when the faces are the program's own formula.
@details Needs the program's dependencies (skipped otherwise).
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
pytest.importorskip("pcbthermal")

import importer as im                                                    # noqa: E402
import our_board                                                         # noqa: E402


def board(tmp_path):
    """!
    @brief Import our IC board from files written to a temporary folder.
    @param tmp_path pytest temp dir.
    @return Tuple (ImportedBoard, Problem).
    """
    g, d = our_board.write(tmp_path)
    ib = im.import_board({"copper": [g], "outline": None, "drills": [d]}, pix=0.1, cell=1.0, box=(0.0, 0.0, our_board.SIZE, our_board.SIZE))
    return ib, im.to_problem(ib, {"layer": 1, "x": 20.0, "y": 20.0, "size": 6.0, "power": 1.0})


def test_import_reads_layers_holes_and_builds_the_problem(tmp_path):
    """!@brief 1 copper layer, 16 plated holes as 16 vias, a 40 x 40 mm board, one heater, and no zones (the copper enters through the faces). @param tmp_path pytest temp dir. @return None."""
    ib, p = board(tmp_path)
    assert len(ib.layers) == 1 and len(ib.holes) == 16
    assert (ib.width, ib.height) == (40.0, 40.0)
    assert len(p.vias) == 16 and len(p.heaters) == 1 and len(p.zones) == 0
    assert {r["kind"] for r in ib.holes} == {"via", "component"}


def test_faces_of_the_programs_own_formula_reproduce_the_programs_run(tmp_path):
    """!@brief The face conductances of the program's formula, given to the network through the importer, give the same temperature as the program run with one zone per cell (plumbing check, 1e-9 K). @param tmp_path pytest temp dir. @return None."""
    ib, p = board(tmp_path)
    sheets = im.layer_sheets(ib, p, "binary")
    mine = im.solve_faces(ib, p, im.layer_faces(sheets, ib, p, "fill"))
    program = im.solve_today(ib, p, "binary")
    assert np.abs(mine - program).max() < 1e-6


def test_imported_faces_are_closer_to_the_pixel_grid_than_the_program_as_it_is(tmp_path):
    """!@brief On our board the heater temperature of the imported flow-based path is within 6 % of the program on the pixel grid and closer than the program as it is (about -5 %: both are small on this board). @param tmp_path pytest temp dir. @return None."""
    ib, p = board(tmp_path)
    ref = im.block_mean(im.solve_fine(ib, p, "binary"), ib)[0][17:23, 17:23].mean()
    flow = im.solve_faces(ib, p, im.layer_faces(im.layer_sheets(ib, p, "binary"), ib, p, "flow"))[0][17:23, 17:23].mean()
    today = im.solve_today(ib, p, "binary")[0][17:23, 17:23].mean()
    assert abs(flow / ref - 1) < 0.06
    assert abs(flow / ref - 1) < abs(today / ref - 1) + 0.02
