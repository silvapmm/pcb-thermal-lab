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
    @brief `run --help` does not call "general" the default: the default is the form stored in the project file (general when absent, laminar in a new project).
    @param capsys pytest fixture.
    """
    from pcbthermal import cli
    with pytest.raises(SystemExit):
        cli.main(["run", "--help"])
    text = " ".join(capsys.readouterr().out.split())
    assert "general (default)" not in text
    assert "the form stored in the project file" in text and "a file without it reads general" in text and "stores laminar" in text
