#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_map_markers_and_cut_locator.py
@brief The hottest and coolest sample marked on the Results temperature maps, and the board thumbnail with the cut line of the profile plot.
"""

import numpy as np
import pytest

from pcbthermal import analysis, plots
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui import fieldscale


@pytest.fixture(scope="module")
def sim():
    """!
    @brief One FVM run of the example board at a 2 mm cell.
    @return The api result of `simulate`.
    """
    return simulate(example_board(), SolverOptions(cell_mm=2.0, models=("fvm",)))


def _rings(ax):
    """!
    @brief The ring marks (the coloured ones, not the halos) drawn on an axis.
    @param ax Matplotlib axis.
    @return List of (colour, x, y).
    """
    out = []
    for ln in ax.lines:
        if ln.get_marker() == "o" and ln.get_markeredgecolor() in (plots.MAX_MARK_COLOUR, plots.MIN_MARK_COLOUR):
            out.append((ln.get_markeredgecolor(), float(ln.get_xdata()[0]), float(ln.get_ydata()[0])))
    return out


def test_extreme_points_lives_in_the_gui_free_module():
    """!
    @brief The editor overlay and the Results maps share one function, and it is importable without Qt.
    """
    assert fieldscale.extreme_points is analysis.extreme_points
    f = np.array([[3.0, 1.0], [5.0, 1.0]])
    e = analysis.extreme_points(f, None, 0.001, 0.001)
    assert e["tmax"] == 5.0 and e["tmin"] == 1.0
    assert e["pmin"] == (1.5, 0.5)                    # Ties: the first sample found (argmin), cell centres at half a cell


def test_temperature_map_marks_both_extremes_of_the_field_as_drawn(sim):
    """!
    @brief extremes=True draws a blue ring on the coolest and a red ring on the hottest sample, at the samples of the field.
    @param sim Simulation fixture.
    """
    r = sim.results["fvm"]
    fig = plots.new_figure()
    ax = plots.draw_field(fig, r.T[0], sim.problem, r.dx, r.dy, extremes=True)
    rings = {c: (x, y) for c, x, y in _rings(ax)}
    e = analysis.extreme_points(r.T[0], None, r.dx, r.dy)
    assert rings[plots.MAX_MARK_COLOUR] == pytest.approx(e["pmax"]) and rings[plots.MIN_MARK_COLOUR] == pytest.approx(e["pmin"])
    # Default (the gradient maps): no ring at all
    ax = plots.draw_field(plots.new_figure(), r.T[0], sim.problem, r.dx, r.dy)
    assert _rings(ax) == []


def test_flat_field_marks_nothing(sim):
    """!
    @brief A flat field has no hottest or coolest point to mark.
    @param sim Simulation fixture.
    """
    r = sim.results["fvm"]
    ax = plots.draw_field(plots.new_figure(), np.full_like(r.T[0], 40.0), sim.problem, r.dx, r.dy, extremes=True)
    assert _rings(ax) == []


def test_every_panel_of_all_layers_is_marked(sim):
    """!
    @brief All layers marks the hottest and the coolest sample of each panel.
    @param sim Simulation fixture.
    """
    r = sim.results["fvm"]
    fig = plots.new_figure()
    plots.draw_fields(fig, r, sim.problem)
    panels = [a for a in fig.axes if a.get_label() != "<colorbar>" and a.lines]
    assert len(panels) == r.T.shape[0]
    for a in panels:
        assert len(_rings(a)) == 2


def test_outline_board_marks_only_samples_on_the_board():
    """!
    @brief On a board with an outline the marks are taken over the samples that are drawn (cells off the outline are NaN), also in the solved view of the Lumped.
    """
    from pcbthermal.model import Problem

    p = Problem.new(width_mm=40, height_mm=30, layers=2)
    p.board.outline = np.array([[0, 0], [0.04, 0], [0.04, 0.015], [0.02, 0.015], [0.02, 0.03], [0, 0.03]])
    p.add_zone(1, rect=(0, 0, 40, 30))
    p.add_heater(1, 1.0, rect=(5, 5, 9, 9))
    s = simulate(p, SolverOptions(cell_mm=1.0, models=("fvm", "lumped")))
    for name in ("fvm", "lumped"):
        r = s.results[name]
        ax = plots.draw_field(plots.new_figure(), r.T[0], s.problem, r.dx, r.dy, extremes=True, equivalent_scale=r.equivalent_scale)
        rings = _rings(ax)
        assert len(rings) == 2
        for _c, x, y in rings:
            # Inside the real outline (or its solved rectangle: scaled by s), never in the notch
            sc = r.equivalent_scale or 1.0
            assert not (x / sc > 20.0 and y / sc > 15.0)


def test_profile_has_a_thumbnail_with_the_cut_line_at_the_plotted_row(sim):
    """!
    @brief The profile figure holds a second axes with the board and one cut line at the row actually plotted, and the title quotes that row.
    @param sim Simulation fixture.
    """
    r = sim.results["fvm"]
    fig = plots.new_figure(7, 4)
    plots.draw_profile(fig, sim.results, sim.problem, axis="x", position_mm=10.1)
    assert len(fig.axes) == 2
    curves, thumb = fig.axes
    xs, ys = r.coords()
    row = float(ys[int(np.argmin(np.abs(ys * 1000.0 - 10.1)))]) * 1000.0
    cut = [ln for ln in thumb.lines if ln.get_color() == plots.CUT_COLOUR]
    assert len(cut) == 1 and list(cut[0].get_ydata()) == pytest.approx([row, row])
    assert f"{row:.1f}" in curves.get_title()
    assert thumb.get_aspect() in (1.0, "equal")
    # Vertical cut, narrow figure: thumbnail on top
    fig = plots.new_figure(3, 5)
    plots.draw_profile(fig, sim.results, sim.problem, axis="y", position_mm=20.0)
    curves, thumb = fig.axes[1], fig.axes[0]
    assert thumb.get_position().y0 > curves.get_position().y0
    assert thumb.lines and [ln for ln in thumb.lines if ln.get_color() == plots.CUT_COLOUR]


def test_profile_thumbnail_survives_every_layer_and_the_default_cut(sim, tmp_path):
    """!
    @brief Any layer, the default (hottest point) cut and the command line wrapper draw without error, and the PNG has the thumbnail.
    @param sim Simulation fixture.
    @param tmp_path pytest temporary folder.
    """
    for layer in range(sim.results["fvm"].T.shape[0]):
        plots.draw_profile(plots.new_figure(), sim.results, sim.problem, layer=layer)
    out = tmp_path / "p.png"
    plots.plot_profiles(sim.results, sim.problem, str(out))
    assert out.stat().st_size > 1000


def test_hot_ring_stays_at_the_model_tmax_point_and_only_the_cold_one_is_computed(sim):
    """!
    @brief With a `hot` point (or `marker` on the map) the red ring is there; the blue ring is still the coolest drawn sample.
    @param sim Simulation fixture.
    """
    r = sim.results["fvm"]
    e = analysis.extreme_points(r.T[0], None, r.dx, r.dy, hot=(99.0, (1.25, 2.5)))
    assert e["tmax"] == 99.0 and e["pmax"] == (1.25, 2.5)
    assert e["pmin"] == analysis.extreme_points(r.T[0], None, r.dx, r.dy)["pmin"]
    ax = plots.draw_field(plots.new_figure(), r.T[0], sim.problem, r.dx, r.dy, extremes=True, marker=(0.003, 0.004))
    rings = {c: (x, y) for c, x, y in _rings(ax)}
    assert rings[plots.MAX_MARK_COLOUR] == pytest.approx((3.0, 4.0))
    assert rings[plots.MIN_MARK_COLOUR] == pytest.approx(analysis.extreme_points(r.T[0], None, r.dx, r.dy)["pmin"])


def test_lumped_hot_mark_is_the_reported_peak_point_on_every_layer_grid():
    """!
    @brief The Lumped map keeps its hot ring at `t_max_location` (the part's peak), in the all-layers view too.
    """
    from pcbthermal.model import Problem

    p = Problem.new(width_mm=40, height_mm=30, layers=2)
    p.add_zone(1, rect=(0, 0, 40, 30))
    p.add_heater(1, 1.0, rect=(5, 5, 9, 9))
    s = simulate(p, SolverOptions(cell_mm=1.0, models=("lumped",)))
    r = s.results["lumped"]
    layer, x, y = r.t_max_location
    fig = plots.new_figure()
    plots.draw_fields(fig, r, s.problem)
    ax = [a for a in fig.axes if a.get_label() != "<colorbar>" and a.lines][layer]
    red = [(px, py) for c, px, py in _rings(ax) if c == plots.MAX_MARK_COLOUR]
    assert red == [pytest.approx((x * 1000.0, y * 1000.0))]
