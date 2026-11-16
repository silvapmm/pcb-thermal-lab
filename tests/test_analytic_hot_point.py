#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_analytic_hot_point.py
@brief The Analytic transient reads each heater at the hottest point of the steady solution WITH the vias and heatsinks, as the steady result does (it read the hottest
       point of the board without them, 2 mm away on a via cluster, and the 0.3 s response was 22 % low).
@details The reference numbers are those of the finite-element comparison of the folder research/transient-reference-boards (board `vias`: 20 x 20 mm, four layers,
         4 x 4 resin-filled vias under a 6 mm part, 1 W, h 10 W/m2K): plateau 113.291 K/W, time to 63 % 119.781 s, and a rise of 4.37 K/W at 0.3 s (derived from the
         recorded error -21.7 % of 3.42 K/W of the old code). The finite-element tool is not run here. The review added the flat top: on a four-layer board with
         vias and a strong heatsink under the part the steady field is flat to 0.03 % over 36 cells, its plain argmax jumped 1 to 2 mm when the part moved by 0.05 mm
         (time to 63 % 1.3 % apart) and fell on cells that the FVM puts 3 % below its hottest node; the point of the board without vias is kept there
         (analytic._readout_point, READOUT_TOLERANCE).
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
    @brief A via cluster that moves the hot point (the centre 0.57 % below it): the point of the served heater is the argmax of the steady field of the board with the vias.
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


def _strong_sink_board(dx_mm=0.0):
    """!
    @brief Four-layer 60 x 40 mm board, 10 mm part (moved by dx_mm), 4 x 4 vias of 2 mm pitch under it and a 300 W/m2K heatsink under it (validation 4.1).
    @param dx_mm Shift of the part along x in mm.
    @return Problem.
    """
    p = Problem.new(width_mm=60, height_mm=40, layers=4, thickness_mm=1.6, copper_um=35.0, ambient=25.0, h_top=10.0, h_bottom=10.0)
    for lay in range(1, 5):
        p.add_zone(lay, rect=(0, 0, 60, 40))
    p.add_heater(1, 2.0, rect=(25 + dx_mm, 15, 35 + dx_mm, 25))
    p.add_via_array((27, 17, 33, 23), 4, 4, diameter=0.3)
    p.add_heatsink(1, 300.0, rect=(20, 10, 40, 30))
    return p


def test_a_flat_top_keeps_the_point_and_the_response_is_continuous():
    """!
    @brief The flat top of the strong-heatsink board keeps the point of the board without vias, and a part moved by 0.05 mm changes the time to 63 % by under 0.2 %
           (the plain argmax: 10.05 against 9.92 s, 1.3 %; the FVM at 0.5 and 0.25 mm 11.25 s at its hottest node, the cell the argmax chose 3 % below it).
    @return None.
    """
    p = _strong_sink_board()
    ms = analytic._ModalSet(p, 0.5, 300)
    assert tuple(int(v) for v in ms.points[0]) == tuple(int(v) for v in analytic._modal_dynamics(p, 0.5, 300, 0.0, 0.0)["points"][0])
    t63 = []
    for dx in (0.0, 0.05):
        t, z, r = analytic.step_responses(_strong_sink_board(dx), cell_mm=0.5, n_terms=300, t_end=3000.0, n_times=400)
        t63.append(float(np.exp(np.interp(np.log(0.632 * r[0]), np.log(z[0]), np.log(t)))))
    assert abs(t63[1] / t63[0] - 1.0) < 2e-3


def test_readout_point_rule():
    """!
    @brief _readout_point keeps the start point within the tolerance and otherwise reads the maximum nearest to it.
    @return None.
    """
    rise = np.ones((2, 5, 5))
    rise[0, 2, 2] = 1.0 - 0.5 * analytic.READOUT_TOLERANCE                 # the start point inside the band: kept
    assert analytic._readout_point(rise, (0, 2, 2), 1e-3, 1e-3) == (0, 2, 2)
    rise[0, 2, 2] = 1.0 - 2.0 * analytic.READOUT_TOLERANCE                 # outside: the nearest maximum on the same layer
    assert analytic._readout_point(rise, (0, 2, 2), 1e-3, 1e-3) in {(0, 1, 2), (0, 3, 2), (0, 2, 1), (0, 2, 3)}
    rise[0] = 0.5
    assert analytic._readout_point(rise, (0, 2, 2), 1e-3, 1e-3) == (1, 2, 2)  # another layer only when the start layer has no maximum
