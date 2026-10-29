#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_ui_cleanup.py
@brief Small interface fixes: model names on the comparison plot, ticks of a very long log axis, the inner tab bar of the results, the size of Preferences.
"""

from types import SimpleNamespace

import numpy as np
from matplotlib.figure import Figure
from PySide6.QtCore import QSettings, Qt

from pcbthermal import plots
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow
from pcbthermal.gui.preferences import PreferencesDialog


def test_the_comparison_plot_writes_the_names_of_the_models_not_their_keys():
    fig = Figure()
    results = {k: SimpleNamespace(t_max=80.0 + i, t_mean=50.0 + i) for i, k in enumerate(("fvm", "lumped", "analytic", "fdm", "solid3d"))}
    plots.draw_comparison(fig, results)
    labels = [t.get_text() for t in fig.axes[0].get_xticklabels()]
    assert labels == ["FVM", "Lumped (LPTN)", "Analytic", "FDM", "3D solid"]


def test_a_log_axis_of_more_than_six_decades_gets_a_tick_every_three_decades():
    fig = Figure()
    ax = fig.add_subplot(111)
    ax.set_xscale("log")
    ax.plot([1e-6, 1e3], [0.0, 1.0])
    plots.engineering_ticks(fig)
    fig.canvas.draw()
    ticks = [t for t in ax.get_xticks() if 1e-6 * 0.99 <= t <= 1e3 * 1.01]
    assert len(ticks) <= 4
    assert all(abs(np.log10(t) / 3.0 - round(np.log10(t) / 3.0)) < 1e-9 for t in ticks)     # Powers of 1000: 1E-6, 1E-3, 1, 1E3


def test_a_short_log_axis_keeps_a_tick_per_decade():
    fig = Figure()
    ax = fig.add_subplot(111)
    ax.set_xscale("log")
    ax.plot([0.1, 600.0], [0.0, 1.0])
    plots.engineering_ticks(fig)
    fig.canvas.draw()
    assert len([t for t in ax.get_xticks() if 0.1 * 0.99 <= t <= 600]) >= 4


def test_the_results_tab_bar_keeps_whole_names_and_scrolls(qtbot, tmp_path):
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    assert win.results.tabs.tabBar().elideMode() == Qt.ElideNone
    assert win.results.tabs.tabBar().usesScrollButtons()


def test_preferences_open_wide_enough_for_the_list_and_the_widest_page(qtbot):
    d = PreferencesDialog()
    qtbot.addWidget(d)
    assert d.width() >= 960
