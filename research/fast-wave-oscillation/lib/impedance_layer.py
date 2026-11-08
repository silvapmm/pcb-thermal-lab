#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file impedance_layer.py
@brief The reviewer's extension of the estimator E3 to a heater on any copper layer: the admittance of the stack seen from that layer is the sum of the admittance
       looking up (to the top face) and looking down (to the bottom face); the layer's copper is the sheet (research/fast-wave-oscillation README 9.4).

@details Imports nothing from pcbthermal; uses only the recursion of the author's impedance.layer_admittance (the tanh form of the layer transfer matrix) applied to the
two halves of the stack. For the top layer it is the author's E3 exactly (the upward half is the convection of the top face only, through no material).
"""

import numpy as np
from scipy.special import kv

import axisym_stack as A


def _admittance(layers, w, h_end):
    """!
    @brief Admittance per unit area at the first face of a list of layers ending in a convective face.
    @param layers List of (thickness m, k W/mK, rho c J/m3K), from the face of the heater layer outwards.
    @param w Angular frequencies (rad/s).
    @param h_end Coefficient of the far face (W/m2K).
    @return Complex array like w.
    """
    Y = np.full(np.shape(w), h_end, dtype=complex)
    for d, k, rc in reversed(layers):
        gam = np.sqrt(1j * np.asarray(w) * rc / k)
        yc = k * gam
        th = np.tanh(gam * d)
        Y = yc * (Y + yc * th) / (yc + Y * th)
    return Y


def impedance_on_layer(stack: A.Stack, layer: int, w, a, h_top, h_bottom):
    """!
    @brief Centre impedance (K/W, complex) of a disc source of radius a on copper layer `layer` (0 = top) of an equal-gap stack.
    @param stack Stack.
    @param layer Heater layer, 0-based.
    @param w Angular frequencies (rad/s).
    @param a Disc radius (m).
    @param h_top Top coefficient.
    @param h_bottom Bottom coefficient.
    @return Complex array like w.
    """
    L = stack.layers
    g = (stack.thickness - L * stack.t_cu) / (L - 1) if L > 1 else stack.thickness - stack.t_cu
    cu = (stack.t_cu, stack.k_cu, stack.rho_cp_cu)
    lam = (g, stack.kz, stack.rho_cp_lam)
    up, down = [], []
    for i in range(layer - 1, -1, -1):           # Above the heater layer: gap, copper, ..., top copper
        up += [lam, cu]
    for i in range(layer + 1, L):                # Below: gap, copper, ..., bottom copper
        down += [lam, cu]
    if L == 1:
        down = [lam]
    # The heater layer's own copper is the sheet; its capacity per area joins the admittance as j w rho c t
    w = np.asarray(w, dtype=float)
    Y = _admittance(up, w, h_top) + _admittance(down, w, h_bottom) + 1j * w * stack.rho_cp_cu * stack.t_cu
    S = stack.k_cu * stack.t_cu
    ma = a * np.sqrt(Y / S)
    return (1.0 - ma * kv(1, ma)) / (np.pi * a * a * Y)


def square_swing_on_layer(stack: A.Stack, layer: int, period, duty, a, h_top, h_bottom, n_samples=16384):
    """!
    @brief Peak-to-peak rise per watt of on-power of a square wave of a heater on any layer (as impedance.square_swing).
    @param stack Stack.
    @param layer Heater layer, 0-based.
    @param period Period (s).
    @param duty Duty.
    @param a Disc radius (m).
    @param h_top Top coefficient.
    @param h_bottom Bottom coefficient.
    @param n_samples Samples per period.
    @return K/W.
    """
    k = np.arange(1, n_samples // 2)
    Z = impedance_on_layer(stack, layer, k * 2.0 * np.pi / period, a, h_top, h_bottom)
    c = (1.0 - np.exp(-2j * np.pi * k * duty)) / (2j * np.pi * k)
    spec = np.zeros(n_samples, dtype=complex)
    spec[1:n_samples // 2] = Z * c
    spec[-(n_samples // 2 - 1):] = np.conj((Z * c)[::-1])
    t = np.fft.ifft(spec).real * n_samples
    return float(t.max() - t.min())
