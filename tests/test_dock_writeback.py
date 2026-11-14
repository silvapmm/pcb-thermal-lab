#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_dock_writeback.py
@brief Editing one field of the Board settings or Simulation settings dock never rewrites another field, and a value loaded from a project is never clamped by a box.
@details The defect: after opening a project with a copper layer of 10 000 um (a 10 mm plate), any edit of any field of the Board dock wrote the clamped box (210 um) back into the
         project, and h above 500 W/m2K and a thickness above 10 mm were clamped the same way, so the next run read hundreds of degrees too hot with no warning. Now a box widens
         to hold a loaded value (`spinfit.fit_range`) and the dock writes only the boxes the user changed.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QAbstractSpinBox, QMessageBox

from pcbthermal import Problem, SolverOptions, simulate
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow
from pcbthermal.gui.spinfit import fit_range
from pcbthermal.model import Materials


@pytest.fixture
def win(qtbot, tmp_path, monkeypatch):
    """!
    @brief A main window with its message boxes replaced (a real box would block the test).
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder for the settings file.
    @param monkeypatch pytest fixture.
    @return MainWindow
    """
    for kind in ("warning", "critical", "information"):
        monkeypatch.setattr(f"pcbthermal.gui.main_window.QMessageBox.{kind}", lambda *a, **k: None)
    monkeypatch.setattr("pcbthermal.gui.main_window.QMessageBox.question", lambda *a, **k: QMessageBox.Discard)
    w = MainWindow(Document(), QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.resize(1500, 900)
    w.show()
    return w


def plate(h_bottom=400.0):
    """!
    @brief A 50 x 50 x 10 mm copper plate (k 150 W/mK) with four 10 x 10 mm sources, as in the published case 2 of Muzychka and others (2003).
    @param h_bottom Bottom coefficient in W/m2K.
    @return Problem
    """
    p = Problem.new(50.0, 50.0, layers=1, thickness_mm=10.001, copper_um=10000.0, ambient=25.0, h_top=1e-6, h_bottom=h_bottom, h_side=None,
                    materials=Materials(k_copper=150.0))
    p.add_full_copper(layers=None)
    for i, (cx, cy, w) in enumerate(((12.5, 12.5, 10.0), (37.5, 12.5, 25.0), (12.5, 37.5, 20.0), (37.5, 37.5, 15.0))):
        p.add_heater(1, w, rect=(cx - 5, cy - 5, cx + 5, cy + 5), name=f"S{i}")
    return p


def hottest(problem):
    """!
    @brief The FVM hottest temperature of a problem at a 2.5 mm cell, in degrees Celsius.
    @param problem Problem.
    @return float
    """
    res = simulate(problem, SolverOptions(models=("fvm",), cell_mm=2.5))
    return float(res.results["fvm"].t_max)


def test_editing_another_field_keeps_a_10_mm_plate(win):
    """!
    @brief Open the plate, edit h_bottom and the ambient, and the copper thickness, the other coefficients and the result stay as loaded.
    @param win MainWindow fixture.
    """
    win._load_problem(plate(), "plate")
    bd = win.doc.problem.board
    before = hottest(win.doc.problem)
    assert bd.copper_thickness[0] == pytest.approx(10000e-6)
    bp = win.board_panel
    assert bp.copper.value() == pytest.approx(10000.0)               # The box shows the stored value, not 210
    bp.h_bottom.setValue(401.0)
    bp.h_bottom.setValue(400.0)
    bp.ambient.setValue(25.5)
    bp.ambient.setValue(25.0)
    bd = win.doc.problem.board
    assert bd.copper_thickness[0] == pytest.approx(10000e-6) and bd.thickness == pytest.approx(10.001e-3)
    assert bd.h_bottom == pytest.approx(400.0) and bd.h_top == pytest.approx(1e-6) and bd.h_side is None
    assert hottest(win.doc.problem) == pytest.approx(before, abs=1e-9)


def test_stored_values_above_the_usual_ranges_are_held(win):
    """!
    @brief h above 500 W/m2K, a thickness above 10 mm, a width above 1 m and a big conductivity are shown and kept through an edit of another field.
    @param win MainWindow fixture.
    """
    p = plate(h_bottom=5000.0)
    p.board.h_top = 2000.0
    p.board.h_side = 800.0
    win._load_problem(p, "strong")
    bp = win.board_panel
    bp.ambient.setValue(26.0)
    bd = win.doc.problem.board
    assert (bd.h_bottom, bd.h_top, bd.h_side) == pytest.approx((5000.0, 2000.0, 800.0))
    assert bd.thickness == pytest.approx(10.001e-3) and bd.copper_thickness[0] == pytest.approx(10000e-6) and bd.ambient == 26.0


def test_every_dock_box_round_trips_a_value_at_its_limit(win):
    """!
    @brief A project whose numeric board fields are far outside the usual ranges passes through an edit of one box without any other field changing.
    @details Generic: every spin box of the Board dock is set, through the document, to a value above its original maximum, and one box is then edited.
    @param win MainWindow fixture.
    """
    win._load_problem(plate(), "limits")
    bp = win.board_panel
    p = win.doc.problem
    b = p.board
    values = dict(width=3.0, height=2.5, thickness=0.09, h_top=9e4, h_bottom=9e4, h_side=9e4, ambient=900.0, air_speed=300.0, h_calibration=50.0)
    for k, v in values.items():
        setattr(b, k, v)
    b.copper_thickness = [15000e-6]
    b.materials.k_copper, b.materials.k_fr4_through, b.materials.k_fr4_inplane = 5000.0, 500.0, 600.0
    b.via_plating = 500e-6
    win.doc.changed.emit()
    snapshot = (b.width, b.height, b.thickness, b.h_top, b.h_bottom, b.h_side, b.ambient, b.air_speed, b.h_calibration, b.copper_thickness[0],
                b.materials.k_copper, b.materials.k_fr4_through, b.materials.k_fr4_inplane, b.via_plating)
    for spin in bp.findChildren(QAbstractSpinBox):
        assert spin.minimum() <= spin.value() <= spin.maximum()
    bp.emis_top.setValue(0.8)                                         # An unrelated edit
    b = win.doc.problem.board
    after = (b.width, b.height, b.thickness, b.h_top, b.h_bottom, b.h_side, b.ambient, b.air_speed, b.h_calibration, b.copper_thickness[0],
             b.materials.k_copper, b.materials.k_fr4_through, b.materials.k_fr4_inplane, b.via_plating)
    assert after == pytest.approx(snapshot, rel=1e-12) and b.emissivity_top == 0.8


def test_a_box_shows_a_rounded_value_without_writing_it_back(win):
    """!
    @brief A stored width of 100.123456 mm is shown with one decimal; an edit of the height does not round the width.
    @param win MainWindow fixture.
    """
    p = plate()
    p.board.width = 0.100123456
    win._load_problem(p, "round")
    win.board_panel.height.setValue(51.0)
    assert win.doc.problem.board.width == pytest.approx(0.100123456, rel=1e-12)


def test_the_simulation_dock_does_not_rewrite_unedited_options(win):
    """!
    @brief The cell stored with more decimals than its box shows, and a laminate sub-gap outside the box range, survive the edit of another option.
    @param win MainWindow fixture.
    """
    win._load_problem(plate(), "options")
    o = win.doc.options
    o.cell_mm, o.laminate_s_max_mm, o.hotspot_c = 0.123456, 9.0, 2500.0
    win.doc.state_changed.emit()
    sp = win.solver_panel
    sp.rings.setValue(sp.rings.value() + 1)
    assert o.cell_mm == pytest.approx(0.123456) and o.laminate_s_max_mm == 9.0 and o.hotspot_c == 2500.0
    assert sp.hot.value() == 2500.0 and sp.lam_s.value() == 9.0


def test_fit_range_widens_and_never_clamps(qtbot):
    """!
    @brief fit_range holds a value above the maximum and below the minimum, for a double and an integer box, and leaves a value inside the range alone.
    @param qtbot pytest-qt fixture.
    """
    from PySide6.QtWidgets import QDoubleSpinBox, QSpinBox
    d = QDoubleSpinBox()
    d.setRange(1.0, 10.0)
    qtbot.addWidget(d)
    fit_range(d, 5.0)
    assert (d.minimum(), d.maximum()) == (1.0, 10.0)
    fit_range(d, 1234.5)
    fit_range(d, -7.0)
    d.setValue(1234.5)
    assert d.value() == 1234.5 and d.minimum() == -7.0
    i = QSpinBox()
    i.setRange(1, 12)
    qtbot.addWidget(i)
    fit_range(i, 40.0)
    i.setValue(40)
    assert i.value() == 40


def test_unequal_copper_and_greyed_boxes_are_not_written(win):
    """!
    @brief The copper per layer of a simple stack-up (70/17.5/17.5/70 um) is not levelled to layer 1 by an edit of another box, and a greyed box (the size of an imported board) never writes.
    @param win MainWindow fixture.
    """
    p = Problem.new(60.0, 40.0, layers=4, thickness_mm=1.6, copper_um=35.0)
    p.board.copper_thickness = [70e-6, 17.5e-6, 17.5e-6, 70e-6]
    p.board.width = 0.0600123
    win._load_problem(p, "unequal")
    bp = win.board_panel
    bp.width.setEnabled(False)                                        # What an imported board does
    bp.ambient.setValue(30.0)
    bd = win.doc.problem.board
    assert list(bd.copper_thickness) == pytest.approx([70e-6, 17.5e-6, 17.5e-6, 70e-6]) and bd.ambient == 30.0
    assert bd.width == pytest.approx(0.0600123, rel=1e-12)
    bp.width.setEnabled(True)
    bp.copper.setValue(35.0)                                          # Editing the copper box does level the layers: the user asked for it
    assert list(win.doc.problem.board.copper_thickness) == pytest.approx([35e-6] * 4)


def test_every_field_with_a_value_the_box_cannot_show_exactly_survives(win):
    """!
    @brief Loop over the board fields: each stored value has more decimals than its box (or lies outside its range) and survives the edit of the ambient.
    @param win MainWindow fixture.
    """
    exact = dict(width=0.0600123, height=0.0400456, thickness=0.00160049, h_top=12.3456, h_bottom=15.6789, h_side=11.1111, h_calibration=1.23456,
                 air_speed=0.4567, emissivity_top=0.8765, emissivity_bottom=0.7654, via_plating=24.6e-6)
    win._load_problem(plate(), "decimals")
    b = win.doc.problem.board
    for k, v in exact.items():
        setattr(b, k, v)
    b.materials.k_copper, b.materials.k_fr4_through, b.materials.k_fr4_inplane = 387.654, 0.3123, 0.9456
    b.copper_thickness = [35.7e-6]
    win.doc.changed.emit()
    win.board_panel.ambient.setValue(31.0)
    b = win.doc.problem.board
    for k, v in exact.items():
        assert getattr(b, k) == pytest.approx(v, rel=1e-12), k
    assert (b.materials.k_copper, b.materials.k_fr4_through, b.materials.k_fr4_inplane) == pytest.approx((387.654, 0.3123, 0.9456), rel=1e-12)
    assert b.copper_thickness[0] == pytest.approx(35.7e-6, rel=1e-12) and b.ambient == 31.0


def test_an_undo_reloads_the_simulation_dock(win):
    """!
    @brief An undo restores the options of the project too; the Simulation dock must show them, or the next edit of another box leaves the cell the user sees unwritten.
    @details Review: the dock reloaded only on `state_changed`, which an undo that does not change the clean flag never emits, so after the undo the box showed 0.7 mm
             while the project held 1 mm; with only edited boxes written, nothing corrected it.
    @param win MainWindow fixture.
    """
    win._load_problem(plate(), "undo")
    doc, sp = win.doc, win.solver_panel
    win.board_panel.h_top.setValue(5.0)
    doc.add_via(10.0, 10.0)
    doc.add_via(20.0, 20.0)
    sp.cell.setValue(0.7)
    assert doc.options.cell_mm == pytest.approx(0.7)
    doc.stack.undo()                                                  # The last via goes: the snapshot restores the cell of before
    assert sp.cell.value() == pytest.approx(doc.options.cell_mm)
    sp.hot.setValue(sp.hot.value() + 1.0)
    assert sp.cell.value() == pytest.approx(doc.options.cell_mm)


def test_the_power_profile_page_does_not_round_the_wave(win):
    """!
    @brief A square wave with a period of 1/3 s, a duty of 12.3456 % and powers with more decimals than the boxes keeps every field through an edit of the power while off.
    @param win MainWindow fixture.
    """
    from pcbthermal.model import SquareWave
    p = plate()
    p.heaters[0].set_profile(SquareWave(p_on=3.333333333, period=1.0 / 3.0, duty=0.123456, p_off=0.0))
    win._load_problem(p, "wave")
    page = win.profile_page
    page.current = 0
    page._load_heater()
    page.p_off.setValue(0.5)
    w = win.doc.problem.heaters[0].profile
    assert w.period == pytest.approx(1.0 / 3.0, rel=1e-12) and w.duty == pytest.approx(0.123456, rel=1e-12)
    assert w.p_on == pytest.approx(3.333333333, rel=1e-12) and w.p_off == 0.5
    page.duty.setValue(50.0)                                          # An edited box is written
    assert win.doc.problem.heaters[0].profile.duty == 0.5
    assert win.doc.problem.heaters[0].profile.period == pytest.approx(1.0 / 3.0, rel=1e-12)


def test_the_profile_run_settings_are_not_rewritten(win):
    """!
    @brief A stored time with more decimals than its box and a step limit above the box range survive the edit of the threshold, and an undo reloads them.
    @param win MainWindow fixture.
    """
    win._load_problem(plate(), "runs")
    po = win.doc.options.profile
    po.time_s, po.max_steps = 1.23456789, 50_000_000
    win.doc.state_changed.emit()
    page = win.profile_page
    assert page.max_steps.value() == 50_000_000
    page.threshold.setValue(page.threshold.value() + 0.5)
    po = win.doc.options.profile
    assert po.time_s == pytest.approx(1.23456789, rel=1e-12) and po.max_steps == 50_000_000


def test_an_integer_option_beyond_a_c_int_does_not_break_the_dock(win):
    """!
    @brief A project with a ring count beyond a C int (a hand-edited file) loads into the dock without an exception and is not rewritten by another edit.
    @param win MainWindow fixture.
    """
    win._load_problem(plate(), "huge")
    o = win.doc.options
    o.lumped_rings = 10 ** 12
    win.solver_panel.refresh()                                        # Raised OverflowError before the review
    win.solver_panel.hot.setValue(win.solver_panel.hot.value() + 1.0)
    assert win.doc.options.lumped_rings == 10 ** 12


def test_fit_range_ignores_values_no_box_can_hold(qtbot):
    """!
    @brief NaN and infinity leave the range alone, and an integer box stops at the C int.
    @param qtbot pytest-qt fixture.
    """
    from PySide6.QtWidgets import QDoubleSpinBox, QSpinBox
    from pcbthermal.gui.spinfit import INT_MAX, show_value
    d = QDoubleSpinBox()
    d.setRange(1.0, 10.0)
    qtbot.addWidget(d)
    for v in (float("nan"), float("inf"), -float("inf"), None, "x"):
        fit_range(d, v)
    assert (d.minimum(), d.maximum()) == (1.0, 10.0)
    i = QSpinBox()
    i.setRange(1, 12)
    qtbot.addWidget(i)
    for v in (float("inf"), 1e300, 10 ** 12):
        fit_range(i, v)
    assert i.maximum() == INT_MAX
    show_value(i, 10 ** 12)
    assert i.value() == INT_MAX


def test_the_h_boxes_say_why_they_are_hidden_or_greyed(win, tmp_path):
    """!
    @brief A project opened from a file shows h top, h bottom and h edges in the typed mode; the computed mode hides the first two (the mode's tooltip says so) and
           insulated edges grey the third (its tooltip says why); the models chosen change nothing.
    @details A user could not find the three coefficients at first: they are hidden when the project uses computed coefficients and the edge one is greyed when the
             edges are insulated, which no tooltip explained.
    @param win MainWindow fixture.
    @param tmp_path Temporary folder.
    """
    from pcbthermal.project import Project, save_project
    bp = win.board_panel
    for mode, h_side in (("manual", 12.0), ("computed", None)):
        p = Problem.new(60.0, 40.0, layers=2, h_side=h_side)
        p.board.h_mode = mode
        path = str(tmp_path / f"{mode}.pcbt.json")
        save_project(path, Project(problem=p))
        win.doc.open(path)
        for k in ("solid3d", "lumped", "analytic", "fdm"):
            win.solver_panel.cb[k].setChecked(True)
        typed = mode == "manual"
        assert bp.h_top.isVisibleTo(bp) == typed and bp.h_bottom.isVisibleTo(bp) == typed
        assert bp.h_top.isEnabled() and bp.h_bottom.isEnabled()
        assert bp.h_side.isVisibleTo(bp) and bp.h_side.isEnabled() == (h_side is not None)
        assert ("Greyed" in bp.h_side.toolTip()) == (h_side is None) and bp.h_side.toolTip().startswith("Heat transfer coefficient of the edges")
    assert "shown only with 'Typed by me'" in bp.h_mode.toolTip()
    bp.side_on.setChecked(True)                                       # Ticking the box enables the coefficient and drops the reason
    assert bp.h_side.isEnabled() and "Greyed" not in bp.h_side.toolTip()


def test_undo_keeps_the_solver_options_chosen_after_the_edit(win):
    """!
    @brief Edit the board, then change the cell, the models and a laminate option, then undo: the board goes back and the options stay (`Document.set_options` is not undoable).
    @param win MainWindow fixture.
    """
    win._load_problem(plate(), "undo")
    win.board_panel.ambient.setValue(30.0)
    win.solver_panel.cell.setValue(0.75)
    win.doc.set_options(models=("fvm", "fdm"), laminate_n_max=7)
    win.doc.stack.undo()
    assert win.doc.problem.board.ambient == 25.0
    o = win.doc.options
    assert o.cell_mm == 0.75 and o.models == ("fvm", "fdm") and o.laminate_n_max == 7
    assert win.solver_panel.cell.value() == 0.75
    win.doc.stack.redo()
    assert win.doc.problem.board.ambient == 30.0 and win.doc.options.cell_mm == 0.75


def test_preferences_boxes_hold_a_stored_value_outside_their_range(qtbot, tmp_path, monkeypatch):
    """!
    @brief A stored memory fraction of 0.99 (box range 0.10 to 0.95) and a Gerber file limit of 8192 MB (range 16 to 4096) are shown as stored and Save keeps them.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder for the configuration.
    @param monkeypatch pytest fixture.
    """
    from pcbthermal import defaults
    from pcbthermal.gui.preferences import PreferencesDialog
    monkeypatch.setenv("PCBTHERMAL_CONFIG", str(tmp_path / "cfg"))
    real = defaults.load

    def load(*a, **k):
        d = real(*a, **k)
        d["solver"]["memory_fraction"] = 0.99
        d["gerber"]["max_file_mb"] = 8192
        return d

    monkeypatch.setattr(defaults, "load", load)
    dlg = PreferencesDialog()
    qtbot.addWidget(dlg)
    mem, gb = dlg.widgets[("solver", "memory_fraction")], dlg.widgets[("gerber", "max_file_mb")]
    assert mem.value() == 0.99 and gb.value() == 8192
    assert dlg.data["solver"]["memory_fraction"] == 0.99 and dlg.data["gerber"]["max_file_mb"] == 8192
