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


def test_profile_has_a_cut_picture_with_the_cut_line_at_the_plotted_row(sim):
    """!
    @brief The profile figure holds an inset over the curves with the board and one cut line at the row actually plotted, and the title quotes that row.
    @param sim Simulation fixture.
    """
    r = sim.results["fvm"]
    fig = plots.new_figure(7, 4)
    plots.draw_profile(fig, sim.results, sim.problem, axis="x", position_mm=10.1, picture="board")
    assert len(fig.axes) == 1 and len(fig.axes[0].child_axes) == 1
    curves, thumb = fig.axes[0], fig.axes[0].child_axes[0]
    xs, ys = r.coords()
    row = float(ys[int(np.argmin(np.abs(ys * 1000.0 - 10.1)))]) * 1000.0
    cut = [ln for ln in thumb.lines if ln.get_color() == plots.CUT_COLOUR]
    assert len(cut) == 1 and list(cut[0].get_ydata()) == pytest.approx([row, row])
    assert f"{row:.1f}" in curves.get_title()
    assert thumb.get_aspect() in (1.0, "equal")
    # Vertical cut, narrow figure: the strip above the curves, as before the overlay
    fig = plots.new_figure(3, 5)
    plots.draw_profile(fig, sim.results, sim.problem, axis="y", position_mm=20.0, picture="board")
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


def _inset_corner(fig):
    """!
    @brief The corner of the cut picture of a drawn profile figure, from the position of its inset.
    @param fig Figure drawn by `plots.draw_profile` in the overlay layout.
    @return "ul", "ur", "ll" or "lr".
    """
    ax = fig.axes[0]
    b = ax.child_axes[0].get_position(original=True)
    bb = ax.get_position()
    return ("u" if (b.y0 + b.y1) / 2 > (bb.y0 + bb.y1) / 2 else "l") + ("r" if (b.x0 + b.x1) / 2 > (bb.x0 + bb.x1) / 2 else "l")


def _hot_left():
    """!
    @brief The example board with U1 moved to the left edge, solved by the FVM.
    @return (problem, results dict).
    """
    pr = example_board()
    for h in pr.heaters:
        if h.name == "U1":
            h.polygon = h.polygon.copy()
            h.polygon[:, 0] -= 0.022
    for v in pr.vias:
        if v.x < 0.05:
            v.x -= 0.022
    s = simulate(pr, SolverOptions(cell_mm=2.0, models=("fvm", "lumped")))
    return pr, s.results


def test_cut_picture_is_top_left_unless_the_curve_or_the_peak_is_under_it(sim):
    """!
    @brief The corner rule: upper left on the example board, moved away when the hottest point sits at the left edge, the legend never in the picture's corner.
    @param sim Simulation fixture.
    """
    fig = plots.new_figure(7, 4)
    plots.draw_profile(fig, sim.results, sim.problem, picture="board")
    assert _inset_corner(fig) == "ul"
    pr, res = _hot_left()
    fig = plots.new_figure(7, 4)
    plots.draw_profile(fig, res, pr, picture="board")
    corner = _inset_corner(fig)
    assert corner != "ul"
    # The legend is in an explicit corner, not the picture's, and not 'best' (loc 0)
    leg = fig.axes[0].get_legend()
    assert leg is not None and leg._loc != 0
    names = {1: "ur", 2: "ul", 3: "ll", 4: "lr"}
    assert names[leg._loc] != corner
    # Deterministic: the same data gives the same corner
    fig2 = plots.new_figure(7, 4)
    plots.draw_profile(fig2, res, pr, picture="board")
    assert _inset_corner(fig2) == corner


def test_cut_picture_follows_the_picture_argument_and_the_cut_line_colour(sim):
    """!
    @brief "off" has no picture, "board" the plain board with the amber line, "map" the temperature map with the white line on its black halo.
    @param sim Simulation fixture.
    """
    fig = plots.new_figure(7, 4)
    plots.draw_profile(fig, sim.results, sim.problem, picture="off")
    assert not fig.axes[0].child_axes and len(fig.axes) == 1
    fig = plots.new_figure(7, 4)
    plots.draw_profile(fig, sim.results, sim.problem, picture="board")
    ins = fig.axes[0].child_axes[0]
    assert not ins.images and [ln for ln in ins.lines if ln.get_color() == plots.CUT_COLOUR]
    fig = plots.new_figure(7, 4)
    plots.draw_profile(fig, sim.results, sim.problem, picture="map", cmap="viridis")
    ins = fig.axes[0].child_axes[0]
    assert len(ins.images) == 1 and ins.images[0].get_cmap().name == "viridis"
    colours = [ln.get_color() for ln in ins.lines]
    assert "#ffffff" in colours and "#000000" in colours and plots.CUT_COLOUR not in colours
    assert ins.patch.get_alpha() == 1.0                   # The frame is opaque


def test_cut_picture_on_a_stretched_model_of_an_outline_board_is_plain_with_a_note():
    """!
    @brief A Lumped reference on an outline board has no map (it would be stretched) and the title says why.
    """
    pr = example_board()
    pr.board.outline = np.array([[0, 0], [0.1, 0], [0.1, 0.05], [0.05, 0.08], [0, 0.08]])
    res = simulate(pr, SolverOptions(cell_mm=2.0, models=("lumped",))).results
    fig = plots.new_figure(7, 4)
    plots.draw_profile(fig, res, pr, picture="map")
    ins = fig.axes[0].child_axes[0]
    assert not ins.images and "equivalent rectangle" in ins.get_title()


def test_cut_picture_png_and_command_line_default_have_the_inset(sim, tmp_path):
    """!
    @brief The saved PNG draws the inset (command line default: board with the map) and a narrow figure keeps the strip.
    @param sim Simulation fixture.
    @param tmp_path pytest temporary folder.
    """
    fig = plots.new_figure(7, 4)
    plots.draw_profile(fig, sim.results, sim.problem)           # The default picture is "map"
    assert len(fig.axes[0].child_axes[0].images) == 1
    out = tmp_path / "p.png"
    plots.plot_profiles(sim.results, sim.problem, str(out), picture="board")
    assert out.stat().st_size > 1000
    fig = plots.new_figure(4, 6)
    plots.draw_profile(fig, sim.results, sim.problem)
    assert len(fig.axes) == 2 and not fig.axes[1].child_axes
