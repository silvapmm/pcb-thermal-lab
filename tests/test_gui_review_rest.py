#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_gui_review_rest.py
@brief Tests of the remaining items of the general GUI review (branch fix/gui-review-rest, releases/2.8.0/fem-model/GUI_FIX_PLAN.md, branch C).
"""

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtWidgets import QApplication

from pcbthermal.gui import theme as th
from tests.test_gui_stress import load, popups, run, win  # noqa: F401  (fixtures and helpers)


def _contrast(fg, bg):
    """!
    @brief WCAG 2.1 contrast ratio of two '#rrggbb' colours.
    @param fg Foreground colour.
    @param bg Background colour.
    @return float ratio, 1 to 21.
    """
    def lum(h):
        c = [int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    a, b = lum(fg), lum(bg)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


@pytest.mark.parametrize("name", ["light", "dark"])
def test_secondary_text_and_the_stop_button_read_in_both_themes(name):
    """!
    @brief The muted text reaches 4.5:1 on the window (it was 4.39:1 in the light theme) and the white label of Stop reaches 4.5:1 on its red fill.
    @param name Theme name.
    """
    c = th.THEMES[name]
    assert _contrast(c["muted"], c["window"]) >= 4.5
    assert _contrast(c["on_accent"], c["stop"]) >= 4.5
    assert _contrast(c["on_accent"], c["primary"]) >= 4.5


def test_the_run_button_turns_red_as_stop_and_the_status_line_keeps_its_height(win):
    """!
    @brief While a calculation runs the button carries the 'stop' property (the red fill of the theme), the slim progress bar shows, and the status line keeps the
           same height for a one-line and a two-line stage, so the Models box does not jump; idle, the bar is hidden with its place kept.
    @param win Main window fixture.
    """
    sp = win.solver_panel
    assert sp.progress.isHidden() and sp.progress.sizePolicy().retainSizeWhenHidden()
    sp.set_busy(True)
    assert sp.run.property("stop") is True and sp.run.text() == sp.STOP_TEXT
    sp.set_progress("Solving FVM", 0.5)
    y1 = sp.checks.mapTo(sp, sp.checks.rect().topLeft()).y()
    h1 = sp.status.height()
    sp.set_progress("Solving FEM (assembly and solve: a large board can take minutes)", 0.66)
    QApplication.processEvents()
    assert sp.status.height() == h1 and sp.checks.mapTo(sp, sp.checks.rect().topLeft()).y() == y1
    sp.set_busy(False)
    sp.set_running(False, "Cancelled.")
    assert sp.run.property("stop") is False and sp.progress.isHidden()


def test_the_status_bar_counts_the_seconds_of_a_running_calculation(win):
    """!
    @brief While busy the status bar names the stage and the elapsed seconds and how to stop; it never says 'Ready.' then.
    @param win Main window fixture.
    """
    win._on_busy(True)
    win.solver_panel.set_progress("Solving FVM", 0.2)
    msg = win.statusBar().currentMessage()
    assert msg.startswith("Calculating (") and " s): Solving FVM" in msg and "Ctrl+." in msg
    win._on_busy(False)
