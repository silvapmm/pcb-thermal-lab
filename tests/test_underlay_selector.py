#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_underlay_selector.py
@brief The Underlay selector (None / Copper / Image) and its opacity pair in the Results maps, the Animation tab and the editor overlay: the entries per project
       type, the pixels of the image underlay (place, scale, flip), the cache, the animation frames and the migration of the stored background opacity.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings
from PySide6.QtGui import QImage

from pcbthermal import analytic, plots
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui.animation import AnimationTab
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow
from pcbthermal.gui.results_view import PlotTab, ResultsView
from pcbthermal.gui.underlay import UnderlayControls
from pcbthermal.model import ImportRecord

RED, GREEN, BLUE, YELLOW = (255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 0, 255)


@pytest.fixture(scope="module")
def sim():
    """!
    @brief One FVM run of the example board (100 x 80 mm) at a 2 mm cell.
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=("fvm",), cell_mm=2.0))


def _quadrants():
    """!
    @brief A 40 x 20 picture with four colours, rows from the top: red and green on top, blue and yellow below.
    @return uint8 array (20, 40, 4).
    """
    a = np.zeros((20, 40, 4), np.uint8)
    a[:10, :20], a[:10, 20:], a[10:, :20], a[10:, 20:] = RED, GREEN, BLUE, YELLOW
    return a


def _png(path, rgba):
    """!
    @brief Write an RGBA array as a PNG file.
    @param path File path.
    @param rgba uint8 array (h, w, 4).
    @return The path as text.
    """
    h, w = rgba.shape[:2]
    img = QImage(np.ascontiguousarray(rgba).data, w, h, 4 * w, QImage.Format_RGBA8888).copy()
    assert img.save(str(path))
    return str(path)


def _map(sim, view):
    """!
    @brief Draw layer 1 of the FVM result with a view and return the axes and the pixels.
    @param sim Simulation.
    @param view plots.MapView.
    @return tuple (axes, uint8 pixel array).
    """
    r = sim.results["fvm"]
    fig = plots.new_figure()
    ax = plots.draw_field(fig, r.T[0], sim.problem, r.dx, r.dy, layer=0, view=view)
    fig.canvas.draw()
    return ax, np.array(fig.canvas.buffer_rgba())


def _px(ax, pix, x_mm, y_mm):
    """!
    @brief The colour of the figure at a point of the board.
    @param ax Axes of the map.
    @param pix Pixel array of the figure.
    @param x_mm X on the board in mm.
    @param y_mm Y on the board in mm (upwards).
    @return RGB tuple.
    """
    x, y = ax.transData.transform((x_mm, y_mm))
    return tuple(int(v) for v in pix[int(round(pix.shape[0] - y)), int(round(x))][:3])


def _near(c, ref, tol=40):
    """!
    @brief Whether a colour is close to a reference.
    @param c RGB tuple.
    @param ref RGBA tuple.
    @param tol Largest difference per channel.
    @return bool.
    """
    return all(abs(a - b) <= tol for a, b in zip(c, ref[:3]))


def test_image_underlay_is_flipped_placed_and_scaled_like_the_editor(sim):
    """!
    @brief With the map invisible (opacity 0) the picture is the image: the top rows of the file are the top of the board, the placement is x, y, w, h of the editor.
    @param sim Simulation fixture.
    """
    b = sim.problem.board
    W, H = b.width * 1000.0, b.height * 1000.0
    full = plots.UnderlayImage(rgba=_quadrants(), x_mm=0.0, y_mm=0.0, w_mm=W, h_mm=H)
    ax, pix = _map(sim, plots.MapView(show_copper=True, underlay="image", image=full, opacity=0.0))
    assert _near(_px(ax, pix, W * 0.25, H * 0.75), RED) and _near(_px(ax, pix, W * 0.75, H * 0.75), GREEN)
    assert _near(_px(ax, pix, W * 0.25, H * 0.25), BLUE) and _near(_px(ax, pix, W * 0.75, H * 0.25), YELLOW)
    # Half the board, from the middle: the left half shows the laminate, the quadrants are half as wide
    half = plots.UnderlayImage(rgba=_quadrants(), x_mm=W / 2.0, y_mm=0.0, w_mm=W / 2.0, h_mm=H)
    ax, pix = _map(sim, plots.MapView(show_copper=True, underlay="image", image=half, opacity=0.0))
    lam = tuple(int(round(v * 255)) for v in plots.MapView().laminate_rgb)
    assert _near(_px(ax, pix, W * 0.25, H * 0.75), lam + (255,), 8)
    assert _near(_px(ax, pix, W * 0.625, H * 0.75), RED) and _near(_px(ax, pix, W * 0.875, H * 0.25), YELLOW)


def test_image_underlay_shows_under_the_map_with_the_opacity(sim):
    """!
    @brief At 70 % the map covers most of the image, at 0 % none of it; the image cache is filled once and reused.
    @param sim Simulation fixture.
    """
    b = sim.problem.board
    img = plots.UnderlayImage(rgba=_quadrants(), x_mm=0.0, y_mm=0.0, w_mm=b.width * 1000.0, h_mm=b.height * 1000.0)
    v0 = plots.MapView(show_copper=True, underlay="image", image=img, opacity=0.0)
    v7 = plots.MapView(show_copper=True, underlay="image", image=img, opacity=0.7, cache=v0.cache)
    _, p0 = _map(sim, v0)
    first = v0.cache["image"]
    _, p7 = _map(sim, v7)
    assert v7.cache["image"] is first                      # One conversion of the picture for any number of redraws
    assert not np.array_equal(p0, p7)


def test_image_without_picture_falls_back_to_the_copper(sim):
    """!
    @brief "image" with no image draws the copper (no failure).
    @param sim Simulation fixture.
    """
    _, a = _map(sim, plots.MapView(show_copper=True))
    _, b = _map(sim, plots.MapView(show_copper=True, underlay="image"))
    assert np.array_equal(a, b)


def test_controls_entries_and_opacity_pair(qtbot):
    """!
    @brief The combo lists None and Copper, Image only with a picture and not for an imported project; the pair is 70 %, linked, enabled with an underlay.
    @param qtbot pytest-qt fixture.
    """
    u = UnderlayControls()
    img = plots.UnderlayImage(rgba=_quadrants(), w_mm=10.0, h_mm=10.0)

    def items():
        return [u.combo.itemData(i) for i in range(u.combo.count())]

    assert items() == ["none", "copper"] and u.kind() == "none" and u.combo.toolTip()
    assert u.opacity.value() == u.opacity_spin.value() == 70 and u.opacity_spin.suffix() == " %" and u.opacity.toolTip() and u.opacity_spin.toolTip()
    assert not u.opacity.isEnabled() and not u.opacity_spin.isEnabled()
    u.set_source(False, {"path": "x"}, image=img)
    assert items() == ["none", "copper", "image"]
    u.combo.setCurrentIndex(2)
    assert u.kind() == "image" and u.opacity.isEnabled()
    u.opacity_spin.setValue(25)
    assert u.opacity.value() == 25 and u.value() == 0.25
    u.opacity.setValue(90)
    assert u.opacity_spin.value() == 90
    u.set_source(True, {"path": "x"}, image=img)           # An imported project: Copper only, and the choice that vanished goes back to None
    assert items() == ["none", "copper"] and u.kind() == "none"


def _win(qtbot, tmp_path):
    """!
    @brief A main window on a private settings file.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return MainWindow.
    """
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    return win


def _entries(u):
    """!
    @brief The data of the entries of a combo.
    @param u UnderlayControls.
    @return List.
    """
    return [u.combo.itemData(i) for i in range(u.combo.count())]


def test_entries_per_project_type_and_migration_of_the_stored_opacity(qtbot, tmp_path):
    """!
    @brief Hand-drawn: Copper, and Image once a background is set; its stored opacity becomes the initial opacity of the maps; Gerber: Copper only, also with an old image.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    win = _win(qtbot, tmp_path)
    r = win.results
    assert _entries(r.temp.underlay) == _entries(r.grad.underlay) == _entries(r.animation.underlay) == ["none", "copper"]
    assert _entries(win.editor_underlay) == ["none", "copper"]
    cfg = {"path": _png(tmp_path / "bg.png", _quadrants()), "x_mm": 0.0, "y_mm": 0.0, "w_mm": 50.0, "h_mm": 40.0, "opacity": 0.25}
    win.doc.project.view["background"] = cfg
    win.doc.changed.emit()
    for u in (r.temp.underlay, r.grad.underlay, r.animation.underlay, win.editor_underlay):
        assert _entries(u) == ["none", "copper", "image"]
    assert r.temp.underlay.opacity.value() == r.grad.underlay.opacity.value() == r.animation.underlay.opacity.value() == 25
    assert win.overlay_opacity.value() == 25
    r.temp.underlay.opacity.setValue(60)                    # A later choice of the user is not taken back
    win.doc.changed.emit()
    assert r.temp.underlay.opacity.value() == 60
    win.doc.project.imports = [ImportRecord(name="b")]
    win.doc.changed.emit()
    for u in (r.temp.underlay, r.animation.underlay, win.editor_underlay):
        assert _entries(u) == ["none", "copper"]
    assert win.doc.project.view["background"]["path"] == cfg["path"]      # Kept in the file, only not offered


def test_two_maps_share_the_underlay_and_the_editor_follows(qtbot, tmp_path, sim):
    """!
    @brief Choosing the underlay on the Temperature tab sets it on the Gradients tab and in the editor, and the editor hides the image unless Image is chosen.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation fixture.
    """
    win = _win(qtbot, tmp_path)
    win.doc.project.view["background"] = {"path": _png(tmp_path / "bg.png", _quadrants()), "x_mm": 0.0, "y_mm": 0.0, "w_mm": 50.0, "h_mm": 40.0}
    win.doc.changed.emit()
    win.results.set_simulation(sim)
    r = win.results
    r.temp.underlay.combo.setCurrentIndex(2)
    assert r.grad.underlay.kind() == "image" and win.editor_underlay.kind() == "image"
    win.canvas.rebuild()
    assert win.canvas._background is not None and win.canvas._background.isVisible()
    win._editor_apply_underlay(True)
    assert win.canvas._background.isVisible()                # Image: shown under the map
    win.editor_underlay.combo.setCurrentIndex(1)
    assert r.temp.underlay.kind() == "copper"
    win._editor_apply_underlay(True)
    assert not win.canvas._background.isVisible()
    win._editor_apply_underlay(False)
    assert win.canvas._background.isVisible()                # No map: the image is back


def test_animation_underlay_view_and_export(qtbot, tmp_path):
    """!
    @brief The Animation tab has the View combo (no Terrain) and the Underlay pair; None draws the old frame, Copper changes it, the exported GIF includes it.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    """
    p = example_board()
    tab = AnimationTab()
    qtbot.addWidget(tab)
    tr = analytic.solve_transient(p, t_end=30.0, n_out=4, cell_mm=2.0, n_terms=40)
    tab.set_result(tr, p)
    assert [tab.view.itemData(i) for i in range(tab.view.count())] == ["current", "smooth"] and tab.view.toolTip()
    assert _entries(tab.underlay) == ["none", "copper"] and tab.underlay.opacity.value() == 70
    assert tab.map_view() is None                            # The defaults draw the original frame, call for call

    def frame():
        tab.canvas.draw()
        return np.array(tab.canvas.buffer_rgba())

    base = frame()
    tab.underlay.combo.setCurrentIndex(1)
    withcu = frame()
    assert not np.array_equal(base, withcu)
    assert 0 in tab.underlay.cache                           # Cached once for the whole animation
    first = tab.underlay.cache[0]
    tab.slider.setValue(0)
    frame()
    assert tab.underlay.cache[0] is first
    tab.underlay.opacity.setValue(10)
    assert not np.array_equal(withcu, frame())
    tab.slider.setValue(tab.slider.maximum())
    tab.underlay.combo.setCurrentIndex(0)
    assert np.array_equal(base, frame())                     # Back to None: the same pixels as the start
    # The export carries the underlay: a GIF with it differs from one without
    tab.underlay.combo.setCurrentIndex(1)
    a, b = tmp_path / "a.gif", tmp_path / "b.gif"
    plots.save_transient_gif(tr, p, str(a), fps=5, view=tab.map_view())
    plots.save_transient_gif(tr, p, str(b), fps=5)
    assert a.stat().st_size > 1000 and a.read_bytes() != b.read_bytes()


def test_results_tab_has_the_combo_in_place_of_the_checkbox(qtbot, sim):
    """!
    @brief The temperature tab has the Underlay combo with a tooltip and no Show copper checkbox; None is the default; the Animation tab has one too.
    @param qtbot pytest-qt fixture.
    @param sim Simulation fixture.
    """
    t = PlotTab("temperature", "dark")
    qtbot.addWidget(t)
    t.set_simulation(sim)
    assert not hasattr(t, "copper") and t.underlay.kind() == "none" and t.underlay.combo.toolTip()
    assert t.map_view().show_copper is False
    rv = ResultsView("dark")
    qtbot.addWidget(rv)
    assert hasattr(rv.animation, "underlay")
