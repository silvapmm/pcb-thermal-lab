#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_surface_export_gui.py
@brief The export entries and the tables of the window: Export results to a folder writes the surface and the table files, the Components tables carry the surface (and, for the
       FEM, the node value) beside the column read-out, the card of the map on the board names its read-out, and the Difference view's Export statistics button writes its CSV.
"""

import csv
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QSettings

from pcbthermal import compare
from pcbthermal.api import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import TAB_RESULTS, MainWindow

MODELS = ("fvm", "lumped", "analytic", "fdm", "solid3d", "fem")


@pytest.fixture(scope="module")
def sim():
    """!
    @brief The example board in every model at a coarse cell, with a hotspot limit low enough to have hotspots.
    @return Simulation.
    """
    return simulate(example_board(), SolverOptions(models=MODELS, cell_mm=2.0, hotspot_c=40.0))


@pytest.fixture
def win(qtbot, tmp_path, sim):
    """!
    @brief A window with the example board and the simulation shown (light theme).
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


def test_export_results_writes_surface_and_tables(win, tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr("pcbthermal.gui.main_window.QFileDialog.getExistingDirectory", lambda *a, **k: str(out))
    win.export_results()
    names = {p.name for p in out.iterdir()}
    for m in ("fvm", "fdm", "analytic", "solid3d", "fem"):
        assert f"surface_{m}.csv" in names and f"surface_{m}_top.png" in names, m
    assert "surface_lumped.csv" not in names                         # the Lumped has no surface read-out
    assert {"field_fvm.csv", "hotspots_fvm.csv", "parts_fvm.csv", "report.txt", "summary.json"} <= names
    with open(out / "hotspots_fvm.csv", newline="") as fh:
        head = next(csv.reader(fh))
    assert "T_max_column_c" in head and "T_max_surface_c" in head


def test_components_tables_carry_the_surface_beside_the_column(win):
    rv = win.results
    rv._fill_components()
    z = [rv.zone_table.horizontalHeaderItem(c).text() for c in range(rv.zone_table.columnCount())]
    h = [rv.hot_table.horizontalHeaderItem(c).text() for c in range(rv.hot_table.columnCount())]
    # The FVM is the reference: the old columns first and unchanged, the surface appended; the FEM node value is only for a FEM reference
    assert z[:5] == ["Zone", "Layer", "Mean °C\n(column)", "Max °C\n(column)", "Min °C\n(column)"] and z[5] == "Max °C\n(surface)" and len(z) == 6
    assert h[:6] == ["Hotspot", "Layer", "Tmax °C\n(column)", "x mm", "y mm", "Area mm²"] and h[6] == "Tmax °C\n(surface)" and len(h) == 7
    assert rv.hot_table.item(0, 6).text() not in ("", "n/a")          # the hottest hotspot is on the top layer: it has a surface value
    # an inner layer has no surface: n/a, and the cell says why
    inner = [r for r in range(rv.zone_table.rowCount()) if rv.zone_table.item(r, 1).text() == "2"]
    assert inner and rv.zone_table.item(inner[0], 5).text() == "n/a" and "Inner copper layer" in rv.zone_table.item(inner[0], 5).toolTip()


def test_a_fem_reference_adds_the_point_column(win, sim):
    rv = win.results
    fem_only = simulate(example_board(), SolverOptions(models=("fem",), cell_mm=2.0, hotspot_c=40.0))
    rv.sim = fem_only
    rv._fill_components()
    h = [rv.hot_table.horizontalHeaderItem(c).text() for c in range(rv.hot_table.columnCount())]
    assert h[-1] == "Node °C\n(point)" and h[-2] == "Tmax °C\n(surface)"
    assert float(rv.hot_table.item(0, 7).text()) > float(rv.hot_table.item(0, 2).text()) - 0.1


def test_the_card_of_the_map_names_the_readout(win):
    # The card paints "max .. °C (column)": the texts the painter is given (review: the first version only checked that it paints)
    win.a_overlay.setChecked(True)
    card = win.canvas._overlay_card
    assert card is not None and card["tmax"] is not None
    texts = win.canvas.overlay_card_texts(card)
    assert len(texts) == 2 and texts[0].startswith("max ") and texts[1].startswith("min ") and all(t.endswith("°C (column)") for t in texts)
    assert texts[0].split()[1] == f"{round(card['tmax'], 1):.1f}" or texts[0].split()[1].replace(",", ".") == f"{round(card['tmax'], 1):g}"
    assert win.canvas.overlay_card_texts({"title": "x", "tmax": None, "tmin": None}) == []
    win.canvas.viewport().grab()                                      # painting with the new text does not raise


def test_difference_export_button_and_file(win, tmp_path, monkeypatch):
    t = win.results.temp
    assert not t.diff_export.isVisibleTo(t)
    assert t.export_difference_statistics(str(tmp_path / "none.csv")) is None and not (tmp_path / "none.csv").exists()
    t.model.setCurrentIndex(t.model.findData("fdm"))
    t.diff_on.setChecked(True)
    assert t.diff_export.isVisibleTo(t) and t.diff_export.toolTip()
    target = tmp_path / "diff.csv"
    monkeypatch.setattr("pcbthermal.gui.results_view.QFileDialog.getSaveFileName", lambda *a, **k: (str(target), "CSV files (*.csv)"))
    t.diff_export.click()
    with open(target, newline="") as fh:
        rows = list(csv.reader(fh))
    row = dict(zip(rows[0], rows[1]))
    assert rows[0] == compare.STATISTICS_HEADER and row["model"] == "FDM" and row["reference"] == "FVM"
    d = t._diff_last[0]
    assert float(row["max_k"]) == pytest.approx(d.maximum, abs=1e-6) and float(row["cell_mm"]) == 2.0
    assert row["verdict"].startswith("Not judged at 2 mm cells")          # a run at another cell than the tables gets no verdict
    t.diff_on.setChecked(False)
    assert not t.diff_export.isVisibleTo(t)


def test_cancelled_dialog_writes_nothing(win, tmp_path, monkeypatch):
    t = win.results.temp
    t.model.setCurrentIndex(t.model.findData("fdm"))
    t.diff_on.setChecked(True)
    monkeypatch.setattr("pcbthermal.gui.results_view.QFileDialog.getSaveFileName", lambda *a, **k: ("", ""))
    assert t.export_difference_statistics() is None
