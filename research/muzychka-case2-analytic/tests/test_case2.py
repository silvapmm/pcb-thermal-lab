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


def test_thick_plate_warning_is_shown_for_all_four_sources_with_the_film_term():
    """!
    @brief The warning of checks.check_thick_plates names all four sources: S0 (4.3 K, 6 % of its rise) now exceeds the 5 % limit because the film term was added; S1, S2 and S3 read 9.3, 7.6 and 5.9 K.
    @details Guards the fix of the thick-plate bound (branch fix/thick-plate-film-term and its documents, docs/validation.md 22.1): before it the text held only the through-thickness
             term (8.3, 6.7, 5.0 and 3.3 K) and S0 stayed silent; the text also says 'upper estimate', not 'bound'.
    @return None.
    """
    _, sim = C.run("fvm", 1.0)
    text = " ".join(w for w in sim.warnings if "thick and poorly" in w)
    assert all(f"S{i}:" in text for i in (0, 1, 2, 3))
    assert text.count("from the face film") == 4 and "upper estimate" in text
    for i, total in ((0, 4.3), (1, 9.3), (2, 7.6), (3, 5.9)):
        assert f"S{i}:" in text and f"up to {total} K" in text


def test_the_board_dock_holds_the_plate():
    """!
    @brief The copper box of the Board dock reaches the 10 mm (10 000 um) plate (it stopped at 210 um) and the loaded plate stays 10 000 um in the project (spinfit.fit_range).
    @details Guards the fix of the dock write-back (branch fix/dock-writeback): before it the box clamped the stored value to 210 um.
    @return None.
    """
    pytest.importorskip("PySide6")
    from pcbthermal.gui.panels import BoardPanel
    from pcbthermal.gui.document import Document
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert BoardPanel(Document()).copper.maximum() >= C.T_MM * 1e3     # The box now reaches the 10 mm plate
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
    import study_case2_review as R
    (_, a, z), _ = R.dock_check()
    assert a["copper um"] == [10000.0] and z["copper um"] == [10000.0]
    assert app is not None


def test_warning_bound_is_exceeded_by_a_column():
    """!
    @brief Review 8.2: with one source over the whole top face (a column), the gap between the 3D surface and the FVM (1.77 K) exceeds the 'up to' q'' t / (2 k) of the
           thick-plate warning (0.93 K) and is close to q'' t / k (1.87 K): the stated number bounds the through-thickness term only, not the film term.
    @return None.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
    import study_case2_review as R
    col = [r for r in R.bound_check() if r["side"] == 50.0][0]
    assert col["gap"] > 1.5 * col["bound_half"]
    assert abs(col["gap"] - col["bound_full"]) < 0.15
    assert not col["warned"]


def test_one_dock_edit_leaves_the_fields_it_did_not_touch():
    """!
    @brief One edit of h_bottom in the Board dock of the real main window leaves the copper (10 000 um), h_top (600), the width (50.04 mm) and the copper conductivity (150.4) as loaded;
           one edit of the emissivity keeps the unequal copper of a simple stack-up.
    @details Guards the fix of the dock write-back (the dock writes only the boxes the user changed, and a box widens to hold a loaded value). Before it the same edit rewrote
             the copper to 210 um, h_top to 500, the width to 50.0 mm, the conductivity to 150 and flattened the unequal copper (Review 8.6).
    @return None.
    """
    pytest.importorskip("PySide6")
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
    import study_case2_review as R
    (_, a, z), (_, a2, z2) = R.dock_check()
    assert z == a
    assert z["copper um"] == [10000.0] and z["h_top"] == 600.0
    assert abs(z["width mm"] - 50.04) < 1e-9 and abs(z["k_copper"] - 150.4) < 1e-9
    assert z2["copper um"] == [70.0, 17.5, 17.5, 70.0] and z2 == a2
