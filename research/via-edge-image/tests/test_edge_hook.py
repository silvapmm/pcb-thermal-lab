#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_edge_hook.py
@brief Tests of the edge image candidates: the Robin line image satisfies its boundary condition, the limits of the film length, the program is untouched without a wall, and the mirror removes the excess at the nearest via.
@details Run: `.venv/bin/python -m pytest -q research/via-edge-image/tests`.
"""

import logging
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import paths  # noqa: E402,F401
import edge_hook as eh  # noqa: E402
import edge_reference as er  # noqa: E402
import program_cases as pc  # noqa: E402
from pcbthermal import viawell  # noqa: E402


def _image_potential(x, y, delta, ell):
    """!
    @brief ln r + ln r' - (2 / l) int exp(-s/l) ln r'(s) ds for a source at (delta, 0) and a wall at x = 0 (the domain is x > 0).
    @param x Field point x.
    @param y Field point y.
    @param delta Distance of the source from the wall.
    @param ell Film length.
    @return float.
    """
    u = 0.5 * math.log((x - delta) ** 2 + y ** 2) + 0.5 * math.log((x + delta) ** 2 + y ** 2)
    line = sum(w * 0.5 * math.log((x + delta + ell * t) ** 2 + y ** 2) for t, w in zip(eh._GL_X, eh._GL_W))
    return u - 2.0 * line


def test_line_image_satisfies_the_robin_condition():
    """!
    @brief du/dx - u / l = 0 on the wall for the point image plus the exponential line image (finite differences).
    @return None.
    """
    for ell in (0.3, 1.0, 5.0):
        for y in (0.0, 0.7, 2.0):
            h = 1e-5
            ux = (_image_potential(h, y, 1.0, ell) - _image_potential(0.0, y, 1.0, ell)) / h
            u = _image_potential(0.0, y, 1.0, ell)
            assert abs(ux - u / ell) < 5e-4 * max(1.0, abs(u / ell)), (ell, y, ux, u / ell)


def test_limits_of_the_film_length():
    """!
    @brief Phi_true goes to ln D for an insulated wall and to -ln D for an isothermal one.
    @return None.
    """
    d = 2 * 0.3e-3
    assert abs(eh.phi_true(0.3e-3, 0.15e-3, math.inf) - math.log(d)) < 1e-12
    # For a very long film Phi carries the constant -2 (ln l - gamma) (a gauge that cancels in c); its dependence on the distance is that of the insulated wall
    dphi = eh.phi_true(0.6e-3, 0.15e-3, 1e12) - eh.phi_true(0.3e-3, 0.15e-3, 1e12)
    assert abs(dphi - math.log(2.0)) < 1e-6
    assert abs(eh.phi_true(0.3e-3, 0.15e-3, 1e-9) + math.log(d)) < 1e-3


def test_robin_tends_to_mirror_for_a_long_film():
    """!
    @brief The edge term of a very long film equals the insulated one (up to the common gauge, which cancels in c).
    @return None.
    """
    w = {(5, 9): 0.5, (4, 9): 0.5}
    c_m = eh.edge_term(w, 1e-3, (9.84e-3, 5e-3), 0.15e-3, [("x", 10e-3)], [math.inf], "mirror")
    c_r = eh.edge_term(w, 1e-3, (9.84e-3, 5e-3), 0.15e-3, [("x", 10e-3)], [1e9], "robin")
    assert abs(c_m - c_r) < 1e-4


def test_mirror_term_of_the_nearest_via_is_positive():
    """!
    @brief A via 0.16 mm from the edge on a 1 mm cell has the lattice image farther than the true one: c = ln(D_lat / D_true) > 1.
    @return None.
    """
    w = {(5, 9): 0.5, (4, 9): 0.5}
    c = eh.edge_term(w, 1e-3, (9.84e-3, 5e-3), 0.15e-3, [("x", 10e-3)], [math.inf], "mirror")
    assert 1.0 < c < 1.6


@pytest.mark.skip(reason="obsolete by design: the program's via is the star coupling since feature/via-star-coupling, the hook patches the mean-potential via of 2.5.1")
def test_no_wall_no_change():
    """!
    @brief A via far from every wall: the patched build gives the program's blocks bit for bit.
    @return None.
    """
    logging.disable(logging.WARNING)
    pc.load_libraries()
    p = er.edge_board(4.0, True, None, None)
    a = pc.max_rise(p, "fvm", 0.5)
    with eh.patched("mirror"):
        b = pc.max_rise(p, "fvm", 0.5)
    # 4 mm is 8 cells at 0.5 mm: outside the reach of 6 cells
    assert a == b


@pytest.mark.skip(reason="obsolete by design: the program's via is the star coupling since feature/via-star-coupling, the hook patches the mean-potential via of 2.5.1")
def test_mirror_removes_the_excess_at_the_nearest_via():
    """!
    @brief The via effect of the via 0.16 mm from the edge on 1 mm cells: the program without its image is about 14 % high, the mirror prototype and the
           program (which has the image since `feature/via-edge-image`) within 2 % of the resolved reference, and equal to each other.
    @return None.
    """
    logging.disable(logging.WARNING)
    pc.load_libraries()
    p = er.edge_board(0.16, True, None, None)
    ref = er.via_effect_reference(p, 1.0 / 16.0)
    q = er.deepcopy_without_via(p)
    base = pc.max_rise(q, "fvm", 1.0)
    e_prog = base - pc.max_rise(p, "fvm", 1.0)
    with eh.patched("none"):
        e_none = base - pc.max_rise(p, "fvm", 1.0)
    with eh.patched("mirror"):
        e_img = base - pc.max_rise(p, "fvm", 1.0)
    assert e_none / ref - 1.0 > 0.12
    assert abs(e_img / ref - 1.0) < 0.02
    # The implementation in the program equals the prototype on a box edge (the reflex-corner guard of the program does not act here)
    assert abs(e_prog - e_img) < 1e-6 * ref


def test_kernel_is_exact_at_integers_and_continuous():
    """!
    @brief lattice_log at integer offsets is ln dx + (pi/2)(a - kappa) from the exact kernel table.
    @return None.
    """
    dx = 1e-3
    got = eh.lattice_log(np.array([1.0]), np.array([0.0]), dx)[0]
    assert abs(got - (math.log(dx) + math.pi / 2 * (viawell.lattice_kernel(1, 0) - viawell.KAPPA))) < 1e-12
