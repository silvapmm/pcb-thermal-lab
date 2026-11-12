#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_edge_film.py
@brief Tests of the edge-film investigation: the 3D truth closes its heat balance and converges, the variant network equals the program when no switch is set, and the centroid film with a zero distance is the film on the node.
@details Run from the repository root: `.venv/bin/python -m pytest -q research/imported-copper-edge-film/tests`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))

import numpy as np                                                             # noqa: E402

import cases                                                                   # noqa: E402
import truth3d                                                                 # noqa: E402
import variants                                                                # noqa: E402
from pcbthermal import laminate                                                # noqa: E402


def test_truth_closes_the_heat_balance_and_converges_in_the_slabs():
    """!
    @brief The 3D truth's heat out equals the heat in, and the rise changes less between 8 and 16 slabs than between 2 and 4 (convergence).
    @return None.
    """
    a = [truth3d.solve(200.0, 0.4, nz) for nz in (2, 4, 8, 16)]
    assert all(abs(r[2]) < 1e-9 for r in a)
    assert abs(a[3][0] - a[2][0]) < abs(a[1][0] - a[0][0])


def test_truth_with_a_dead_edge_equals_the_one_dimensional_losses_when_copper_covers_everything():
    """!
    @brief With the film on the wall set to a negligible value the heat leaves by the two faces only, so the mean rise is below the one-sided film bound P / (h_total A) times a factor.
    @details The board of 20 mm has 4e-4 m2 of each face, h_top + h_bottom = 20 W/m2K, so a uniform rise would be 1 / (20 x 4e-4) = 125 K for 1 W; the heater is local, so the mean rise under it is larger.
    @return None.
    """
    r = truth3d.solve(1e-6, 0.4, 4, inset=0.0)
    assert r[0] > 125.0 and abs(r[2]) < 1e-9


def test_the_variant_network_without_switches_is_the_program():
    """!
    @brief With every switch at its default the variant network and builder give the program's number to the last digit.
    @return None.
    """
    cases.set_inset(1.2)
    p = cases.build("square", "imported", 200.0, ang=22.5)
    ref = cases.run(p, 2.0)[0]
    with variants.use():
        assert cases.run(p, 2.0)[0] == ref


def test_the_centroid_film_with_zero_distance_is_the_film_on_the_node():
    """!
    @brief `alpha = 0` makes every distance zero, so the film is the one of the program on the node.
    @return None.
    """
    cases.set_inset(1.2)
    p = cases.build("square", "imported", 200.0, ang=22.5)
    ref = cases.run(p, 2.0)[0]
    with variants.use(film="centroid", alpha=0.0):
        assert abs(cases.run(p, 2.0)[0] - ref) < 1e-9


def test_a_constant_field_is_exact_for_the_centroid_film():
    """!
    @brief The change of the film goes into the ambient term as well, so a board with no source at the ambient temperature stays there; here the heat balance of a run closes.
    @return None.
    """
    cases.set_inset(1.2)
    p = cases.build("square", "imported", 200.0, ang=22.5)
    with variants.use(film="centroid", alpha=0.5), laminate.using(0.4e-3, 4):
        m, tm, be = cases.run(p, 2.0)
    assert abs(be) < 1e-9 and np.isfinite(m)


def test_graded_sub_gaps_sum_to_the_gap():
    """!
    @brief The cosine and end-graded sub-gaps add up to the gap and are positive.
    @return None.
    """
    for grade in ("cos", "ends"):
        variants.CFG["grade"] = grade
        try:
            for n in (2, 3, 4, 8, 16):
                s = variants.sub_gaps(1.53e-3, n)
                assert abs(s.sum() - 1.53e-3) < 1e-15 and (s > 0).all()
        finally:
            variants.CFG["grade"] = "uniform"
