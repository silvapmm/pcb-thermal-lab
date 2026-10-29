#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_plate_h_level.py
@brief Tests of the plate-level investigation: the similarity solver against Ostrach's tables, the levels against their definitions, the in-memory patch of the program and the 2D plate solver (energy balance, limits).

Run: .venv/bin/python -m pytest -q research/plate-h-level/tests
"""

import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import levels as L                                        # noqa: E402
import plate2d as p2                                      # noqa: E402
import similarity as sim                                  # noqa: E402
from pcbthermal import convection                         # noqa: E402


@pytest.mark.parametrize("pr,thp", [(0.72, 0.5046), (0.733, 0.5080), (1.0, 0.5671), (2.0, 0.7165), (10.0, 1.1694), (100.0, 2.191)])
def test_ostrach_table(pr, thp):
    """!
    @brief -H'(0) of Table I of Ostrach (NACA Report 1111, pages 77 and 78) is reproduced by the collocation solver to 0.05 %.
    @param pr Prandtl number.
    @param thp Tabulated -H'(0).
    @return None.
    """
    assert -sim.bvp(pr)[1] == pytest.approx(thp, rel=5e-4)


def test_shooting_and_collocation_agree():
    """!
    @brief The two independent routes (own RK4 shooting, scipy collocation) agree on -theta'(0) at Pr 0.71 within 0.1 %.
    @return None.
    """
    assert sim.shoot(0.71)[1] == pytest.approx(sim.bvp(0.71)[1], rel=1e-3)


def test_profile_against_ostrach_rows():
    """!
    @brief Rows of Table I(b) (Pr 0.72): F' and H at eta 0.5, 1, 1.5, 2 read from the page image.
    @return None.
    """
    e, fp, th = sim.profile(0.72, eta_max=5.0, n=5000)
    for eta, f1, h in ((0.5, 0.2246, 0.7493), (1.0, 0.2759, 0.5168), (1.5, 0.2363, 0.3281), (2.0, 0.1697, 0.1945)):
        i = int(round(eta / 5.0 * 5000))
        assert fp[i] == pytest.approx(f1, abs=1e-3)
        assert th[i] == pytest.approx(h, abs=5e-4)


def test_exact_coefficient_and_fits():
    """!
    @brief The average coefficient at Pr 0.71 is (4/3) of the local one, 0.5157, and the Churchill-Chu term is within 0.3 % of it.
    @return None.
    """
    c = sim.coefficient(0.71, "bvp")
    assert c == pytest.approx(0.5157, abs=5e-4)
    assert c == pytest.approx(4.0 / 3.0 * (-sim.bvp(0.71)[1]) / (4 * 0.71) ** 0.25, rel=1e-12)
    assert sim.churchill_usagi(0.71) / c == pytest.approx(1.0, abs=0.003)
    assert 0.59 / c == pytest.approx(1.144, abs=0.003)


def test_levels_general_is_the_program():
    """!
    @brief The "general" and "laminar" levels equal the program's own forms, and `use_level` restores the function.
    @return None.
    """
    original = convection.h_natural_vertical
    for form in ("general", "laminar"):
        h0, ra0 = original(60.0, 20.0, 0.1, form)
        h1, ra1 = L.h_vertical(form, 60.0, 20.0, 0.1)
        assert h1 == pytest.approx(h0, rel=1e-12)
        assert ra1 == pytest.approx(ra0, rel=1e-12)
    with L.use_level("mcadams"):
        h, ra = convection.h_natural_vertical(60.0, 20.0, 0.1, "general")
        assert h == pytest.approx(L.h_vertical("mcadams", 60.0, 20.0, 0.1)[0])
    assert convection.h_natural_vertical is original


def test_levels_order_at_pcb_rayleigh():
    """!
    @brief At Ra = 1e5 the 0.59 level is above the laminar form, which is above the general form and the exact boundary layer, as in the README table.
    @return None.
    """
    n = {k: float(L.nu_level(k, 1e5, 0.71)) for k in L.LEVELS}
    assert n["mcadams"] > n["laminar"] > n["general"] > n["bl"]
    assert n["laminar"] / n["bl"] == pytest.approx(1.071, abs=0.003)


def test_unknown_level():
    """!
    @brief An unknown level is refused.
    @return None.
    """
    with pytest.raises(ValueError):
        L.nu_level("nope", 1e5, 0.71)


@pytest.fixture(scope="module")
def small_plate():
    """!
    @brief A small 2D case at Ra = 1e4 on a coarse grid, run once for the tests below.
    @return tuple (Plate2D, result dict).
    """
    m = p2.Plate2D(1e4, 0.71, nx=40, ny_plate=30, ny_below=14, ny_above=20, dx0=2.5e-3, dy_end=4e-3)
    r = m.run(dt=3.0 * m.x[1] ** 2, max_steps=60000, check=5000, tol=1e-4)
    return m, r


def test_plate2d_energy_balance(small_plate):
    """!
    @brief The heat leaving the domain equals the heat leaving the plate within 3 %.
    @param small_plate Fixture.
    @return None.
    """
    m, r = small_plate
    assert r["converged"]
    assert m.energy_balance() == pytest.approx(1.0, abs=0.03)


def test_plate2d_between_the_levels(small_plate):
    """!
    @brief At Ra = 1e4 the mean Nusselt number lies between the exact boundary layer (no leading edge) and 0.59 Ra^(1/4), within 8 % of the laminar form.
    @param small_plate Fixture.
    @return None.
    """
    m, r = small_plate
    assert float(L.nu_level("bl", 1e4, 0.71)) < r["nu"] < float(L.nu_level("mcadams", 1e4, 0.71)) * 1.0
    assert r["nu"] == pytest.approx(float(L.nu_level("laminar", 1e4, 0.71)), rel=0.08)


def test_plate2d_local_nu_decreases_up_the_plate(small_plate):
    """!
    @brief The local Nusselt number falls from the leading edge up to the upper part of the plate.
    @param small_plate Fixture.
    @return None.
    """
    m, _ = small_plate
    y, nu = m.nusselt_local()
    mid = len(y) // 2
    assert nu[2] > nu[mid] > 0.0 and nu[mid] < nu[3]
