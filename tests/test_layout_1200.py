#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_layout_1200.py
@brief Pages that were cut in a 1200 x 800 window: the Power profile page has no horizontal scroll bar, the About box shows its last line, the chart legends do not cover the bars, the profile legend uses short model names.
"""

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


def test_the_power_profile_page_has_no_horizontal_scroll_bar_at_1200_x_800(qtbot, tmp_path):
    """!
    @brief The page stacks its two panes when the window is narrow, so the tab needs no horizontal scroll bar and the forms are not squeezed.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.resize(1200, 800)
    win.show()
    win.tabs.setCurrentIndex(2)
    qtbot.wait(150)
    area = win.tabs.currentWidget()
    assert isinstance(area, QScrollArea) and area.horizontalScrollBar().maximum() == 0
    page = win.profile_page
    assert page.minimumSizeHint().width() <= area.viewport().width()
    # Review of the branch: stacked, the waveform plot was squeezed to 10 px (constrained layout collapsed); it keeps a floor and the page scrolls down
    from pcbthermal.gui.profile_page import PLOT_MIN_PX
    assert page.canvas.height() >= PLOT_MIN_PX
    win.resize(2000, 1000)                                  # Wide again: side by side
    qtbot.wait(150)
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QSplitter
    splitters = [s for s in page.findChildren(QSplitter) if s.count() == 2]
    assert splitters and splitters[0].orientation() == Qt.Horizontal


def test_the_about_box_shows_its_whole_text(qtbot):
    """!
    @brief The label of the About box has the height its text needs at its width (the last line used to be cut).
    @param qtbot pytest-qt fixture.
    """
    from pcbthermal.gui.help import AboutDialog
    d = AboutDialog()
    qtbot.addWidget(d)
    d.show()
    qtbot.wait(50)
    assert d.text.height() >= d.text.heightForWidth(d.text.width())


def test_bar_legends_sit_beside_the_axes_and_the_profile_legend_uses_short_names():
    """!
    @brief The legend of the model and heater bar charts is outside the plot area; the legend of the cut curves says 'LPTN', never the key 'lumped'.
    """
    from matplotlib.figure import Figure
    from pcbthermal import plots
    from pcbthermal.results import MODEL_SHORT, short_name
    sim = simulate(example_board(), SolverOptions(models=("fvm", "lumped"), cell_mm=2.0))
    fig = Figure(layout="constrained")
    plots.draw_comparison(fig, sim.results)
    fig.canvas.draw()
    assert fig.legends and not fig.axes[0].get_legend()
    assert short_name("lumped") == "LPTN" and short_name("solid3d") == "3D solid" and set(MODEL_SHORT) == {"fvm", "lumped", "analytic", "fdm", "solid3d", "fem"}
    fig3 = Figure(layout="constrained")
    plots.draw_profile(fig3, sim.results, sim.problem, picture="off")
    texts = [t.get_text() for ax in fig3.axes for t in (ax.get_legend().get_texts() if ax.get_legend() else [])]
    assert "LPTN" in texts and "FVM" in texts and "lumped" not in texts
    fig2 = Figure(layout="constrained")
    plots.draw_bars(fig2, ["a", "b"], {"Tmax": [1.0, 2.0], "Tmean": [0.5, 1.0]})
    fig2.canvas.draw()
    assert fig2.legends
