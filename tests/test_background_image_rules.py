#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_background_image_rules.py
@brief The background image dialog (opacity slider linked with a box) and the rule that an imported (Gerber) project cannot get an image, only lose one.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QPushButton

from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import BACKGROUND_IMPORTED_TIP, BackgroundDialog, MainWindow
from pcbthermal.model import ImportRecord

BG = {"path": "/x/photo.png", "x_mm": 1.0, "y_mm": 2.0, "w_mm": 30.0, "h_mm": 20.0, "opacity": 0.25}


def _win(qtbot, tmp_path):
    """!
    @brief A main window on a private settings file.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return MainWindow.
    """
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    return win


def test_dialog_has_no_opacity_and_keeps_a_stored_one(qtbot):
    d = BackgroundDialog(dict(BG), (50.0, 40.0))
    qtbot.addWidget(d)
    assert not hasattr(d, "opacity") and not hasattr(d, "opacity_box")
    assert d.config()["opacity"] == pytest.approx(0.25)             # An old project keeps its value (the initial opacity of the map over the image)
    d2 = BackgroundDialog(None, (50.0, 40.0))
    qtbot.addWidget(d2)
    d2.path = "a.png"
    assert "opacity" not in d2.config()


def test_drawn_project_keeps_the_action_enabled(qtbot, tmp_path):
    win = _win(qtbot, tmp_path)
    win._update_background_action()
    assert win.a_bg.isEnabled()


def test_imported_project_disables_the_action_and_the_call(qtbot, tmp_path, monkeypatch):
    win = _win(qtbot, tmp_path)
    win.doc.project.imports = [ImportRecord(name="b")]
    win.doc.changed.emit()
    assert not win.a_bg.isEnabled() and "Gerber" in win.a_bg.toolTip()
    shown = []
    monkeypatch.setattr(BackgroundDialog, "exec", lambda self: shown.append(self) or 0)
    win.set_background()                                  # Other paths than the menu are refused too
    assert not shown and "background" not in win.doc.project.view


def test_old_project_with_both_loads_and_offers_removal(qtbot, tmp_path, monkeypatch):
    win = _win(qtbot, tmp_path)
    win.doc.project.view["background"] = dict(BG)
    win.doc.project.imports = [ImportRecord(name="b")]
    win.doc.changed.emit()
    assert win.a_bg.isEnabled() and BACKGROUND_IMPORTED_TIP in win.a_bg.toolTip()
    assert win.doc.project.view["background"]["path"] == BG["path"]        # Nothing is deleted silently

    def remove_it(self):
        assert self.path and self.remove_btn.isEnabled()
        self._remove()
        return 1
    monkeypatch.setattr(BackgroundDialog, "exec", remove_it)
    win.set_background()
    assert "background" not in win.doc.project.view


def test_dialog_of_an_imported_project_cannot_choose(qtbot):
    d = BackgroundDialog(dict(BG), (50.0, 40.0), imported=True)
    qtbot.addWidget(d)
    btn = [b for b in d.findChildren(QPushButton) if b.text() == "Choose image…"][0]
    assert not btn.isEnabled() and btn.toolTip() == BACKGROUND_IMPORTED_TIP
    assert d.config()["opacity"] == pytest.approx(0.25)
    d._remove()
    assert d.config() is None
