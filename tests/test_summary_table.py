#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_summary_table.py
@brief The models table of the Results summary: one column definition (api.SUMMARY_COLUMNS) behind the window, the text report and the Markdown report; two-line
       headers that name the read-out, the balance as a percentage with a floor, the surface column, nothing cut at 1200 x 800, no second copy of the table on screen.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings

from pcbthermal.api import SUMMARY_COLUMNS, SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.results import model_label
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow

MODELS = ("fvm", "fdm", "lumped", "analytic")


@pytest.fixture(scope="module")
def sim():
    """!
    @brief One run of four models on the example board (the surface read-out exists for the FVM and the FDM only).
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=MODELS, cell_mm=2.0))


def _window(qtbot, tmp_path, w, h):
    """!
    @brief A shown main window of a given size with private settings.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param w Width in px.
    @param h Height in px.
    @return MainWindow.
    """
    win = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    win.resize(w, h)
    win.show()
    return win


def test_one_definition_feeds_the_window_the_text_and_the_markdown(sim):
    """!
    @brief The three outputs list the same columns in the same order, with the same cells (the key of the model in the first column of the text and the Markdown).
    @param sim Simulation fixture.
    """
    cols, rows, tips = sim.summary_grid()
    assert [c.key for c in cols] == [c.key for c in SUMMARY_COLUMNS]          # the surface column is there: the FVM and FDM have a surface read-out
    md = [ln for ln in sim.to_markdown().split("\n") if ln.startswith("| ")]
    assert [x.strip() for x in md[0].strip("|").split("|")] == [c.header_markdown("FVM") for c in cols]
    for cells, line in zip(rows, md[2:]):
        assert [x.strip() for x in line.strip("|").split("|")] == cells
    text = sim.to_text().split("\n")
    assert "ΔT K" in text[0] and "(column)" in text[1] and "(surface)" in text[1] and "(all layers)" in text[1] and "(of ΔT)" in text[1] and "Error vs FVM" in text[0]
    body = [ln for ln in text if ln.split(" ")[0] in {model_label(m) for m in MODELS}]
    assert len(body) == len(MODELS) and len({len(ln) for ln in body}) == 1 and len(body[0]) == len(text[2])    # aligned: widths from the longest cell
    assert "ΔT [K]" in sim.to_markdown() and "ΔT [°C]" not in sim.to_markdown() and "dT C" not in sim.to_text()


def test_the_surface_column_is_the_top_face_peak_or_n_a(sim):
    """!
    @brief Tmax (surface) is the top-face peak of every model that has one (FVM, FDM, Analytic, 3D solid, FEM) and n/a for the Lumped; it is left out when no model has one.
    @param sim Simulation fixture.
    """
    rows = {r["model"]: r for r in sim.table()}
    assert rows["fvm"]["t_max_surface_c"] == pytest.approx(sim.results["fvm"].extras["t_max_surface_top"]) and rows["lumped"]["t_max_surface_c"] is None
    cols, cells, _ = sim.summary_grid(lambda k: k)          # the keys, to look the rows up
    i = [c.key for c in cols].index("t_max_surface_c")
    by = {r[0]: r[i] for r in cells}
    assert by["lumped"] == "n/a" and by["analytic"] != "n/a" and by["fvm"] != "n/a"
    only = simulate(example_board(), SolverOptions(models=("lumped",), cell_mm=2.0))
    assert "t_max_surface_c" not in [c.key for c in only.summary_columns()] and "surface" not in only.to_text()


def test_the_window_table_has_two_line_headers_tips_and_a_percentage_balance(qtbot, tmp_path, sim):
    """!
    @brief The Qt table reads the definition: headers that name the read-out, a tooltip per header, the raw balance in the tooltip of its cell, one row per model with no empty row.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation fixture.
    """
    win = _window(qtbot, tmp_path, 1500, 900)
    win._on_done(sim)
    t = win.results.model_table
    heads = [t.horizontalHeaderItem(c).text() for c in range(t.columnCount())]
    assert "Tmax °C\n(column)" in heads and "Tmean °C\n(all layers)" in heads and "ΔT K" in heads and "Error vs FVM\n(of ΔT)" in heads and "Tmax °C\n(surface)" in heads
    assert all(t.horizontalHeaderItem(c).toolTip() for c in range(t.columnCount()))
    mean_tip = t.horizontalHeaderItem(heads.index("Tmean °C\n(all layers)")).toolTip()
    assert "all copper layers" in mean_tip and "over the board" not in mean_tip
    assert "ring network" in t.horizontalHeaderItem(heads.index("Tmax °C\n(column)")).toolTip()
    assert t.rowCount() == len(MODELS)
    bal = heads.index("Balance")
    assert t.item(0, bal).text() == "0.00 %" and t.item(0, bal).toolTip().startswith("Raw value")
    assert t.height() <= t.horizontalHeader().height() + len(MODELS) * t.verticalHeader().defaultSectionSize() + 12      # no empty row left
    # The on-screen report no longer repeats the table; the saved report and the command line keep it
    assert "Tmean" not in win.results.report.toPlainText() and "Tmean" in sim.report()


def test_nothing_is_cut_at_1200_x_800(qtbot, tmp_path, sim):
    """!
    @brief In a 1200 x 800 window every header and cell is shown whole or reached by the horizontal scroll bar: no column is narrower than its header or its text, and the table is not taller than its rows.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation fixture.
    """
    win = _window(qtbot, tmp_path, 1200, 800)
    win._on_done(sim)
    win.results.tabs.setCurrentIndex(0)
    qtbot.wait(100)
    t = win.results.model_table
    head = t.horizontalHeader()
    for c in range(t.columnCount() - 1):                          # the last column stretches; the others are as wide as their content
        assert head.sectionSize(c) >= t.sizeHintForColumn(c), (c, head.sectionSize(c), t.sizeHintForColumn(c))
        assert head.sectionSize(c) >= head.sectionSizeHint(c), c
    assert t.horizontalScrollBar().maximum() > 0 and t.horizontalScrollBar().isVisibleTo(t)       # the columns do not fit: scroll, never cut
    assert t.verticalScrollBar().maximum() == 0 and t.height() >= head.height() + t.rowCount() * t.verticalHeader().defaultSectionSize()
    # At a wide window the table fits with no scroll bar
    win.resize(2000, 1000)
    qtbot.wait(100)
    assert t.horizontalScrollBar().maximum() == 0


def test_the_components_tables_are_not_cut_at_1200_x_800(qtbot, tmp_path, sim):
    """!
    @brief The Components tables take the same fix as the Summary: columns as wide as their header or content, a horizontal scroll bar when they do not fit, only the last one stretches.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation fixture.
    """
    win = _window(qtbot, tmp_path, 1200, 800)
    win._on_done(sim)
    win.results.tabs.setCurrentIndex(4)             # Components
    qtbot.wait(100)
    rv = win.results
    for t in (rv.heater_table, rv.zone_table, rv.hot_table):
        head = t.horizontalHeader()
        assert head.stretchLastSection() and head.sectionResizeMode(0) == head.ResizeMode.ResizeToContents
        for c in range(t.columnCount() - 1):
            assert head.sectionSize(c) >= head.sectionSizeHint(c), (t.columnCount(), c, head.sectionSize(c), head.sectionSizeHint(c))
            assert head.sectionSize(c) >= t.sizeHintForColumn(c), (c,)
    t = rv.heater_table                                 # 11 columns: either all fit or the scroll bar reaches the rest
    assert t.horizontalScrollBar().maximum() > 0 or t.viewport().width() >= sum(t.horizontalHeader().sectionSize(c) for c in range(t.columnCount()))
    # Review of the branch: the scroll bar took the height of the second row (U2 hidden); the table keeps two rows above its bar
    assert t.viewport().height() >= 2 * t.verticalHeader().defaultSectionSize()


def test_warnings_are_ordered_junction_then_warnings_then_notes(qtbot):
    """!
    @brief The list puts a junction above its limit first, then the other warnings, then the notes; within a kind the order of the checks stays; the title says °C.
    @param qtbot pytest-qt fixture.
    """
    from pcbthermal import checks
    from pcbthermal.gui.warning_box import WarningAccordion
    acc = WarningAccordion("t")
    qtbot.addWidget(acc)
    note1 = checks.warn("U1: a note one", "note")
    alert = checks.warn("U3: a part is outside the board", "alert", "heater", 2)
    note2 = checks.warn("U2: a note two", "note")
    junction = checks.warn("U2: the junction reaches 130.4 degC, 90.4 K above its limit of 40 degC", "alert", "heater", 1)
    alert2 = checks.warn("U4: heats nothing", "alert", "heater", 3)
    acc.set_warnings([note1, alert, note2, junction, alert2])
    assert [str(r.warning) for r in acc.rows] == [str(w) for w in (junction, alert, alert2, note1, note2)]
    assert "°C" in acc.rows[0].title_label.text() and "degC" not in acc.rows[0].title_label.text()


@pytest.mark.parametrize("theme", ["dark", "light"])
@pytest.mark.parametrize("size", [(1200, 800), (1500, 900)])
def test_the_warnings_box_does_not_touch_the_report_console(qtbot, tmp_path, size, theme):
    """!
    @brief On the Summary page the Warnings box keeps a gap of SUMMARY_WARNINGS_GAP_PX above the report console, which keeps a useful height.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param size Window size (w, h) in px.
    @param theme Theme name.
    """
    from PySide6.QtCore import QPoint
    from pcbthermal.gui.results_view import SUMMARY_WARNINGS_GAP_PX
    win = _window(qtbot, tmp_path, *size)
    if hasattr(win, "set_theme"):
        win.set_theme(theme)
    view = win.results
    run = simulate(example_board(), SolverOptions(models=MODELS, cell_mm=2.0))
    view.set_simulation(run)
    view._show_warnings(["Test note: some text of the note that the box lists."])      # Shown whatever the example raises
    view.warnings.setVisible(True)
    view.tabs.setCurrentIndex(0)
    win.tabs.setCurrentIndex([win.tabs.tabText(i) for i in range(win.tabs.count())].index("Results"))
    qtbot.wait(200)
    assert view.warnings.isVisible()
    top = view.report.mapTo(view, QPoint(0, 0)).y()
    # The accordion's own bottom margin is the gap: its box ends that many px above the console
    box = view.warnings.box
    bottom = box.mapTo(view, QPoint(0, box.height())).y()
    assert top - bottom >= SUMMARY_WARNINGS_GAP_PX
    assert view.report.height() >= 120
