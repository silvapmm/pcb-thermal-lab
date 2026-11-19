#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_summary_table_setting.py
@brief The Preferences setting `results.summary_table_in_report`: shipped false (the report text of the Summary page has no table, as before), true (the text also
       carries the aligned table), the widget in both cases, a change saved in Preferences applied to the result already shown, an old user file without the key,
       and the report written to a file never governed by the setting.
"""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QCheckBox

from pcbthermal import defaults
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow
from pcbthermal.gui.preferences import PreferencesDialog

MARK = "Tmean"          # A header of the models table that appears only in the aligned text table


@pytest.fixture(scope="module")
def sim():
    """!
    @brief One run of two models on the example board.
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=("fvm", "lumped"), cell_mm=2.0))


@pytest.fixture(autouse=True)
def private_config(tmp_path, monkeypatch):
    """!
    @brief Point the configuration folder to an empty temporary one so the user's real file never matters.
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture.
    @return None.
    """
    monkeypatch.setenv("PCBTHERMAL_CONFIG", str(tmp_path / "cfg"))


def _window(qtbot, tmp_path):
    """!
    @brief A main window with private settings.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return MainWindow.
    """
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    return win


def _write_user(value):
    """!
    @brief Write a user file that sets the key.
    @param value True or False.
    @return None.
    """
    os.makedirs(defaults.user_dir(), exist_ok=True)
    with open(defaults.user_file(), "w", encoding="utf-8") as fh:
        json.dump({"results": {"summary_table_in_report": value}}, fh)


def test_shipped_value_is_false_and_an_old_file_without_the_key_keeps_it():
    """!
    @brief The shipped default is False; a user file of an older version (no `results` section at all, or other sections only) gives False too.
    @return None.
    """
    assert defaults.shipped()["results"]["summary_table_in_report"] is False
    assert defaults.value("results", "summary_table_in_report") is False
    os.makedirs(defaults.user_dir(), exist_ok=True)
    with open(defaults.user_file(), "w", encoding="utf-8") as fh:
        json.dump({"solver": {"cell_mm": 2.0}}, fh)
    assert defaults.value("results", "summary_table_in_report") is False
    assert defaults.value("solver", "cell_mm") == 2.0


def test_user_file_round_trip():
    """!
    @brief Saving True writes only the difference; saving the shipped value again removes the key (and the file when nothing else differs).
    @return None.
    """
    full = defaults.load()
    full["results"]["summary_table_in_report"] = True
    written = defaults.save_user(full)
    assert written["results"] == {"summary_table_in_report": True} and set(written) == {"_comment", "results"}
    assert defaults.value("results", "summary_table_in_report") is True
    full["results"]["summary_table_in_report"] = False
    assert defaults.save_user(full) == {}
    assert not defaults.has_user_file()


def test_summary_text_without_the_table_by_default_and_with_it_when_set(qtbot, tmp_path, sim):
    """!
    @brief Default: the report text has no table and the widget has the rows; set to True: the text carries the table, the widget is the same; the saved report always has it.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation fixture.
    @return None.
    """
    win = _window(qtbot, tmp_path)
    win.results.set_simulation(sim)
    assert MARK not in win.results.report.toPlainText()
    assert win.results.model_table.rowCount() == 2
    _write_user(True)
    win.results.set_simulation(sim)
    text = win.results.report.toPlainText()
    assert MARK in text and "Tmean" in sim.report(inline_warnings=False, table=True)
    assert win.results.model_table.rowCount() == 2
    # The numbers of the table are those of the Simulation, not a copy: same lines as the report built by the API
    assert text == sim.report(inline_warnings=False, table=True)
    # Never governed by the setting: the report of write_outputs / export_report and the console report of the API
    assert MARK in sim.report()
    _write_user(False)
    win.results.set_simulation(sim)
    assert text != win.results.report.toPlainText() and win.results.report.toPlainText() == sim.report(inline_warnings=False, table=False)


def test_refresh_report_applies_a_saved_change_to_the_result_shown(qtbot, tmp_path, sim):
    """!
    @brief After Preferences are saved the report text of the result already shown is rewritten; without a result the call does nothing.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation fixture.
    @return None.
    """
    win = _window(qtbot, tmp_path)
    win.results.refresh_report()                                # No result yet: no error, no text
    assert win.results.report.toPlainText() == ""
    win.results.set_simulation(sim)
    assert MARK not in win.results.report.toPlainText()
    _write_user(True)
    win.results.refresh_report()
    assert MARK in win.results.report.toPlainText()


def test_preferences_page_has_the_checkbox_with_tip_and_saves_it(qtbot):
    """!
    @brief The Results page has a labelled check box with a tooltip (meaning, default, what it never changes, JSON key); ticking it and saving writes the key.
    @param qtbot pytest-qt fixture.
    @return None.
    """
    d = PreferencesDialog()
    qtbot.addWidget(d)
    assert "Results" in d.section_titles()
    w = d.widgets[("results", "summary_table_in_report")]
    assert isinstance(w, QCheckBox) and not w.isChecked()
    tip = w.toolTip()
    assert "models table" in tip and "never a number" in tip
    assert "report.txt" in tip and "summary_table_in_report" in tip and "not saved in project files" in tip
    w.setChecked(True)
    d.save_btn.click()
    assert d.saved and defaults.value("results", "summary_table_in_report") is True


def test_a_toggle_in_a_shown_result_keeps_the_window_alive(qtbot, tmp_path, sim):
    """!
    @brief Stress: flip the setting ten times with a result on screen, rewriting the text each time; the widget table and the text stay consistent.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation fixture.
    @return None.
    """
    win = _window(qtbot, tmp_path)
    win.results.set_simulation(sim)
    for i in range(10):
        _write_user(bool(i % 2 == 0))
        win.results.refresh_report()
        assert (MARK in win.results.report.toPlainText()) == (i % 2 == 0)
        assert win.results.model_table.rowCount() == 2
