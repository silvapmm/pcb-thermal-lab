#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_results_name_model.py
@brief The Components page, the chart title, the status line and summary.json name the reference model (an FDM-only or 3D-solid-only run is not the FVM), and the extra line does not push the chart off the page at 1200 x 800.
"""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QScrollArea

from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow
from pcbthermal.gui.results_view import ResultsView


def _window(qtbot, tmp_path):
    """!
    @brief A main window of 1200 x 800 with the example board.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return MainWindow.
    """
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.resize(1200, 800)
    win.show()
    return win


def test_the_line_is_hidden_before_a_run_and_names_the_model_after_it(qtbot):
    """!
    @brief No run, no line; after a run it is one line with the full name of the reference model, and the tooltip of the tables names the short one.
    @param qtbot pytest-qt fixture.
    """
    view = ResultsView()
    qtbot.addWidget(view)
    view.show()
    assert not view.reference_line.isVisible()
    view.set_simulation(simulate(example_board(), SolverOptions(models=("fdm",), cell_mm=2.0)))
    line = view.reference_line
    assert line.text() == "Reference model: Finite difference (FDM). Other models: the Models tab."
    assert "Model box of the maps does not change this page" in line.toolTip() and "(here: FDM)" in line.toolTip()
    assert view.heater_table.toolTip().startswith("Values of the reference model (FDM);")
    view.clear()
    assert not line.isVisible()


def test_the_chart_title_has_two_lines_and_names_the_model(qtbot):
    """!
    @brief The bar chart title keeps its first line and adds the short name of the reference model on a second line.
    @param qtbot pytest-qt fixture.
    """
    view = ResultsView()
    qtbot.addWidget(view)
    view.set_simulation(simulate(example_board(), SolverOptions(models=("solid3d",), cell_mm=2.0)))
    ax = view.comp_fig.axes[0]
    assert ax.get_title() == "Heater temperatures (column mean)\nReference model: 3D solid"


def test_components_page_fits_at_1200_x_800(qtbot, tmp_path):
    """!
    @brief With the line added there is no vertical scroll bar on the Components page, the chart is at least 180 px tall and the line is one line high.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    win = _window(qtbot, tmp_path)
    win._on_done(simulate(example_board(), SolverOptions(models=("fvm",), cell_mm=2.0)))
    res = win.results
    res.tabs.setCurrentIndex(4)
    qtbot.wait(200)
    page = res.tabs.currentWidget()
    area = page if isinstance(page, QScrollArea) else None
    assert area is None or area.verticalScrollBar().maximum() == 0
    assert res.comp_canvas.height() >= 180
    line = res.reference_line
    assert line.isVisible() and line.height() <= line.fontMetrics().lineSpacing() + 4


@pytest.mark.parametrize("model,short", [("fdm", "FDM"), ("fvm", "FVM"), ("solid3d", "3D solid")])
def test_dock_line_and_status_bar_start_with_done_and_the_model(qtbot, tmp_path, model, short):
    """!
    @brief The line under Run and the status bar both read 'Done: <model>, Tmax ...' (the prefix keeps the status bar rule).
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param model Model key that ran alone.
    @param short Its short name.
    """
    win = _window(qtbot, tmp_path)
    win._on_done(simulate(example_board(), SolverOptions(models=(model,), cell_mm=2.0)))
    want = f"Done: {short}, Tmax "
    assert win.solver_panel.status.text().startswith(want)
    assert win.statusBar().currentMessage().startswith(want)


def test_summary_json_holds_the_reference_model_key(tmp_path):
    """!
    @brief summary.json says which model is the reference: the key of the model (fdm for an FDM-only run, fvm when the FVM ran).
    @param tmp_path Temporary folder.
    """
    for models, key in ((("fdm",), "fdm"), (("fvm", "lumped"), "fvm")):
        sim = simulate(example_board(), SolverOptions(models=models, cell_mm=2.0))
        out = tmp_path / key
        sim.save(str(out), plots=False)
        assert json.loads((out / "summary.json").read_text(encoding="utf-8"))["reference_model"] == key
