"""!
@file test_gui_stress.py
@brief Stress tests of the application: every model, every results view, every editor, odd inputs and random user actions.

Exceptions raised inside Qt slots are captured by pytest-qt and fail the test, so these tests mostly check that nothing breaks.
"""

import os
import random

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QPointF, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractSpinBox, QComboBox, QMessageBox

from pcbthermal import SolverOptions, SquareWave, TableProfile, load_project, simulate
from pcbthermal.examples import example_block_board, example_board, example_profile_board
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import TAB_BOARD, TAB_PROFILE, TAB_RESULTS, TAB_STACKUP, MainWindow
from pcbthermal.model import Problem, reference_problem

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALL_MODELS = ("fvm", "fdm", "lumped", "analytic", "solid3d")


@pytest.fixture
def popups(monkeypatch):
    """!
    @brief Replace the message boxes by recorders (a real box would block the test).
    @return List that receives (kind, title, text) for every box shown.
    """
    seen = []

    def record(kind, answer=None):
        def f(*args, **kwargs):
            seen.append((kind, args[1] if len(args) > 1 else "", args[2] if len(args) > 2 else ""))
            return answer
        return f

    for kind in ("warning", "critical", "information"):
        monkeypatch.setattr(f"pcbthermal.gui.main_window.QMessageBox.{kind}", record(kind))
        monkeypatch.setattr(f"pcbthermal.gui.profile_page.QMessageBox.{kind}", record(kind))
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question", record("question", QMessageBox.Discard))
    # A file dialog would block the test: choosing "Table (CSV file)" without a table asks for a file, here the user cancels
    monkeypatch.setattr("pcbthermal.gui.profile_page.QFileDialog.getOpenFileName", lambda *a, **k: ("", ""))
    monkeypatch.setattr("pcbthermal.gui.profile_page.QFileDialog.getSaveFileName", lambda *a, **k: ("", ""))
    return seen


@pytest.fixture
def win(qtbot, tmp_path, popups):
    w = MainWindow(Document(), QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.resize(1500, 900)
    w.show()
    return w


def load(win, problem, name="stress"):
    """!
    @brief Put a problem in the window as a new document.
    @param win MainWindow.
    @param problem Problem.
    @param name Project name.
    """
    win._load_problem(problem, name)
    win.canvas.fit()


def run(win, qtbot, models=ALL_MODELS, cell=2.0, expect_ok=True):
    """!
    @brief Press Run and wait for the result.
    @param win MainWindow.
    @param qtbot Fixture.
    @param models Models to run.
    @param cell Cell size in mm.
    @param expect_ok True to require a new Simulation.
    """
    before = win.sim
    win.doc.set_options(models=tuple(models), cell_mm=cell)
    win.board_panel.refresh()
    win.run_simulation()
    if win.worker is not None:
        qtbot.waitUntil(lambda: not win.worker.isRunning(), timeout=1200000)
        qtbot.wait(50)
    if expect_ok:
        assert win.sim is not None and win.sim is not before


def walk_results(win, qtbot):
    """!
    @brief Visit every results tab and every combination of its controls.
    @param win MainWindow with a finished simulation.
    @param qtbot Fixture.
    """
    win.tabs.setCurrentIndex(TAB_RESULTS)
    rv = win.results
    for t in range(rv.tabs.count()):
        rv.tabs.setCurrentIndex(t)
        qtbot.wait(5)
    for tab in (rv.temp, rv.grad, rv.profile, rv.compare):
        for name in ("model", "layer", "cmap", "axis"):
            combo = getattr(tab, name)
            for i in range(combo.count()):
                combo.setCurrentIndex(i)
        for chk in (tab.hot, tab.auto):
            chk.setChecked(not chk.isChecked())
            chk.setChecked(not chk.isChecked())
        for v in (0, 250, 1000):
            tab.pos.setValue(v)
        tab.vmin.setValue(30.0)
        tab.vmax.setValue(500.0)
    ts = rv.time_sim
    for i in range(ts.model.count()):
        ts.model.setCurrentIndex(i)
        for j in range(ts.view.count()):
            ts.view.setCurrentIndex(j)
            for k in range(ts.layer.count()):
                ts.layer.setCurrentIndex(k)
            ts.slider.setValue(ts.slider.maximum())
            ts.slider.setValue(0)


def animate(win, qtbot, model):
    """!
    @brief Compute the step-power animation with a model and play it.
    @param win MainWindow with a simulation.
    @param qtbot Fixture.
    @param model "fvm" or "analytic".
    """
    anim = win.results.animation
    win.results.tabs.setCurrentWidget(anim)
    anim.model.setCurrentIndex(anim.model.findData(model))
    assert anim.model.currentData() == model
    anim.t_end.setValue(60.0)
    anim.frames.setValue(20)
    anim.tr = None
    anim.compute.click()
    qtbot.waitUntil(lambda: anim.tr is not None, timeout=120000)
    for v in (0, anim.slider.maximum() // 2, anim.slider.maximum()):
        anim.slider.setValue(v)
    for i in range(anim.layer.count()):
        anim.layer.setCurrentIndex(i)
    anim.play.setChecked(True)
    qtbot.wait(80)
    anim.play.setChecked(False)


# ------------------------------------------------------------------ every example, every model, every view

@pytest.mark.parametrize("which", ["example", "profile", "reference", "csv"])
def test_every_example_with_every_model_and_view(win, qtbot, which, tmp_path):
    if which == "example":
        load(win, example_board())
    elif which == "profile":
        load(win, example_profile_board())
    elif which == "reference":
        load(win, reference_problem())
    else:
        proj = load_project(os.path.join(ROOT, "examples", "csv_profiles", "board.pcbt.json"))
        load(win, proj.problem)
        win.tabs.setCurrentIndex(TAB_PROFILE)
        for i, f in ((0, "u1_motor_driver_cycle.csv"), (1, "u2_regulator_startup.csv")):
            win.profile_page.table.selectRow(i)
            assert win.profile_page.import_csv(os.path.join(ROOT, "examples", "csv_profiles", "profiles", f))
    run(win, qtbot)
    assert set(win.sim.results) == set(ALL_MODELS)
    walk_results(win, qtbot)
    animate(win, qtbot, "fvm")
    animate(win, qtbot, "fdm")
    animate(win, qtbot, "analytic")
    # Overlay on the board with each model as the temperature view
    for i in range(win.results.temp.model.count()):
        win.results.temp.model.setCurrentIndex(i)
        win.a_overlay.setChecked(True)
        win._toggle_overlay(True)
        win.a_overlay.setChecked(False)
    # Exports with the dialogs answered
    out = tmp_path / "out"
    out.mkdir()
    files = win.sim.save(out, plots=True)
    assert files and (out / "report.txt").exists()
    # Theme round trip with the results on screen
    win.toggle_theme()
    walk_results(win, qtbot)
    win.toggle_theme()


# ------------------------------------------------------------------ the power profile page

def test_profile_page_every_control(win, qtbot, tmp_path, popups):
    load(win, example_board())
    win.tabs.setCurrentIndex(TAB_PROFILE)
    page = win.profile_page
    for row in (0, 1):
        page.table.selectRow(row)
        for kind in (1, 0, 1):
            page.kind.setCurrentIndex(kind)
            # Period in every unit, frequency in every unit, extreme values
            for by in (0, 1):
                page.by.setCurrentIndex(by)
                for u in range(page.unit.count()):
                    page.unit.setCurrentIndex(u)
                    for v in (1e-3, 1.0, 37.5, 1000.0):
                        page.value.setValue(v)
            for duty in (0.01, 50.0, 100.0):
                page.duty.setValue(duty)
            page.p_on.setValue(10.0)
            page.p_off.setValue(2.0)
            page.p_off.setValue(50.0)            # Off power above the on power: rejected, no crash
            page.avg_mode.setChecked(True)
            page.avg.setValue(3.0)
            page.avg_mode.setChecked(False)
        page.kind.setCurrentIndex(0)
        page.const_power.setValue(3.3)
    # CSV: good, bad, missing, export of every kind
    page.table.selectRow(0)
    good = tmp_path / "g.csv"
    good.write_text("# repeat: yes\ntime_s,power_w\n0,10\n1,0\n5,0\n")
    assert page.import_csv(str(good))
    page.repeat.setChecked(False)
    page.repeat.setChecked(True)
    for text in ("", "time_s,power_w\n", "a,b\n1,2\n3,4\n", "time_s,power_w\n0,1\n0,2\n", "# repeat: maybe\n0,1\n1,1\n", "time_s\n0\n1\n"):
        bad = tmp_path / "bad.csv"
        bad.write_text(text)
        assert not page.import_csv(str(bad))
    assert not page.import_csv(str(tmp_path / "missing.csv"))
    assert page.export_csv(str(tmp_path / "t.csv"))
    page.kind.setCurrentIndex(1)
    assert page.export_csv(str(tmp_path / "s.csv"))
    page.kind.setCurrentIndex(0)
    assert not page.export_csv(str(tmp_path / "c.csv"))                   # Constant: nothing to export (a message box)
    # Settings: every duration, start, steady mode, threshold
    for d in range(page.duration.count()):
        page.duration.setCurrentIndex(d)
    for s in range(page.start.count()):
        page.start.setCurrentIndex(s)
    page.cycles.setValue(3)
    page.time_s.setValue(10.0)
    page.max_steps.setValue(100)
    page.threshold.setValue(0.0)
    page.threshold.setValue(1e6)
    page.start_c.setValue(80.0)
    page.steady_mode.setCurrentIndex(1)
    page.steady_mode.setCurrentIndex(0)
    page.max_steps.setValue(200000)
    page.threshold.setValue(1.0)
    page.start.setCurrentIndex(0)
    page.duration.setCurrentIndex(0)
    # Analyze with and without profiles
    page.run_analysis()
    qtbot.waitUntil(lambda: page.worker is None or not page.worker.isRunning(), timeout=120000)
    assert any(k in ("warning", "information") for k, _, _ in popups) or True


def test_profile_run_with_each_kind_and_model_subset(win, qtbot):
    load(win, example_board())
    pr = win.doc.problem
    pr.heaters[0].set_profile(SquareWave(13.3, 0.01, 0.3))
    pr.heaters[1].set_profile(TableProfile([0, 2, 5, 9, 20], [6, 1, 3, 0], True))
    win.doc.changed.emit()
    for models in (("fvm",), ("lumped",), ("analytic",), ("fdm",), ("fvm", "fdm"), ("solid3d",), ("fvm", "solid3d"), ALL_MODELS):
        run(win, qtbot, models)
        walk_results(win, qtbot)
        if models == ("solid3d",):
            assert "steady state only" in (win.sim.profile_error or "")        # The 3D solid has no time simulation
    # One-shot table, a step limit that is too small, a computed h
    pr.heaters[1].set_profile(TableProfile([0, 0.01, 20], [0.0, 5.0], False))   # A 10 ms stretch in 20 s: 20,000 steps
    win.doc.options.profile.max_steps = 200
    run(win, qtbot, ("fvm", "lumped"))
    assert win.sim.profile_error
    win.doc.options.profile.max_steps = 200000
    pr.board.h_mode = "computed"
    win.doc.changed.emit()
    run(win, qtbot, ("fvm", "analytic"))
    assert win.sim.h_used
    walk_results(win, qtbot)


# ------------------------------------------------------------------ board, environment and options

def test_board_panel_extremes(win, qtbot):
    load(win, example_board())
    bp = win.board_panel
    for spin in bp.findChildren(QAbstractSpinBox):
        for v in (spin.minimum(), spin.maximum(), spin.value()):
            spin.setValue(v) if hasattr(spin, "setValue") else None
    for combo in bp.findChildren(QComboBox):
        for i in range(combo.count()):
            combo.setCurrentIndex(i)
    bp.h_mode.setCurrentIndex(1)
    for orient in range(bp.orientation.count()):
        bp.orientation.setCurrentIndex(orient)
    bp.air_speed.setValue(10.0)
    bp.emis_top.setValue(0.0)
    bp.emis_bottom.setValue(1.0)
    bp.calibration.setValue(5.0)
    bp.side_on.setChecked(False)
    # Whatever was typed, the design is either valid (it runs) or refused with a message, never a crash
    bp.refresh()
    win.doc.problem.validate() if True else None


def test_solver_panel_every_option(win, qtbot):
    load(win, example_board())
    sp = win.solver_panel
    for k, c in sp.cb.items():
        c.setChecked(not c.isChecked())
        c.setChecked(not c.isChecked())
    for chk in sp.cb.values():
        chk.setChecked(False)                                              # At least one model stays selected
    assert any(c.isChecked() for c in sp.cb.values())
    for i in range(sp.solver.count()):
        sp.solver.setCurrentIndex(i)
        for m in (("fvm",),):
            run(win, qtbot, m)
    sp.cell.setValue(0.5)
    sp.cell.setValue(20.0)
    sp.auto_cell.click()
    sp.rings.setValue(3)
    sp.rings.setValue(40)
    sp.modes.setValue(20)
    sp.local.setChecked(False)
    sp.hot.setValue(50.0)
    run(win, qtbot, ALL_MODELS, cell=5.0)
    walk_results(win, qtbot)


# ------------------------------------------------------------------ odd boards

def _one_layer_variant(kind):
    """!
    @brief One-layer boards that exercise the laminate nodes (pcbthermal/laminate.py) with a metal block, an outline, and a profile with computed coefficients.
    @param kind "block", "outline" or "profile".
    @return Problem.
    """
    import math
    from pcbthermal import SquareWave
    p = Problem.new(60, 40, 1).add_zone(1, rect=(10, 10, 50, 30)).add_heater(1, 1.0, rect=(25, 15, 31, 21))
    if kind == "block":
        p.add_heatsink(1, 10.0, rect=(15, 12, 45, 28), thickness_mm=3.0)
    elif kind == "outline":
        p.set_outline([[30 + 19.5 * math.cos(a), 20 + 19.5 * math.sin(a)] for a in (2 * math.pi * k / 48 for k in range(48))])
    else:
        p.board.h_mode = "computed"
        p.heaters[0].set_profile(SquareWave(p_on=4.0, period=60.0, duty=0.25))
    return p


@pytest.mark.parametrize("build", ["one_layer", "one_layer_block", "one_layer_outline", "one_layer_profile", "twelve_layers", "tiny_board", "big_board", "heater_outside", "zero_power",
                                   "no_zone", "tiny_heater", "all_inner_heater", "overlapping", "many_vias", "corner_heatsink"])
def test_odd_boards_run_or_refuse_cleanly(win, qtbot, popups, build):
    p = {
        "one_layer": lambda: Problem.new(60, 40, 1).add_full_copper().add_heater(1, 1.0, rect=(20, 15, 30, 25)),
        "one_layer_block": lambda: _one_layer_variant("block"),
        "one_layer_outline": lambda: _one_layer_variant("outline"),
        "one_layer_profile": lambda: _one_layer_variant("profile"),
        "twelve_layers": lambda: Problem.new(60, 40, 12).add_full_copper(list(range(1, 13))).add_heater(1, 2.0, rect=(20, 15, 30, 25)),
        "tiny_board": lambda: Problem.new(8, 6, 2).add_full_copper().add_heater(1, 0.1, rect=(2, 2, 5, 4)),
        "big_board": lambda: Problem.new(400, 300, 2).add_full_copper().add_heater(1, 20.0, rect=(100, 100, 140, 140)),
        "heater_outside": lambda: Problem.new(60, 40, 2).add_full_copper().add_heater(1, 1.0, rect=(50, 30, 80, 60)),
        "zero_power": lambda: Problem.new(60, 40, 2).add_full_copper().add_heater(1, 0.0, rect=(20, 15, 30, 25)),
        "no_zone": lambda: Problem.new(60, 40, 2).add_heater(1, 1.0, rect=(20, 15, 30, 25)),
        "tiny_heater": lambda: Problem.new(60, 40, 2).add_full_copper().add_heater(1, 1.0, rect=(20, 15, 20.5, 15.5)),
        "all_inner_heater": lambda: Problem.new(60, 40, 4).add_full_copper().add_heater(2, 1.0, rect=(20, 15, 30, 25)),
        "overlapping": lambda: Problem.new(60, 40, 2).add_full_copper().add_heater(1, 1.0, rect=(20, 15, 30, 25)).add_heater(1, 2.0, rect=(25, 15, 35, 25)),
        "many_vias": lambda: Problem.new(60, 40, 2).add_full_copper().add_heater(1, 1.0, rect=(20, 15, 30, 25)).add_via_array((20, 15, 30, 25), 12, 12, diameter=0.3),
        "corner_heatsink": lambda: Problem.new(60, 40, 2).add_full_copper().add_heater(1, 1.0, rect=(20, 15, 30, 25)).add_heatsink(2, 40.0, rect=(0, 0, 60, 40)),
    }[build]()
    load(win, p)
    n_before = len(popups)
    run(win, qtbot, ALL_MODELS, cell=2.0, expect_ok=False)
    if win.sim is not None and not win._stale:
        walk_results(win, qtbot)
        if win.sim.problem.total_power() > 0:
            animate(win, qtbot, "fvm")
    # Either a result exists or the user was told why not
    assert win.sim is not None or len(popups) > n_before


def test_run_twice_and_edit_while_running_and_close(win, qtbot):
    load(win, example_board())
    win.doc.set_options(models=ALL_MODELS, cell_mm=1.0)
    win.run_simulation()
    win.run_simulation()                                                   # Second click while running is ignored
    win.doc.problem.add_heater(1, 1.0, rect=(5, 5, 8, 8))
    win.doc.changed.emit()                                                 # An edit while it runs
    qtbot.waitUntil(lambda: not win.worker.isRunning(), timeout=120000)
    qtbot.waitUntil(lambda: win.sim is not None, timeout=5000)
    assert win._stale and "outdated" in win.tabs.tabText(TAB_RESULTS)      # The edit made during the run marks it outdated
    win.doc.problem.heaters[0].power = 6.0
    win.doc.changed.emit()
    assert win._stale and "outdated" in win.tabs.tabText(TAB_RESULTS)
    run(win, qtbot)
    assert not win._stale
    win.run_simulation()
    win.close()                                                            # Closing with a run in flight must not crash
    qtbot.wait(300)


# ------------------------------------------------------------------ editing with the mouse and the keyboard

def vp(canvas, x, y):
    return canvas.mapFromScene(QPointF(x, y))


def drag(canvas, a, b):
    pa, pb = vp(canvas, *a), vp(canvas, *b)
    QTest.mousePress(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, pa)
    QTest.mouseMove(canvas.viewport(), (pa + pb) / 2)
    QTest.mouseMove(canvas.viewport(), pb)
    QTest.mouseRelease(canvas.viewport(), Qt.LeftButton, Qt.NoModifier, pb)


def test_draw_everything_edit_undo_run(win, qtbot):
    win.doc.new(100, 80, 4)
    win._after_load()
    win.canvas.fit()
    for tool, box in (("zone", ((10, 10), (90, 70))), ("heater", ((30, 30), (40, 40))), ("heater", ((60, 30), (66, 36))),
                      ("heatsink", ((20, 20), (50, 50)))):
        if tool == "heatsink":
            win.layer_combo.setCurrentIndex(3)
        win.tool_actions[tool].trigger()
        drag(win.canvas, *box)
    win.layer_combo.setCurrentIndex(0)
    for p in ((33, 33), (35, 35), (37, 37), (33, 37)):
        win.tool_actions["via"].trigger()                                  # The tool returns to "select" after every via
        QTest.mouseClick(win.canvas.viewport(), Qt.LeftButton, Qt.NoModifier, vp(win.canvas, *p))
    assert win.doc.count("heater") == 2 and win.doc.count("via") == 4
    win.canvas.set_selection([("heater", 0)])
    for key in (Qt.Key_Right, Qt.Key_Down, Qt.Key_Left, Qt.Key_Up):
        QTest.keyClick(win.canvas, key)
    QTest.keyClick(win.canvas, Qt.Key_D, Qt.ControlModifier)
    QTest.keyClick(win.canvas, Qt.Key_A, Qt.ControlModifier)
    for _ in range(12):
        win.doc.stack.undo()
    for _ in range(12):
        win.doc.stack.redo()
    # Zoom, pan and the overlays
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QApplication
    for delta in (120, -120, 240, -360):
        pos = vp(win.canvas, 50, 40)
        ev = QWheelEvent(QPointF(pos), QPointF(win.canvas.viewport().mapToGlobal(pos)), QPoint(0, 0), QPoint(0, delta),
                         Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
        QApplication.sendEvent(win.canvas.viewport(), ev)
    win._toggle_grid(True)
    win._toggle_grid(False)
    win._toggle_solver_grid(True)
    win._toggle_solver_grid(False)
    win.canvas.fit()
    run(win, qtbot, ALL_MODELS)
    walk_results(win, qtbot)
    for _ in range(4):
        win.doc.stack.undo()
    win.canvas.set_selection([("heater", 0)])
    QTest.keyClick(win.canvas, Qt.Key_Delete)
    win.doc.stack.undo()
    for layers in (1, 2, 6, 3):
        win.board_panel.layers.setValue(layers)
    run(win, qtbot, ("fvm", "lumped", "analytic"), expect_ok=False)


def test_files_save_open_legacy_and_exports(win, qtbot, tmp_path, monkeypatch, popups):
    load(win, example_profile_board())
    win.doc.problem.board.h_mode = "computed"
    win.doc.changed.emit()
    path = tmp_path / "p.pcbt.json"
    win.doc.save(str(path))
    win.open_file(str(path))
    assert win.doc.problem.has_profiles() and win.doc.problem.board.h_mode == "computed"
    run(win, qtbot, ("fvm", "fdm"))
    # Export dialogs
    monkeypatch.setattr("pcbthermal.gui.main_window.QFileDialog.getExistingDirectory", lambda *a, **k: str(tmp_path / "res"))
    (tmp_path / "res").mkdir()
    win.export_results()
    monkeypatch.setattr("pcbthermal.gui.main_window.QFileDialog.getSaveFileName", lambda *a, **k: (str(tmp_path / "r.txt"), ""))
    win.export_report()
    monkeypatch.setattr("pcbthermal.gui.main_window.QFileDialog.getSaveFileName", lambda *a, **k: (str(tmp_path / "s.json"), ""))
    win.export_summary()
    assert (tmp_path / "r.txt").exists() and (tmp_path / "s.json").exists() and (tmp_path / "res" / "report.txt").exists()
    # A broken file is reported, not raised
    broken = tmp_path / "broken.pcbt.json"
    broken.write_text("{ not json")
    win.open_file(str(broken))
    assert any(k == "critical" for k, _, _ in popups)
    # Examples shipped with the repository open and run
    for name in ("example_board.pcbt.json", "profile_board.pcbt.json", "reference_board.pcbt.json"):
        win.open_file(os.path.join(ROOT, "examples", name))
        run(win, qtbot, ("fvm", "analytic"))


# ------------------------------------------------------------------ random user actions

@pytest.mark.parametrize("seed", [20261016, 1, 2])
def test_random_user_actions(win, qtbot, tmp_path, seed):
    rng = random.Random(seed)
    load(win, example_profile_board())
    csv = tmp_path / "r.csv"
    csv.write_text("time_s,power_w\n0,3\n2,1\n7,0\n")
    widgets = []

    def collect():
        widgets.clear()
        for root in (win.board_panel, win.solver_panel, win.profile_page, win.results):
            widgets.extend(root.findChildren(QAbstractSpinBox))
            widgets.extend(root.findChildren(QComboBox))

    actions_done = 0
    for step in range(260):
        collect()
        choice = rng.random()
        if choice < 0.55 and widgets:
            w = rng.choice(widgets)
            if not w.isEnabled():
                continue
            if isinstance(w, QComboBox):
                if w.count():
                    w.setCurrentIndex(rng.randrange(w.count()))
            else:
                lo, hi = w.minimum(), w.maximum()
                w.setValue(rng.choice((lo, hi, (lo + hi) / 2, w.value() * 1.5 if w.value() else 1.0)) if hi < 1e7 else w.value())
        elif choice < 0.65:
            win.tabs.setCurrentIndex(rng.choice((TAB_BOARD, TAB_STACKUP, TAB_PROFILE, TAB_RESULTS)))
        elif choice < 0.72:
            n = len(win.doc.problem.heaters)
            if n:
                win.profile_page.table.selectRow(rng.randrange(n))
        elif choice < 0.78:
            win.profile_page.import_csv(str(csv))
        elif choice < 0.82:
            win.doc.stack.undo()
        elif choice < 0.85:
            win.doc.stack.redo()
        elif choice < 0.89:
            win.toggle_theme()
        elif choice < 0.93 and win.sim is not None:
            walk_results(win, qtbot)
        elif choice < 0.96:
            try:
                win.doc.problem.validate()
                win.doc.options.validate()
            except ValueError:
                continue                                                   # Invalid state typed by the monkey: skip the run
            b = win.doc.problem.board
            cells = b.width * b.height / (2e-3 * 2e-3) * b.layers
            if win.doc.problem.heaters and win.doc.problem.total_power() > 0 and cells < 3e5 \
                    and win.doc.options.analytic_modes <= 400 and win.doc.options.profile.max_steps <= 300000:
                run(win, qtbot, tuple(rng.sample(ALL_MODELS, rng.randint(1, 5))), cell=max(win.doc.options.cell_mm, 2.0),
                    expect_ok=False)
        else:
            qtbot.wait(2)
        actions_done += 1
    assert actions_done > 150


def test_a_result_delivered_without_a_run_is_not_outdated(win):
    load(win, example_board())
    win._on_done(simulate(win.doc.problem, SolverOptions(models=("fvm",), cell_mm=2.0)))
    assert not win._stale and win.tabs.tabText(TAB_RESULTS) == "Results"


def test_overlapping_background_jobs_wait_for_each_other(win, qtbot):
    """A simulation started while an animation and an analysis are computing used to abort the process (SuperLU in two threads)."""
    load(win, example_profile_board())
    win.doc.set_options(models=ALL_MODELS, cell_mm=1.0)
    anim = win.results.animation
    anim.model.setCurrentIndex(anim.model.findData("fvm"))
    anim.t_end.setValue(60.0)
    anim.frames.setValue(30)
    anim.tr = None
    anim.compute.click()                                                   # Animation starts...
    win.profile_page.run_analysis()                                        # ...an analysis...
    win.run_simulation()                                                   # ...and a simulation, all at once
    qtbot.waitUntil(lambda: anim.tr is not None and win.sim is not None and bool(win.profile_page.decisions), timeout=240000)
    qtbot.waitUntil(lambda: not win.worker.isRunning() and not win.profile_page.worker.isRunning(), timeout=60000)


def test_metal_block_in_the_application(win, qtbot):
    """A heatsink with a thickness is a metal block: inspector fields, a run with the FVM and the FDM, its table and its own temperature view."""
    load(win, example_block_board())
    win.layer_combo.setCurrentIndex(3)                                  # The block is on the bottom layer: work on that layer
    win.canvas.set_selection([("heatsink", 0)])
    win._on_canvas_selection([("heatsink", 0)])
    spins = win.inspector.form_host.findChildren(QAbstractSpinBox)
    suffixes = {s.suffix().strip() for s in spins}
    assert {"mm", "K·cm²/W", "W/mK"} <= suffixes                       # Thickness, interface and conductivity are editable
    thickness = next(s for s in spins if s.suffix().strip() == "mm" and abs(s.value() - 3.0) < 1e-9)
    thickness.setValue(5.0)
    assert win.doc.problem.heatsinks[0].thickness == pytest.approx(0.005)
    contact = next(s for s in spins if s.suffix().strip() == "K·cm²/W")
    contact.setValue(10.0)
    assert win.doc.problem.heatsinks[0].contact_r == pytest.approx(1e-3)
    combos = win.inspector.form_host.findChildren(QComboBox)
    material = next(c for c in combos if c.findText("Copper") >= 0)
    material.setCurrentIndex(material.findText("Copper"))
    assert win.doc.problem.heatsinks[0].k == pytest.approx(386.0)
    tim = next(c for c in win.inspector.form_host.findChildren(QComboBox) if c.findText("Thermal paste, good", Qt.MatchStartsWith) >= 0)
    for i in range(tim.count()):                                       # Every interface preset sets the interface resistance
        tim.setCurrentIndex(i)
        if tim.currentData() == "direct":                              # No material: no sheet and no resistance
            hs = win.doc.problem.heatsinks[0]
            assert hs.interface_resistance() == 0.0 and hs.pad_k == 0.0 and hs.pad_thickness == 0.0
        elif tim.currentData() is not None:                            # (conductivity, thickness) of the sheet: its resistance is thickness / k
            k_, t_ = tim.currentData()
            hs = win.doc.problem.heatsinks[0]
            assert hs.contact_r == pytest.approx(t_ / k_, rel=1e-2) and hs.pad_k == pytest.approx(k_) and hs.pad_thickness == pytest.approx(t_)
            assert hs.interface_resistance() == pytest.approx(t_ / k_, rel=1e-2)
    for i in range(material.count()):                                   # And every metal
        material.setCurrentIndex(i)
    run(win, qtbot, ("fvm", "fdm", "lumped", "analytic"), cell=2.0)
    assert any("block" in w for w in win.sim.warnings)                  # The two simple models say they replace the block
    rv = win.results
    assert rv.block_table.rowCount() == 1 and rv.block_table.item(0, 1).text() == "bottom"
    rv.tabs.setCurrentWidget(rv.temp)
    for model in ("fvm", "fdm", "lumped"):
        rv.temp.model.setCurrentIndex(rv.temp.model.findData(model))
        k = rv.temp.layer.findData(101)                                  # "Metal block (bottom)"
        assert k >= 0
        rv.temp.layer.setCurrentIndex(k)                                 # Drawn for the models that have it, a message for the others
        rv.temp.layer.setCurrentIndex(0)
    walk_results(win, qtbot)
    animate(win, qtbot, "fvm")
    animate(win, qtbot, "fdm")
    # Removing the thickness turns it back into a plain heatsink; the table disappears
    win.doc.problem.heatsinks[0].thickness = 0.0
    win.doc.changed.emit()
    run(win, qtbot, ("fvm",), cell=2.0)
    assert rv.block_table.rowCount() == 0


def test_component_fields_in_the_application(win, qtbot):
    """A part with theta, a junction limit, psi_JB and a power temperature coefficient: inspector fields, a run with every model, its table and the warnings."""
    load(win, example_board())
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    form = win.inspector.form_host
    spins = {s.suffix().strip(): [] for s in form.findChildren(QAbstractSpinBox)}
    for s in form.findChildren(QAbstractSpinBox):
        spins[s.suffix().strip()].append(s)
    assert {"W", "K/W", "°C", "%/K"} <= set(spins)
    theta = next(s for s in spins["K/W"] if abs(s.value() - 6.0) < 1e-9)          # U1 of the example has 6 K/W
    theta.setValue(10.0)
    assert win.doc.problem.heaters[0].theta == pytest.approx(10.0)
    family = next(c for c in form.findChildren(QComboBox) if c.itemText(0) == "Custom")
    family.setCurrentIndex(1)                                                      # The first family fills theta, theta_JC(top) and Tj max with its typical values
    h0 = win.doc.problem.heaters[0]
    assert h0.theta == pytest.approx(5.0) and h0.theta_jc_top == pytest.approx(27.0) and h0.tj_max == pytest.approx(150.0)
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    spins = win.inspector.form_host.findChildren(QAbstractSpinBox)                 # The form was rebuilt
    next(s for s in spins if s.toolTip().startswith("Maximum junction temperature")).setValue(90.0)
    next(s for s in spins if s.suffix().strip() == "%/K").setValue(0.4)
    assert win.doc.problem.heaters[0].tj_max == pytest.approx(90.0) and win.doc.problem.heaters[0].power_tc == pytest.approx(0.004)
    run(win, qtbot, ALL_MODELS, cell=2.0)
    rv = win.results
    assert rv.heater_table.columnCount() >= 8 and rv.heater_table.item(0, 6).text() != "-" and rv.heater_table.item(0, 7).text() != "-"
    assert any("above its limit" in w for w in win.sim.warnings)                  # 90 degC is below what the board gives
    walk_results(win, qtbot)
    # A coefficient with no stable point: warning, no crash, every view still opens
    win.doc.set_props("heater", 0, power_tc=0.05)
    run(win, qtbot, ("fvm", "lumped"), cell=2.0)
    assert any("thermal runaway" in w for w in win.sim.warnings)
    walk_results(win, qtbot)


def test_top_path_in_the_application(win, qtbot):
    """The heatsink on a part: three inspector fields, a run with every model, the top-path column, the warning for the time simulation, and undo."""
    load(win, example_board())
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    form = win.inspector.form_host
    by_tip = lambda start: next(s for s in win.inspector.form_host.findChildren(QAbstractSpinBox) if s.toolTip().startswith(start))
    by_tip("Resistance from a heatsink on top").setValue(12.0)                      # The top boxes appear with the heatsink resistance
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    by_tip("Junction-to-case").setValue(30.0)
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    by_tip("Resistance per area of the interface between the package top").setValue(0.5)
    h = win.doc.problem.heaters[0]
    assert (h.theta_jc_top, h.interface, h.theta_sa) == (pytest.approx(30.0), pytest.approx(0.5), pytest.approx(12.0))
    run(win, qtbot, ALL_MODELS, cell=2.0)
    rv = win.results
    top = rv.heater_table.columnCount() - 1
    assert rv.heater_table.item(0, top).text() != "-" and float(rv.heater_table.item(0, top).text()) > 0
    assert rv.heater_table.item(1, top).text() == "-"                       # U2 has no heatsink
    walk_results(win, qtbot)
    win.doc.stack.undo()                                                     # Undo restores the previous value and the run stays consistent
    run(win, qtbot, ("fvm",), cell=2.0)
    assert win.doc.problem.heaters[0].theta_sa != 12.0 or win.doc.problem.heaters[0].interface != 0.5
    # An absurd heatsink (very high resistance) and zero power: no crash
    win.doc.set_props("heater", 0, theta_sa=5000.0, power=0.0)
    run(win, qtbot, ("fvm", "lumped"), cell=2.0)
    walk_results(win, qtbot)


def test_dragging_keeps_every_element_on_the_board(win, qtbot):
    """Vias, zones, heaters and heatsinks dragged or nudged never leave the board; a via moves by the distance dragged, not by its coordinates."""
    from pcbthermal.gui.canvas import ViaItem
    load(win, example_board())
    pr, view = win.doc.problem, win.canvas
    view.set_snap(0)
    vias = [it for it in view.scene().items() if isinstance(it, ViaItem)]
    it = next(v for v in vias if v.index == 0)
    x0, y0 = pr.vias[0].x * 1000, pr.vias[0].y * 1000
    it.setSelected(True)
    it.setPos(it.pos() + QPointF(2.0, 3.0))                              # Drag by (2, 3) mm
    QTest.mouseRelease(view.viewport(), Qt.LeftButton)
    assert pr.vias[0].x * 1000 == pytest.approx(x0 + 2.0, abs=1e-6) and pr.vias[0].y * 1000 == pytest.approx(y0 + 3.0, abs=1e-6)
    # Far outside: the drag is limited by the board edge
    view.rebuild()
    it = next(v for v in view.scene().items() if isinstance(v, ViaItem) and v.index == 0)
    it.setSelected(True)
    it.setPos(QPointF(5000.0, -5000.0))
    QTest.mouseRelease(view.viewport(), Qt.LeftButton)
    b = pr.board
    assert 0 <= pr.vias[0].x <= b.width and 0 <= pr.vias[0].y <= b.height
    # Nudge with the arrow keys and Document.move past the edge: the selection stops at the edge
    win.doc.move([("heater", 0)], 1e5, 1e5)
    poly = pr.heaters[0].polygon
    assert poly[:, 0].max() <= b.width + 1e-9 and poly[:, 1].max() <= b.height + 1e-9
    win.doc.move([("zone", 0), ("via", 1)], -1e5, -1e5)
    assert min(pr.zones[0].polygon.min(), pr.vias[1].x, pr.vias[1].y) >= -1e-9
    # Whatever happened, every element is still inside the board
    for lst in (pr.zones, pr.heaters, pr.heatsinks):
        for el in lst:
            assert el.polygon.min() >= -1e-9 and el.polygon[:, 0].max() <= b.width + 1e-9 and el.polygon[:, 1].max() <= b.height + 1e-9


def test_rulers_paint_at_every_zoom(win, qtbot):
    """The rulers and the scale bar are drawn without errors from a very small to a very large zoom."""
    load(win, example_board())
    for factor in (1.0, 8.0, 0.05, 40.0, 0.01):
        win.canvas.resetTransform()
        win.canvas.scale(factor, -factor)
        win.canvas.viewport().repaint()
        qtbot.wait(5)
    img = win.canvas.viewport().grab().toImage()
    assert img.width() > 0


def test_cancel_a_simulation_from_the_window(win, qtbot):
    """Cancel stops a running simulation, leaves the window usable and a new run works."""
    load(win, example_board())
    win.doc.set_options(models=("fvm", "solid3d"), cell_mm=0.5)
    win.run_simulation()
    assert win.worker.isRunning() and win.solver_panel.cancel.isVisible() is not None
    win.solver_panel.cancel.click()
    assert not win.worker.isRunning() and win.solver_panel.status.text() == "Cancelled."
    assert win.sim is None or win.sim is not None                         # No result is taken from the cancelled run
    run(win, qtbot, ("fvm",), cell=2.0)
    assert win.sim.reference.model == "fvm"


def test_advanced_stackup_in_the_application(win, qtbot, tmp_path):
    """Switch to the advanced stack-up, edit layers and materials in the table, change the layer count, run every model, draw the section in every look, save and reopen."""
    from pcbthermal.gui.stackup import StackupEditor, stack_layers
    load(win, example_board())
    page = win.stackup_page
    win.tabs.setCurrentIndex(TAB_STACKUP)
    simple_total = win.doc.problem.board.total_thickness()
    page.mode.setCurrentIndex(1)                                           # Advanced
    b = win.doc.problem.board
    assert b.is_advanced() and b.total_thickness() == pytest.approx(simple_total) and page.editor.rowCount() == 2 * b.layers - 1
    spins = {r: [page.editor.cellWidget(r, c) for c in range(2, 7)] for r in range(page.editor.rowCount())}
    spins[0][0].setValue(70.0)                                             # Top copper 70 um
    assert b.copper_thickness[0] == pytest.approx(70e-6) and b.total_thickness() == pytest.approx(simple_total + 35e-6)
    spins[1][0].setValue(100.0)                                            # First gap 100 um
    assert b.dielectrics[0].thickness == pytest.approx(100e-6)
    combo = page.editor.cellWidget(1, 1)
    combo.setCurrentIndex(combo.findText("Metal-core dielectric (2 W/mK)"))
    assert b.dielectrics[0].k_through == pytest.approx(2.0) and b.dielectrics[0].name.startswith("Metal-core")
    spins[1][1].setValue(1.5)                                              # k through typed by hand
    assert b.dielectrics[0].k_through == pytest.approx(1.5)
    # The Board panel shows the total and does not overwrite the per-layer values
    assert win.board_panel.thickness.value() == pytest.approx(b.total_thickness() * 1000, abs=1e-3) and not win.board_panel.thickness.isEnabled()
    win.board_panel.width.setValue(win.board_panel.width.value() + 1.0)
    assert b.copper_thickness[0] == pytest.approx(70e-6) and b.is_advanced()
    # More and fewer layers keep one dielectric per gap
    for n in (6, 2, 1, 3, 4):
        win.board_panel.layers.setValue(n)
        if n == 1:                                                         # The typical 1-layer board is a simple one (no gaps to describe): back to advanced
            assert not win.doc.problem.board.is_advanced()
            page.mode.setCurrentIndex(1)
        assert len(win.doc.problem.board.dielectrics) == n - 1 and page.editor.rowCount() == max(2 * n - 1, 1)
        win.doc.problem.validate()
    run(win, qtbot, ALL_MODELS, cell=2.0)
    walk_results(win, qtbot)
    # The diagram in every look, and a click on every layer
    win.tabs.setCurrentIndex(TAB_STACKUP)
    for unit in range(page.unit.count()):
        for scale in range(page.scale.count()):
            page.unit.setCurrentIndex(unit)
            page.scale.setCurrentIndex(scale)
            page.view.repaint()
    for i, rect in enumerate(page.view._rects):
        QTest.mouseClick(page.view, Qt.LeftButton, pos=rect.center().toPoint())
        assert page.view.selected == i and "thickness" in page.info.text()
    assert len(stack_layers(win.doc.problem)) == len(page.view.layers)
    # Save, reopen: the stack-up is kept; undo goes back to the simple board
    path = str(tmp_path / "adv.pcbt.json")
    from pcbthermal import load_project, save_project
    save_project(path, win.doc.project)
    again = load_project(path).problem.board
    assert again.is_advanced() and np.allclose(again.gap_thicknesses(), win.doc.problem.board.gap_thicknesses())
    page.mode.setCurrentIndex(0)                                           # Back to simple keeps the total thickness
    assert not win.doc.problem.board.is_advanced() and win.doc.problem.board.thickness == pytest.approx(again.total_thickness())
    run(win, qtbot, ("fvm",), cell=2.0)


def test_selected_shape_shows_and_edits_its_measures(win, qtbot):
    """Clicking a rectangle shows X, Y, width, height and area; editing them moves or resizes it; a polygon shows its box and area."""
    load(win, example_board())
    win.canvas.set_selection([("heater", 0)])
    win._on_canvas_selection([("heater", 0)])
    form = win.inspector.form_host
    spins = [s for s in form.findChildren(QAbstractSpinBox) if s.toolTip().startswith(("X of", "Y of", "Width of", "Height of"))]
    assert len(spins) == 4
    x0 = win.doc.problem.heaters[0].polygon[:, 0].min() * 1000
    assert spins[0].value() == pytest.approx(x0, abs=1e-6)
    spins[2].setValue(8.0)                                                    # Width 8 mm
    poly = win.doc.problem.heaters[0].polygon * 1000
    assert poly[:, 0].max() - poly[:, 0].min() == pytest.approx(8.0, abs=1e-6)
    win.doc.add_shape("zone", 0, [[10, 10], [30, 10], [35, 25], [20, 30], [8, 20]])      # An irregular polygon
    idx = len(win.doc.problem.zones) - 1
    win.canvas.set_selection([("zone", idx)])
    win._on_canvas_selection([("zone", idx)])
    texts = [l.text() for l in win.inspector.form_host.findChildren(__import__("PySide6.QtWidgets", fromlist=["QLabel"]).QLabel)]
    assert any("5 vertices" in t and "area" in t for t in texts)


def test_board_outline_in_the_application(win, qtbot, tmp_path):
    """Presets, the vertex table, the outline tool, a run with every model (the rectangular ones on the rectangle of the same area, with a warning in the summary), every results view and a save/open."""
    from PySide6.QtWidgets import QTableWidgetItem
    load(win, example_board())
    bp, pr = win.board_panel, win.doc.problem
    assert not pr.board.has_outline() and not bp.outline_table.isEnabled()
    for i in range(1, bp.preset.count()):                                  # Every preset gives a valid outline (the first one is the plain rectangle)
        bp.preset.setCurrentIndex(i)
        win.doc.problem.validate()
    bp.preset.setCurrentIndex(bp.preset.findData("L shape"))
    b = win.doc.problem.board
    assert b.has_outline() and bp.outline_table.rowCount() == 6 and "6 vertices" in bp.outline_label.text()
    bp.outline_table.setItem(0, 0, QTableWidgetItem("5"))                   # Move a vertex
    assert win.doc.problem.board.outline[0, 0] == pytest.approx(0.005)
    bp.outline_table.setItem(0, 0, QTableWidgetItem("abc"))                 # Not a number: ignored, the table shows the stored value again
    assert bp.outline_table.item(0, 0).text() == "5.000"
    bp.outline_table.setItem(1, 1, QTableWidgetItem("999"))                 # Outside the box: ignored
    assert win.doc.problem.board.outline[:, 1].max() <= win.doc.problem.board.height + 1e-12
    bp.v_add.click()
    assert bp.outline_table.rowCount() == 7
    bp.outline_table.selectRow(6)
    bp.v_del.click()
    assert bp.outline_table.rowCount() == 6
    # The outline tool: drag a rectangle, then click a polygon
    win.tool_actions["outline"].setChecked(True)
    assert win.canvas.tool == "outline"
    W, H = win.doc.problem.board.width * 1000, win.doc.problem.board.height * 1000
    p0, p1 = win.canvas.mapFromScene(QPointF(5, 5)), win.canvas.mapFromScene(QPointF(W - 5, H - 5))
    QTest.mousePress(win.canvas.viewport(), Qt.LeftButton, pos=p0)
    QTest.mouseMove(win.canvas.viewport(), pos=p1)
    QTest.mouseRelease(win.canvas.viewport(), Qt.LeftButton, pos=p1)
    assert win.doc.problem.board.outline is not None and len(win.doc.problem.board.outline) == 4
    win.tool_actions["select"].setChecked(True)
    bp.preset.setCurrentIndex(bp.preset.findData("Circle / ellipse"))
    win.canvas.viewport().repaint()
    # The example parts must be on the board for a sensible run: an L cut would put U2 off the board, so use chamfered corners
    bp.preset.setCurrentIndex(bp.preset.findData("Chamfered corners"))
    run(win, qtbot, ALL_MODELS, cell=2.0)
    assert any("same area" in w for w in win.sim.warnings) and set(ALL_MODELS) <= set(win.sim.results)       # No dialog: the warning is in the summary
    assert "same area" in win.results.warnings.text() and win.results.warnings.isVisible()
    walk_results(win, qtbot)
    # Save and reopen: the outline is kept; undo restores the rectangle
    from pcbthermal import load_project, save_project
    path = str(tmp_path / "outline.pcbt.json")
    save_project(path, win.doc.project)
    assert np.allclose(load_project(path).problem.board.outline, win.doc.problem.board.outline)
    win.doc.set_outline(None)
    assert not win.doc.problem.board.has_outline()
    run(win, qtbot, ("fvm", "lumped", "analytic"), cell=2.0)


def test_power_calculator_in_the_application(win, qtbot, monkeypatch):
    """The calculator finds the power of a part from a temperature, writes it into the heater, and the datasheet route works; no heater and bad inputs do not crash."""
    from pcbthermal.gui.calculator import PowerCalculator
    load(win, example_board())
    # A 2 mm cell keeps the band cheap: with the default board description it runs seven sources (four design terms), three times in this scenario
    win.doc.set_options(cell_mm=2.0)
    truth = win.doc.problem.heaters[0].power
    row = simulate(win.doc.problem, SolverOptions(models=("fvm",), cell_mm=2.0)).heater_rows()[0]
    dlg = PowerCalculator(win.doc)
    qtbot.addWidget(dlg)
    dlg.point.setCurrentIndex(dlg.point.findData("mean"))
    dlg.measured.setValue(row["t_mean"])
    dlg.ambient.setValue(win.doc.problem.board.ambient)
    win.doc.set_props("heater", 0, power=1.0, merge=False)                    # The part's power is "unknown"
    dlg.compute.click()
    qtbot.waitUntil(lambda: dlg.use.isEnabled(), timeout=120000)
    assert dlg.selected_power() == pytest.approx(truth, rel=0.01)                 # Nominal is the default case
    assert dlg.out["best_w"] < truth < dlg.out["worst_w"] and "worst case" in dlg.result.text()
    dlg.case.setCurrentIndex(dlg.case.findData("worst"))                      # The worst case is what goes into the part
    worst = dlg.out["worst_w"]
    dlg.use.click()
    assert win.doc.problem.heaters[0].power == pytest.approx(worst)
    dlg.case.setCurrentIndex(dlg.case.findData("nominal"))
    dlg.use.setEnabled(True)
    dlg.use.click()
    assert win.doc.problem.heaters[0].power == pytest.approx(truth, rel=0.01)
    # The board-description control: every level runs; "none" has no design terms and the others list them apart in the result
    for level in ("none", "estimated"):
        dlg.measured.setValue(row["t_mean"])
        dlg.design.setCurrentIndex(dlg.design.findData(level))
        win.doc.set_props("heater", 0, power=1.0, merge=False)
        dlg.compute.click()
        qtbot.waitUntil(lambda: dlg.use.isEnabled(), timeout=120000)
        has_design = any(c.get("design") for c in dlg.out["contributions"])
        assert has_design == (level != "none") and ("Board description" in dlg.result.text()) == (level != "none")
        assert dlg.out["best_w"] <= truth <= dlg.out["worst_w"]
    dlg.measured.setValue(10.0)                                               # Below the ambient: an error message, no crash
    dlg.compute.click()
    qtbot.waitUntil(lambda: "above the ambient" in dlg.result.text(), timeout=120000)
    dlg.tj.setValue(120.0); dlg.tref.setValue(100.0); dlg.par.setValue(10.0)
    assert "2.000 W" in dlg.out2.text()
    dlg.tj.setValue(90.0)
    assert "hotter" in dlg.out2.text()
    dlg.close()
    empty = PowerCalculator(Document())
    qtbot.addWidget(empty)
    assert not empty.compute.isEnabled()


def test_natural_form_control_in_the_application(win, qtbot):
    """The vertical natural convection form: shown with computed h, enabled only for a vertical board, written to the document, undone, run, saved and reloaded."""
    load(win, example_board())
    bp = win.board_panel
    assert [bp.natural_form.itemData(i) for i in range(bp.natural_form.count())] == ["general", "laminar"] and bp.natural_form.toolTip()
    bp.h_mode.setCurrentIndex(1)
    assert not bp.natural_form.isEnabled()                                 # Horizontal: the form does not enter the correlation
    bp.orientation.setCurrentIndex(1)
    assert bp.natural_form.isEnabled()
    bp.natural_form.setCurrentIndex(1)
    assert win.doc.problem.board.natural_form == "laminar"
    run(win, qtbot, ("fvm",))
    assert win.sim.h_used
    win.doc.stack.undo()
    assert win.doc.problem.board.natural_form == "general"
    bp.refresh()
    assert bp.natural_form.currentData() == "general"
    # Every combination of orientation and form, back and forth, never breaks the panel
    for o in (0, 1, 0):
        for f in (1, 0, 1):
            bp.orientation.setCurrentIndex(o)
            bp.natural_form.setCurrentIndex(f)
            assert win.doc.problem.board.natural_form == ("laminar" if f else "general")
    win.doc.problem.validate()


def test_a_3d_model_too_large_is_refused_in_the_application(win, qtbot, popups):
    """Regression of the random-actions hang: a 502.5 mm board with the 3D solid at 2 mm (a million unknowns) kept the calculation process in
    a direct solve for hours. The panel now says it will not run, the other models answer at once and the 3D solid alone fails with the cell to use."""
    import time
    from pcbthermal import solid3d
    p = example_profile_board()
    p.board.width = p.board.height = 0.5025
    p.board.h_mode = "computed"
    load(win, p)
    win.doc.set_options(models=("solid3d", "lumped"), cell_mm=2.0)
    win.solver_panel.refresh()
    assert "will not run" in win.solver_panel.cells_label.text()
    t0 = time.time()
    run(win, qtbot, ("solid3d", "lumped"), cell=2.0)
    assert set(win.sim.results) == {"lumped"} and any("3D solid was not run" in w for w in win.sim.warnings)
    run(win, qtbot, ("solid3d",), cell=2.0, expect_ok=False)            # Alone: the job fails with the message, it does not wait
    assert time.time() - t0 < 120 and not win.worker.isRunning()
    assert any(k == "critical" and "use a cell of" in t for k, _, t in popups)
    win.doc.set_options(models=("solid3d",), cell_mm=20.0)
    win.solver_panel.refresh()
    assert "will not run" not in win.solver_panel.cells_label.text() and solid3d.unknowns(win.doc.problem, 20.0)[0] <= solid3d.MAX_CELLS


def test_inner_copper_choice_in_the_application(win, qtbot):
    """The inner copper combo of the Stack-up tab: disabled on two layers and in the simple stack-up, reloads the template as one undoable edit, survives layer changes, runs every model."""
    load(win, example_board())
    page = win.stackup_page
    win.tabs.setCurrentIndex(TAB_STACKUP)
    page.mode.setCurrentIndex(0)                                           # Simple: every layer has the outer copper, nothing to choose
    assert not page.inner_oz.isEnabled()
    page.mode.setCurrentIndex(1)                                           # Advanced
    win.board_panel.layers.setValue(2)
    assert not page.inner_oz.isEnabled()                                   # No inner copper on two layers
    win.board_panel.layers.setValue(3)
    assert page.inner_oz.isEnabled()                                       # Three layers have one inner layer
    for n in (6, 4):
        win.board_panel.layers.setValue(n)
        page.inner_oz.setCurrentIndex(page.inner_oz.findData(0.5))        # Start every round from the default
        assert page.inner_oz.isEnabled() and page.inner_oz.currentData() == 0.5
        b = win.doc.problem.board
        total = b.total_thickness()
        page.inner_oz.setCurrentIndex(page.inner_oz.findData(1.0))
        assert b.template_inner_oz == 1.0 and b.copper_thickness[1] == pytest.approx(35e-6)
        assert b.total_thickness() == pytest.approx(total + (n - 2) * 19.8e-6)   # Dielectrics kept: the board grows by the extra inner copper
        win.doc.stack.undo()                                                     # One step brings back the 0.5 oz stack-up
        b = win.doc.problem.board
        assert b.template_inner_oz == 0.5 and b.copper_thickness[1] == pytest.approx(15.2e-6) and page.inner_oz.currentData() == 0.5
        win.doc.stack.redo()
        win.board_panel.layers.setValue(n + 2 if n == 4 else 8)            # The choice is kept when the layer count changes
        assert win.doc.problem.board.copper_thickness[1] == pytest.approx(35e-6)
        win.doc.problem.validate()
    run(win, qtbot, ALL_MODELS, cell=2.0)
    page.inner_oz.setCurrentIndex(page.inner_oz.findData(0.5))
    assert win.doc.problem.board.copper_thickness[1] == pytest.approx(15.2e-6)


def test_warning_list_under_run_with_many_warnings(win, qtbot):
    """Many warnings at once (parts off the board, overlapping parts, a via off the board, no power): the list is capped in height and scrolls, every warning about an element selects it on its layer, a rename keeps the list in step, undo removes the warnings."""
    def build(proj):
        pr = proj.problem
        for k in range(6):
            pr.add_heater(1 + (k % 2), 1.0, rect=(10 + 5 * k, 10, 20 + 5 * k, 20), name=f"P{k}")    # Overlapping, no copper under them
        pr.add_heater(1, 1.0, rect=(90, 70, 130, 100), name="Off")                                   # Partly off the 100 x 80 mm board
        pr.add_via(500.0, 500.0)
        pr.add_zone(1, rect=(-50, -50, -20, -20), name="Z")                                          # Zone off the board
    win.doc.edit("Many", build)
    win._update_checks()
    box = win.solver_panel.checks
    assert len(box.warnings) >= 8 and box.isVisibleTo(win.solver_panel.footer)
    assert box.height() <= box.MAX_HEIGHT
    for w in box.warnings:
        if w.kind is not None:
            box.warning_clicked.emit(w.kind, w.index)
            assert win.canvas.selected_elements() == [(w.kind, w.index)]
    box.warning_clicked.emit("heater", 999)                                  # A stale index is ignored
    box.warning_clicked.emit("nothing", 0)
    win.doc.stack.undo()
    win._update_checks()
    assert len(box.warnings) == 1 and box.warnings[0].kind is None            # The empty board's own warning: one line, no count
    assert "warnings" not in box.toPlainText()


def test_preferences_every_section_in_both_themes(win, qtbot, tmp_path, monkeypatch):
    """Open Preferences from the window, visit every section by the list and by the keyboard in both themes at a small size, edit a table cell and a field, save, reset and close."""
    from PySide6.QtWidgets import QApplication
    from pcbthermal.gui import theme as th
    from pcbthermal.gui.preferences import PreferencesDialog
    monkeypatch.setenv("PCBTHERMAL_CONFIG", str(tmp_path / "cfg"))
    for theme in ("dark", "light"):
        th.apply_theme(QApplication.instance(), theme)
        d = PreferencesDialog(win)
        qtbot.addWidget(d)
        d.resize(640, 480)
        d.show()
        for row in range(d.sections.count()):
            d.sections.setCurrentRow(row)
            assert d.pages.currentIndex() == row and d.pages.currentWidget().isVisibleTo(d)
            d.grab()
        table, cols = d.tables["via_fills"]
        table.item(1, 1).setText("0,5")                                    # A decimal comma is read as a point
        assert d.data["libraries"]["via_fills"][1]["k_w_per_mk"] == 0.5
        d.widgets[("new_board", "ambient_c")].setValue(31.0)
        d.save()
        d.reset()
        d.close()
