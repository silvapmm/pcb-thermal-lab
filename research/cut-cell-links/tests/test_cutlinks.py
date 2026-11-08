#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_cutlinks.py
@brief Tests of the cut-cell prototype `lib/cutlinks.py` (the program is not touched): aligned edges, energy balance, sign of the links, the film, the frame problem.
@details Run: .venv/bin/python -m pytest -q research/cut-cell-links/tests   (from the repository root; a few seconds each)
"""

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import cutlinks as cl         # noqa: E402
import boards as bd           # noqa: E402
from pcbthermal import Problem    # noqa: E402


def aligned(h_side=200.0):
    """!
    @brief A square outline on the grid lines of a 1 mm cell.
    @param h_side Edge coefficient in W/m2K.
    @return Problem.
    """
    p = Problem.new(30, 30, 2, h_side=h_side).add_full_copper()
    p.add_heater(1, 2.0, rect=(13.5, 13.5, 16.5, 16.5), name="U")
    p.set_outline([[5, 5], [25, 5], [25, 25], [5, 25]])
    return p


def test_aperture_and_links_equal_the_program_on_grid_lines():
    """!
    @brief With the outline on the grid lines no cell is cut: the link schemes without the film give the program's temperatures.
    @return None.
    """
    t0 = cl.tmax(aligned(), 1.0, "program")
    for s in ("aperture", "links"):
        assert abs(cl.tmax(aligned(), 1.0, s) - t0) < 1e-9


def test_film_factor_of_a_whole_edge_cell_is_one_plus_g_d_over_sl():
    """!
    @brief On an aligned edge the centre is half a cell from the outline: the film conductance is g0 / (1 + g0 (dx/2) / (S L)).
    @return None.
    """
    p = aligned()
    p.validate()
    with cl.using("aperture+film"):
        net = cl.CutLinkNetwork(p, 30, 30)
    # Edge cell on the left side, away from corners: column 5, row 15, copper layer 0
    L = net.dy
    S = net.S[0, 15, 5]
    gnew = net.g_side[0, 15, 5]
    fac = net.film_factor[0, 15, 5]
    gold = gnew * fac
    assert fac == pytest.approx(1.0 + gold * (0.5 * net.dx) / (S * L), rel=1e-12)


@pytest.mark.parametrize("scheme", cl.SCHEMES)
def test_energy_balance_on_a_turned_square(scheme):
    """!
    @brief The heat to the air equals the power for every scheme on a board whose outline cuts cells at every depth.
    @param scheme Scheme name.
    @return None.
    """
    p = bd.edge_board(angle=27.0, h_side=200.0, pc=0.5)
    r = cl.solve(p, 1.0, scheme)
    assert sum(r.power_out.values()) == pytest.approx(2.0, rel=1e-9)


@pytest.mark.parametrize("scheme", ("aperture", "aperture+film", "links", "links+film", "links+strip"))
def test_matrix_is_symmetric_with_no_positive_off_diagonal(scheme):
    """!
    @brief The system matrix stays symmetric and an M-matrix pattern (no positive off-diagonal) on a turned square with slivers.
    @param scheme Scheme name.
    @return None.
    """
    m = cl.matrix_checks(bd.edge_board(angle=18.4, sx=0.13, sy=0.07, pc=0.5), 1.0, scheme)
    assert m["asym"] < 1e-12
    assert m["pos_offdiag"] == 0
    assert m["lam_min"] > 0


def test_signed_distance_of_a_square():
    """!
    @brief Distances to a 10 mm square: inside positive, outside negative, the nearest side.
    @return None.
    """
    sq = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=float) * 1e-3
    d = cl.signed_distance(sq, np.array([5e-3, 12e-3, 1e-3]), np.array([5e-3, 5e-3, 5e-3]))
    assert d == pytest.approx([5e-3, -2e-3, 1e-3])


def test_frame_board_reproduces_the_edge_board_when_not_turned():
    """!
    @brief At zero turn and shift, the frame problem and the outline problem are the same continuum problem: at a fine cell the peaks agree to a few mK.
    @return None.
    """
    kw = dict(h_side=200.0, pc=0.0)
    a = cl.tmax(bd.edge_board(**kw), 0.25, "program")
    b = cl.tmax(bd.frame_board(**kw), 0.25, "program")
    assert abs(a - b) < 5e-3
