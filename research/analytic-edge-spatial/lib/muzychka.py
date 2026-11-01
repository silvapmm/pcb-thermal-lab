#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file muzychka.py
@brief The thermal spreading resistance of a rectangular flux channel with edge cooling, equation 21 of Muzychka, Culham and Yovanovich (AIAA 2003-4188, Part II), and the fin limit of the same problem.

@details The channel is 2c x 2d x t, with a heat source of 2a x 2b at the centre of the top face (the rest of the top face adiabatic), a film h on the bottom face and
         film coefficients h_ex, h_ey on the edges x = c and y = d (planes of symmetry x = 0, y = 0). Equation 21 (read as an image of p. 4 of the paper; the page was
         also OCR'd by a model, which is untrusted, and every symbol was checked against the independent finite-volume solution in tests/test_analytic_edge.py):

             R_t = c d / (k a^2 b^2) sum_m sum_n sin^2(dx_m a/c) sin^2(dy_n b/d) phi_mn / (dx_m dy_n beta_mn [sin(2 dx_m)/2 + dx_m][sin(2 dy_n)/2 + dy_n])

         with the eigenvalues dx tan dx = Bi_e,x = h_ex c / k (dx = lam_x c), dy tan dy = h_ey d / k, beta_mn = sqrt(lam_x^2 + lam_y^2) and
         phi_mn = (beta + (h/k) tanh(beta t)) / ((h/k) + beta tanh(beta t)) (the form of eq. 24 in dimensional units). R_t is the mean rise of the source over the total
         power. `fin_limit` is the same problem as a thin sheet (the through-thickness profile dropped): the series of robin_basis with S = k t, a bottom film h,
         the edge parameter beta_e = h_e / k, which is what the Analytic model solves.
"""

import os
import sys

import numpy as np
from scipy.optimize import brentq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from robin_basis import Basis   # noqa: E402


def eigen_even(Bi, n):
    """!
    @brief First n roots of delta tan delta = Bi (delta = lam * half length).
    @param Bi Edge Biot number h_e c / k.
    @param n Number of roots.
    @return Array (n,).
    """
    return np.array([brentq(lambda d: d * np.tan(d) - Bi, k * np.pi + 1e-14, k * np.pi + 0.5 * np.pi - 1e-12, xtol=1e-14) for k in range(n)])


def eq21(a, b, c, d, t, k, h, hex_, hey, n=400):
    """!
    @brief Total resistance of the edge-cooled rectangular flux channel, equation 21.
    @param a Half width of the source in x (m).
    @param b Half width of the source in y (m).
    @param c Half width of the channel in x (m).
    @param d Half width of the channel in y (m).
    @param t Thickness (m).
    @param k Conductivity (W/mK).
    @param h Film coefficient of the bottom face (W/m2K).
    @param hex_ Edge coefficient on x = c (W/m2K).
    @param hey Edge coefficient on y = d (W/m2K).
    @param n Terms per direction.
    @return float R_t in K/W.
    """
    dx = eigen_even(hex_ * c / k, n)
    dy = eigen_even(hey * d / k, n)
    lx, ly = dx / c, dy / d
    beta = np.sqrt(lx[:, None] ** 2 + ly[None, :] ** 2)
    hk = h / k
    phi = (beta + hk * np.tanh(beta * t)) / (hk + beta * np.tanh(beta * t))
    num = (np.sin(dx * a / c) ** 2)[:, None] * (np.sin(dy * b / d) ** 2)[None, :] * phi
    den = dx[:, None] * dy[None, :] * beta * ((np.sin(2 * dx) / 2 + dx)[:, None]) * ((np.sin(2 * dy) / 2 + dy)[None, :])
    return float(c * d / (k * a ** 2 * b ** 2) * (num / den).sum())


def fin_limit(a, b, c, d, t, k, h, hex_, hey, n=400):
    """!
    @brief The same problem as a thin sheet (what the Analytic model solves with the Robin basis), mean rise of the source over the power.
    @param a Half width of the source in x (m).
    @param b Half width of the source in y (m).
    @param c Half width of the channel in x (m).
    @param d Half width of the channel in y (m).
    @param t Thickness (m).
    @param k Conductivity (W/mK).
    @param h Film coefficient of the bottom face (W/m2K).
    @param hex_ Edge coefficient on x = c (W/m2K).
    @param hey Edge coefficient on y = d (W/m2K).
    @param n Modes per direction of the full board (2n in the symmetric half).
    @return float R in K/W.
    """
    W, H = 2 * c, 2 * d
    bx, by = Basis(W, hex_ / k, 2 * n), Basis(H, hey / k, 2 * n)
    S = k * t
    eig2 = bx.eig2[:, None] + by.eig2[None, :]
    # unit power over the source [c-a, c+a] x [d-b, d+b]
    px, py = bx.project(c - a, c + a), by.project(d - b, d + b)
    q = np.outer(px / bx.norm, py / by.norm) / (4 * a * b)
    amp = q / (S * eig2 + h)
    # mean over the source of theta = sum amp * phi_m phi_n -> integrate the eigenfunctions over the source
    return float((amp * np.outer(px, py)).sum() / (4 * a * b))
