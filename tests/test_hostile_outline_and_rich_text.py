#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_hostile_outline_and_rich_text.py
@brief A hostile project file cannot exhaust memory through the board outline (pieces of the edge distance, crossings of the cut-cell links, non-finite coordinates) and a
       file or member name is never read as rich text in the package message boxes and labels.
"""

import os

import numpy as np
import pytest

from pcbthermal import checks, geometry as geo
from pcbthermal.examples import example_board
from pcbthermal.model import Problem

PLANT = "<b>x</b><img src='file:///etc/passwd'>"


def _star(n_edges, r_tip=0.0499, r_valley=0.005, c=0.05):
    """!
    @brief A simple star polygon whose edges are long (about 0.45 of the box side).
    @param n_edges Number of edges (even).
    @param r_tip Tip radius in m.
    @param r_valley Valley radius in m.
    @param c Centre in m.
    @return numpy.ndarray (n_edges, 2) in m.
    """
    th = np.arange(n_edges) * 2 * np.pi / n_edges
    r = np.where(np.arange(n_edges) % 2 == 0, r_tip, r_valley)
    return np.column_stack([c + r * np.cos(th), c + r * np.sin(th)])


def _brute(poly, x, y):
    """!
    @brief Unsigned distance to the nearest segment by brute force.
    @param poly Polygon (n, 2) in m.
    @param x X of the points in m.
    @param y Y of the points in m.
    @return numpy.ndarray distances in m.
    """
    a, b = poly, np.roll(poly, -1, axis=0)
    ab = b - a
    out = []
    for xi, yi in zip(x, y):
        t = np.clip(((xi - a[:, 0]) * ab[:, 0] + (yi - a[:, 1]) * ab[:, 1]) / np.maximum((ab ** 2).sum(1), 1e-300), 0, 1)
        out.append(np.hypot(xi - a[:, 0] - t * ab[:, 0], yi - a[:, 1] - t * ab[:, 1]).min())
    return np.array(out)


def test_piece_count_is_bounded_and_the_answer_unchanged(monkeypatch):
    """!
    @brief A coarser piece (the cap forced low) gives the same distances as the brute force, and a normal outline keeps the 1/2000 piece (identical to the cap off).
    @param monkeypatch pytest fixture.
    @return None
    """
    p = _star(400)
    rng = np.random.default_rng(1)
    x, y = rng.uniform(0.001, 0.099, 300), rng.uniform(0.001, 0.099, 300)
    ref = geo.signed_distance_to_outline(p, x, y)
    monkeypatch.setattr(geo, "OUTLINE_MAX_PIECES", 3000)                        # perimeter / 3000 is far above diag / 2000: the cap is the active bound
    capped = geo.signed_distance_to_outline(p, x, y)
    assert np.allclose(np.abs(capped), _brute(p, x, y), atol=1e-12)
    assert np.allclose(capped, ref, atol=1e-12) and (np.sign(capped) == np.sign(ref)).all()


def test_a_zigzag_of_20000_long_edges_stays_small():
    """!
    @brief 20 000 long edges used to cut into 13 million pieces (1.4 GB); now the pieces are at most OUTLINE_MAX_PIECES plus one per edge.
    @return None
    """
    import tracemalloc
    p = _star(20000)
    tracemalloc.start()
    d = geo.signed_distance_to_outline(p, np.array([0.05, 0.002]), np.array([0.05, 0.05]))
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    assert np.isfinite(d).all() and d[0] > 0                                     # the centre is inside the star
    assert peak < 400e6


def test_non_finite_outline_raises_cleanly():
    """!
    @brief NaN and infinite coordinates raise ValueError in the geometry functions, in the crossing count and in Board.validate.
    @return None
    """
    for bad in (np.nan, np.inf, -np.inf):
        p = _star(40)
        p[3, 0] = bad
        with pytest.raises(ValueError, match="finite"):
            geo.signed_distance_to_outline(p, np.array([0.05]), np.array([0.05]))
        with pytest.raises(ValueError, match="finite"):
            geo.face_apertures(p, 50, 50, 2e-3, 2e-3)
        with pytest.raises(ValueError, match="finite"):
            geo.outline_crossings(p, 1e-3)
        prob = Problem.new(100, 100, 2)
        prob.board.outline = p
        with pytest.raises(ValueError, match="finite"):
            prob.board.validate()


def test_face_apertures_refuses_too_many_crossings():
    """!
    @brief An outline of long edges on a fine grid asks for more crossings than the bound: a ValueError before any array of that size is built; a normal outline is unaffected.
    @return None
    """
    p = _star(20000)
    with pytest.raises(ValueError, match="too many long edges"):
        geo.face_apertures(p, 4000, 4000, 25e-6, 25e-6)
    ax, ay = geo.face_apertures(_star(40), 50, 50, 2e-3, 2e-3)                    # A normal case runs
    assert ax.shape == (50, 49) and ay.shape == (49, 50)


def test_live_check_gives_a_plain_warning_for_a_hostile_outline():
    """!
    @brief check_input answers with the one outline warning (no memory taken, no other check run on it) when the outline is beyond the bound at this cell, and the normal list otherwise.
    @return None
    """
    prob = Problem.new(100, 100, 2)
    prob.board.outline = _star(20000)
    w = checks.check_input(prob, ("fvm",), cell_mm=0.01, live=True)
    assert len(w) == 1 and "outline" in str(w[0]) and "coarser cell" in str(w[0]) and "research/" not in str(w[0])
    ok = checks.check_input(prob, ("fvm",), cell_mm=1.0, live=True)               # 20 000 edges at 1 mm are inside the bound
    assert not any("grid lines" in str(x) for x in ok)
    nan = Problem.new(100, 100, 2)
    nan.board.outline = _star(40)
    nan.board.outline[2, 1] = np.nan
    assert "finite" in str(checks.check_input(nan, ("fvm",), cell_mm=1.0, live=True)[0])


# ---------------------------------------------------------------------------------------------------------------------------------------- rich text
def test_package_messages_are_plain_text(qtbot, monkeypatch):
    """!
    @brief The message boxes of the package actions (which quote member and file names) are plain text, so a name with markup is shown as typed.
    @param qtbot pytest-qt fixture.
    @param monkeypatch pytest fixture.
    @return None
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox, QWidget
    from pcbthermal.gui import package_actions as pa
    seen = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: seen.append((self.text(), self.textFormat())) or QMessageBox.Ok)
    parent = QWidget()
    qtbot.addWidget(parent)
    pa._plain_message(parent, QMessageBox.Warning, "t", f"member {PLANT} not used")
    assert seen == [(f"member {PLANT} not used", Qt.PlainText)]


def test_export_dialog_note_is_plain_text(qtbot, monkeypatch):
    """!
    @brief The privacy note of the export dialog lists file names from the package: its label is plain text.
    @param qtbot pytest-qt fixture.
    @param monkeypatch pytest fixture.
    @return None
    """
    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtWidgets import QLabel
    from pcbthermal import package as pkg
    from pcbthermal.gui import package_actions as pa
    from pcbthermal.gui.main_window import MainWindow
    w = MainWindow(settings=QSettings(os.path.join(os.environ["PCBTHERMAL_CONFIG"], "w.ini"), QSettings.IniFormat))
    qtbot.addWidget(w)
    w.doc.open_problem(example_board(), "ex")
    name = "a<b>x</b><img src=x>.gtl"
    pkg.attach_sources(w.doc.project, [(name, b"G04 C:\\Users\\someone\\board*\n%FSLAX46Y46*%\nM02*\n", "gerber", "Top copper")], set_name="ex")
    dlg = pa.ExportPackageDialog(w, True, False)
    qtbot.addWidget(dlg)
    notes = [lb for lb in dlg.findChildren(QLabel) if "Found in the first" in lb.text()]
    assert notes, "the privacy note did not appear"
    assert all(lb.textFormat() == Qt.PlainText for lb in notes)
    assert "<img" not in notes[0].text()                  # the package already neutralises the member name; the label would not have shown it as markup either
