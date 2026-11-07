#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_lumped_first_ring.py
@brief The first ring of the Lumped network is at most one equivalent radius of the footprint wide (research/lumped-ring-uniform-deficit, INTEGRATION.md 1 and 3).

@details Before the cap the ring next to a small part was 0.04 of the distance to the farthest cell of the board wide, so the result of a 1 mm part on a uniform two-layer
         sheet fell with the board (centred, against the FVM at 0.5 mm: 60 x 40 mm -1.4 %, 100 x 80 mm -13.7 %, 200 x 150 mm -25.3 %). The tests hold: the rule of `lumped.ring_edges`
         (cap, floor of 1.5 cells, no effect where the footprint is wide enough), the independent 3D layered solver and the FVM on a 100 x 80 mm sheet, the independence from the board
         size, the time to 63 % against the FVM step response, the shapes (aspect 1 and 3, a thin tab) and the bit identity of every board where the cap does not act (the example board,
         steady and step response).
"""

import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "helpers"))
import layered3d as L3                                         # noqa: E402

from pcbthermal import Problem, SolverOptions, api, examples, lumped, profiles, simulate   # noqa: E402
from pcbthermal.model import Materials                         # noqa: E402

DX = 0.5e-3


def sheet(w_mm, h_mm, sx_mm, sy_mm=None, pos=None):
    """!
    @brief A uniform two-layer board (35 um copper, 1.6 mm, films 10 / 15 W/m2K, edge 10 W/m2K) with one rectangular 1 W source on the top layer.
    @param w_mm Board width in mm.
    @param h_mm Board height in mm.
    @param sx_mm Source width in mm.
    @param sy_mm Source height in mm (None: square).
    @param pos (x, y) centre of the source in mm (None: the board centre).
    @return Problem.
    """
    sy_mm = sx_mm if sy_mm is None else sy_mm
    cx, cy = pos if pos is not None else (w_mm / 2, h_mm / 2)
    p = Problem.new(w_mm, h_mm, layers=2, thickness_mm=1.6, copper_um=35.0, h_top=10.0, h_bottom=15.0, h_side=10.0)
    p.add_full_copper(fill=1.0)
    p.add_heater(1, 1.0, rect=(cx - sx_mm / 2, cy - sy_mm / 2, cx + sx_mm / 2, cy + sy_mm / 2), name="U")
    return p


def rise(p, model, cell_mm=0.5):
    """!
    @brief Hottest rise of one model.
    @param p Problem.
    @param model Model key.
    @param cell_mm Cell in mm.
    @return float Rise over the ambient in K.
    """
    return simulate(p, SolverOptions(models=(model,), cell_mm=cell_mm)).results[model].t_max - p.board.ambient


def err(a, b):
    """!
    @brief Relative difference in percent.
    @param a Value.
    @param b Reference.
    @return float 100 (a / b - 1).
    """
    return 100.0 * (a / b - 1.0)


# --- The rule of ring_edges ---------------------------------------------------------------------------------------------------------------------------

def test_first_ring_is_one_cell_and_a_half_for_a_tiny_footprint_on_a_big_board():
    """!
    @brief A one-cell footprint on a 0.5 m board: the first ring is 1.5 cells, not 0.04 of the distance to the farthest cell.
    @return None.
    """
    dx = 0.5e-3
    a_eq = math.sqrt(dx * dx / math.pi)
    e = lumped.ring_edges(0.3, dx, dx, 10, a_eq=a_eq)
    assert e[1] == pytest.approx(1.5 * dx)
    assert lumped.ring_edges(0.3, dx, dx, 10)[1] == pytest.approx(0.04 * 0.3)      # the program without the cap


def test_cap_never_acts_on_a_footprint_wider_than_the_old_first_ring():
    """!
    @brief A 10 mm square footprint, a board where 0.04 rho_max is under its equivalent radius: the edges are those of the program to the last bit.
    @return None.
    """
    dx = 0.5e-3
    a_eq = math.sqrt(400 * dx * dx / math.pi)                    # 10 mm square = 20 x 20 cells: 5.64 mm
    for rho_max in (0.02, 0.05, 0.1, 0.14):                       # 0.04 rho_max up to 5.6 mm
        assert np.array_equal(lumped.ring_edges(rho_max, dx, dx, 10, a_eq=a_eq), lumped.ring_edges(rho_max, dx, dx, 10))
    big = lumped.ring_edges(0.3, dx, dx, 10, a_eq=a_eq)           # here 0.04 rho_max = 12 mm: the cap acts
    assert big[1] == pytest.approx(a_eq)


def test_cap_is_the_equivalent_radius_and_never_below_one_and_a_half_cells():
    """!
    @brief For any footprint and board the first edge is between 1.5 cells and max(1.5 cells, a_eq) when the old ring was wider than the cap.
    @return None.
    """
    dx = 1.0e-3
    for n_cells in (1, 4, 9, 36, 400):
        a_eq = math.sqrt(n_cells * dx * dx / math.pi)
        for rho_max in (0.05, 0.2, 0.5):
            e1 = lumped.ring_edges(rho_max, dx, dx, 10, a_eq=a_eq)[1]
            old = lumped.ring_edges(rho_max, dx, dx, 10)[1]
            assert e1 >= 1.5 * dx - 1e-15
            assert e1 <= old + 1e-15                                          # the cap only narrows
            assert e1 <= max(1.5 * dx, a_eq) + 1e-15


def test_the_equivalent_radius_helper_counts_the_touched_cells():
    """!
    @brief a_eq = sqrt(N0 dx dy / pi), with at least one cell.
    @return None.
    """
    foot = np.zeros((5, 5), dtype=bool)
    foot[1:3, 1:4] = True                                        # 6 cells
    assert lumped._equivalent_radius(foot, 2e-3, 1e-3) == pytest.approx(math.sqrt(6 * 2e-6 / math.pi))
    assert lumped._equivalent_radius(np.zeros((3, 3), dtype=bool), 1e-3, 1e-3) == pytest.approx(math.sqrt(1e-6 / math.pi))


# --- The numbers on a simple big board ----------------------------------------------------------------------------------------------------------------

def test_one_mm_part_on_100_by_80_agrees_with_the_independent_3d_solver():
    """!
    @brief The 1 mm part at the centre of a 100 x 80 mm uniform sheet against the independent 3D layered solver (cell mean of the source cells, 0.5 mm).
    @details Before the cap the Lumped read -13.7 % of the FVM here; with it the Lumped is within 1 % of the FVM and of the 3D solver (measured 44.78 against 44.81 K).
    @return None.
    """
    cu_t, gap, k_cu, k_fr4, h = 35e-6, 1.5e-3, 400.0, 0.4, 10.0
    w, hh, side = 100e-3, 80e-3, 1e-3
    c = (w / 2, hh / 2)
    ref = L3.solve(DX, int(round(w / DX)), int(round(hh / DX)), [(cu_t, k_cu, 1), (gap, k_fr4, 2), (cu_t, k_cu, 1)],
                   (c[0] - side / 2, c[1] - side / 2, c[0] + side / 2, c[1] + side / 2), 1.0, h, h, film_under_source=True)["cell_mean_source"]
    mat = Materials(k_copper=k_cu, k_fr4_through=k_fr4, k_fr4_inplane=k_fr4)
    p = Problem.new(100.0, 80.0, layers=2, thickness_mm=(2 * cu_t + gap) * 1e3, copper_um=cu_t * 1e6, ambient=0.0, h_top=h, h_bottom=h, h_side=None, materials=mat)
    p.add_full_copper()
    p.add_heater(1, 1.0, rect=(49.5, 39.5, 50.5, 40.5), name="U")
    lum = rise(p, "lumped")
    assert abs(err(lum, ref)) < 2.0, (lum, ref)


def test_one_mm_part_on_100_by_80_is_within_a_few_percent_of_the_fvm():
    """!
    @brief The same board with the program's film coefficients: the Lumped against the FVM at 0.5 mm (program before the cap: -13.7 %, after +1.0 %).
    @return None.
    """
    p = sheet(100, 80, 1.0)
    assert abs(err(rise(p, "lumped"), rise(p, "fvm"))) < 5.0


def test_result_of_a_small_part_does_not_follow_the_distance_to_the_farthest_cell():
    """!
    @brief 30 x 20, 60 x 40, 100 x 80 and 200 x 150 mm: the Lumped error against the FVM of a 1 mm part stays within a few percent (before the cap -25 % on the largest).
    @return None.
    """
    errors = []
    for (w, h) in ((30, 20), (60, 40), (100, 80), (200, 150)):
        p = sheet(w, h, 1.0)
        errors.append(err(rise(p, "lumped"), rise(p, "fvm")))
    assert max(abs(e) for e in errors) < 5.0, errors
    assert max(errors) - min(errors) < 5.0, errors


@pytest.mark.parametrize("sx,sy,low,high", [
    (1.0, 1.0, -5.0, 5.0),                                       # aspect 1
    (3.0, 1.0, 0.0, 15.0),                                       # aspect 3: the documented hot side (+10 %), held from growing
    (6.0, 2.0, -6.0, 8.0),
    (10.0, 0.5, -12.0, 8.0),                                     # a thin tab
])
def test_shapes_on_100_by_80_against_the_fvm(sx, sy, low, high):
    """!
    @brief Rectangles of aspect 1, 3 and a thin tab on 100 x 80 mm (measured +1.0, +10.1, -1.7 and -5.4 %).
    @param sx Source width in mm.
    @param sy Source height in mm.
    @param low Lower bound of the error in percent.
    @param high Upper bound of the error in percent.
    @return None.
    """
    p = sheet(100, 80, sx, sy)
    e = err(rise(p, "lumped"), rise(p, "fvm"))
    assert low < e < high, e


def test_aspect_three_part_on_200_by_150_reads_hot_by_less_than_fifteen_percent():
    """!
    @brief A 3 x 1 mm part on 200 x 150 mm: +9.3 % of the FVM with the cap (the hot side is documented, the test keeps it from growing).
    @return None.
    """
    p = sheet(200, 150, 3.0, 1.0)
    e = err(rise(p, "lumped"), rise(p, "fvm"))
    assert 0.0 < e < 15.0, e


def test_time_to_63_percent_of_a_small_part_follows_the_fvm_step_response():
    """!
    @brief The 1 mm part on 100 x 80 mm: time to 63 % of the Lumped step response within 10 % of the FVM's at 0.5 mm (program before the cap: 1.9 times).
    @return None.
    """
    p = sheet(100, 80, 1.0)
    lum = api.step_response(p, "lumped", SolverOptions(models=("lumped",), cell_mm=0.5))
    fvm = profiles.step_response_fvm(p, cell_mm=0.5)

    def t63(resp):
        return float(np.interp(0.632 * resp.rth[0], np.asarray(resp.z)[0], resp.times))

    assert abs(err(t63(lum), t63(fvm))) < 10.0, (t63(lum), t63(fvm))


# --- Nothing moves where the cap does not act ----------------------------------------------------------------------------------------------------------

def _without_cap(monkeypatch):
    """!
    @brief Make lumped.ring_edges ignore the cap (the program as it was).
    @param monkeypatch pytest fixture.
    @return None.
    """
    original = lumped.ring_edges
    monkeypatch.setattr(lumped, "ring_edges", lambda rho_max, dx, dy, rings, min_width=None, a_eq=None: original(rho_max, dx, dy, rings, min_width))


def test_example_board_is_bit_identical_steady_and_step_response(monkeypatch):
    """!
    @brief The example board (cell 1 mm): the cap does not act, so the Lumped field and the step response are those of the program to the last bit.
    @param monkeypatch pytest fixture.
    @return None.
    """
    p = examples.example_board()
    opts = SolverOptions(models=("lumped",), cell_mm=1.0)
    t_new = np.array(simulate(p, opts).results["lumped"].T)
    r_new = np.array(api.step_response(p, "lumped", opts).z)
    _without_cap(monkeypatch)
    t_old = np.array(simulate(p, opts).results["lumped"].T)
    r_old = np.array(api.step_response(p, "lumped", opts).z)
    assert np.array_equal(t_new, t_old)
    assert np.array_equal(r_new, r_old)


def test_the_cap_does_act_on_a_small_part_of_a_big_board(monkeypatch):
    """!
    @brief The control of the previous test: on the 200 x 150 mm sheet the old and the new fields differ.
    @param monkeypatch pytest fixture.
    @return None.
    """
    p = sheet(200, 150, 1.0)
    new = rise(p, "lumped")
    _without_cap(monkeypatch)
    old = rise(p, "lumped")
    assert new > 1.2 * old
