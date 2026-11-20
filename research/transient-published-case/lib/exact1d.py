#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file exact1d.py
@brief Independent exact solutions (imports nothing from the program) of the transient benchmark cases of the study: the bar with a sinusoidal end temperature (the case of the
       published benchmark T3), the semi-infinite solid with a flux step, and the uniformly heated square plate with held edges.
@details Eigenfunction expansions with the time integral done in closed form, so the only error is the truncation of the series (checked by doubling the number of terms);
         plus an own 1D linear finite-element run of the bar (`fe1d_bar`) that reproduces the mesh results other programs publish for the same case.
"""
import numpy as np
from scipy.special import erfc  # noqa: F401  (kept for readers extending the file)


def bar_sinusoidal_end(x, t, length=0.1, k=35.0, rho=7200.0, cp=440.5, amp=100.0, period_half=40.0, n_terms=4000):
    """!
    @brief Temperature of a bar that starts at 0, with u(0, t) = 0 and u(L, t) = amp sin(pi t / period_half).
    @details Write u = (x/L) g(t) + v with g the end temperature; v has zero ends and obeys v_t = a v_xx - (x/L) g'(t), v(x, 0) = 0. Projected on sin(n pi x / L) the mode
             amplitude b_n obeys b_n' + mu_n b_n = -c_n g'(t), c_n = 2 (-1)^(n+1) / (n pi), mu_n = a (n pi / L)^2, and with g' = amp w cos(w s) the convolution is closed:
             b_n = -c_n amp w (mu cos(w t) + w sin(w t) - mu exp(-mu t)) / (mu^2 + w^2).
    @param x Position in m (scalar).
    @param t Time in s (scalar).
    @param length Bar length in m.
    @param k Conductivity in W/mK.
    @param rho Density in kg/m3.
    @param cp Specific heat in J/kgK.
    @param amp Amplitude of the end temperature in K.
    @param period_half The pi t / period_half argument: the end follows amp sin(pi t / period_half), s.
    @param n_terms Number of series terms.
    @return float Temperature in K above the initial value.
    """
    a = k / (rho * cp)
    w = np.pi / period_half
    n = np.arange(1, n_terms + 1)
    mu = a * (n * np.pi / length) ** 2
    c = 2.0 * (-1.0) ** (n + 1) / (n * np.pi)
    b = -c * amp * w * (mu * np.cos(w * t) + w * np.sin(w * t) - mu * np.exp(-mu * t)) / (mu ** 2 + w ** 2)
    return float((x / length) * amp * np.sin(w * t) + np.sum(b * np.sin(n * np.pi * x / length)))


def bar_sinusoidal_end_lines(n, length=0.1, k=35.0, rho=7200.0, cp=440.5, x_probe=0.08, t_end=32.0):
    """!
    @brief A second, numerical route to the T3 value that shares nothing with the series: the method of lines (second-order central differences on n intervals, the held
           ends exact) integrated in time by an implicit Runge-Kutta method (Radau IIA) to a tolerance of 1e-11, so the only error is the space error, of order (L/n)^2.
    @details Two values at n and 2n give the Richardson limit (4 T(2n) - T(n)) / 3, an estimate of the exact value independent of the eigenfunction expansion.
    @param n Intervals along the bar (count; x_probe must be a node: n a multiple of 5 for 0.08 m).
    @param length Bar length in m.
    @param k Conductivity in W/mK.
    @param rho Density in kg/m3.
    @param cp Specific heat in J/kgK.
    @param x_probe Read-out position in m.
    @param t_end Final time in s.
    @return float Temperature at x_probe and t_end in degC.
    """
    import scipy.sparse as sp
    from scipy.integrate import solve_ivp
    a = k / (rho * cp)
    dx = length / n
    m = n - 1
    lap = sp.diags([np.ones(m - 1), -2.0 * np.ones(m), np.ones(m - 1)], [-1, 0, 1]) * (a / dx ** 2)

    def rhs(t, u):
        r = lap @ u
        r[-1] += a * 100.0 * np.sin(np.pi * t / 40.0) / dx ** 2      # the held end at x = L enters the last interior row
        return r

    sol = solve_ivp(rhs, (0.0, t_end), np.zeros(m), method="Radau", jac=lap.tocsc(), rtol=1e-11, atol=1e-11, t_eval=[t_end])
    u = np.concatenate([[0.0], sol.y[:, -1], [100.0 * np.sin(np.pi * t_end / 40.0)]])
    return float(np.interp(x_probe, np.linspace(0.0, length, n + 1), u))


def fe1d_bar(n, steps, theta=1.0, lumped=False, length=0.1, k=35.0, rho_c=7200.0 * 440.5, x_probe=0.08, t_end=32.0):
    """!
    @brief An own 1D linear finite-element run of the T3 bar (two-node elements, held ends imposed exactly, theta method with equal steps), to reproduce the MESH results
           that other programs publish for the same case (the Abaqus DC1D2 rows with a lumped capacity and the MOOSE EDGE2 rows with a consistent one, both 1 s implicit-Euler
           steps per their input files).
    @param n Elements along the bar (count).
    @param steps Equal time steps over t_end (count).
    @param theta 1.0 implicit Euler, 0.5 Crank-Nicolson.
    @param lumped True for the row-sum (lumped) capacity matrix, False for the consistent one.
    @param length Bar length in m.
    @param k Conductivity in W/mK.
    @param rho_c Volumetric heat capacity in J/m3K.
    @param x_probe Read-out position in m (linear interpolation between nodes).
    @param t_end Final time in s.
    @return float Temperature at x_probe and t_end in degC.
    """
    h = length / n
    kk = np.zeros((n + 1, n + 1))
    mm = np.zeros((n + 1, n + 1))
    me = rho_c * h * (np.diag([0.5, 0.5]) if lumped else np.array([[1.0 / 3.0, 1.0 / 6.0], [1.0 / 6.0, 1.0 / 3.0]]))
    for e in range(n):
        idx = np.ix_([e, e + 1], [e, e + 1])
        kk[idx] += k / h * np.array([[1.0, -1.0], [-1.0, 1.0]])
        mm[idx] += me
    dt = t_end / steps
    temp = np.zeros(n + 1)
    for s in range(steps):
        a = mm / dt + theta * kk
        b = (mm / dt - (1.0 - theta) * kk) @ temp
        # held ends: row replaced by the identity (an exact Dirichlet condition, as in the input decks)
        a[0, :], a[0, 0], b[0] = 0.0, 1.0, 0.0
        a[-1, :], a[-1, -1], b[-1] = 0.0, 1.0, 100.0 * np.sin(np.pi * (s + 1) * dt / 40.0)
        temp = np.linalg.solve(a, b)
    return float(np.interp(x_probe, np.linspace(0.0, length, n + 1), temp))


def semi_infinite_flux_step(t, q, k, rho_c):
    """!
    @brief Surface temperature rise of a semi-infinite solid with a constant surface flux switched on at t = 0: 2 q sqrt(alpha t / pi) / k
           (Lienhard, A Heat Transfer Textbook 6.00, eqn (5.56), printed p. 229).
    @param t Time in s.
    @param q Flux in W/m2.
    @param k Conductivity in W/mK.
    @param rho_c Volumetric heat capacity in J/m3K.
    @return float Rise in K.
    """
    alpha = k / rho_c
    return 2.0 * q / k * np.sqrt(alpha * t / np.pi)


def square_plate_uniform_heating(x, y, t, side, k, rho_c, qvol, n_max=401):
    """!
    @brief Temperature rise of a square plate (side `side`, edges held at 0) with a uniform volumetric source switched on at t = 0 and insulated faces.
    @details u = sum over odd m, n of 16 / (m n pi^2) (qvol / rho_c) (1 - exp(-mu t)) / mu sin(m pi x / s) sin(n pi y / s), mu = alpha pi^2 (m^2 + n^2) / s^2.
    @param x Position in m (array or scalar).
    @param y Position in m (array or scalar, broadcast with x).
    @param t Time in s.
    @param side Side in m.
    @param k Conductivity in W/mK.
    @param rho_c Volumetric heat capacity in J/m3K.
    @param qvol Source in W/m3.
    @param n_max Largest odd index.
    @return numpy.ndarray Rise in K with the shape of broadcast(x, y).
    """
    alpha = k / rho_c
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    out = np.zeros(np.broadcast(x, y).shape)
    odd = np.arange(1, n_max + 1, 2)
    for m in odd:
        sx = np.sin(m * np.pi * x / side)
        for n in odd:
            mu = alpha * np.pi ** 2 * (m * m + n * n) / side ** 2
            out = out + 16.0 / (m * n * np.pi ** 2) * (qvol / rho_c) * (1.0 - np.exp(-mu * t)) / mu * sx * np.sin(n * np.pi * y / side)
    return out


def robin_roots(side, k, h, n_roots=60):
    """!
    @brief Positive roots beta of beta tan(beta side / 2) = h / k (the even modes cos(beta (x - side/2)) of a slab with the film h on both faces).
    @param side Slab thickness in m.
    @param k Conductivity in W/mK.
    @param h Film coefficient in W/m2K.
    @param n_roots Number of roots.
    @return numpy.ndarray Roots in 1/m.
    """
    from scipy.optimize import brentq
    roots = []
    for i in range(n_roots):
        lo = (2 * i * np.pi + 1e-9) / side
        hi = ((2 * i + 1) * np.pi - 1e-9) / side                       # tan runs from 0 to +inf on (2 i pi, (2 i + 1) pi) / side
        f = lambda b: b * np.tan(b * side / 2.0) - h / k              # noqa: E731
        roots.append(brentq(f, lo, hi, xtol=1e-14))
    return np.array(roots)


def square_plate_robin_heating(x, y, t, side, k, rho_c, qvol, h, n_roots=60):
    """!
    @brief Temperature rise of a square plate with a film h on the four edges (ambient 0), uniform source from t = 0, insulated faces: the Robin version of the Dirichlet series.
    @details Product of the 1D modes cos(beta (x - s/2)); the projection of 1 on a mode is (2 sin(beta s / 2) / beta) / (s/2 + sin(beta s) / (2 beta)).
    @param x Position in m (array).
    @param y Position in m (array, broadcast with x).
    @param t Time in s.
    @param side Side in m.
    @param k Conductivity in W/mK.
    @param rho_c Volumetric heat capacity in J/m3K.
    @param qvol Source in W/m3.
    @param h Edge film in W/m2K.
    @param n_roots Modes per direction.
    @return numpy.ndarray Rise in K.
    """
    alpha = k / rho_c
    b = robin_roots(side, k, h, n_roots)
    c = (2.0 * np.sin(b * side / 2.0) / b) / (side / 2.0 + np.sin(b * side) / (2.0 * b))
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    out = np.zeros(np.broadcast(x, y).shape)
    for i in range(b.size):
        fx = np.cos(b[i] * (x - side / 2.0))
        for j in range(b.size):
            mu = alpha * (b[i] ** 2 + b[j] ** 2)
            out = out + c[i] * c[j] * (qvol / rho_c) * (1.0 - np.exp(-mu * t)) / mu * fx * np.cos(b[j] * (y - side / 2.0))
    return out
