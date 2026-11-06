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
    assert pop.pos() == gp                                                       # anchored under the button
    pop.last_control = pop.cmap
    win._toggle_display_popover()
    assert not pop.isVisible()
    win._toggle_display_popover()
    assert pop.last_control is pop.cmap


def test_popover_controls_per_context(qtbot, tmp_path, sim):
    win = _win(qtbot, tmp_path)
    _with_result(win, sim)
    pop, r = win.display_popover, win.results
    # the board: Underlay, Map opacity and Colour map; View and Contour greyed
    win.tabs.setCurrentIndex(TAB_BOARD)
    assert pop.context == "editor"
    assert pop.underlay.isEnabled() and pop.opacity.isEnabled() and pop.opacity_spin.isEnabled() and pop.cmap.isEnabled()
    assert not pop.view.isEnabled() and not pop.contour.isEnabled()
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
        assert t.model.count() == 0 and t.layer.count() == 0                      # Model and Layer stay (filled by a run)
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
