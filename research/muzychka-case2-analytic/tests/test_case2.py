#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_case2.py
@brief Tests of the case 2 investigation: the independent solver reproduces the paper, and the gap of the layered models is the two terms the README names.
@details Run from the repository root: QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q research/muzychka-case2-analytic/tests
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import numpy as np
import pytest

import case2 as C


@pytest.fixture(scope="module")
def ref():
    """!
    @brief The independent 3D solution (0.5 mm, 8 sub-slabs).
    @return dict of case2.reference3d.
    """
    return C.reference3d(0.5, 8)


def test_independent_solver_reproduces_the_paper_centroids(ref):
    """!
    @brief The surface centroids of the 3D solver are within 0.05 K of Table 4 of the paper (ambient 25 C assumed, as the extracted table has none).
    @param ref Fixture.
    @return None.
    """
    assert np.abs(np.array(ref["surf_c"]) - C.PAPER_CENTROID).max() < 0.05


def test_models_sit_below_the_surface_by_through_thickness_plus_film(ref):
    """!
    @brief FVM, FDM and Analytic read the layer temperature: 3D layer mean minus 0.84 K (the film term, Q t / (2 k A) = 0.93 K for the mean flux), and the 3D solid reads the layer mean itself.
    @param ref Fixture.
    @return None.
    """
    lay = np.array(ref["lay_c"])
    for m in ("fvm", "fdm", "analytic"):
        r, _ = C.run(m, 1.0)
        d = lay - np.array(r["cen"])
        assert d.min() > 0.7 and d.max() < 1.05, (m, d)
    r, _ = C.run("solid3d", 1.0)
    assert np.abs(np.array(r["cen"]) - lay).max() < 0.15


def test_half_layer_film_in_series_closes_the_film_term(ref):
    """!
    @brief With h_bottom replaced by 1 / (1/h + t/(2k)) (an input change) the layered models read the 3D layer mean within 0.15 K.
    @param ref Fixture.
    @return None.
    """
    h_eff = 1.0 / (1.0 / C.H_PAPER + C.T_MM * 1e-3 / (2 * C.K_PLATE))
    for m in ("fvm", "fdm", "analytic"):
        r, _ = C.run(m, 1.0, h=h_eff)
        assert np.abs(np.array(r["cen"]) - ref["lay_c"]).max() < 0.15, m


def test_error_in_kelvin_does_not_depend_on_h():
    """!
    @brief The FVM shortfall against the 3D surface of source 2 is the same at h = 25 and h = 1000 (within 0.1 K), so the percentage grows with h, not with a lower h.
    @return None.
    """
    e = []
    for h in (25.0, 1000.0):
        ref = C.reference3d(0.5, 8, h=h)
        r, _ = C.run("fvm", 1.0, h=h)
        e.append(r["cen"][1] - ref["surf_c"][1])
    assert abs(e[0] - e[1]) < 0.1


def test_thick_plate_warning_is_shown_for_the_three_large_sources_only():
    """!
    @brief The warning of checks.check_thick_plates names S1, S2 and S3 (bound 8.3, 6.7 and 5.0 K) and not S0 (3.3 K, 4.8 % of its rise, under the 5 % limit).
    @return None.
    """
    _, sim = C.run("fvm", 1.0)
    text = " ".join(w for w in sim.warnings if "thick and poorly" in w)
    assert all(f"S{i}:" in text for i in (1, 2, 3)) and "S0:" not in text


def test_the_board_dock_cannot_hold_the_plate():
    """!
    @brief The copper box of the Board dock stops at 210 um: a 10 mm plate cannot be typed there (it can be loaded from a project file).
    @return None.
    """
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from pcbthermal.gui.document import Document
    from pcbthermal.gui.panels import BoardPanel
    p = BoardPanel(Document())
    assert p.copper.maximum() == 210.0 and p.copper.maximum() < C.T_MM * 1e3
    assert app is not None
