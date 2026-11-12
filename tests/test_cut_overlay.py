#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_cut_overlay.py
@brief The cut overlay of the Results - Profiles tab: its content follows the toolbar Layer, the Display panel and the Map button; the tab has only the Cut overlay
       box; the Display popover has a Profiles context (View and Contour greyed).
"""

import copy
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings

from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import TAB_RESULTS, MainWindow


@pytest.fixture(scope="module")
def sim():
    """!
    @brief One FVM and Lumped run of the example board (2 mm cell).
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=("fvm", "lumped"), cell_mm=2.0))


def _window(qtbot, tmp_path, sim):
    """!
    @brief A main window on the Results - Profiles tab with the example result.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation.
    @return MainWindow
    """
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win._load_problem(copy.deepcopy(sim.problem), "t")
    win.results.set_simulation(sim)
    win.sim, win._stale = sim, False
    win._update_map_button()
    win._apply_layer()
    win.show()
    win.tabs.setCurrentIndex(TAB_RESULTS)
    win.results.tabs.setCurrentWidget(win.results.profile)
    return win


def _inset(win):
    """!
    @brief The inset axes of the profile figure (None when the figure has none).
    @param win MainWindow.
    @return Axes or None.
    """
    kids = win.results.profile.fig.axes[0].child_axes
    return kids[0] if kids else None


def test_the_tab_has_one_new_control_and_it_hides_the_overlay(qtbot, tmp_path, sim):
    """!
    @brief The Cut overlay box is on by default, has a tooltip, hides and shows the inset, and the tab has no other new control.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation.
    """
    win = _window(qtbot, tmp_path, sim)
    pt = win.results.profile
    assert pt.cut_overlay.isChecked() and pt.cut_overlay.toolTip()
    pt.redraw()
    assert _inset(win) is not None
    pt.cut_overlay.setChecked(False)
    assert _inset(win) is None
    pt.cut_overlay.setChecked(True)
    assert _inset(win) is not None


def test_the_map_button_puts_the_heat_map_in_the_picture_and_the_display_underlay_under_it(qtbot, tmp_path, sim):
    """!
    @brief Map button off: the board only; on: the temperature map; Underlay Copper: the copper under it (an image more); the colour map is the Display one.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation.
    """
    win = _window(qtbot, tmp_path, sim)
    pt = win.results.profile
    pt.redraw()
    n_off = len(_inset(win).images)
    win.a_overlay.setChecked(True)
    ins = _inset(win)
    assert len(ins.images) == n_off + 1
    win.display.set_kind("copper")
    ins = _inset(win)
    assert len(ins.images) >= n_off + 2                      # The copper picture and the map over it
    assert ins.images[-1].get_alpha() == pytest.approx(win.display.value())
    win.display.set_cmap("viridis")
    assert _inset(win).images[-1].get_cmap().name == "viridis"
    win.a_overlay.setChecked(False)
    assert len(_inset(win).images) < len(ins.images)


def test_the_picture_follows_the_toolbar_layer(qtbot, tmp_path, sim):
    """!
    @brief The title of the picture names the layer of the toolbar Layer box (the same as the curve's axis label).
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation.
    """
    win = _window(qtbot, tmp_path, sim)
    pt = win.results.profile
    for layer in (0, 2):
        pt.set_layer(layer)
        assert _inset(win).get_title() == f"Layer {layer + 1}"
        assert f"Layer {layer + 1} temperature" in pt.fig.axes[0].get_ylabel()


def test_a_narrow_window_keeps_the_strip_above_the_curves(qtbot, tmp_path, sim):
    """!
    @brief A figure narrower than 5 in has the picture in a strip above the curves (two axes, no inset).
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation.
    """
    win = _window(qtbot, tmp_path, sim)
    pt = win.results.profile
    pt.fig.set_size_inches(4.0, 5.0)
    pt.redraw()
    assert len(pt.fig.axes) == 2 and not pt.fig.axes[1].child_axes and not pt.fig.axes[0].child_axes


def test_the_display_popover_greys_view_and_contour_in_the_profiles_context(qtbot, tmp_path, sim):
    """!
    @brief In the Profiles tab the Display popover has a profile context: View and Contour greyed, Underlay, opacity and Colour map usable.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation.
    """
    win = _window(qtbot, tmp_path, sim)
    assert win._display_context() == "profile"
    pop = win.display_popover
    pop.set_context("profile")
    assert not pop.view.isEnabled() and not pop.contour.isEnabled()
    assert pop.underlay.isEnabled() and pop.cmap.isEnabled()
    pop.set_context("temperature")
    assert pop.view.isEnabled()
