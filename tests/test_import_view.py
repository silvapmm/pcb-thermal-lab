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
from PySide6.QtGui import QMouseEvent

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
    b = sx.load()
    cov = b.copper[0][2]
    assert cov.size > 5e6
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    t0 = time.perf_counter()
    red, f = reduced_coverage(cov)
    assert time.perf_counter() - t0 < 1.0 and max(red.shape) <= 2048
    # ru_maxrss is bytes on macOS and kilobytes on Linux; the reduction itself must add well under 100 MB
    grew = (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - before) / (1.0 if os.uname().sysname == "Darwin" else 1024.0)
    assert grew < 100e6
