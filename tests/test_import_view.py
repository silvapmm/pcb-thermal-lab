#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_import_view.py
@brief The imported board in the views: the copper pattern and the part names on the editor canvas (View - Imported copper, Element names), and the designators, hover,
       hole legend and fitting table of step 2 of the import window.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import resource
import time

import numpy as np
import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QPoint, QPointF, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QCheckBox

from pcbthermal import copper
from pcbthermal.gui import import_session as ims
from pcbthermal.gui.canvas import BoardView, reduced_coverage
from pcbthermal.gui.document import Document
from pcbthermal.gui.import_window import ImportBoardWindow
from pcbthermal.gui.main_window import MainWindow
from tests.helpers.synthetic_board import make_board

REAL = os.environ.get("PCBT_REAL_BOARDS", "")


def _imported(qtbot, tmp_path, powers=("U1", "Q1")):
    """!
    @brief Run the synthetic board through the import window and return the window after the import.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param powers Designators that get 1 W (they become heaters).
    @return ImportBoardWindow
    """
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.show()
    w.confirm = lambda *a: True
    w.notify = lambda title, text: pytest.fail(f"{title}: {text}")
    w.open_path(str(make_board(tmp_path / "fab", inner=0)))
    w.go(1)
    for d in powers:
        w.session.set_part(d, power=1.0)
    w.go(2)
    assert w.do_import() is True
    return w


@pytest.fixture
def imported_doc(qtbot, tmp_path):
    """!
    @brief A Document that holds the imported synthetic board.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return Document
    """
    w = _imported(qtbot, tmp_path)
    doc = Document()
    doc.open_import(w.problem, w.record)
    return doc


def test_the_canvas_draws_the_imported_copper_of_the_active_layer(qtbot, imported_doc):
    view = BoardView(imported_doc, "dark")
    qtbot.addWidget(view)
    assert view._copper_item is not None and view._copper_item.zValue() < 1       # under the elements
    first = view._copper_item.pixmap().toImage()
    view.set_layer(1)                                           # the bottom layer: another mask
    assert view._copper_item is not None and view._copper_item.pixmap().toImage() != first
    view.set_show_imported_copper(False)
    assert view._copper_item is None
    view.set_show_imported_copper(True)
    assert view._copper_item is not None


def test_a_drawn_board_has_no_copper_image(qtbot):
    from pcbthermal.examples import example_board
    doc = Document()
    doc.open_problem(example_board(), "example")
    view = BoardView(doc, "dark")
    qtbot.addWidget(view)
    assert view._copper_item is None


def test_the_copper_image_is_cached_and_follows_the_theme(qtbot, imported_doc):
    view = BoardView(imported_doc, "dark")
    qtbot.addWidget(view)
    pm = view._copper_item.pixmap()
    view.rebuild()
    assert view._copper_item.pixmap().cacheKey() == pm.cacheKey()                  # the same pixmap, not built again
    view.set_theme("light")
    assert view._copper_item.pixmap().cacheKey() != pm.cacheKey()


def test_the_view_menu_has_the_two_switches(qtbot, tmp_path, imported_doc):
    win = MainWindow(imported_doc, QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(win)
    assert win.a_imported.isChecked() and win.a_labels.isChecked() and win.a_imported.toolTip() and win.a_labels.toolTip()
    win.a_imported.setChecked(False)
    assert win.canvas._copper_item is None
    win.a_imported.setChecked(True)
    assert win.canvas._copper_item is not None
    win.a_labels.setChecked(False)
    assert all(it.label is None for it in win.canvas.scene().items() if hasattr(it, "label") and getattr(it, "kind", "") == "heater")


def test_part_names_that_do_not_fit_wait_for_the_zoom(qtbot, imported_doc):
    view = BoardView(imported_doc, "dark")
    qtbot.addWidget(view)
    view.resize(700, 500)
    view.show()
    view.fit()
    heaters = [it for it in view.scene().items() if getattr(it, "kind", "") == "heater" and it.label is not None]
    assert len(heaters) == 2
    view.zoom(40.0)
    assert all(it.label.isVisible() for it in heaters if it.boundingRect().width() * abs(view.transform().m11()) > 60)
    view.zoom(1 / 4000.0)
    assert not any(it.label.isVisible() for it in heaters)


def test_a_huge_mask_is_drawn_from_a_reduced_copy_quickly_and_lightly():
    big = np.zeros((3300, 3300), np.uint8)                       # CO60 has 10.8 Mpx per layer
    big[::7, :] = 255
    t0 = time.perf_counter()
    red, f = reduced_coverage(big)
    assert time.perf_counter() - t0 < 1.0 and f == 2 and red.shape == (1650, 1650)
    assert abs(float(red.mean()) - float(big[:3300, :3300].mean())) < 1.0          # the mean coverage is kept
    assert max(reduced_coverage(np.zeros((100, 100), np.uint8))[0].shape) == 100


@pytest.mark.skipif(not REAL or not os.path.isdir(os.path.join(REAL, "co60")), reason="PCBT_REAL_BOARDS does not point to the real boards")
def test_the_co60_canvas_is_fast_and_light(qtbot):
    sx = ims.ImportSession()
    sx.set_files(os.path.join(REAL, "co60"))
    sx.load()
    sx.pixel_mm = sx.auto_pixel() / 2.0                          # twice as fine as the automatic pixel: about 10.8 Mpx per layer
    prob = sx.build_problem()
    doc = Document()
    doc.open_import(prob, sx.record)
    mask = doc.problem.imported.layers[0]["mask"]
    rows, cols = mask["shape"]
    copper.unpack_coverage(mask)                                 # the models keep this array anyway; only the canvas' own cost is measured
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    t0 = time.perf_counter()
    view = BoardView(doc, "dark")
    qtbot.addWidget(view)
    spent = time.perf_counter() - t0
    assert view._copper_item is not None and max(view._copper_item.pixmap().width(), view._copper_item.pixmap().height()) <= 2048
    # ru_maxrss is bytes on macOS and kilobytes on Linux
    grew = (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - before) * (1.0 if os.uname().sysname == "Darwin" else 1024.0)
    print(f"co60 mask {rows} x {cols} = {rows * cols / 1e6:.1f} Mpx: canvas {spent:.2f} s, +{grew / 1e6:.0f} MB")
    assert spent < 1.0 and grew < 100e6


# ---------------------------------------------------------------------------------------------------------------------------------- step 2 of the import window
def _step2(qtbot, tmp_path, width=1280):
    """!
    @brief The import window of the synthetic board on step 2.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @param width Window width in pixels.
    @return ImportBoardWindow
    """
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.resize(width, 820)
    w.show()
    w.confirm = lambda *a: True
    w.notify = lambda title, text: pytest.fail(f"{title}: {text}")
    w.open_path(str(make_board(tmp_path / "fab", inner=0)))
    w.go(1)
    return w


def _centre(sx, des):
    """!
    @brief The centre of the heat-source polygon of a part (mm, Gerber frame).
    @param sx ImportSession.
    @param des Designator.
    @return tuple (x, y)
    """
    poly = sx.part(des).polygon_mm
    return sum(q[0] for q in poly) / len(poly), sum(q[1] for q in poly) / len(poly)


def test_every_matched_part_gets_a_label_and_the_toggle_removes_them(qtbot, tmp_path):
    w = _step2(qtbot, tmp_path)
    pv = w.page2.preview
    pv.resize(900, 700)
    pv.zoom = 3.0
    pv.update()
    on = pv.grab().toImage()
    pv.show_layers["labels"] = False
    off = pv.grab().toImage()
    assert on != off
    # The pixel size of the label grows with the zoom and a part that is too small for its text has none
    assert pv.label_pixels("U1", 16, 30) > pv.label_pixels("U1", 12, 30) and pv.label_pixels("U1", 5, 30) is None and pv.label_pixels("U1", 40, 3) is None
    boxes = {c.text(): c for c in w.page2.findChildren(QCheckBox)}
    assert "Labels" in boxes and "Holes" in boxes and boxes["Labels"].toolTip() and boxes["Holes"].toolTip()
    boxes["Labels"].setChecked(False)
    assert pv.show_layers["labels"] is False


def test_the_hole_legend_counts_vias_and_component_holes(qtbot, tmp_path):
    w = _step2(qtbot, tmp_path)
    pv = w.page2.preview
    classes = pv.hole_classes()
    assert sorted((k, d, n) for k, d, n in classes) == [("component hole", 3.0, 1), ("via", 0.3, 2)]
    pv.resize(900, 700)
    with_legend = pv.grab().toImage()
    pv.show_layers["holes"] = False
    assert pv.grab().toImage() != with_legend


def test_hovering_a_part_names_it_and_a_click_selects_its_row(qtbot, tmp_path):
    w = _step2(qtbot, tmp_path)
    sx, pg = w.session, w.page2
    des = next(p.designator for p in sx.parts() if p.polygon_mm and p.side == "top")
    x, y = _centre(sx, des)
    text = pg.preview.hover_text(x, y)
    assert text.startswith(des) and "Package:" in text and "Source:" in text and "Power:" in text
    assert pg.preview.hover_text(-500.0, -500.0) is None
    pg.preview.resize(900, 700)
    pt = pg.preview.to_px(x, y)
    QTest.mouseClick(pg.preview, Qt.LeftButton, pos=QPoint(int(pt.x()), int(pt.y())))
    assert pg.selected == des and pg.table.item(pg.table.currentRow(), 1).text() == des and pg.preview.selected_part == des
    # The reverse: a row of the table highlights its part in the preview
    other = next(p.designator for p in sx.parts() if p.polygon_mm and p.designator != des)
    row = next(r for r in range(pg.table.rowCount()) if pg.table.item(r, 1).text() == other)
    pg.table.selectRow(row)
    assert pg.preview.selected_part == other
    # A hole says what it is
    h = sx.board().holes[0]
    assert "drill" in pg.preview.hover_text(h.x, h.y)


@pytest.mark.parametrize("width", [1480, 1100, 800])
def test_the_parts_table_fits_the_window(qtbot, tmp_path, width):
    w = _step2(qtbot, tmp_path, width)
    t = w.page2.table
    qtbot.wait(50)
    hh = t.horizontalHeader()
    last = t.columnCount() - 1
    needed = hh.sectionPosition(last) + hh.sectionSize(last)
    print(f"width {width}: table viewport {t.viewport().width()} px, columns need {needed} px, scroll maximum {t.horizontalScrollBar().maximum()}")
    if width >= 1100:
        assert t.horizontalScrollBar().maximum() == 0 and needed <= t.viewport().width() + 1
    assert "(W)" in t.horizontalHeaderItem(7).text() and "\n" in t.horizontalHeaderItem(7).text()


def test_the_by_position_wording_says_what_to_check(qtbot, tmp_path):
    w = _step2(qtbot, tmp_path)
    sx = w.session
    q = sx.parts()[0]
    q.from_file = dict(q.from_file, source="placement by position")      # the synthetic paste file names its parts, so make one a by-position part
    assert sx.source_label(q) == "by position (approx.)"
    tip = sx.source_explanation(q)
    assert "0.3 mm" in tip and "package" in tip and "preview" in tip


@pytest.mark.skipif(not REAL or not os.path.isdir(os.path.join(REAL, "rp2040")), reason="PCBT_REAL_BOARDS does not point to the real boards")
def test_the_rp2040_step_two_warning_and_table(qtbot):
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.resize(1100, 820)
    w.show()
    w.confirm = lambda *a: True
    w.open_path(os.path.join(REAL, "rp2040"))
    w.go(1)
    sx = w.session
    assert any("names no parts" in x and "0.3 mm" in x and "check" in x for x in sx.parts_warnings())
    assert "by position" in w.page2.warn.text()
    t = w.page2.table
    qtbot.wait(100)
    assert t.horizontalScrollBar().maximum() == 0                      # 30 parts with real package names, still no scroll bar at 1100 px
    pv = w.page2.preview
    pv.resize(900, 700)
    des = [p.designator for p in sx.parts() if p.polygon_mm and p.side == "top"]
    assert len(des) >= 20 and pv.hole_classes()
