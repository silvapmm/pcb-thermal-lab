#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file plate_series.py
@brief Closed-form cosine series of a plate with a centred square flux source: the surface temperature, the through-thickness mean and the source mean, for the Biot map.
@details Plate W x W x t, conductivity k (isotropic), side walls adiabatic, top face adiabatic except under the source (flux q = P / a^2), bottom face film h.
         Per mode (m, n) with lambda = pi sqrt(m^2 + n^2) / W and beta = h / (k lambda), the temperature rise is
             T(z) = C [cosh(lambda (t - z)) + beta sinh(lambda (t - z))],  k C lambda [sinh(lambda t) + beta cosh(lambda t)] = q_mn,
         so the top face is C [cosh(lambda t) + beta sinh(lambda t)] and the thickness mean is C [sinh(lambda t) + beta (cosh(lambda t) - 1)] / (lambda t).
         The uniform mode (lambda = 0) gives q0 / h + q0 t / k at the top and q0 / h + q0 t / (2 k) as the mean. No pcbthermal import: it is an independent reference,
         checked against tests/helpers/layered3d.py in tests/test_plate_series.py. Not a source of the literature; it is the textbook separation of variables.
"""
import numpy as np


def _coeff_1d(m, W, a, mean_over_source):
    """!
    @brief Cosine coefficient of the 1D indicator of the source [W/2 - a/2, W/2 + a/2] times the value of the mode at the evaluation point(s).
    @param m Array of mode numbers.
    @param W Plate side in m.
    @param a Source side in m.
    @param mean_over_source True: evaluate the mode as its mean over the source; False: at the centre W/2.
    @return Tuple (source coefficient c_m, mode value e_m) arrays.
    """
    m = np.asarray(m, dtype=float)
    lo, hi = W / 2 - a / 2, W / 2 + a / 2
    with np.errstate(divide="ignore", invalid="ignore"):
        integ = np.where(m == 0, a, W / (m * np.pi) * (np.sin(m * np.pi * hi / W) - np.sin(m * np.pi * lo / W)))
        ev_mean = np.where(m == 0, 1.0, W / (m * np.pi * a) * (np.sin(m * np.pi * hi / W) - np.sin(m * np.pi * lo / W)))
    eps = np.where(m == 0, 1.0, 2.0)
    c = eps / W * integ                                          # cosine coefficient of the indicator (times 1/W per axis)
    ev = ev_mean if mean_over_source else np.cos(m * np.pi / 2)
    return c, ev


def rises(W, a, t, k, h, q=1.0, modes=300, source_mean=False):
    """!
    @brief Top-face temperature rise and thickness-mean rise at the plate centre (or averaged over the source), above the film's ambient.
    @param W Plate side in m.
    @param a Source side in m (a < W).
    @param t Plate thickness in m.
    @param k Conductivity in W/mK.
    @param h Bottom film coefficient in W/m2K.
    @param q Flux in W/m2 under the source.
    @param modes Modes per axis (0 .. modes).
    @param source_mean True: both values are averaged over the source area instead of taken at the centre.
    @return Tuple (surface rise, mean rise) in K.
    """
    m = np.arange(modes + 1)
    c, ev = _coeff_1d(m, W, a, source_mean)
    cc = np.outer(c, c) * q                                      # q_mn
    ee = np.outer(ev, ev)
    lam = np.pi * np.hypot(m[:, None], m[None, :]) / W
    top = np.zeros_like(lam)
    mean = np.zeros_like(lam)
    z = lam == 0
    top[z] = 1.0 / h + t / k                                     # per unit q_00
    mean[z] = 1.0 / h + t / (2 * k)
    lz = lam[~z]
    be = h / (k * lz)
    x = np.minimum(lz * t, 600.0)                                # cosh overflow guard; ratios stay exact
    ch, sh = np.cosh(x), np.sinh(x)
    den = k * lz * (sh + be * ch)
    top[~z] = (ch + be * sh) / den
    mean[~z] = (sh + be * (ch - 1)) / (lz * t) / den
    return float((cc * ee * top).sum()), float((cc * ee * mean).sum())


def delta_fraction(Bi, t_over_a, W_over_a=5.0, modes=300, source_mean=False):
    """!
    @brief (surface - thickness mean) / surface rise at the source, from the dimensionless groups only.
    @param Bi h t / k of the bottom film.
    @param t_over_a Thickness over the source side.
    @param W_over_a Plate side over the source side.
    @param modes Modes per axis.
    @param source_mean Average over the source instead of the centre.
    @return float fraction of the surface rise.
    """
    a = 1.0
    t = t_over_a
    k = 1.0
    h = Bi * k / t
    s, mn = rises(W_over_a * a, a, t, k, h, 1.0, modes, source_mean)
    return (s - mn) / s
