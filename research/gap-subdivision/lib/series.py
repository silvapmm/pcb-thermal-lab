#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file series.py
@brief Exact (series) solution of a uniform laminated plate with a rectangular source: any number of layers, orthotropic, films on both faces, adiabatic sides.
@details The reference of the gap-subdivision investigation for boards without patterned copper (imports nothing from pcbthermal). The plate is a stack of layers
         (thickness t, in-plane conductivity kxy, through conductivity kz) from the top down, a film h_top on the whole top face, a film h_bottom on the whole bottom face, adiabatic
         sides; the source is a uniform flux on a rectangle of the top face. Each mode cos(lam x) cos(del y) of the cosine series has an exact solution through the stack:
         in a layer, kz T'' = kxy beta^2 T with beta^2 = lam^2 + del^2, so the layer has the admittance Yc = beta sqrt(kxy kz) and the exponent g t with g = beta sqrt(kxy / kz);
         the admittance seen from the top of a layer that rests on an admittance Yb is Y = Yc (Yb + Yc tanh(g t)) / (Yc + Yb tanh(g t)), the film on the top face is in parallel.
         The temperature of the top face is then the sum over the modes of (flux coefficient) / (admittance). No mesh and no node count: this is the answer that every
         discretisation through the thickness must approach. Checked in tests/test_series.py against the series circuit, Eq. 27 of Muzychka, Culham and
         Yovanovich (2003) (single layer) and Eqs. 14 and 15 of Yovanovich, Muzychka and Culham (1999) (two layers, lib/yovanovich1999.py).
"""

import numpy as np


def _coef(n, length, centre, width):
    """!
    @brief Cosine-series coefficients of a rectangle of unit integral on [0, length].
    @param n Highest mode.
    @param length Plate size in m.
    @param centre Centre of the rectangle in m.
    @param width Width of the rectangle in m.
    @return numpy.ndarray of n + 1 coefficients F_m so that f(x) = sum F_m cos(m pi x / length) has the integral 1 over the rectangle (F_0 = 1 / length).
    """
    m = np.arange(0, n + 1)
    lam = m * np.pi / length
    with np.errstate(invalid="ignore", divide="ignore"):
        s = np.where(m == 0, 1.0, np.sin(lam * width / 2) / (lam * width / 2))
    return np.where(m == 0, 1.0, 2.0) * s * np.cos(lam * centre) / length


def _window(n, length, width):
    """!
    @brief Attenuation of mode m when the field is averaged over a window of the given width (a sinc).
    @param n Highest mode.
    @param length Plate size in m.
    @param width Window width in m (0 or less: none).
    @return numpy.ndarray of n + 1 factors.
    """
    m = np.arange(0, n + 1)
    lam = m * np.pi / length
    if width <= 0:
        return np.ones(n + 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(m == 0, 1.0, np.sin(lam * width / 2) / (lam * width / 2))


def admittance(beta, layers, h_top, h_bottom):
    """!
    @brief Admittance (flux per temperature of a mode) seen from the top face of the stack, films included.
    @param beta Array of mode wave numbers sqrt(lam^2 + del^2) in 1/m (zero allowed).
    @param layers List of (thickness m, kxy W/mK, kz W/mK) from the top down.
    @param h_top Film coefficient of the top face in W/m2K.
    @param h_bottom Film coefficient of the bottom face in W/m2K.
    @return numpy.ndarray with the shape of beta.
    """
    beta = np.asarray(beta, dtype=float)
    y = np.full(beta.shape, float(h_bottom))
    safe = np.where(beta > 0, beta, 1.0)
    for t, kxy, kz in reversed(layers):
        yc = safe * np.sqrt(kxy * kz)
        th = np.tanh(safe * np.sqrt(kxy / kz) * t)
        # A layer resting on the admittance y; y = 0 (adiabatic bottom) works too
        y = yc * (y + yc * th) / (yc + y * th)
    # Zero mode: the series of the through resistances, no lateral flow
    r0 = sum(t / kz for t, _, kz in layers)
    y0 = 1.0 / (r0 + 1.0 / h_bottom) if h_bottom > 0 else 0.0
    y = np.where(beta > 0, y, y0)
    return y + h_top


def source_rise(a, b, layers, h_top, h_bottom, power, xs, ys, window=(0.0, 0.0), points=((None, None),), nmax=None):
    """!
    @brief Temperature rise of the top face of a laminated plate under a uniform rectangular source, at points or averaged over small windows.
    @param a Plate size along x in m.
    @param b Plate size along y in m.
    @param layers List of (thickness m, kxy, kz) from the top down.
    @param h_top Film coefficient of the top face (whole face) in W/m2K.
    @param h_bottom Film coefficient of the bottom face in W/m2K.
    @param power Heat in W (all of it enters through the source).
    @param xs Source (centre x in m, width in m).
    @param ys Source (centre y in m, height in m).
    @param window (wx, wy) size in m of the window over which the rise is averaged at each point (0: the value at the point).
    @param points List of (x, y) centres in m where the rise is wanted; (None, None) means the source centre.
    @param nmax Highest mode in each direction (None: chosen from the smallest length scale, between 600 and 2400).
    @return numpy.ndarray of rises in K, one per point.
    @note The temperature is that of the top face of the first layer (the program's copper node differs by q t / (2 k), a few mK for 35 um of copper).
    """
    xc, c = xs
    yc, d = ys
    if nmax is None:
        # At least 60 modes across the smallest of the source size and the window
        small = min([v for v in (c, d, window[0] or 1e9, window[1] or 1e9)])
        nmax = int(min(max(600, 60 * max(a, b) / small), 2400))
    fx = _coef(nmax, a, xc, c)
    fy = _coef(nmax, b, yc, d)
    lam = np.arange(0, nmax + 1) * np.pi / a
    dl = np.arange(0, nmax + 1) * np.pi / b
    wx, wy = _window(nmax, a, window[0]), _window(nmax, b, window[1])
    out = []
    for (px, py) in points:
        px = xc if px is None else px
        py = yc if py is None else py
        total = 0.0
        # Chunk over the x modes to bound the memory of the 2D mode grid
        for i0 in range(0, nmax + 1, 200):
            i1 = min(i0 + 200, nmax + 1)
            beta = np.sqrt(lam[i0:i1, None] ** 2 + dl[None, :] ** 2)
            y = admittance(beta, layers, h_top, h_bottom)
            cx = fx[i0:i1] * wx[i0:i1] * np.cos(lam[i0:i1] * px)
            cy = fy * wy * np.cos(dl * py)
            total += float(np.sum(cx[:, None] * cy[None, :] / y))
        out.append(power * total)
    return np.array(out)


def spreading_resistance(a, b, c, d, layers, h_bottom, nmax=800):
    """!
    @brief Rs = (mean source temperature - mean temperature of the contact plane) / Q of a centred source on a laminated channel with an adiabatic top (Eq. 11 of Yovanovich et al. 1999).
    @param a Channel size along x in m (the paper's 2c).
    @param b Channel size along y in m (the paper's 2d).
    @param c Source size along x in m (the paper's 2a).
    @param d Source size along y in m (the paper's 2b).
    @param layers List of (thickness m, kxy, kz) from the top down.
    @param h_bottom Film coefficient of the bottom face in W/m2K.
    @param nmax Highest mode in each direction.
    @return Rs in K/W.
    """
    # Mean source rise for 1 W, less the contact-plane mean (the zero mode: the 1D resistance per area over the channel area)
    rs = source_rise(a, b, layers, 0.0, h_bottom, 1.0, (a / 2, c), (b / 2, d), window=(c, d), nmax=nmax)[0]
    r1d = (sum(t / kz for t, _, kz in layers) + 1.0 / h_bottom) / (a * b)
    return float(rs - r1d)
