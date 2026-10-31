#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_ref3d.py
@brief Tests of lib/ref3d.py: it reproduces the resolved solver of bare-spot-under-source, closes the energy balance, gives a series circuit for a uniform column, the graded sub-slabs do not
        change a 1D column, and the Richardson extrapolation returns the limit and the order of a known sequence. Small boards.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "bare-spot-under-source", "lib"))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

import boards as BD  # noqa: E402
import ref3d as R3  # noqa: E402
import resolved3d as RS  # noqa: E402


def test_same_as_the_resolved_solver():
    """!
    @brief The face peak of a two-layer board with a window equals that of bare-spot-under-source/lib/resolved3d.py (same slabs, equal sub-gaps) to 1e-9.
    @return None.
    """
    spec = BD.Spec("w", layers=2, size=12.0, part=4.0, shapes=[("window", 4), ("full",)])
    p = BD.problem(spec)
    mine = R3.solve_spec(spec, p, 0.5, 4, quadrant=False)
    nb = BD.board_numbers(p)
    n = 24
    c = 6.0
    masks = RS.window_masks(n, n, 0.5e-3, 2, tuple(v * 1e-3 for v in BD.centred(4, 12.0)), (0,))
    sl = RS.build_slabs(2, masks, nb["k_cu"], nb["gaps"], nb["t_cu"], 4, nb["kxy"], nb["kz"])
    ref = RS.solve(0.5e-3, n, n, sl, tuple(v * 1e-3 for v in BD.centred(4, 12.0)), spec.power, nb["h_top"], nb["h_bottom"])
    assert abs(mine["max"] - ref["max"]) < 1e-9 * ref["max"]
    assert abs(mine["balance"] - 1.0) < 1e-9 and abs(ref["balance"] - 1.0) < 1e-9


def test_quadrant_equals_full_board():
    """!
    @brief A symmetric board solved on its quadrant (sides insulated) gives the full-board peak.
    @return None.
    """
    spec = BD.Spec("q", layers=2, size=12.0, part=4.0, shapes=[("pad", 6), ("none",)])
    p = BD.problem(spec)
    a = R3.solve_spec(spec, p, 0.5, 4, quadrant=True)["max"]
    b = R3.solve_spec(spec, p, 0.5, 4, quadrant=False)["max"]
    assert abs(a - b) < 1e-9 * b


def test_uniform_column_is_a_series_circuit():
    """!
    @brief A heater over the whole board on a uniform two-layer board: the rise is P times the series of the films and the gap (the copper is isothermal), whatever the grading.
    @return None.
    """
    spec = BD.Spec("col", layers=2, size=12.0, part=12.0)
    p = BD.problem(spec)
    nb = BD.board_numbers(p)
    A = 12e-3 ** 2
    # Top face to ambient in parallel with the path through the gap to the bottom film
    r_gap = nb["gaps"][0] / (nb["kz"][0] * A) + 1.0 / (nb["h_bottom"] * A)
    g = nb["h_top"] * A + 1.0 / r_gap
    expected = spec.power / g
    for nsub, ratio in ((1, 1.0), (4, 1.0), (4, 2.0), (8, 1.5)):
        got = R3.solve_spec(spec, p, 1.0, nsub, ratio, quadrant=False)["mean"]
        # The face of a source cell is the node plus half a copper cell: the copper is 35 um of 385 W/mK, 1e-7 m2K/W, negligible against 5e-4
        assert abs(got / expected - 1.0) < 2e-3, (nsub, ratio, got, expected)


def test_richardson_on_a_known_sequence():
    """!
    @brief f(h) = 1 + 2 h^2 on h = 4, 2, 1: limit 1, order 2, GCI of the fine grid as the formula says.
    @return None.
    """
    f = [1 + 2 * 16, 1 + 2 * 4, 1 + 2 * 1]
    r = R3.richardson(f, 2.0)
    assert abs(r["limit"] - 1.0) < 1e-12 and abs(r["order"] - 2.0) < 1e-12 and r["monotone"]
    assert abs(r["gci_fine"] - 1.25 * abs((3 - 9) / 3) / 3) < 1e-12


def test_transient_goes_to_the_steady_value():
    """!
    @brief The step response of the reference tends to its steady solution (long time, small board).
    @return None.
    """
    spec = BD.Spec("tr", layers=2, size=12.0, part=4.0, shapes=[("pad", 6), ("none",)])
    p = BD.problem(spec)
    st = R3.solve_spec(spec, p, 1.0, 4, quadrant=False)
    tr = R3.transient_spec(spec, p, 1.0, 4, [1.0, 10.0, 100.0, 3000.0], quadrant=False)
    assert tr["peak"][0] < tr["peak"][1] < tr["peak"][2] <= tr["peak"][3] * 1.0001
    assert abs(tr["peak"][3] / st["max_centre"] - 1.0) < 2e-3
