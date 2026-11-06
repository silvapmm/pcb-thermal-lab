#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_animation_underlay.py
@brief The Animation tab offers the same Underlay entries as the Temperature tab for every project type and follows (and leads) its choice; Terrain is never offered there.
@details Checked on a new project, with a background image, after a project is opened (document change), after Gerbers are imported, and with a window open.
"""

import pytest

pytest.importorskip("pytestqt")

from pcbthermal.model import ImportRecord
from tests.test_underlay_selector import _entries, _png, _quadrants, _win


def _all(win):
    """!
    @brief The underlay controls of every tab that draws a map.
    @param win MainWindow.
    @return List of UnderlayControls: Temperature, Gradients, Animation, editor toolbar.
    """
    r = win.results
    return [r.temp.underlay, r.grad.underlay, r.animation.underlay, win.editor_underlay]


def test_same_entries_for_every_project_type(qtbot, tmp_path):
    """!
    @brief New, with an image, reopened and imported projects: Animation lists exactly what Temperature lists (Gerber: None and Copper only).
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    win = _win(qtbot, tmp_path)
    assert all(_entries(u) == ["none", "copper"] for u in _all(win))                      # hand drawn, no image
    win.doc.project.view["background"] = {"path": _png(tmp_path / "bg.png", _quadrants()), "x_mm": 0.0, "y_mm": 0.0, "w_mm": 50.0, "h_mm": 40.0}
    win.doc.changed.emit()                                                                # a project opened or a background set
    assert all(_entries(u) == ["none", "copper", "image"] for u in _all(win))
    win.doc.project.imports = [ImportRecord(name="b")]
    win.doc.changed.emit()                                                                # Gerbers imported
    assert all(_entries(u) == ["none", "copper"] for u in _all(win))
    win.doc.project.imports = []
    win.doc.changed.emit()                                                                # back to the hand-drawn project: the image returns
    assert _entries(win.results.animation.underlay) == _entries(win.results.temp.underlay) == ["none", "copper", "image"]


def test_animation_never_offers_terrain(qtbot, tmp_path):
    """!
    @brief The View box of the Animation lists Current and Smooth only.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    anim = _win(qtbot, tmp_path).results.animation
    assert [anim.view.itemData(i) for i in range(anim.view.count())] == ["current", "smooth"]


def test_the_choice_is_shared_both_ways(qtbot, tmp_path):
    """!
    @brief Copper chosen on the Temperature tab shows on the Animation (with the opacity) and the other way round, and the editor combo follows.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    win = _win(qtbot, tmp_path)
    r = win.results
    r.temp.underlay.combo.setCurrentIndex(1)
    assert r.animation.underlay.kind() == "copper" and r.grad.underlay.kind() == "copper"
    r.grad.underlay.opacity.setValue(35)
    assert r.animation.underlay.opacity.value() == 35 and r.temp.underlay.opacity.value() == 35
    r.animation.underlay.combo.setCurrentIndex(0)
    assert r.temp.underlay.kind() == r.grad.underlay.kind() == win.editor_underlay.kind() == "none"
    r.animation.underlay.combo.setCurrentIndex(1)
    r.animation.underlay.opacity.setValue(20)
    assert r.temp.underlay.kind() == "copper" and r.temp.underlay.opacity.value() == 20 and win.editor_underlay.kind() == "copper"
    win.doc.project.imports = [ImportRecord(name="b")]
    win.doc.changed.emit()                                                                # an entry that stays valid is kept
    assert r.animation.underlay.kind() == "copper"
