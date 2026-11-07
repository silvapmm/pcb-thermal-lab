#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file stackimpedance.py
@brief Closed-form thermal impedance of the layered stack under a part, and the swing and waveform of a repeating power profile from it (the ripple of a fast power wave).

@details **Why.** The layered models (FVM, FDM, and the Lumped and Analytic tuned on them) keep one temperature per copper layer, with half of each adjacent laminate gap on it
(about 0.77 mm of FR-4 on a 1.6 mm two-layer board, twelve times the capacity of 35 um of copper). A wave whose shortest stretch is below a few seconds heats only the copper
and a thin skin of laminate, so the node swing is 2 to 3 times too small at 1 to 3 Hz and 8 to 12 times from 50 Hz to 1 kHz (docs/theory.md 10.5, docs/validation.md 37.1).
This module computes the swing from the real stack instead (docs/theory.md eqs. 10.2 to 10.5):

1. **The admittance of the column** Y(w) (W/m2K, eq. 10.2): what lies above the heater's plane and what lies below it, in parallel, each a list of slabs ending in the
   convection coefficient of its outer face. The heater's own copper is a slab of the column (on an outer layer all of it lies between the part and the laminate, on an inner
   layer half on each side); a lumped copper capacity read 0.90 of the 3D reference at 3 kHz with a 10 % duty, where a stretch of 33 us does not heat 35 um of copper
   uniformly. A slab of thickness d, conductivity k and volumetric heat capacity c turns the admittance Y_load beyond it into (eq. 10.3)
   Y = k g (Y_load + k g tanh(g d)) / (k g + Y_load tanh(g d)), g = sqrt(j w c / k): the transfer matrix (quadrupole) of a slab written with tanh, which stays finite when g d
   is large (cosh and sinh would overflow in a thick laminate at kilohertz). Both sides are always used ("two-sided"): a heater on an inner or bottom layer sees the stack
   on both faces (the one-sided top form read 1.07 to 1.57 of the reference on an inner layer).
2. **The disc on the sheet** (eq. 10.4): the copper of the heater's layer spreads the heat sideways, a sheet of conductance S = f k_cu t_cu (W/K) over the admittance:
   S laplacian(theta) - Y theta = -q(r). A uniform flux on the disc of the part's area (radius a) gives at its centre Z = (1 - m a K1(m a)) / (pi a^2 Y), m^2 = Y / S, with
   complex arguments (the fin equation of a sheet with a vertical loss, solved for a disc with modified Bessel functions; the form of [CarslawJaeger], status M).
3. **The harmonic sum** (eq. 10.5): a repeating power with Fourier coefficients c_k (W) gives theta(t) = 2 Re sum_k sigma_k Z(k w0) c_k e^(j k w0 t), 8191 harmonics, one
   inverse FFT (about 2 ms). The mean (k = 0) is left out on purpose: it is the steady rise of the average power, which the board run holds with the real board. sigma_k is
   the Lanczos factor sinc(k / N): a wave much slower than the board has a flat impedance over all its harmonics, and a cut Fourier series of a jump overshoots by the
   Wilbraham-Gibbs 9 %; the factor removes that and changes a fast wave by less than 0.05 %.

**Where it applies** (column_for_heater): a part with copper under it on its layer (fill at least MIN_FILL = 0.9; below it the part is on bare laminate, where the face term
of laminate.face_terms is the model and checks.check_fast_wave warns), no metal block on the board.

@note What the column does not hold, and the measured effect against the 3D reference (docs/validation.md 37.2): vias (the closed form reads above the truth: 1.07 to 1.59 at
      0.1 to 1 Hz with 4 to 36 vias under a 10 mm part on two layers, up to 2.04 on four; within 2 % from 100 Hz: the safe side), planes of the other layers other than as slabs of the column and elongated parts
      (up to 1.37, safe side), the board edge (0.61 at 0.1 Hz for a part within its radius of two sides: warned), the other heaters (their in-phase waves add at a neighbour:
      estimated 17 % of the swing at 0.1 Hz with a 1 mm gap, 5 % at 1 Hz, under 0.4 % from 10 Hz; not added).
@see docs/theory.md 10.5, docs/validation.md 37, research/fast-wave-oscillation (README 5 and 8, INTEGRATION.md A, B, D, W2).
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
    @brief Admittance per unit area at the first face of a list of layers that ends in a convective face (docs/theory.md eq. 10.3, applied slab by slab).
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
    capacity: float = 0.0                       # Lumped heat capacity per unit area at the heater's plane (J/m2K); column_for_heater puts the heater's copper in up/down as a slab and leaves 0
    up: List[Tuple[float, float, float]] = field(default_factory=list)      # Layers above (toward layer 1): (d m, k W/mK, rho c J/m3K), nearest first
    down: List[Tuple[float, float, float]] = field(default_factory=list)    # Layers below, nearest first
    h_top: float = 10.0                         # Convection coefficient of the top face (W/m2K)
    h_bottom: float = 10.0                      # Convection coefficient of the bottom face (W/m2K)
    layer: int = 0                              # Heater layer, 0-based

    def admittance(self, w):
        """!
        @brief Admittance per unit area seen from the heater's plane: above, below and the lumped capacity (0 from column_for_heater) in parallel.
        @param w Angular frequencies in rad/s (array).
        @return Complex array in W/m2K.
        """
        w = np.asarray(w, dtype=float)
        return half_admittance(self.up, w, self.h_top) + half_admittance(self.down, w, self.h_bottom) + 1j * w * self.capacity

    def impedance(self, w):
        """!
        @brief Complex thermal impedance at the centre of the part for a power at angular frequency w (docs/theory.md eq. 10.4).
        @details 1 / (pi a^2 Y) is the one-dimensional column under the disc; the bracket 1 - m a K1(m a) is the share that stays under the disc after the sideways spread in the
                 heater's copper (it tends to 1 for a large disc or a fast wave, where m a is large, and to the spread of an infinite sheet for a slow one).
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
        c = (1.0 - np.exp(-2j * np.pi * k * duty)) / (2j * np.pi * k)       # Fourier coefficient k of a unit pulse train (on for the fraction duty from t = 0), docs/theory.md (10.5)
        return self._from_coefficients(period, c, n)

    def _from_coefficients(self, period: float, c: np.ndarray, n: int) -> np.ndarray:
        """!
        @brief The zero-mean periodic temperature of a power whose Fourier coefficients are c (harmonics 1 to n / 2 - 1), on n samples of one period.
        @details theta(t) = 2 Re sum_k sigma_k Z(k w0) c_k e^(j k w0 t) (docs/theory.md (10.5)), evaluated by one inverse FFT. The mean (k = 0) is left out: it is the steady rise of
                 the average power, which the board run holds with the real board (edges, vias, neighbours); the closed form only adds the wave about it.
        @param period Period in s.
        @param c Complex coefficients of harmonics 1 .. n / 2 - 1, in W (or per W of a unit wave).
        @param n Samples per period.
        @return Real array of n values in K (per the unit of c), zero mean.
        """
        k = np.arange(1, n // 2)
        z = self.impedance(k * 2.0 * np.pi / period)
        # Lanczos sigma factor: without it a wave slower than the board's response (impedance flat over all the harmonics) shows the Gibbs overshoot of the cut series, 9 % of the
        # swing at 10^6 s (the Wilbraham-Gibbs constant of a jump, 0.0895 of it on each side); where the impedance falls with frequency (every wave of interest) the high harmonics
        # carry little and the factor changes the swing by less than 0.05 % (measured from 0.1 Hz to 10 kHz at 10 and 50 % duty)
        zc = z * c * np.sinc(k / (n // 2))
        spec = np.zeros(n, dtype=complex)
        spec[1:n // 2] = zc
        spec[-(n // 2 - 1):] = np.conj(zc[::-1])
        return np.fft.ifft(spec).real * n

    def profile_ripple(self, profile, n: int = N_SAMPLES) -> "Ripple":
        """!
        @brief The zero-mean temperature wave of any repeating power profile (square wave or table), in K (not per watt).
        @details A square wave uses its exact pulse coefficients times p_on - p_off (identical to ripple() scaled); a table uses profile_coefficients(). The table's on-state at
                 t = 0 of every period is its first row, as in the board run.
        @param profile SquareWave or repeating TableProfile.
        @param n Samples per period.
        @return Ripple in K (scale 1).
        """
        if getattr(profile, "kind", "") == "square":
            return Ripple(profile.period, profile.duty, (profile.p_on - profile.p_off) * self._signal(profile.period, profile.duty, n))
        return Ripple(profile.period, float("nan"), self._from_coefficients(profile.period, profile_coefficients(profile, n), n))

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


# Above this many stretches x harmonics a table's coefficients come from the FFT of its exact step means instead of the exact sum over the stretches (memory of the outer product)
EXACT_COEFFICIENT_LIMIT = 4_000_000


def profile_coefficients(profile, n: int = N_SAMPLES) -> np.ndarray:
    """!
    @brief Fourier coefficients (harmonics 1 to n / 2 - 1) of a repeating power table, in W.
    @details c_k = (1 / T) integral_0^T P(t) e^(-j k w0 t) dt; for constant stretches P_i on [t_i, t_(i+1)] that is
             sum_i P_i (e^(-j k w0 t_i) - e^(-j k w0 t_(i+1))) / (j 2 pi k), exact. A table with very many stretches is sampled instead: the exact mean power of each of the n bins
             (TableProfile.mean_power) and an FFT; a bin of constant power on [b, b + 1] T / n has the coefficient FFT_k / n times sinc(k / n) e^(-j pi k / n) (exact for the binned
             table, which differs from the table only inside the bins that hold a stretch edge).
    @param profile TableProfile (repeat).
    @param n Samples per period.
    @return Complex array of n / 2 - 1 values in W.
    """
    k = np.arange(1, n // 2)
    T = float(profile.period)
    t = np.asarray(profile.times, dtype=float)
    p = np.asarray(profile.powers, dtype=float)
    if len(p) * len(k) <= EXACT_COEFFICIENT_LIMIT:
        e = np.exp(-2j * np.pi * np.outer(t, k) / T)                    # (stretch edges, harmonics)
        return (p[:, None] * (e[:-1] - e[1:])).sum(axis=0) / (2j * np.pi * k)
    edges = np.arange(n + 1) * (T / n)
    bins = profile.mean_power(edges[:-1], edges[1:])
    return np.fft.fft(bins)[1:n // 2] / n * np.sinc(k / n) * np.exp(-1j * np.pi * k / n)


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
             heater's own layer needs a fill of at least MIN_FILL and is a slab of the column (outer layer: all of it between the part and the laminate; inner layer: half above, half below). Vias, heatsinks, the board edge, a top path and the other heaters are not in the column.
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
    # The heater's own copper is a slab of the column, not a lumped capacity: a wave with a stretch of tens of microseconds (a few kHz at 10 % duty) does not heat the 35 um
    # isothermally, and the lumped form read 0.90 of the reference there (research/fast-wave-oscillation out/review_sample.json: 3 kHz, duty 10 and 90 %). On an outer layer the
    # part sits on the outer face of the copper, so the whole slab lies between it and the laminate; on an inner layer the source is taken at the middle of the copper (half each side)
    cu = copper_slab(l0)
    if l0 == 0:
        down = [cu] + down
    elif l0 == L - 1:
        up = [cu] + up
    else:
        half = (0.5 * cu[0], cu[1], cu[2])
        up, down = [half] + up, [half] + down
    col = HeaterColumn(radius=float(np.sqrt(area / np.pi)), sheet=f0 * m.k_copper * float(t_cu[l0]),
                       capacity=0.0, up=up, down=down,
                       h_top=float(b.h_top), h_bottom=float(b.h_bottom), layer=l0)
    return col, "ok"
