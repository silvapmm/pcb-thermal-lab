#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_fdm_harmonic_face.py
@brief The FDM joins two nodes by the harmonic mean of their sheet conductances (default), so no heat leaks across a copper edge; checked against the independent 3D solver.
@details With the arithmetic mean half of the sheet of a copper node leaks into a bare neighbour: a bare-pad board read 13 % low at 1 mm (independent 3D solver),
         the harmonic mean 7 % low (4 % at 0.5 mm). Uniform boards do not change, the matrix stays symmetric with no positive off-diagonal, and a node cut by the outline
         keeps the cover-weighted link (a harmonic mean of the cover-scaled values would make the link to a sliver 2c/(1 + c)).
"""

import os
import sys

import numpy as np
import pytest
import scipy.sparse as sp

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))
import layered3d as L                                          # noqa: E402

from pcbthermal import fdm, Problem                            # noqa: E402
from pcbthermal.model import Materials                         # noqa: E402


def gap_board():
    """!
    @brief 50 x 24 mm, two layers, copper cut by a 3 mm gap (x 23 to 26 mm) on both layers, a 6 mm 2 W part beside the gap.
    @return Problem.
    """
    p = Problem.new(50.0, 24.0, layers=2, thickness_mm=1.6, copper_um=35.0, ambient=25.0, h_top=10.0, h_bottom=15.0, h_side=None,
                    materials=Materials(k_fr4_through=0.3, k_fr4_inplane=0.3))
    for layer in (1, 2):
        p.add_zone(layer, rect=(0, 0, 23.0, 24.0))
        p.add_zone(layer, rect=(26.0, 0, 50.0, 24.0))
    p.add_heater(1, 2.0, rect=(16, 9, 22, 15), name="U")
    return p


def gap_reference(cell_mm):
    """!
    @brief Hottest top cell under the part in the independent 3D solver (copper k in the strips, laminate in the gap, same cell).
    @param cell_mm Cell in mm.
    @return float Rise in K.
    """
    n, m = int(round(50 / cell_mm)), int(round(24 / cell_mm))
    xs = (np.arange(n) + 0.5) * cell_mm
    k = np.where((xs > 23.0) & (xs < 26.0), 0.3, 385.0)[None, :] * np.ones((m, 1))
    t = 35e-6
    r = L.solve(cell_mm * 1e-3, n, m, [(t, k, 1), (1.6e-3 - 2 * t, 0.3, 8), (t, k, 1)], (16e-3, 9e-3, 22e-3, 15e-3), 2.0, 10.0, 15.0, film_under_source=True)
    return float(r["cell_max_source"])


def test_the_harmonic_mean_is_the_default():
    # solve_steady and the network take "harmonic" unless told otherwise; the extras record it
    r = fdm.solve_steady(gap_board(), 1.0)
    assert r.extras["harmonic"] == 1.0
    assert fdm.solve_steady(gap_board(), 1.0, "arithmetic").extras["harmonic"] == 0.0


@pytest.mark.parametrize("cell, bound", [(1.0, 0.07), (0.5, 0.04)])
def test_across_a_copper_gap_the_harmonic_mean_is_closer_to_the_independent_solver(cell, bound):
    # Measured (same cell): arithmetic -14.32 / -6.29 %, harmonic -5.49 / -3.17 % at 1 / 0.5 mm (this test keeps face_fill=False: the harmonic mean of the nodal sheets)
    ref = gap_reference(cell)
    a = float(fdm.solve_steady(gap_board(), cell, "arithmetic").t_max) - 25.0
    h = float(fdm.solve_steady(gap_board(), cell, face_fill=False).t_max) - 25.0
    assert abs(h / ref - 1.0) < abs(a / ref - 1.0)
    assert h / ref - 1.0 == pytest.approx(-bound + 0.015, abs=0.015)
    assert h / ref - 1.0 < 0.0                                  # still on the cool side: the mean never overshoots the reference here


def test_uniform_copper_is_bit_identical_for_both_means():
    p = Problem.new(30.0, 30.0, layers=2, h_top=10.0, h_bottom=15.0, h_side=None)      # no edge coefficient: no laminate band, so every copper node has the same sheet
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(12, 12, 18, 18))
    a = fdm.solve_steady(p, 1.0, "arithmetic")
    h = fdm.solve_steady(p, 1.0)
    assert np.array_equal(np.asarray(a.T), np.asarray(h.T))


def test_the_matrix_stays_symmetric_with_no_positive_off_diagonal():
    p = gap_board()
    K = sp.csr_matrix(fdm.Network(p, 1.0).K)
    assert abs(K - K.T).max() <= 1e-12 * abs(K).max()
    assert (K - sp.diags(K.diagonal())).max() <= 0.0


def test_a_node_cut_by_the_outline_keeps_the_cover_weighted_link():
    # Full copper on a round board: the sheets are uniform except at the laminate band of the edge (2e-5 K measured), so the result equals the arithmetic mean
    # (the plain harmonic mean of the cover-scaled values moved part_across_outline +0.37 to +0.56 % of the rise at 1 mm)
    p = Problem.new(40.0, 40.0, layers=2, h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_full_copper()
    p.set_outline([[20 + 17 * np.cos(a), 20 + 17 * np.sin(a)] for a in np.linspace(0, 2 * np.pi, 97)[:-1]])
    p.add_heater(1, 1.0, rect=(17, 17, 23, 23))
    a = fdm.solve_steady(p, 1.0, "arithmetic")
    h = fdm.solve_steady(p, 1.0)
    assert float(h.t_max) == pytest.approx(float(a.t_max), abs=1e-3)
