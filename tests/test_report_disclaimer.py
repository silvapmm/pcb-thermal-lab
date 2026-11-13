#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_report_disclaimer.py
@brief Every report writer carries the one shared disclaimer line, once.
"""

import json
import os

from pcbthermal import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.results import DISCLAIMER


def _sim():
    """!
    @brief Small run of the example board.
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=("fvm",), cell_mm=2.0))


def test_text_and_markdown_reports_carry_the_disclaimer_once():
    """!
    @brief The text report (also the on-screen summary), the on-screen variant and the Markdown report hold the line exactly once.
    """
    sim = _sim()
    for text in (sim.report(), sim.report(inline_warnings=False), sim.to_markdown()):
        assert text.count(DISCLAIMER) == 1
    assert "design aid" in DISCLAIMER and "measurement" in DISCLAIMER


def test_saved_files_carry_the_disclaimer(tmp_path):
    """!
    @brief report.txt and summary.json written by save() hold it.
    @param tmp_path Pytest temporary folder.
    """
    sim = _sim()
    sim.save(str(tmp_path), plots=False)
    assert (tmp_path / "report.txt").read_text(encoding="utf-8").count(DISCLAIMER) == 1
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))["disclaimer"] == DISCLAIMER


def test_computed_h_note_and_disclaimer_are_separate_lines():
    """!
    @brief A computed-h run keeps the convection note and still has one disclaimer.
    """
    p = example_board()
    p.board.h_mode = "computed"
    sim = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))
    from pcbthermal.api import CONVECTION_NOT_MEASURED_NOTE
    assert sim.report().count(DISCLAIMER) == 1 and CONVECTION_NOT_MEASURED_NOTE in sim.report()


def test_calculator_source_uses_the_shared_constant():
    """!
    @brief The Power Calculator window shows the shared constant, not its own wording.
    """
    here = os.path.dirname(os.path.dirname(__file__))
    src = open(os.path.join(here, "pcbthermal", "gui", "calculator.py"), encoding="utf-8").read()
    assert "DISCLAIMER" in src and "design aid" not in src
