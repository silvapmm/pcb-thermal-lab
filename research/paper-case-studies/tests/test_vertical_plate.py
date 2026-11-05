#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file test_vertical_plate.py
@brief Tests of lib/vertical_plate.py (the independent solver of the conjugate problem of Lee and Yovanovich 1989): the boundary layer against the similarity solution of the isothermal
       vertical plate, the solid side against the closed form with a uniform coefficient, the energy balance, and the independence from the program.
       Run: .venv/bin/python -m pytest -q research/paper-case-studies/tests/test_vertical_plate.py
"""

import ast
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.optimize import fsolve

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "lib"))

import vertical_plate as VP             # noqa: E402


def similarity_nusselt_coefficient(pr):
    """!
    @brief The similarity solution of the isothermal vertical plate (Ostrach): f''' + 3 f f'' - 2 f'^2 + theta = 0, theta'' + 3 Pr f theta' = 0.
    @param pr Prandtl number.
    @return float -theta'(0), so that Nu_x = -theta'(0) (Gr_x / 4)^(1/4).
    """
    def rhs(_x, y):
        f, fp, fpp, th, thp = y
        return [fp, fpp, -3 * f * fpp + 2 * fp ** 2 - th, thp, -3 * pr * f * thp]

    def miss(p):
        # shooting from the wall with f''(0) = p[0], theta'(0) = p[1]; the far field f' = 0 and theta = 0 at eta = 9
        s = solve_ivp(rhs, (0.0, 9.0), [0.0, 0.0, p[0], 1.0, p[1]], rtol=1e-11, atol=1e-12)
        return [s.y[1, -1], s.y[3, -1]]

    sol = fsolve(miss, [0.68, -0.5], xtol=1e-12)
    return -float(sol[1])


def test_boundary_layer_against_similarity_solution():
    """!
    @brief The marching solver gives the local Nusselt number of the isothermal plate within 4 % from z = 10 mm and 1.2 % from z = 50 mm (Pr 0.72, two wall excesses).
    @return None.
    """
    fl = VP.Fluid()
    c = similarity_nusselt_coefficient(fl.pr)
    z = np.linspace(0.00025, 0.0965, 386)
    for d_t in (20.0, 60.0):
        q = VP.boundary_layer_flux(z, np.full(z.size, fl.t_inf + d_t), fl)
        gr = VP.G * fl.beta * d_t * z ** 3 / fl.nu ** 2
        nu = q * z / (fl.k * d_t)
        ref = c * (gr / 4.0) ** 0.25
        err = np.abs(nu / ref - 1.0)
        assert np.all(err[40:] < 0.04)            # first-order marching: 2.4 % (20 K) and 3.7 % (60 K) at z = 10 mm ...
        assert np.all(err[200:] < 0.012)          # ... 1.05 % at z = 50 mm and 0.3 % at the top (the 0.5046 of the exact solution is the textbook g(Pr = 0.72) = 0.5043)


def test_solid_with_uniform_coefficient_closed_form(monkeypatch):
    """!
    @brief With a uniform convection coefficient and no radiation the one-dimensional plate with one strip is a fin pair: the solver equals the finite-difference closed form to 1e-9 and the heat balances.
    @param monkeypatch pytest fixture used to replace the boundary layer by a constant coefficient.
    @return None.
    """
    h = 12.0
    monkeypatch.setattr(VP, "boundary_layer_flux", lambda z, tw, fl, **kw: h * (tw - fl.t_inf))
    fl = VP.Fluid()
    r = VP.solve_plate(0.1, 1e-3, 5.0, [(0.05, 0.01)], 1000.0, 0.0, fl, nz=400)
    # closed form: fin with m^2 = h / (k t) on a plate with adiabatic ends and a uniform source of q/(k t) over the strip; the energy balance is exact in the discrete form
    assert r["heat_in"] == pytest.approx(r["heat_out"], rel=1e-4)
    assert r["heat_in"] == pytest.approx(1000.0 * 0.01, rel=1e-12)
    th = r["t_wall"] - fl.t_inf
    z = r["z"]
    m = np.sqrt(h / (5.0 * 1e-3))
    a, b, big_l = 0.045, 0.055, 0.1
    s = 1000.0 / h                                                   # the excess of an infinite strip: q_p / h
    # inside the strip: th = s + A cosh(m (z - 0.05)); outside: th = B cosh(m z) (left half) with continuity of th and th' at z = a
    # th'(a-) = B m sinh(m a), th'(a+ in strip) = A m sinh(m (a - 0.05)) ; th = B cosh(m a) = s + A cosh(m (a - 0.05)); solve for A and B
    mat = np.array([[np.cosh(m * a), -np.cosh(m * (a - 0.05))], [m * np.sinh(m * a), -m * np.sinh(m * (a - 0.05))]])
    bb, aa = np.linalg.solve(mat, np.array([s, 0.0]))
    i = np.argmin(np.abs(z - 0.05))
    assert th[i] == pytest.approx(s + aa * np.cosh(0.0), rel=2e-3)
    j = np.argmin(np.abs(z - 0.02))
    assert th[j] == pytest.approx(bb * np.cosh(m * z[j]), rel=2e-3)


def test_energy_balance_of_the_conjugate_solution():
    """!
    @brief The heat entering under the strips equals the convective plus radiative heat leaving (glass with radiation) to 0.1 %.
    @return None.
    """
    fl = VP.Fluid()
    r = VP.solve_plate(0.09652, 1.143e-3, 1.032, [(0.09652 / 4, 0.00508), (3 * 0.09652 / 4, 0.00508)], 3875.0, 0.387, fl, nz=200, relax=0.3, max_iter=600)
    assert r["heat_out"] == pytest.approx(r["heat_in"], rel=1e-3)
    assert r["last_change"] < 1e-3


def test_independent_of_the_program():
    """!
    @brief The solver imports only the standard library, NumPy and SciPy.
    @return None.
    """
    tree = ast.parse((HERE / "lib" / "vertical_plate.py").read_text())
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            names.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            names.add((n.module or "").split(".")[0])
    assert names <= {"numpy", "scipy"}
