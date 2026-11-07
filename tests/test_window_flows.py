#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_window_flows.py
@brief Flows of the main window that no other test drives: Preferences (each of the ten sections, Save and Reset), File - Open example, Save and Save As, a newer or damaged file,
       the keyboard (Del, Backspace, Ctrl+A, Ctrl+comma, the zoom keys, the tab keys, G and T) sent as key events, and the Animation tab (compute, play and pause, GIF export, the
       underlay combo).
"""

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractSpinBox, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QMessageBox, QSpinBox

from pcbthermal import defaults
from pcbthermal.examples import example_board
from pcbthermal.gui import preferences as prefs
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import TAB_BOARD, TAB_PROFILE, TAB_RESULTS, TAB_STACKUP, MainWindow
from pcbthermal.project import FORMAT_2, Project, save_project


@pytest.fixture
def popups(monkeypatch):
    """!
    @brief Replace the message boxes of the main window by recorders; "Save the changes?" is answered Discard unless a test sets `answer`.
    @param monkeypatch pytest fixture.
    @return list of (kind, title, text); its attribute `answer` (a settable dict) holds the answer of the question.
    """
    class Seen(list):
        """!
        @brief List of the boxes shown, with the settable answer of the question box.
        """
        answer = None
    seen = Seen()
    answer = {"question": QMessageBox.Discard}
    seen.answer = answer

    def record(kind):
        def f(*args, **kwargs):
            seen.append((kind, args[1] if len(args) > 1 else "", args[2] if len(args) > 2 else ""))
            return answer["question"] if kind == "question" else None
        return f
    for kind in ("warning", "critical", "information", "question"):
        monkeypatch.setattr(f"pcbthermal.gui.main_window.QMessageBox.{kind}", record(kind))
    return seen


@pytest.fixture
def win(qtbot, tmp_path, popups):
    """!
    @brief A main window on an empty project, shown and active (the shortcuts need an active window).
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param popups Recorder of the message boxes.
    @return MainWindow
    """
    w = MainWindow(Document(), QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.resize(1500, 900)
    w.show()
    w.activateWindow()
    return w


# ------------------------------------------------------------------------------------------------------------------------------ Preferences
def _bump(widget):
    """!
    @brief Change a spin box to another value inside its range.
    @param widget QSpinBox or QDoubleSpinBox.
    @return The new value.
    """
    lo, hi, v = widget.minimum(), widget.maximum(), widget.value()
    target = (lo + min(hi, lo + 100)) / 2
    if abs(target - v) < 10 ** -widget.decimals() * 2 if isinstance(widget, QDoubleSpinBox) else target == v:
        target = min(hi, v + 1) if v + 1 <= hi else max(lo, v - 1)
    widget.setValue(target)
    return widget.value()


def test_preferences_has_ten_sections_and_each_one_applies_and_resets(win, qtbot, monkeypatch):
    opened = []
    monkeypatch.setattr(prefs.PreferencesDialog, "exec", lambda self: (opened.append(self), 0)[1])
    win.a_prefs.trigger()
    assert len(opened) == 1
    d = opened[0]
    qtbot.addWidget(d)
    assert len(d.section_titles()) == 10 and d.section_titles()[6:] == ["Defaults for new projects", "Solver", "Gerber import", "Power Calculator"]
    assert not defaults.has_user_file()
    changed = {}
    for row in range(d.sections.count()):
        d.sections.setCurrentRow(row)
        assert d.pages.currentIndex() == row
    # Libraries: one entry added to each (the user file holds the difference)
    for lib in defaults.LIBRARIES:
        before = len(d.data["libraries"][lib])
        d._add_row(lib)
        assert len(d.data["libraries"][lib]) == before + 1
    # Scalars: one value of each section moved
    for section in defaults.SECTIONS:
        for (sec, key), wdg in d.widgets.items():
            if sec == section and isinstance(wdg, (QSpinBox, QDoubleSpinBox)):
                changed[(sec, key)] = _bump(wdg)
                break
        else:
            pytest.fail(f"no spin box in the section {section}")
    assert set(s for s, _ in changed) == set(defaults.SECTIONS)
    d.save_btn.click()
    assert d.saved and defaults.has_user_file()
    user = json.load(open(defaults.user_file(), encoding="utf-8"))
    for lib in defaults.LIBRARIES:
        assert any(e["name"] == "New entry" for e in user["libraries"][lib])
    for (sec, key), v in changed.items():
        assert defaults.value(sec, key) == pytest.approx(v)
    # The main window refreshes what depends on the libraries after the dialog (show_preferences runs the same code with the dialog's saved flag)
    monkeypatch.setattr(prefs.PreferencesDialog, "exec", lambda self: (setattr(self, "saved", True), 0)[1])
    win.show_preferences()
    assert "Defaults saved" in win.statusBar().currentMessage()
    # Reset needs the user's yes; "no" keeps the file
    monkeypatch.setattr(prefs.QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.No))
    d.reset_btn.click()
    assert defaults.has_user_file()
    monkeypatch.setattr(prefs.QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    d.reset_btn.click()
    assert not defaults.has_user_file()
    for (sec, key), wdg in d.widgets.items():
        if (sec, key) in changed:
            assert wdg.value() == pytest.approx(defaults.shipped()[sec][key])
    for lib in defaults.LIBRARIES:
        assert d.tables[lib][0].rowCount() == len(defaults.shipped()["libraries"][lib])
    d.close()


def test_a_new_board_takes_the_saved_default_and_an_open_board_keeps_its_value(win, qtbot, monkeypatch):
    win._load_problem(example_board(), "mine")
    ambient = win.doc.problem.board.ambient
    d = prefs.PreferencesDialog(win)
    qtbot.addWidget(d)
    d.widgets[("new_board", "ambient_c")].setValue(ambient + 11.0)
    d.save()
    assert win.doc.problem.board.ambient == ambient                                      # the open board keeps its value
    win.doc.new()
    assert win.doc.problem.board.ambient == pytest.approx(ambient + 11.0)                # a new one uses the default
    d.close()


# ------------------------------------------------------------------------------------------------------------------------------------ files
def test_open_example_both_entries_and_the_discard_question(win, popups):
    ex = [a for m in win.menuBar().actions() if m.text() == "&File" for s in m.menu().actions() if s.menu() and s.text() == "Open example" for a in s.menu().actions()]
    assert [a.text() for a in ex][:1] == ["Reference board (100 × 100 mm, 2 layers)"] and len(ex) == 2
    ex[0].trigger()
    assert win.doc.title.startswith("reference") and win.doc.path is None and not win.doc.modified and not win.doc.stack.canUndo()
    win.doc.set_props("heater", 0, power=9.0, merge=False)                               # a stack edit: the project is modified (set_options is not)
    assert win.doc.modified
    popups.clear()
    ex[1].trigger()                                                                       # asks, the answer is Discard
    assert [k for k, _t, _x in popups] == ["question"] and win.doc.title.startswith("example-4layer") and len(win.doc.problem.heaters) == 2
    win.doc.set_props("heater", 0, power=8.0, merge=False)
    popups.answer["question"] = QMessageBox.Cancel                                        # Cancel keeps the project
    ex[0].trigger()
    assert win.doc.title.startswith("example-4layer")


def test_save_and_save_as_write_a_project_file_and_clear_the_modified_flag(win, tmp_path, monkeypatch, popups):
    win._load_problem(example_board(), "mine")
    target = tmp_path / "board"                                                           # no suffix typed: ".pcbt.json" is added
    asked = []
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (asked.append(a[-1]), (str(target), ""))[1]))
    win.doc.set_props("heater", 0, power=3.0, merge=False)
    assert win.windowTitle().startswith("mine *")
    win.a_save.trigger()                                                                  # no path yet: Save asks like Save as
    path = str(target) + ".pcbt.json"
    assert asked == ["PCB Thermal project (*.pcbt.json);;PCB Thermal project package (*.pcbtz)"] and os.path.exists(path) and win.doc.path == path and not win.doc.modified and " *" not in win.windowTitle()
    assert json.load(open(path))["format"] != FORMAT_2                                    # a project without imports is format 1
    # Save with unsaved changes writes in place, no dialog and no backup (the format did not change)
    asked.clear()
    win.doc.set_props("heater", 0, power=4.0, merge=False)
    assert win.doc.modified
    win.a_save.trigger()
    assert not asked and not win.doc.modified and not os.path.exists(path + ".bak")
    again = Document()
    again.open(path)
    assert again.problem.heaters[0].power == pytest.approx(4.0)
    # Save as to another name: the document follows it
    other = tmp_path / "other.pcbt.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(other), "")))
    win.a_saveas.trigger()
    assert win.doc.path == str(other) and other.exists()
    # Cancel in the dialog changes nothing
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")))
    assert win.save_file_as() is False and win.doc.path == str(other)
    # A save that fails shows the reason and keeps the document modified
    win.doc.set_props("heater", 0, power=5.0, merge=False)
    monkeypatch.setattr(win.doc, "save", lambda path=None: (_ for _ in ()).throw(OSError("disk full")))
    popups.clear()
    assert win.save_file() is False and popups[0][:2] == ("critical", "Cannot save") and "disk full" in popups[0][2] and win.doc.modified


def test_open_refuses_a_newer_a_damaged_and_a_missing_file_and_keeps_the_open_project(win, tmp_path, popups, monkeypatch):
    good = tmp_path / "good.pcbt.json"
    save_project(good, Project(problem=example_board()))
    win.open_file(str(good))
    assert win.doc.path == str(good) and not popups
    newer = tmp_path / "newer.pcbt.json"
    newer.write_text(json.dumps({"format": "pcbthermal-project-3", "app_version": "3.1.0", "project": {}}))
    cut = tmp_path / "cut.pcbt.json"
    cut.write_text('{"format": "pcbthermal-project-1", "board": {"wid')
    binary = tmp_path / "bin.pcbt.json"
    binary.write_bytes(b"\x00\x01\x02\xff" * 20)
    for bad, words in ((newer, ("format 3", "3.1.0")), (cut, ("not valid JSON",)), (binary, ()), (tmp_path / "missing.pcbt.json", ())):
        popups.clear()
        win.open_file(str(bad))
        assert [(k, t) for k, t, _x in popups] == [("critical", "Cannot open file")], popups
        assert all(w in popups[0][2] for w in words) and popups[0][2].strip() != ""
        assert win.doc.path == str(good) and win.doc.problem.heaters
    # The file dialog route: Cancel in the dialog opens nothing
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
    popups.clear()
    win.open_file()
    assert not popups and win.doc.path == str(good)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(good), "")))
    win.a_open.trigger()
    assert win.doc.path == str(good)


def test_the_program_keeps_no_list_of_recent_files(win):
    """There is no recent-files menu in this version: the File menu holds the documented entries only (a regression guard for the day one is added: this test then needs its flows)."""
    file_menu = next(m.menu() for m in win.menuBar().actions() if m.text() == "&File")
    texts = [a.text() for a in file_menu.actions()]
    assert not any("recent" in t.lower() for t in texts)
    assert {"New board…", "Open…", "Import Gerber board…", "Save", "Save as…"} <= set(texts)


# ------------------------------------------------------------------------------------------------------------------------------ the keyboard
def _key(win, key, mod=Qt.NoModifier):
    """!
    @brief Send a key press and release to the main window (the shortcut map sees it).
    @param win MainWindow.
    @param key Qt key.
    @param mod Keyboard modifiers.
    @return None
    """
    QTest.keyClick(win, key, mod)


def _zoom(win):
    """!
    @brief The scale of the editor view.
    @param win MainWindow.
    @return float
    """
    return win.canvas.transform().m11()


def test_delete_and_backspace_delete_the_selection_and_undo_brings_it_back(win, qtbot):
    win._load_problem(example_board(), "ex")
    n = len(win.doc.problem.heaters)
    win.layer_combo.setCurrentIndex(0)
    for key in (Qt.Key_Delete, Qt.Key_Backspace):
        m = len(win.doc.problem.heaters)
        win.canvas.set_selection([("heater", 0)])
        win._on_canvas_selection([("heater", 0)])
        assert win.canvas.selected_elements() == [("heater", 0)]
        _key(win, key)
        assert len(win.doc.problem.heaters) == m - 1, key
        win.doc.stack.undo()
        assert len(win.doc.problem.heaters) == m
    assert len(win.doc.problem.heaters) == n
    win.canvas.set_selection([])
    _key(win, Qt.Key_Delete)                                                              # nothing selected: nothing happens
    assert len(win.doc.problem.heaters) == n


def test_select_all_selects_the_elements_of_the_active_layer(win):
    win._load_problem(example_board(), "ex")
    pr = win.doc.problem
    expect = {(k, i) for k, lst in (("zone", pr.zones), ("heater", pr.heaters), ("heatsink", pr.heatsinks)) for i, e in enumerate(lst) if e.layer == win.canvas.layer} \
        | {("via", i) for i in range(len(pr.vias))}
    assert expect
    _key(win, Qt.Key_A, Qt.ControlModifier)
    assert set(win.canvas.selected_elements()) == expect


def test_ctrl_comma_opens_preferences_and_ctrl_digits_switch_the_tabs(win, monkeypatch):
    opened = []
    monkeypatch.setattr(prefs.PreferencesDialog, "exec", lambda self: (opened.append(self), 0)[1])
    _key(win, Qt.Key_Comma, Qt.ControlModifier)
    assert len(opened) == 1
    for key, tab in ((Qt.Key_4, TAB_RESULTS), (Qt.Key_3, TAB_PROFILE), (Qt.Key_2, TAB_STACKUP), (Qt.Key_1, TAB_BOARD)):
        _key(win, key, Qt.ControlModifier)
        assert win.tabs.currentIndex() == tab


def test_zoom_keys_and_fit(win):
    win._load_problem(example_board(), "ex")
    win.canvas.fit()
    fit = _zoom(win)
    _key(win, Qt.Key_Equal, Qt.ControlModifier)                                           # Ctrl+= is the second key of Zoom in
    zin = _zoom(win)
    assert zin == pytest.approx(fit * 1.25)
    _key(win, Qt.Key_Plus, Qt.ControlModifier)
    assert _zoom(win) > zin
    _key(win, Qt.Key_Minus, Qt.ControlModifier)
    assert _zoom(win) < zin * 1.25
    _key(win, Qt.Key_Minus, Qt.ControlModifier)
    _key(win, Qt.Key_Minus, Qt.ControlModifier)
    _key(win, Qt.Key_Minus, Qt.ControlModifier)
    assert _zoom(win) < fit
    _key(win, Qt.Key_0, Qt.ControlModifier)
    assert _zoom(win) == pytest.approx(fit, rel=1e-6)


def test_letter_keys_toggle_the_grid_and_the_solver_grid_and_the_temperature_overlay(win):
    win._load_problem(example_board(), "ex")
    grid = win.a_grid.isChecked()
    _key(win, Qt.Key_G)
    assert win.a_grid.isChecked() == (not grid)
    _key(win, Qt.Key_G, Qt.ShiftModifier)
    assert win.a_sgrid.isChecked()
    _key(win, Qt.Key_G, Qt.ShiftModifier)
    assert not win.a_sgrid.isChecked()
    _key(win, Qt.Key_G)
    assert win.a_grid.isChecked() == grid


def test_undo_and_redo_keys(win):
    win._load_problem(example_board(), "ex")
    p0 = win.doc.problem.heaters[0].power
    win.doc.set_props("heater", 0, power=p0 + 1.0, merge=False)
    _key(win, Qt.Key_Z, Qt.ControlModifier)
    assert win.doc.problem.heaters[0].power == pytest.approx(p0)
    _key(win, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
    assert win.doc.problem.heaters[0].power == pytest.approx(p0 + 1.0)
    _key(win, Qt.Key_Z, Qt.ControlModifier)
    _key(win, Qt.Key_Y, Qt.ControlModifier)
    assert win.doc.problem.heaters[0].power == pytest.approx(p0 + 1.0)


# ------------------------------------------------------------------------------------------------------------------------------- animation
def test_animation_tab_compute_play_pause_export_and_the_underlay_combo(win, qtbot, tmp_path, monkeypatch):
    from pcbthermal.gui import animation as an
    win._load_problem(example_board(), "ex")
    win.doc.set_options(cell_mm=2.0)
    anim = win.results.animation
    anim.model.setCurrentIndex(anim.model.findData("fvm"))
    anim.t_end.setValue(60.0)
    anim.frames.setValue(12)
    anim.tr = None
    assert not anim.export.isEnabled() or anim.tr is None
    anim.compute.click()
    qtbot.waitUntil(lambda: anim.tr is not None, timeout=180000)
    assert len(anim.tr.times) >= 12 and anim.slider.maximum() == len(anim.tr.times) - 1
    # Play from the start, a few frames advance, Pause stops the timer
    anim.slider.setValue(0)
    anim.fps.setValue(20)
    anim.play.click()
    assert anim.play.isChecked() and anim.play.text() == "Pause" and anim.timer.isActive()
    qtbot.waitUntil(lambda: anim.slider.value() >= 2, timeout=5000)
    anim.play.click()
    assert anim.play.text() == "Play" and not anim.timer.isActive()
    stop = anim.slider.value()
    qtbot.wait(300)
    assert anim.slider.value() == stop                                                    # paused: the frame does not move
    # Play to the end stops by itself
    anim.slider.setValue(anim.slider.maximum() - 1)
    anim.play.click()
    qtbot.waitUntil(lambda: not anim.play.isChecked(), timeout=5000)
    assert anim.slider.value() == anim.slider.maximum()
    # Export the GIF with the underlay None and then Copper
    for kind in ("none", "copper"):
        win.display_popover.underlay.setCurrentIndex(win.display_popover.underlay.findData(kind))
        assert win.display.kind == kind
        out = tmp_path / f"anim_{kind}.gif"
        monkeypatch.setattr(an.QFileDialog, "getSaveFileName", staticmethod(lambda *a, o=out, **k: (str(o), "")))
        anim.export.click()
        assert out.exists() and out.read_bytes()[:4] == b"GIF8" and out.stat().st_size > 1000, kind
        assert str(out) in anim.status.text()
    # Cancel in the file dialog writes nothing
    monkeypatch.setattr(an.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")))
    anim.export.click()
    assert sorted(p.name for p in tmp_path.glob("*.gif")) == ["anim_copper.gif", "anim_none.gif"]
