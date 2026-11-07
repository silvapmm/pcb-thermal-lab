#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_robin2d.py
@brief Tests of the independent Robin solver of `lib/robin2d.py`: geometry against closed forms, a constant solution, the order of accuracy, the stiff-edge behaviour.
@details Run from the repository root: `.venv/bin/python -m pytest -q research/bochkov-robin-check/tests`.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
import robin2d as R  # noqa: E402


def test_triangle_geometry_closed_forms():
    """!
    @brief Cell volumes add up to the triangle area and the boundary pieces to the perimeter.
    @return None
    """
    dom = R.thesis_triangle()
    v = dom.v
    area = 0.5 * abs(np.sum(v[:, 0] * np.roll(v[:, 1], -1) - np.roll(v[:, 0], -1) * v[:, 1]))
    r = R.solve(dom, 65, shift=(0.1, -0.2), scheme="bg")
    assert abs(r["V"].sum() - area) < 2e-6 * area
    h = r["h"]
    xs = -1 + 0.1 * h + np.arange(65) * h
    ys = -1 - 0.2 * h + np.arange(65) * h
    pc = dom.pieces(np.concatenate([xs - h / 2, [xs[-1] + h / 2]]), np.concatenate([ys - h / 2, [ys[-1] + h / 2]]))
    assert abs(pc["w"].sum() - dom.len.sum()) < 1e-12


def test_disc_geometry_closed_forms():
    """!
    @brief Disc: summed arc pieces equal 2 pi r and the strip area is pi r^2 to 1e-5.
    @return None
    """
    dom = disc = R.disc_domain()
    r = R.solve(disc, 65, shift=(0.3, 0.2), scheme="bg")
    assert abs(r["V"].sum() - np.pi * 0.49) < 1e-5 * np.pi * 0.49
    h = r["h"]
    xs = -1 + 0.3 * h + np.arange(65) * h
    ys = -1 + 0.2 * h + np.arange(65) * h
    pc = dom.pieces(np.concatenate([xs - h / 2, [xs[-1] + h / 2]]), np.concatenate([ys - h / 2, [ys[-1] + h / 2]]))
    assert abs(pc["w"].sum() - 2 * np.pi * 0.7) < 1e-12


def _const_disc(scale):
    """!
    @brief A disc whose exact solution is the constant 1 (f = 0, g = alpha) with a constant alpha (with a variable alpha the pairing is exact only to O(h^2)).
    @param scale Robin coefficient multiplier.
    @return Disc domain.
    """
    return R.Disc((0.1, -0.05), 0.7, lambda x, y: scale * np.ones_like(x), lambda x, y: np.ones_like(x), lambda x, y: (0 * x, 0 * x))


def test_constant_solution_is_exact_every_scheme():
    """!
    @brief A constant is reproduced to round-off by every scheme, at every stiffness (checks the sign pairing of the diagonal and the right-hand side).
    @return None
    """
    for scale in (1.0, 100.0, 1e4):
        dom = _const_disc(scale)
        for sch, kw in (("bg", {}), ("nofilm", {}), ("film", {}), ("film", {"rational": True})):
            r = R.solve(dom, 33, shift=(0.2, 0.1), scheme=sch, f=lambda x, y: 0 * x, **kw)
            ins = dom.inside(r["X"], r["Y"])
            if sch == "bg" and scale > 10:
                continue  # eq. 1.14 has negative denominators there (documented): no claim
            assert np.nanmax(np.abs(r["u"][ins & r["active"]] - 1.0)) < 1e-8, (scale, sch, kw)


def test_order_of_accuracy_on_disc_and_triangle():
    """!
    @brief The symmetric scheme converges with order near two in the solution and about one in the gradient (thesis section 1.4.4, 1.5.2).
    @return None
    """
    shifts = [(-0.3, -0.3), (0.0, 0.2), (0.3, 0.0)]
    for dom, lo_u in ((R.disc_domain(), 1.6), (R.thesis_triangle(), 1.3)):
        eu = []
        eg = []
        for n in (33, 65, 129):
            a = b = 0.0
            for s in shifts:
                e = R.errors(dom, R.solve(dom, n, shift=s, scheme="bg"))
                a, b = max(a, e[0]), max(b, e[1])
            eu.append(a)
            eg.append(b)
        order_u = np.log(eu[0] / eu[-1]) / np.log(4.0)
        order_g = np.log(eg[0] / eg[-1]) / np.log(4.0)
        assert order_u > lo_u, order_u
        assert 0.5 < order_g < 1.6, order_g


def test_film_matches_bg_on_smooth_disc_and_survives_stiff_edge():
    """!
    @brief On a smooth disc with a soft edge film and bg agree; with a stiff edge the unfloored eq. 1.14 breaks and the floored series film does not.
    @return None
    """
    dom = R.disc_domain(1.0)
    e_bg = R.errors(dom, R.solve(dom, 65, shift=(0.1, 0.1), scheme="bg"))[0]
    e_f = R.errors(dom, R.solve(dom, 65, shift=(0.1, 0.1), scheme="film"))[0]
    assert abs(e_f - e_bg) < 0.2 * e_bg
    stiff = R.disc_domain(1e4)
    worst_bg = max(R.errors(stiff, R.solve(stiff, 33, shift=s, scheme="bg"))[0] for s in ((0.0, 0.0), (0.3, 0.1)))
    worst_f = max(R.errors(stiff, R.solve(stiff, 33, shift=s, scheme="film"))[0] for s in ((0.0, 0.0), (0.3, 0.1)))
    assert worst_bg > 0.5 and worst_f < 0.05
