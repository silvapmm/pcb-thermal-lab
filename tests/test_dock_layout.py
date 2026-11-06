#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_dock_layout.py
@brief The side docks (Board settings, Simulation settings, Elements, Properties) show no horizontal scroll bar at 380, 420 and 460 px in both themes, for a drawn board and for an imported one.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QAbstractScrollArea, QApplication

from pcbthermal.gui import import_session as ims
from pcbthermal.gui import theme
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow
from tests.helpers.synthetic_board import make_board

WIDTHS = (380, 420, 460)


def _document(kind, tmp_path):
    """!
    @brief A Document with a drawn example board or an imported synthetic one.
    @param kind "drawn" or "imported".
    @param tmp_path Temporary folder.
    @return Document
    """
    doc = Document()
    if kind == "drawn":
        doc.open(os.path.join(os.path.dirname(__file__), "..", "examples", "example_board.pcbt.json"))
        return doc
    sx = ims.ImportSession()
    sx.set_files(str(make_board(tmp_path / "fab", inner=0)))
    sx.load()
    doc.open_import(sx.build_problem(), sx.record)
    return doc


@pytest.mark.parametrize("kind", ["drawn", "imported"])
@pytest.mark.parametrize("mode", ["light", "dark"])
def test_docks_do_not_scroll_sideways(qtbot, tmp_path, mode, kind):
    """!
    @brief Every dock at three widths: no visible horizontal scroll bar and no content wider than its viewport.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param mode Theme name.
    @param kind Board kind (drawn or imported).
    """
    theme.apply_theme(QApplication.instance(), mode)
    win = MainWindow(_document(kind, tmp_path), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.resize(1600, 1000)
    win.show()
    for dock in (win.dock_board, win.dock_sim, win.dock_elements, win.dock_inspector):
        for w in WIDTHS:
            win.resizeDocks([dock], [w], Qt.Horizontal)
            QApplication.processEvents()
            for area in dock.findChildren(QAbstractScrollArea):
                if not area.isVisible():
                    continue
                where = f"{mode} {kind} {dock.objectName()} {w}px {type(area).__name__}"
                assert not area.horizontalScrollBar().isVisible(), where
                inner = area.widget() if hasattr(area, "widget") else None
                if inner is not None:
                    assert inner.minimumSizeHint().width() <= area.viewport().width(), where
