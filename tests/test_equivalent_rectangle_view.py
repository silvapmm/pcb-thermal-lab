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
        assert any("the maps draw that rectangle dashed" in w for w in sim.results[m].warnings)


def test_draw_field_adds_the_rectangle_only_when_asked(sim):
    """!
    @brief draw_field draws the dashed rectangle and its legend for a scale, and nothing for None.
    @param sim Simulation fixture.
    """
    r = sim.results["lumped"]
    fig = plots.new_figure()
    ax = plots.draw_field(fig, r.T[0], sim.problem, r.dx, r.dy, equivalent_scale=r.equivalent_scale)
    lines = _dashed(ax)
    assert len(lines) == 1 and ax.get_legend() is not None
    b = sim.problem.board
    assert max(lines[0].get_xdata()) == pytest.approx(b.width * 1000.0)
    assert f"{b.width * 1000.0 * r.equivalent_scale:.1f}" in lines[0].get_label()
    ax = plots.draw_field(fig, r.T[0], sim.problem, r.dx, r.dy)
    assert _dashed(ax) == []
    fig = plots.new_figure()
    plots.draw_fields(fig, r, sim.problem)
    assert sum(len(_dashed(a)) for a in fig.axes) >= 1
    plots.draw_fields(fig, r, sim.problem, show_equivalent=False)
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


def test_gui_checkbox_and_board_overlay(qtbot, tmp_path, sim):
    """!
    @brief The Results tab shows the checkbox for Lumped and Analytic only, and the board overlay draws the dashed rectangle of a Lumped reference.
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
    # Board view: a Lumped reference gets the dashed item, an FVM one does not
    win._load_problem(sim.problem, "t")
    ref = sim.results["lumped"]
    win.canvas.set_overlay(ref.T[0], ref.dx, ref.dy, equivalent_scale=ref.equivalent_scale)
    assert win.canvas._equivalent_item is not None
    win.canvas.clear_overlay()
    assert win.canvas._equivalent_item is None
    fvm = sim.results["fvm"]
    win.canvas.set_overlay(fvm.T[0], fvm.dx, fvm.dy, equivalent_scale=fvm.equivalent_scale)
    assert getattr(win.canvas, "_equivalent_item", None) is None
