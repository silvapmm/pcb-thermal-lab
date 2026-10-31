#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file cosine_stack.py
@brief Cosine-series (Fourier) solution of a laminated rectangular block with a centred square source on the top face, for the truncation test of F1.
@details The block of lateral sides a x b has adiabatic sides, isotropic layers, a film coefficient on the top face and on the bottom face, and a uniform
flux on a centred square of side s on the top. The temperature is expanded in cos(m pi x / a) cos(n pi y / b); each mode is solved by the 2 x 2 transfer matrix of the
layers. The film is applied to the whole top face, also under the source, because that is the only case a separable series solves exactly (the program's
finite-volume solver leaves the source area without a film; the two differ at large Biot numbers, which is what the study measures). The solver imports nothing from the program.
"""

import numpy as np


def _mode_response(lam, layers, h_top, h_bottom):
    """!
    @brief Top and bottom surface temperatures of one mode for a unit top flux.
    @param lam Mode wavenumber (1/m), zero for the uniform mode.
    @param layers List of (thickness m, conductivity W/mK) from the top down.
    @param h_top Top film coefficient (W/m2K).
    @param h_bottom Bottom film coefficient (W/m2K).
    @return Tuple (T_top, T_bottom, None): surface temperatures per unit applied top flux (the third item is kept for call compatibility).
    """
    m = np.eye(2)
    for t, k in layers:
        if lam < 1e-12:
            li = np.array([[1.0, -t / k], [0.0, 1.0]])
        else:
            c, s = np.cosh(lam * t), np.sinh(lam * t)
            li = np.array([[c, -s / (k * lam)], [-k * lam * s, c]])
        m = li @ m
    # Unknown (T_top, phi_top): bottom state = m @ (T_top, phi_top), and phi_bottom = h_bottom T_bottom
    # Equations: phi_top = q - h_top T_top (q = 1); bottom: m[1,0] T + m[1,1] phi = h_bottom (m[0,0] T + m[0,1] phi)
    # Substituting phi = 1 - h_top T gives one linear equation in T
    p0 = m[1, 1] - h_bottom * m[0, 1]
    p1 = (m[1, 0] - h_bottom * m[0, 0]) - h_top * p0
    t_top = -p0 / p1
    phi = 1.0 - h_top * t_top
    t_bot = m[0, 0] * t_top + m[0, 1] * phi
    return t_top, t_bot, None


def solve(a, b, s, layers, h_top, h_bottom, power, n_modes):
    """!
    @brief Mean source temperature and mean wall temperature (free top face and bottom together) of the block.
    @param a Block length along x (m).
    @param b Block length along y (m).
    @param s Side of the centred square source (m).
    @param layers List of (thickness m, conductivity W/mK) from the top down.
    @param h_top Top film coefficient (W/m2K), applied to the whole top face (see the module note).
    @param h_bottom Bottom film coefficient (W/m2K).
    @param power Source power (W).
    @param n_modes Number of modes per direction (m, n = 0 .. n_modes - 1).
    @return Tuple (T_source_mean, T_wall_mean, R_solid) in K above the ambient and K/W.
    """
    q0 = power / (s * s)
    area = a * b
    t_src = 0.0
    top_total = 0.0          # integral of the top temperature over the whole top face
    bot_total = 0.0
    for m_i in range(n_modes):
        al = m_i * np.pi / a
        nm = 1.0 if m_i == 0 else 2.0
        fm = nm / a * (s if m_i == 0 else 2.0 / al * np.sin(al * s / 2.0) * np.cos(al * a / 2.0))
        # Mean of cos(al x) over the source, for the average of the temperature over the source
        sm = 1.0 if m_i == 0 else (2.0 / (al * s) * np.sin(al * s / 2.0) * np.cos(al * a / 2.0))
        for n_i in range(n_modes):
            be = n_i * np.pi / b
            nn = 1.0 if n_i == 0 else 2.0
            fn = nn / b * (s if n_i == 0 else 2.0 / be * np.sin(be * s / 2.0) * np.cos(be * b / 2.0))
            sn = 1.0 if n_i == 0 else (2.0 / (be * s) * np.sin(be * s / 2.0) * np.cos(be * b / 2.0))
            lam = np.hypot(al, be)
            q_mn = q0 * fm * fn
            tt, tb, _ = _mode_response(lam, layers, h_top, h_bottom)
            t_src += q_mn * tt * sm * sn
            if m_i == 0 and n_i == 0:                      # only the uniform mode has a nonzero mean over the whole face
                top_total += q_mn * tt * area
                bot_total += q_mn * tb * area
    # Wall: free top face (whole top minus the source) and the bottom; the source-area part of the top uses the source mean
    top_free = top_total - t_src * s * s
    t_wall = (top_free + bot_total) / (2.0 * area - s * s)
    return t_src, t_wall, (t_src - t_wall) / power
