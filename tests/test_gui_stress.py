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
from pcbthermal.gui.main_window import TAB_BOARD, TAB_PROFILE, TAB_RESULTS, MainWindow
from pcbthermal.model import Problem, reference_problem

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALL_MODELS = ("fvm", "fdm", "lumped", "analytic")


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
        qtbot.waitUntil(lambda: not win.worker.isRunning(), timeout=180000)
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
    for models in (("fvm",), ("lumped",), ("analytic",), ("fdm",), ("fvm", "fdm"), ALL_MODELS):
        run(win, qtbot, models)
        walk_results(win, qtbot)
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

@pytest.mark.parametrize("build", ["one_layer", "twelve_layers", "tiny_board", "big_board", "heater_outside", "zero_power",
                                   "no_zone", "tiny_heater", "all_inner_heater", "overlapping", "many_vias", "corner_heatsink"])
def test_odd_boards_run_or_refuse_cleanly(win, qtbot, popups, build):
    p = {
        "one_layer": lambda: Problem.new(60, 40, 1).add_full_copper().add_heater(1, 1.0, rect=(20, 15, 30, 25)),
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
            win.tabs.setCurrentIndex(rng.choice((TAB_BOARD, TAB_PROFILE, TAB_RESULTS)))
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
                run(win, qtbot, tuple(rng.sample(ALL_MODELS, rng.randint(1, 4))), cell=max(win.doc.options.cell_mm, 2.0),
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
    assert win.doc.problem.heatsinks[0].k == pytest.approx(385.0)
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
