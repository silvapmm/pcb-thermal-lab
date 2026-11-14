#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_analytic_hot_point.py
@brief The Analytic transient reads each heater at the hottest point of the steady solution WITH the vias and heatsinks, as the steady result does (it read the hottest
       point of the board without them, 2 mm away on a via cluster, and the 0.3 s response was 22 % low).
@details The reference numbers are those of the finite-element comparison of the folder research/transient-reference-boards (board `vias`: 20 x 20 mm, four layers,
         4 x 4 resin-filled vias under a 6 mm part, 1 W, h 10 W/m2K): plateau 113.291 K/W, time to 63 % 119.781 s, and a rise of 4.37 K/W at 0.3 s (derived from the
         recorded error -21.7 % of 3.42 K/W of the old code). The finite-element tool is not run here.
"""
import numpy as np
import pytest

from pcbthermal import Problem, analytic

FEM_PLATEAU, FEM_T63, FEM_Z03 = 113.291, 119.781, 4.374


def _vias_board():
    """!
    @brief The `vias` board of the transient comparison.
    @return Problem.
    """
    p = Problem.new(20, 20, 4, 1.6, 35.0, h_top=10.0, h_bottom=10.0, h_side=10.0)
    for lay in range(1, 5):
        p.add_zone(lay, rect=(0, 0, 20, 20))
    p.add_heater(1, 1.0, rect=(7, 7, 13, 13), role="source")
    for x in (8.8, 9.6, 10.4, 11.2):
        for y in (8.8, 9.6, 10.4, 11.2):
            p.add_via(x, y, 0.3, fill_k=0.3)
    return p


def _t63(t, z, r):
    """!
    @brief Time to 63.2 % of the plateau by linear interpolation.
    @param t Times in seconds.
    @param z Response in K/W.
    @param r Plateau in K/W.
    @return float
    """
    return float(np.interp(0.632 * r, z, t))


def test_plateau_of_the_transient_equals_the_steady_maximum():
    """!
    @brief The step response ends at the maximum of the steady solve (it ended 0.6 % below it).
    @return None.
    """
    p = _vias_board()
    steady = analytic.solve_steady(p, cell_mm=0.5, n_terms=100)
    t, z, r = analytic.step_responses(p, cell_mm=0.5, n_terms=100, t_end=1500.0, n_times=120)
    assert r[0] == pytest.approx(float(steady.T.max() - p.board.ambient), rel=1e-3)


def test_against_the_finite_element_numbers_of_the_study():
    """!
    @brief Plateau, time to 63 % and the first seconds against the finite-element reference (before: -0.62 %, +1.01 %, -21.7 %).
    @return None.
    """
    t, z, r = analytic.step_responses(_vias_board(), cell_mm=0.5, n_terms=100, t_end=1500.0, n_times=200)
    assert abs(r[0] / FEM_PLATEAU - 1.0) < 1e-3
    assert abs(_t63(t, z[0], r[0]) / FEM_T63 - 1.0) < 5e-3
    z03 = float(np.interp(0.3, t, z[0]))
    assert -0.12 < z03 / FEM_Z03 - 1.0 < 0.0           # the own early error with vias remains (about -8 %), the offset of the wrong point is gone


def test_the_readout_point_is_the_hot_point_of_the_steady_field():
    """!
    @brief The point of the served heater is the argmax of the steady field of the board with the vias.
    @return None.
    """
    p = _vias_board()
    steady = analytic.solve_steady(p, cell_mm=0.5, n_terms=100)
    ms = analytic._ModalSet(p, 0.5, 100)
    assert tuple(int(v) for v in ms.points[0]) == tuple(int(v) for v in np.unravel_index(int(np.argmax(steady.T)), steady.T.shape))


def test_boards_without_vias_and_heatsinks_do_not_change():
    """!
    @brief No local element: the uniform modal system, with the point found by _modal_dynamics (no local block).
    @return None.
    """
    p = _vias_board()
    p.vias = []
    d = analytic._local_dynamics(p, 0.5, 60)
    ref = analytic._modal_dynamics(p, 0.5, 60)
    assert d["local"] is None
    assert d["points"] == ref["points"] and np.array_equal(d["U"], ref["U"]) and np.array_equal(d["lam"], ref["lam"])
