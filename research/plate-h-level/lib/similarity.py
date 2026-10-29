#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file similarity.py
@brief Independent solution of the laminar free-convection boundary layer on an isothermal vertical plate (Ostrach / Sparrow and Gregg / LeFevre similarity equations).
@details Imports nothing from pcbthermal. The similarity equations (Boussinesq fluid, constant properties, wall at constant temperature) are

             f''' + 3 f f'' - 2 f'^2 + theta = 0,    theta'' + 3 Pr f theta' = 0,
             f(0) = f'(0) = 0, theta(0) = 1, f'(inf) = theta(inf) = 0,

         with eta = (y/x) (Gr_x/4)^(1/4). The local Nusselt number is Nu_x = -theta'(0) (Gr_x/4)^(1/4) and the plate-average one
         Nu_L = (4/3) Nu_x(L) = C(Pr) Ra_L^(1/4), see `coefficient`.
         The boundary value problem is solved by a shooting method with a fixed-step RK4 written here (no SciPy ODE code) and,
         as a second route, by scipy.integrate.solve_bvp; the two must agree.
"""

import numpy as np
from scipy.integrate import solve_bvp
from scipy.optimize import fsolve


def _rhs(y, pr):
    """!
    @brief Right-hand side of the first-order system y = (f, f', f'', theta, theta').
    @param y State vector of 5 numbers.
    @param pr Prandtl number.
    @return numpy.ndarray derivative.
    """
    f, fp, fpp, th, thp = y
    return np.array([fp, fpp, -3.0 * f * fpp + 2.0 * fp * fp - th, thp, -3.0 * pr * f * thp])


def _rk4(y0, pr, eta_max, n):
    """!
    @brief Fixed-step fourth-order Runge-Kutta integration of the system.
    @param y0 Initial state.
    @param pr Prandtl number.
    @param eta_max End of the interval.
    @param n Number of steps.
    @return numpy.ndarray final state.
    """
    h = eta_max / n
    y = np.array(y0, float)
    for _ in range(n):
        k1 = _rhs(y, pr)
        k2 = _rhs(y + 0.5 * h * k1, pr)
        k3 = _rhs(y + 0.5 * h * k2, pr)
        k4 = _rhs(y + h * k3, pr)
        y = y + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
    return y


def profile(pr, eta_max=10.0, n=2000):
    """!
    @brief The similarity profiles f', theta against eta (for the drawing of the boundary layer).
    @param pr Prandtl number.
    @param eta_max End of the interval.
    @param n Number of RK4 steps (the profile is stored at every step).
    @return tuple (eta, f', theta) arrays.
    """
    fpp0, thp0 = shoot(pr)
    h = eta_max / n
    y = np.array([0.0, 0.0, fpp0, 1.0, thp0])
    out = [y.copy()]
    for _ in range(n):
        k1 = _rhs(y, pr)
        k2 = _rhs(y + 0.5 * h * k1, pr)
        k3 = _rhs(y + 0.5 * h * k2, pr)
        k4 = _rhs(y + h * k3, pr)
        y = y + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
        out.append(y.copy())
    out = np.array(out)
    return np.linspace(0, eta_max, n + 1), out[:, 1], out[:, 3]


def shoot(pr, eta_max=None, n=5500, guess=None):
    """!
    @brief Shooting solution: find f''(0) and theta'(0) so that f' and theta vanish at eta_max.
    @param pr Prandtl number.
    @param eta_max Far-field position in similarity units (default 5.5: the layer of air is about 4 units thick and a longer interval makes the shooting unstable, so this
                   route is only a check for 0.5 <= Pr <= 2; `bvp` is the route for other Prandtl numbers).
    @param n RK4 steps.
    @param guess Starting values (f''(0), theta'(0)); default scaled with Pr.
    @return tuple (f''(0), theta'(0)).
    """
    if eta_max is None:
        eta_max = 5.5
    if guess is None:
        guess = (0.68, -0.5)

    def miss(p):
        y = _rk4([0.0, 0.0, p[0], 1.0, p[1]], pr, eta_max, n)
        return [y[1], y[3]]
    sol = fsolve(miss, guess, xtol=1e-13)
    return float(sol[0]), float(sol[1])


def bvp(pr, eta_max=50.0):
    """!
    @brief Second route, scipy's collocation solver for the same boundary value problem.
    @param pr Prandtl number.
    @param eta_max Far-field position (50 is converged to 1e-5 for 0.1 <= Pr <= 100; Pr = 0.01 needs 100).
    @return tuple (f''(0), theta'(0)).
    @throws RuntimeError If the collocation did not converge.
    """
    eta = np.linspace(0, eta_max, 400)
    y0 = np.zeros((5, eta.size))
    y0[0] = 0.5 * (1 - np.exp(-eta)) ** 2
    y0[1] = eta * np.exp(-eta)
    y0[3] = np.exp(-eta)
    y0[4] = -np.exp(-eta)
    sol = solve_bvp(lambda e, y: np.array([_rhs(y[:, i], pr) for i in range(y.shape[1])]).T,
                    lambda a, b: np.array([a[0], a[1], a[3] - 1.0, b[1], b[3]]), eta, y0, tol=1e-9, max_nodes=200000)
    if not sol.success:
        raise RuntimeError("solve_bvp did not converge")
    return float(sol.y[2, 0]), float(sol.y[4, 0])


def coefficient(pr, method="shoot"):
    """!
    @brief The exact coefficient C(Pr) of the plate-average Nusselt number Nu_L = C Ra_L^(1/4) of the laminar boundary layer.
    @details Nu_x = -theta'(0) (Gr_x/4)^(1/4); h_x ~ x^(-1/4) so the average over L is (4/3) h_L; Gr = Ra/Pr, hence
             Nu_L = (4/3) (-theta'(0)) / (4 Pr)^(1/4) * Ra_L^(1/4).
    @param pr Prandtl number.
    @param method "shoot" (own RK4) or "bvp" (scipy collocation).
    @return float C.
    """
    thp = shoot(pr)[1] if method == "shoot" else bvp(pr)[1]
    return (4.0 / 3.0) * (-thp) / (4.0 * pr) ** 0.25


def local_coefficient(pr):
    """!
    @brief The local coefficient Nu_x = c_x Ra_x^(1/4), c_x = -theta'(0) / (4 Pr)^(1/4).
    @param pr Prandtl number.
    @return float c_x.
    """
    return -shoot(pr)[1] / (4.0 * pr) ** 0.25


def churchill_usagi(pr):
    """!
    @brief The Prandtl-number fit 0.670 / [1 + (0.492/Pr)^(9/16)]^(4/9) of the average coefficient (Churchill and Chu's laminar term).
    @param pr Prandtl number.
    @return float.
    """
    return 0.670 / (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (4.0 / 9.0)


def lefevre_local(pr):
    """!
    @brief LeFevre's Prandtl fit of the local coefficient, 0.503 / [1 + (0.492/Pr)^(9/16)]^(4/9) (coefficient of Ra_x^(1/4)).
    @param pr Prandtl number.
    @return float coefficient.
    """
    return 0.503 / (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (4.0 / 9.0)
