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


def test_a_fem_mesh_above_the_cap_says_which_cell_to_use_and_that_cell_fits():
    """!
    @brief The FEM refusal for too many unknowns names a cell, like the memory lines of the other models, and a mesh at that cell is accepted; the live
           warning has a whole title (it was cut to 'The finite-element model').
    """
    import re

    from pcbthermal import femmesh
    from pcbthermal.checks import check_input, is_fem_left_out, warning_title
    from pcbthermal.model import Problem

    p = Problem.new(400, 300, layers=4)
    p.add_full_copper()
    p.add_heater(1, 5.0, rect=(190, 140, 210, 160), name="U1")
    for cell in (0.25, 0.5, 0.7):
        with pytest.raises(ValueError) as exc:
            femmesh.unknowns(p, cell)
        m = re.search(r"use a cell of about (\d+\.\d) mm or more", str(exc.value))
        assert m, str(exc.value)
        assert femmesh.unknowns(p, float(m.group(1)))[0] <= femmesh.FEM_MAX_UNKNOWNS
    w = [str(x) for x in check_input(p, ("fvm", "fem"), cell_mm=0.5, live=True)]
    fem = [x for x in w if is_fem_left_out(x)]
    assert fem and warning_title(fem[0]) == "The FEM (finite elements) will be left out" and "use a cell of about" in fem[0]


def test_the_memory_lines_and_the_warning_rows_use_one_dot_painter(win, monkeypatch):
    """!
    @brief Every dot of the window comes from gui/dots.py: the memory lines (rich text) embed the picture of dots.dot_pixmap, as the warning rows draw it.
    @param win Main window fixture.
    @param monkeypatch pytest fixture.
    """
    from pcbthermal.examples import example_board
    from pcbthermal.gui import dots

    calls = []
    real = dots.dot_pixmap
    monkeypatch.setattr(dots, "dot_pixmap", lambda *a: calls.append(a) or real(*a))
    monkeypatch.setattr(dots, "_HTML_CACHE", {})
    load(win, example_board())
    win.doc.set_options(models=("fvm", "fem"), cell_mm=1.0)
    QApplication.processEvents()
    text = win.solver_panel.cells_label.text()
    assert text.count('src="data:image/png;base64,') >= 2 and calls
    assert "●" not in text


def test_the_elements_header_is_not_cut_on_an_empty_board(win):
    """!
    @brief On a new empty board the Elements list keeps every header whole ('Layer' was cut to 'Laye').
    @param win Main window fixture.
    """
    from pcbthermal.model import Problem

    load(win, Problem.new(100, 80, layers=2))
    tree = win.elements.tree
    head = tree.header()
    for c in range(3):
        assert head.sectionSize(c) >= head.fontMetrics().horizontalAdvance(tree.headerItem().text(c)) + 16


@pytest.mark.parametrize("case", ["block", "source"])
def test_the_right_docks_never_scroll_sideways_at_their_narrowest(win, case):
    """!
    @brief A dock's scroll area is never narrower than its content plus the vertical bar: no sideways bar in the Simulation dock dragged to 300 px, nor in the
           Properties of a metal block (it asked 337 px) or of a heat source.
    @param win Main window fixture.
    @param case Element shown in Properties.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QScrollArea

    from pcbthermal.examples import example_board

    p = example_board()
    p.add_heatsink(1, 50.0, rect=(5, 5, 20, 20), name="Block", thickness_mm=3.0)
    load(win, p)
    if case == "block":
        win._select_from_warning("heatsink", len(p.heatsinks) - 1)
    else:
        win.doc.set_props("heater", 1, role="source")
        win._select_from_warning("heater", 1)
    QApplication.processEvents()
    win.resizeDocks([win.dock_sim, win.dock_inspector], [300, 300], Qt.Horizontal)
    QApplication.processEvents()
    for d in (win.dock_sim, win.dock_inspector):
        for a in d.findChildren(QScrollArea):
            assert a.horizontalScrollBar().maximum() == 0, (d.windowTitle(), a.width(), a.widget().minimumSizeHint().width())


def test_the_ruler_corner_holds_only_the_unit(win):
    """!
    @brief The corner square of the rulers shows the unit 'mm' and nothing else, whatever the pan (the ticks of both rulers were drawn through the letters).
    @param win Main window fixture.
    """
    from PySide6.QtGui import QColor, QImage, QPainter, QPen

    from pcbthermal.examples import example_board

    load(win, example_board())
    view = win.canvas
    c = th.colors(view.theme)

    def corner(draw):
        img = QImage(40, 40, QImage.Format_RGB32)
        img.fill(QColor(c["canvas"]))
        p = QPainter(img)
        draw(p)
        p.end()
        return [img.pixel(x, y) for x in range(18) for y in range(18)]

    def only_unit(p):
        p.setPen(QPen(QColor(c["text"])))
        font = p.font()
        font.setPointSizeF(7.5)
        p.setFont(font)
        p.drawText(2, 12, "mm")

    want = corner(only_unit)
    for _ in range(12):
        view.horizontalScrollBar().setValue(view.horizontalScrollBar().value() + 7)
        view.verticalScrollBar().setValue(view.verticalScrollBar().value() + 5)
        assert corner(view._paint_rulers) == want


def test_an_empty_board_shows_the_first_steps_and_the_hint_goes_with_the_first_element(win):
    """!
    @brief A new board has no element: the canvas shows the first-step hint; after the first heater it is gone.
    @param win Main window fixture.
    """
    from pcbthermal.model import Problem

    load(win, Problem.new(100, 80, layers=2))
    assert win.canvas.empty_hint_shown() and "Run (F5)" in win.canvas.EMPTY_HINT
    win.doc.problem.add_heater(1, 1.0, rect=(40, 30, 50, 40), name="U1")
    win.doc.changed.emit()
    assert not win.canvas.empty_hint_shown()


def test_open_recent_lists_the_projects_newest_first_and_drops_missing_files(win, tmp_path):
    """!
    @brief File - Open recent lists the projects opened or saved, newest first; a file that was deleted leaves the list; the menu is greyed when it is empty.
    @param win Main window fixture.
    @param tmp_path pytest fixture.
    """
    from pcbthermal.examples import example_board
    from pcbthermal.project import Project, save_project

    win.settings.setValue("recent_files", [])
    win._fill_recent_menu()
    assert not win.recent_menu.isEnabled()
    paths = []
    for name in ("a", "b"):
        path = tmp_path / f"{name}.pcbt.json"
        save_project(str(path), Project(problem=example_board()))
        paths.append(str(path))
        win.open_file(str(path))
    assert win.recent_files()[:2] == [paths[1], paths[0]]
    texts = [a.text() for a in win.recent_menu.actions() if a.text()]
    assert texts[0].endswith("b.pcbt.json") and texts[1].endswith("a.pcbt.json") and win.recent_menu.isEnabled()
    os_remove = __import__("os").remove
    os_remove(paths[0])
    assert paths[0] not in win.recent_files()
