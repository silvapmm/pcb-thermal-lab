#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_reimport_view_fit.py
@brief Replace or Update with ANOTHER board through the real MainWindow: the new board, its copper, holes and parts are in the document and the editor view is fitted to it (the
       maintainer imported the CMM board, replaced it by the RP2040 and saw nothing: the view kept the zoom and centre of the old board), also after Undo and Redo.
@details Uses the driver of `test_reimport_matrix.py`. The synthetic pair has boards of 40 and 80 mm; the library pair (CMM2 and RP2040, 130 x 102 and 52 x 51 mm) skips without
         the boards (`PCBT_REAL_BOARDS`).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("pytestqt")

from PySide6.QtCore import QRectF

from tests.test_reimport_different_board import other_board
from tests.test_reimport_matrix import app, base, library, snapshot  # noqa: F401  (fixtures)


def board_in_view(app):
    """!
    @brief How well the view shows the board.
    @param app The App of the matrix tests.
    @return tuple (fraction of the board inside the viewport, fraction of the viewport the board fills)
    """
    c, b = app.win.canvas, app.doc.problem.board
    box = QRectF(0.0, 0.0, b.width * 1000.0, b.height * 1000.0)
    vis = c.mapToScene(c.viewport().rect()).boundingRect()
    inside = vis.intersected(box)
    return inside.width() * inside.height() / (box.width() * box.height()), box.width() * box.height() / (vis.width() * vis.height())


def assert_fitted(app):
    """!
    @brief The whole board is in the view and fills a good part of it.
    @param app The App of the matrix tests.
    """
    inside, fills = board_in_view(app)
    assert inside > 0.99 and 0.2 < fills <= 1.0, (inside, fills)


@pytest.mark.parametrize("mode", ["replace", "update"])
def test_another_synthetic_board_is_shown_whole_and_undo_shows_the_old_one(app, base, tmp_path, mode):
    app.win.resize(1300, 800)
    app.win.show()
    app.run(base, "replace", powers={"U1": 3.0})
    app.win.canvas.fit()
    assert_fitted(app)
    old = snapshot(app.doc)
    w0 = app.doc.problem.board.width
    msg = app.run(other_board(base, tmp_path), mode)
    assert app.doc.problem.board.width == pytest.approx(2 * w0)                       # the new board, not the old one
    assert app.doc.problem.imported is not None and snapshot(app.doc)["masks"] != old["masks"]
    assert app.doc.project.imports[0].parts                                           # the parts of the new files are listed
    assert msg and "re-imported" in msg
    assert_fitted(app)                                                                # the view follows the new board
    app.doc.stack.undo()
    assert app.doc.problem.board.width == pytest.approx(w0) and snapshot(app.doc) == old
    assert_fitted(app)
    app.doc.stack.redo()
    assert app.doc.problem.board.width == pytest.approx(2 * w0)
    assert_fitted(app)


def test_the_zoom_the_user_chose_stays_when_the_same_board_is_re_imported(app, base):
    app.win.resize(1300, 800)
    app.win.show()
    app.run(base, "replace")
    c = app.win.canvas
    c.scale(3.0, 3.0)
    s = c.transform().m11()
    app.run(base, "replace")
    assert c.transform().m11() == pytest.approx(s)


@pytest.mark.parametrize("order", [("cmm2", "rp2040"), ("rp2040", "cmm2")])
@pytest.mark.parametrize("mode", ["replace", "update"])
def test_library_boards_replaced_by_each_other_are_shown_whole(app, order, mode):
    first, second = library(order[0]), library(order[1])
    untick = lambda src: ["pos.csv"] if src.endswith("cmm2") else []                  # the CMM set holds two placement files
    app.win.resize(1300, 800)
    app.win.show()
    app.run(first, "replace", untick=untick(first))
    app.win.canvas.fit()
    w0 = app.doc.problem.board.width
    app.run(second, mode, untick=untick(second))
    pr = app.doc.problem
    assert pr.board.width != pytest.approx(w0) and pr.imported is not None and pr.vias
    assert_fitted(app)
    app.doc.stack.undo()
    assert app.doc.problem.board.width == pytest.approx(w0)
    assert_fitted(app)


def test_a_zoom_in_stays_when_the_board_size_is_typed_in_the_dock(app):
    """!
    @brief Review: the first rule fitted the view again whenever less than half of the board was in view, so a user zoomed in on a corner who typed a new width lost the zoom.
    @param app The App of the matrix tests.
    """
    import numpy as np
    from pcbthermal.model import Heater
    app.win.resize(1300, 800)
    app.win.show()
    app.doc.edit("heater", lambda p: p.problem.heaters.append(Heater(name="H", power=1.0, layer=0,
                 polygon=np.array([[0.01, 0.01], [0.02, 0.01], [0.02, 0.02], [0.01, 0.02]]))))
    c = app.win.canvas
    c.fit()
    c.zoom(4.0)
    c.centerOn(15.0, 15.0)
    s = c.transform().m11()
    bp = app.win.board_panel
    bp.width.setValue(bp.width.value() + 1.0)
    bp.width.editingFinished.emit()
    assert app.doc.problem.board.width == pytest.approx(0.101)
    assert c.transform().m11() == pytest.approx(s)                                    # the size changed, the user is still looking at the board
    app.doc.stack.undo()
    assert c.transform().m11() == pytest.approx(s)


def test_a_zoom_in_does_not_survive_a_replace_by_another_board(app, base, tmp_path):
    """!
    @brief A re-import of another board fits the view even when the user had zoomed in: the old zoom and centre mean nothing on the new board.
    @param app The App of the matrix tests.
    @param base Folder of the synthetic set.
    @param tmp_path Temporary folder.
    """
    app.win.resize(1300, 800)
    app.win.show()
    app.run(base, "replace")
    c = app.win.canvas
    c.fit()
    c.zoom(4.0)
    c.centerOn(10.0, 10.0)
    app.run(other_board(base, tmp_path), "replace")
    assert_fitted(app)
    c.zoom(4.0)
    c.centerOn(10.0, 10.0)
    app.doc.stack.undo()
    assert_fitted(app)
