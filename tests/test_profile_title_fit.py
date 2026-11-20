#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_profile_title_fit.py
@brief The Profiles chart keeps its title and its axis labels inside the canvas at the window sizes of the layout checks, the title keeps all its words in two lines,
       and the help of `run --natural-form` says what the default really is.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings

from pcbthermal import plots
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import TAB_RESULTS, MainWindow

SIZES = ((1200, 800), (1000, 700), (900, 700), (800, 600))


@pytest.fixture(scope="module")
def sim():
    """!
    @brief The example board in the three main models at a 2 mm cell.
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=("fvm", "lumped", "analytic"), cell_mm=2.0))


@pytest.mark.parametrize("size", SIZES)
def test_the_profiles_title_and_labels_lie_inside_the_canvas(qtbot, tmp_path, sim, size):
    """!
    @brief In the Profiles tab of the main window the title (the text with the "nearest cell centre" note, as the slider rarely sits on a cell centre), the y label and the
           x label are inside the canvas at every size; it fails when the title is one 450 px line (left margin of -35 px at 1000 x 700).
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation fixture.
    @param size Window size (width, height) in pixels.
    """
    doc = Document()
    doc.open_problem(example_board(), "example")
    win = MainWindow(doc, QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.show()
    win.sim = sim
    win.results.set_simulation(sim)
    win.tabs.setCurrentIndex(TAB_RESULTS)
    win.resize(*size)
    win.results.tabs.setCurrentWidget(win.results.profile)
    qtbot.wait(150)
    tab = win.results.profile
    tab.redraw()
    tab.canvas.draw()
    fig = tab.fig
    renderer = fig.canvas.get_renderer()
    width, height = fig.canvas.get_width_height()
    ax = [a for a in fig.axes if a.get_title().startswith("Cut")][0]
    assert "nearest to" in ax.get_title()                      # The long case: the cut asked is not on a cell centre
    for name, artist in (("title", ax.title), ("ylabel", ax.yaxis.label), ("xlabel", ax.xaxis.label)):
        box = artist.get_window_extent(renderer)
        assert box.x0 >= -0.5 and box.x1 <= width + 0.5 and box.y0 >= -0.5 and box.y1 <= height + 0.5, (name, size, box, (width, height))


def test_the_title_keeps_all_its_words_in_two_lines(sim):
    """!
    @brief A wide figure has the title in the two lines that were one: the position, then the note; no word is lost.
    @param sim Simulation fixture.
    """
    fig = plots.new_figure(7, 4)
    plots.draw_profile(fig, sim.results, sim.problem, axis="x", position_mm=40.0, picture="off")
    title = [a for a in fig.axes if a.get_title().startswith("Cut")][0].get_title()
    assert title.split("\n")[0].startswith("Cut along x at y = ") and title.split("\n")[1].startswith("(the cell centre nearest to 40.0 mm)")
    assert " ".join(title.split()).startswith("Cut along x at y = ") and "(the cell centre nearest to 40.0 mm)" in " ".join(title.split())


def test_the_natural_form_help_names_the_real_default(capsys):
    """!
    @brief `run --help` does not call "general" the default: the default is the form stored in the project file (general when absent and in the example board, laminar in a new board of the window).
    @param capsys pytest fixture.
    """
    from pcbthermal import cli
    with pytest.raises(SystemExit):
        cli.main(["run", "--help"])
    text = " ".join(capsys.readouterr().out.split())
    assert "general (default)" not in text
    assert "the form stored in the project file" in text and "general when the file has none" in text and "laminar since 2.5.0" in text
    assert "'example' command" in text                         # Review: the board of the example command stores general, so "a project made in the program" was too broad


def _inside(fig, ax):
    """!
    @brief The texts of a profile axes that stick out of the canvas of its figure (drawn first).
    @param fig Figure, drawn.
    @param ax Axes with the curves.
    @return list of (name, box) for the title, the y label and the x label that are not inside the canvas.
    """
    renderer = fig.canvas.get_renderer()
    width, height = fig.canvas.get_width_height()
    out = []
    for name, artist in (("title", ax.title), ("ylabel", ax.yaxis.label), ("xlabel", ax.xaxis.label)):
        box = artist.get_window_extent(renderer)
        if box.x0 < -0.5 or box.x1 > width + 0.5 or box.y0 < -0.5 or box.y1 > height + 0.5:
            out.append((name, box))
    return out


@pytest.mark.parametrize("picture", ("map", "off"))
def test_the_texts_fit_at_every_width_without_a_warning(sim, picture):
    """!
    @brief Review: a sweep of the figure width from 100 to 1400 px (two heights) keeps the title and the labels inside the canvas and raises no warning except the
           collapse of a canvas too small for any chart (which the Results canvas paints blank, `plots.draw_unless_collapsed`); the first version fitted the title
           before the legend, the cut picture and the tick format moved the axes, and the narrow title overhung the right edge by up to 39 px (100 x 315 px; the x label by 20 px).
    @param sim Simulation fixture.
    @param picture Cut picture ("map": inset or strip; "off").
    """
    import warnings
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    res = {k: r for k, r in sim.results.items() if r.T is not None}
    bad = []
    for width in range(100, 1401, 40):
        for height in (315, int(0.45 * width) + 60):
            fig = Figure(figsize=(width / 100.0, height / 100.0), dpi=100, layout="constrained")
            FigureCanvasAgg(fig)
            with warnings.catch_warnings():
                warnings.simplefilter("error", UserWarning)
                plots.draw_profile(fig, res, sim.problem, axis="x", position_mm=40.0, picture=picture)
                if plots.draw_unless_collapsed(fig, fig.canvas.draw):
                    continue
            ax = [a for a in fig.axes if a.get_title().startswith("Cut")][0]
            bad += [(width, height, name) for name, _box in _inside(fig, ax)]
            assert all(line.strip() != "mm)" and not line.startswith("mm") for line in ax.get_title().split("\n"))   # A unit never starts a line
    assert not bad, bad


def test_a_resize_after_the_draw_fits_the_texts_again(qtbot, tmp_path, sim):
    """!
    @brief Review: the wrapping was measured once, at the draw; a window shrunk afterwards (here 1600 x 1000, then 800 x 600) kept the wide title, cut at the left
           (-11 px). The canvas resize now fits the texts again (`plots.refit_texts`), and back at the wide size the title is two lines again.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation fixture.
    """
    doc = Document()
    doc.open_problem(example_board(), "example")
    win = MainWindow(doc, QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.show()
    win.sim = sim
    win.results.set_simulation(sim)
    win.tabs.setCurrentIndex(TAB_RESULTS)
    tab = win.results.profile
    win.results.tabs.setCurrentWidget(tab)
    win.resize(1600, 1000)
    qtbot.wait(150)
    tab.redraw()
    tab.canvas.draw()
    for size in ((800, 600), (1600, 1000)):
        win.resize(*size)
        qtbot.wait(150)
        tab.canvas.draw()                                       # No redraw of the tab: only the resize of the canvas
        ax = [a for a in tab.fig.axes if a.get_title().startswith("Cut")][0]
        assert not _inside(tab.fig, ax), (size, _inside(tab.fig, ax))
    assert ax.get_title().count("\n") == 1                      # Wide again: the two lines, not the narrow wrapping
