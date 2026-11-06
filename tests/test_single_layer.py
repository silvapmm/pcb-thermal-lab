#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_single_layer.py
@brief The single layer choice of the toolbar (list per context, the fallback rule and its one-line note, the editor and the maps on one choice, the removed tab boxes,
       the tooltips) and the model name of the card of the map on the board (click, menu, refused models, focus).
"""

import copy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QEvent, QPoint, QPointF, QSettings, Qt
from PySide6.QtGui import QMouseEvent

from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui import layerchoice as lc
from pcbthermal.gui import tips
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import TAB_BOARD, TAB_PROFILE, TAB_RESULTS, TAB_STACKUP, MainWindow


@pytest.fixture(scope="module")
def sim():
    """!
    @brief One FVM and Lumped run of the example board (2 mm cell).
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=("fvm", "lumped"), cell_mm=2.0))


def _window(qtbot, tmp_path, sim):
    """!
    @brief A main window that holds the example board and its simulation.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation.
    @return MainWindow
    """
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win._load_problem(copy.deepcopy(sim.problem), "t")
    win.results.set_simulation(sim)
    win.sim, win._stale = sim, False
    win._update_map_button()
    win._apply_layer()
    return win


def _texts(win):
    """!
    @brief The texts of the toolbar Layer box.
    @param win MainWindow.
    @return list of str.
    """
    return [win.layer_combo.itemText(i) for i in range(win.layer_combo.count())]


def _go(win, tab):
    """!
    @brief Show a Results tab.
    @param win MainWindow.
    @param tab The tab widget of the Results.
    """
    win.tabs.setCurrentIndex(TAB_RESULTS)
    win.results.tabs.setCurrentWidget(tab)


# ------------------------------------------------------------------------------------------------------------------ the model (no window)
def test_lists_per_context():
    assert [d for _t, d in lc.items("single", 4)] == [0, 1, 2, 3]
    assert [t for t, _d in lc.items("single", 4)] == ["1 top", "2", "3", "4 bottom"]
    ext = lc.items(lc.EXTENDED_CONTEXT, 2, (0, 1))
    assert [t for t, _d in ext] == ["All layers", "All (2 x 2)", "1 top", "2 bottom", "Metal block (top)", "Metal block (bottom)"]
    assert [d for _t, d in ext][-2:] == [100, 101]
    assert [d for _t, d in lc.items(lc.EXTENDED_CONTEXT, 2)] == [-1, -2, 0, 1]      # No result block: no entry


def test_fallback_rule_and_latest_pick_wins():
    c = lc.LayerChoice()
    c.pick(2)
    c.pick(lc.ALL_GRID)
    assert c.effective(lc.EXTENDED_CONTEXT, 4) == (lc.ALL_GRID, "")
    value, note = c.effective("single", 4)
    assert value == 2 and "All (2 x 2)" in note and "Temperature only" in note and "layer 3" in note
    assert c.effective(lc.EXTENDED_CONTEXT, 4) == (lc.ALL_GRID, "")               # Back in Temperature, All returns
    c.pick(1)                                                                     # A single layer picked meanwhile wins
    assert c.effective(lc.EXTENDED_CONTEXT, 4) == (1, "") and c.effective("single", 4) == (1, "")
    c.pick(lc.BLOCK_BASE + 1)
    assert c.effective("single", 4)[0] == 1 and c.effective(lc.EXTENDED_CONTEXT, 4, (1,)) == (101, "")
    assert c.effective(lc.EXTENDED_CONTEXT, 4, ())[0] == 1                          # The result has no such block


def test_a_layer_beyond_the_board_is_clamped():
    c = lc.LayerChoice()
    c.pick(3)
    assert c.effective("single", 2)[0] == 1 and c.single(2) == 1


# ------------------------------------------------------------------------------------------------------------------ the window
def test_the_lists_in_each_context(qtbot, tmp_path, sim):
    win = _window(qtbot, tmp_path, sim)
    n = sim.problem.board.layers
    layers = [lc.layer_label(l, n) for l in range(n)]
    for tab in (TAB_BOARD, TAB_STACKUP, TAB_PROFILE):
        win.tabs.setCurrentIndex(tab)
        assert _texts(win) == layers
    _go(win, win.results.temp)
    assert _texts(win) == ["All layers", "All (2 x 2)"] + layers
    for w in (win.results.grad, win.results.animation, win.results.profile, win.results.time_sim):
        _go(win, w)
        assert _texts(win) == layers


def test_a_metal_block_is_listed_only_in_temperature(qtbot, tmp_path):
    p = example_board()
    p.add_heatsink(1, 10.0, rect=(15, 12, 45, 28), thickness_mm=3.0)
    s = simulate(p, SolverOptions(models=("fvm",), cell_mm=2.0))
    win = _window(qtbot, tmp_path, s)
    _go(win, win.results.temp)
    has_block = bool(win.results.temp.block_faces())
    assert has_block and win.layer_combo.findData(100) >= 0
    _go(win, win.results.grad)
    assert win.layer_combo.findData(100) < 0 and win.layer_combo.findData(101) < 0


def test_the_tab_boxes_are_gone_and_the_toolbar_drives_every_tab(qtbot, tmp_path, sim):
    win = _window(qtbot, tmp_path, sim)
    rv = win.results
    for w in (rv.temp, rv.grad, rv.profile, rv.animation, rv.time_sim):
        assert not hasattr(w, "layer")
    win.tabs.setCurrentIndex(TAB_BOARD)
    win.layer_combo.setCurrentIndex(2)
    assert win.canvas.layer == 2
    assert [rv.temp.layer_value, rv.grad.layer_value, rv.animation.layer_value, rv.time_sim.layer_value] == [2, 2, 2, 2]
    _go(win, rv.temp)
    win.layer_combo.setCurrentIndex(win.layer_combo.findData(-2))
    assert rv.temp.layer_value == -2 and win.canvas.layer == 2                       # The board keeps the last single layer
    assert rv.grad.layer_value == 2


def test_fallback_note_over_the_maps(qtbot, tmp_path, sim):
    win = _window(qtbot, tmp_path, sim)
    rv = win.results
    _go(win, rv.temp)
    win.layer_combo.setCurrentIndex(win.layer_combo.findData(-2))
    assert not rv.layer_note.isVisible() or rv.layer_note.text() == ""
    _go(win, rv.grad)
    assert rv.layer_note.isVisibleTo(rv) and "Temperature only" in rv.layer_note.text() and "All (2 x 2)" in rv.layer_note.text()
    assert win.layer_combo.currentData() == 0 and rv.grad.layer_value == 0
    _go(win, rv.animation)
    assert rv.layer_note.isVisibleTo(rv)
    win.tabs.setCurrentIndex(TAB_BOARD)                                              # The editor shows the single layer, no map line
    assert not rv.layer_note.isVisibleTo(rv) and win.layer_combo.currentData() == 0
    _go(win, rv.temp)                                                                # All returns
    assert win.layer_combo.currentData() == -2 and rv.temp.layer_value == -2
    # A single layer picked in Gradients wins over the stored All
    _go(win, rv.grad)
    win.layer_combo.setCurrentIndex(win.layer_combo.findData(1))
    assert not rv.layer_note.isVisibleTo(rv)
    _go(win, rv.temp)
    assert win.layer_combo.currentData() == 1 and rv.temp.layer_value == 1


def test_selecting_an_element_on_another_layer_moves_the_one_choice(qtbot, tmp_path, sim):
    win = _window(qtbot, tmp_path, sim)
    p = win.doc.problem
    k = next(i for i, h in enumerate(p.heaters) if h.layer != win.canvas.layer) if any(h.layer != win.canvas.layer for h in p.heaters) else None
    if k is None:
        p.heaters[0].layer = 1 if p.board.layers > 1 else 0
        k = 0
    win._on_list_selection([("heater", k)])
    assert win.layer_combo.currentData() == p.heaters[k].layer == win.canvas.layer == win.results.grad.layer_value


def test_the_map_on_the_board_follows_the_choice(qtbot, tmp_path, sim):
    win = _window(qtbot, tmp_path, sim)
    win.a_overlay.setChecked(True)
    _go(win, win.results.temp)
    win.layer_combo.setCurrentIndex(win.layer_combo.findData(3))
    win.tabs.setCurrentIndex(TAB_BOARD)
    import numpy as np
    assert np.array_equal(win.canvas._overlay_args["field"], sim.reference.T[3])


def test_tooltips_per_context(qtbot, tmp_path, sim):
    win = _window(qtbot, tmp_path, sim)
    seen = {}
    for name, go in (("editor", lambda: win.tabs.setCurrentIndex(TAB_BOARD)), ("profile page", lambda: win.tabs.setCurrentIndex(TAB_PROFILE)),
                     ("temperature", lambda: _go(win, win.results.temp)), ("gradient", lambda: _go(win, win.results.grad)),
                     ("animation", lambda: _go(win, win.results.animation)), ("profiles", lambda: _go(win, win.results.profile))):
        go()
        seen[name] = win.layer_combo.toolTip()
        assert seen[name] == tips.LAYER_TIPS[name] and len(seen[name]) > 40
    assert len(set(seen.values())) == len(seen)


def test_the_layer_choice_is_not_stored_in_the_project(qtbot, tmp_path, sim):
    """!
    @brief The layer was never part of the file or of the window state: a pick changes neither (the format is unchanged, old projects load as before).
    """
    from pcbthermal.project import Project, project_to_dict

    win = _window(qtbot, tmp_path, sim)
    before = project_to_dict(Project(problem=win.doc.problem))
    win.layer_combo.setCurrentIndex(2)
    assert project_to_dict(Project(problem=win.doc.problem)) == before
    assert not any("layer" in k.lower() for k in win.settings.allKeys())


# ------------------------------------------------------------------------------------------------------------------ the card
def _click(view, pos):
    """!
    @brief Press the left button on the viewport of the board.
    @param view BoardView.
    @param pos QPointF in viewport pixels.
    """
    e = QMouseEvent(QEvent.MouseButtonPress, pos, view.viewport().mapToGlobal(pos), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    view.mousePressEvent(e)


def test_the_card_name_opens_the_model_menu(qtbot, tmp_path, sim):
    win = _window(qtbot, tmp_path, sim)
    win.show()
    win.a_overlay.setChecked(True)
    qtbot.wait(20)
    win.canvas.viewport().repaint()
    hit = win.canvas.card_hit_rect()
    assert hit is not None
    pos = hit.center()
    got = []
    win.canvas.card_clicked.connect(got.append)
    win.canvas.setFocus()
    _click(win.canvas, QPointF(pos))
    assert len(got) == 1 and win.canvas.hasFocus()
    # Outside the card nothing is emitted
    _click(win.canvas, QPointF(hit.right() + 200, hit.bottom() + 200))
    assert len(got) == 1


def test_the_menu_changes_the_same_model_control(qtbot, tmp_path, sim):
    win = _window(qtbot, tmp_path, sim)
    win.a_overlay.setChecked(True)
    t = win.results.temp
    assert t.model.currentData() == "fvm"
    win._open_model_menu(QPoint(0, 0))
    menu = win._model_menu
    texts = [a.text() for a in menu.actions()]
    assert texts == [t.model.itemText(i) for i in range(t.model.count())] and len(texts) == 2
    assert [a.isChecked() for a in menu.actions()] == [True, False]
    menu.actions()[1].trigger()
    assert t.model.currentData() == "lumped"                                       # No second list: the Temperature tab's own control
    assert win.canvas._overlay_card["title"] == "Lumped"
    menu.close()


def test_a_refused_model_is_listed_greyed_with_its_reason(qtbot, tmp_path):
    import numpy as np
    p = example_board()
    W, H = p.board.width, p.board.height
    p.board.outline = np.array([[0, 0], [W, 0], [W, 0.45 * H], [0.65 * W, 0.45 * H], [0.65 * W, H], [0.35 * W, H], [0.35 * W, 0.45 * H], [0, 0.45 * H]], dtype=float)
    p.heaters = p.heaters[:1]
    p.heaters[0].polygon = np.array([[0.4 * W, 0.6 * H], [0.55 * W, 0.6 * H], [0.55 * W, 0.8 * H], [0.4 * W, 0.8 * H]])
    p.vias = []
    s = simulate(p, SolverOptions(models=("fvm", "lumped"), cell_mm=2.0))
    win = _window(qtbot, tmp_path, s)
    win._open_model_menu(QPoint(0, 0))
    acts = win._model_menu.actions()
    assert acts[0].isEnabled() and not acts[1].isEnabled() and "outline" in acts[1].text() and "stretched" in acts[1].toolTip()
    win._model_menu.close()


# ------------------------------------------------------------------------------------------------------------------ the review
def test_a_layer_change_in_the_editor_does_not_draw_the_hidden_maps(qtbot, tmp_path, sim):
    """!
    @brief The hidden Results tabs are drawn when shown, not at every layer change (it made a layer change about 30 times slower).
    """
    win = _window(qtbot, tmp_path, sim)
    win.show()
    win.tabs.setCurrentIndex(TAB_BOARD)
    rv = win.results
    calls = []
    for t in (rv.temp, rv.grad):
        orig = t.redraw
        t.redraw = (lambda o=orig, name=t.kind: (calls.append(name), o())[1])
    win.layer_combo.setCurrentIndex(2)
    assert calls == [] and rv.grad.layer_value == 2                                  # The value moved, nothing was drawn
    _go(win, rv.grad)
    qtbot.wait(10)
    assert "gradient" in calls and "temperature" not in calls
    axes = [a for a in rv.grad.fig.axes if a.get_images()]
    assert axes and "layer 3" in " ".join(a.get_title() for a in rv.grad.fig.axes)  # The figure is of layer 3 (0-based 2)


def test_picking_the_fallback_layer_shown_counts_as_a_pick(qtbot, tmp_path, sim):
    win = _window(qtbot, tmp_path, sim)
    rv = win.results
    _go(win, rv.temp)
    win.layer_combo.setCurrentIndex(win.layer_combo.findData(lc.ALL_LAYERS))
    _go(win, rv.grad)
    assert win.layer_combo.currentData() == 0 and rv.layer_note.isVisibleTo(rv)
    win.layer_combo.activated.emit(win.layer_combo.currentIndex())                   # The user picks the layer already shown
    assert not rv.layer_note.isVisibleTo(rv)
    _go(win, rv.temp)
    assert win.layer_combo.currentData() == 0                                        # The latest pick wins: All does not return


def test_selecting_an_element_keeps_all_layers_in_temperature(qtbot, tmp_path, sim):
    win = _window(qtbot, tmp_path, sim)
    p = win.doc.problem
    _go(win, win.results.temp)
    win.layer_combo.setCurrentIndex(win.layer_combo.findData(lc.ALL_GRID))
    win.tabs.setCurrentIndex(TAB_BOARD)
    p.heaters[0].layer = 1
    win._on_list_selection([("heater", 0)])
    assert win.canvas.layer == 1 and win.layer_combo.currentData() == 1 and win.results.grad.layer_value == 1
    assert win.results.temp.layer_value == lc.ALL_GRID                                # Not a pick: the grid stays in Temperature
    _go(win, win.results.temp)
    assert win.layer_combo.currentData() == lc.ALL_GRID


def test_a_one_layer_board_lists_no_grid():
    assert [d for _t, d in lc.items(lc.EXTENDED_CONTEXT, 1)] == [lc.ALL_LAYERS, 0]
    c = lc.LayerChoice()
    c.pick(lc.ALL_GRID)
    assert c.effective(lc.EXTENDED_CONTEXT, 1) == (lc.ALL_LAYERS, "")


def test_the_model_menu_shows_tooltips_keeps_one_menu_and_has_a_key(qtbot, tmp_path, sim):
    win = _window(qtbot, tmp_path, sim)
    win.show()
    win.a_overlay.setChecked(True)
    win._open_model_menu(QPoint(0, 0))
    first = win._model_menu
    assert first.toolTipsVisible()
    win._open_model_menu(QPoint(0, 0))
    assert win._model_menu is not first
    win._model_menu.close()
    # The key M is a window action of the View menu (the card answers the mouse only)
    keys = [a for a in win.actions() if "M" in [k.toString() for k in a.shortcuts()]]
    assert len(keys) == 1
    view = [a for a in win.menuBar().actions() if a.text() == "&View"][0].menu()
    assert win.a_model in view.actions()
    keys[0].trigger()
    menu = win._model_menu
    assert menu.isVisible() and menu.activeAction() is not None and menu.activeAction().isChecked()
    menu.close()
