#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file stackimpedance.py
@brief Closed-form thermal impedance of the layered stack under a part, and the swing and waveform of a square wave from it (the ripple of a fast power wave).

@details The layered models keep one node per copper layer, with half of the next laminate slab on it, so a wave whose shortest stretch is below a few seconds heats a column that is
too thick and the node swing is 2 to 12 times too small (docs/theory.md 10.5, docs/validation.md 37). This module computes the swing of such a wave in closed form instead, from
the real thicknesses of the stack. Two ingredients (both standard methods; the first is the transfer-matrix (quadrupole) method of layered slabs, the second the fin equation of a
sheet with a vertical admittance, solved for a disc source with Bessel functions as in Carslaw and Jaeger):

1. Y(w), the admittance per unit area seen from the copper of the heater's layer: the stack above it, the stack below it and the capacity of the copper itself, in parallel. For a
   layer of thickness d, conductivity k and volumetric heat capacity c, with gamma = sqrt(j w c / k) and the admittance Y_load of what lies beyond it, the admittance at its near
   face is Y = k gamma (Y_load + k gamma tanh(gamma d)) / (k gamma + Y_load tanh(gamma d)) (the tanh form of the transfer matrix: no overflow in a thick laminate). The
   outermost faces end in their convection coefficients.
2. The copper of the heater's layer is a sheet of conductance S = f k_cu t_cu over that admittance: S laplacian(theta) - Y theta = -q(r). For a uniform flux q0 on a disc of radius
   a (the part, taken as the disc of the same area) and m^2 = Y / S, the rise at the centre is (q0 / Y)(1 - m a K1(m a)), complex arguments.

The temperature of a square wave of swing dP is the sum of the harmonics dP Z(k w0) c_k e^(j k w0 t), c_k the Fourier coefficient of a unit pulse train; the sum has no mean.
Where it does not apply (see column_for_heater): no copper under the part, a metal block on the board; vias, heatsinks, the board edge and the other heaters are not in it (it
overstates with vias, planes and elongated parts, understates a part close to a board edge at waves slower than 1 Hz).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
from scipy.special import kv

from . import blocks, copper
from .geometry import points_in_polygon, polygon_area

# Harmonics are computed on a grid of this many samples per period (harmonics up to half of it); 16384 is the number the reference runs used and costs about 2 ms
N_SAMPLES = 16384

# The impedance applies where the copper under the part is at least this fraction (fill); below it the part is on bare laminate (the face term of laminate.face_terms is the model there)
MIN_FILL = 0.9

# Samples per side of the lattice that measures the copper fill under the part
FILL_LATTICE = 16


def half_admittance(layers: List[Tuple[float, float, float]], w: np.ndarray, h_end: float) -> np.ndarray:
    """!
    @brief Admittance per unit area at the first face of a list of layers that ends in a convective face.
    @param layers List of (thickness in m, conductivity in W/mK, volumetric heat capacity in J/m3K), from the face of the heater's layer outwards.
    @param w Angular frequencies in rad/s (array).
    @param h_end Convection coefficient of the far face in W/m2K.
    @return Complex array like w, in W/m2K.
    """
    w = np.asarray(w, dtype=float)
    y = np.full(w.shape, h_end, dtype=complex)
    # From the far face towards the heater: each layer transforms the admittance of what lies beyond it
    for d, k, rc in reversed(layers):
        gam = np.sqrt(1j * w * rc / k)
        yc = k * gam
        th = np.tanh(gam * d)
        y = yc * (y + yc * th) / (yc + y * th)
    return y


@dataclass
class HeaterColumn:
    """!
    @brief The layered column under one part, in the form the impedance needs (SI units).
    """
    radius: float                               # Radius of the disc of the same area as the part (m)
    sheet: float                                # Conductance of the heater layer's copper, f k_cu t_cu (W/K)
    capacity: float                             # Heat capacity per unit area of the heater layer's slab (J/m2K)
    up: List[Tuple[float, float, float]] = field(default_factory=list)      # Layers above (toward layer 1): (d m, k W/mK, rho c J/m3K), nearest first
    down: List[Tuple[float, float, float]] = field(default_factory=list)    # Layers below, nearest first
    h_top: float = 10.0                         # Convection coefficient of the top face (W/m2K)
    h_bottom: float = 10.0                      # Convection coefficient of the bottom face (W/m2K)
    layer: int = 0                              # Heater layer, 0-based

    def admittance(self, w):
        """!
        @brief Admittance per unit area seen from the heater's copper: above, below and its own capacity in parallel.
        @param w Angular frequencies in rad/s (array).
        @return Complex array in W/m2K.
        """
        w = np.asarray(w, dtype=float)
        return half_admittance(self.up, w, self.h_top) + half_admittance(self.down, w, self.h_bottom) + 1j * w * self.capacity

    def impedance(self, w):
        """!
        @brief Complex thermal impedance at the centre of the part for a power at angular frequency w.
        @param w Angular frequencies in rad/s (array, above 0).
        @return Complex array in K/W.
        """
        y = self.admittance(w)
        ma = self.radius * np.sqrt(y / self.sheet)
        return (1.0 - ma * kv(1, ma)) / (np.pi * self.radius ** 2 * y)

    def _signal(self, period: float, duty: float, n: int):
        """!
        @brief The periodic response to a unit square wave of power, on a grid of n samples of one period.
        @param period Period in s.
        @param duty On fraction (0 to 1).
        @param n Samples per period.
        @return Real array of n values in K per W of swing, zero mean.
        """
        k = np.arange(1, n // 2)
        z = self.impedance(k * 2.0 * np.pi / period)
        c = (1.0 - np.exp(-2j * np.pi * k * duty)) / (2j * np.pi * k)       # Fourier coefficient k of a unit pulse train
        # Lanczos sigma factor: without it a wave slower than the board's response (impedance flat over all the harmonics) shows the Gibbs overshoot of the cut series, 9 % of the
        # swing at 10^6 s; where the impedance falls with frequency (every wave of interest) it changes the swing by less than 0.01 %
        c = c * np.sinc(k / (n // 2))
        spec = np.zeros(n, dtype=complex)
        spec[1:n // 2] = z * c
        spec[-(n // 2 - 1):] = np.conj((z * c)[::-1])
        return np.fft.ifft(spec).real * n

    def swing(self, period: float, duty: float, n: int = N_SAMPLES) -> float:
        """!
        @brief Peak-to-peak temperature of a unit square wave of power in the periodic steady state.
        @param period Period in s.
        @param duty On fraction (0 to 1 exclusive).
        @param n Samples per period (harmonics up to n / 2).
        @return Swing in K per W of swing of the power (p_on - p_off).
        """
        t = self._signal(period, duty, n)
        return float(t.max() - t.min())

    def ripple(self, period: float, duty: float, n: int = N_SAMPLES) -> "Ripple":
        """!
        @brief The zero-mean waveform of a unit square wave of power, with its extremes.
        @param period Period in s.
        @param duty On fraction (0 to 1 exclusive).
        @param n Samples per period.
        @return Ripple (per watt of swing of the power).
        """
        return Ripple(period, duty, self._signal(period, duty, n))


@dataclass
class Ripple:
    """!
    @brief The periodic, zero-mean temperature wave of a heater from a unit swing of its power (K per W); scale by the swing of the power.
    """
    period: float                               # Period in s
    duty: float                                 # On fraction
    samples: np.ndarray                         # One period, phase i / n at sample i, K per W of swing, zero mean

    @property
    def plus(self) -> float:
        """!
        @brief Highest value of the wave above its mean.
        @return K per W of swing.
        """
        return float(self.samples.max())

    @property
    def minus(self) -> float:
        """!
        @brief Lowest value of the wave below its mean (negative).
        @return K per W of swing.
        """
        return float(self.samples.min())

    def at(self, t) -> np.ndarray:
        """!
        @brief The wave at times t (the wave starts with the on-state at t = 0 of every period, as the power does).
        @param t Times in s (array).
        @return Array like t in K per W of swing, linearly interpolated between samples.
        """
        t = np.asarray(t, dtype=float)
        n = len(self.samples)
        pos = (t / self.period % 1.0) * n
        i = np.floor(pos).astype(int) % n
        frac = pos - np.floor(pos)
        return self.samples[i] * (1.0 - frac) + self.samples[(i + 1) % n] * frac

    def mean_over(self, t0, t1) -> np.ndarray:
        """!
        @brief Mean of the wave over the intervals [t0, t1], as the power of a step is the mean of the power wave over it.
        @details A run that samples a fast wave at steps longer than its period would alias it into a constant (the value at one phase); the mean over the step does not: it tends to
                 the wave when the step is short and to zero (the mean of the wave) when the step is long. Computed from the running integral of the sampled wave (trapezoids, the
                 residual drift of a period removed), interpolated.
        @param t0 Start times in s (array).
        @param t1 End times in s (array, above t0).
        @return Array like t0 in K per W of swing.
        """
        n = len(self.samples)
        s = np.append(self.samples, self.samples[0])
        cum = np.concatenate([[0.0], np.cumsum(0.5 * (s[:-1] + s[1:]))]) * (self.period / n)
        drift = cum[-1]
        phases = np.arange(n + 1) / n

        def integral(t):
            t = np.asarray(t, dtype=float)
            cycles = np.floor(t / self.period)
            ph = t / self.period - cycles
            return cycles * drift + np.interp(ph, phases, cum)

        d = np.maximum(np.asarray(t1, dtype=float) - np.asarray(t0, dtype=float), 1e-300)
        return (integral(t1) - integral(t0)) / d - drift / self.period


def _layer_fill(problem, polygon, layer: int) -> float:
    """!
    @brief Mean copper fill of one layer under a polygon, from a lattice of points inside it.
    @param problem A Problem.
    @param polygon Vertices (n, 2) in m.
    @param layer 0-based layer.
    @return Fill from 0 to 1 (the union of the zones, a hatched zone at its fill; an imported layer from its mask).
    """
    poly = np.asarray(polygon, dtype=float)
    x0, y0 = poly.min(axis=0)
    x1, y1 = poly.max(axis=0)
    gx, gy = np.meshgrid(x0 + (np.arange(FILL_LATTICE) + 0.5) * (x1 - x0) / FILL_LATTICE, y0 + (np.arange(FILL_LATTICE) + 0.5) * (y1 - y0) / FILL_LATTICE)
    inside = points_in_polygon(gx, gy, poly)
    if not inside.any():
        return 0.0
    px, py = gx[inside], gy[inside]
    if copper.has_imported(problem):
        # An imported layer is a mask: read it on a raster fine enough for the part (at most about 400 cells along the longer side of the board: the live check calls this)
        b = problem.board
        cell = max(min(x1 - x0, y1 - y0) / 8.0, max(b.width, b.height) / 400.0)
        nx, ny = max(int(round(b.width / cell)), 1), max(int(round(b.height / cell)), 1)
        fill = copper.problem_fill(problem, nx, ny, b.width / nx, b.height / ny, samples=2)[layer]
        j = np.clip((px / (b.width / nx)).astype(int), 0, nx - 1)
        i = np.clip((py / (b.height / ny)).astype(int), 0, ny - 1)
        return float(fill[i, j].mean())
    f = np.zeros(px.shape)
    for z in problem.zones:
        if z.layer == layer:
            f = np.maximum(f, np.where(points_in_polygon(px, py, z.polygon), z.fill, 0.0))
    return float(f.mean())


def column_for_heater(problem, index: int) -> Tuple[Optional[HeaterColumn], str]:
    """!
    @brief The layered column under a heater, or the reason why the closed form does not apply.
    @details The stack is read as the FVM reads it: the copper thicknesses, the gaps one by one with their conductivities and capacities (advanced stack-up) or equal (simple), the
             laminate under the copper of a one-layer board. A copper layer other than the heater's enters as the mixture of copper and laminate at the fill measured under the part. The
             heater's own layer needs a fill of at least MIN_FILL. Vias, heatsinks, the board edge, a top path and the other heaters are not in the column.
    @param problem A Problem (h_top and h_bottom as typed or the effective values of a computed-h run).
    @param index Heater index.
    @return Tuple (HeaterColumn or None, status): status is "ok", "bare" (copper under the part below MIN_FILL), "block" (a metal block on the board) or "empty" (a part with no area).
    """
    if blocks.has_blocks(problem):
        return None, "block"
    b = problem.board
    h = problem.heaters[index]
    area = polygon_area(h.polygon)
    if area <= 0.0:
        return None, "empty"
    fill = [_layer_fill(problem, h.polygon, l) for l in range(b.layers)]
    f0 = fill[h.layer]
    if f0 < MIN_FILL:
        return None, "bare"
    m = b.materials
    t_cu = np.asarray(b.copper_thickness, dtype=float)
    rc_cu = m.rho_copper * m.cp_copper
    gap_d = b.gap_thicknesses()
    gap_k, _, gap_rc = b.gap_properties()
    if b.layers == 1:
        gap_d, gap_k, gap_rc = np.array([b.thickness - t_cu[0]]), np.array([m.k_fr4_through]), np.array([m.rho_fr4 * m.cp_fr4])
    k_lam0, rc_lam0 = m.k_fr4_through, m.rho_fr4 * m.cp_fr4

    def copper_slab(l):
        # A copper layer with fill f over the part: copper and laminate side by side, in parallel through the thickness
        f = fill[l]
        return (float(t_cu[l]), f * m.k_copper + (1.0 - f) * k_lam0, f * rc_cu + (1.0 - f) * rc_lam0)

    def gap(j):
        return (float(gap_d[j]), float(gap_k[j]), float(gap_rc[j]))

    L, l0 = b.layers, h.layer
    up: List[Tuple[float, float, float]] = []
    for l in range(l0 - 1, -1, -1):                                         # Above: the gap, then the copper, up to the top copper
        up += [gap(l), copper_slab(l)]
    down: List[Tuple[float, float, float]] = []
    for l in range(l0 + 1, L):                                              # Below: the gap, then the copper, down to the bottom copper
        down += [gap(l - 1), copper_slab(l)]
    if L == 1:
        down = [gap(0)]                                                     # A one-layer board: the laminate under the copper
    col = HeaterColumn(radius=float(np.sqrt(area / np.pi)), sheet=f0 * m.k_copper * float(t_cu[l0]),
                       capacity=float(t_cu[l0]) * (f0 * rc_cu + (1.0 - f0) * rc_lam0), up=up, down=down,
                       h_top=float(b.h_top), h_bottom=float(b.h_bottom), layer=l0)
    return col, "ok"
