#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_equivalent_rectangle_view.py
@brief The maps draw the rectangle of the same area that the Lumped and Analytic models solved, only for those models and only on a board with an outline.
"""

import numpy as np
import pytest

from pcbthermal import plots
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow
from PySide6.QtCore import QSettings


def _outline_problem():
    """!
    @brief The example board cut to a T-shaped outline.
    @return Problem with an outline.
    """
    p = example_board()
    W, H = p.board.width, p.board.height
    p.board.outline = np.array([[0, 0], [W, 0], [W, 0.45 * H], [0.65 * W, 0.45 * H], [0.65 * W, H], [0.35 * W, H], [0.35 * W, 0.45 * H], [0, 0.45 * H]], dtype=float)
    p.heaters = p.heaters[:1]
    p.heaters[0].polygon = np.array([[0.4 * W, 0.6 * H], [0.55 * W, 0.6 * H], [0.55 * W, 0.8 * H], [0.4 * W, 0.8 * H]])
    p.vias = []
    return p


def _dashed(ax):
    """!
    @brief Lines of an axis that carry the legend text of the equivalent rectangle.
    @param ax Matplotlib axes.
    @return List of Line2D.
    """
    return [ln for ln in ax.get_lines() if ln.get_label().startswith(plots.EQUIVALENT_LABEL)]


@pytest.fixture(scope="module")
def sim():
    """!
    @brief One run of the four models on the outline board (2 mm cell).
    @return Simulation.
    """
    return simulate(_outline_problem(), SolverOptions(models=("fvm", "fdm", "lumped", "analytic"), cell_mm=2.0))


def test_scale_is_recorded_only_for_lumped_and_analytic(sim):
    """!
    @brief The result carries the scale s of the rectangle for the two reduced models and None for the others.
    @param sim Simulation fixture.
    """
    assert sim.results["fvm"].equivalent_scale is None and sim.results["fdm"].equivalent_scale is None
    s = sim.problem.equivalent_rectangle()[1]
    assert 0.5 < s < 1.0
    for m in ("lumped", "analytic"):
        assert sim.results[m].equivalent_scale == pytest.approx(s)
        assert any("show that rectangle as solved" in w for w in sim.results[m].warnings)


def test_draw_field_adds_the_rectangle_only_when_asked(sim):
    """!
    @brief draw_field draws the field as solved for a scale: the dashed edge has the size its legend gives, the image fills that rectangle, and
           the parts are those of the rectangle; nothing changes for None.
    @param sim Simulation fixture.
    """
    r = sim.results["lumped"]
    eq, s = sim.problem.equivalent_rectangle()
    fig = plots.new_figure()
    ax = plots.draw_field(fig, r.T[0], sim.problem, r.dx, r.dy, equivalent_scale=r.equivalent_scale)
    lines = _dashed(ax)
    assert len(lines) == 1 and fig.legends
    W, H = eq.board.width * 1000.0, eq.board.height * 1000.0
    assert max(lines[0].get_xdata()) == pytest.approx(W) and max(lines[0].get_ydata()) == pytest.approx(H)
    assert f"{W:.1f} x {H:.1f} mm" in lines[0].get_label()
    ext = ax.get_images()[0].get_extent()                                   # The field fills the solved rectangle, not the real box
    assert ext[1] == pytest.approx(W, rel=1e-6) and ext[3] == pytest.approx(H, rel=1e-6)
    assert not np.ma.getmaskarray(ax.get_images()[0].get_array()).any()              # Nothing blanked: the rectangle is the board that was solved
    heater = eq.heaters[0].polygon * 1000.0                                  # The part is drawn where the model put it
    xs = [ln.get_xdata() for ln in ax.get_lines() if ln.get_linestyle() == "--" and len(ln.get_xdata()) == len(heater) + 1]
    assert any(np.allclose(x[:-1], heater[:, 0]) for x in xs)
    assert ax.get_xlim() == pytest.approx((0, sim.problem.board.width * 1000.0))   # The axes keep the real box, so the real outline is in sight
    ax = plots.draw_field(fig, r.T[0], sim.problem, r.dx, r.dy)
    assert _dashed(ax) == [] and not fig.legends
    assert np.ma.getmaskarray(ax.get_images()[0].get_array()).any()                  # Stretched view: blanked outside the outline as before
    fig = plots.new_figure()
    plots.draw_fields(fig, r, sim.problem)
    assert sum(len(_dashed(a)) for a in fig.axes) == sim.problem.board.layers and len(fig.legends) == 1
    plots.draw_fields(fig, r, sim.problem, show_equivalent=False)
    assert sum(len(_dashed(a)) for a in fig.axes) == 0 and not fig.legends


def test_gradient_uses_the_solved_spacing(sim):
    """!
    @brief The gradient of a Lumped or Analytic result on an outline board is taken on the spacing that was solved, not the stretched one.
    @param sim Simulation fixture.
    """
    from pcbthermal import analysis
    r = sim.results["analytic"]
    s = r.equivalent_scale
    gy, gx = np.gradient(r.T[0], r.dy * s * 1000.0, r.dx * s * 1000.0)
    assert np.allclose(analysis.gradient_magnitude(r)[0], np.hypot(gx, gy))
    f = sim.results["fvm"]
    gy, gx = np.gradient(f.T[0], f.dy * 1000.0, f.dx * 1000.0)
    assert np.array_equal(analysis.gradient_magnitude(f)[0], np.hypot(gx, gy))


def test_old_result_without_the_field_draws_stretched(sim):
    """!
    @brief A result pickled before the field existed (no attribute in its dict) reads None and draws as before.
    @param sim Simulation fixture.
    """
    import copy
    r = copy.copy(sim.results["lumped"])
    del r.__dict__["equivalent_scale"]
    assert r.equivalent_scale is None
    fig = plots.new_figure()
    plots.draw_fields(fig, r, sim.problem)
    assert sum(len(_dashed(a)) for a in fig.axes) == 0


def test_rectangular_board_is_unchanged():
    """!
    @brief A board without an outline records no scale and the image is the same with or without the argument.
    @return None.
    """
    p = example_board()
    s = simulate(p, SolverOptions(models=("lumped", "analytic"), cell_mm=2.0))
    for r in s.results.values():
        assert r.equivalent_scale is None
    r = s.results["lumped"]
    f1, f2 = plots.new_figure(), plots.new_figure()
    plots.draw_field(f1, r.T[0], p, r.dx, r.dy)
    plots.draw_field(f2, r.T[0], p, r.dx, r.dy, equivalent_scale=0.8)        # No outline: ignored
    f1.canvas.draw()
    f2.canvas.draw()
    assert np.array_equal(np.asarray(f1.canvas.buffer_rgba()), np.asarray(f2.canvas.buffer_rgba()))


def test_gui_checkbox(qtbot, tmp_path, sim):
    """!
    @brief The Temperature and Gradient tabs show the checkbox for Lumped and Analytic only; the board overlay stays the stretched map without a
           rectangle (the editor's parts are on the real board, so the solved frame cannot be drawn there).
    @param qtbot pytest-qt fixture.
    @param tmp_path pytest folder.
    @param sim Simulation fixture.
    """
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.show()
    t = win.results.temp
    t.set_simulation(sim)
    for key, visible in (("fvm", False), ("lumped", True), ("analytic", True), ("fdm", False)):
        t.model.setCurrentIndex(t.model.findData(key))
        assert t.equiv.isVisibleTo(t) is visible, key
    t.model.setCurrentIndex(t.model.findData("lumped"))
    assert len(_dashed(t.fig.axes[0])) == 1
    t.equiv.setChecked(False)
    assert _dashed(t.fig.axes[0]) == []
    t.equiv.setChecked(True)
    assert len(_dashed(t.fig.axes[0])) == 1
    g = win.results.grad
    g.set_simulation(sim)
    g.model.setCurrentIndex(g.model.findData("analytic"))
    assert g.equiv.isVisibleTo(g) and len(_dashed(g.fig.axes[0])) == 1
    win._load_problem(sim.problem, "t")
    ref = sim.results["lumped"]
    win.canvas.set_overlay(ref.T[0], ref.dx, ref.dy)
    assert not hasattr(win.canvas, "_equivalent_item")
