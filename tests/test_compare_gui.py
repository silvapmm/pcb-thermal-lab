#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_compare_gui.py
@brief Tests of the Difference view in the application: the one verdict line under the Model row (no More button, the warning colour outside the usual range in both
       themes, its tooltip), the default reference after a change of the model shown, the user's own reference, the refusals, the title of the figure at every canvas
       width (drawn large and then shrunk, as the window is), and the proof that the view moves no number of any model.
"""

import os
import warnings

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from pcbthermal import compare, plots
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui import layerchoice
from pcbthermal.gui import theme as th
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import TAB_RESULTS, MainWindow

MODELS = ("fvm", "lumped", "analytic", "fdm")


@pytest.fixture(scope="module")
def sim():
    """!
    @brief The example board in four models at the 1 mm cell of the documented tables (the FDM is a node field: another grid).
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=MODELS, cell_mm=1.0))


@pytest.fixture
def win(qtbot, tmp_path, sim):
    """!
    @brief A window with the example board and the simulation shown on the Temperature page (light theme).
    @param qtbot Fixture.
    @param tmp_path Fixture.
    @param sim Simulation fixture.
    @return MainWindow.
    """
    st = QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat)
    st.setValue("theme", "light")
    w = MainWindow(Document(), st)
    qtbot.addWidget(w)
    w._load_problem(example_board(), "ex")
    w.resize(1200, 800)
    w.show()
    w._on_done(sim)
    w.tabs.setCurrentIndex(TAB_RESULTS)
    w.results.tabs.setCurrentWidget(w.results.temp)
    qtbot.wait(30)
    return w


def _show(temp, model):
    """!
    @brief Choose the model shown in the Temperature page.
    @param temp The Temperature PlotTab.
    @param model Model key.
    """
    temp.model.setCurrentIndex(temp.model.findData(model))


def _choose_layer(win, data):
    """!
    @brief Pick an entry of the toolbar Layer box as the user would.
    @param win MainWindow.
    @param data Data of the entry (a layer index, `layerchoice.ALL_LAYERS`, `SURFACE_BASE + face`, ...).
    """
    i = win.layer_combo.findData(data)
    assert i >= 0, data
    win._pick_combo_entry(i)


def _inside(artist, fig):
    """!
    @brief Whether the extent of a text lies inside the canvas of a figure.
    @param artist Matplotlib Text.
    @param fig Figure.
    @return bool
    """
    b = artist.get_window_extent(fig.canvas.get_renderer())
    return b.x0 >= -0.5 and b.y0 >= -0.5 and b.x1 <= fig.bbox.width + 0.5 and b.y1 <= fig.bbox.height + 0.5


def test_the_difference_line_is_one_line_with_the_verdict_first_and_no_more_button(win, qtbot):
    """!
    @brief LPTN - FVM on the example board: one line that begins with the verdict, the tooltip holds the range and the evidence, there is no More button and the page
           keeps its width.
    @param win MainWindow fixture.
    @param qtbot Fixture.
    """
    t = win.results.temp
    assert not hasattr(t, "diff_more") and t.diff_note.max_lines == 1
    _show(t, "lumped")
    t.diff_on.setChecked(True)
    qtbot.wait(30)
    assert t.diff_ref.currentData() == "fvm" and t.diff_note.isVisible()
    text = t.diff_note.text()
    assert text.startswith("Usual for the LPTN: hottest point ") and "% of the rise (usual -5.4 to +8.4 %)" in text
    assert "\n" not in text
    tip = t.diff_note.toolTip()
    assert "19 of 20 scenarios" in tip and "docs/validation.md sections 1 and 2" in tip and "the map can differ more around the parts" in tip
    assert t.diff_note.height() <= t.diff_note.fontMetrics().lineSpacing() + 8        # One line of text high
    assert t.diff_note.styleSheet() == ""                                                # The usual colour inside the range
    assert t.minimumSizeHint().width() < t.width()                                       # The line never sets the width of the page


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_outside_the_usual_range_the_line_has_the_warning_colour_of_the_theme(win, qtbot, monkeypatch, theme):
    """!
    @brief A gap outside the documented range (a narrowed range stands for it) draws the line in the `alert_note` token of the theme, and its words say so; inside the
           range it has no colour of its own. The pixels of the label hold the token's colour.
    @param win MainWindow fixture.
    @param qtbot Fixture.
    @param monkeypatch Fixture.
    @param theme "light" or "dark".
    """
    if theme == "dark":
        win.toggle_theme()
    t = win.results.temp
    assert win.results.temp.theme == theme
    monkeypatch.setitem(compare.EXPECTED, ("lumped", "fvm"), compare.Tip("LPTN: narrowed for the test", "section 1", -0.1, 0.1, 1, 20, ()))
    _show(t, "lumped")
    t.diff_on.setChecked(True)
    qtbot.wait(30)
    assert t.diff_note.text().startswith("Outside the usual range for the LPTN:") and "(usual -0.1 to +0.1 %)" in t.diff_note.text()
    tone = th.colors(theme)["alert_note"]
    assert tone in t.diff_note.styleSheet()
    img = t.diff_note.grab().toImage()
    r, g, b = (int(tone[i:i + 2], 16) for i in (1, 3, 5))
    close = sum(1 for y in range(img.height()) for x in range(img.width())
                if max(abs(img.pixelColor(x, y).red() - r), abs(img.pixelColor(x, y).green() - g), abs(img.pixelColor(x, y).blue() - b)) <= 24)
    assert close >= 20, f"the line is not drawn in {tone}"
    monkeypatch.undo()
    t.redraw()
    assert t.diff_note.text().startswith("Usual for the LPTN") and t.diff_note.styleSheet() == ""


def test_the_pairs_of_the_table_have_a_line_and_the_others_none(win, qtbot):
    """!
    @brief FDM and Analytic against the FVM say their documented range; the Analytic against the LPTN has no evidence, so no line (the map is still drawn).
    @param win MainWindow fixture.
    @param qtbot Fixture.
    """
    t = win.results.temp
    t.diff_on.setChecked(True)
    for model, words in (("fdm", "Usual for the FDM"), ("analytic", "Usual for the Analytic")):
        _show(t, model)
        qtbot.wait(20)
        assert t.diff_ref.currentData() == "fvm" and t.diff_note.text().startswith(words), (model, t.diff_note.text())
    t.diff_ref.setCurrentIndex(t.diff_ref.findData("lumped"))        # Analytic - LPTN: nothing documented
    qtbot.wait(20)
    assert not t.diff_note.isVisible() and t.fig._suptitle is not None and "Analytic − LPTN" in t.fig._suptitle.get_text()


def test_the_reference_is_the_fvm_after_a_change_of_the_model_shown(win, qtbot):
    """!
    @brief The defect of the prototype: run the four models, show the FDM or the Analytic, switch the Difference on: the reference is the FVM, not the LPTN. A
           reference that the user chose is kept while it is possible; one the user did not choose returns to the FVM whenever the model shown changes.
    @param win MainWindow fixture.
    @param qtbot Fixture.
    """
    t = win.results.temp
    assert t.model.currentData() == "fvm"
    for model in ("fdm", "analytic", "lumped"):
        _show(t, model)
        t.diff_on.setChecked(True)
        qtbot.wait(20)
        assert t.diff_ref.currentData() == "fvm", model
        t.diff_on.setChecked(False)
    # The FVM shown: the reference moves off it to the first other model; shown again after a change it is back on the FVM
    _show(t, "fvm")
    t.diff_on.setChecked(True)
    qtbot.wait(20)
    assert t.diff_ref.currentData() != "fvm"
    _show(t, "fdm")
    qtbot.wait(20)
    assert t.diff_ref.currentData() == "fvm"
    # The user's own choice is kept while it is possible, and gives way when it becomes the model shown
    t.diff_ref.setCurrentIndex(t.diff_ref.findData("analytic"))
    _show(t, "lumped")
    qtbot.wait(20)
    assert t.diff_ref.currentData() == "analytic"
    _show(t, "analytic")
    qtbot.wait(20)
    assert t.diff_ref.currentData() == "fvm"


def test_a_surface_read_out_of_the_lptn_is_refused_in_the_warning_colour(win, qtbot):
    """!
    @brief With the Layer box on the top surface the LPTN has no read-out: the one line gives the reason in the warning colour and the temperature map is drawn.
    @param win MainWindow fixture.
    @param qtbot Fixture.
    """
    t = win.results.temp
    _show(t, "lumped")
    t.diff_on.setChecked(True)
    _choose_layer(win, layerchoice.SURFACE_BASE)
    qtbot.wait(30)
    text = t.diff_note.text()
    assert text.startswith("Difference not shown: ") and text.endswith("The temperature map is drawn.") and "surface" in text
    assert th.colors("light")["alert_note"] in t.diff_note.styleSheet()
    _show(t, "fdm")                                                         # FDM - FVM on the surface: both hold it
    qtbot.wait(30)
    assert t.diff_note.text().startswith("Usual for the FDM") and "surface (top)" in t.fig._suptitle.get_text()


def test_all_layers_shows_layer_one_and_the_line_names_the_title_does(win, qtbot):
    """!
    @brief The All-layers entry gives the Difference of layer 1; the figure title says so and the tooltip of the line carries the sentence.
    @param win MainWindow fixture.
    @param qtbot Fixture.
    """
    t = win.results.temp
    _show(t, "lumped")
    t.diff_on.setChecked(True)
    _choose_layer(win, layerchoice.ALL_LAYERS)
    qtbot.wait(30)
    assert "layer 1, column mean" in t.fig._suptitle.get_text()
    assert "one layer at a time" in t.diff_note.toolTip()


def test_the_figure_title_says_the_interpolation_and_stays_inside_at_every_window_size(win, qtbot):
    """!
    @brief FDM - FVM (the FDM is a node field, interpolated onto the cell grid): the title carries the sentence; the title, the colour bar and its label stay in the canvas
           when the window is shrunk from large (the title was drawn for the large size), with no layout warning and no overlap of the title with the colour bar.
    @param win MainWindow fixture.
    @param qtbot Fixture.
    """
    t = win.results.temp
    _show(t, "fdm")
    t.diff_on.setChecked(True)
    win.resize(1600, 1000)
    qtbot.wait(60)
    assert "(FDM was interpolated onto the FVM grid)" in t.fig._suptitle.get_text().replace("\n", " ")
    for w, h in ((1400, 900), (1200, 800), (1000, 760), (900, 700), (760, 620)):
        win.resize(w, h)
        qtbot.wait(60)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            t.canvas.draw()
        assert not [c for c in caught if "layout" in str(c.message).lower()], (w, h)
        fig = t.fig
        cax = [a for a in fig.axes if a is not fig.axes[0]][0]
        r = fig.canvas.get_renderer()
        assert _inside(fig._suptitle, fig) and _inside(cax.yaxis.label, fig) and _inside(fig.axes[0].xaxis.label, fig), (w, h, t.canvas.width())
        assert not fig._suptitle.get_window_extent(r).overlaps(cax.get_tightbbox(r)), (w, h)


def _bare_sweep_figure(sim, width, height, shrink_from):
    """!
    @brief The Difference figure drawn at one size (or drawn at a large size and then shrunk, the refit being called as the resize handler of the page does).
    @param sim Simulation.
    @param width Final canvas width, px.
    @param height Final canvas height, px.
    @param shrink_from None, or the (width, height) at which the figure is first drawn.
    @return Figure.
    """
    d = compare.difference_field(sim.results["lumped"], sim.results["fvm"], sim.problem)
    fig = Figure(layout="constrained", dpi=100)
    FigureCanvasAgg(fig)
    fig.set_size_inches((shrink_from or (width, height))[0] / 100.0, (shrink_from or (width, height))[1] / 100.0)
    plots.draw_difference(fig, d, sim.problem)
    fig.canvas.draw()
    if shrink_from:
        fig.set_size_inches(width / 100.0, height / 100.0)
        plots.refit_texts(fig)
    return fig


@pytest.mark.parametrize("shrink_from", [None, (1600, 1000)])
def test_the_difference_title_fits_every_canvas_width(sim, shrink_from):
    """!
    @brief Sweep of the canvas width from 1400 px to 150 px: the title, the colour-bar label, the tick labels and the axis labels lie inside the canvas, the title does not
           touch the colour bar and the layout gives no warning. (A canvas narrower than about 150 px collapses the layout of every map of the program.)
    @param sim Simulation fixture.
    @param shrink_from None to draw at the size, or the size to draw at before shrinking.
    """
    for width, height in ((1400, 700), (1200, 560), (1000, 500), (800, 450), (600, 420), (535, 530), (400, 400), (300, 400), (230, 400), (180, 350), (150, 300)):
        fig = _bare_sweep_figure(sim, width, height, shrink_from)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            fig.canvas.draw()
        assert not [c for c in caught if "layout" in str(c.message).lower()], (width, shrink_from)
        ax, cax = fig.axes[0], fig.axes[1]
        r = fig.canvas.get_renderer()
        items = [fig._suptitle, cax.yaxis.label, ax.xaxis.label, ax.yaxis.label]
        items += [tick for a in (ax, cax) for tick in a.get_xticklabels() + a.get_yticklabels() if tick.get_visible() and tick.get_text()]
        outside = [i.get_text() for i in items if not _inside(i, fig)]
        assert not outside, (width, height, shrink_from, outside[:3])
        assert not fig._suptitle.get_window_extent(r).overlaps(cax.get_tightbbox(r)), (width, shrink_from)


def test_the_title_is_wrapped_to_the_figure_not_to_the_axes(sim):
    """!
    @brief At 200 px (the 900 x 700 window with both docks open is about 230 px: the case that ran over the colour bar) the title has more lines than at 1200 px and every line fits the figure width.
    @param sim Simulation fixture.
    """
    narrow = _bare_sweep_figure(sim, 200, 400, None)
    wide = _bare_sweep_figure(sim, 1200, 560, None)
    assert narrow._suptitle.get_text().count("\n") > wide._suptitle.get_text().count("\n")
    r = narrow.canvas.get_renderer()
    assert narrow._suptitle.get_window_extent(r).width <= narrow.bbox.width - 4
    lines = narrow._suptitle.get_text().split("\n")
    assert all(line == line.rstrip() for line in lines), lines                      # "mm   RMS" broken at its spaces leaves no space at the end of a centred line


def test_the_view_moves_no_number_of_any_model(win, qtbot, sim):
    """!
    @brief Display only: the fields, the maxima and the arrays of every result are byte for byte the same after the view was switched on, through every model pair and
           layer choice, and off again.
    @param win MainWindow fixture.
    @param qtbot Fixture.
    @param sim Simulation fixture.
    """
    before = {k: (r.T.copy(), r.t_max, r.t_min, r.t_mean, {a: np.array(v, copy=True) for a, v in r.arrays.items()}) for k, r in sim.results.items()}
    t = win.results.temp
    t.diff_on.setChecked(True)
    for model in MODELS:
        _show(t, model)
        for data in (0, layerchoice.ALL_LAYERS, layerchoice.SURFACE_BASE):
            _choose_layer(win, data)
            qtbot.wait(5)
    t.diff_on.setChecked(False)
    for k, r in sim.results.items():
        T, tmax, tmin, tmean, arrays = before[k]
        assert np.array_equal(r.T, T) and (r.t_max, r.t_min, r.t_mean) == (tmax, tmin, tmean), k
        assert set(r.arrays) == set(arrays) and all(np.array_equal(r.arrays[a], arrays[a], equal_nan=True) for a in arrays), k


def test_a_run_at_2_mm_gets_no_verdict_and_no_warning_colour(qtbot, tmp_path):
    """!
    @brief The FDM against the FVM on the example board at 2 mm is -1.1 % of the rise, outside the 1 mm range: the line says it is not judged at that cell, in the normal
           colour (a false alarm at a coarse cell is worse than no verdict), and its tooltip says why.
    @param qtbot Fixture.
    @param tmp_path Fixture.
    """
    st = QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat)
    st.setValue("theme", "light")
    w = MainWindow(Document(), st)
    qtbot.addWidget(w)
    w._load_problem(example_board(), "ex")
    w.resize(1200, 800)
    w.show()
    w._on_done(simulate(example_board(), SolverOptions(models=("fvm", "fdm"), cell_mm=2.0)))
    w.tabs.setCurrentIndex(TAB_RESULTS)
    w.results.tabs.setCurrentWidget(w.results.temp)
    t = w.results.temp
    _show(t, "fdm")
    t.diff_on.setChecked(True)
    qtbot.wait(30)
    assert t.diff_ref.currentData() == "fvm"
    assert t.diff_note.text() == "Not judged at 2 mm cells: FDM hottest point -0.7 K, -1.1 % of the rise (usual -0.5 to 0.0 % at 1 mm)", t.diff_note.text()
    assert t.diff_note.styleSheet() == "" and "no verdict" in t.diff_note.toolTip()


def test_on_an_outline_board_the_refusal_names_the_outline_and_the_fvm_gets_a_usable_reference(qtbot, tmp_path):
    """!
    @brief A T-shaped board: the LPTN shown is refused against the FVM because it solved a rectangle of the same area (review: it kept the LPTN as its own reference and
           said 'the model and the reference are the same'); the FVM shown takes the first usable reference (the FDM), not the refused LPTN.
    @param qtbot Fixture.
    @param tmp_path Fixture.
    """
    p = example_board()
    p.set_outline([[0, 80], [0, 50], [35, 50], [35, 0], [65, 0], [65, 50], [100, 50], [100, 80]])
    st = QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat)
    st.setValue("theme", "light")
    w = MainWindow(Document(), st)
    qtbot.addWidget(w)
    w._load_problem(p, "t")
    w.resize(1200, 800)
    w.show()
    w._on_done(simulate(p, SolverOptions(models=("fvm", "lumped", "fdm"), cell_mm=2.0)))
    w.tabs.setCurrentIndex(TAB_RESULTS)
    w.results.tabs.setCurrentWidget(w.results.temp)
    t = w.results.temp
    t.diff_on.setChecked(True)
    _show(t, "lumped")
    qtbot.wait(30)
    assert t.diff_ref.currentData() == "fvm"
    assert t.diff_note.text().startswith("Difference not shown: LPTN solved this outline board on a rectangle"), t.diff_note.text()
    _show(t, "fvm")
    qtbot.wait(30)
    assert t.diff_ref.currentData() == "fdm" and t.fig._suptitle is not None and "FVM − FDM" in t.fig._suptitle.get_text()
