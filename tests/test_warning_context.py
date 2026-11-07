#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_warning_context.py
@brief The warnings name the controls of the front end that launched the run: the window never reads a flag of the command line, the command line never reads a dock.
@details The text of a message is built from one source string and the place to change a setting comes from `pcbthermal.uicontext` (`check_input(..., ui=)`,
         `SolverOptions.ui`); this scans every text of a board that raises the cell-size and laminate sentences for both contexts.
"""

import re

import numpy as np
import pytest

from pcbthermal import Problem, SolverOptions, checks, copper, simulate, uicontext


def _board():
    """!
    @brief A 30 mm two-layer board with a small part, a via array under it, a lone via and imported copper stripes.
    @return Problem.
    """
    p = Problem.new(30, 30, 2)
    p.add_heater(1, 1.0, rect=(12, 12, 14, 14), name="U")
    p.add_via(3, 27)
    for x in (12.5, 13.0, 13.5):
        for y in (12.5, 13.0, 13.5):
            p.add_via(x, y)
    n = 300
    stripes = np.zeros((n, n), np.uint8)
    stripes[:, ::20] = 255
    stripes[:, 1::20] = 255
    p.imported = copper.imported_from_rasters([stripes, stripes], 0.1, "faces")
    return p


def _all_texts(ui):
    """!
    @brief Every warning text (full and one-line) of the live checks and of a run launched from a front end.
    @param ui 'gui' or 'cli'.
    @return List of strings.
    """
    p = _board()
    models = ("fvm", "fdm", "lumped", "analytic")
    texts = []
    for cell in (1.0, 2.0, 4.0):
        for w in checks.check_input(p, models, cell, ui=ui):
            texts += [str(w), checks.line(w)]
    sim = simulate(p, SolverOptions(models=models, cell_mm=2.0, ui=ui))
    texts += [str(w) for w in sim.warnings]
    texts.append(copper.coarse_cell_warning(ui))
    assert uicontext.current() == "cli"                           # the context is restored after the calls
    return texts


def test_gui_texts_name_no_command_line_flag():
    """!
    @brief A run and a live check launched from the window never name a flag of the command line.
    @return None.
    """
    texts = _all_texts("gui")
    assert any("Simulation settings" in t for t in texts)         # the sentence for the window is there
    bad = [t for t in texts if re.search(r"(^|[\s(])--[a-z]", t)]
    assert not bad, bad[0]


def test_cli_texts_name_no_window_control():
    """!
    @brief The same checks for the command line and the API never name a dock or a button of the window.
    @return None.
    """
    texts = _all_texts("cli")
    assert any("--cell-mm" in t for t in texts)
    bad = [t for t in texts if re.search(r"Simulation settings|Auto button|Laminate sub-gap", t)]
    assert not bad, bad[0]


def test_laminate_sentence_follows_the_context():
    """!
    @brief The laminate setting is named 'Laminate sub-gap' in the window and --laminate-s-max-mm on the command line.
    @return None.
    """
    assert uicontext.laminate_where("sub-gap", "gui") == "'Laminate sub-gap'"
    assert uicontext.laminate_where("sub-gaps", "cli") == "--laminate-n-max"
    with uicontext.using_ui("gui"):
        assert uicontext.current() == "gui"
        with uicontext.using_ui(None):
            assert uicontext.current() == "gui"
    assert uicontext.current() == "cli"


def test_ui_option_is_not_saved_and_is_validated():
    """!
    @brief The front end is a session property: not written in a project and refused when unknown.
    @return None.
    """
    assert "ui" not in SolverOptions(ui="gui").to_dict()
    assert SolverOptions.from_dict({"ui": "gui"}).ui == "cli"
    with pytest.raises(ValueError):
        SolverOptions(ui="web").validate()
