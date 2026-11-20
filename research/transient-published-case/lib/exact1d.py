#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file exact1d.py
@brief Independent exact solutions (imports nothing from the program) of the transient benchmark cases of the study: the bar with a sinusoidal end temperature (the case of the
       published benchmark T3), the semi-infinite solid with a flux step, and the uniformly heated square plate with held edges.
@details Eigenfunction expansions with the time integral done in closed form, so the only error is the truncation of the series (checked by doubling the number of terms).
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
