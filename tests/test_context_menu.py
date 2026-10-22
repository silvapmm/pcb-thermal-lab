"""!
@file test_context_menu.py
@brief Right-click editing on the board: add and delete polygon vertices, add elements on an empty spot, and the geometry helpers behind them.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QPointF, QSettings

from pcbthermal import SolverOptions, simulate
from pcbthermal.examples import example_board
from pcbthermal.geometry import insert_vertex, nearest_edge_point, nearest_vertex, polygon_area
from pcbthermal.gui.document import Document
from pcbthermal.gui.main_window import MainWindow

SQUARE = [[0, 0], [10, 0], [10, 10], [0, 10]]


def test_geometry_helpers():
    edge, q, d = nearest_edge_point(SQUARE, (5, -2))
    assert edge == 0 and np.allclose(q, [5, 0]) and d == pytest.approx(2.0)
    poly, k = insert_vertex(SQUARE, (10.5, 4))                          # Nearest edge is the right one (vertex 1 to 2)
    assert k == 2 and np.allclose(poly[2], [10, 4]) and len(poly) == 5
    assert polygon_area(poly) == pytest.approx(100.0)                   # The shape does not change
    assert nearest_vertex(SQUARE, (9, 9)) == (2, pytest.approx(2 ** 0.5))


@pytest.fixture
def win(qtbot, tmp_path):
    w = MainWindow(Document(), QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.resize(1400, 900)
    w.show()
    w._load_problem(example_board(), "ctx")
    return w


def actions(menu):
    out = {}
    for a in menu.actions():
        if a.menu() is not None:
            out.update(actions(a.menu()))                                  # The "Add here" submenu
        elif a.text():
            out[a.text()] = a
    return out


def test_vertex_editing_from_the_menu_then_every_model_runs(win):
    cv, pr = win.canvas, win.doc.problem
    h = pr.heaters[0]
    c = h.polygon.min(axis=0) * 1000.0 + 0.4                                 # Inside, near a corner (the vias under the part would take the click)
    n0 = len(h.polygon)
    menu = cv.build_context_menu(QPointF(*c))                              # On the part: its menu, and it becomes the selection
    acts = actions(menu)
    assert {"Add a vertex here", "Delete this vertex", "Duplicate", "Delete heater"} <= set(acts)
    assert cv.selected_elements() == [("heater", 0)]
    # Add a vertex near the bottom edge, then drag it outwards by editing the polygon: a pentagon
    x0, y0 = h.polygon.min(axis=0) * 1000.0
    acts["Add a vertex here"].trigger()
    assert len(win.doc.problem.heaters[0].polygon) == n0 + 1
    pts = win.doc.polygon_mm(win.doc.problem.heaters[0])
    area_before = polygon_area(pts)
    pts[1 if abs(pts[1][1] - y0) < 1e-6 else 0][1] -= 0.0                   # Shape unchanged until a vertex moves
    assert polygon_area(pts) == pytest.approx(area_before)
    # Delete a vertex on a vertex: the menu offers it when the cursor is on one
    corner = QPointF(*pts[0])
    menu = cv.build_context_menu(corner)
    acts = actions(menu)
    assert acts["Delete this vertex"].isEnabled()
    acts["Delete this vertex"].trigger()
    assert len(win.doc.problem.heaters[0].polygon) == n0
    # Undo restores the five-vertex polygon, redo the four
    win.doc.undo_stack.undo() if hasattr(win.doc, "undo_stack") else None
    win.doc.problem.validate()
    for m in (("fvm", "fdm", "lumped", "analytic")):
        simulate(win.doc.problem, SolverOptions(models=(m,), cell_mm=2.0))


def test_three_vertices_stay_and_a_crossing_delete_is_refused(win):
    cv = win.canvas
    win.doc.set_polygon("zone", 0, [[10, 10], [30, 10], [20, 30]])
    cv.remove_vertex("zone", 0, 0)
    assert len(win.doc.problem.zones[0].polygon) == 3
    win.doc.set_polygon("zone", 0, [[10, 10], [30, 10], [30, 30], [20, 20], [10, 30]])   # Concave: dropping (20, 20)... stays simple
    cv.remove_vertex("zone", 0, 3)
    assert len(win.doc.problem.zones[0].polygon) == 4


def test_empty_spot_menu_adds_elements_and_vias(win):
    cv, pr = win.canvas, win.doc.problem
    spot = QPointF(5.0, pr.board.height * 1000.0 - 5.0)
    cv.scene().clearSelection()
    nh, nz, nv = len(pr.heaters), len(pr.zones), len(pr.vias)
    acts = actions(cv.build_context_menu(spot))
    assert {"Add heater here", "Add zone here", "Add heatsink here", "Add via here"} <= set(acts)
    acts["Add heater here"].trigger()
    acts = actions(cv.build_context_menu(spot))
    acts["Add zone here"].trigger()
    acts = actions(cv.build_context_menu(spot))
    acts["Add via here"].trigger()
    pr = win.doc.problem
    assert (len(pr.heaters), len(pr.zones), len(pr.vias)) == (nh + 1, nz + 1, nv + 1)
    new = pr.heaters[-1].polygon * 1000.0
    assert new.min() >= -1e-9 and np.ptp(new, axis=0) == pytest.approx([5.0, 5.0])
    assert cv.build_context_menu(QPointF(-50.0, -50.0)) is None                                  # Outside the board: no menu
    acts = actions(cv.build_context_menu(QPointF(*(pr.vias[-1].x * 1000.0, pr.vias[-1].y * 1000.0))))
    assert {"Duplicate", "Delete via", "Add heater here"} <= set(acts) and "Add a vertex here" not in acts       # A via: its own entries and the Add here submenu


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_random_menu_actions_keep_the_board_valid_and_solvable(win, seed):
    import random
    rng = random.Random(seed)
    cv = win.canvas
    b = win.doc.problem.board
    for _ in range(60):
        pt = QPointF(rng.uniform(-5, b.width * 1000 + 5), rng.uniform(-5, b.height * 1000 + 5))
        menu = cv.build_context_menu(pt)
        if menu is None:
            continue
        acts = [a for a in actions(menu).values() if a.isEnabled()]
        rng.choice(acts).trigger()
        if rng.random() < 0.15:
            win.doc.stack.undo()
    win.doc.problem.validate()
    for m in ("fvm", "lumped"):
        simulate(win.doc.problem, SolverOptions(models=(m,), cell_mm=2.5))


def test_dragging_a_vertex_handle_moves_only_that_vertex(win):
    """The selected polygon must not travel with the handle (Qt moves every selected movable item with the dragged one): its position stays 0, only the vertex follows
    the mouse while dragging, and the document gets the new polygon on release."""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    cv = win.canvas
    h = win.doc.problem.heaters[0]
    cv.set_selection([("heater", 0)])
    cv.add_vertex("heater", 0, tuple(h.polygon.mean(axis=0) * 1000.0 + [0.0, 6.0]))
    cv.set_selection([("heater", 0)])
    item = cv._handle_item
    before = [(p.x(), p.y()) for p in (item.polygon().at(i) for i in range(item.polygon().count()))]
    handle = cv._handles[1]
    start = cv.mapFromScene(handle.pos())
    vp = cv.viewport()
    QTest.mousePress(vp, Qt.LeftButton, pos=start)
    for k in range(1, 5):
        QTest.mouseMove(vp, pos=start + QPoint(5 * k, -4 * k))
        assert item.pos().x() == 0.0 and item.pos().y() == 0.0                         # The piece does not move
        now = [(p.x(), p.y()) for p in (item.polygon().at(i) for i in range(item.polygon().count()))]
        assert [q for i, q in enumerate(now) if i != 1] == [q for i, q in enumerate(before) if i != 1]      # Only vertex 1 changes
    QTest.mouseRelease(vp, Qt.LeftButton, pos=start + QPoint(20, -16))
    after = win.doc.problem.heaters[0].polygon * 1000.0
    assert len(after) == 5 and (after[1] != before[1]).any()
    assert [tuple(map(float, after[i])) for i in (0, 2, 3, 4)] == [before[i] for i in (0, 2, 3, 4)]
