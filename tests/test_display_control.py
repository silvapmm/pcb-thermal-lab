#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_display_control.py
@brief The Display control of the main toolbar: the shared display state, the popover per context, the map button (no result, result, outdated, off by default), the card
       of the map on the board with its rings, the key T, the dot of an active underlay and the tabs that lost their own controls.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import copy

import numpy as np
import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pcbthermal import plots
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui import fieldscale
from pcbthermal.gui.display import DisplayPopover, DisplayState
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import TAB_BOARD, TAB_RESULTS, MainWindow
from pcbthermal.model import ImportRecord


@pytest.fixture(scope="module")
def sim():
    """!
    @brief One run of the FVM and the Lumped model on the example board (2 mm cell).
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=("fvm", "lumped"), cell_mm=2.0))


def _win(qtbot, tmp_path):
    """!
    @brief A main window on a private settings file, without a result.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return MainWindow.
    """
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win._load_problem(example_board(), "t")
    return win


def _with_result(win, sim):
    """!
    @brief Give a window a finished simulation, as a run does.
    @param win MainWindow.
    @param sim Simulation.
    """
    win.results.set_simulation(sim)
    win.sim, win._stale = sim, False
    win._update_map_button()


def test_the_toolbar_order_and_the_old_controls_are_gone(qtbot, tmp_path):
    win = _win(qtbot, tmp_path)
    seq = []
    for a in win.toolbar.actions():
        w = win.toolbar.widgetForAction(a)
        action_button = w is None or (hasattr(w, "defaultAction") and w.defaultAction() is a)
        seq.append("|" if a.isSeparator() else a.text() if action_button else (w.objectName() or type(w).__name__))
    # Layer combo, Map on/off, Display | Snap ... | Run
    k = seq.index("Temperature map on the board")
    assert seq[k - 1] == "QComboBox" and seq[k + 1] == "displayButton" and seq[k + 2] == "|" and seq[k + 3] == "QLabel" and seq[k + 4] == "QComboBox"
    assert seq[-2:] == ["|", "Run simulation"]
    for gone in ("editor_underlay", "overlay_opacity", "overlay_opacity_box", "overlay_sync"):
        assert not hasattr(win, gone), gone


def test_the_map_button_states_and_the_default_off(qtbot, tmp_path, sim):
    win = _win(qtbot, tmp_path)
    a = win.a_overlay
    assert a.isCheckable() and not a.isChecked() and not a.isEnabled() and a.toolTip() == "Run a simulation first"      # no result: greyed
    _with_result(win, sim)
    assert a.isEnabled() and not a.isChecked() and win.canvas._overlay is None                                           # a result: enabled, off
    a.setChecked(True)
    assert win.canvas._overlay is not None
    win.doc.set_props("heater", 0, power=3.0)                                                                           # the first edit
    assert win.canvas._overlay is None and not a.isChecked() and not a.isEnabled() and a.toolTip() == "The result is outdated: run the simulation again"
    win._on_done(sim)                                                                                                  # a new run (the design is as run)
    assert a.isEnabled() and not a.isChecked()


def test_the_key_t_toggles_the_map_and_says_why_when_it_cannot(qtbot, tmp_path, sim):
    win = _win(qtbot, tmp_path)
    assert win._hidden_overlay_key.shortcut() == QKeySequence("T")
    win._hidden_overlay_key.trigger()
    assert not win.a_overlay.isChecked() and win.statusBar().currentMessage() == "Run a simulation first"
    _with_result(win, sim)
    win._hidden_overlay_key.trigger()
    assert win.a_overlay.isChecked() and win.canvas._overlay is not None
    win._hidden_overlay_key.trigger()
    assert not win.a_overlay.isChecked() and win.canvas._overlay is None
    # the popover carries the same action, so the key keeps working while it is the active window
    assert win._hidden_overlay_key in win.display_popover.actions()


def test_the_popover_does_not_take_the_focus_and_reopens_on_the_last_control(qtbot, tmp_path):
    win = _win(qtbot, tmp_path)
    win.show()
    win.canvas.setFocus()
    before = QApplication.focusWidget()
    win._toggle_display_popover()
    pop = win.display_popover
    assert pop.isVisible() and pop.testAttribute(Qt.WA_ShowWithoutActivating) and win.display_button.focusPolicy() == Qt.NoFocus
    assert QApplication.focusWidget() is before                                  # the canvas keeps the keyboard (the key T)
    gp = win.display_button.mapToGlobal(win.display_button.rect().bottomLeft())
    area = win.display_button.screen().availableGeometry()
    # anchored under the button, moved left only as far as the screen edge needs (the offscreen screen is 800 pixels wide)
    assert pop.pos().y() == gp.y() and pop.pos().x() == min(gp.x(), area.right() + 1 - pop.width())
    pop.last_control = pop.cmap
    win._toggle_display_popover()
    assert not pop.isVisible()
    win._toggle_display_popover()
    assert pop.last_control is pop.cmap


def test_popover_controls_per_context(qtbot, tmp_path, sim):
    win = _win(qtbot, tmp_path)
    _with_result(win, sim)
    pop, r = win.display_popover, win.results
    # the board: Underlay, Map opacity, Colour map and View (Current, Smooth); Terrain and Contour greyed
    win.tabs.setCurrentIndex(TAB_BOARD)
    assert pop.context == "editor"
    assert pop.underlay.isEnabled() and pop.opacity.isEnabled() and pop.opacity_spin.isEnabled() and pop.cmap.isEnabled()
    assert pop.view.isEnabled() and not pop.contour.isEnabled()
    terrain = pop.view.model().item(pop.view.findData("terrain"))
    assert not terrain.isEnabled() and "Results tab" in terrain.toolTip() and pop.view.model().item(pop.view.findData("smooth")).isEnabled()
    # the Temperature map: everything, the contour step in K and only with Terrain
    win.tabs.setCurrentIndex(TAB_RESULTS)
    r.tabs.setCurrentWidget(r.temp)
    assert pop.context == "temperature" and pop.view.isEnabled() and "Temperature" in pop.contour_label.text() and pop.contour.suffix() == " K"
    assert not pop.contour.isEnabled() and not pop.contour_label.isEnabled()      # greyed, not hidden, unless View = Terrain
    pop.show()
    assert pop.contour.isVisibleTo(pop) and pop.contour_label.isVisibleTo(pop)
    win.display.set_view("terrain")
    assert pop.contour.isEnabled() and pop.contour_label.isEnabled()
    # the Gradients map: its own step, in K/mm with 'auto'
    r.tabs.setCurrentWidget(r.grad)
    assert pop.context == "gradient" and "Gradients" in pop.contour_label.text() and pop.contour.suffix() == " K/mm" and pop.contour.specialValueText() == "auto"
    assert pop.contour.value() == 0.0 and pop.contour.isEnabled()
    pop.contour.setValue(0.5)
    assert win.display.contour_grad == 0.5 and win.display.contour_temp == 5.0   # one value per map type
    r.tabs.setCurrentWidget(r.temp)
    assert pop.contour.value() == 5.0
    # the Animation: no Terrain, the step greyed, with a note
    r.tabs.setCurrentWidget(r.animation)
    assert pop.context == "animation" and not pop.contour.isEnabled()
    assert not pop.view.model().item(pop.view.findData("terrain")).isEnabled() and pop.note.text()
    assert r.animation.map_view() is None                                         # Terrain is drawn as Current in motion


def test_the_choices_work_before_a_run_and_are_kept_for_the_first_map(qtbot, tmp_path, sim):
    win = _win(qtbot, tmp_path)
    pop = win.display_popover
    pop.underlay.setCurrentIndex(1)
    pop.view.setCurrentIndex(pop.view.findData("smooth"))
    pop.cmap.setCurrentIndex(pop.cmap.findText("viridis"))
    pop.opacity_spin.setValue(40)
    pop.flush()
    _with_result(win, sim)
    v = win.results.temp.map_view()
    assert v.mode == "smooth" and v.show_copper and v.opacity == pytest.approx(0.4) and win.display.cmap == "viridis"
    win.a_overlay.setChecked(True)
    assert win.canvas._overlay_args["cmap"] == "viridis" and abs(win.canvas._overlay.opacity() - 0.4) < 1e-9


def test_one_state_for_every_map_and_the_tabs_lost_their_controls(qtbot, tmp_path):
    win = _win(qtbot, tmp_path)
    r = win.results
    assert r.display is win.display and all(t.display is win.display for t in (r.temp, r.grad, r.animation))
    for t in (r.temp, r.grad):
        for name in ("underlay", "opacity", "opacity_spin", "view", "contour", "contour_label", "cmap"):
            assert not hasattr(t, name), name
        assert t.model.count() == 0 and not hasattr(t, "layer")                   # Model stays (filled by a run); the layer is the toolbar choice
    assert not hasattr(r.animation, "view") and not hasattr(r.animation, "cmap") and not hasattr(r.animation, "underlay")
    assert hasattr(r.temp, "hot") and hasattr(r.temp, "auto") and hasattr(r.temp, "vmin")           # Hotspot and limits stay
    win.display.set_view("smooth")
    win.display.set_cmap("plasma")
    assert r.temp.map_view().mode == "smooth" and r.grad.map_view().mode == "smooth" and win.display.cmap == "plasma"


def test_the_gradients_tab_keeps_its_own_model_and_the_board_follows_the_temperature_tab(qtbot, tmp_path, sim):
    win = _win(qtbot, tmp_path)
    _with_result(win, sim)
    r = win.results
    r.grad.model.setCurrentIndex(r.grad.model.findData("lumped"))
    r.temp.model.setCurrentIndex(r.temp.model.findData("fvm"))
    win.a_overlay.setChecked(True)
    assert win.canvas._overlay_card["title"] == "FVM" and r.grad.model.currentData() == "lumped"
    r.temp.model.setCurrentIndex(r.temp.model.findData("lumped"))
    assert win.canvas._overlay_card["title"] == "Lumped"


def test_the_dot_badge_marks_an_active_underlay(qtbot, tmp_path):
    win = _win(qtbot, tmp_path)
    b = win.display_button
    assert b.property("dot") is False and b.toolTip()
    win.display.set_kind("copper")
    assert b.property("dot") is True
    win.display.set_kind("none")
    assert b.property("dot") is False
    # the two icons differ (the dot is drawn on the second)
    from pcbthermal.gui import theme as th

    on = th.tool_icon("display_dot", "light").pixmap(22, 22).toImage()
    off = th.tool_icon("display", "light").pixmap(22, 22).toImage()
    assert on != off


def test_the_card_text_the_rings_and_their_positions(qtbot, tmp_path, sim):
    win = _win(qtbot, tmp_path)
    _with_result(win, sim)
    win.a_overlay.setChecked(True)
    card = win.canvas._overlay_card
    ref = sim.results["fvm"]
    mask = fieldscale.inside_mask(sim.problem, ref.T[0].shape, ref.dx, ref.dy)
    f = np.where(mask, ref.T[0], np.nan)
    assert card["title"] == "FVM"
    assert card["tmax"] == pytest.approx(float(np.nanmax(f))) and card["tmin"] == pytest.approx(float(np.nanmin(f)))   # the two ends of the colour bar
    a = win.canvas._overlay_args
    assert (a["vmin"], a["vmax"]) == pytest.approx((card["tmin"], card["tmax"]))
    j, i = np.unravel_index(np.nanargmax(f), f.shape)
    assert card["pmax"] == pytest.approx(((i + 0.5) * ref.dx * 1000.0, (j + 0.5) * ref.dy * 1000.0))
    j, i = np.unravel_index(np.nanargmin(f), f.shape)
    assert card["pmin"] == pytest.approx(((i + 0.5) * ref.dx * 1000.0, (j + 0.5) * ref.dy * 1000.0))
    # the pixels: the card and the rings change the picture, and the rings have no text of their own
    win.canvas.resize(700, 520)
    win.canvas.show()
    win.canvas.fit()
    with_card = win.canvas.viewport().grab().toImage()
    win.canvas._overlay_card = None
    assert with_card != win.canvas.viewport().grab().toImage()


def test_extreme_points_use_the_samples_on_the_board_and_the_grid_points():
    f = np.array([[1.0, 2.0, 3.0], [9.0, 5.0, 0.0]])
    m = np.array([[True, True, True], [False, True, True]])               # the 9 is off the board, the 0 is on
    e = fieldscale.extreme_points(f, m, 0.001, 0.002)
    assert (e["tmax"], e["tmin"]) == (5.0, 0.0) and e["pmax"] == pytest.approx((1.5, 3.0)) and e["pmin"] == pytest.approx((2.5, 3.0))
    n = fieldscale.extreme_points(f, m, 0.001, 0.002, nodes=True)
    assert n["pmax"] == pytest.approx((1.0, 2.0))                           # a grid point sits at its own position
    assert fieldscale.extreme_points(np.full((2, 2), np.nan), None, 1, 1) is None


def test_a_refused_model_shows_only_the_title_in_the_alert_colour(qtbot, tmp_path):
    from tests.test_canvas_overlay import _t_problem

    p = _t_problem()
    s = simulate(p, SolverOptions(models=("fvm", "lumped"), cell_mm=2.0))
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win._load_problem(copy.deepcopy(p), "t")
    _with_result(win, s)
    win.results.temp.model.setCurrentIndex(win.results.temp.model.findData("lumped"))
    win.a_overlay.setChecked(True)
    card = win.canvas._overlay_card
    assert card["title"] == "Lumped: not drawn on an outline board (stretched map)" and card["tmax"] is None
    assert win.canvas._overlay is None and win.canvas.colourbar_geometry() is None
    win.canvas.resize(600, 450)
    win.canvas.show()
    assert win.canvas.viewport().grab().toImage() is not None                  # painting the title-only card does not raise
    win.results.temp.model.setCurrentIndex(win.results.temp.model.findData("fvm"))
    assert win.canvas._overlay is not None and win.canvas._overlay_card["title"] == "FVM"


def test_the_card_goes_with_the_map(qtbot, tmp_path, sim):
    win = _win(qtbot, tmp_path)
    _with_result(win, sim)
    win.a_overlay.setChecked(True)
    assert win.canvas._overlay_card is not None
    win.canvas.rebuild()                                                       # a rebuild of the scene keeps the card
    assert win.canvas._overlay_card is not None
    win.a_overlay.setChecked(False)
    assert win.canvas._overlay_card is None


def test_the_entries_are_the_same_for_every_project_type(qtbot, tmp_path):
    from tests.test_underlay_selector import _png, _quadrants

    win = _win(qtbot, tmp_path)
    keys = lambda: [k for _l, k in win.display.entries()]                       # noqa: E731
    assert keys() == ["none", "copper"]
    win.doc.project.view["background"] = {"path": _png(tmp_path / "bg.png", _quadrants()), "x_mm": 0.0, "y_mm": 0.0, "w_mm": 50.0, "h_mm": 40.0}
    win.doc.changed.emit()
    assert keys() == ["none", "copper", "image"]
    win.doc.project.imports = [ImportRecord(name="b")]
    win.doc.changed.emit()                                                      # Gerbers imported: Copper only
    assert keys() == ["none", "copper"]
    win.doc.project.imports = []
    win.doc.changed.emit()
    assert keys() == ["none", "copper", "image"]
    win.display.set_kind("copper")
    win.doc.project.imports = [ImportRecord(name="b")]
    win.doc.changed.emit()
    assert win.display.kind == "copper"                                        # an entry that stays valid is kept (as in the old Animation test)
    win.doc.project.imports = []
    win.doc.changed.emit()
    win.display.set_kind("image")
    win.doc.project.imports = [ImportRecord(name="b")]
    win.doc.changed.emit()
    assert win.display.kind == "none"                                           # a choice that is no longer valid goes back to None


def test_the_state_defaults_and_reset():
    d = DisplayState()
    assert (d.kind, d.opacity, d.view, d.cmap) == ("none", 70, "current", plots.CMAPS[0]) and d.contour_temp == 5.0 and d.contour_grad == 0.0
    d.set_kind("copper")
    d.set_opacity(120)
    d.set_view("terrain")
    d.set_cmap("not a map")
    assert (d.kind, d.opacity, d.view, d.cmap) == ("copper", 100, "terrain", plots.CMAPS[0])
    d.reset()
    assert (d.kind, d.opacity, d.view) == ("none", 70, "current")
    assert DisplayState().map_view("temperature", "light") is None            # the defaults draw the old picture, call for call
    pop = DisplayPopover(DisplayState())
    assert pop.rows["cmap"][1].toolTip() and pop.rows["view"][1].toolTip() and pop.rows["contour"][1].toolTip()


def test_a_click_in_the_open_list_of_a_combo_keeps_the_popover(qtbot, tmp_path):
    """!
    @brief The drop-down list of the Underlay combo is a window of its own: a click on an entry is inside the popover, not outside (the review found that the old
           `isAncestorOf` test closed the popover on that click, so no entry could be chosen with the mouse).
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    win = _win(qtbot, tmp_path)
    win.show()
    win._toggle_display_popover()
    pop = win.display_popover
    pop.underlay.showPopup()
    view = pop.underlay.view()
    assert not pop.isAncestorOf(view.viewport()) and view.viewport().window() is not pop      # the case the old rule missed
    QTest.mouseClick(view.viewport(), Qt.LeftButton, Qt.NoModifier, view.visualRect(view.model().index(1, 0)).center())
    assert pop.isVisible() and win.display.kind == "copper"
    QTest.mouseClick(win.canvas.viewport(), Qt.LeftButton)                       # a click on the board is outside: it closes
    assert not pop.isVisible()


def test_escape_in_the_window_closes_the_popover_without_reaching_the_canvas(qtbot, tmp_path):
    """!
    @brief The popover opened by the mouse does not have the keyboard, so Esc arrives at the canvas: it closes the popover and is consumed (it does not also cancel a drawing).
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    win = _win(qtbot, tmp_path)
    win.show()
    win.canvas.setFocus()
    win._toggle_display_popover()
    pop = win.display_popover
    seen = []
    orig = win.canvas.keyPressEvent
    win.canvas.keyPressEvent = lambda e: (seen.append(e.key()), orig(e))
    QTest.keyClick(win.canvas, Qt.Key_Escape)
    assert not pop.isVisible() and Qt.Key_Escape not in seen
    QTest.keyClick(win.canvas, Qt.Key_Escape)                                    # with the popover closed Esc reaches the canvas again
    assert Qt.Key_Escape in seen


def test_the_menu_entry_opens_the_popover_with_the_keyboard(qtbot, tmp_path):
    """!
    @brief View - Display settings is the keyboard route (the toolbar button takes no focus): the popover opens on a control that has the keyboard focus of its window.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    win = _win(qtbot, tmp_path)
    win.show()
    assert win.a_display in win.menuBar().actions()[2].menu().actions() and win.a_display.toolTip()
    assert win.display_button.accessibleName() == "Display"
    win.a_display.trigger()
    pop = win.display_popover
    assert pop.isVisible() and pop.focusWidget() is pop.underlay
    win.a_display.trigger()
    assert not pop.isVisible()


def test_the_popover_stays_on_the_screen(qtbot, tmp_path):
    """!
    @brief Near the right edge of the screen the popover is moved left so that it is whole (it hung off the screen before the review).
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    win = _win(qtbot, tmp_path)
    win.resize(1280, 800)
    win.show()
    area = win.display_button.screen().availableGeometry()
    win.move(area.right() - 500, area.top())
    win._toggle_display_popover()
    g = win.display_popover.frameGeometry()
    assert area.contains(g.topLeft()) and g.right() <= area.right()


def test_the_popover_closes_when_another_window_is_active(qtbot, tmp_path, monkeypatch):
    """!
    @brief The window loses the activation to another window: the popover closes; to the popover itself (a click in it): it stays.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture.
    """
    win = _win(qtbot, tmp_path)
    win.show()
    win._toggle_display_popover()
    pop = win.display_popover
    monkeypatch.setattr(QApplication, "activeWindow", staticmethod(lambda: pop))
    win._close_popover_if_inactive()
    assert pop.isVisible()
    other = MainWindow(Document(), QSettings(str(tmp_path / "o.ini"), QSettings.IniFormat))
    qtbot.addWidget(other)
    monkeypatch.setattr(QApplication, "activeWindow", staticmethod(lambda: other))
    win._close_popover_if_inactive()
    assert not pop.isVisible()


def test_the_key_d_opens_the_popover_with_the_keyboard_but_not_while_typing(qtbot, tmp_path):
    """!
    @brief The plain key D is a window-level shortcut of View - Display settings (the offscreen platform does not dispatch shortcuts, so the hidden action is triggered); a D typed in a field is text.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QLineEdit
    win = _win(qtbot, tmp_path)
    win.show()
    keyed = [a for a in win.actions() if [k.toString() for k in a.shortcuts()] == ["D"]]
    assert len(keyed) == 1 and keyed[0].shortcutContext() == Qt.WindowShortcut         # Same guard as G and T: a text field gets the key first
    pop = win.display_popover
    keyed[0].trigger()
    assert pop.isVisible() and pop.focusWidget() is pop.underlay
    pop.hide()
    edit = QLineEdit(win)                                                 # A text field: the letter is typed, nothing opens
    edit.show()
    edit.setFocus()
    QTest.keyClick(edit, Qt.Key_D)
    assert edit.text().lower() == "d" and not pop.isVisible()


def test_every_tab_change_closes_the_popover(qtbot, tmp_path, sim):
    """!
    @brief The popover closes on a click on a tab, on Ctrl+1 to Ctrl+4 and on the Results sub-tabs.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation fixture.
    """
    win = _win(qtbot, tmp_path)
    win.show()
    _with_result(win, sim)
    win.tabs.setCurrentIndex(TAB_RESULTS)
    pop = win.display_popover
    for change in (lambda: win.results.tabs.setCurrentIndex(1 - win.results.tabs.currentIndex()),   # the code route of a click on a sub-tab
                   lambda: win.results.tabs.setCurrentIndex(0),
                   lambda: win.tabs.setCurrentIndex(TAB_BOARD)):
        win._toggle_display_popover()
        assert pop.isVisible()
        change()
        assert not pop.isVisible()
    # Keyboard route: the Ctrl+number actions
    win._toggle_display_popover()
    assert pop.isVisible()
    for a in win.actions():
        if a.shortcut().toString() == "Ctrl+4":
            a.trigger()
    assert win.tabs.currentIndex() == 3 and not pop.isVisible()
    # Mouse route: a click on the tab bar
    win._toggle_display_popover()
    bar = win.tabs.tabBar()
    QTest.mouseClick(bar, Qt.LeftButton, pos=bar.tabRect(0).center())
    assert win.tabs.currentIndex() == 0 and not pop.isVisible()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_results_tab_has_no_horizontal_scroll_at_1280x800(qtbot, tmp_path, sim, theme):
    """!
    @brief At 1280 x 800 with both side docks open the control rows of the Results tabs wrap and the page has no horizontal scroll bar.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation fixture.
    @param theme "light" or "dark".
    """
    from pcbthermal.gui.flow import FlowLayout
    win = _win(qtbot, tmp_path)
    if win.theme_name != theme:
        win.toggle_theme()
    win.resize(1280, 800)
    win.show()
    _with_result(win, sim)
    win.tabs.setCurrentIndex(TAB_RESULTS)
    for d in (win.dock_board, win.dock_elements, win.dock_sim, win.dock_inspector):
        d.show()
    QApplication.processEvents()
    for i in range(win.results.tabs.count()):
        win.results.tabs.setCurrentIndex(i)
        QApplication.processEvents()
        page = win.results.tabs.currentWidget()
        lay = getattr(page, "layout", lambda: None)()
        controls = lay.itemAt(0).layout() if lay is not None and lay.count() else None
        if isinstance(controls, FlowLayout):
            # The row wraps when its parts do not fit on one line
            assert controls.sizeHint().width() <= page.width() or controls.line_count(page.width()) > 1
            assert controls.minimumSize().width() < controls.sizeHint().width()
        # No horizontal scroll bar anywhere above the page: the centre area and the Results tab widgets
        w = page
        while w is not None:
            for sb in w.findChildren(type(win.tabs.tabBar())) if False else []:
                pass
            w = w.parentWidget()
        from PySide6.QtWidgets import QScrollArea
        for area in win.findChildren(QScrollArea):
            if area.isVisible() and area.isAncestorOf(page):
                hb = area.horizontalScrollBar()
                assert hb.maximum() == 0, (area.objectName(), hb.maximum(), i)



def test_the_application_filter_is_installed_only_while_the_popover_is_open(qtbot, tmp_path, monkeypatch):
    """!
    @brief The click-outside filter watches every event of the application, so it is installed when the popover opens and removed when it closes (also when
           the window closes with it open): an event sent to an unrelated widget reaches the window's filter only while the popover is open.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param monkeypatch pytest fixture (counts the calls of the filter).
    """
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QWidget

    calls = []
    original = MainWindow.eventFilter

    def counting(self, obj, event):
        """!
        @brief The window's filter, counting the user events it sees.
        @param self MainWindow.
        @param obj Receiver.
        @param event The event.
        @return What the real filter returns.
        """
        if event.type() == QEvent.User:
            calls.append(obj)
        return original(self, obj, event)

    monkeypatch.setattr(MainWindow, "eventFilter", counting)
    win = _win(qtbot, tmp_path)
    win.show()
    other = QWidget()
    qtbot.addWidget(other)

    def seen():
        """!
        @brief Send one user event to an unrelated widget.
        @return True when the window's filter saw it.
        """
        n = len(calls)
        QApplication.sendEvent(other, QEvent(QEvent.User))
        return len(calls) > n

    assert not seen()                                                     # Closed at start: not installed
    win._toggle_display_popover()
    assert win.display_popover.isVisible() and seen()                     # Open: installed
    win._toggle_display_popover()
    assert not win.display_popover.isVisible() and not seen()             # Closed again: removed
    win._toggle_display_popover()
    win.close()                                                           # The window closes with the popover open: removed too
    assert not seen()


def test_a_deferred_close_after_the_popover_was_deleted_raises_nothing(qtbot, tmp_path):
    """!
    @brief A call queued while the popover was open must not touch it after Qt deleted it: no RuntimeError, no filter left behind.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    import shiboken6
    from PySide6.QtCore import QEvent, QTimer

    win = _win(qtbot, tmp_path)
    win._toggle_display_popover()
    assert win._popover_filter_on
    QTimer.singleShot(0, win._close_popover_if_inactive)      # The call that changeEvent queues on a loss of activation
    pop = win.display_popover
    pop.deleteLater()
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert not shiboken6.isValid(pop)
    assert win.display_popover is None and not win._popover_filter_on
    QApplication.processEvents()                              # The queued call runs now and must find nothing to close
    win._close_display_popover()                              # Idempotent
    win._close_display_popover()
    win._on_tab_changed()
    win._toggle_display_popover()
    assert not win._in_display_popover(win)


def test_the_view_can_be_chosen_on_the_board_and_is_kept(qtbot, tmp_path, sim):
    """!
    @brief Bug report on 2.5.2: with the map on the board the View stayed on Current. Current and Smooth now work there, Terrain says where it is shown.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation fixture.
    """
    win = _win(qtbot, tmp_path)
    _with_result(win, sim)
    win.tabs.setCurrentIndex(TAB_BOARD)
    win._toggle_display_popover()
    pop = win.display_popover
    win.a_overlay.setChecked(True)
    assert pop.view.isEnabled() and win.canvas._overlay.transformationMode() == Qt.FastTransformation
    pop.view.setCurrentIndex(pop.view.findData("smooth"))                         # the user's own click on the combo
    assert win.display.view == "smooth" and win.canvas._overlay.transformationMode() == Qt.SmoothTransformation
    assert win.canvas._overlay_args["smooth"] is True
    # a rebuild of the scene (layer change) keeps the smooth map, and so does another tab and back
    win.canvas.rebuild()
    assert win.canvas._overlay.transformationMode() == Qt.SmoothTransformation
    win.tabs.setCurrentIndex(TAB_RESULTS)
    win.tabs.setCurrentIndex(TAB_BOARD)
    assert win.display.view == "smooth" and win.canvas._overlay.transformationMode() == Qt.SmoothTransformation
    assert win.canvas._overlay is not None and pop.view.currentData() == "smooth"
    # Terrain chosen in the Results is drawn as Current on the board, and the entry explains itself
    win.display.set_view("terrain")
    assert win.canvas._overlay.transformationMode() == Qt.FastTransformation
    assert not pop.view.model().item(pop.view.findData("terrain")).isEnabled()
    pop.view.setCurrentIndex(pop.view.findData("current"))
    assert win.display.view == "current" and win.canvas._overlay is not None
    # undo and redo are not touched by the display choice
    n = len(win.doc.problem.heaters)
    win.doc.stack.undo()
    win.doc.stack.redo()
    assert len(win.doc.problem.heaters) == n


def test_smooth_on_the_board_interpolates_the_temperatures_like_the_results_map(qtbot, tmp_path, sim):
    """!
    @brief Smooth on the board means what it means in the Results maps: the temperatures are interpolated between the cells and then coloured, so every
           pixel is a colour of the bar (blending the colours of the cells is not), and the picture covers the same board as Current.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation fixture.
    """
    from matplotlib import colormaps

    from pcbthermal.gui import canvas as canvas_mod

    win = _win(qtbot, tmp_path)
    _with_result(win, sim)
    win.tabs.setCurrentIndex(TAB_BOARD)
    win.a_overlay.setChecked(True)
    item = win.canvas._overlay
    cur_rect, (nx, ny) = item.sceneBoundingRect(), (item.pixmap().width(), item.pixmap().height())
    win.display.set_view("smooth")
    item = win.canvas._overlay
    k = item.pixmap().width() // nx
    assert k == min(canvas_mod.OVERLAY_SMOOTH_FACTOR, canvas_mod.OVERLAY_SMOOTH_PIXELS // max(nx, ny)) and k > 1
    assert item.pixmap().height() == k * ny
    r = item.sceneBoundingRect()
    assert abs(r.width() - cur_rect.width()) < 1e-6 and abs(r.height() - cur_rect.height()) < 1e-6 and abs(r.left() - cur_rect.left()) < 1e-6
    # every pixel is a colour of the bar (a nearest entry of the 256-colour table within rounding)
    img = item.pixmap().toImage().convertToFormat(item.pixmap().toImage().Format.Format_RGBA8888)
    px = np.frombuffer(img.constBits(), np.uint8).reshape(img.height(), img.bytesPerLine())[:, : 4 * img.width()].reshape(img.height(), img.width(), 4)
    rgb = px[px[..., 3] > 0][:, :3].astype(int)
    table = (colormaps[win.display.cmap](np.linspace(0, 1, 256))[:, :3] * 255).astype(int)
    far = np.abs(rgb[:, None, :] - table[None, :, :]).sum(axis=2).min(axis=1)
    assert far.max() <= 6
    # back to Current: one pixel per cell again
    win.display.set_view("current")
    assert win.canvas._overlay.pixmap().width() == nx
