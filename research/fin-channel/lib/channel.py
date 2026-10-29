#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file channel.py
@brief Composite correlations of natural convection between vertical isothermal parallel plates (the channel effect between close fins) and a plate-fin array model that uses them.

@details Sources (the reading status of each is in the README of this folder and in research/theory/BIBLIOGRAPHY.md):
         * Elenbaas (1942), as written in Teertstra, Culham and Yovanovich, "Comprehensive review of natural and mixed convection heat transfer models for circuit board
           arrays" (equation 8):        Nu_b = (1/24) Ra_b [1 - exp(-35/Ra_b)]^(3/4)
         * Churchill (1977), same review, equation 20:      Nu_b = [ (24/Ra_b)^(3/2) + ( [1 + (0.492/Pr)^(9/16)]^(4/9) / (0.75 Ra_b^(1/4)) )^(3/2) ]^(-2/3)
         * Bar-Cohen and Rohsenow (1984), same review, equation 21 (Pr = 0.7, symmetric isothermal):  Nu_b = [ (24/Ra_b)^2 + (1/(0.59 Ra_b^(1/4)))^2 ]^(-1/2)
         * Raithby and Hollands (1985), same review, equation 22 with r_T = 1:  Nu_b = [ (24/Ra_b)^1.9 + (1/(C Ra_b^(1/4)))^1.9 ]^(-1/1.9), C = 0.62
         with Nu_b = h b / k (b the gap between the plates, h the mean coefficient of one wall) and the channel (Elenbaas) Rayleigh number
         Ra_b = g beta (Tw - T0) b^4 Pr / (nu^2 L) (L the height of the plates, the length of the channel in the flow direction); equations 1 to 6 of the review.
         Air properties at the film temperature (Tw + T0)/2; beta = 1/T0 in the review, 1/T_film here (the difference is below 8 % of Ra at 60 K; documented in the README).

         The array model is the standard one of the plate-fin heat sink: n fins of thickness t and height H, gaps s, length L in the flow direction, the channels between
         fins with the channel coefficient, the two outer faces with the coefficient of an isolated vertical plate; each fin as a straight fin with an adiabatic tip at
         the corrected height Hc = H + t/2 and the efficiency tanh(mHc)/(mHc), the same fin formula as `pcbthermal.blocks.fin_ratio`. The wall excess temperature that drives the
         channel Rayleigh number is the area-weighted mean of the base (excess theta_b) and of the fins (mean excess eta theta_b: the mean temperature ratio of an adiabatic-tip
         fin equals its efficiency).
"""

import math

import numpy as np
from scipy.optimize import minimize_scalar

G = 9.80665
P_ATM = 101325.0
R_AIR = 287.05
CP_AIR = 1007.0


def air(t_film_c):
    """!
    @brief Properties of dry air at atmospheric pressure (Sutherland-type fits, the same fits as `pcbthermal.convection.air_properties`, written again here).
    @param t_film_c Film temperature in degC.
    @return Dict with k (W/mK), nu (m2/s), alpha (m2/s), pr and beta (1/K, ideal gas at the film temperature).
    """
    t = t_film_c + 273.15
    mu = 1.458e-6 * t ** 1.5 / (t + 110.4)
    k = 2.648e-3 * t ** 1.5 / (t + 245.4 * 10.0 ** (-12.0 / t))
    rho = P_ATM / (R_AIR * t)
    return {"k": k, "nu": mu / rho, "alpha": k / (rho * CP_AIR), "pr": mu * CP_AIR / k, "beta": 1.0 / t}


def ra_channel(delta_t, gap, length, t_ambient_c=20.0, t_wall_excess=None):
    """!
    @brief Channel (Elenbaas) Rayleigh number Ra_b = g beta dT b^4 Pr / (nu^2 L).
    @param delta_t Wall-to-ambient temperature difference in K.
    @param gap Distance between the plates in m.
    @param length Length of the channel in the flow direction in m.
    @param t_ambient_c Ambient air temperature in degC.
    @param t_wall_excess Unused (kept so that callers can pass the same dict); the film temperature is ambient + dT/2.
    @return Dimensionless number.
    """
    p = air(t_ambient_c + 0.5 * delta_t)
    return G * p["beta"] * delta_t * gap ** 4 * p["pr"] / (p["nu"] ** 2 * length)


def nu_elenbaas(ra):
    """!
    @brief Elenbaas (1942) mean Nusselt number of the symmetric isothermal channel, equation 8 of the Teertstra review.
    @param ra Channel Rayleigh number Ra_b.
    @return Nu_b = h b / k.
    """
    return ra / 24.0 * (1.0 - math.exp(-35.0 / ra)) ** 0.75


def nu_churchill(ra, pr=0.71):
    """!
    @brief Churchill (1977) composite correlation of the symmetric isothermal channel, equation 20 of the Teertstra review.
    @param ra Channel Rayleigh number Ra_b.
    @param pr Prandtl number.
    @return Nu_b.
    """
    c = (1.0 + (0.492 / pr) ** (9.0 / 16.0)) ** (4.0 / 9.0)
    return ((24.0 / ra) ** 1.5 + (c / (0.75 * ra ** 0.25)) ** 1.5) ** (-2.0 / 3.0)


def nu_bcr(ra, c_fd=24.0, c_bl=0.59):
    """!
    @brief Bar-Cohen and Rohsenow (1984) composite correlation of the symmetric isothermal channel (Pr = 0.7), equation 21 of the Teertstra review (and equation 9.45 of Incropera and DeWitt as quoted in the repository).
    @param ra Channel Rayleigh number Ra_b.
    @param c_fd Constant of the fully developed limit (24 symmetric, 12 for one adiabatic wall).
    @param c_bl Constant of the boundary-layer limit (0.59).
    @return Nu_b.
    """
    return ((c_fd / ra) ** 2 + (1.0 / (c_bl * ra ** 0.25)) ** 2) ** -0.5


def nu_rh(ra, c=0.62, n=1.9):
    """!
    @brief Raithby and Hollands (1985) composite correlation of the symmetric isothermal channel, equation 22 of the Teertstra review with r_T = 1.
    @param ra Channel Rayleigh number Ra_b.
    @param c Boundary-layer constant (0.62, confirmed by Martin, Raithby and Yovanovich 1991).
    @param n Blending exponent (1.9).
    @return Nu_b.
    """
    return ((24.0 / ra) ** n + (1.0 / (c * ra ** 0.25)) ** n) ** (-1.0 / n)


CORRELATIONS = {"Elenbaas": nu_elenbaas, "Churchill": nu_churchill, "Bar-Cohen-Rohsenow": nu_bcr, "Raithby-Hollands": nu_rh}


def optimum_spacing_constants(nu_fun=nu_bcr, pr=0.71):
    """!
    @brief The optimum spacing of plates of negligible thickness that maximises the heat per unit base area, from a composite correlation.
    @details Heat per unit base area and per plate pair is 2 h L dT / b = 2 k L dT Nu_b / b^2, and Ra_b = c b^4, so the maximum is where Nu_b(Ra_b) / b^2 is largest;
             with b = S: S_opt = K L / Ra_L^(1/4) (Ra_L = g beta dT L^3 Pr / nu^2) and Nu_b(opt) is the number returned. Defined without any air property.
    @param nu_fun Function Nu_b(Ra_b).
    @param pr Prandtl number for the correlations that use it.
    @return Tuple (K, Ra_b at the optimum, Nu_b at the optimum).
    """
    def neg(lnb):
        """!
        @brief Negative of Nu_b / b^2 for a gap exp(lnb) in units where Ra_b = b^4.
        @param lnb Natural logarithm of the gap.
        @return Value to minimise.
        """
        b = math.exp(lnb)
        ra = b ** 4
        nu = nu_fun(ra, pr) if nu_fun is nu_churchill else nu_fun(ra)
        return -nu / b ** 2
    res = minimize_scalar(neg, bounds=(-3.0, 3.0), method="bounded", options={"xatol": 1e-10})
    b = math.exp(res.x)
    ra_b = b ** 4
    # Ra_b = Ra_L (b/L)^4, so b/L = Ra_b^(1/4) / Ra_L^(1/4)  ->  K = Ra_b^(1/4)
    nu = nu_fun(ra_b, pr) if nu_fun is nu_churchill else nu_fun(ra_b)
    return ra_b ** 0.25, ra_b, nu


def fin_efficiency(h, k, t, hc):
    """!
    @brief Efficiency of a straight fin with an adiabatic tip at the corrected height.
    @param h Coefficient on the fin in W/m2K.
    @param k Conductivity of the fin in W/mK.
    @param t Fin thickness in m.
    @param hc Corrected height H + t/2 in m.
    @return tanh(m hc)/(m hc), m = sqrt(2 h / (k t)).
    """
    m = math.sqrt(2.0 * max(h, 1e-12) / (k * t))
    return math.tanh(m * hc) / (m * hc)


def h_plate_vertical(delta_t, height, t_ambient_c=20.0, form="laminar"):
    """!
    @brief Isolated vertical isothermal plate, Churchill and Chu: the coefficient that a model without the channel effect would use on the fin faces.
    @param delta_t Wall-to-ambient difference in K.
    @param height Plate height (the flow length) in m.
    @param t_ambient_c Ambient temperature in degC.
    @param form "laminar" (0.68 + 0.670 Ra^(1/4)/[...]^(4/9)) or "general" (the all-range form).
    @return h in W/m2K (convection only).
    """
    p = air(t_ambient_c + 0.5 * delta_t)
    ra = G * p["beta"] * delta_t * height ** 3 / (p["nu"] * p["alpha"])
    f = 1.0 + (0.492 / p["pr"]) ** (9.0 / 16.0)
    if form == "laminar":
        nu = 0.68 + 0.670 * ra ** 0.25 / f ** (4.0 / 9.0)
    else:
        nu = (0.825 + 0.387 * ra ** (1.0 / 6.0) / f ** (8.0 / 27.0)) ** 2
    return nu * p["k"] / height


def phi(ra_b):
    """!
    @brief Fraction of the isolated-plate limit that the channel keeps: Nu_b / (0.59 Ra_b^(1/4)) of the Bar-Cohen and Rohsenow composite, a function of Ra_b alone.
    @details phi = [1 + (24 x 0.59 / Ra_b^(3/4))^2]^(-1/2) = [1 + (14.16 / Ra_b^(3/4))^2]^(-1/2): 0.9 at Ra_b = 90, 0.75 at 40.5 and 0.5 at 16.5; it tends to Ra_b/24 divided by 0.59 Ra_b^(1/4) (that is, to zero as Ra_b^(3/4)) for a gap that closes.
             It multiplies the coefficient the program already uses on the fins (so that a typed or computed coefficient is kept where the channel is open: phi tends to 1).
    @param ra_b Channel Rayleigh number Ra_b = g beta theta b^4 Pr / (nu^2 L).
    @return Number between 0 and 1.
    """
    return (1.0 + (24.0 * 0.59 / ra_b ** 0.75) ** 2) ** -0.5


def exposed_h_channel(theta_b, gap, t, height, length, k_fin, t_ambient_c=20.0, nu_fun=nu_bcr, tol=1e-9):
    """!
    @brief Coefficient of the finned face per unit of base area with the channel effect: the quantity `blocks.exposed_h` gives with a uniform coefficient.
    @details Per pitch p = gap + t and per unit of length: the free base (gap) and the two faces of a fin (corrected height Hc) see the channel coefficient
             h_ch = Nu_b k / gap, with Ra_b from the mean wall excess (base at theta_b, fins at eta theta_b); then
             h_exp = h_ch [ (1 - t/p) + 2 Hc eta / p ] as in `blocks.fin_ratio` but with h_ch. The outer faces of the first and last fin (single plate) are not distinguished (the
             arrays of interest have many fins).
    @param theta_b Excess temperature of the base of the fins over the ambient air in K.
    @param gap Air gap between two fins in m (pitch minus thickness).
    @param t Fin thickness in m.
    @param height Fin height H in m.
    @param length Length of the channel in the flow direction in m.
    @param k_fin Conductivity of the fins in W/mK.
    @param t_ambient_c Ambient temperature in degC.
    @param nu_fun Composite correlation Nu_b(Ra_b).
    @param tol Relative tolerance of the wall-excess iteration.
    @return Dict with h_exp (W/m2K per base area), h_ch, eta, ra_b, theta_wall.
    """
    p = gap + t
    hc = height + 0.5 * t
    th_w = theta_b
    for _ in range(200):
        ra = ra_channel(th_w, gap, length, t_ambient_c)
        a = air(t_ambient_c + 0.5 * th_w)
        h_ch = (nu_fun(ra, a["pr"]) if nu_fun is nu_churchill else nu_fun(ra)) * a["k"] / gap
        eta = fin_efficiency(h_ch, k_fin, t, hc)
        th_new = theta_b * (gap + eta * 2.0 * hc) / (gap + 2.0 * hc)
        done = abs(th_new - th_w) < tol * theta_b
        th_w = 0.5 * (th_w + th_new) if not done else th_new
        if done:
            break
    h_exp = h_ch * ((1.0 - t / p) + 2.0 * hc * eta / p)
    return {"h_exp": h_exp, "h_ch": h_ch, "eta": eta, "ra_b": ra, "theta_wall": th_w}


def array_heat(theta_b, n, s, t, height, length, k_fin, t_ambient_c=20.0, nu_fun=nu_bcr, channel=True, plate_form="laminar", tol=1e-6):
    """!
    @brief Convective heat of a plate-fin array on a vertical base (fins horizontal, channels vertical) for a given base excess temperature.
    @details channel=False reproduces what a model without the channel effect does: every face of the fins and the free base use the coefficient of an isolated vertical
             plate of height `length` at the same wall excess (the program's uniform-h fin model on a vertical board). channel=True uses the composite Nu_b of `nu_fun`
             for the n - 1 channels (their fin faces and the base between the fins) and the isolated-plate coefficient for the two outer faces. The fin
             efficiency is recomputed with each coefficient; the wall excess of the channels is iterated until it changes by less than tol (relative).
    @param theta_b Base-to-ambient temperature difference in K.
    @param n Number of fins.
    @param s Gap between fins in m.
    @param t Fin thickness in m.
    @param height Fin height H in m (from the base).
    @param length Length of the fins in the flow direction (vertical) in m.
    @param k_fin Conductivity of the fins in W/mK.
    @param t_ambient_c Ambient temperature in degC.
    @param nu_fun Composite correlation Nu_b(Ra_b) used for the channels.
    @param channel True to use the channel correlation, False for the isolated-plate coefficient everywhere.
    @param plate_form "laminar" or "general" Churchill-Chu form of the isolated plate.
    @param tol Relative tolerance of the wall-excess iteration.
    @return Dict with q (W), h_channel (W/m2K), h_outer, eta_channel, ra_b, theta_wall, area_base, width.
    """
    hc = height + 0.5 * t
    width = n * t + (n - 1) * s
    a_base_free = (n - 1) * s * length
    th_w = theta_b
    q = 0.0
    out = {}
    for _ in range(100):
        # Without the channel effect the coefficient is that of the board face at the base temperature (what the program does); with it, the outer faces see the wall mean
        h_plate = h_plate_vertical(th_w if channel else theta_b, length, t_ambient_c, plate_form)
        if channel:
            ra = ra_channel(th_w, s, length, t_ambient_c)
            p = air(t_ambient_c + 0.5 * th_w)
            h_ch = (nu_fun(ra, p["pr"]) if nu_fun is nu_churchill else nu_fun(ra)) * p["k"] / s
        else:
            ra = float("nan")
            h_ch = h_plate
        eta_ch = fin_efficiency(h_ch, k_fin, t, hc)
        eta_out = fin_efficiency(h_plate, k_fin, t, hc)
        # channel faces: 2 (n - 1) fin faces; outer: 2 faces; base between the fins in the channels
        q = theta_b * (h_ch * (a_base_free + 2 * (n - 1) * eta_ch * hc * length) + h_plate * 2 * eta_out * hc * length)
        a_ch_fin = 2 * (n - 1) * hc * length
        th_new = theta_b * (a_base_free + eta_ch * a_ch_fin) / (a_base_free + a_ch_fin)
        if abs(th_new - th_w) < tol * theta_b:
            th_w = th_new
            break
        th_w = 0.5 * (th_w + th_new)
    out.update({"q": q, "h_channel": h_ch, "h_outer": h_plate, "eta_channel": eta_ch, "ra_b": ra, "theta_wall": th_w, "area_base": a_base_free, "width": width})
    return out
