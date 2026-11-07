#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file impedance.py
@brief Closed-form thermal impedance of the top copper sheet of a board under a disc source at angular frequency w, and the peak-to-peak swing of a square wave from it (research/fast-wave-oscillation README 5, estimator E3).

@details Imports nothing from pcbthermal. Two ingredients, both own derivations (the layered-slab quadrupole is the standard transfer-matrix method; the disc on a sheet with a vertical
admittance is the fin equation with Bessel functions, the form of Carslaw and Jaeger's disc sources, status M and verified here against the numerical reference):

1. Y(w), the admittance per unit area seen from the top face of the top copper, from the quadrupole (transfer matrices) of every layer below it with the convection of the bottom face
   at the end, plus the convection of the top face in parallel. Each layer of thickness d, conductivity k, diffusivity a, gamma = sqrt(j w / a):
   [T0; q0] = [[cosh(gamma d), sinh(gamma d) / (k gamma)], [k gamma sinh(gamma d), cosh(gamma d)]] [T1; q1], evaluated as the equivalent admittance recursion with tanh.
2. The sheet of conductance S = k_cu t_cu carries the lateral flow: S laplacian(theta) - Y theta = -q(r). For a uniform flux q0 on the disc r < a, with m^2 = Y / S,
   centre rise q0 / Y (1 - m a K1(m a)) and disc-mean rise q0 / Y (1 - 2 I1(m a) K1(m a)), complex arguments.
The swing of a square wave is the peak-to-peak of the sum of the harmonics Z(k w0) c_k.
"""

import numpy as np
from scipy.special import iv, kv

import axisym_stack as A


def layer_admittance(stack: A.Stack, w: np.ndarray, h_top: float, h_bottom: float) -> np.ndarray:
    """!
    @brief Admittance per unit area Y(w) = q0 / T0 at the top face of the stack (top copper included), W/m2K, complex.
    @param stack Stack (equal gaps between the copper layers, outer copper on the faces; one layer: copper on a laminate).
    @param w Angular frequencies in rad/s (array).
    @param h_top Top convection coefficient (W/m2K).
    @param h_bottom Bottom convection coefficient (W/m2K).
    @return Complex array like w.
    """
    L = stack.layers
    layers = []                                    # (d, k, rho_cp) top down
    if L == 1:
        layers = [(stack.t_cu, stack.k_cu, stack.rho_cp_cu), (stack.thickness - stack.t_cu, stack.kz, stack.rho_cp_lam)]
    else:
        g = (stack.thickness - L * stack.t_cu) / (L - 1)
        for i in range(L):
            layers.append((stack.t_cu, stack.k_cu, stack.rho_cp_cu))
            if i < L - 1:
                layers.append((g, stack.kz, stack.rho_cp_lam))
    w = np.asarray(w, dtype=float)
    # Admittance recursion from the bottom face upward: a layer of effusivity-like admittance Yc = k gamma loaded by Y_load shows
    # Y = Yc (Y_load + Yc tanh(gamma d)) / (Yc + Y_load tanh(gamma d)) (the transfer matrix in the stable tanh form: no cosh overflow in a thick laminate)
    Y = np.full_like(w, h_bottom, dtype=complex)
    for d, k, rcp in reversed(layers):
        gam = np.sqrt(1j * w * rcp / k)
        yc = k * gam
        th = np.tanh(gam * d)
        Y = yc * (Y + yc * th) / (yc + Y * th)
    return Y + h_top


def impedance(stack: A.Stack, w: np.ndarray, a: float, h_top: float, h_bottom: float, readout: str = "center", sheet: str = "top") -> np.ndarray:
    """!
    @brief Complex thermal impedance in K/W of the top copper under a disc source of radius a.
    @param stack Stack.
    @param w Angular frequencies (array, rad/s, > 0).
    @param a Disc radius in m.
    @param h_top Top coefficient.
    @param h_bottom Bottom coefficient.
    @param readout "center" or "mean" (over the disc).
    @param sheet "top": lateral conductance of the top copper only; "all": of every copper layer.
    @return Complex array like w.
    """
    Y = layer_admittance(stack, w, h_top, h_bottom)
    S = stack.k_cu * stack.t_cu * (stack.layers if sheet == "all" else 1)
    ma = a * np.sqrt(Y / S)
    if readout == "center":
        f = 1.0 - ma * kv(1, ma)
    else:
        f = 1.0 - 2.0 * iv(1, ma) * kv(1, ma)
    return f / (np.pi * a * a * Y)


def square_swing(stack: A.Stack, period: float, duty: float, a: float, h_top: float, h_bottom: float, readout: str = "center", sheet: str = "top",
                 n_samples: int = 16384) -> float:
    """!
    @brief Peak-to-peak rise per watt of on-power of a unit square wave (periodic steady state) from the impedance.
    @param stack Stack.
    @param period Period in s.
    @param duty On fraction.
    @param a Source radius in m.
    @param h_top Top coefficient.
    @param h_bottom Bottom coefficient.
    @param readout "center" or "mean".
    @param sheet "top" or "all".
    @param n_samples Samples per period (harmonics up to n_samples / 2).
    @return Swing in K/W.
    """
    k = np.arange(1, n_samples // 2)
    w0 = 2.0 * np.pi / period
    Z = impedance(stack, k * w0, a, h_top, h_bottom, readout, sheet)
    c = (1.0 - np.exp(-2j * np.pi * k * duty)) / (2j * np.pi * k)             # Fourier coefficient of a unit pulse train
    spec = np.zeros(n_samples, dtype=complex)
    spec[1:n_samples // 2] = Z * c
    spec[-(n_samples // 2 - 1):] = np.conj((Z * c)[::-1])
    t = np.fft.ifft(spec).real * n_samples
    return float(t.max() - t.min())
