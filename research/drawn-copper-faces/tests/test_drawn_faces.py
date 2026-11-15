#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_drawn_faces.py
@brief Tests of the copy that reads drawn zones as an import: exact coverage, the same numbers as a real import, the heat balance, the unchanged boards, and a closed-form face.
@details Run: `.venv/bin/python -m pytest -q research/drawn-copper-faces/tests`. Small boards at a 1 mm cell, a few seconds in all.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import dc_cases as D                                                      # noqa: E402
import patched as P                                                       # noqa: E402
from pcbthermal import fvm, laminate                                      # noqa: E402


def test_zone_raster_area_is_exact():
    """!
    @brief The raster of a zone has exactly the area of the zone, also for an edge that cuts the pixels (the 4 x 4 samples of the program do not).
    @return None.
    """
    p = D.problem(D.case("plain_inset", 200.0))
    r = D.zone_rasters(p, 0.5, quantise=False)[0]
    area = r.sum() / 255.0 * 0.5 * 0.5                                     # mm2
    assert abs(area - 17.6 * 17.6) < 1e-3                                  # the inset square 1.2 mm from the wall
    q = D.problem(D.case("plain_inset", 200.0))
    q.zones[0].polygon = np.array([[1.13, 1.13], [18.77, 1.13], [18.77, 18.77], [1.13, 18.77]]) * 1e-3
    r2 = D.zone_rasters(q, 0.5, quantise=False)[0]
    assert abs(r2.sum() / 255.0 * 0.25 - 17.64 ** 2) < 1e-3


def test_copy_equals_a_real_import():
    """!
    @brief The copy of the networks and a deep copy of the problem with the same rasters as an import give the same temperatures.
    @return None.
    """
    p = D.problem(D.case("stripes", 200.0))
    q = D.zones_to_imported(p, 1.0, "faces")
    with P.use("faces"):
        a = D.heater_mean_fvm(p, 1.0)
        b = D.heater_mean_fdm(p, 1.0)
    P.STATE["float"] = True
    assert abs(a[0] - D.heater_mean_fvm(q, 1.0)[0]) < 5e-3                 # the import is quantised to uint8: 0.4 % of a fill step
    assert abs(b[0] - D.heater_mean_fdm(q, 1.0)[0]) < 5e-3
    assert abs(a[1]) < 1e-9 and abs(b[1]) < 1e-9                           # heat balance


def test_copper_on_cell_lines_does_not_move():
    """!
    @brief Copper whose edges are cell lines (every cell full or empty) gives the program's numbers.
    @return None.
    """
    p = D.problem(D.case("plain_wall", 200.0))
    base = D.heater_mean_fvm(p, 1.0)[0]
    with P.use("faces"):
        assert abs(D.heater_mean_fvm(p, 1.0)[0] - base) < 1e-12                   # the layers have no cut cell: the program's own path
    p = D.problem(D.case("plain_inset", 200.0))
    base = D.heater_mean_fvm(p, 0.4)[0]                                    # 1.2 mm is three cells of 0.4: aligned
    with P.use("faces"):
        assert abs(D.heater_mean_fvm(p, 0.4)[0] - base) < 1e-12


def test_face_across_a_copper_edge_is_the_series_of_the_two_parts():
    """!
    @brief Between two cells that a copper edge (normal to x) separates, the flow-based face is the series of the copper and bare stretches of the window from centre to centre.
    @details One layer-pair board without sub-gaps (the laminate rule off, `n_max` 1) so that the sheets of a pixel are the two-phase values a_full and b_bare.
    @return None.
    """
    p = D.problem(D.case("plain_inset", 200.0))
    cell = 1.0
    with laminate.using(0.4e-3, 1), P.use("faces"):
        net = fvm.Network(p, 20, 20)
        gx, _ = net._lateral_links()
        b = p.board
        slab = b.slab_thicknesses()[0]
        tcu = np.asarray(b.copper_thickness)[0]
        klam = b.layer_laminate()[0][0]
        a_full = b.materials.k_copper * tcu + klam * (slab - tcu)
        b_bare = klam * slab
        # row 10 (y = 10.5 mm), cells 0 (x 0..1) and 1 (x 1..2): the edge is at x = 1.2 mm, the centres at 0.5 and 1.5 mm
        i = 10
        expect = (cell * 1e-3) / (0.7e-3 / b_bare + 0.3e-3 / a_full)       # a window of width dy: g = dy / sum(l / S)
        # the face between cells 1 and 2 (centres 1.5 and 2.5) lies wholly in copper: its value is the full sheet; the face of cells 0 and 1 is the series
        assert abs(gx[0, i, 0] - expect) / expect < 1e-3
        assert abs(gx[0, i, 1] - a_full) / a_full < 1e-3


def test_the_shipped_program_is_the_copy_and_the_earlier_path_is_the_drawn_column():
    """!
    @brief After the adoption the program's own networks equal the copy, and the earlier path (copper.drawn_source switched off at runtime) still gives the 'drawn' column of README 3.1.
    @return None.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
    import study_adopted as A
    p = D.problem(D.case("stripes", 200.0))
    now = D.heater_mean_fvm(p, 1.0)[0]
    with P.use("faces"):
        assert abs(D.heater_mean_fvm(p, 1.0)[0] - now) < 1e-9                  # the same raster, the same faces (README 12.2)
    with A.earlier_path():
        before = D.heater_mean_fvm(p, 1.0)[0]
    ref = 73.872                                                             # finite elements, extrapolated (README 2.1)
    assert round(100 * (before / ref - 1), 1) == -8.0
    assert round(100 * (now / ref - 1), 1) == -0.6
