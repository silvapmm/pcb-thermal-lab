#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_canvas_overlay.py
@brief The temperature overlay of the editor canvas (opacity, the Results colour scale, cells off the outline, colour bar, outdated and stretched maps, active layer) and the
       4096-pixel cap of the imported copper pixmap (CO60 at 2850 x 951, RP2040 unchanged).
"""

import copy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time

import numpy as np
import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings
from PySide6.QtGui import QImage

from pcbthermal import plots
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui import fieldscale
from pcbthermal.gui import import_session as ims
from pcbthermal.gui.canvas import COPPER_DISPLAY_PIXELS, BoardView
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow

REAL = os.environ.get("PCBT_REAL_BOARDS", "")


def _t_problem():
    """!
    @brief The example board cut to a T-shaped outline, one heater.
    @return Problem with an outline.
    """
    p = example_board()
    W, H = p.board.width, p.board.height
    p.board.outline = np.array([[0, 0], [W, 0], [W, 0.45 * H], [0.65 * W, 0.45 * H], [0.65 * W, H], [0.35 * W, H], [0.35 * W, 0.45 * H], [0, 0.45 * H]], dtype=float)
    p.heaters = p.heaters[:1]
    p.heaters[0].polygon = np.array([[0.4 * W, 0.6 * H], [0.55 * W, 0.6 * H], [0.55 * W, 0.8 * H], [0.4 * W, 0.8 * H]])
    p.vias = []
    return p


@pytest.fixture(scope="module")
def sim_t():
    """!
    @brief One run of the FVM and the Lumped model on the T board (2 mm cell).
    @return Simulation.
    """
    return simulate(_t_problem(), SolverOptions(models=("fvm", "lumped"), cell_mm=2.0))


@pytest.fixture(scope="module")
def sim_rect():
    """!
    @brief One run of the FVM on the example board (2 mm cell).
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=("fvm",), cell_mm=2.0))


def _window(qtbot, tmp_path, sim, problem):
    """!
    @brief A main window that holds a problem and its simulation.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation.
    @param problem Problem the simulation was made from.
    @return MainWindow
    """
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win._load_problem(copy.deepcopy(problem), "t")              # a copy: an edit in one test must not change the module fixtures of the next
    win.results.set_simulation(sim)
    win.sim, win._stale = sim, False
    win._update_map_button()
    return win


def _rgba(img):
    """!
    @brief A QImage as an RGBA array.
    @param img QImage.
    @return uint8 array (rows, columns, 4).
    """
    img = img.convertToFormat(QImage.Format_RGBA8888)
    return np.frombuffer(img.constBits(), np.uint8).reshape(img.height(), img.bytesPerLine() // 4, 4)[:, :img.width()].copy()


def test_colour_limits_follow_the_results_rule():
    f = np.array([[1.0, 5.0], [np.nan, 3.0]])
    assert fieldscale.colour_limits(f) == (1.0, 5.0)
    assert fieldscale.colour_limits(f, False, 0.0, 10.0) == (0.0, 10.0)
    lo, hi = fieldscale.colour_limits(np.full((2, 2), 4.0))
    assert hi > lo


def test_opacity_changes_the_painted_pixels_and_the_default_is_70_percent(qtbot, tmp_path, sim_rect):
    win = _window(qtbot, tmp_path, sim_rect, sim_rect.problem)
    pop = win.display_popover
    assert win.display.opacity == 70 and pop.opacity.toolTip() and not win.a_overlay.isChecked()          # the map is off by default
    win.a_overlay.setChecked(True)
    assert abs(win.canvas._overlay.opacity() - 0.7) < 1e-9
    win.canvas.resize(500, 400)
    win.canvas.show()
    win.canvas.fit()
    shots = []
    for v in (100, 30):
        pop.opacity.setValue(v)
        pop.flush()
        shots.append(_rgba(win.canvas.viewport().grab().toImage()))
    assert not np.array_equal(shots[0], shots[1])            # a lower opacity paints other pixels
    assert abs(win.canvas._overlay.opacity() - 0.3) < 1e-9


def test_cells_off_the_outline_are_transparent(qtbot, tmp_path, sim_t):
    win = _window(qtbot, tmp_path, sim_t, sim_t.problem)
    win.results.temp.model.setCurrentIndex(win.results.temp.model.findData("fvm"))
    win.a_overlay.setChecked(True)
    assert win.canvas._overlay is not None
    px = _rgba(win.canvas._overlay.pixmap().toImage())
    ref = sim_t.results["fvm"]
    mask = fieldscale.inside_mask(sim_t.problem, ref.T[0].shape, ref.dx, ref.dy)
    assert not mask.all() and mask.any()
    assert (px[..., 3][~mask] == 0).all() and (px[..., 3][mask] == 255).all()


def test_the_scale_is_the_one_of_the_results_view(qtbot, tmp_path, sim_rect):
    win = _window(qtbot, tmp_path, sim_rect, sim_rect.problem)
    t = win.results.temp
    t.auto.setChecked(False)
    t.vmin.setValue(30.0)
    t.vmax.setValue(60.0)
    win.a_overlay.setChecked(True)
    a = win.canvas._overlay_args
    assert (a["vmin"], a["vmax"]) == (30.0, 60.0) and a["cmap"] == win.display.cmap and a["unit"] == "°C"
    t.auto.setChecked(True)
    win.a_overlay.setChecked(False)
    win.a_overlay.setChecked(True)
    f = sim_rect.reference.T[0]
    assert win.canvas._overlay_args["vmax"] == pytest.approx(float(np.nanmax(f)))


def test_the_colour_bar_is_painted_only_with_the_overlay(qtbot, tmp_path, sim_rect):
    win = _window(qtbot, tmp_path, sim_rect, sim_rect.problem)
    win.canvas.resize(500, 400)
    win.canvas.show()
    win.canvas.fit()
    off = _rgba(win.canvas.viewport().grab().toImage())
    win.a_overlay.setChecked(True)
    win.canvas.set_overlay_opacity(0.1)                      # the board nearly clear: the difference at the corner is the bar
    on = _rgba(win.canvas.viewport().grab().toImage())
    h, w = off.shape[:2]
    bx, by, bw, bh, _ = win.canvas.colourbar_geometry()      # The bar is wherever it fits without covering the board
    corner = (slice(int(by), int(by + bh)), slice(int(bx), int(bx + bw)))
    assert not np.array_equal(off[corner], on[corner])


def test_auto_limits_on_an_outline_board_are_those_of_the_results_map(qtbot, tmp_path, sim_t):
    # Review: the cells off the outline sit at the ambient, and the overlay took them into its Auto range (25.0 against the tab's 35.1 degC on this T)
    from pcbthermal.plots import _off_board

    win = _window(qtbot, tmp_path, sim_t, sim_t.problem)
    t = win.results.temp
    t.model.setCurrentIndex(t.model.findData("fvm"))
    win.a_overlay.setChecked(True)
    r = sim_t.results["fvm"]
    on = _off_board(r.T[0], sim_t.problem, r.dx, r.dy)
    a = win.canvas._overlay_args
    assert a["vmin"] == pytest.approx(float(np.nanmin(on))) and a["vmax"] == pytest.approx(float(np.nanmax(on)))
    assert a["vmin"] > float(np.nanmin(r.T[0])) + 1.0                    # the off-board ambient is not the lower limit


def test_the_overlay_follows_the_controls_of_the_temperature_tab(qtbot, tmp_path, sim_t):
    # Review: the overlay kept the colour map and limits of the moment it was switched on
    win = _window(qtbot, tmp_path, sim_t, sim_t.problem)
    t = win.results.temp
    t.model.setCurrentIndex(t.model.findData("fvm"))
    win.a_overlay.setChecked(True)
    other = [c for c in plots.CMAPS if c != win.display.cmap][0]
    win.display.set_cmap(other)                                          # the colour map is the shared display choice
    assert win.canvas._overlay_args["cmap"] == other
    t.auto.setChecked(False)
    t.vmin.setValue(40.0)
    t.vmax.setValue(90.0)
    assert (win.canvas._overlay_args["vmin"], win.canvas._overlay_args["vmax"]) == (40.0, 90.0)
    t.model.setCurrentIndex(t.model.findData("lumped"))                 # the stretched map of the outline board: refused at once
    assert win.canvas._overlay is None and "stretched" in win.statusBar().currentMessage()
    assert win.canvas._overlay_card["tmax"] is None and "Lumped" in win.canvas._overlay_card["title"]          # only the card says so


def test_switching_on_an_outdated_result_says_so_and_leaves_the_button_off(qtbot, tmp_path, sim_rect):
    win = _window(qtbot, tmp_path, sim_rect, sim_rect.problem)
    win.doc.set_props("heater", 0, power=3.0)
    win.a_overlay.setChecked(True)
    assert win.canvas._overlay is None and not win.a_overlay.isChecked()
    assert not win.a_overlay.isEnabled() and "outdated" in win.a_overlay.toolTip()
    assert "outdated" in win.statusBar().currentMessage()


def test_an_edit_hides_the_overlay(qtbot, tmp_path, sim_rect):
    win = _window(qtbot, tmp_path, sim_rect, sim_rect.problem)
    win.a_overlay.setChecked(True)
    assert win.canvas._overlay is not None
    win.doc.set_props("heater", 0, power=3.0)
    assert win.canvas._overlay is None and not win.a_overlay.isChecked() and not win.a_overlay.isEnabled()
    win.a_overlay.setChecked(True)                           # still outdated: refused
    assert win.canvas._overlay is None


def test_a_stretched_map_on_an_outline_board_is_refused_with_a_note(qtbot, tmp_path, sim_t):
    win = _window(qtbot, tmp_path, sim_t, sim_t.problem)
    t = win.results.temp
    t.model.setCurrentIndex(t.model.findData("lumped"))
    assert sim_t.results["lumped"].equivalent_scale is not None
    win.a_overlay.setChecked(True)
    assert win.canvas._overlay is None and "stretched" in win.statusBar().currentMessage()
    assert win.canvas._overlay_card["tmax"] is None and win.canvas._overlay_card["title"].startswith("Lumped: not drawn")
    t.model.setCurrentIndex(t.model.findData("fvm"))
    win.a_overlay.setChecked(True)
    assert win.canvas._overlay is not None


def test_the_overlay_follows_the_active_layer_and_survives_a_rebuild(qtbot, tmp_path, sim_rect):
    win = _window(qtbot, tmp_path, sim_rect, sim_rect.problem)
    win.a_overlay.setChecked(True)
    top = win.canvas._overlay_args["field"]
    n = sim_rect.reference.T.shape[0]
    win.layer_combo.setCurrentIndex(n - 1)
    assert win.canvas._overlay is not None
    assert np.array_equal(win.canvas._overlay_args["field"], sim_rect.reference.T[n - 1])
    assert not np.array_equal(top, win.canvas._overlay_args["field"])
    win.canvas.rebuild()                                     # selection and theme changes rebuild the scene
    assert win.canvas._overlay is not None


# ------------------------------------------------------------------------------------------------------------------------------------ the copper cap
def test_the_copper_cap_is_4096():
    assert COPPER_DISPLAY_PIXELS == 4096


def _doc_of(key):
    """!
    @brief A Document with the library board imported at the automatic pixel.
    @param key Folder name under PCBT_REAL_BOARDS.
    @return Document
    """
    sx = ims.ImportSession()
    sx.set_files(os.path.join(REAL, key))
    sx.load()
    doc = Document()
    doc.open_import(sx.build_problem(), sx.record)
    return doc


@pytest.mark.skipif(not REAL or not os.path.isdir(os.path.join(REAL, "co60")), reason="PCBT_REAL_BOARDS does not point to the real boards")
def test_co60_is_drawn_whole_at_4096(qtbot):
    doc = _doc_of("co60")
    t0 = time.perf_counter()
    view = BoardView(doc, "dark")
    qtbot.addWidget(view)
    spent = time.perf_counter() - t0
    pm = view._copper_item.pixmap()
    assert (pm.width(), pm.height()) == (2850, 951), (pm.width(), pm.height())
    assert spent < 1.0, spent


@pytest.mark.skipif(not REAL or not os.path.isdir(os.path.join(REAL, "rp2040")), reason="PCBT_REAL_BOARDS does not point to the real boards")
def test_rp2040_is_unchanged_by_the_cap(qtbot):
    doc = _doc_of("rp2040")
    mask = doc.problem.imported.layers[0]["mask"]
    view = BoardView(doc, "dark")
    qtbot.addWidget(view)
    pm = view._copper_item.pixmap()
    assert (pm.height(), pm.width()) == tuple(mask["shape"])        # factor 1, as before


def test_the_opacity_box_and_the_slider_follow_each_other(qtbot, tmp_path, sim_rect):
    win = _window(qtbot, tmp_path, sim_rect, sim_rect.problem)
    pop = win.display_popover
    pop.set_context("editor")
    assert pop.opacity_spin.value() == 70 and pop.opacity_spin.suffix() == " %" and pop.opacity_spin.toolTip()
    assert pop.opacity_spin.isEnabled()                      # on the board the opacity matters also without an underlay
    win.a_overlay.setChecked(True)
    pop.opacity_spin.setValue(25)
    pop.flush()
    assert pop.opacity.value() == 25 and abs(win.canvas._overlay.opacity() - 0.25) < 1e-9
    pop.opacity.setValue(90)
    pop.flush()
    assert pop.opacity_spin.value() == 90 and abs(win.canvas._overlay.opacity() - 0.9) < 1e-9
    pop.opacity_spin.setValue(0)
    pop.flush()
    assert win.canvas._overlay.opacity() == 0.0


def _round_problem():
    """!
    @brief The example board cut to a disc-like outline (48 vertices), one heater, so that many cells are cut by the outline but have their centre off it.
    @return Problem with a rounded outline.
    """
    p = example_board()
    W, H = p.board.width, p.board.height
    a = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    p.board.outline = np.column_stack([0.5 * W + 0.5 * W * np.cos(a), 0.5 * H + 0.5 * H * np.sin(a)])
    p.heaters = p.heaters[:1]
    p.heaters[0].polygon = np.array([[0.45 * W, 0.45 * H], [0.55 * W, 0.45 * H], [0.55 * W, 0.55 * H], [0.45 * W, 0.55 * H]])
    p.vias = []
    return p


def test_overlay_and_results_leave_the_same_cells_blank(qtbot, tmp_path):
    """!
    @brief Cells cut by a rounded corner whose centre is off the board are blank in the Results map; the overlay now blanks the same cells.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    from pcbthermal import plots
    from pcbthermal.geometry import coverage_fraction

    sim = simulate(_round_problem(), SolverOptions(models=("fvm",), cell_mm=2.0))
    ref = sim.results["fvm"]
    win = _window(qtbot, tmp_path, sim, sim.problem)
    win.results.temp.model.setCurrentIndex(win.results.temp.model.findData("fvm"))
    win.a_overlay.setChecked(True)
    alpha = _rgba(win.canvas._overlay.pixmap().toImage())[..., 3] > 0
    results = np.isfinite(plots._off_board(ref.T[0], sim.problem, ref.dx, ref.dy))
    assert np.array_equal(alpha, results)
    ny, nx = ref.T[0].shape
    old_rule = np.asarray(coverage_fraction(sim.problem.board.outline, nx, ny, ref.dx, ref.dy, 8)) > 0.0
    assert (old_rule & ~results).any()                      # The case is real: the coverage rule painted cells that the tab leaves blank


def test_colour_bar_ticks_are_round_and_short():
    """!
    @brief The tick values are multiples of 1, 2 or 5 times a power of ten and their text has at most one decimal for steps of 0.1 and more.
    """
    for lo, hi in ((35.1111, 184.743), (25.0, 25.5), (0.0, 7.3), (-12.0, 4.0)):
        vals, step = fieldscale.nice_ticks(lo, hi, 4)
        assert 2 <= len(vals) <= 8 and all(lo - 1e-9 <= v <= hi + 1e-9 for v in vals)
        assert step / 10 ** np.floor(np.log10(step)) in (1.0, 2.0, 5.0) or abs(step / 10 ** np.floor(np.log10(step)) - 10) < 1e-9
        for v in vals:
            t = fieldscale.tick_label(v, step)
            assert float(t) == pytest.approx(v, abs=step / 100)
            if step >= 0.1:
                assert len(t.split(".")[1]) <= 1 if "." in t else True
    vals, step = fieldscale.nice_ticks(35.1111, 184.743, 4)
    assert [fieldscale.tick_label(v, step) for v in vals] == ["50", "100", "150"]


def test_colour_bar_never_covers_the_board_at_fit_zoom(qtbot, tmp_path, sim_rect):
    """!
    @brief At fit-to-window zoom, in a wide and a narrow window, the bar box does not meet the board rectangle or the scale bar, and the drawn labels are the round ticks.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim_rect Simulation of the example board.
    """
    win = _window(qtbot, tmp_path, sim_rect, sim_rect.problem)
    win.a_overlay.setChecked(True)
    win.canvas.show()
    for size in ((700, 500), (360, 420), (900, 260)):
        win.canvas.resize(*size)
        qtbot.wait(100)                                     # Let the layout settle before fitting
        win.canvas.fit()
        win.canvas.viewport().grab()                        # Paints once, which fills the label list
        x, y, w, h, covers = win.canvas.colourbar_geometry()
        bx, by, bw, bh = win.canvas._board_pixel_rect()
        sx, sy, sw, sh = win.canvas._scale_bar_rect()

        def meet(a, b):
            return min(a[0] + a[2], b[0] + b[2]) > max(a[0], b[0]) and min(a[1] + a[3], b[1] + b[3]) > max(a[1], b[1])

        assert not covers and not meet((x, y, w, h), (bx, by, bw, bh)), (size, win.canvas.viewport().width(), win.canvas.viewport().height(), (x, y, w, h), (bx, by, bw, bh))
        assert not meet((x, y, w, h), (sx, sy, sw, sh)), size
        assert x >= 0 and y >= 0 and x + w <= win.canvas.viewport().width() + 1 and y + h <= win.canvas.viewport().height() + 1
        for t in win.canvas._colourbar_labels:
            assert len(t) <= 6 and ("." not in t or len(t.split(".")[1]) <= 2)
