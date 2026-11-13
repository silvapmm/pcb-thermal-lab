#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_window_growth.py
@brief A window never grows because of its content: the import window and the main window keep their width when a Gerber set with very long file names, many problems or
       a long status text is read, when real boards are imported over an open project, and when a saved geometry is absurd.
@details The cause found for the report 'the window grew all over horizontally after I imported other Gerbers': the status line and the subtitle of the import window were
         QLabels without word wrap, whose minimum width is the width of their text (the list of problems names every file), so the minimum width of the whole window
         reached 4000 px and the window was widened to hold it. They are `ElidedLabel` now.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

import shutil

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QLabel

from pcbthermal.gui import import_window as iw
from pcbthermal.gui.document import Document
from pcbthermal.gui.elided import ElidedLabel, clamp_to_screen
from pcbthermal.gui.main_window import MainWindow
from tests.helpers.synthetic_board import make_board
from tests.test_reimport_matrix import app, base, library  # noqa: F401  (fixtures)

LONG = "x_long_file_name_" * 40


def screen_width(widget):
    """!
    @brief Width in pixels of the available area of the screen of a widget.
    @param widget QWidget.
    @return int
    """
    return widget.screen().availableGeometry().width()


def test_elided_label_never_asks_for_width(qtbot):
    """!
    @brief The label reports a zero minimum width for any text, keeps the whole text and shows it in the tooltip.
    @param qtbot pytest-qt fixture.
    """
    lab = ElidedLabel("short")
    qtbot.addWidget(lab)
    lab.setText(LONG)
    assert lab.minimumSizeHint().width() == 0 and lab.sizeHint().width() == 0
    assert lab.text() == LONG and lab.toolTip() == LONG


def test_clamp_to_screen_cuts_an_absurd_size(qtbot):
    """!
    @brief A window of 9000 x 9000 px is cut to the available area of its screen.
    @param qtbot pytest-qt fixture.
    """
    w = QLabel("x")
    qtbot.addWidget(w)
    w.resize(9000, 9000)
    assert clamp_to_screen(w)
    area = w.screen().availableGeometry()
    assert w.width() <= area.width() and w.height() <= area.height()


def test_the_main_window_does_not_restore_an_absurd_geometry(qtbot, tmp_path):
    """!
    @brief A saved geometry of a huge window (another screen, a damaged settings file) gives a window that fits this screen.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    first = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(first)
    first.resize(9000, 5000)
    settings = QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat)
    settings.setValue("geometry", first.saveGeometry())
    settings.sync()
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    area = win.screen().availableGeometry()
    assert win.width() <= area.width() and win.height() <= area.height()


def test_the_import_window_keeps_its_width_with_long_names_and_many_problems(qtbot, tmp_path):
    """!
    @brief A set whose files have very long names, with every other file unticked and 200 problems in the status line, leaves the import window within the screen
           and its minimum width within 1.2 times the one of the empty window.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    src = make_board(tmp_path / "set", inner=0)
    for f in list(src.iterdir()):
        shutil.copy(f, src / (("a_long_file_name_" * 12) + f.name))   # 200 characters, within the 255 of a file system
        f.unlink()
    win = iw.ImportBoardWindow()
    qtbot.addWidget(win)
    win.show()
    QApplication.processEvents()
    empty = win.minimumSizeHint().width()
    win.confirm = lambda *a: True
    win.notify = lambda *a: None
    win.open_path(str(src))
    for i in range(len(win.session.files)):
        win.session.set_use(i, False)
    win.reload()
    win.status.setText("Next is disabled: " + "; ".join(f"{LONG}{i} cannot be read" for i in range(200)))
    for step in (0, 1, 2):
        win.go(step)
        QApplication.processEvents()
        assert win.minimumSizeHint().width() <= max(1.2 * empty, 1.2 * 800)
        assert win.width() <= screen_width(win)


def test_no_unwrapped_label_of_the_import_window_widens_it(qtbot):
    """!
    @brief Any QLabel of the import window without word wrap, given a text of 700 characters, leaves the minimum width of the window as it was (generic guard).
    @param qtbot pytest-qt fixture.
    """
    src = os.path.join(os.environ.get("PCBT_REAL_BOARDS", ""), "rp2040")
    if not os.path.isdir(src):
        pytest.skip("the library boards are not linked (PCBT_REAL_BOARDS)")
    win = iw.ImportBoardWindow()
    qtbot.addWidget(win)
    win.show()
    win.confirm = lambda *a: True
    win.notify = lambda *a: None
    win.open_path(src)
    for step in (0, 1, 2):
        win.go(step)
        QApplication.processEvents()
        base_w = win.minimumSizeHint().width()
        for lab in win.findChildren(QLabel):
            if lab.wordWrap():
                continue
            old = lab.text()
            lab.setText(LONG)
            QApplication.processEvents()
            grown = win.minimumSizeHint().width()
            lab.setText(old)
            assert grown <= base_w + 20, f"step {step}: a {type(lab.parent()).__name__} label ({old[:30]!r}) widens the window to {grown} px"


@pytest.mark.parametrize("keys", [["rp2040", "co60", "oswlight", "vstcm", "isastm", "cmm2", "stickhub"]])
def test_importing_other_boards_over_an_open_project_keeps_the_main_window(app, keys):
    """!
    @brief Real boards imported one after the other (Replace and Update) through the real main window: its size, size hint and minimum size hint do not grow.
    @param app Application driver of test_reimport_matrix.
    @param keys Library board keys.
    """
    win = app.win
    win.resize(1480, 900)
    win.show()
    QApplication.processEvents()
    before = (win.width(), win.sizeHint().width(), win.minimumSizeHint().width())
    for key in keys:
        src = library(key)
        for mode in ("replace", "update"):
            app.run(src, mode)
            QApplication.processEvents()
            assert win.width() == before[0]
            assert win.sizeHint().width() <= 1.2 * before[1] and win.minimumSizeHint().width() <= 1.2 * before[2]
            assert win.width() <= screen_width(win) or before[0] > screen_width(win)


def test_the_status_line_wraps_the_reason_on_up_to_three_lines(qtbot):
    """!
    @brief The status line says why Next is disabled: a reason that fits two lines is drawn whole (no ellipsis), a longer one takes three lines and ends with an ellipsis;
           the width it asks for stays zero and the whole text is the tooltip and the accessible description (review: one elided line hid the reason).
    @param qtbot pytest-qt fixture.
    """
    lab = ElidedLabel("", max_lines=3)
    qtbot.addWidget(lab)
    lab.resize(400, 60)
    words = "Two files claim 'Placement (pick and place)': cpl_jlc.csv and pos.csv"
    lab.setText(words)
    lines = lab._lines(400)
    assert 1 <= len(lines) <= 2 and " ".join(lines) == words                    # the whole reason, wrapped at spaces
    lab.setText("Next is disabled: " + "; ".join(f"{LONG}{i} cannot be read" for i in range(20)))
    lines = lab._lines(400)
    assert len(lines) == 3 and lines[-1].endswith("…")
    assert all(lab.fontMetrics().horizontalAdvance(t) <= 400 for t in lines)    # a word longer than the line is cut inside the word
    assert lab.heightForWidth(400) == 3 * lab.fontMetrics().lineSpacing() + 2
    assert lab.minimumSizeHint().width() == 0 and lab.sizeHint().width() == 0
    assert lab.toolTip() == lab.text() == lab.accessibleDescription()


def test_the_import_window_status_shows_the_reason_whole_at_its_size(qtbot, tmp_path):
    """!
    @brief The import window at its normal size shows a typical reason for a disabled Next whole on the status line (not cut to one line).
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    win = iw.ImportBoardWindow()
    qtbot.addWidget(win)
    win.resize(1000, 700)
    win.show()
    reason = ("Next is disabled: Two files claim 'Placement (pick and place)': cpl_jlc_very_long_name_of_the_assembly_house.csv and "
              "pos_very_long_name_of_the_cad_export.csv; No drill file: no vias are imported")
    win.status.setText(reason)
    QApplication.processEvents()
    lines = win.status._lines(win.status.contentsRect().width())
    assert " ".join(lines) == reason and win.status.height() >= len(lines) * win.status.fontMetrics().lineSpacing()


def test_a_normal_saved_geometry_is_restored_unchanged(qtbot, tmp_path):
    """!
    @brief A saved main-window geometry that fits the screen is restored as it was (the clamp only acts on a window larger than its screen).
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    first = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(first)
    area = first.screen().availableGeometry()
    first.setGeometry(area.left() + 20, area.top() + 30, min(700, area.width() - 40), min(500, area.height() - 40))
    size = first.size()
    settings = QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat)
    settings.setValue("geometry", first.saveGeometry())
    settings.sync()
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    assert win.size() == size
