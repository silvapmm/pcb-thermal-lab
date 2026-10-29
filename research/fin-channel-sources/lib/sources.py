#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file sources.py
@brief The formulas and the plot-read numbers of the sources that `research/fin-channel-sources/` opened, with the independent solvers used to reproduce them.

@details Nothing of a third party is stored here except formulas (with their equation numbers) and numbers read from plots (marked "plot"). Sources:
         * Yovanovich, Teertstra and Muzychka, J. Thermophys. Heat Transfer 16 (1) (2002) 116-121: equations 28 and 29 for the duct, the parallel-plate numbers of
           Table 3 and the 100:1 rectangle of equation 32; the Elenbaas (1942) data of its Figure 11 (plot values).
         * Bar-Cohen, Iyengar and Kraus, J. Electronic Packaging 125 (2003) 208-216: equations 1 to 21 (plate-fin array with the composite Nusselt number).
         * Ostrach, NACA Report 1111 (1953): Table I, the similarity solution of the vertical plate (values of -H'(0)).
         * Da Silva and others, ENCIT 2012, paper 324: six measured short fin arrays on a horizontal base (values read from the plots of its Figures 4 to 7).
         * Tari and Mehrtash, Applied Thermal Engineering 61 (2013) 728-736: equations 4, 5 and 10 (horizontal plate-fin heat sinks, from CFD).
         The independent channel solver of the merged folder (`research/fin-channel/lib/channel_bl.py`) and its correlations (`channel.py`) are imported, never edited.
"""

import math
import os
import sys
import types

import numpy as np
from scipy.integrate import solve_bvp
from scipy.optimize import brentq, minimize_scalar

HERE = os.path.dirname(os.path.abspath(__file__))
FIN_CHANNEL_LIB = os.path.join(os.path.dirname(os.path.dirname(HERE)), "fin-channel", "lib")
if FIN_CHANNEL_LIB not in sys.path:
    sys.path.insert(0, FIN_CHANNEL_LIB)

import channel as ch                                         # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from pcbthermal import blocks                                # noqa: E402  (imported, never edited: the fin ratio of the program's block)

G = ch.G


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------
# Yovanovich, Teertstra and Muzychka (2002)
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------

def ytm_parallel_plates_nu(ra_b, n=None, eps=0.01):
    """!
    @brief The composite model of Yovanovich, Teertstra and Muzychka (2002), equation 29, for the parallel-plate channel treated as a rectangular duct of aspect ratio eps.
    @details Equation 29: Nu_sqrtA = { [2 Ra_sA (sqrtA/L) fReA^-1 (sqrtA/P)^2]^-n + [0.6 (Ra_sA sqrtA/L)^(1/4)]^-n }^(-1/n), with sqrtA the square root of the cross-section
             (a rectangle b x (b/eps): sqrtA = b / sqrt(eps), P = 2 b (1 + 1/eps)), fRe_sqrtA = 119.56 for eps = 0.01 (Table 2; other values are not used here), and the
             combination parameter n = 1.2 / eps^(1/9) (equation 32, 2.00 for eps = 0.01). The conversions of equations 30 and 31 take Ra_b (the Elenbaas number of
             the channel width b) to Ra_sA sqrtA/L = Ra_b (sqrtA/b)^4 and Nu_sA = Nu_b sqrtA / b, with sqrtA / b = 1/sqrt(eps) (10 for eps = 0.01).
    @param ra_b Elenbaas number of the channel width, Ra_b = g beta dT b^4 Pr / (nu^2 L).
    @param n Combination parameter; None takes equation 32.
    @param eps Aspect ratio b/a of the duct (0.01 for the parallel-plate channel of the paper, a 100:1 rectangle).
    @return Nu_b = h b / k.
    """
    if n is None:
        n = 1.2 / eps ** (1.0 / 9.0)
    fre = 119.56                                          # f Re_sqrtA of the 100:1 rectangle, Table 2 (only valid for eps = 0.01)
    root_a_over_b = 1.0 / math.sqrt(eps)
    p_over_b = 2.0 * (1.0 + 1.0 / eps)
    ra_a_l = ra_b * root_a_over_b ** 4                    # Ra_sqrtA sqrtA / L = Ra_b (sqrtA/b)^4
    root_a_over_p = root_a_over_b / p_over_b
    nu_fd = 2.0 * ra_a_l / fre * root_a_over_p ** 2
    nu_bl = 0.6 * ra_a_l ** 0.25
    nu_sa = (nu_fd ** (-n) + nu_bl ** (-n)) ** (-1.0 / n)
    return nu_sa / root_a_over_b


# Elenbaas (1942) parallel-plate data as drawn in Figure 11 of Yovanovich, Teertstra and Muzychka (2002): pixel centres of the open squares in a 400 dpi render, with the
# axis calibration read from the same render (1e3 at x = 141 px, 153.3 px per decade; Nu 1e2 at y = 90 px, 220.3 px per decade). PLOT VALUES, about +-5 px (0.03 decade).
FIG11_PIXELS = [(237, 683), (262, 663), (286, 642), (303, 604), (325, 571), (359, 526), (380, 507), (387, 485), (421, 446), (444, 410), (471, 381), (488, 348), (517, 321),
                (549, 297), (571, 274), (610, 252), (642, 238), (665, 233), (723, 194), (751, 187), (778, 182), (822, 160), (857, 158), (889, 142), (931, 127), (976, 116)]
FIG11_CAL = {"x0": 141.0, "dx": 153.3, "y0": 90.0, "dy": 220.3}


def elenbaas_data_from_fig11():
    """!
    @brief Convert the pixel centres of Figure 11 to (Ra_b, Nu_b) of the channel width b (plot values).
    @details Ra_sqrtA sqrtA/L = 1e4 Ra_b and Nu_sqrtA = 10 Nu_b for the 100:1 rectangle (sqrtA = 10 b), from the conversions printed with Table 3 of the paper
             (10 for sqrtA/W, equations 30 and 31).
    @return Tuple of numpy arrays (ra_b, nu_b).
    """
    c = FIG11_CAL
    ra, nu = [], []
    for px, py in FIG11_PIXELS:
        x = 10.0 ** (3.0 + (px - c["x0"]) / c["dx"])
        y = 10.0 ** (2.0 - (py - c["y0"]) / c["dy"])
        ra.append(x / 1.0e4)
        nu.append(y / 10.0)
    return np.array(ra), np.array(nu)


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------
# Bar-Cohen, Iyengar and Kraus (2003)
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------

def bik_nu_fin(el_eta):
    """!
    @brief Equation 13 of Bar-Cohen, Iyengar and Kraus (2003): Nu_fin = [576 / (eta El)^2 + 2.873 / (eta El)^(1/2)]^(-1/2).
    @param el_eta Product eta_fin El (the Elenbaas number with the mean fin excess temperature eta theta_b).
    @return Nu_fin = h_fin s / k.
    """
    return (576.0 / el_eta ** 2 + 2.873 / el_eta ** 0.5) ** -0.5


def bik_array(theta_b, s, t, height, length, width, k_fin, t_amb_c=25.0, c_plate=0.59, tip="insulated"):
    """!
    @brief The plate-fin array of Bar-Cohen, Iyengar and Kraus (2003), equations 1 to 14: isothermal base, insulated tips, composite Nusselt number on the fins.
    @details qT = n_fin (q_fin + h_base A_b,f theta_b) (eq. 1, 2), A_b,f = L s (3), n_fin = W / (s + t) (5), q_fin = L k t theta_b m tanh(mH) (7), m = (2 h_fin / k t)^(1/2) (8),
             eta = tanh(mH) / mH (9), h_base = C Ra_L^(1/4) k / L with C = 0.59 (10, 11), Nu_fin = h_fin s / k from eq. 13 with El = g beta theta_b Pr s^4 / (L nu^2) (14)
             and eta_fin El in place of El; the array coefficient h_a = qT / (L W theta_b) (16). The film temperature for the properties is t_amb + theta_b / 2 (the paper does not
             say; the effect of 20 to 45 degC ambient is shown by the study).
    @param theta_b Base excess over the ambient in K.
    @param s Gap between the fins in m.
    @param t Fin thickness in m.
    @param height Fin height in m (H of the paper, tip not corrected).
    @param length Length in the flow direction in m (L).
    @param width Width of the base in m (W).
    @param k_fin Fin conductivity in W/mK.
    @param t_amb_c Ambient temperature in degC.
    @param c_plate C of equation 10 for the unfinned base (0.59).
    @param tip Only "insulated" (the paper's assumption).
    @return Dict with ha (W/m2K), q (W), h_fin, eta, el, nu_fin.
    """
    p = ch.air(t_amb_c + 0.5 * theta_b)
    el = G * p["beta"] * theta_b * p["pr"] * s ** 4 / (length * p["nu"] ** 2)

    def residual(h):
        """!
        @brief Fixed point of h_fin = Nu_fin(eta(h) El) k / s.
        @param h Trial coefficient in W/m2K.
        @return h_new - h.
        """
        m = math.sqrt(2.0 * h / (k_fin * t))
        eta = math.tanh(m * height) / (m * height)
        return bik_nu_fin(eta * el) * p["k"] / s - h

    h_fin = brentq(residual, 1e-6, 1e4)
    m = math.sqrt(2.0 * h_fin / (k_fin * t))
    eta = math.tanh(m * height) / (m * height)
    q_fin = length * k_fin * t * theta_b * m * math.tanh(m * height)
    ra_l = G * p["beta"] * theta_b * p["pr"] * length ** 3 / p["nu"] ** 2
    h_base = c_plate * ra_l ** 0.25 * p["k"] / length
    n_fin = width / (s + t)
    q = n_fin * (q_fin + h_base * length * s * theta_b)
    return {"ha": q / (length * width * theta_b), "q": q, "h_fin": h_fin, "eta": eta, "el": el, "nu_fin": bik_nu_fin(eta * el), "q_fin": q_fin, "m": m}


def bik_s_opt_eq17(theta_b, length, eta, t_amb_c=25.0, coeff=2.66):
    """!
    @brief Equation 17 of Bar-Cohen, Iyengar and Kraus (2003): s_opt = 2.66 (L nu^2 / (g beta eta theta_b Pr))^(1/4).
    @param theta_b Base excess in K.
    @param length Length in m.
    @param eta Fin efficiency.
    @param t_amb_c Ambient in degC.
    @param coeff The coefficient (2.66 of the paper; 2.7156 recomputed from equation 13).
    @return Spacing in m.
    """
    p = ch.air(t_amb_c + 0.5 * theta_b)
    return coeff * (length * p["nu"] ** 2 / (G * p["beta"] * eta * theta_b * p["pr"])) ** 0.25


def bik_least_material(theta_b, s, length, width, k_fin, t_amb_c=25.0):
    """!
    @brief The least-material array of the paper: fin thickness equal to the spacing, fin height from equation 20 (t = 0.993 h_fin H^2 / k), iterated with the composite h_fin.
    @param theta_b Base excess in K.
    @param s Gap and fin thickness in m (the paper finds t = s at the optimum).
    @param length Length in m.
    @param width Width in m.
    @param k_fin Fin conductivity in W/mK.
    @param t_amb_c Ambient in degC.
    @return Dict of bik_array plus the height used.
    """
    h = 20.0
    height = 0.1
    for _ in range(200):
        height_new = math.sqrt(s * k_fin / (0.993 * h))
        res = bik_array(theta_b, s, s, height_new, length, width, k_fin, t_amb_c)
        if abs(height_new - height) < 1e-9 and abs(res["h_fin"] - h) < 1e-9:
            height = height_new
            break
        height, h = height_new, 0.5 * (h + res["h_fin"])
    res = bik_array(theta_b, s, s, height, length, width, k_fin, t_amb_c)
    res["height"] = height
    return res


def optimum_of_ha(theta_b, t, height, length, width, k_fin, t_amb_c=25.0, bounds=(1e-3, 0.03)):
    """!
    @brief Spacing that maximises the array coefficient h_a for fixed fin thickness and height (the maximum of Figure 2 of the paper).
    @param theta_b Base excess in K.
    @param t Fin thickness in m.
    @param height Fin height in m.
    @param length Length in m.
    @param width Width in m.
    @param k_fin Fin conductivity in W/mK.
    @param t_amb_c Ambient in degC.
    @param bounds Search interval of the spacing in m.
    @return Tuple (s_opt in m, h_a in W/m2K).
    """
    res = minimize_scalar(lambda s: -bik_array(theta_b, s, t, height, length, width, k_fin, t_amb_c)["ha"], bounds=bounds, method="bounded", options={"xatol": 1e-7})
    return res.x, -res.fun


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------
# Ostrach (1953)
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------

# -H'(0) of Table I of NACA Report 1111, read from the image of the table (the OCR text of the scan is unusable); Pr: value
OSTRACH_TABLE_I = {0.01: 0.0812, 0.72: 0.5046, 0.733: 0.5080, 1.0: 0.5671, 2.0: 0.7165, 10.0: 1.1694, 100.0: 2.191}


def ostrach_h0(pr, eta_max=None, full=False):
    """!
    @brief Independent solution of the similarity equations of the isothermal vertical plate and the heat transfer parameter -H'(0).
    @details F''' + 3 F F'' - 2 F'^2 + H = 0,  H'' + 3 Pr F H' = 0, F(0) = F'(0) = 0, H(0) = 1, F'(inf) = H(inf) = 0 (Ostrach 1953 form, the variable eta = (Gr_x / 4)^(1/4) y / x);
             solved with scipy's collocation `solve_bvp` on a finite interval with a continuation in Pr. The local Nusselt number is Nu_x = -H'(0) (Gr_x / 4)^(1/4).
    @param pr Prandtl number.
    @param eta_max Truncation of the semi-infinite interval; None picks 14 (Pr >= 0.5) or 14 / sqrt(Pr) (thicker thermal layer for small Pr), at most 400.
    @param full True to return the pair (F''(0), -H'(0)).
    @return -H'(0), or the pair.
    """
    if eta_max is None:
        eta_max = 14.0 if pr >= 0.5 else 14.0 / pr ** 0.5
        eta_max = min(eta_max, 400.0)

    def rhs(eta, y):
        """!
        @brief First-order system y = (F, F', F'', H, H').
        @param eta Similarity variable (unused, autonomous).
        @param y State array.
        @return Derivatives.
        """
        f, fp, fpp, h, hp = y
        return np.vstack([fp, fpp, -3.0 * f * fpp + 2.0 * fp ** 2 - h, hp, -3.0 * pr * f * hp])

    def bc(ya, yb):
        """!
        @brief Boundary conditions at 0 and eta_max.
        @param ya State at 0.
        @param yb State at eta_max.
        @return Residuals.
        """
        return np.array([ya[0], ya[1], ya[3] - 1.0, yb[1], yb[3]])

    eta = np.linspace(0.0, eta_max, 400)
    guess = np.zeros((5, eta.size))
    decay = np.exp(-eta / 2.0)
    guess[0] = 0.5 * (1 - decay)
    guess[1] = 0.25 * decay * eta / 1.0 * 0.5
    guess[2] = 0.3 * decay
    guess[3] = decay
    guess[4] = -0.5 * decay
    sol = solve_bvp(rhs, bc, eta, guess, tol=1e-9, max_nodes=200000)
    if not sol.success:
        raise RuntimeError(f"Ostrach similarity solution did not converge for Pr = {pr}: {sol.message}")
    if full:
        return float(sol.y[2][0]), float(-sol.y[4][0])
    return -sol.y[4][0]


def ostrach_h0_shooting(pr, guess=None):
    """!
    @brief Second, independent solution of the same similarity equations: shooting from the wall with an adaptive Runge-Kutta (DOP853) and a Newton search for F''(0) and H'(0).
    @param pr Prandtl number.
    @param guess Starting values (F''(0), H'(0)); None takes the collocation solution of `ostrach_h0`.
    @return Tuple (F''(0), -H'(0)).
    """
    from scipy.integrate import solve_ivp
    from scipy.optimize import fsolve

    eta_max = 40.0 if pr >= 0.5 else 120.0

    def rhs(eta, y):
        """!
        @brief Right side of the first-order system (F, F', F'', H, H').
        @param eta Similarity variable (unused).
        @param y State.
        @return Derivatives.
        """
        f, fp, fpp, h, hp = y
        return [fp, fpp, -3.0 * f * fpp + 2.0 * fp ** 2 - h, hp, -3.0 * pr * f * hp]

    def resid(p):
        """!
        @brief Far-field residuals F'(eta_max), H(eta_max).
        @param p Trial (F''(0), H'(0)).
        @return Two residuals.
        """
        s = solve_ivp(rhs, [0.0, eta_max], [0.0, 0.0, p[0], 1.0, p[1]], rtol=1e-11, atol=1e-13, method="DOP853")
        return [s.y[1, -1], s.y[3, -1]]

    if guess is None:
        fpp0, h0 = ostrach_h0(pr, full=True)
        guess = (fpp0, -h0)
    p = fsolve(resid, guess, xtol=1e-12)
    return float(p[0]), float(-p[1])


def churchill_prandtl_function(pr):
    """!
    @brief The Prandtl dependence of the laminar term of Churchill and Chu: 0.670 / [1 + (0.492/Pr)^(9/16)]^(4/9), in Nu_L = f(Pr) Ra_L^(1/4) (the form without the 0.68).
    @param pr Prandtl number.
    @return f(Pr).
    """
    return 0.670 / (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (4.0 / 9.0)


def ostrach_prandtl_function(pr):
    """!
    @brief The same function from the similarity solution: Nu_L = (4/3) Nu_x(L) = (4/3) (-H'(0)) (Gr_L/4)^(1/4) = (4/3) (-H'(0)) 2^(-1/2) Pr^(-1/4) Ra_L^(1/4).
    @param pr Prandtl number.
    @return f(Pr) in Nu_L = f Ra_L^(1/4).
    """
    return (4.0 / 3.0) * ostrach_h0(pr) / math.sqrt(2.0) / pr ** 0.25


# ---------------------------------------------------------------------------------------------------------------------------------------------------------------
# Horizontal-base arrays: ENCIT 2012 (measured, plot values) and Tari and Mehrtash (2013) (CFD correlation)
# ---------------------------------------------------------------------------------------------------------------------------------------------------------------

# Dimensions of Table 1 of Da Silva and others (ENCIT 2012): n fins, gap S, thickness t, height H, length L, width W, base thickness b (mm); 6063-T5 aluminium
ENCIT_ARRAYS = {
    1: {"n": 7, "s": 14.35, "t": 2.0, "h": 7.0, "l": 100.0, "w": 100.10},
    2: {"n": 7, "s": 14.35, "t": 2.0, "h": 14.0, "l": 100.0, "w": 100.10},
    3: {"n": 7, "s": 14.35, "t": 2.0, "h": 20.0, "l": 100.0, "w": 100.10},
    4: {"n": 14, "s": 5.55, "t": 2.0, "h": 7.0, "l": 100.0, "w": 100.15},
    5: {"n": 14, "s": 5.55, "t": 2.0, "h": 14.0, "l": 100.0, "w": 100.15},
    6: {"n": 14, "s": 5.55, "t": 2.0, "h": 20.0, "l": 100.0, "w": 100.15},
}

# Mean coefficient on the total wetted area against the base excess (K, W/m2K), read from the plots of Figures 4 to 6 of the paper (PLOT VALUES, +-0.3 W/m2K,
# +-2 K; the "experimental" curves, radiation neglected by the authors, heater power less the conduction loss through the MDF insulation). Every plotted point is
# listed (the review added four that a first reading had left out: array 2 at 36 K, array 5 at 35 and 51 K, array 6 at 13 K): 47 points.
ENCIT_H_MEASURED = {
    1: [(14, 6.2), (20, 7.9), (33, 8.0), (45, 8.3), (59, 8.7), (76, 9.0), (91, 9.7)],
    2: [(12, 4.7), (27, 6.2), (35, 6.9), (36, 6.85), (51, 7.6), (56, 7.8), (62, 8.1), (68, 8.3)],
    3: [(14, 6.3), (23, 6.3), (27, 7.8), (32, 8.8), (41, 9.3), (49, 10.0), (59, 10.3)],
    4: [(11, 2.6), (19, 3.1), (27, 4.0), (35, 4.5), (44, 5.4), (58, 5.5), (69, 6.0)],
    5: [(12, 3.0), (26, 4.0), (33, 4.6), (35, 4.45), (42, 4.95), (49, 5.05), (51, 5.1), (60, 5.35), (65, 5.5)],
    6: [(8, 2.5), (13, 3.0), (17, 3.6), (22, 4.2), (29, 4.6), (36, 5.0), (43, 5.4), (50, 5.75), (56, 6.0)],
}


def array_geometry(a):
    """!
    @brief Wetted areas of a rectangular plate-fin array of ENCIT_ARRAYS (SI).
    @param a Entry of ENCIT_ARRAYS (mm).
    @return Dict with the free base area, the fin side area, the fin tip area, the end faces and the total (m2), and the heights.
    """
    n, s, t, h, l, w = a["n"], a["s"] * 1e-3, a["t"] * 1e-3, a["h"] * 1e-3, a["l"] * 1e-3, a["w"] * 1e-3
    free_base = (n - 1) * s * l + 0.0                    # between fins; the base outside the first and last fin is neglected (W = n t + (n - 1) s to within 0.1 mm)
    sides = 2.0 * n * h * l
    tips = n * t * l
    return {"free_base": free_base, "sides": sides, "tips": tips, "total": free_base + sides + tips, "h": h, "t": t, "s": s, "l": l, "w": w, "n": n}


def uniform_h_array(a, delta_t, k_fin=200.0, t_amb_c=20.0, channel_length=None, fins="program"):
    """!
    @brief What the program's finned block does with this array on a horizontal base: one uniform coefficient on every face, the horizontal-plate coefficient of a plate hot
           face up (McAdams, Nu = 0.54 Ra^(1/4), length area/perimeter of the base) and the straight-fin efficiency; returned as the mean coefficient on the total wetted area.
    @details With fins = "program" the heat is the one of `pcbthermal.blocks.fin_ratio` (called, not copied): per unit of base area (1 - t/p) + 2 Hc eta / p, so the block
             of width W carries W/p fins (6.12 for the 14.35 mm arrays, 13.2 for the 5.55 mm ones, against 7 and 14 real fins). With fins = "actual" the same uniform
             coefficient is put on the real fins (n fins, n - 1 gaps), which isolates the channel effect from the fin count. In both cases the heat is divided by the real
             wetted area (free base, fin sides and tips), the area basis of the measurement. Face coefficient from the fits of `channel.air` (the same fits as
             `convection.air_properties`). Convection only.
    @param a Entry of ENCIT_ARRAYS.
    @param delta_t Base excess in K.
    @param k_fin Fin conductivity in W/mK (6063-T5: 200 is a typical value, not given by the paper).
    @param t_amb_c Ambient in degC.
    @param channel_length If given (m), the coefficient is multiplied by the channel fraction phi(Ra_b) of Proposal B of `research/fin-channel/INTEGRATION.md`, with Ra_b computed
           with this length of channel (the vertical-channel rule used outside its orientation; the length is a choice: the fin length or half of it).
    @param fins "program" (the fin ratio of the program, W/p fins) or "actual" (the real fins of the array).
    @return Dict with h_face, eta, q (W), h_mean (W/m2K on the total area) and phi.
    @throws ValueError For another value of fins.
    """
    g = array_geometry(a)
    p = ch.air(t_amb_c + 0.5 * delta_t)
    lc = g["w"] * g["l"] / (2.0 * (g["w"] + g["l"]))
    ra = G * p["beta"] * delta_t * lc ** 3 / (p["nu"] * p["alpha"])
    h_face = 0.54 * ra ** 0.25 * p["k"] / lc
    phi = 1.0
    if channel_length is not None:
        phi = ch.phi(ch.ra_channel(delta_t, g["s"], channel_length, t_amb_c))
        h_face *= phi
    hc = g["h"] + 0.5 * g["t"]
    m = math.sqrt(2.0 * h_face / (k_fin * g["t"]))
    eta = math.tanh(m * hc) / (m * hc)
    if fins == "actual":
        # The real array: n fins and n - 1 gaps, the uniform coefficient on every wetted face
        q = delta_t * h_face * (g["free_base"] + eta * (g["sides"] + g["tips"]))
    elif fins == "program":
        # The program's block: the fin ratio per unit of base area times the base area W L (the program does not know where the first and last fins stand)
        block = types.SimpleNamespace(has_fins=lambda: True, fin_thickness=g["t"], fin_pitch=g["s"] + g["t"], fin_height=g["h"], k=k_fin)
        q = delta_t * h_face * blocks.fin_ratio(h_face, block) * g["w"] * g["l"]
    else:
        raise ValueError("fins must be 'program' or 'actual'")
    return {"h_face": h_face, "eta": eta, "q": q, "h_mean": q / (g["total"] * delta_t), "ra": ra, "phi": phi}


def tari_horizontal_up(a, delta_t, t_amb_c=20.0):
    """!
    @brief Equation 5 of Tari and Mehrtash (2013), upward-facing horizontal plate-fin heat sink: Nu_S = 0.0915 (Gr'_up,h Pr)^0.436, Gr'_up,h = g beta dT S^3 (H/L)^0.5 (S/H)^0.38 / nu^2.
    @details Fitted to CFD of heat sinks with L = 250 and 340 mm, H = 5 to 25 mm, S = 8.8 to 14.7 mm, t = 3 mm, 25 to 125 W (section 3.1 of the paper); valid for Gr' Pr < 5000
             (equation 10). Which area the coefficient h refers to is not stated in the text read; it is returned as given (h = Nu_S k / S).
    @param a Entry of ENCIT_ARRAYS.
    @param delta_t Base excess in K.
    @param t_amb_c Ambient in degC.
    @return Dict with h (W/m2K), the modified Grashof-Prandtl product and a flag for the validity range of the correlation.
    """
    g = array_geometry(a)
    p = ch.air(t_amb_c + 0.5 * delta_t)
    gr_mod = G * p["beta"] * delta_t * g["s"] ** 3 * (g["h"] / g["l"]) ** 0.5 * (g["s"] / g["h"]) ** 0.38 / p["nu"] ** 2
    x = gr_mod * p["pr"]
    nu = 0.0915 * x ** 0.436
    return {"h": nu * p["k"] / g["s"], "x": x, "nu_s": nu, "in_range": bool(x < 5000.0 and 8.8e-3 <= g["s"] <= 14.7e-3 and g["l"] >= 0.25)}


def tari_horizontal_down(a, delta_t, t_amb_c=20.0):
    """!
    @brief Equation 4 of Tari and Mehrtash (2013), downward-facing horizontal heat sink: Nu_S = 0.0149 Ra_S^0.5, Ra_S = g beta dT S^3 / (nu alpha).
    @param a Entry of ENCIT_ARRAYS (only S is used).
    @param delta_t Base excess in K.
    @param t_amb_c Ambient in degC.
    @return h in W/m2K (h = Nu_S k / S).
    """
    g = array_geometry(a)
    p = ch.air(t_amb_c + 0.5 * delta_t)
    ra = G * p["beta"] * delta_t * g["s"] ** 3 / (p["nu"] * p["alpha"])
    return 0.0149 * ra ** 0.5 * p["k"] / g["s"]
