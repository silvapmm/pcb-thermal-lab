#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review_checks.py
@brief The independent checks of the review (README section 11): do the reproductions of this folder hold with code and data that do not share the study's assumptions?

@details Questions answered (the numbers printed here are the ones of README section 11):
         R1. Ostrach (1953) Table I: a third solution of the similarity equations, written for the review with nonlinear finite differences on a stretched grid
             (Newton, sparse direct solve, continuation in Pr), shares no code with `lib/sources.py` (collocation and shooting).
         R2. The array of Bar-Cohen, Iyengar and Kraus (2003): the same equations with the air properties interpolated from a printed table (Incropera and DeWitt,
             Table A.4, values from memory, marked M) instead of the Sutherland fits of `channel.air`, and with beta at the film or at the ambient temperature, to see how
             much of the 0.2 and 1.0 % agreement depends on the property fits.
         R3. The constants of the correlations by plain algebra: 24^2, 0.59^-2, the Elenbaas boundary-layer limit 35^(3/4)/24, the optimum of Nu_b/b^2 of equations 8 and 21.
Usage: .venv/bin/python research/fin-channel-sources/scripts/study_review_checks.py   (about 30 seconds)
"""

import math

import numpy as np
from scipy.optimize import brentq, minimize_scalar
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

G = 9.81

# Air at 1 atm, Incropera and DeWitt Table A.4 (T in K; nu in m2/s, k in W/mK, Pr): values from memory (M), used only as a second property source
TABLE_T = [250.0, 300.0, 350.0, 400.0]
TABLE_NU = [11.44e-6, 15.89e-6, 20.92e-6, 26.41e-6]
TABLE_K = [22.3e-3, 26.3e-3, 30.0e-3, 33.8e-3]
TABLE_PR = [0.720, 0.707, 0.700, 0.690]


def similarity_fd(pr, eta_max=20.0, n=1500, init=None):
    """!
    @brief Solve F''' + 3 F F'' - 2 F'^2 + H = 0, H'' + 3 Pr F H' = 0 (Ostrach's form) by finite differences on a stretched grid and Newton iterations.
    @details Unknowns F, G = F', H at every node; F' = G by the trapezoid rule, the two second-order equations by three-point differences on the non-uniform grid;
             F(0) = G(0) = 0, H(0) = 1, G(eta_max) = H(eta_max) = 0. The wall derivatives are one-sided and second order.
    @param pr Prandtl number.
    @param eta_max Truncation of the semi-infinite interval.
    @param n Number of nodes.
    @param init Previous solution (x, F, G, H) for a continuation in Pr, or None for a decaying start.
    @return Tuple (F''(0), -H'(0), solution tuple for the next continuation step).
    @throws RuntimeError If Newton does not converge.
    """
    s = np.linspace(0.0, 1.0, n)
    x = eta_max * (np.exp(3.0 * s) - 1.0) / (np.exp(3.0) - 1.0)        # nodes crowded at the wall, where the thermal layer is thin for large Pr
    if init is None:
        f, g, h = np.zeros(n), 0.5 * x * np.exp(-x), np.exp(-x)
    else:
        f, g, h = (np.interp(x, init[0], v) for v in init[1:])
    i_f, i_g, i_h = 0, n, 2 * n
    hm, hp = x[1:-1] - x[:-2], x[2:] - x[1:-1]
    a2, c2 = 2.0 / (hm * (hm + hp)), 2.0 / (hp * (hm + hp))           # second derivative weights
    b2 = -a2 - c2
    d_m, d_p = -hp / (hm * (hm + hp)), hm / (hp * (hm + hp))           # first derivative weights
    d_0 = -d_m - d_p
    k = np.arange(1, n - 1)
    for _ in range(300):
        rows, cols, vals, res = [], [], [], np.zeros(3 * n)

        def put(r, c, v):
            """!
            @brief Add entries to the Jacobian lists.
            @param r Row indices.
            @param c Column indices.
            @param v Values.
            @return None.
            """
            rows.append(np.atleast_1d(r))
            cols.append(np.atleast_1d(c))
            vals.append(np.broadcast_to(np.atleast_1d(v), np.atleast_1d(r).shape).astype(float))

        # Boundary conditions
        res[i_f] = f[0]
        put(i_f, i_f, 1.0)
        res[i_g] = g[0]
        put(i_g, i_g, 1.0)
        res[i_h] = h[0] - 1.0
        put(i_h, i_h, 1.0)
        res[i_g + n - 1] = g[-1]
        put(i_g + n - 1, i_g + n - 1, 1.0)
        res[i_h + n - 1] = h[-1]
        put(i_h + n - 1, i_h + n - 1, 1.0)
        # F' = G (trapezoid) on rows 1..n-1 of the F block
        j = np.arange(1, n)
        dx = x[1:] - x[:-1]
        res[i_f + j] = f[j] - f[j - 1] - 0.5 * dx * (g[j] + g[j - 1])
        put(i_f + j, i_f + j, 1.0)
        put(i_f + j, i_f + j - 1, -1.0)
        put(i_f + j, i_g + j, -0.5 * dx)
        put(i_f + j, i_g + j - 1, -0.5 * dx)
        # Momentum and energy on the interior nodes
        gpp = a2 * g[k - 1] + b2 * g[k] + c2 * g[k + 1]
        gp = d_m * g[k - 1] + d_0 * g[k] + d_p * g[k + 1]
        hpp = a2 * h[k - 1] + b2 * h[k] + c2 * h[k + 1]
        hpr = d_m * h[k - 1] + d_0 * h[k] + d_p * h[k + 1]
        r = i_g + k
        res[r] = gpp + 3.0 * f[k] * gp - 2.0 * g[k] ** 2 + h[k]
        put(r, i_g + k - 1, a2 + 3.0 * f[k] * d_m)
        put(r, i_g + k, b2 + 3.0 * f[k] * d_0 - 4.0 * g[k])
        put(r, i_g + k + 1, c2 + 3.0 * f[k] * d_p)
        put(r, i_f + k, 3.0 * gp)
        put(r, i_h + k, 1.0)
        r = i_h + k
        res[r] = hpp + 3.0 * pr * f[k] * hpr
        put(r, i_h + k - 1, a2 + 3.0 * pr * f[k] * d_m)
        put(r, i_h + k, b2 + 3.0 * pr * f[k] * d_0)
        put(r, i_h + k + 1, c2 + 3.0 * pr * f[k] * d_p)
        put(r, i_f + k, 3.0 * pr * hpr)
        jac = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(3 * n, 3 * n)).tocsc()
        d = spsolve(jac, -res)
        f, g, h = f + d[:n], g + d[n:2 * n], h + d[2 * n:]
        if np.max(np.abs(d)) < 1e-11:
            break
    else:
        raise RuntimeError("finite-difference similarity solution did not converge for Pr = %g" % pr)
    h1, h2 = x[1] - x[0], x[2] - x[1]

    def wall_derivative(y):
        """!
        @brief One-sided second-order derivative at the wall on the non-uniform grid.
        @param y Nodal values.
        @return dy/deta at eta = 0.
        """
        return -(2 * h1 + h2) / (h1 * (h1 + h2)) * y[0] + (h1 + h2) / (h1 * h2) * y[1] - h1 / (h2 * (h1 + h2)) * y[2]

    return wall_derivative(g), -wall_derivative(h), (x, f, g, h)


def air_table(t_c):
    """!
    @brief Air properties interpolated linearly in the printed table (second property source of R2).
    @param t_c Temperature in degC.
    @return Tuple (nu in m2/s, k in W/mK, Pr, T in K).
    """
    t = t_c + 273.15
    return float(np.interp(t, TABLE_T, TABLE_NU)), float(np.interp(t, TABLE_T, TABLE_K)), float(np.interp(t, TABLE_T, TABLE_PR)), t


def bik_ha(s, t=1e-3, height=45e-3, length=0.1, width=0.1, theta=25.0, k_fin=200.0, t_amb=25.0, beta_at="film"):
    """!
    @brief Array coefficient of Bar-Cohen, Iyengar and Kraus (2003), equations 1 to 16, written again for the review with the table properties.
    @param s Gap in m.
    @param t Fin thickness in m.
    @param height Fin height in m.
    @param length Length in the flow direction in m.
    @param width Base width in m.
    @param theta Base excess in K.
    @param k_fin Fin conductivity in W/mK.
    @param t_amb Ambient in degC.
    @param beta_at "film" (beta = 1/T_film) or "ambient" (beta = 1/T_amb).
    @return Tuple (h_a in W/m2K, h_fin in W/m2K).
    """
    nu, k, pr, t_film = air_table(t_amb + 0.5 * theta)
    beta = 1.0 / t_film if beta_at == "film" else 1.0 / (t_amb + 273.15)
    el = G * beta * theta * pr * s ** 4 / (length * nu ** 2)

    def residual(h):
        """!
        @brief Fixed point of the fin coefficient with the efficiency inside the Elenbaas number.
        @param h Trial coefficient in W/m2K.
        @return Residual in W/m2K.
        """
        m = math.sqrt(2.0 * h / (k_fin * t))
        eta = math.tanh(m * height) / (m * height)
        return (576.0 / (eta * el) ** 2 + 2.873 / (eta * el) ** 0.5) ** -0.5 * k / s - h

    h_fin = brentq(residual, 1e-6, 1e4)
    m = math.sqrt(2.0 * h_fin / (k_fin * t))
    q_fin = length * k_fin * t * theta * m * math.tanh(m * height)
    h_base = 0.59 * (G * beta * theta * pr * length ** 3 / nu ** 2) ** 0.25 * k / length
    q = width / (s + t) * (q_fin + h_base * length * s * theta)
    return q / (length * width * theta), h_fin


def bik_least_material(t_amb, beta_at):
    """!
    @brief Least-material array (s = t = 9 mm, height from equation 20, t = 0.993 h_fin H^2 / k) with the table properties.
    @param t_amb Ambient in degC.
    @param beta_at "film" or "ambient".
    @return Tuple (height in m, h_a in W/m2K).
    """
    height = 0.6
    for _ in range(400):
        _, h = bik_ha(9e-3, t=9e-3, height=height, t_amb=t_amb, beta_at=beta_at)
        new = math.sqrt(9e-3 * 200.0 / (0.993 * h))
        if abs(new - height) < 1e-10:
            break
        height = new
    return height, bik_ha(9e-3, t=9e-3, height=height, t_amb=t_amb, beta_at=beta_at)[0]


def main():
    """!
    @brief Print R1 to R3.
    @return None.
    """
    print("R1. Ostrach Table I, -H'(0) and F''(0) by finite differences (review's own solver)")
    table = {0.01: 0.0812, 0.72: 0.5046, 0.733: 0.5080, 1.0: 0.5671, 2.0: 0.7165, 10.0: 1.1694, 100.0: 2.191}
    fpp, h0, _ = similarity_fd(0.01, eta_max=200.0)
    print("   Pr %7.3f  table %.4f  finite differences %.4f (%+.2f %%)  F''(0) %.4f" % (0.01, table[0.01], h0, 100 * (h0 / table[0.01] - 1), fpp))
    _, _, sol = similarity_fd(0.72)
    for pr in (0.72, 0.733, 0.85, 1.0, 1.4, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 25.0, 40.0, 60.0, 100.0):
        fpp, h0, sol = similarity_fd(pr, init=sol)          # continuation: a cold start converges to a spurious root at Pr 1 and 2
        if pr in table:
            print("   Pr %7.3f  table %.4f  finite differences %.4f (%+.2f %%)  F''(0) %.4f" % (pr, table[pr], h0, 100 * (h0 / table[pr] - 1), fpp))
    print("R2. Bar-Cohen, Iyengar and Kraus array with tabulated air (paper: about 8 mm, 52.4 W/m2K; least material 198 W/m2K)")
    for t_amb in (20.0, 25.0, 45.0):
        for beta_at in ("film", "ambient"):
            r = minimize_scalar(lambda s: -bik_ha(s, t_amb=t_amb, beta_at=beta_at)[0], bounds=(2e-3, 2e-2), method="bounded", options={"xatol": 1e-7})
            height, ha_lm = bik_least_material(t_amb, beta_at)
            print("   ambient %4.1f degC, beta at %-7s: optimum %.2f mm, h_a %.2f (%+.1f %%); h_a(8 mm) %.2f; least material H %.0f mm, h_a %.1f (%+.1f %%)" % (
                t_amb, beta_at, r.x * 1e3, -r.fun, 100 * (-r.fun / 52.4 - 1), bik_ha(8e-3, t_amb=t_amb, beta_at=beta_at)[0], height * 1e3, ha_lm, 100 * (ha_lm / 198 - 1)))
    print("R3. Constants by algebra")
    print("   24^2 = %d; 0.59^-2 = %.4f; Elenbaas limit 35^(3/4)/24 = %.4f" % (24 ** 2, 0.59 ** -2, 35 ** 0.75 / 24))
    for name, fun in (("equation 21", lambda r: ((24.0 / r) ** 2 + (0.59 * r ** 0.25) ** -2) ** -0.5),
                      ("equation 8", lambda r: (r / 24.0) * (1.0 - math.exp(-35.0 / r)) ** 0.75)):
        res = minimize_scalar(lambda lr: -fun(math.exp(lr)) / math.exp(lr) ** 0.5, bounds=(0.0, 8.0), method="bounded", options={"xatol": 1e-10})
        ra = math.exp(res.x)
        print("   optimum of Nu_b / b^2, %s: Ra_b %.2f, K = Ra_b^(1/4) %.4f, Nu_b %.4f" % (name, ra, ra ** 0.25, fun(ra)))


if __name__ == "__main__":
    main()
