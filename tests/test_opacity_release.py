#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_opacity_release.py
@brief The opacity controls (Results maps, Animation, editor overlay) redraw once per finished edit: a drag redraws nothing, the release redraws once, keys and typing wait for a pause.
@details The box follows a drag live; the slider released, Enter in the box, or the debounce timer after a key or wheel step end an edit.
"""

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QSlider, QSpinBox

from pcbthermal.gui.underlay import OPACITY_DEBOUNCE_MS, ReleaseSync, UnderlayControls
from tests.test_underlay_selector import _win


def _pair():
    """!
    @brief A slider and a box with a ReleaseSync that records its calls.
    @return Tuple (slider, box, sync, calls).
    """
    s, b = QSlider(), QSpinBox()
    for w in (s, b):
        w.setRange(0, 100)
    b.setKeyboardTracking(False)
    calls = []
    return s, b, ReleaseSync(s, b, calls.append), calls


def test_drag_redraws_nothing_and_the_release_redraws_once(qtbot):
    """!
    @brief While the slider is down the box shows the value and nothing is called; the release calls once with the final value.
    @param qtbot pytest-qt fixture.
    """
    s, b, sync, calls = _pair()
    qtbot.addWidget(s)
    s.setSliderDown(True)
    for v in (10, 40, 80):
        s.setValue(v)
        assert b.value() == v                      # the label is live
    qtbot.wait(2 * OPACITY_DEBOUNCE_MS)
    assert calls == []                             # still dragging: no redraw, however long
    s.setSliderDown(False)                         # emits sliderReleased
    assert calls == [80]
    qtbot.wait(2 * OPACITY_DEBOUNCE_MS)
    assert calls == [80]                           # and not again after the pause


def test_keys_and_wheel_are_debounced_into_one_call(qtbot):
    """!
    @brief A run of steps without the mouse draws once, after the pause.
    @param qtbot pytest-qt fixture.
    """
    s, b, sync, calls = _pair()
    qtbot.addWidget(s)
    for v in (1, 2, 3, 4, 5):
        s.setValue(v)
    assert calls == []
    qtbot.waitUntil(lambda: calls == [5], timeout=2000)
    qtbot.wait(2 * OPACITY_DEBOUNCE_MS)
    assert calls == [5]


def test_box_edit_is_applied_on_enter_or_after_the_pause(qtbot):
    """!
    @brief The box moves the slider silently; editingFinished applies at once, otherwise the pause does.
    @param qtbot pytest-qt fixture.
    """
    s, b, sync, calls = _pair()
    qtbot.addWidget(b)
    b.setValue(30)
    assert s.value() == 30 and calls == []
    b.editingFinished.emit()
    assert calls == [30]
    b.setValue(55)
    qtbot.waitUntil(lambda: calls == [30, 55], timeout=2000)


def test_underlay_controls_and_editor_overlay_use_it(qtbot, tmp_path):
    """!
    @brief The Results/Animation underlay and the editor overlay opacity redraw on release only; their numeric box stays live.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    win = _win(qtbot, tmp_path)
    u = win.results.temp.underlay
    assert isinstance(u, UnderlayControls)
    drawn = []
    u.changed.connect(lambda: drawn.append(u.value()))
    u.combo.setCurrentIndex(1)
    drawn.clear()
    u.opacity.setSliderDown(True)
    u.opacity.setValue(20)
    u.opacity.setValue(30)
    assert u.opacity_spin.value() == 30 and drawn == []
    u.opacity.setSliderDown(False)
    assert drawn == [0.3]
    # the editor overlay of the main window
    seen = []
    win.overlay_sync.callback = seen.append
    win.overlay_opacity.setEnabled(True)
    win.overlay_opacity.setSliderDown(True)
    win.overlay_opacity.setValue(10)
    win.overlay_opacity.setValue(15)
    assert win.overlay_opacity_box.value() == 15 and seen == []
    win.overlay_opacity.setSliderDown(False)
    assert seen == [15]
