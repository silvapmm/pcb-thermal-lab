#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_review.py
@brief Tests of the reviewer's additions: the independent two-sheet solver, the vectorised apertures, the sliver anomaly against the independent reference, the film floor.
"""

import math
import os
import sys

import numpy as np
import pytest

LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import indep_sheet as ind        # noqa: E402
import vecaperture as va         # noqa: E402
import cutgeom                   # noqa: E402
import cutlinks as cl            # noqa: E402
import boards as bd              # noqa: E402
from pcbthermal import Problem, fvm   # noqa: E402


def _turn(pts, ang):
    """!
    @brief Turn mm points about (15, 15), in metres.
    @param pts Points in mm.
    @param ang Degrees.
    @return Array (n, 2) in m.
    """
    a = math.radians(ang)
    return np.array([[15 + (x - 15) * math.cos(a) - (y - 15) * math.sin(a), 15 + (x - 15) * math.sin(a) + (y - 15) * math.cos(a)] for x, y in pts]) * 1e-3


def test_independent_solver_energy_and_program():
    """!
    @brief The independent solver closes its energy balance and lands within 0.2 K of the program on an aligned rectangle at 0.25 mm (they differ only in the edge film placement).
    @return None.
    """
    t, bal = ind.solve(30e-3, 30e-3, 0.25e-3, 200.0, (10e-3, 10e-3, 13e-3, 13e-3))
    assert bal == pytest.approx(1.0, abs=1e-9)
    p = Problem.new(30, 30, 2, h_side=200).add_full_copper()
    p.add_heater(1, 2.0, rect=(10, 10, 13, 13))
    assert fvm.solve_steady(p, cell_mm=0.25).t_max - 25.0 == pytest.approx(t, abs=0.2)


@pytest.mark.parametrize("ang", [0, 7, 23, 45])
@pytest.mark.parametrize("pts", [
    [[5.3, 5.3], [24.7, 5.3], [24.7, 12.45], [12.45, 12.45], [12.45, 24.7], [5.3, 24.7]],
    [[0, 12], [10.37, 12], [10.37, 0], [19.63, 0], [19.63, 12], [30, 12], [30, 24], [0, 24]],
    [[5, 5], [25, 5], [25, 25], [15.6, 25], [15.4, 10.3], [15.2, 25], [5, 25]],
])
def test_vectorised_apertures_equal_the_prototype(pts, ang):
    """!
    @brief The vectorised apertures equal the prototype's clipped ones on a re-entrant L, the small T and a notch crossed twice, turned (to the prototype's 1e-6-cell offset).
    @param pts Outline in mm.
    @param ang Turn in degrees.
    @return None.
    """
    poly = _turn(pts, ang)
    g = cutgeom.cut_geometry_exact(poly, 30, 30, 1e-3, 1e-3)
    ax, ay = va.apertures(poly, 30, 30, 1e-3, 1e-3)
    assert np.abs(ax - g["ax"]).max() < 2e-5
    assert np.abs(ay - g["ay"]).max() < 2e-5


def test_sliver_anomaly_against_independent_reference():
    """!
    @brief The program's hottest point jumps between covers 0.01 and 0.02 of the edge column (h_side 200, 1 mm) against the independent reference; aperture does not.
    @return None.
    """
    errs = {}
    for c in (0.01, 0.02):
        e = 6.0 - c
        ref = ind.richardson(lambda h: ind.solve((25 - e) * 1e-3, 20e-3, h, 200.0, ((8 - e) * 1e-3, 8.5e-3, (11 - e) * 1e-3, 11.5e-3))[0] + 25.0,
                             (0.25e-3, 0.125e-3, 0.0625e-3))[0]
        p = Problem.new(30, 30, 2, h_side=200.0).add_full_copper()
        p.add_heater(1, 2.0, rect=(8.0, 13.5, 11.0, 16.5))
        p.set_outline([[e, 5], [25, 5], [25, 25], [e, 25]])
        errs[c] = {s: cl.tmax(p, 1.0, s) - ref for s in ("program", "aperture")}
    assert errs[0.02]["program"] - errs[0.01]["program"] > 3.0
    assert abs(errs[0.02]["aperture"] - errs[0.01]["aperture"]) < 0.3


def test_film_floor_binds_with_copper_held_off_the_edge():
    """!
    @brief With full copper the film factor stays far from the floor at h_side 2000; with the copper held inside the outline (bare-laminate nodes, film factor 1 - h |d| / k) it reaches it.
    @return None.
    """
    for pat, binds in ((False, False), (True, True)):
        p = bd.edge_board(angle=20, h_side=2000.0, pattern=pat, pc=0.5)
        p.validate()
        cl.CutLinkNetwork.mode = "aperture+film"
        n = cl.CutLinkNetwork(p, 30, 30)
        f = n.film_factor[:, n._edge_lengths() > 0]
        assert (f.min() <= 0.25 + 1e-12) == binds
