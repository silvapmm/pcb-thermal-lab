#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fem_gui.py
@brief The finite-element model in the application: its checkbox, memory verdicts, mesh options, results views, read-outs, cancel, refusals and project files.

The checkbox is exposed like the 3D solid (off by default, never disabled for lack of pyamg), the FEM is skipped (not fatal) next to other models, and every number it
shows names its read-out. The runs use small boards and cells of 2 mm or more.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json

import numpy as np
import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import Qt

from pcbthermal import femcore, memory
from pcbthermal.examples import example_board
from pcbthermal.model import Materials, Problem
from tests.test_gui_stress import load, popups, run, walk_results, win  # noqa: F401  (fixtures and helpers)

needs_pyamg = pytest.mark.skipif(not femcore.available(), reason="the package pyamg is not installed")


def small_board():
    """!
    @brief A 40 x 30 mm, 2-layer board with one 1 W part (a mesh far below the limit of the direct solver).
    @return A Problem.
    """
    p = Problem.new(40, 30, layers=2, h_top=10.0, h_bottom=10.0, name="fem-small")
    p.add_full_copper([1, 2])
    p.add_heater(1, 1.0, rect=(17, 12, 23, 18), name="U1")
    return p


def thick_plate():
    """!
    @brief Case 2 of Muzychka, Culham and Yovanovich: a 50 x 50 x 10 mm copper plate with four 10 x 10 mm sources of 10, 25, 20 and 15 W, h 400 W/m2K on the bottom.
    @return A Problem.
    """
    p = Problem.new(50, 50, layers=1, thickness_mm=10.001, copper_um=1e4, ambient=25.0, h_top=1e-6, h_bottom=400.0, h_side=None, materials=Materials(k_copper=150.0))
    p.add_full_copper()
    for i, (c, pw) in enumerate(zip([(12.5, 12.5), (37.5, 12.5), (12.5, 37.5), (37.5, 37.5)], [10.0, 25.0, 20.0, 15.0])):
        p.add_heater(1, pw, rect=(c[0] - 5, c[1] - 5, c[0] + 5, c[1] + 5), name=f"S{i}")
    return p


def test_the_fem_checkbox_is_off_by_default_and_exposed_like_the_3d_solid(win):
    """!
    @brief Unticked on a new project, enabled, with the label and a short tooltip carrying the measured numbers; guarded like the 3D solid.
    @param win Main window fixture.
    """
    from pcbthermal.gui import panels, preferences
    sp = win.solver_panel
    box = sp.cb["fem"]
    assert box.text() == "Finite elements (FEM), comparison"
    assert not box.isChecked() and box.isEnabled() and "fem" not in win.doc.options.models
    tip = box.toolTip()
    assert "0.4 to 0.9 %" in tip and "no surface" in tip and "steady" in tip.lower() and "0.2 %" not in tip
    assert tip.count(".") <= 8                                           # short: details are in the guide
    assert "fem" in panels.GUARDED_MODELS and "solid3d" in panels.GUARDED_MODELS
    assert "fem" in preferences.MODELS
    assert list(sp.cb)[-1] == "fem"


def test_the_fem_is_never_greyed_for_lack_of_pyamg_and_the_row_says_what_is_missing(win, monkeypatch):
    """!
    @brief Without pyamg a mesh above the direct solver's limit is announced in the panel and in the live checks, and the box stays usable.
    @param win Main window fixture.
    @param monkeypatch pytest fixture.
    """
    monkeypatch.setattr(femcore, "available", lambda: False)
    load(win, example_board())
    win.doc.set_options(models=("fvm", "fem"), cell_mm=2.0)               # 67 229 unknowns: above FEM_DIRECT_MAX
    sp = win.solver_panel
    sp.refresh()
    assert sp.cb["fem"].isEnabled()
    assert "pyamg" in sp.cells_label.text() and "will be left out" in sp.cells_label.text()
    assert sp.run.isEnabled() and not sp.blocked                           # FVM is ticked too: the FEM is left out, not the run
    # a small board needs no pyamg: no extra row
    load(win, small_board())
    win.doc.set_options(models=("fem",), cell_mm=2.0)
    sp.refresh()
    assert "pyamg" not in sp.cells_label.text() and sp.run.isEnabled()


def test_the_panel_shows_the_fem_verdict_and_the_skip_rule(win, monkeypatch):
    """!
    @brief A refused FEM row, 'N unknowns ... above the memory limit'; Run stays enabled next to the FVM and is blocked when the FEM is alone.
    @param win Main window fixture.
    @param monkeypatch pytest fixture.
    """
    monkeypatch.setattr(memory, "ram_bytes", lambda: int(4e9))
    load(win, example_board())
    win.doc.options.memory_fraction = 0.5
    win.doc.set_options(models=("fvm", "fem"), cell_mm=1.0)
    sp = win.solver_panel
    sp.refresh()
    text = sp.cells_label.text()
    assert "FEM:" in text and "275724 unknowns" in text and "above the memory limit, it will not run" in text
    assert sp.run.isEnabled() and not sp.blocked                           # the same rule as the API: only the 3D solid and the FEM may be skipped
    win.doc.set_options(models=("fem",), cell_mm=1.0)
    sp.refresh()
    assert not sp.run.isEnabled() and "FEM" in sp.blocked
    win.doc.set_options(models=("fdm", "fem"), cell_mm=1.0)               # FDM fits at this cell: Run enabled
    sp.refresh()
    assert sp.run.isEnabled()


def test_fem_refusals_do_not_stop_the_other_models(win, qtbot):
    """!
    @brief A slanted outline: the live check says the FEM cannot be built, the row names the mesh reason (not '0 unknowns'), Run stays enabled and the FVM answers.
    @param win Main window fixture.
    @param qtbot pytest-qt fixture.
    """
    p = small_board()
    p.board.outline = np.array([(0, 0), (0.04, 0), (0.04, 0.02), (0.02, 0.03), (0, 0.03)])
    load(win, p)
    win.doc.set_options(models=("fvm", "fem"), cell_mm=2.0)
    sp = win.solver_panel
    sp.refresh()
    assert "0 unknowns" not in sp.cells_label.text() and "FEM:" in sp.cells_label.text() and "left out" in sp.cells_label.text()
    assert sp.run.isEnabled() and not sp.blocked
    run(win, qtbot, ("fvm", "fem"), cell=2.0)
    assert set(win.sim.results) == {"fvm"} and any("FEM was not run" in w or "FEM) was not run" in w for w in win.sim.warnings)
    win.doc.set_options(models=("fem",), cell_mm=2.0)
    sp.refresh()
    assert not sp.run.isEnabled()                                          # alone: nothing else to answer


def test_the_two_fem_options_change_the_count_and_are_greyed_without_the_fem(win):
    """!
    @brief 'FEM gap elements' and 'FEM refinement': written only when edited, greyed unless the FEM is ticked, they change the unknown count.
    @param win Main window fixture.
    """
    load(win, small_board())
    sp = win.solver_panel
    win.doc.set_options(models=("fvm",), cell_mm=2.0, fem_refine=1.25)
    sp.refresh()
    assert not sp.fem_gap.isEnabled() and not sp.fem_ref.isEnabled() and "Greyed" in sp.fem_gap.toolTip()
    sp.cb["fem"].setChecked(True)
    assert sp.fem_gap.isEnabled() and sp.fem_ref.isEnabled()
    assert win.doc.options.fem_refine == 1.25                              # shown rounded, never written back by another edit
    sp.cell.setValue(3.0)
    assert win.doc.options.fem_refine == 1.25
    n6 = [v for v in sp.verdicts() if v.model == "fem"][0].unknowns
    sp.fem_gap.setValue(12)
    assert win.doc.options.fem_gap_elements == 12
    assert [v for v in sp.verdicts() if v.model == "fem"][0].unknowns > n6
    sp.fem_ref.setValue(3.0)
    assert win.doc.options.fem_refine == 3.0
    win.doc.stack.undo()
    assert win.doc.options.fem_refine == 3.0                                # options are not undoable, on purpose
    assert sp.fem_gap.toolTip() and sp.fem_ref.toolTip()


def test_fem_only_and_fem_with_fvm_save_and_reopen(win, tmp_path):
    """!
    @brief The FEM tick, alone or with the FVM, and its two mesh numbers survive save and open; the file is still readable by the v2.7.1 shape (comparison_models).
    @param win Main window fixture.
    @param tmp_path pytest folder.
    """
    load(win, small_board())
    for models in (("fem",), ("fvm", "fem")):
        win.doc.set_options(models=models, cell_mm=2.0, fem_gap_elements=8, fem_refine=1.5)
        path = tmp_path / ("_".join(models) + ".pcbt.json")
        win.doc.save(str(path))
        data = json.loads(path.read_text())
        assert "fem" in json.dumps(data["options"] if "options" in data else data)
        win.doc.set_options(models=("lumped",))
        win.open_file(str(path))
        assert win.doc.options.models == models and win.doc.options.fem_gap_elements == 8 and win.doc.options.fem_refine == 1.5
        assert [k for k, c in win.solver_panel.cb.items() if c.isChecked()] == list(models)
        assert win.solver_panel.fem_gap.value() == 8


def test_the_progress_text_names_the_model_not_its_key(win, qtbot, monkeypatch):
    """!
    @brief 'Solving FEM' and 'Solving 3D solid', never 'Solving fem'; the FEM message says that a large board can take minutes.
    @param win Main window fixture.
    @param qtbot pytest-qt fixture.
    @param monkeypatch pytest fixture.
    """
    from pcbthermal import api
    seen = []
    api.simulate(small_board(), api.SolverOptions(models=("fvm", "fem", "solid3d"), cell_mm=3.0), progress=lambda m, f: seen.append(m))
    assert "Solving FVM" in seen and any(m.startswith("Solving FEM") and "minutes" in m for m in seen) and "Solving 3D solid" in seen
    assert not any(m in ("Solving fem", "Solving solid3d") for m in seen)


@needs_pyamg
def test_a_fem_run_walks_every_results_tab(win, qtbot):
    """!
    @brief FVM with FEM, then FEM alone: the model combos list FEM, the card says FEM, the Layer box has the surface entries, the tables name their read-out, six rows fit.
    @param win Main window fixture.
    @param qtbot pytest-qt fixture.
    """
    load(win, small_board())
    run(win, qtbot, ("fvm", "fem"), cell=2.0)
    rv = win.results
    assert set(win.sim.results) == {"fvm", "fem"}
    rv.tabs.setCurrentWidget(rv.temp)
    assert rv.temp.model.findData("fem") >= 0 and "FEM" in [rv.temp.model.itemText(i) for i in range(rv.temp.model.count())]
    rv.temp.model.setCurrentIndex(rv.temp.model.findData("fem"))
    texts = [win.layer_combo.itemText(i) for i in range(win.layer_combo.count())]
    assert "Surface (top)" in texts and "Surface (bottom)" in texts
    win.layer_combo.setCurrentIndex(win.layer_combo.findData(0))
    qtbot.wait(50)
    assert "column mean" in rv.temp.fig.axes[0].get_title()
    walk_results(win, qtbot)
    # the read-out is named in every table, and the surface column says resolved for the FEM
    assert "(column)" in rv.zone_table.horizontalHeaderItem(2).text() and "(column)" in rv.hot_table.horizontalHeaderItem(2).text()
    # FEM alone: the Results open on it and every tab works (the reference is the FEM itself)
    run(win, qtbot, ("fem",), cell=2.0)
    assert win.sim.reference.model == "fem" and set(win.sim.results) == {"fem"}
    walk_results(win, qtbot)
    # the part table: resolved, with the hottest node in the tooltip
    rv.tabs.setCurrentWidget(rv.components if hasattr(rv, "components") else rv.tabs.currentWidget())
    rv._fill_components()
    head = rv.heater_table.horizontalHeaderItem(rv.heater_table.columnCount() - 1).text()
    assert "resolved" in head and "estimate" not in head
    tip = rv.heater_table.item(0, rv.heater_table.columnCount() - 1).toolTip()
    assert "Resolved by the finite elements" in tip and "Hottest node under the part" in tip
    assert win.sim.reference.arrays["T_point"] is not None


@needs_pyamg
def test_the_fem_surface_entries_and_the_thick_plate(win, qtbot):
    """!
    @brief The plate of Muzychka case 2: the Surface (top) map of the FEM is resolved and hotter than the column by 2 to 5 K; the title and the tooltip say resolved.
    @param win Main window fixture.
    @param qtbot pytest-qt fixture.
    """
    load(win, thick_plate())
    run(win, qtbot, ("fvm", "fem"), cell=2.0)
    rv = win.results
    res = win.sim.results["fem"]
    rv.tabs.setCurrentWidget(rv.temp)
    rv.temp.model.setCurrentIndex(rv.temp.model.findData("fem"))
    win.layer_combo.setCurrentIndex(win.layer_combo.findData(200))
    qtbot.wait(50)
    title = rv.temp.fig.axes[0].get_title()
    assert "resolved" in title and "estimate" not in title
    assert "resolved" in win.layer_combo.itemData(win.layer_combo.findData(200), Qt.ToolTipRole)
    assert np.nanmax(res.arrays["T_surface"][0]) == pytest.approx(res.extras["t_max_surface_top"], abs=1e-9)
    win.layer_combo.setCurrentIndex(win.layer_combo.findData(0))
    qtbot.wait(50)
    assert "column mean" in rv.temp.fig.axes[0].get_title()
    gap = res.extras["t_max_surface_top"] - res.t_max
    assert 2.0 < gap < 5.5                                                  # the plate has a thickness effect that the column read-out hides


@needs_pyamg
def test_fem_cancel_leaves_no_worker(win, qtbot):
    """!
    @brief Stop during a FEM run: the job ends, no result is taken, the next run works.
    @param win Main window fixture.
    @param qtbot pytest-qt fixture.
    """
    load(win, example_board())
    win.doc.set_options(models=("fem",), cell_mm=1.0)
    win.run_simulation()
    assert win.worker is not None and win.worker.isRunning()
    win.solver_panel.run.click()
    qtbot.waitUntil(lambda: not win.worker.isRunning(), timeout=60000)
    assert win.solver_panel.status.text() == "Cancelled."
    run(win, qtbot, ("fvm",), cell=2.0)
    assert win.sim.reference.model == "fvm"


def test_the_card_title_of_the_fem(win):
    """!
    @brief The card of the map on the board names the FEM by its short label, not its key.
    @param win Main window fixture.
    """
    from pcbthermal.gui import fieldscale
    assert fieldscale.MODEL_SHORT["fem"] == "FEM"


def test_the_fem_alone_without_pyamg_on_a_large_mesh_blocks_run(win, monkeypatch, popups):
    """!
    @brief Review of branch 5: alone, a FEM whose mesh needs pyamg would fail the run ('Simulation failed'); the row says it will not run and Run is blocked, while next
           to the FVM it is only left out.
    @param win Main window fixture.
    @param monkeypatch pytest fixture.
    @param popups Recorder of the message boxes.
    """
    monkeypatch.setattr(femcore, "available", lambda: False)
    load(win, example_board())
    sp = win.solver_panel
    win.doc.set_options(models=("fem",), cell_mm=2.0)                    # 67 229 unknowns: above FEM_DIRECT_MAX
    sp.refresh()
    text = sp.cells_label.text()
    assert "pyamg" in text and "will not run" in text and "left out" not in text
    assert not sp.run.isEnabled() and "pyamg" in sp.blocked
    win.run_simulation()                                                   # F5 or the menu: a box with the reason, no job
    assert any(k == "warning" and t == "Cannot run" and "pyamg" in m for k, t, m in popups) and win.worker is None
    win.doc.set_options(models=("fvm", "fem"), cell_mm=2.0)
    sp.refresh()
    assert "will be left out" in sp.cells_label.text() and sp.run.isEnabled() and not sp.blocked


def test_the_tables_name_their_read_out(win):
    """!
    @brief Review of branch 5: every temperature header of the Components and Summary tables names its read-out in the text or in its tooltip (the block table: 'block').
    @param win Main window fixture.
    """
    rv = win.results
    assert "(block)" in rv.block_table.horizontalHeaderItem(2).text() and "(block)" in rv.block_table.horizontalHeaderItem(3).text()
    assert "no surface" in rv.block_table.horizontalHeaderItem(2).toolTip()
    for t, cols in ((rv.zone_table, (2, 3, 4)), (rv.hot_table, (2,))):
        for c in cols:
            assert "Column read-out" in t.horizontalHeaderItem(c).toolTip(), (t, c)
    # The models table: Tmax and Tmean say 'column' in the header text, the surface column says 'surface' (one definition: api.SUMMARY_COLUMNS)
    heads = {rv.model_table.horizontalHeaderItem(c).text().replace("\n", " "): c for c in range(rv.model_table.columnCount())}
    assert "Tmax °C (column)" in heads and "Tmean °C (all layers)" in heads and "ΔT K" in heads


@needs_pyamg
def test_the_thick_plate_warning_of_a_fem_reference_says_resolved():
    """!
    @brief Review of branch 5: with the FEM as the reference (FEM alone), the thick-plate warning quotes the resolved surface, not 'the surface estimate of this
           model', and does not say that the model keeps one temperature through the thickness; with the FVM it keeps its wording.
    """
    from pcbthermal import api
    for models, says, never in ((("fem",), "The surface resolved by the finite elements", "The surface estimate of this model"),
                                (("fvm",), "The surface estimate of this model", "resolved by the finite elements")):
        sim = api.simulate(thick_plate(), api.SolverOptions(models=models, cell_mm=2.0))
        plates = [w for w in sim.warnings if "thick and poorly conducting" in w]
        assert plates, models
        for w in plates:
            assert says in w and never not in w
            assert ("keep one temperature through the thickness" in w) == (models == ("fvm",))
