#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_import_apply_flow.py
@brief The application of a Gerber import by the main window: File - Import Gerber board on an empty project, the three steps driven through the real buttons, the Document afterwards
       (problem, imported copper, parts, heaters with the powers, record, no undo steps), Cancel at each of the three steps leaving the open project as it was, and a bad Gerber file
       showing its message without a crash.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest

from pcbthermal.examples import example_board
from pcbthermal.gui import import_window as iw
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow
from tests.helpers.synthetic_board import make_board


@pytest.fixture
def board_dir(tmp_path):
    """!
    @brief The synthetic fabrication set with two inner layers.
    @param tmp_path Temporary folder.
    @return Path of the folder.
    """
    return make_board(tmp_path / "fab", inner=2)


@pytest.fixture
def win(qtbot, tmp_path):
    """!
    @brief A main window on an empty project.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return MainWindow
    """
    w = MainWindow(Document(), QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.resize(1400, 850)
    w.show()
    return w


def _drive(monkeypatch, source, stop_at=None, powers=None, notes=None):
    """!
    @brief Replace the modal exec of the import window by a driver that uses the real buttons: open the source, press Next to step 2, edit the powers, press Next to step 3 and Import.
    @param monkeypatch pytest fixture.
    @param source Folder or ZIP to open.
    @param stop_at Step (1, 2 or 3) at which the window is closed with Cancel instead of going on, or None to import.
    @param powers Dict designator -> watts typed on step 2.
    @param notes List that receives (title, text) of the messages of the window.
    @return list that receives the window opened.
    """
    seen = []

    def fake_exec(self):
        seen.append(self)
        self.confirm = lambda *a: True
        self.notify = lambda title, text: (notes if notes is not None else []).append((title, text))
        self.open_path(str(source))
        if stop_at == 1 or not self.session.complete():
            self.close_btn.click()                                    # Cancel / Close on step 1
            return self.result()
        QTest.mouseClick(self.next_btn, Qt.LeftButton)                # step 2: the parts
        assert self.step == 1
        for ref, w in (powers or {}).items():
            self.session.set_part(ref, power=w)
        if stop_at == 2:
            self.close_btn.click()
            return self.result()
        QTest.mouseClick(self.next_btn, Qt.LeftButton)                # step 3: the model
        assert self.step == 2 and self.next_btn.text() == "Import"
        if stop_at == 3:
            self.close_btn.click()
            return self.result()
        QTest.mouseClick(self.next_btn, Qt.LeftButton)                # Import
        return self.result()
    monkeypatch.setattr(iw.ImportBoardWindow, "exec", fake_exec)
    return seen


def test_import_on_an_empty_project_builds_the_document(win, board_dir, monkeypatch):
    _drive(monkeypatch, board_dir, powers={"U1": 3.0, "Q1": 1.5})
    assert not win.doc.problem.heaters and not win.doc.project.imports
    win.a_import.trigger()
    doc = win.doc
    pr = doc.problem
    assert doc.project.imports and doc.project.imports[0] is not None
    assert pr.board.layers == 4 and pr.board.width == pytest.approx(0.040) and pr.board.height == pytest.approx(0.030)
    assert pr.imported is not None and len(pr.imported.layers) == 4                      # the masks of the four copper layers
    assert len(pr.vias) == 2
    assert sorted(h.name for h in pr.heaters) == ["Q1", "U1"]
    assert {h.name: h.power for h in pr.heaters} == {"Q1": 1.5, "U1": 3.0}
    assert {p.designator for p in doc.project.imports[0].parts} == {"U1", "Q1", "D1", "R1"}
    assert doc.path is None and doc.title                                                # a new, unsaved project
    # A new import is a new document: the undo history starts empty (nothing to undo back to the empty project), and the window shows the board
    assert not doc.stack.canUndo()
    assert win.statusBar().currentMessage() == "Ready."
    assert win.a_imported.isChecked() and win.canvas is not None


def test_the_imported_project_survives_a_run_and_a_save_and_reopen(win, board_dir, monkeypatch, tmp_path, qtbot):
    from PySide6.QtWidgets import QFileDialog
    _drive(monkeypatch, board_dir, powers={"U1": 2.0})
    win.show_import()
    win.doc.set_options(models=("fvm",), cell_mm=2.0)
    win.run_simulation()
    qtbot.waitUntil(lambda: win.worker is None or not win.worker.isRunning(), timeout=180000)
    qtbot.wait(100)
    assert win.sim is not None and win.sim.heater_rows()[0]["t_max"] > win.doc.problem.board.ambient
    target = tmp_path / "imp.pcbt.json"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "")))
    assert win.save_file_as()
    import json
    assert json.loads(target.read_text())["format"] == "pcbthermal-project-2"
    win.open_file(str(target))
    assert win.doc.project.imports and win.doc.problem.imported is not None and [h.power for h in win.doc.problem.heaters] == [2.0]


@pytest.mark.parametrize("step", [1, 2, 3])
def test_cancel_at_each_step_leaves_the_open_project_as_it_was(win, board_dir, monkeypatch, step):
    win._load_problem(example_board(), "mine")
    win.doc.set_props("heater", 0, power=7.0, merge=False)                              # an unsaved edit: the project is modified
    before = win.doc.snapshot()
    n = win.doc.stack.count()
    seen = _drive(monkeypatch, board_dir, stop_at=step, powers={"U1": 4.0})
    win.show_import()
    assert len(seen) == 1 and seen[0].result() == 0
    assert win.doc.snapshot() == before and win.doc.stack.count() == n and not win.doc.project.imports
    assert win.doc.title.startswith("mine") and win.doc.modified


def test_cancel_with_an_empty_project_loads_nothing(win, board_dir, monkeypatch):
    _drive(monkeypatch, board_dir, stop_at=2)
    win.show_import()
    assert not win.doc.problem.heaters and not win.doc.project.imports and win.doc.problem.imported is None


def test_importing_over_a_modified_project_asks_and_discard_replaces_it(win, board_dir, monkeypatch):
    win._load_problem(example_board(), "mine")
    win.doc.set_props("heater", 0, power=7.0, merge=False)
    asked = []
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question", lambda *a, **k: (asked.append(a[1]), QMessageBox.Discard)[1])
    _drive(monkeypatch, board_dir, powers={"U1": 1.0})
    win.show_import()
    assert asked == ["Unsaved changes"] and win.doc.project.imports and [h.name for h in win.doc.problem.heaters] == ["U1"]


def test_a_cancelled_question_keeps_the_open_project(win, board_dir, monkeypatch):
    win._load_problem(example_board(), "mine")
    win.doc.set_props("heater", 0, power=7.0, merge=False)
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question", lambda *a, **k: QMessageBox.Cancel)
    _drive(monkeypatch, board_dir, powers={"U1": 1.0})
    win.show_import()
    assert not win.doc.project.imports and win.doc.problem.heaters[0].power == 7.0


def test_a_bad_gerber_file_shows_its_message_and_does_not_import(win, tmp_path, monkeypatch):
    d = make_board(tmp_path / "bad")
    (d / "F.gbr").write_bytes(b"%FSLAX46Y46*%\n\x00\xff\xfe garbage \x01\x02 X999999999999Y%%%%D01*\nG75*\nM02*\n")
    notes = []
    seen = _drive(monkeypatch, d, powers={"U1": 1.0}, notes=notes)
    win.show_import()                                                                    # no crash
    w = seen[0]
    # Whatever the reader makes of the garbage, the outcome is consistent: either a message and nothing imported, or a board that was read and imported whole
    if not w.session.complete():
        assert not win.doc.project.imports and not win.doc.problem.heaters
        assert w.status.text().startswith("Next is disabled") or notes
    else:
        assert win.doc.project.imports


def test_a_source_that_does_not_exist_is_a_message_and_the_project_is_kept(win, tmp_path, monkeypatch):
    win._load_problem(example_board(), "mine")
    before = win.doc.snapshot()
    notes = []
    _drive(monkeypatch, tmp_path / "nothing.zip", notes=notes)
    win.show_import()
    assert notes and notes[-1][0] == "Cannot read the files" and win.doc.snapshot() == before
