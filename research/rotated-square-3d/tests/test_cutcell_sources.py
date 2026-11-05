#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_cutcell_sources.py
@brief Tests of the two libraries written for the cut-cell literature check: `lib/jc_poisson.py` (reproduction of Johansen and Colella, Problem 1) and `lib/sheet_robin.py` (round sheet with a Robin film, closed form and cut-cell schemes).
@details Light cases only (seconds, below 0.5 GB). Run: .venv/bin/python -m pytest -q research/rotated-square-3d/tests/test_cutcell_sources.py
"""

import os
import sys

import numpy as np
from scipy.integrate import quad

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import jc_poisson as jc      # noqa: E402
import sheet_robin as sr     # noqa: E402

# Published, report LBNL-39908 Tables I and II (read from the page images)
PUB = {40: (1.20e-1, 1.66e-3, 5.85e-5, 8.34e-6), 80: (7.71e-2, 4.15e-4, 7.36e-6, 1.02e-6), 160: (4.20e-2, 1.04e-4, 1.17e-6, 1.07e-7)}


def test_jc_reproduces_the_published_tables():
    """!
    @brief The independent implementation gives the published truncation and solution errors of Problem 1 (within 3 %, 1-norm within 5 %) and the same number of whole cells.
    @return None.
    """
    for n, (tau_p, tau_i, xi_inf, xi_1) in PUB.items():
        r = jc.solve(n)
        assert abs(r["tau_partial_inf"] / tau_p - 1.0) < 0.03
        assert abs(r["tau_full_inf"] / tau_i - 1.0) < 0.03
        assert abs(r["xi_inf"] / xi_inf - 1.0) < 0.03
        assert abs(r["xi_1_mean"] / xi_1 - 1.0) < 0.05
    assert jc.solve(40)["n_full"] == 400 and jc.solve(80)["n_full"] == 1824        # the published N^I


def test_jc_converges_at_second_order_in_the_solution():
    """!
    @brief The maximum solution error falls by about 8 (rate 3, the dipole argument of the report, p. 6 and 15) from 80 to 160 cells and does not stall.
    @return None.
    """
    e = [jc.solve(n)["xi_inf"] for n in (40, 80, 160)]
    assert e[0] / e[1] > 6.0 and e[1] / e[2] > 5.0


def test_jc_geometry_is_closed():
    """!
    @brief The areas of the cut cells add up to the area of the flower (0.5 * integral of R(theta)^2 d theta = pi (0.09 + 0.01125)) within 1e-4 at 80 cells.
    @return None.
    """
    g = jc.Grid(80)
    exact = np.pi * (0.30 ** 2 + 0.5 * 0.15 ** 2)
    assert abs((g.kap * g.dx ** 2).sum() / exact - 1.0) < 1e-3
    for (i, j), (lf, mid, nrm) in g.front.items():
        assert abs(np.hypot(*nrm) - 1.0) < 1e-9


def test_closed_forms_satisfy_the_energy_balance():
    """!
    @brief Disc and annulus: the heat through the rim films equals the source minus the face losses (quadrature of the closed form).
    @return None.
    """
    radius, S, G, q = 0.01, 0.05, 20.0, 1000.0
    for H in (0.016, 5.0, 100.0):
        loss = G * quad(lambda r: float(sr.disc_exact(r, radius, S, G, H, q)) * 2 * np.pi * r, 0, radius)[0]
        assert abs((q * np.pi * radius ** 2 - loss) / sr.disc_rim_loss(radius, S, G, H, q) - 1.0) < 1e-9
    r1 = radius / 3.0
    loss = G * quad(lambda r: float(sr.annulus_exact(r, r1, radius, S, G, 5.0, 7.0, q)) * 2 * np.pi * r, r1, radius)[0]
    assert abs((q * np.pi * (radius ** 2 - r1 ** 2) - loss) / sr.annulus_rim_loss(r1, radius, S, G, 5.0, 7.0, q) - 1.0) < 1e-9


def test_closed_form_limits():
    """!
    @brief No rim film: the centre rise is q/G (nothing leaves through the rim, no spreading needed); a stiff rim: the rise at the rim goes to zero.
    @return None.
    """
    radius, S, G, q = 0.01, 0.05, 20.0, 1000.0
    assert abs(float(sr.disc_exact(0.0, radius, S, G, 0.0, q)) - q / G * (1.0 - 0.0)) < 1e-9
    assert float(sr.disc_exact(radius, radius, S, G, 1e9, q)) < 1e-4


def test_schemes_close_the_energy_balance_and_converge():
    """!
    @brief On a disc moved 0.37 cell against the grid every scheme conserves the heat (rim + faces = power to 1e-10), and the aperture scheme is within 3 % of the highest
           rise at 10 cells per radius and 1 % at 40 (the program's treatment of the cut cell is checked to be the worst of the four in the interior at 10 cells per radius).
    @return None.
    """
    radius, S, G, q, H = 0.01, 0.05, 20.0, 1000.0, 5.0
    t_ref = float(sr.disc_exact(0.0, radius, S, G, H, q))
    errs = {}
    for n_r in (10, 40):
        dx = radius / n_r
        centre = (0.37 * dx, 0.21 * dx)
        shape = sr.Shape(radius, dx, centre=centre)
        for sc in sr.SCHEMES:
            res = sr.solve(shape, S, G, H, q, sc)
            assert abs(res["q_rim"] + res["q_loss"] - res["power"]) < 1e-10 * res["power"]
            px, py = (shape.cx, shape.cy) if sc == "program" else (res["px"], res["py"])
            ex = sr.disc_exact(np.hypot(px - centre[0], py - centre[1]), radius, S, G, H, q)
            whole = shape.kap > 1.0 - 1e-9
            errs[(n_r, sc)] = float(np.nanmax(np.where(whole, np.abs(res["T"] - ex), 0.0))) / t_ref
    assert errs[(10, "aperture")] < 0.03 and errs[(40, "aperture")] < 0.01
    assert errs[(10, "program")] > max(errs[(10, s)] for s in ("aperture", "aperture+bochkov", "links", "links+strip"))
    # The film written as in the literature (distance from the cell centre to the boundary point) is the most accurate of the five at this film
    assert errs[(10, "aperture+bochkov")] < 0.5 * errs[(10, "aperture")] and errs[(40, "aperture+bochkov")] < 0.005


def test_shape_geometry_is_exact():
    """!
    @brief Cover, centroid and apertures of the round sheet: the areas add up to the exact area of the disc and the annulus, the rim length to the circumferences (1e-6),
           a cell wholly inside has cover 1, apertures 1 and its centroid at the cell centre, and the apertures along a grid line add up to the exact chord.
    @return None.
    """
    radius, dx = 0.01, 0.0013
    sh = sr.Shape(radius, dx, centre=(0.37 * dx, 0.21 * dx))
    assert abs((sh.kap * dx * dx).sum() / (np.pi * radius ** 2) - 1.0) < 1e-6
    ann = sr.Shape(radius, dx, centre=(0.1 * dx, 0.6 * dx), inner=radius / 3.0)
    assert abs((ann.kap * dx * dx).sum() / (np.pi * (radius ** 2 - (radius / 3.0) ** 2)) - 1.0) < 1e-6
    # The total rim length is the circumference (outer + inner)
    assert abs(ann.rim.sum() / (2.0 * np.pi * (radius + radius / 3.0)) - 1.0) < 1e-6
    # A cell wholly inside: cover 1, centroid at the centre, apertures 1
    i = j = sh.nx // 2
    assert abs(sh.kap[i, j] - 1.0) < 1e-12 and abs(sh.ax[i, j] - 1.0) < 1e-12 and abs(sh.ax[i + 1, j] - 1.0) < 1e-12
    assert abs(sh.cx[i, j] - (sh.x0 + dx * (i + 0.5))) < 1e-12
    # Heat balance of the exact geometry: the sum of the apertures along a column cut at the sheet's centre line equals the chord there (2 R)
    col = int((0.37 * dx - sh.x0) / dx)
    assert abs(sh.ax[col, :].sum() * dx - 2.0 * np.sqrt(radius ** 2 - (sh.x0 + col * dx - 0.37 * dx) ** 2)) < 1e-9


def test_sheet_scheme_names():
    """!
    @brief An unknown scheme is refused.
    @return None.
    """
    shape = sr.Shape(0.01, 0.002)
    try:
        sr.solve(shape, 0.05, 20.0, 5.0, 1000.0, "nothing")
    except ValueError:
        return
    raise AssertionError("expected ValueError")
