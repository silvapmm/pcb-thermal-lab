#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_ui_cleanup.py
@brief Small interface fixes: model names on the comparison plot, ticks of a very long log axis, the inner tab bar of the results, the size of Preferences.
"""

from types import SimpleNamespace

import numpy as np
from matplotlib.figure import Figure
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication

from pcbthermal import plots
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow
from pcbthermal.gui.preferences import PreferencesDialog


def test_the_comparison_plot_writes_the_names_of_the_models_not_their_keys():
    fig = Figure()
    results = {k: SimpleNamespace(t_max=80.0 + i, t_mean=50.0 + i) for i, k in enumerate(("fvm", "lumped", "analytic", "fdm", "solid3d"))}
    plots.draw_comparison(fig, results)
    labels = [t.get_text() for t in fig.axes[0].get_xticklabels()]
    assert labels == ["FVM", "Lumped (LPTN)", "Analytic", "FDM", "3D solid"]


def test_a_log_axis_of_more_than_six_decades_gets_a_tick_every_three_decades():
    fig = Figure()
    ax = fig.add_subplot(111)
    ax.set_xscale("log")
    ax.plot([1e-6, 1e3], [0.0, 1.0])
    plots.engineering_ticks(fig)
    fig.canvas.draw()
    ticks = [t for t in ax.get_xticks() if 1e-6 * 0.99 <= t <= 1e3 * 1.01]
    assert len(ticks) <= 4
    assert all(abs(np.log10(t) / 3.0 - round(np.log10(t) / 3.0)) < 1e-9 for t in ticks)     # Powers of 1000: 1E-6, 1E-3, 1, 1E3


def test_a_short_log_axis_keeps_a_tick_per_decade():
    fig = Figure()
    ax = fig.add_subplot(111)
    ax.set_xscale("log")
    ax.plot([0.1, 600.0], [0.0, 1.0])
    plots.engineering_ticks(fig)
    fig.canvas.draw()
    assert len([t for t in ax.get_xticks() if 0.1 * 0.99 <= t <= 600]) >= 4


def test_the_results_tab_bar_keeps_whole_names_and_scrolls(qtbot, tmp_path):
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    assert win.results.tabs.tabBar().elideMode() == Qt.ElideNone
    assert win.results.tabs.tabBar().usesScrollButtons()


def test_preferences_open_wide_enough_for_the_list_and_the_widest_page(qtbot):
    d = PreferencesDialog()
    qtbot.addWidget(d)
    assert d.width() >= 960


def _window(qtbot, tmp_path):
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.show()
    return win


def test_a_comma_pasted_from_the_context_menu_is_read_as_a_point(qtbot, monkeypatch):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QContextMenuEvent, QGuiApplication
    from PySide6.QtWidgets import QDoubleSpinBox

    from pcbthermal.gui import theme

    theme.fix_number_locale()
    spin = QDoubleSpinBox()
    spin.setRange(0, 100)
    spin.setDecimals(3)
    qtbot.addWidget(spin)
    spin.show()
    QGuiApplication.clipboard().setText("0,45")
    spin.lineEdit().selectAll()

    def click_paste(menu, _pos):
        # Stand-in for the user choosing Paste in the menu
        next(a for a in menu.actions() if "Paste" in a.text()).trigger()

    monkeypatch.setattr(theme, "_show_menu", click_paste)
    ev = QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(2, 2), QPoint(2, 2))
    QApplication.sendEvent(spin.lineEdit(), ev)
    assert spin.lineEdit().text() == "0.45"
    assert abs(spin.value() - 0.45) < 1e-12


def test_a_stale_warning_list_ignores_clicks_until_the_next_check(qtbot):
    from pcbthermal.checks import CheckWarning
    from pcbthermal.gui.panels import WarningList

    w = WarningList()
    qtbot.addWidget(w)
    got = []
    w.warning_clicked.connect(lambda k, i: got.append((k, i)))
    cw = CheckWarning("a heater warning")
    cw.kind, cw.index = "heater", 3
    w.set_warnings([cw])
    from PySide6.QtCore import QUrl
    w._clicked(QUrl("heater:3"))
    assert got == [("heater", 3)]
    w.set_stale()
    w._clicked(QUrl("heater:3"))
    assert got == [("heater", 3)]                      # Ignored: the design was edited after this list was made
    w.set_warnings([cw])
    w._clicked(QUrl("heater:3"))
    assert len(got) == 2


def test_an_edit_marks_the_warnings_stale_and_a_click_on_a_removed_element_does_nothing(qtbot, tmp_path):
    win = _window(qtbot, tmp_path)
    win.solver_panel.checks.warnings = ["x"]
    win.doc.changed.emit()
    assert win.solver_panel.checks.stale
    win._select_from_warning("heater", 99)             # No such element: no error, nothing selected
    win._select_from_warning("nonsense", 0)


def test_the_run_button_stays_in_sight_on_a_low_window(qtbot, tmp_path):
    win = _window(qtbot, tmp_path)
    win.resize(1200, 420)
    qtbot.wait(100)
    run = win.solver_panel.run
    top = run.mapTo(win.dock_sim.widget(), run.rect().topLeft()).y()
    assert 0 <= top and top + run.height() <= win.dock_sim.widget().height()
    from pcbthermal.gui.panels import WarningList
    win.solver_panel.checks.set_warnings([f"warning number {i} " * 6 for i in range(30)])
    qtbot.wait(100)
    assert win.solver_panel.checks.height() <= win.dock_sim.widget().height() // 4 + 1
    top = run.mapTo(win.dock_sim.widget(), run.rect().topLeft()).y()
    assert top >= 0 and top + run.height() <= win.dock_sim.widget().height()
    assert WarningList.MAX_HEIGHT >= win.solver_panel.checks.height()


def test_the_count_of_unknowns_is_whole_in_a_narrow_dock(qtbot, tmp_path):
    win = _window(qtbot, tmp_path)
    win.dock_sim.widget().resize(260, 700)
    qtbot.wait(100)
    lab = win.solver_panel.cells_label
    assert lab.height() >= lab.heightForWidth(lab.width()) - 1       # The wrapped text is not cut to its first line
