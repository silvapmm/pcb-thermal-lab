#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_reduced_warning_text.py
@brief The imported-copper texts: the reduced-model warning quotes the measured sample and its cause, the cell warning of a small part never recommends a cell that Auto cannot give,
       and check_input works with live and ui together.
@details The numbers quoted are those of the study `research/reduced-models-imported-passives` (README 3.2 and 3.3): 42 parts of three boards, Lumped 25 to 82 % and Analytic 17 to 77 %
         too cool at 0.5 mm, 39 to 81 % for the 0402 class; a 0402 reads 84.6 K at a 1 mm cell and 201.2 K at 0.25 mm (2.4 times).
"""

import numpy as np

from pcbthermal import Problem, checks, copper


def _board(side_mm):
    """!
    @brief A 30 mm two-layer board with imported stripes and one powered part of the given side.
    @param side_mm Side of the square part in mm.
    @return Problem.
    """
    p = Problem.new(30, 30, 2)
    p.add_heater(1, 1.0, rect=(12, 12, 12 + side_mm, 12 + side_mm), name="C3")
    n = 300
    stripes = np.zeros((n, n), np.uint8)
    stripes[:, ::20] = 255
    p.imported = copper.imported_from_rasters([stripes, stripes], 0.1, "faces")
    return p


def _part_texts(p, cell, ui="gui"):
    """!
    @brief The texts of the 'smallest side' warning of the part C3 at a cell.
    @param p Problem.
    @param cell Cell in mm.
    @param ui 'gui' or 'cli'.
    @return list of (full text, short line).
    """
    return [(str(w), checks.line(w)) for w in checks.check_input(p, ("fvm",), cell, ui=ui) if "smallest side" in str(w)]


def test_reduced_model_warning_states_cause_and_sample():
    """!
    @brief The text names the cause (cell average, pads and necks invisible), the measured ranges, 'a sample, not a bound', and who reads the copper; no internal names.
    @return None.
    """
    w = copper.REDUCED_MODEL_WARNING
    for part in ("average over a cell", "invisible", "42 parts", "three imported boards", "25 to 82 %", "17 to 77 %", "39 to 81 %", "0402",
                 "a sample, not a bound", "FVM, FDM and 3D solid do read", "finite-volume model for the result"):
        assert part in w, part
    for old in ("27 to 42", "17 to 35", "24 windows", "RP2040"):
        assert old not in w, old
    for name in ("research/", "fix/", "feature/"):
        assert name not in w


def test_small_part_cell_note_numbers():
    """!
    @brief The example quoted for a typed coarse cell is the C3 pair of the study (84.6 K and 201 K, ratio 2.4).
    @return None.
    """
    assert round(201.2 / 84.6, 1) == 2.4
    t = copper.SMALL_PART_CELL_NOTE_TEXT
    assert "84.6 K" in t and "201 K" in t and "2.4 times" in t and "one part" in t and "not a bound" in t
    assert t in copper.coarse_cell_warning("gui")


def test_cell_recommendation_respects_the_auto_floor():
    """!
    @brief For a 0.65 mm part on imported copper the cell recommended is 0.25 mm (not 0.16 mm), the coarse-cell example is added from 1 mm, and at 0.25 mm the text asks for care.
    @return None.
    """
    p = _board(0.65)
    full, short = _part_texts(p, 1.0)[0]
    assert "0.25 mm" in full and "0.16" not in full and "2.4 times" in full and "Auto button" in full and "--" not in full
    assert "0.25 mm" in short
    full, _ = _part_texts(p, 0.5)[0]
    assert "0.25 mm" in full and "2.4 times" not in full
    full, _ = _part_texts(p, 0.25)[0]
    assert "finest cell" in full and "0.16" not in full and "use a cell size" not in full
    # A drawn board keeps the plain rule (a quarter of the side)
    q = Problem.new(30, 30, 2)
    q.add_heater(1, 1.0, rect=(12, 12, 12.65, 12.65))
    assert "0.16 mm or less" in _part_texts(q, 1.0)[0][0]
    # The command line names its own option
    assert "--cell-mm" in _part_texts(p, 1.0, ui="cli")[0][0]


def test_check_input_live_and_ui_together():
    """!
    @brief check_input(problem, models, live=True, ui='gui') runs and gives the same warnings as live=False for a board without a via pass; the window never reads a flag.
    @return None.
    """
    p = _board(0.65)
    live = checks.check_input(p, ("fvm", "lumped"), 1.0, live=True, ui="gui")
    full = checks.check_input(p, ("fvm", "lumped"), 1.0, live=False, ui="gui")
    assert [str(w) for w in live] == [str(w) for w in full]
    assert all("--" not in str(w) and "--" not in checks.line(w) for w in live)
    assert any("smallest side" in str(w) for w in live)
