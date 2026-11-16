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


def test_models_read_the_column_mean_with_the_film_in_series(ref):
    """!
    @brief FVM, FDM and Analytic read the 3D layer (column) mean within 0.1 K (+0.04 to +0.09 K), and the 3D solid reads it too: since fix/face-film-half-slab the film is
           in series with the half plate in the program (Board.face_film_h); before it they read 0.84 K below (the film term, README 3).
    @param ref Fixture.
    @return None.
    """
    lay = np.array(ref["lay_c"])
    for m in ("fvm", "fdm", "analytic", "solid3d"):
        r, _ = C.run(m, 1.0)
        d = np.array(r["cen"]) - lay
        assert d.min() > 0.0 and d.max() < 0.10, (m, d)


def test_typing_the_series_film_again_counts_it_twice(ref):
    """!
    @brief The input change of README 3 (h_bottom typed as 1 / (1/h + t/(2k))) is now inside the program: typed again it counts the half plate twice and the layered models
           read about 1 K above the column mean (0.97 to 1.03 K), so the user must type the plain film.
    @param ref Fixture.
    @return None.
    """
    h_eff = 1.0 / (1.0 / C.H_PAPER + C.T_MM * 1e-3 / (2 * C.K_PLATE))
    for m in ("fvm", "fdm", "analytic"):
        r, _ = C.run(m, 1.0, h=h_eff)
        d = np.array(r["cen"]) - np.array(ref["lay_c"])
        assert d.min() > 0.85 and d.max() < 1.15, (m, d)


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


def test_thick_plate_warning_names_the_three_sources_above_the_limit():
    """!
    @brief The warning of checks.check_thick_plates names S1, S2 and S3 with the through-thickness bound only (8.3, 6.7 and 5.0 K) and not S0 (3.3 K, 4.7 % of its rise,
           under the 5 % limit): since fix/face-film-half-slab the ambient film passes the half plate in the model, so the film term left the bound of a one-layer plate.
    @details Before that branch (fix/thick-plate-warning-bound) the bound added the film term (4.3, 9.3, 7.6, 5.9 K) and all four warned; the real gap of S0 between the 3D surface
             and the FVM is now 2.0 K, under its 3.3 K bound.
    @return None.
    """
    _, sim = C.run("fvm", 1.0)
    text = " ".join(w for w in sim.warnings if "thick and poorly" in w)
    assert "S0:" not in text and all(f"S{i}:" in text for i in (1, 2, 3))
    assert "from the face film" not in text and "upper estimate" in text
    for i, total in ((1, 8.3), (2, 6.7), (3, 5.0)):
        assert f"up to {total} K" in text


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


def test_warning_bound_holds_for_a_column():
    """!
    @brief Review 8.2, after fix/face-film-half-slab: with one source over the whole top face (a column) the gap between the 3D surface and the FVM is the through-thickness
           term alone (0.84 K), under the 'up to' q'' t / (2 k) of the warning (0.93 K); before the film entered the model the gap was 1.77 K and the bound did not hold.
    @return None.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
    import study_case2_review as R
    col = [r for r in R.bound_check() if r["side"] == 50.0][0]
    assert 0.8 * col["bound_half"] < col["gap"] <= col["bound_half"]
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
