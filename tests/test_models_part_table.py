#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_models_part_table.py
@brief The temperature under every part in every model: the API definition (rows, reference column, n/a, power per model, one model), the report block and the CSV file, the chart of the whole board, and the two tables of the Models tab (layout at 1200 x 800, elided names, tooltips, many parts, clear).
"""

import copy
import csv
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from matplotlib.figure import Figure

from pcbthermal import analysis, plots
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.results import model_color, model_order

FOUR = ("fvm", "lumped", "analytic", "fdm")


@pytest.fixture(scope="module")
def sim4():
    """!
    @brief The example board in four models at a 2 mm cell (about 1 s).
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(cell_mm=2.0, models=FOUR))


# ------------------------------------------------------------------ the API definition

def test_one_row_per_part_and_one_column_per_model_in_the_program_order(sim4):
    cmp = sim4.part_comparison()
    assert cmp["reference"] == "fvm" and cmp["models"] == ["fvm", "lumped", "analytic", "fdm"]
    assert [p["name"] for p in cmp["parts"]] == ["U1", "U2"]
    for part in cmp["parts"]:
        for key in ("t_max", "t_mean"):
            assert set(part[key]) == set(FOUR) and all(v is not None and np.isfinite(v) for v in part[key].values())
        assert part["t_max_delta"]["fvm"] is None                       # the reference has no difference from itself
        assert part["t_max_delta"]["fdm"] == pytest.approx(part["t_max"]["fdm"] - part["t_max"]["fvm"])
    assert sim4.part_comparison()["board"]["fvm"] == (pytest.approx(sim4.results["fvm"].t_max), pytest.approx(sim4.results["fvm"].t_mean))


def test_the_reference_column_equals_the_components_numbers_and_every_model_its_own_heater_stats(sim4):
    cmp = sim4.part_comparison()
    for part, row in zip(cmp["parts"], sim4.heater_rows()):                       # heater_rows = what the Components table shows
        assert part["t_max"]["fvm"] == row["t_max"] and part["t_mean"]["fvm"] == row["t_mean"]
        assert part["power_w"] == row["power_w"]
    for m in FOUR:
        rows = analysis.heater_stats(sim4.results[m], sim4.problem, sim4.power_used.get(m))
        for part, row in zip(cmp["parts"], rows):
            assert part["t_max"][m] == row["t_max"] and part["t_mean"][m] == row["t_mean"]


def test_the_lptn_part_mean_is_its_painted_node_and_its_max_is_the_network_peak(sim4):
    # The LPTN paints one node under each part (two when its footprint is cut into zones over a group of vias; both parts of the example board stay one node,
    # arrays["zoned_heaters"]): the mean under the footprint is that node, the maximum is the network's own peak of the part (never below the node)
    part = sim4.part_comparison()["parts"][0]
    assert part["t_max"]["lumped"] >= part["t_mean"]["lumped"]
    assert part["t_max"]["lumped"] == pytest.approx(float(sim4.results["lumped"].arrays["heater_peak"][0]))


def test_a_value_that_is_not_finite_is_none_and_reads_n_a(sim4, monkeypatch, tmp_path):
    from pcbthermal import api
    real = api.heater_stats

    def stats(result, problem, powers=None):
        rows = real(result, problem, powers)
        if result.model == "analytic":
            for r in rows:
                r["t_max"] = float("nan")
        return rows

    monkeypatch.setattr(api, "heater_stats", stats)
    cmp = sim4.part_comparison()
    assert cmp["parts"][0]["t_max"]["analytic"] is None and cmp["parts"][0]["t_max_delta"]["analytic"] is None
    assert cmp["parts"][0]["t_mean"]["analytic"] is not None            # the other reading of that model stays
    assert "Analytic n/a" in "\n".join(sim4.part_comparison_lines())
    path = tmp_path / "p.csv"
    sim4.write_part_comparison_csv(str(path))
    rows = list(csv.reader(open(path)))
    assert rows[1][rows[0].index("analytic_c")] == ""


def test_each_model_uses_the_power_it_dissipated():
    p = example_board()
    p.heaters[0].power_tc = 0.004                                     # P = P0 (1 + tc (Tj - 25)): the models disagree on the power a little
    sim = simulate(p, SolverOptions(cell_mm=2.0, models=("fvm", "lumped", "analytic")))
    part = sim.part_comparison()["parts"][0]
    for m in ("fvm", "lumped", "analytic"):
        assert part["power_by_model"][m] == pytest.approx(sim.power_used[m][0])
    assert len({round(w, 6) for w in part["power_by_model"].values()}) > 1
    assert part["power_w"] == pytest.approx(part["power_by_model"]["fvm"])
    # and the numbers are those of heater_stats with that power
    assert part["t_max"]["lumped"] == analysis.heater_stats(sim.results["lumped"], sim.problem, sim.power_used["lumped"])[0]["t_max"]


def test_one_model_gives_one_column_and_no_block_and_no_file(tmp_path):
    sim = simulate(example_board(), SolverOptions(cell_mm=2.0, models=("fvm",)))
    cmp = sim.part_comparison()
    assert cmp["models"] == ["fvm"] and len(cmp["parts"]) == 2
    assert sim.part_comparison_lines() == []                              # nothing to compare
    assert "Parts by model" not in sim.report()
    files = sim.save(str(tmp_path), plots=False)
    assert not any(f.endswith("parts_by_model.csv") for f in files)


def test_a_model_other_than_the_fvm_is_the_reference_when_the_fvm_did_not_run():
    sim = simulate(example_board(), SolverOptions(cell_mm=2.0, models=("lumped", "analytic")))
    cmp = sim.part_comparison()
    assert cmp["reference"] == "lumped" and cmp["models"] == ["lumped", "analytic"]
    assert cmp["parts"][0]["t_max_delta"]["lumped"] is None
    assert cmp["parts"][0]["t_max_delta"]["analytic"] == pytest.approx(cmp["parts"][0]["t_max"]["analytic"] - cmp["parts"][0]["t_max"]["lumped"])
    assert "difference from the reference LPTN" in "\n".join(sim.part_comparison_lines())


def test_no_part_gives_no_rows(sim4):
    sim = copy.copy(sim4)
    sim.problem = copy.deepcopy(sim4.problem)
    sim.problem.heaters = []
    cmp = sim.part_comparison()
    assert cmp["parts"] == [] and cmp["models"] == ["fvm", "lumped", "analytic", "fdm"]
    assert sim.part_comparison_lines() == []


def test_the_report_and_the_csv_hold_the_same_numbers_and_summary_numbers_do_not_move(sim4, tmp_path):
    table_before = sim4.table()
    text = sim4.report()
    assert "Parts by model" in text and "U1 (4.00 W) hottest point: FVM" in text and "U1 (4.00 W) mean: FVM" in text and "(reference)" in text
    cmp = sim4.part_comparison()
    u1 = cmp["parts"][0]
    assert f"FDM {u1['t_max']['fdm']:.2f} ({u1['t_max_delta']['fdm']:+.2f})" in text
    files = sim4.save(str(tmp_path), plots=False)
    csv_path = [f for f in files if f.endswith("parts_by_model.csv")]
    assert csv_path
    rows = list(csv.DictReader(open(csv_path[0])))
    assert len(rows) == 4 and rows[0]["part"] == "U1" and rows[0]["reading"] == "Tmax"
    assert float(rows[0]["fdm_c"]) == pytest.approx(u1["t_max"]["fdm"], abs=1e-4)
    assert float(rows[0]["fdm_minus_fvm_k"]) == pytest.approx(u1["t_max_delta"]["fdm"], abs=1e-4)
    assert sim4.table() == table_before                                  # this item moves no model number


# ------------------------------------------------------------------ the order and the colours, the chart

def test_model_order_and_colours():
    assert model_order(["fem", "fvm", "analytic", "lumped"], "fvm") == ["fvm", "lumped", "analytic", "fem"]
    assert model_order(["fem", "fvm", "lumped"], "lumped") == ["lumped", "fvm", "fem"]
    assert model_order(["lumped", "x"], None) == ["lumped", "x"]
    assert len({model_color(k) for k in ("fvm", "lumped", "analytic", "fdm", "solid3d", "fem")}) == 6
    assert model_color("lumped") == model_color("lumped")


@pytest.mark.parametrize("theme_text", ["black", "white"])
def test_the_chart_has_one_bar_per_model_and_group_the_reference_hatched_and_named(sim4, theme_text):
    import matplotlib
    fig = Figure(layout="constrained")
    with matplotlib.rc_context({"text.color": theme_text}):
        plots.draw_comparison(fig, sim4.results, "fvm")
        fig.canvas.draw()
    ax = fig.axes[0]
    bars = [b for b in ax.patches]
    assert len(bars) == 2 * len(FOUR)                                          # two groups, one bar per model
    hatched = [b for b in bars if b.get_hatch()]
    assert len(hatched) == 2 and all(b.get_linewidth() >= 1.0 for b in hatched)  # the reference only, in both groups
    assert [t.get_text() for t in ax.get_xticklabels()] == ["Tmax (column)", "Tmean (all layers)"]
    assert ax.get_ylim()[0] == 0.0
    assert [t.get_text() for t in fig.legends[0].get_texts()] == ["FVM (reference)", "LPTN", "Analytic", "FDM"]
    assert ax.get_title().count("\n") == 1 and "reference FVM (hatched)" in ax.get_title()
    labels = sorted(t.get_text() for t in ax.texts)
    assert labels == sorted(f"{v:.1f}" for m in FOUR for v in (sim4.results[m].t_max, sim4.results[m].t_mean))
    assert all(t.get_rotation() == 90 for t in ax.texts)                       # written upright on the bars
    # the hatch colour is set on purpose, whatever the theme's text colour
    assert all(matplotlib.colors.same_color(b.get_hatchcolor(), "white") for b in hatched)
    # the colours are those of the models, so a model keeps its colour when another does not run
    by_label = {c.get_label(): c.patches[0].get_facecolor() for c in ax.containers}
    assert matplotlib.colors.same_color(by_label["LPTN"], model_color("lumped"))


def test_the_chart_with_the_lptn_as_reference_puts_it_first_and_hatches_it():
    sim = simulate(example_board(), SolverOptions(cell_mm=2.0, models=("lumped", "analytic")))
    fig = Figure(layout="constrained")
    plots.draw_comparison(fig, sim.results, "lumped")
    assert [t.get_text() for t in fig.legends[0].get_texts()] == ["LPTN (reference)", "Analytic"]
    assert "reference LPTN (hatched)" in fig.axes[0].get_title()


# ------------------------------------------------------------------ the two tables of the Models tab

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings, Qt                                      # noqa: E402

from pcbthermal.gui.document import Document                                  # noqa: E402
from pcbthermal.gui.main_window import MainWindow                             # noqa: E402
from pcbthermal.gui import results_view                                      # noqa: E402


def many_parts_board(n):
    """!
    @brief The example board with n parts (copies of U2 in a row, with long names for some).
    @param n Number of parts (at least 2).
    @return Problem.
    """
    p = example_board()
    for k in range(n - 2):
        p.add_heater(1, 0.5 + 0.1 * k, rect=(8 + 8 * (k % 9), 5 + 7 * (k // 9), 13 + 8 * (k % 9), 9 + 7 * (k // 9)), name=f"Q{k + 3} high side MOSFET switching" if k % 3 == 0 else f"R{k + 3}")
    return p


def show(qtbot, tmp_path, sim, size=(1200, 800), theme="dark"):
    """!
    @brief A MainWindow of the given size showing the Models tab of a simulation.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param sim Simulation to show.
    @param size Window size in px.
    @param theme Theme name.
    @return MainWindow.
    """
    s = QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat)
    s.setValue("theme", theme)
    win = MainWindow(Document(), s)
    qtbot.addWidget(win)
    win.resize(*size)
    win.show()
    win._load_problem(sim.problem, "t")
    win._on_done(sim)
    rv = win.results
    rv.tabs.setCurrentIndex(rv.tabs.indexOf(rv.compare))
    qtbot.wait(150)
    return win


def check_layout(tab, min_chart=results_view.MODELS_CHART_MIN_PX):
    """!
    @brief The layout rules of the Models tab: no sideways scroll, the tables not clipped, the chart at least min_chart px with its toolbar, equal columns in the two tables.
    @param tab ModelsTab.
    @param min_chart Least height of the chart box in px.
    """
    assert tab.area.horizontalScrollBar().maximum() == 0
    for t in (tab.table_max, tab.table_mean):
        assert t.horizontalScrollBar().maximum() == 0, "a table scrolls sideways"
        assert t.horizontalHeader().length() <= t.viewport().width()
        assert t.height() >= t.horizontalHeader().height() + sum(t.rowHeight(r) for r in range(t.rowCount())), "a table is clipped"
    assert tab.chart_box.height() >= min_chart and tab.canvas.height() > 100
    assert [tab.table_max.columnWidth(c) for c in range(tab.table_max.columnCount())] == [tab.table_mean.columnWidth(c) for c in range(tab.table_mean.columnCount())]
    assert tab.table_max.columnWidth(0) <= results_view.MODELS_FIRST_COLUMN_MAX_PX


@pytest.fixture(scope="module")
def sim6():
    """!
    @brief The example board in the six models at a 2 mm cell (the FEM needs pyamg only above small meshes).
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(cell_mm=2.0, models=("fvm", "lumped", "analytic", "fdm", "solid3d", "fem")))


def test_the_tables_hold_the_api_numbers_the_reference_first_in_bold_and_the_differences_in_the_tips(qtbot, tmp_path, sim6):
    win = show(qtbot, tmp_path, sim6)
    tab = win.results.compare
    cmp = sim6.part_comparison()
    assert tab.models_shown == ["fvm", "lumped", "analytic", "fdm", "solid3d", "fem"]
    heads = [tab.table_max.horizontalHeaderItem(c).text() for c in range(tab.table_max.columnCount())]
    assert heads == ["Part", "FVM (ref.)", "LPTN", "Analytic", "FDM", "3D solid", "FEM"]
    assert tab.table_max.horizontalHeaderItem(1).font().bold() and not tab.table_max.horizontalHeaderItem(2).font().bold()
    assert "hottest point under the part" in tab.title_max.text() and "mean under the part" in tab.title_mean.text()
    for table, key in ((tab.table_max, "t_max"), (tab.table_mean, "t_mean")):
        assert table.rowCount() == 2
        for r, part in enumerate(cmp["parts"]):
            for j, m in enumerate(cmp["models"]):
                cell = table.item(r, 1 + j)
                assert cell.text() == f"{part[key][m]:.1f}"                  # plain value, one decimal
                assert cell.font().bold() == (m == "fvm")
                assert cell.background().style() == Qt.NoBrush               # no colour
    tip = tab.table_max.item(0, 4).toolTip()
    d = cmp["parts"][0]["t_max_delta"]["fdm"]
    assert tip == f"FDM, max under U1 (column): {cmp['parts'][0]['t_max']['fdm']:.2f} °C, {d:+.2f} K vs FVM (reference)"
    assert "(reference)" in tab.table_max.item(0, 1).toolTip() and "K vs" not in tab.table_max.item(0, 1).toolTip()
    assert "single" not in tab.table_max.item(0, 2).toolTip() and "one node per part" in tab.table_mean.item(0, 2).toolTip() and "painted under the part" in tab.table_mean.item(0, 2).toolTip()
    assert tab.table_mean.item(0, 4).toolTip().startswith("FDM, mean under U1 (column): ")
    check_layout(tab)


def test_the_layout_at_1200_x_800_in_both_themes_with_two_and_many_parts(qtbot, tmp_path, sim6):
    for theme in ("dark", "light"):
        win = show(qtbot, tmp_path, sim6, theme=theme)
        tab = win.results.compare
        check_layout(tab)
        assert tab.area.verticalScrollBar().maximum() == 0                  # two parts: both tables whole, no scroll
        win.close()
    big = simulate(many_parts_board(12), SolverOptions(cell_mm=2.0, models=FOUR))
    win = show(qtbot, tmp_path, big)
    tab = win.results.compare
    check_layout(tab)
    assert tab.table_max.rowCount() == 12
    assert tab.area.verticalScrollBar().maximum() > 0                       # 12 parts: the two tables scroll together in their one area
    # the long names are cut at the first column's width and the whole name is the tooltip
    item = tab.table_max.item(2, 0)
    assert item.text().startswith("Q3 high side MOSFET switching") and "Q3 high side MOSFET switching" in item.toolTip() and tab.table_max.columnWidth(0) <= 120
    assert tab.table_max.textElideMode() == Qt.ElideRight


def test_the_layout_check_can_fail(qtbot, tmp_path, monkeypatch):
    # The check above must be able to fail: with no chart minimum and a tables area that asks for all its rows, the chart is squeezed (or the page overflows);
    # with a wide first column a table scrolls sideways
    big = simulate(many_parts_board(12), SolverOptions(cell_mm=2.0, models=FOUR))
    monkeypatch.setattr(results_view, "MODELS_CHART_MIN_PX", 100)
    monkeypatch.setattr(results_view, "MODELS_TABLES_MAX_PX", 5000)
    win = show(qtbot, tmp_path, big)
    with pytest.raises(AssertionError):
        check_layout(win.results.compare, min_chart=280)
    win.close()
    monkeypatch.setattr(results_view, "MODELS_CHART_MIN_PX", 280)
    monkeypatch.setattr(results_view, "MODELS_TABLES_MAX_PX", 300)
    five = simulate(many_parts_board(12), SolverOptions(cell_mm=2.0, models=FOUR + ("solid3d",)))
    win = show(qtbot, tmp_path, five)
    check_layout(win.results.compare)                                      # the real values hold with five models and long names
    win.close()
    monkeypatch.setattr(results_view, "MODELS_FIRST_COLUMN_MAX_PX", 400)
    win = show(qtbot, tmp_path, five)
    with pytest.raises(AssertionError):
        check_layout(win.results.compare)


def test_one_model_one_column_lptn_reference_no_part_and_clear(qtbot, tmp_path):
    one = simulate(example_board(), SolverOptions(cell_mm=2.0, models=("fvm",)))
    win = show(qtbot, tmp_path, one)
    tab = win.results.compare
    assert tab.table_max.columnCount() == 2 and tab.table_max.horizontalHeaderItem(1).text() == "FVM (ref.)"
    check_layout(tab)
    lp = simulate(example_board(), SolverOptions(cell_mm=2.0, models=("lumped", "analytic")))
    win.results.set_simulation(lp)
    assert tab.table_max.horizontalHeaderItem(1).text() == "LPTN (ref.)" and tab.table_max.horizontalHeaderItem(2).text() == "Analytic"
    assert "vs LPTN (reference)" in tab.table_max.item(0, 2).toolTip()
    # no part: tables with their headers and no row, and a message
    nopart = copy.copy(lp)
    nopart.problem = copy.deepcopy(lp.problem)
    nopart.problem.heaters = []
    win.results.set_simulation(nopart)
    assert tab.table_max.rowCount() == 0 and tab.table_mean.rowCount() == 0 and not tab.message.isHidden() and "no part" in tab.message.text()
    win.results.set_simulation(lp)
    assert tab.message.isHidden() and tab.table_max.rowCount() == 2
    win.results.clear()
    assert tab.table_max.rowCount() == 0 and tab.table_max.columnCount() == 1 and tab.models_shown == []


def test_a_window_narrower_than_1200_px_lets_the_tables_scroll_sideways_inside_the_page(qtbot, tmp_path, sim6):
    # Below 1200 px the six columns no longer fit: each table must keep its own sideways bar inside the page (the area has none), never be cut at the right
    for width in (1100, 900):
        win = show(qtbot, tmp_path, sim6, size=(width, 800))
        tab = win.results.compare
        view = tab.area.viewport().width()
        for t in (tab.table_max, tab.table_mean):
            assert t.horizontalScrollBar().maximum() > 0, "six columns fit a narrow page?"
            assert t.mapTo(tab.area.viewport(), t.rect().topRight()).x() < view, "a table is cut at the right of the page"
            assert t.viewport().height() >= sum(t.rowHeight(r) for r in range(t.rowCount())), "the sideways bar covers a row"
        win.close()
