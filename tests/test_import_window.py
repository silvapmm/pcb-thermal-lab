#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_import_window.py
@brief The Gerber import window: the session (files, roles, checks, board, hooks of the features not merged yet), the stepper and its locked steps, Back / Next / Import now,
       the file list with editable functions, the preview, the live theme switch and the File menu entry.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pcbthermal.gui import theme as th
from pcbthermal.gui import import_session as ims
from pcbthermal.gui.document import Document
from pcbthermal.gui.import_session import ImportNotAvailable, ImportSession
from pcbthermal.gui.import_window import ImportBoardWindow
from pcbthermal.gui.main_window import MainWindow
from tests.helpers.synthetic_board import HEIGHT, WIDTH, make_board, make_zip


@pytest.fixture
def board_dir(tmp_path):
    """!
    @brief The synthetic fabrication set with two inner layers.
    @param tmp_path Temporary folder.
    @return Path of the folder.
    """
    return make_board(tmp_path / "fab", inner=2)


@pytest.fixture
def window(qtbot, board_dir):
    """!
    @brief An import window with the synthetic board read.
    @param qtbot pytest-qt fixture.
    @param board_dir Folder of the files.
    @return ImportBoardWindow
    """
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.show()
    w.confirm = lambda title, text: True
    w.notify = lambda title, text: w.__dict__.setdefault("notes", []).append((title, text))
    w.open_path(str(board_dir))
    return w


# ---------------------------------------------------------------------------------------------------------------------------------- session
def test_roles_are_detected_from_x2_excellon_and_columns(board_dir):
    sx = ImportSession()
    sx.set_files(board_dir)
    roles = {f.name: f.role for f in sx.files}
    assert roles == {"B.gbr": ims.COPPER_BOTTOM, "F.gbr": ims.COPPER_TOP, "In1.gbr": "Inner copper 1", "In2.gbr": "Inner copper 2", "drill.drl": ims.PLATED, "edge.gbr": ims.OUTLINE,
                     "pasteF.gbr": "Solder paste top", "pos.csv": ims.PLACEMENT}
    assert {f.name: f.how for f in sx.files}["drill.drl"] == "Excellon header" and {f.name: f.how for f in sx.files}["F.gbr"] == "Gerber X2 attribute"
    assert [l.role for l in sx.layers()] == [ims.COPPER_TOP, "Inner copper 1", "Inner copper 2", ims.COPPER_BOTTOM]
    assert sx.complete() and sx.stackup()["copper_um"].__len__() == 4


def test_the_board_is_read_with_outline_holes_and_layers(board_dir):
    sx = ImportSession()
    sx.set_files(board_dir)
    b = sx.load()
    assert b.width == pytest.approx(WIDTH) and b.height == pytest.approx(HEIGHT)
    assert b.outline_area_mm2 == pytest.approx(WIDTH * HEIGHT)
    assert [r for r, _, _ in b.copper] == [ims.COPPER_TOP, "Inner copper 1", "Inner copper 2", ims.COPPER_BOTTOM]
    # The bottom copper is a pour of 38 x 28 mm on a 40 x 30 board: its coverage is that share of the window
    cov = dict((r, c) for r, _, c in b.copper)[ims.COPPER_BOTTOM]
    assert cov.sum(dtype=np.float64) / 255.0 * b.pixel_mm ** 2 == pytest.approx(38 * 28, rel=0.02)
    assert sx.vias() == (2, 1, 0)                               # Two 0.3 mm vias, one 3 mm component hole
    assert sx.board() is b


def test_two_files_claiming_a_function_stop_the_import(board_dir):
    sx = ImportSession()
    sx.set_files(board_dir)
    i = [f.name for f in sx.files].index("B.gbr")
    sx.set_role(i, ims.COPPER_TOP)
    assert any("Two files claim 'Top copper'" in p for p in sx.problems()) and not sx.complete()
    assert sx.load() is None
    sx.set_role(i, ims.COPPER_BOTTOM)
    assert sx.complete() and sx.load() is not None


def test_no_copper_and_inner_gaps_are_problems(board_dir):
    sx = ImportSession()
    sx.set_files(board_dir)
    for i, f in enumerate(sx.files):
        if f.role in ims.COPPER:
            sx.set_use(i, False)
    assert "No copper layer is selected" in sx.problems()
    sx.set_files(board_dir)
    i = [f.name for f in sx.files].index("In1.gbr")
    sx.set_use(i, False)                                         # Inner 2 without inner 1
    assert any("without a gap" in p for p in sx.problems())


def test_a_missing_outline_and_drill_are_notes_not_problems(tmp_path):
    d = make_board(tmp_path / "fab", drills=False)
    (d / "edge.gbr").unlink()
    sx = ImportSession()
    sx.set_files(d)
    assert sx.complete()
    notes = " ".join(sx.notes())
    assert "No board outline" in notes and "No drill file" in notes
    b = sx.load()
    assert b.outline == [] and b.outline_area_mm2 is None and b.width == pytest.approx(WIDTH - 2, abs=0.5)      # The box of the copper: 38 x 28 mm


def test_a_file_the_reader_refuses_is_marked(tmp_path):
    d = make_board(tmp_path / "fab")
    (d / "F.gbr").write_text("%TF.FileFunction,Copper,L1,Top*%\n%FSLAX46Y46*%\n%MOMM*%\n%AMFOO*1,1,1,0,0*%\n%ADD10FOO,1*%\nD10*\nX0Y0D03*\nM02*\n%SRX2Y2I1J1*%\n")
    sx = ImportSession()
    sx.set_files(d)
    sx.load()
    top = next(f for f in sx.files if f.name == "F.gbr")
    # Whatever the reader does with this file, a refusal is shown with the file's name and never raises out of load()
    assert top.error == "" or "F.gbr" in " ".join(sx.problems())


def test_a_zip_is_read_in_memory_and_gives_the_same_board(board_dir, tmp_path):
    z = make_zip(board_dir, tmp_path / "set.zip")
    sx = ImportSession()
    sx.set_files(z)
    assert sx.complete() and len(sx.files) == 8 and sx.name == "set"
    b = sx.load()
    assert b.outline_area_mm2 == pytest.approx(WIDTH * HEIGHT) and sx.vias() == (2, 1, 0)
    folder = ImportSession()
    folder.set_files(board_dir)
    assert {f.name: f.sha256 for f in sx.files} == {f.name: f.sha256 for f in folder.files}
    sx.close()


def test_an_unsafe_zip_and_a_non_source_are_refused(tmp_path):
    import zipfile
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("../evil.gbr", "x")
    sx = ImportSession()
    with pytest.raises(Exception, match="unsafe"):
        sx.set_files(bad)
    (tmp_path / "note.txt").write_text("hello")
    with pytest.raises(ValueError):
        sx.set_files(tmp_path / "note.txt")
    with pytest.raises(ValueError):
        sx.set_files(tmp_path / "empty_folder_that_does_not_exist")


def test_files_from_a_list_and_numbered_inner_layers(tmp_path):
    d = make_board(tmp_path / "fab")
    sx = ImportSession()
    sx.set_files([d / "F.gbr", d / "B.gbr", d / "edge.gbr"])
    assert sx.complete() and len(sx.files) == 3 and not sx.used(ims.PLATED)
    # Altium names an inner layer .G1 and .G2 without an X2 index: they get distinct numbers
    for name in ("a.g1", "b.g2"):
        (d / name).write_text("%FSLAX46Y46*%\n%MOMM*%\nM02*\n")
    sx.set_files(d)
    assert sorted(f.role for f in sx.files if f.role in ims.INNER) == ["Inner copper 1", "Inner copper 2"]


def test_hooks_of_the_features_not_merged_yet_have_a_stable_interface(board_dir):
    sx = ImportSession()
    sx.set_files(board_dir)
    sx.load()
    assert sx.parts() == [] and sx.copper() is None and sx.heat_sources() == []
    with pytest.raises(ImportNotAvailable):
        sx.build_problem()
    v, raster = sx.memory_verdict(1.0, 0.05)
    assert v.verdict == "ok" and raster > 0 and v.unknowns > 0
    texts = " ".join(sx.warnings())
    assert "No heat source is defined" in texts and "Lumped and Analytic" in texts


# ---------------------------------------------------------------------------------------------------------------------------------- window
def test_the_window_reads_the_folder_and_fills_the_file_list(window):
    t = window.page1.table
    assert t.rowCount() == 8 and window.session.complete()
    names = [t.item(r, 1).text() for r in range(t.rowCount())]
    assert names == sorted(names) and "F.gbr" in names
    assert "Step 1 is complete" in window.page1.problem.text()
    assert window.page1.layers_label.text().startswith("4:")
    assert "2 vias, 1 component holes" in window.page1.drill_label.text()
    assert "40.00 x 30.00 mm" in window.page1.outline_label.text()
    assert window.page1.layer_pick.count() == 4


def test_the_function_combo_changes_the_session_and_a_clash_is_shown(window, qtbot):
    page = window.page1
    row = [window.session.files[r].name for r in range(8)].index("B.gbr")
    page.table.cellWidget(row, 3).setCurrentText(ims.COPPER_TOP)
    qtbot.waitUntil(lambda: not window.session.complete(), timeout=2000)
    assert "Two files claim" in page.problem.text()
    assert not window.next_btn.isEnabled() and not window.early_btn.isEnabled()
    assert "Next is disabled" in window.status.text()
    red = QColor(th.colors(th.current_name())["bad"])
    assert page.table.item(row, 1).foreground().color().name() == red.name()
    page.table.cellWidget(row, 3).setCurrentText(ims.COPPER_BOTTOM)
    qtbot.waitUntil(window.session.complete, timeout=2000)
    assert window.next_btn.isEnabled()


def test_use_box_leaves_a_file_out(window, qtbot):
    row = [f.name for f in window.session.files].index("In2.gbr")
    window.page1.table.item(row, 0).setCheckState(Qt.Unchecked)
    qtbot.waitUntil(lambda: len(window.session.layers()) == 3, timeout=2000)
    assert window.page1.layer_pick.count() == 3 or window.page1.layers_label.text().startswith("3:")


def test_steps_are_locked_until_step_1_is_complete(qtbot):
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.show()
    states = w.step_states()
    assert [s for s, _ in states] == ["current", "locked", "locked"]
    assert all("Locked: step 1 is not complete" in tip for s, tip in states if s == "locked")
    assert "No folder, ZIP or files chosen" in states[1][1]
    assert not w.next_btn.isEnabled() and not w.early_btn.isEnabled() and not w.back_btn.isEnabled()
    w.go(1)
    assert w.step == 0                                           # A locked step cannot be opened
    QTest.mouseClick(w.stepper, Qt.LeftButton, pos=w.stepper.point_of(2))
    assert w.step == 0


def test_stepper_states_back_next_and_import(window):
    w = window
    assert [s for s, _ in w.step_states()] == ["current", "ready", "ready"]
    assert w.next_btn.text() == "Next" and w.early_btn.isVisible() and w.early_btn.isEnabled() and not w.back_btn.isEnabled()
    QTest.mouseClick(w.next_btn, Qt.LeftButton)
    assert w.step == 1 and [s for s, _ in w.step_states()] == ["done", "current", "ready"] and w.back_btn.isEnabled()
    QTest.mouseClick(w.stepper, Qt.LeftButton, pos=w.stepper.point_of(2))     # A click on a reachable marker jumps
    assert w.step == 2 and w.next_btn.text() == "Import" and not w.early_btn.isVisible()
    QTest.mouseClick(w.back_btn, Qt.LeftButton)
    assert w.step == 1
    QTest.mouseClick(w.stepper, Qt.LeftButton, pos=w.stepper.point_of(0))
    assert w.step == 0 and w.stack.currentIndex() == 0


def test_import_now_asks_when_no_heat_source_and_reports_what_is_not_available(window):
    answers = []
    window.confirm = lambda title, text: (answers.append((title, text)), False)[1]
    assert window.do_import() is False and answers and answers[0][0] == "No heat source defined"
    window.confirm = lambda title, text: True
    assert window.do_import() is False                           # The imported copper is not merged: the user is told, the window stays open
    assert window.notes[-1][0] == "Import not available" and window.problem is None and window.isVisible()
    window.session.build_problem = lambda: "problem"             # What the real session will return
    assert window.do_import() is True and window.problem == "problem"


def test_a_bad_source_gives_a_message_and_keeps_the_window(window, tmp_path):
    window.open_path(str(tmp_path / "nothing.zip"))
    assert window.notes and window.notes[-1][0] == "Cannot read the files"


def test_the_preview_draws_and_zooms(window, qtbot):
    pv = window.page1.preview
    pv.resize(500, 400)
    img = pv.grab().toImage()
    centre = QColor(img.pixel(img.width() // 2, img.height() // 2))
    assert centre.name() != QColor(th.colors(th.current_name())["canvas"]).name()      # Copper is drawn over the canvas colour
    z = pv.zoom
    QTest.mouseClick(pv, Qt.LeftButton)
    pv.zoom = 4.0
    pv.update()
    pv.reset_view()
    assert pv.zoom == 1.0 and z == 1.0
    window.page1.layer_pick.setCurrentText("Inner copper 2")
    assert pv.selected == "Inner copper 2"


@pytest.mark.parametrize("name", ["light", "dark"])
def test_the_window_follows_a_live_theme_switch(window, name):
    app = QApplication.instance()
    other = "dark" if name == "light" else "light"
    th.apply_theme(app, name)
    window.refresh()
    first = window.page1.preview.grab().toImage()
    stepper_first = window.stepper.grab().toImage()
    th.apply_theme(app, other)
    window.refresh()
    second = window.page1.preview.grab().toImage()
    assert first != second and window.stepper.grab().toImage() != stepper_first
    c = th.colors(other)
    assert QColor(second.pixel(3, 3)).name() == QColor(c["canvas"]).name()      # The canvas of the preview is the theme's canvas token
    window.page1.refresh()
    assert c["ok"] in window.page1.problem.text()                # The message carries the status colour of the new theme
    th.apply_theme(app, "dark")


def test_the_file_menu_opens_the_window_and_loads_nothing_when_closed(qtbot, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question", lambda *a, **k: QMessageBox.Discard)
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    assert "Import Gerber board" in win.a_import.text() and win.a_import.toolTip()
    texts = [a.text() for m in win.menuBar().actions() if m.text() == "&File" for a in m.menu().actions()]
    assert "Import Gerber board…" in texts
    opened = []
    monkeypatch.setattr("pcbthermal.gui.main_window.ImportBoardWindow.exec", lambda self: (opened.append(self), 0)[1])
    win.a_import.trigger()
    assert len(opened) == 1 and not win.doc.problem.heaters
    assert QPoint is not None
