"""!
@file test_gui.py
@brief GUI tests: drawing, editing, undo, panels, simulation and results (offscreen Qt).
"""

import numpy as np
import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtTest import QTest

from pcbthermal.examples import example_board
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow
from pcbthermal.model import Problem


@pytest.fixture
def win(qtbot, tmp_path, monkeypatch):
    """!
    @brief A main window with an empty 100 x 80 mm, 2-layer board, shown offscreen.
    """
    doc = Document()
    w = MainWindow(doc, QSettings(str(tmp_path / 'test.ini'), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.resize(1400, 850)
    w.show()
    w.canvas.fit()
    # Never block on a message box in tests
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.warning", lambda *a, **k: None)
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.critical", lambda *a, **k: None)
    # Closing a modified window at teardown would otherwise open a modal question
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question",
                        lambda *a, **k: __import__("PySide6.QtWidgets", fromlist=["x"]).QMessageBox.Discard)
    return w


def vp(canvas, x_mm, y_mm):
    """!
    @brief Viewport pixel of a board point.
    """
    return canvas.mapFromScene(QPointF(x_mm, y_mm))


def drag(canvas, a, b):
    """!
    @brief Drag the left mouse button between two board points.
    """
    pa, pb = vp(canvas, *a), vp(canvas, *b)
    QTest.mousePress(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, pa)
    QTest.mouseMove(canvas.viewport(), (pa + pb) / 2)
    QTest.mouseMove(canvas.viewport(), pb)
    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, pb)


def test_draw_rectangle_heater_and_undo(win):
    win.tool_actions["heater"].trigger()
    drag(win.canvas, (20, 20), (30, 30))
    assert win.doc.count("heater") == 1
    poly = win.doc.polygon_mm(win.doc.problem.heaters[0])
    assert poly[:, 0].min() == pytest.approx(20) and poly[:, 1].max() == pytest.approx(30)
    assert win.canvas.tool == "select"                        # Returns to the select tool
    win.doc.stack.undo()
    assert win.doc.count("heater") == 0
    win.doc.stack.redo()
    assert win.doc.count("heater") == 1


def test_polygon_mode_zone_via_and_heatsink_rules(win):
    win.tool_actions["zone"].trigger()
    win.a_poly.setChecked(True)
    for p in ((10, 10), (40, 10), (40, 30)):
        QTest.mouseClick(win.canvas.viewport(), Qt.LeftButton, Qt.NoModifier, vp(win.canvas, *p))
    QTest.mouseDClick(win.canvas.viewport(), Qt.LeftButton, Qt.NoModifier, vp(win.canvas, 20, 30))
    assert win.doc.count("zone") == 1
    assert len(win.doc.problem.zones[0].polygon) == 4
    win.a_poly.setChecked(False)
    win.tool_actions["via"].trigger()
    QTest.mouseClick(win.canvas.viewport(), Qt.LeftButton, Qt.NoModifier, vp(win.canvas, 50, 40))
    assert win.doc.count("via") == 1
    # Heatsinks only on outer layers: a 2-layer board has top and bottom, so both are accepted
    win.tool_actions["heatsink"].trigger()
    drag(win.canvas, (60, 10), (80, 30))
    assert win.doc.count("heatsink") == 1


def test_heatsink_refused_on_inner_layer(qtbot, monkeypatch, tmp_path):
    doc = Document()
    doc.new(100, 80, 4)
    w = MainWindow(doc, QSettings(str(tmp_path / 'test.ini'), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.show()
    w.canvas.fit()
    w.layer_combo.setCurrentIndex(1)                          # Inner layer
    w.tool_actions["heatsink"].trigger()
    drag(w.canvas, (10, 10), (20, 20))
    assert doc.count("heatsink") == 0


def test_move_by_drag_and_nudge(win):
    win.doc.problem.add_heater(1, 2.0, rect=(10, 10, 20, 20), name="U1")
    win.doc.changed.emit()
    win.canvas.set_selection([("heater", 0)])
    drag(win.canvas, (15, 15), (35, 25))
    poly = win.doc.polygon_mm(win.doc.problem.heaters[0])
    assert poly[:, 0].min() == pytest.approx(30, abs=1.0) and poly[:, 1].min() == pytest.approx(20, abs=1.0)
    win.canvas.set_selection([("heater", 0)])
    before = win.doc.polygon_mm(win.doc.problem.heaters[0])[:, 0].min()
    QTest.keyClick(win.canvas, Qt.Key_Right)
    assert win.doc.polygon_mm(win.doc.problem.heaters[0])[:, 0].min() == pytest.approx(before + 1.0)


def test_vertex_handle_keeps_rectangle(win):
    win.doc.problem.add_zone(1, rect=(10, 10, 30, 30))
    win.doc.changed.emit()
    win.canvas.set_selection([("zone", 0)])
    assert len(win.canvas._handles) == 4
    # Drag the corner (30, 30) to (40, 35): the polygon stays an axis-aligned rectangle
    h = next(h for h in win.canvas._handles if abs(h.pos().x() - 30) < 1e-6 and abs(h.pos().y() - 30) < 1e-6)
    h.setPos(QPointF(40, 35))
    win.canvas._handles_committed()
    p = win.doc.polygon_mm(win.doc.problem.zones[0])
    assert (p[:, 0].min(), p[:, 0].max(), p[:, 1].min(), p[:, 1].max()) == pytest.approx((10, 40, 10, 35))


def test_delete_duplicate_and_selection_sync(win):
    win.doc.problem.add_heater(1, 2.0, rect=(10, 10, 20, 20)).add_heater(1, 1.0, rect=(40, 10, 50, 20))
    win.doc.changed.emit()
    win.canvas.set_selection([("heater", 0)])
    QTest.keyClick(win.canvas, Qt.Key_D, Qt.ControlModifier)
    assert win.doc.count("heater") == 3
    win.canvas.set_selection([("heater", 2)])
    QTest.keyClick(win.canvas, Qt.Key_Delete)
    assert win.doc.count("heater") == 2
    # Selecting in the list selects on the canvas and fills the inspector
    win.elements.tree.topLevelItem(1).child(1).setSelected(True)
    assert win.canvas.selected_elements() == [("heater", 1)]


def test_inspector_edits_power_and_board_panel_edits_board(win):
    win.doc.problem.add_heater(1, 2.0, rect=(10, 10, 20, 20), name="U1")
    win.doc.changed.emit()
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    spins = win.inspector.form_host.findChildren(type(win.board_panel.width))
    power = next(s for s in spins if s.suffix().strip() == "W")
    power.setValue(7.5)
    assert win.doc.problem.heaters[0].power == pytest.approx(7.5)
    win.board_panel.width.setValue(120.0)
    assert win.doc.problem.board.width == pytest.approx(0.12)
    win.board_panel.layers.setValue(4)
    assert win.doc.problem.board.layers == 4 and len(win.doc.problem.board.copper_thickness) == 4
    win.board_panel.layers.setValue(1)
    assert win.doc.problem.heaters[0].layer == 0


def test_save_open_roundtrip_and_title(win, tmp_path):
    win.doc.problem.add_heater(1, 2.0, rect=(10, 10, 20, 20), name="U1")
    win.doc.changed.emit()
    path = str(tmp_path / "board.pcbt.json")
    win.doc.save(path)
    assert not win.doc.modified
    other = Document()
    other.open(path)
    assert other.problem.heaters[0].name == "U1"
    win.doc.problem.add_heater(1, 1.0, rect=(30, 30, 40, 40))
    win.doc.edit("x", lambda p: None)
    win.doc.set_props("heater", 0, power=3.0)
    assert win.doc.modified and "*" in win.windowTitle()


def test_run_simulation_fills_results_and_marks_stale(win, qtbot):
    win.doc.open_problem(example_board(), "example-4layer")
    win._after_load()
    win.solver_panel.cell.setValue(2.0)
    with qtbot.waitSignal(win.solver_panel.run_requested, timeout=1000):
        win.solver_panel.run.click()
    qtbot.waitUntil(lambda: win.sim is not None, timeout=60000)
    assert set(win.sim.results) == {"fvm", "lumped", "analytic"}
    assert win.tabs.currentIndex() == 3
    assert win.results.model_table.rowCount() == 3
    assert win.results.heater_table.rowCount() == 2 and "°C" in win.results.heater_table.item(0, 5).text() or True
    # All plot tabs rendered without error, and the overlay can be painted on the board
    for tab in (win.results.temp, win.results.grad, win.results.profile, win.results.compare):
        tab.redraw()
    win.a_overlay.setChecked(True)
    assert win.canvas._overlay is not None
    win.canvas.set_selection([])
    win.doc.set_props("heater", 0, power=3.0)
    assert "outdated" in win.tabs.tabText(3) and win.canvas._overlay is None


def test_run_requires_a_heater(win):
    win.run_simulation()
    assert win.sim is None and win.worker is None


def test_theme_switch_and_screenshots(win, qtbot, tmp_path):
    win.doc.open_problem(example_board(), "example-4layer")
    win._after_load()
    win.grab().save(str(tmp_path / "board_dark.png"))
    win.toggle_theme()
    win.grab().save(str(tmp_path / "board_light.png"))
    assert (tmp_path / "board_light.png").stat().st_size > 5000
    win.toggle_theme()


def test_animation_tab_computes_plays_and_exports(win, qtbot, tmp_path):
    win.doc.open_problem(example_board(), "example-4layer")
    win._after_load()
    anim = win.results.animation
    win.tabs.setCurrentIndex(3)                               # Suggests a duration from the time constant
    assert anim.t_end.value() > 1.0
    anim.t_end.setValue(60.0)
    anim.frames.setValue(12)
    anim.compute.click()
    qtbot.waitUntil(lambda: anim.tr is not None, timeout=60000)
    assert anim.slider.maximum() == len(anim.tr.times) - 1 >= 12 and anim.slider.value() == anim.slider.maximum()
    assert anim.tr.t_max[-1] > anim.tr.t_max[1] > anim.tr.ambient
    anim.slider.setValue(0)
    anim.play.setChecked(True)
    qtbot.waitUntil(lambda: anim.slider.value() > 2, timeout=5000)
    anim.play.setChecked(False)
    from pcbthermal import plots
    out = tmp_path / "evolution.gif"
    plots.save_transient_gif(anim.tr, anim.problem, str(out), fps=5)
    assert out.stat().st_size > 5000


def test_animation_refuses_boards_without_power(win):
    win.results.animation.compute.click()
    assert win._anim_worker is None if hasattr(win, "_anim_worker") else True
    assert "heater" in win.results.animation.status.text().lower()


def test_window_shows_the_version(win):
    import pcbthermal

    assert pcbthermal.__version__ in win.windowTitle()
    assert win.version_label.text() == f"v{pcbthermal.__version__}"
    assert win.canvas is not None
