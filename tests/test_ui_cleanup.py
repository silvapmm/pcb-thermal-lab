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
    """!
    @brief A shown main window with private settings.
    @param qtbot pytest-qt helper.
    @param tmp_path Temporary folder for the settings file.
    @return MainWindow.
    """
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.show()
    return win


def _menu(target, pos, *names):
    """!
    @brief Open the real context menu of a widget and choose some of its entries (as a user would), then close it.
    @param target Widget that receives the context-menu event.
    @param pos Global position of the event.
    @param names Entries to trigger, by their text without the accelerator and the shortcut, lower case.
    @return List of the texts of the menu entries (None when no menu opened).
    """
    from PySide6.QtCore import QPoint, QTimer
    from PySide6.QtGui import QContextMenuEvent

    seen = []

    tries = [0]

    def answer():
        menu = QApplication.activePopupWidget()
        if menu is None and tries[0] < 100:             # A loaded machine opens the popup late: wait up to 5 s
            tries[0] += 1
            QTimer.singleShot(50, answer)
            return
        seen.append([a.text().replace("&", "").split("\t")[0].lower() for a in menu.actions()] if menu else None)
        if menu is not None:
            for name in names:
                next(a for a in menu.actions() if a.text().replace("&", "").split("\t")[0].lower() == name).trigger()
            menu.close()

    QTimer.singleShot(50, answer)
    QApplication.sendEvent(target, QContextMenuEvent(QContextMenuEvent.Mouse, QPoint(2, 2), pos))
    return seen[0] if seen else None


def test_the_context_menu_of_a_number_field_pastes_a_comma_as_a_point_and_keeps_its_other_entries(qtbot):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QDoubleSpinBox, QSpinBox

    from pcbthermal.gui import theme

    theme.fix_number_locale()
    spin = QDoubleSpinBox()
    spin.setRange(0, 100)
    spin.setDecimals(3)
    spin.setSuffix(" mm")                              # Most number fields of the program carry a unit
    spin.setValue(1.6)
    qtbot.addWidget(spin)
    spin.show()
    edit = spin.lineEdit()
    pos = spin.mapToGlobal(QPoint(2, 2))
    clip = QGuiApplication.clipboard()

    # Right click on the text: Select All, then Paste of "0,45" (read as 45 by Qt's own Paste)
    clip.setText("0,45")
    entries = _menu(edit, pos, "select all", "paste")
    assert entries is not None and {"undo", "redo", "cut", "copy", "paste", "delete", "select all", "step up", "step down"} <= set(entries)
    # the number of decimals shown depends on the field's state, so test the point and the value
    assert "," not in edit.text() and abs(spin.value() - 0.45) < 1e-12
    # Undo of the menu takes the paste back (the application style sheet makes Qt drop the undo history of a spin box,
    # so the entry is only exercised when the field has one)
    if edit.isUndoAvailable():
        _menu(edit, pos, "undo")
    else:
        spin.setValue(1.6)
    assert edit.text() == "1.600 mm" and abs(spin.value() - 1.6) < 1e-12
    # Select All of the menu selects the number, not the unit (as Qt's spin box menu); Copy and Cut work
    _menu(edit, pos, "select all")
    assert edit.selectedText() == "1.600"
    _menu(edit, pos, "copy")                           # Copy is enabled only once something is selected
    assert clip.text() == "1.600"
    spin.setValue(2.5)
    spin.selectAll()
    _menu(edit, pos, "cut")
    assert clip.text() == "2.500"
    # Right click on the arrows goes to the spin box itself: the same menu, with the converted Paste and Step up
    spin.setValue(1.6)
    _menu(spin, pos, "step up")
    assert abs(spin.value() - 2.6) < 1e-12
    clip.setText("3,25")
    spin.selectAll()
    _menu(spin, pos, "paste")
    spin.interpretText()
    assert abs(spin.value() - 3.25) < 1e-12
    # An integer field: a plain number pastes as it is
    ints = QSpinBox()
    ints.setRange(0, 100)
    ints.setValue(5)
    qtbot.addWidget(ints)
    ints.show()
    clip.setText("12")
    _menu(ints.lineEdit(), ints.mapToGlobal(QPoint(2, 2)), "select all", "paste")
    ints.interpretText()
    assert ints.value() == 12


def test_a_stale_warning_list_ignores_clicks_until_the_next_check(qtbot):
    from PySide6.QtCore import QUrl

    from pcbthermal.checks import CheckWarning
    from pcbthermal.gui.panels import WarningList

    w = WarningList()
    qtbot.addWidget(w)
    got = []
    w.warning_clicked.connect(lambda k, i: got.append((k, i)))
    cw = CheckWarning("a heater warning")
    cw.kind, cw.index = "heater", 3
    w.set_warnings([cw])
    w._clicked(QUrl("heater:3"))
    assert got == [("heater", 3)]
    w.set_stale()
    w._clicked(QUrl("heater:3"))
    assert got == [("heater", 3)]                      # Ignored: the design was edited after this list was made
    w.set_warnings([cw])
    w._clicked(QUrl("heater:3"))
    assert len(got) == 2


def test_a_click_on_a_warning_after_an_edit_selects_nothing_until_the_check_runs(qtbot, tmp_path):
    from PySide6.QtCore import QUrl

    from pcbthermal.checks import CheckWarning
    from pcbthermal.examples import example_board

    win = _window(qtbot, tmp_path)
    win._load_problem(example_board(), "t")
    cw = CheckWarning("about heater 2")
    cw.kind, cw.index = "heater", 1
    checks = win.solver_panel.checks
    checks.set_warnings([cw])
    win.canvas.set_selection([])
    win.doc.changed.emit()                             # An edit: the list is stale until the timer runs the check
    assert checks.stale
    checks._clicked(QUrl("heater:1"))
    assert win.canvas.selected_elements() == []
    checks.set_warnings([cw])                          # The check ran: the links work again
    checks._clicked(QUrl("heater:1"))
    assert win.canvas.selected_elements() == [("heater", 1)]
    win.canvas.set_selection([])
    win._select_from_warning("heater", 99)             # No such element: no error, nothing selected
    win._select_from_warning("nonsense", 0)
    assert win.canvas.selected_elements() == []


def test_thirty_warnings_do_not_push_the_run_button_or_the_settings_out_of_a_low_window(qtbot, tmp_path):
    from PySide6.QtWidgets import QScrollArea

    from pcbthermal.gui.panels import WarningList

    win = _window(qtbot, tmp_path)
    checks, run = win.solver_panel.checks, win.solver_panel.run
    win.resize(1200, 420)
    qtbot.wait(100)
    low = win.height()                                 # The lowest the window goes without warnings (its minimum, about 450 px)
    assert low <= 480
    checks.set_warnings([f"warning number {i} " * 6 for i in range(30)])
    qtbot.wait(100)                                    # The list appears (the window may grow to show it) before the user makes it low again
    win.resize(1200, 420)
    qtbot.wait(100)
    host = win.dock_sim.widget()
    # The list shrinks and scrolls instead of raising the minimum height of the window (a fixed-height list raised it by 110 to 160 px)
    assert win.height() <= low + WarningList.MIN_HEIGHT + 10
    assert checks.height() <= max(WarningList.MIN_HEIGHT, host.height() // 4) + 1
    assert host.findChild(QScrollArea).height() >= 120                 # The settings keep their strip
    top = run.mapTo(win, run.rect().topLeft()).y()
    assert top >= 0 and top + run.height() <= win.height()
    # A tall window shows more of the list again
    win.resize(1200, 1000)
    qtbot.wait(100)
    assert WarningList.MIN_HEIGHT < checks.height() <= WarningList.MAX_HEIGHT


def test_the_count_of_unknowns_spans_the_whole_form_row(qtbot, tmp_path):
    from PySide6.QtWidgets import QFormLayout

    win = _window(qtbot, tmp_path)
    lab = win.solver_panel.cells_label
    form = lab.parentWidget().layout()
    form = form if isinstance(form, QFormLayout) else next(f for f in lab.parentWidget().findChildren(QFormLayout) if f.indexOf(lab) >= 0)
    # In the field column the wrapped text was cut to its first line on macOS (not reproduced offscreen): it spans both columns now
    assert form.getWidgetPosition(lab)[1] == QFormLayout.SpanningRole
    win.solver_panel.cb["solid3d"].setChecked(True)
    win.solver_panel.cell.setValue(0.2)            # The longest text: the count, the 3D count and its note
    win.resizeDocks([win.dock_sim], [200], Qt.Horizontal)
    qtbot.wait(100)
    assert lab.height() >= lab.heightForWidth(lab.width()) - 1
