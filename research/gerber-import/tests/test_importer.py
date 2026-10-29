"""!
@file test_importer.py
@brief The import of a Gerber set on our own board (phase 1): the box, the copper mask, the plated holes with their net and kind, and the warning for an aperture thinner than the pixel; no program needed.
"""

import numpy as np

import importer
import our_board


def board(tmp_path, pix=0.1):
    """!
    @brief Import our IC board from files written to a temporary folder.
    @param tmp_path pytest temp dir.
    @param pix Pixel (mm).
    @return ImportedBoard.
    """
    g, d = our_board.write(tmp_path)
    return importer.import_board({"copper": [g], "outline": None, "drills": [d]}, pix=pix, cell=1.0, box=(0.0, 0.0, our_board.SIZE, our_board.SIZE))


def test_import_reads_the_box_the_copper_and_the_holes(tmp_path):
    """!
    @brief One copper layer on a 40 x 40 mm box, 16 plated holes (8 vias, 8 component holes), copper near 10 % of the board and a coverage mask that keeps the area of the binary one within 2 %.
    @param tmp_path pytest temp dir.
    @return None.
    """
    ib = board(tmp_path)
    assert len(ib.layers) == 1 and (ib.width, ib.height) == (40.0, 40.0)
    assert len(ib.holes) == 16 and {r["kind"] for r in ib.holes} == {"via", "component"}
    binary, cover = ib.layers[0]["binary"], ib.layers[0]["coverage"]
    assert binary.shape == (400, 400) and 0.08 < binary.mean() < 0.13
    assert abs(cover.sum() / binary.sum() - 1) < 0.02


def test_a_pixel_wider_than_the_thinnest_track_is_warned_about(tmp_path):
    """!
    @brief The board has 0.2 mm tracks: a 0.1 mm pixel raises no warning, a 0.5 mm pixel does.
    @param tmp_path pytest temp dir.
    @return None.
    """
    assert not board(tmp_path, 0.1).warnings
    assert any("thinnest aperture" in w for w in board(tmp_path, 0.5).warnings)
