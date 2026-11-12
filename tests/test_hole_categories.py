#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_hole_categories.py
@brief The three kinds of hole of an import (via, component hole, non-plated hole or slot): what the record stores, that a project with them round-trips, that the re-import
       tests the kind "via" positively, and that the editor draws them with one item per kind (display only: no number moves).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import copy
import time

import numpy as np
import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QPointF, QSettings

from pcbthermal.gui.canvas import BoardView, ViaItem
from pcbthermal.gui.document import Document
from pcbthermal.gui.import_session import carry_over
from pcbthermal.gui.import_window import ImportBoardWindow
from pcbthermal.gui.main_window import MainWindow
from pcbthermal.project import project_from_dict, project_to_dict
from tests.helpers.synthetic_board import make_board

# A non-plated drill file: two round holes and a routed slot of 4 mm (X2 function NonPlated)
NPTH = ("M48\n; #@! TF.FileFunction,NonPlated,1,2,NPTH\nMETRIC,TZ\nT1C1.200\nT2C0.800\n%\nT1\nX5.0Y25.0\nX35.0Y25.0\n"
        "T2\nG00X10.0Y27.0\nM15\nG01X14.0Y27.0\nM16\nM30\n")


def _imported(qtbot, tmp_path):
    """!
    @brief Import the synthetic board with a non-plated drill file added.
    @param qtbot pytest-qt fixture.
    @param tmp_path Temporary folder.
    @return ImportBoardWindow after the import.
    """
    folder = make_board(tmp_path / "fab", inner=0)
    (folder / "npth.drl").write_text(NPTH)
    w = ImportBoardWindow()
    qtbot.addWidget(w)
    w.show()
    w.confirm = lambda *a: True
    w.notify = lambda title, text: pytest.fail(f"{title}: {text}")
    w.open_path(str(folder))
    w.go(1)
    w.session.set_part("U1", power=1.0)
    w.go(2)
    assert w.do_import() is True
    return w


def _kinds(record):
    """!
    @brief Count the holes of a record per kind.
    @param record model.ImportRecord.
    @return dict kind -> count.
    """
    out = {}
    for h in record.holes:
        out[h["kind"]] = out.get(h["kind"], 0) + 1
    return out


def test_the_record_stores_the_three_kinds_and_the_slot_length(qtbot, tmp_path):
    w = _imported(qtbot, tmp_path)
    assert _kinds(w.record) == {"via": 2, "component": 1, "nonplated": 3}
    slot = next(h for h in w.record.holes if "length_mm" in h)
    assert slot["kind"] == "nonplated" and slot["length_mm"] == pytest.approx(4.0) and slot["d_mm"] == pytest.approx(0.8)
    assert (slot["x2_mm"] - slot["x_mm"], slot["y2_mm"] - slot["y_mm"]) == pytest.approx((4.0, 0.0))
    # Display only: the problem has the two vias and nothing for the other holes
    assert len(w.problem.vias) == 2


def test_the_record_round_trips_through_the_project_file(qtbot, tmp_path):
    w = _imported(qtbot, tmp_path)
    doc = Document()
    doc.open_import(w.problem, w.record)
    d = project_to_dict(doc.project)
    again = project_from_dict(copy.deepcopy(d))
    assert again.imports[0].holes == w.record.holes
    assert project_to_dict(again) == d


def test_the_reimport_merge_tests_the_kind_via_positively(qtbot, tmp_path):
    w = _imported(qtbot, tmp_path)
    old = copy.deepcopy(w.problem)
    # A hand-drawn via exactly on a non-plated hole and one on a component hole: neither is an imported via, so both are carried over as hand-drawn
    npth = next(h for h in w.record.holes if h["kind"] == "nonplated" and "length_mm" not in h)
    comp = next(h for h in w.record.holes if h["kind"] == "component")
    old.add_via(npth["x_mm"], npth["y_mm"], 0.3)
    old.add_via(comp["x_mm"], comp["y_mm"], 0.3)
    new = copy.deepcopy(w.problem)
    assert len(new.vias) == 2
    carry_over(old, w.record, new, copy.deepcopy(w.record))
    assert len(new.vias) == 4


def test_the_editor_draws_one_item_per_kind(qtbot, tmp_path):
    w = _imported(qtbot, tmp_path)
    doc = Document()
    doc.open_import(w.problem, w.record)
    view = BoardView(doc, "dark")
    qtbot.addWidget(view)
    assert set(view._hole_items) == {"component", "nonplated"}
    assert view.hole_counts() == {"via": 2, "component": 1, "nonplated": 3}
    for it in view._hole_items.values():
        assert not it.flags() & it.GraphicsItemFlag.ItemIsSelectable and it.zValue() < 4
    view.set_show_holes("nonplated", False)
    assert not view._hole_items["nonplated"].isVisible() and view._hole_items["component"].isVisible()
    view.set_show_holes("via", False)
    assert not any(it.isVisible() for it in view.scene().items() if isinstance(it, ViaItem))
    view.set_show_holes("via", True)
    # A rebuild keeps the choice
    view.set_show_holes("component", False)
    view.rebuild()
    assert not view._hole_items["component"].isVisible()
    comp = next(h for h in w.record.holes if h["kind"] == "component")
    assert view.hole_at(QPointF(comp["x_mm"], comp["y_mm"])) == ""            # hidden: no hover text
    view.set_show_holes("component", True)
    assert "Component hole, 3 mm" in view.hole_at(QPointF(comp["x_mm"], comp["y_mm"]))
    view.set_show_holes("nonplated", True)
    slot = next(h for h in w.record.holes if "length_mm" in h)
    assert "slot" in view.hole_at(QPointF(slot["x_mm"], slot["y_mm"]))
    assert view.hole_at(QPointF(-50.0, -50.0)) == ""


def test_a_drawn_board_has_no_hole_items(qtbot):
    from pcbthermal.examples import example_board
    doc = Document()
    doc.open_problem(example_board(), "example")
    view = BoardView(doc, "dark")
    qtbot.addWidget(view)
    assert view._hole_items == {} and view.hole_counts() == {"via": len(doc.problem.vias), "component": 0, "nonplated": 0}


def test_eight_hundred_holes_are_two_items_and_stay_fast(qtbot, tmp_path):
    w = _imported(qtbot, tmp_path)
    rec = copy.deepcopy(w.record)
    rng = np.random.default_rng(1)
    for k in range(800):
        rec.holes.append({"x_mm": float(rng.uniform(0, 40)), "y_mm": float(rng.uniform(0, 30)), "d_mm": 1.0, "kind": "component" if k % 2 else "nonplated"})
    doc = Document()
    doc.open_import(w.problem, rec)
    view = BoardView(doc, "dark")
    qtbot.addWidget(view)
    assert len(view._hole_items) == 2
    t0 = time.perf_counter()
    for _ in range(5):
        view.rebuild()
    per_rebuild = (time.perf_counter() - t0) / 5
    t0 = time.perf_counter()
    view.grab()
    paint = time.perf_counter() - t0
    print(f"800 holes: rebuild {per_rebuild * 1e3:.1f} ms, paint {paint * 1e3:.1f} ms")
    assert per_rebuild < 0.5 and paint < 1.0, (per_rebuild, paint)


def test_the_view_menu_remembers_the_choice_and_counts_in_the_tooltip(qtbot, tmp_path):
    s = QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat)
    win = MainWindow(settings=s)
    qtbot.addWidget(win)
    assert set(win.a_holes) == {"via", "component", "nonplated"} and all(a.isChecked() for a in win.a_holes.values())
    win.a_holes["nonplated"].setChecked(False)
    assert win.canvas.show_holes["nonplated"] is False
    win2 = MainWindow(settings=s)
    qtbot.addWidget(win2)
    assert win2.a_holes["nonplated"].isChecked() is False and win2.canvas.show_holes["nonplated"] is False
    assert "0 on this board" in win2.a_holes["component"].toolTip()


def test_the_import_preview_and_the_editor_use_the_same_tones():
    from pcbthermal.gui import theme as th
    assert th.HOLE_TONE == {"via": "via", "component": "warn", "nonplated": "muted"}
    for name in ("dark", "light"):
        assert all(t in th.colors(name) for t in th.HOLE_TONE.values())
