#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_results_views.py
@brief The View modes of the Results maps (Current, Smooth, Terrain), the Show copper box, the Opacity and Contour controls and the 2 x 2 layer grid.
"""

import hashlib
import time

import matplotlib
import numpy as np
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from pcbthermal import analysis, plots
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui import theme as th
from pcbthermal.gui.results_view import PlotTab, ResultsView

# sha256 of the RGBA buffer of the maps that `develop` (v2.5.0 plus the fixes before this feature) draws for the example board at a 2 mm cell; they hold
# the Current view to the old pictures, byte for byte. Pixel output depends on the Matplotlib version, so the check runs only on the one that made them.
BASELINE_MPL = "3.11.2"
BASELINE = {
    "field": "f8df8cc4336659a1c70df3b8d987e4b725349adc31ba654eb1718781efed1ead",
    "fields": "beeecfc3a81eb77f9a974bdc33da7d37b534766b0d7e2fb0f0b8522b14596b93",
    "gradient": "b6a9fa153874ae40079e6db31c2c47300326b267b0f834d680eac7a6ea1f5e38",
}


@pytest.fixture(scope="module")
def sim():
    """!
    @brief One FVM run of the example board at a 2 mm cell.
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=("fvm",), cell_mm=2.0))


@pytest.fixture(scope="module")
def sim1():
    """!
    @brief One FVM run of the example board (100 x 80 mm) at a 1 mm cell, for the timing.
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=("fvm",), cell_mm=1.0))


def _rgba(fig):
    """!
    @brief The rendered pixels of a figure.
    @param fig Figure with an Agg canvas.
    @return uint8 array (h, w, 4).
    """
    fig.canvas.draw()
    return np.array(fig.canvas.buffer_rgba())


def _field(sim, view=None, layer=0, **kw):
    """!
    @brief Draw layer `layer` of the FVM result with a view.
    @param sim Simulation.
    @param view MapView or None.
    @param layer 0-based layer.
    @param kw Extra draw_field arguments.
    @return uint8 pixel array.
    """
    r = sim.results["fvm"]
    fig = plots.new_figure()
    plots.draw_field(fig, r.T[layer], sim.problem, r.dx, r.dy, layer=layer, view=view, **kw)
    return _rgba(fig)


def _sha(a):
    """!
    @brief Hash of a pixel array.
    @param a numpy array.
    @return Hex digest.
    """
    return hashlib.sha256(a.tobytes()).hexdigest()


@pytest.mark.skipif(matplotlib.__version__ != BASELINE_MPL, reason="the baseline pictures were made with another Matplotlib")
def test_current_view_is_byte_identical_to_develop(sim):
    """!
    @brief Without a view, and with a MapView that is Current with no copper, the pictures are those of develop.
    @param sim Simulation fixture.
    """
    r = sim.results["fvm"]
    for view in (None, plots.MapView()):
        assert _sha(_field(sim, view, hotspot=100.0, title="t")) == BASELINE["field"]
        fig = plots.new_figure()
        plots.draw_fields(fig, r, sim.problem, view=view)
        assert _sha(_rgba(fig)) == BASELINE["fields"]
        fig = plots.new_figure()
        plots.draw_field(fig, analysis.gradient_magnitude(r)[0], sim.problem, r.dx, r.dy, layer=0, label="g", view=view)
        assert _sha(_rgba(fig)) == BASELINE["gradient"]
    assert _sha(_field(sim, None, hotspot=100.0, title="t")) == BASELINE["field"]


def test_every_mode_changes_the_pixels_and_keeps_the_colour_scale(sim):
    """!
    @brief Smooth, Terrain and the copper box differ from Current; the colour bar limits are those of the data in every view.
    @param sim Simulation fixture.
    """
    base = _field(sim, plots.MapView())
    seen = {_sha(base)}
    for mode in ("smooth", "terrain"):
        for cu in (False, True):
            px = _field(sim, plots.MapView(mode=mode, show_copper=cu))
            assert _sha(px) not in seen, (mode, cu)
            seen.add(_sha(px))
    px = _field(sim, plots.MapView(show_copper=True))
    assert _sha(px) not in seen
    r = sim.results["fvm"]
    for mode in plots.VIEW_MODES:
        fig = plots.new_figure()
        ax = plots.draw_field(fig, r.T[0], sim.problem, r.dx, r.dy, view=plots.MapView(mode=mode), vmin=40.0, vmax=90.0)
        cb = fig.axes[-1]
        assert cb.get_ylim() == pytest.approx((40.0, 90.0))
        assert ax is not None


def test_smooth_is_bicubic_and_does_not_touch_the_data(sim):
    """!
    @brief The Smooth image is the same array with a bicubic interpolation.
    @param sim Simulation fixture.
    """
    r = sim.results["fvm"]
    fig = plots.new_figure()
    ax = plots.draw_field(fig, r.T[0], sim.problem, r.dx, r.dy, view=plots.MapView(mode="smooth"))
    im = ax.get_images()[0]
    assert im.get_interpolation() == "bicubic"
    assert np.array_equal(np.asarray(im.get_array()), r.T[0])


def test_terrain_draws_labelled_contours_every_step(sim):
    """!
    @brief Terrain draws contour lines at multiples of the step (and thicker, labelled ones at multiples of twice the step); a larger step draws fewer.
    @param sim Simulation fixture.
    """
    r = sim.results["fvm"]

    def levels(step):
        fig = plots.new_figure()
        ax = plots.draw_field(fig, r.T[0], sim.problem, r.dx, r.dy, view=plots.MapView(mode="terrain", contour_step=step))
        return sorted({round(float(lv), 6) for c in ax.collections if hasattr(c, "levels") for lv in c.levels})

    five, ten = levels(5.0), levels(10.0)
    assert five and all(abs(v / 5.0 - round(v / 5.0)) < 1e-9 for v in five)
    assert len(ten) < len(five) and all(abs(v / 10.0 - round(v / 10.0)) < 1e-9 for v in ten)


def test_gradient_field_picks_a_round_contour_step(sim):
    """!
    @brief A step of zero (the gradient tab) gives a round step in the unit of the field, not a multiple of 5.
    @param sim Simulation fixture.
    """
    r = sim.results["fvm"]
    g = analysis.gradient_magnitude(r)[0]
    fig = plots.new_figure()
    ax = plots.draw_field(fig, g, sim.problem, r.dx, r.dy, view=plots.MapView(mode="terrain", contour_step=0.0))
    assert any(len(c.levels) for c in ax.collections if hasattr(c, "levels"))
    assert plots._nice_step(7.3) in (1.0, 2.0) and plots._nice_step(0.0) == 1.0


def test_copper_box_shows_the_copper_under_the_field_and_opacity_matters(sim):
    """!
    @brief With the copper under the field, a lower opacity lets more of the copper through (the picture moves towards the copper grey).
    @param sim Simulation fixture.
    """
    cache = {}
    lo = _field(sim, plots.MapView(show_copper=True, opacity=0.2, cache=cache)).astype(float)
    hi = _field(sim, plots.MapView(show_copper=True, opacity=1.0, cache=cache)).astype(float)
    plain = _field(sim, plots.MapView()).astype(float)
    assert np.abs(hi - plain).mean() < 0.5 * np.abs(lo - plain).mean() + 1e-9       # opacity 1 is the plain map again, at least in the field area
    assert 0 in cache                                                              # The picture of the layer is cached
    n = len(cache)
    _field(sim, plots.MapView(show_copper=True, cache=cache))
    assert len(cache) == n                                                         # A second draw reuses it


def test_copper_image_from_zones_and_from_an_imported_mask(sim):
    """!
    @brief The zones give 1 inside and 0 outside; an imported mask of the layer replaces them (rows flipped to start at the bottom).
    @param sim Simulation fixture.
    """
    p = sim.problem
    z = plots.copper_image(p, 0)
    assert z.shape[0] > 10 and 0.0 <= z.min() and z.max() <= 1.0 and z.max() == 1.0 and z.min() == 0.0
    zone = next(zz for zz in p.zones if zz.layer == 0)
    cx, cy = zone.polygon.mean(axis=0)
    b = p.board
    assert z[int(cy / b.height * z.shape[0]), int(cx / b.width * z.shape[1])] == pytest.approx(1.0)
    from pcbthermal import copper

    q = example_board()
    mask = np.zeros((80, 100), np.uint8)
    mask[:10, :] = 255                                                             # The top 10 rows of the raster (top of the board)
    q.imported = copper.imported_from_rasters([mask], 1.0)
    img = plots.copper_image(q, 0)
    assert img.shape == (80, 100) and img[-1].min() == pytest.approx(1.0) and img[0].max() == 0.0


def test_solved_rectangle_has_no_copper_and_says_so():
    """!
    @brief A Lumped result on an outline board drawn as solved shows a note instead of the copper.
    """
    p = example_board()
    W, H = p.board.width, p.board.height
    p.board.outline = np.array([[0, 0], [W, 0], [W, 0.45 * H], [0.65 * W, 0.45 * H], [0.65 * W, H], [0.35 * W, H], [0.35 * W, 0.45 * H], [0, 0.45 * H]], dtype=float)
    p.heaters = p.heaters[:1]
    p.heaters[0].polygon = np.array([[0.4 * W, 0.6 * H], [0.55 * W, 0.6 * H], [0.55 * W, 0.8 * H], [0.4 * W, 0.8 * H]])
    p.vias = []
    s = simulate(p, SolverOptions(models=("lumped",), cell_mm=2.0))
    r = s.results["lumped"]
    view = plots.MapView(show_copper=True)
    fig = plots.new_figure()
    ax = plots.draw_field(fig, r.T[0], p, r.dx, r.dy, equivalent_scale=r.equivalent_scale, view=view)
    assert any("copper not drawn" in t.get_text() for t in ax.texts)
    assert view.cache == {}
    fig = plots.new_figure()
    ax = plots.draw_field(fig, r.T[0], p, r.dx, r.dy, equivalent_scale=None, view=view)         # Stretched on the real box: the copper is drawn
    assert not any("copper not drawn" in t.get_text() for t in ax.texts) and 0 in view.cache
    _rgba(fig)


def test_grid_layout_has_one_axis_per_layer_in_two_columns(sim):
    """!
    @brief The 2 x 2 layout puts the four layers in a grid; an odd count hides the empty cell.
    @param sim Simulation fixture.
    """
    r = sim.results["fvm"]
    fig = plots.new_figure()
    plots.draw_fields(fig, r, sim.problem, grid=True)
    shown = [a for a in fig.axes if a.get_visible() and a.get_images()]
    assert len(shown) == 4
    xs = sorted({round(a.get_position().x0, 2) for a in shown})
    ys = sorted({round(a.get_position().y0, 2) for a in shown})
    assert len(xs) == 2 and len(ys) == 2


@pytest.fixture
def tab(sim):
    """!
    @brief A temperature tab showing the simulation.
    @param sim Simulation fixture.
    @return PlotTab.
    """
    QApplication.instance() or QApplication([])
    t = PlotTab("temperature", "dark")
    t.set_simulation(sim)
    return t


def test_controls_default_to_the_old_picture_and_follow_the_view(tab):
    """!
    @brief The defaults are Current with no copper; the opacity is enabled only with the copper box and the contour step only for Terrain.
    @param tab PlotTab fixture.
    """
    assert tab.view.currentData() == "current" and not (tab.underlay.kind() == "copper")
    assert [tab.view.itemData(i) for i in range(tab.view.count())] == ["current", "smooth", "terrain"]
    assert tab.opacity.value() == 70 and tab.contour.value() == 5.0
    assert not tab.opacity.isEnabled() and tab.contour.isHidden() and tab.contour_label.isHidden()
    tab.underlay.combo.setCurrentIndex(1)
    assert tab.opacity.isEnabled()
    tab.view.setCurrentIndex(tab.view.findData("terrain"))
    assert not tab.contour.isHidden() and not tab.contour_label.isHidden()
    tab.view.setCurrentIndex(0)
    assert tab.contour.isHidden()
    labels = [tab.layer.itemText(i) for i in range(tab.layer.count())]
    assert labels[:3] == ["All layers", "All (2 x 2)", "Layer 1"] and tab.layer.currentData() == 0


def test_default_tab_draws_the_old_figure_and_a_view_changes_it(tab):
    """!
    @brief The default tab draws what draw_field draws with no view; choosing Terrain or the copper box changes the figure without a new solve.
    @param tab PlotTab fixture.
    """
    first = _rgba_tab(tab)
    tab.view.setCurrentIndex(tab.view.findData("terrain"))
    terrain = _rgba_tab(tab)
    assert _sha(first) != _sha(terrain)
    tab.view.setCurrentIndex(0)
    assert _sha(_rgba_tab(tab)) == _sha(first)                                      # Back to Current: the same pixels
    tab.underlay.combo.setCurrentIndex(1)
    assert _sha(_rgba_tab(tab)) != _sha(first)
    tab.layer.setCurrentIndex(tab.layer.findData(-2))
    tab.redraw()
    assert len([a for a in tab.fig.axes if a.get_images()]) == 4


def _rgba_tab(tab):
    """!
    @brief The pixels of a tab's figure after a redraw.
    @param tab PlotTab.
    @return uint8 array.
    """
    tab.redraw()
    tab.canvas.draw()
    return np.array(tab.canvas.buffer_rgba())


def test_theme_switch_redraws_with_the_theme_colours(tab):
    """!
    @brief With the copper box ticked, a theme switch redraws the figure with the other tokens (the picture changes and the contour colour follows).
    @param tab PlotTab fixture.
    """
    tab.underlay.combo.setCurrentIndex(1)
    tab.view.setCurrentIndex(tab.view.findData("terrain"))
    dark = _sha(_rgba_tab(tab))
    assert tab.map_view().contour_color == th.colors("dark")["map_contour"]
    tab.set_theme("light")
    assert tab.map_view().laminate_rgb[0] == pytest.approx(int(th.colors("light")["map_laminate"][1:3], 16) / 255.0, abs=1e-3)
    assert _sha(_rgba_tab(tab)) != dark


def test_temperature_and_gradient_tabs_share_the_view(sim):
    """!
    @brief Changing the view on the temperature tab changes the gradient tab and the other way round; the layers and the contour step stay separate.
    @param sim Simulation fixture.
    """
    QApplication.instance() or QApplication([])
    rv = ResultsView("dark")
    rv.set_simulation(sim)
    rv.temp.view.setCurrentIndex(rv.temp.view.findData("smooth"))
    rv.temp.underlay.combo.setCurrentIndex(1)
    rv.temp.opacity.setValue(40)
    assert rv.grad.view.currentData() == "smooth" and (rv.grad.underlay.kind() == "copper") and rv.grad.opacity.value() == 40
    rv.grad.view.setCurrentIndex(rv.grad.view.findData("terrain"))
    assert rv.temp.view.currentData() == "terrain"
    assert rv.grad.contour.isHidden()                                              # The gradient has no K step: it picks a round one
    rv.set_simulation(sim)                                                         # A new result keeps the choice
    assert rv.temp.view.currentData() == "terrain" and rv.temp.opacity.value() == 40
    assert rv.grad.map_view().contour_step == 0.0


def test_redraw_is_fast_on_a_100_by_80_mm_board(sim1):
    """!
    @brief Terrain with the copper box on a 100 x 80 mm board at 1 mm redraws in under 0.3 s once the copper picture is cached, with no new solve.
    @param sim1 Simulation fixture.
    """
    QApplication.instance() or QApplication([])
    t = PlotTab("temperature", "dark")
    t.set_simulation(sim1)
    t.underlay.combo.setCurrentIndex(1)
    t.view.setCurrentIndex(t.view.findData("terrain"))
    t.redraw()
    t.canvas.draw()                                                                # Warm: the copper picture is made here
    t0 = time.perf_counter()
    t.redraw()
    t.canvas.draw()
    assert time.perf_counter() - t0 < 0.3


def test_opacity_spin_box_and_slider_are_one_value_and_drive_the_pixels(tab):
    """!
    @brief The 0 to 100 % box and the slider follow each other with one redraw each, are enabled with the copper box only, and change the pixels.
    @param tab PlotTab fixture.
    """
    assert (tab.opacity_spin.minimum(), tab.opacity_spin.maximum(), tab.opacity_spin.value(), tab.opacity_spin.suffix()) == (0, 100, 70, " %")
    assert not tab.opacity_spin.isEnabled() and tab.opacity_spin.toolTip() and tab.opacity.toolTip()
    tab.underlay.combo.setCurrentIndex(1)
    assert tab.opacity_spin.isEnabled()
    calls = []
    tab.view_changed.connect(lambda: calls.append(1))
    p70 = _sha(_rgba_tab(tab))
    tab.opacity_spin.setValue(20)
    assert tab.opacity.value() == 20 and len(calls) == 1
    p20 = _sha(_rgba_tab(tab))
    tab.opacity.setValue(70)
    assert tab.opacity_spin.value() == 70 and len(calls) == 2
    assert p20 != p70 and _sha(_rgba_tab(tab)) == p70
    tab.opacity_spin.setValue(0)
    assert tab.map_view().opacity == 0.0


def test_default_view_matches_the_plain_imshow_on_any_matplotlib(sim, monkeypatch):
    """!
    @brief Version-independent twin of the hash test: the default picture equals the one drawn by develop's literal `imshow` call (patched in for
           `_draw_map`), in the same run, so a Matplotlib upgrade that skips the hash test still guards the default view.
    @param sim Simulation fixture.
    @param monkeypatch pytest fixture.
    """
    r = sim.results["fvm"]

    def pictures():
        """!
        @brief The single map, the row of layers and a gradient map with the default view.
        @return list of uint8 arrays.
        """
        out = [_field(sim, None, hotspot=100.0, title="t"), _field(sim, plots.MapView(), hotspot=100.0, title="t")]
        fig = plots.new_figure()
        plots.draw_fields(fig, r, sim.problem, view=plots.MapView())
        out.append(_rgba(fig))
        return out

    new = pictures()

    def develop_imshow(ax, field, problem, dx, dy, layer, cmap, vmin, vmax, view, solved_view=False):
        """!
        @brief The map call of develop before the View modes, argument for argument.
        @param ax Axis.
        @param field Field.
        @param problem Problem.
        @param dx Cell width in m.
        @param dy Cell height in m.
        @param layer Layer (unused).
        @param cmap Colormap.
        @param vmin Lower limit or None.
        @param vmax Upper limit or None.
        @param view MapView (unused).
        @param solved_view Unused.
        @return AxesImage.
        """
        _, _, ext = plots._field_axes(field, problem, dx, dy)
        return ax.imshow(field, origin="lower", cmap=cmap, extent=ext, vmin=np.nanmin(field) if vmin is None else vmin,
                         vmax=np.nanmax(field) if vmax is None else vmax)

    monkeypatch.setattr(plots, "_draw_map", develop_imshow)
    old = pictures()
    assert all(np.array_equal(a, b) for a, b in zip(new, old))


def test_upsampling_keeps_every_cell_in_its_place():
    """!
    @brief The Terrain lattice is not stretched: on a ramp the upsampled value at a pixel is the ramp at that pixel (the corner-aligned zoom was off by
           0.375 of a cell at the edges), and a blank cell blanks exactly its own k x k pixels.
    """
    n = 20
    ramp = np.tile(np.arange(n, dtype=float), (n, 1))                              # Value = index of the cell = position of its centre minus 0.5
    z, filled, xs, ys = plots._upsampled(ramp, [0.0, float(n), 0.0, float(n)])
    k = z.shape[1] // n
    inner = slice(k, (n - 1) * k)                                                   # The end cells are clamped (nearest), the rest must follow the ramp
    assert np.abs(z[n * k // 2, inner] - (xs[inner] - 0.5)).max() < 0.1          # The corner-aligned zoom: 0.33 of a cell here
    blank = ramp.copy()
    blank[:, 0] = np.nan
    z, filled, xs, ys = plots._upsampled(blank, [0.0, float(n), 0.0, float(n)])
    assert np.isnan(z[:, :k]).all() and not np.isnan(z[:, k:]).any() and not np.isnan(filled).any()


def test_terrain_keeps_the_colours_of_the_bar_on_flat_ground():
    """!
    @brief On a plateau (and on a plateau with a ripple of a millikelvin) the Terrain picture has the colours of the colour bar; only slopes are lit.
           Matplotlib's LightSource rescaled every picture's light to its own extremes, so flat ground moved off the bar and a ripple became a pattern.
    """
    from pcbthermal.model import Problem

    p = Problem.new(width_mm=40, height_mm=40, layers=1)
    y, x = np.mgrid[0:40, 0:40]
    field = 50.0 + 30.0 * np.exp(-((x - 10.0) ** 2 + (y - 10.0) ** 2) / 20.0)        # A hill in one corner, flat elsewhere
    field[25:, 25:] = 60.0 + 1e-3 * np.sin(x[25:, 25:] * 3.0)                          # A plateau with a ripple
    fig = plots.new_figure()
    ax = plots.draw_field(fig, field, p, 1e-3, 1e-3, view=plots.MapView(mode="terrain"), outline=False)
    rgba = np.asarray(ax.get_images()[0].get_array())
    k = rgba.shape[0] // 40
    sm = plots.ScalarMappable(plots.Normalize(np.nanmin(field), np.nanmax(field)), "inferno")
    flat = rgba[30 * k:38 * k, 30 * k:38 * k, :3]
    assert np.abs(flat - np.asarray(sm.to_rgba(60.0))[:3]).max() < 0.01
    assert np.abs(rgba[10 * k:12 * k, 4 * k:6 * k, :3] - rgba[10 * k:12 * k, 14 * k:16 * k, :3]).max() > 0.02   # The hill is lit on one side


def test_smooth_and_terrain_reach_the_outline_and_the_bar_is_opaque():
    """!
    @brief On an outline board Smooth draws a gap-free picture clipped to the outline (blank cells used to eat a band of 1.5 cells along it), and with the
           copper under the map the colour bar keeps full colours.
    """
    from pcbthermal.model import Problem

    p = Problem.new(width_mm=40, height_mm=30, layers=1)
    p.set_outline([(0, 0), (40, 0), (40, 12), (20, 12), (20, 30), (0, 30)])
    p.add_zone(1, rect=(2, 2, 18, 28))
    p.add_heater(1, 1.0, rect=(5, 20, 9, 24))
    s = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0))
    r = s.results["fvm"]
    for mode in ("smooth", "terrain"):
        fig = plots.new_figure()
        ax = plots.draw_field(fig, r.T[0], p, r.dx, r.dy, view=plots.MapView(mode=mode, show_copper=True))
        im = ax.get_images()[-1]
        assert im.get_clip_path() is not None
        assert not np.isnan(np.asarray(im.get_array(), dtype=float)).any()
        cbar = fig.axes[-1]
        assert all(getattr(c, "get_alpha", lambda: None)() in (None, 1.0) for c in cbar.collections + cbar.images)
        _rgba(fig)
