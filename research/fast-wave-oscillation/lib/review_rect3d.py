#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file review_rect3d.py
@brief The reviewer's independent reference for research/fast-wave-oscillation: 3D finite volumes of the RECTANGULAR board (copper layers and laminate resolved through the
       thickness, the real rectangular part), solved in the frequency domain, and the periodic steady state of a square wave from the harmonic sum.

@details Imports nothing from pcbthermal and nothing from the author's lib/ (axisym_stack.py, impedance.py, columns.py). It differs from the author's reference in every
choice that could hide a shared error: Cartesian (x, y, z) cells of the rectangle instead of the axisymmetric disc of equal area, the rectangular part (any aspect,
any position) instead of a disc, a complex sparse solve per frequency, (K + j w C) T = q, instead of a modal decomposition, the readout as the HOTTEST footprint cell of the
heater's layer at every instant (the quantity of the program's step response) instead of the disc centre. It also holds what the author's reference cannot: a heater on any
copper layer, copper absent in a rectangle of any layer (partial copper), plated vias as copper columns, different top and bottom coefficients.

Grid. In the plane: uniform fine cells over the part plus a margin, growing geometrically to the board edges; the part edges and the via cells are grid lines. Through the
thickness: n_cu equal cells per copper layer and, in every laminate gap, cells that grow geometrically from `first` at each copper face (ratio `growth`). Conductance between
neighbours: the half-cell resistances in series (harmonic mean). Convection on the top and bottom faces through the half-cell resistance of the face cell, insulated board edge.
Laminate anisotropic (k_z through, k_r along the plane). A copper cell where the copper is absent holds laminate. A via is a plated barrel of copper area
pi (r^2 - (r - t)^2) (drill radius r, plating t inside it, the program's convention), added to the z conductivity and to the capacity of the cells it occupies, through the whole thickness.

Response. The transfer function H(w) from the power to every footprint cell is solved at frequencies spaced evenly in log f (8 per decade by default) and interpolated
(cubic spline of log|H| and of the unwrapped phase in log f); above the last frequency it is continued with the log-log slope of the last two points. The periodic steady
state of a unit square wave (on-power 1 W, period T, duty D) is T_c(t) = D H_c(0) + 2 Re sum_k c_k H_c(k w0) e^(j k w0 t), c_k = (1 - e^(-j 2 pi k D)) / (j 2 pi k),
evaluated on 2^14 samples per period; the swing is the peak-to-peak of the hottest cell max_c T_c(t). A time-domain check with implicit steps on the same matrices is
`time_domain_swing`.
"""

import dataclasses
from typing import List, Optional, Sequence, Tuple

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.interpolate import CubicSpline


@dataclasses.dataclass
class Board:
    """!
    @brief A rectangular board with equal laminate gaps (SI units), the stack of the program's simple stack-up.
    """
    width: float = 60e-3                 # Board width along x (m)
    height: float = 40e-3                # Board height along y (m)
    layers: int = 2                      # Copper layers
    thickness: float = 1.6e-3            # Total thickness (m)
    t_cu: float = 35e-6                  # Copper thickness of every layer (m)
    k_cu: float = 385.0                  # Copper conductivity (W/mK)
    rc_cu: float = 8960.0 * 385.0        # Copper volumetric heat capacity (J/m3K)
    kz: float = 0.3                      # Laminate conductivity through the thickness (W/mK)
    kr: float = 0.9                      # Laminate conductivity along the plane (W/mK)
    rc_lam: float = 1850.0 * 900.0       # Laminate volumetric heat capacity (J/m3K)
    h_top: float = 10.0                  # Top face coefficient (W/m2K)
    h_bottom: float = 10.0               # Bottom face coefficient (W/m2K)
    copper: bool = True                  # False: no copper anywhere


@dataclasses.dataclass
class Case:
    """!
    @brief The part, its layer, the copper removed and the vias.
    """
    part: Tuple[float, float, float, float]               # (x0, y0, x1, y1) of the part in m
    layer: int = 0                                        # Copper layer of the heater, 0 = top
    no_copper: Sequence[Tuple[int, Tuple[float, float, float, float]]] = ()   # (layer, rect) where the copper is absent
    vias: Sequence[Tuple[float, float]] = ()             # Via centres in m
    via_drill: float = 0.3e-3                             # Drill diameter (m); the plating is inside it, as in the program's Via
    via_plating: float = 25e-6                            # Barrel plating (m)
    bottom_extra: Sequence[Tuple[Tuple[float, float, float, float], float]] = ()   # (rect, h) added to the bottom coefficient (a heatsink of the program)


def _lines(lo: float, hi: float, a: float, b: float, fine: float, growth: float, extra: Sequence[float] = ()) -> np.ndarray:
    """!
    @brief Grid lines of one axis: uniform cells of width <= fine on [a, b], growing by `growth` towards lo and hi.
    @param lo Domain start (m).
    @param hi Domain end (m).
    @param a Start of the fine region (m), lo <= a.
    @param b End of the fine region (m), b <= hi.
    @param fine Fine cell width (m).
    @param growth Ratio of neighbouring cells outside the fine region.
    @param extra Further lines to insert (via cell edges), inside [lo, hi].
    @return Sorted array of lines.
    """
    n = max(1, int(np.ceil((b - a) / fine - 1e-9)))
    pts = list(np.linspace(a, b, n + 1))
    for start, end, sgn in ((a, lo, -1.0), (b, hi, 1.0)):
        x, w = start, fine
        while sgn * (end - x) > 1e-12:
            w *= growth
            nx = x + sgn * w
            if sgn * (end - nx) < 0.5 * w:              # The last cell absorbs the rest
                nx = end
            pts.append(nx)
            x = nx
    pts = np.unique(np.concatenate([np.round(np.array(pts), 12), np.round(np.asarray(extra, dtype=float), 12)]))
    return pts[(pts >= lo - 1e-12) & (pts <= hi + 1e-12)]


def _graded_gap(d: float, first: float, growth: float) -> np.ndarray:
    """!
    @brief Cell widths of a laminate gap graded from both faces.
    @param d Gap thickness (m).
    @param first First width at each face (m).
    @param growth Ratio of neighbouring cells.
    @return Widths summing to d.
    """
    half, w = [], first
    while sum(half) + w < 0.5 * d:
        half.append(w)
        w *= growth
    half = np.array(half) if half else np.array([0.5 * d])
    half *= 0.5 * d / half.sum()
    return np.concatenate([half, half[::-1]])


class Reference:
    """!
    @brief The assembled 3D model of one board and case, and its frequency responses at the footprint cells of the heater's layer.
    """

    def __init__(self, board: Board, case: Case, fine: float = None, margin: float = None, growth_xy: float = 1.3, n_cu: int = 6, first: float = 0.5e-6,
                 growth_z: float = 1.25, quarter: bool = False, top_first: Optional[float] = None):
        """!
        @brief Build the grid and the matrices.
        @param board Board.
        @param case Case.
        @param fine Fine in-plane cell (m); default the smaller part side / 10.
        @param margin Fine margin around the part (m); default the smaller part side / 2.
        @param growth_xy In-plane growth ratio outside the fine region.
        @param n_cu Cells per copper layer.
        @param first First laminate cell at a copper face (m).
        @param growth_z Growth ratio of the laminate cells.
        @param quarter True: model the quarter x >= W/2, y >= H/2 (part, copper and vias must be symmetric about the board centre; the cut planes are adiabatic).
        @param top_first None: the top copper slot in n_cu equal cells; a width in m: that slot graded from the top face with this first cell (needed when the part sits on
               bare laminate: a cell-centred surface cell of laminate reads low by about 0.45 of its width over the penetration depth, 12 % for 2 um at 1 kHz).
        """
        b, c = board, case
        x0, y0, x1, y1 = c.part
        s = min(x1 - x0, y1 - y0)
        fine = fine or s / 10.0
        margin = s / 2.0 if margin is None else margin
        r_cell = 0.5 * c.via_drill
        ex_x = [v for (vx, _) in c.vias for v in (vx - r_cell, vx + r_cell)]
        ex_y = [v for (_, vy) in c.vias for v in (vy - r_cell, vy + r_cell)]
        for _, (a0, b0, a1, b1) in c.no_copper:
            ex_x += [a0, a1]
            ex_y += [b0, b1]
        lox, loy = (0.5 * b.width, 0.5 * b.height) if quarter else (0.0, 0.0)
        ax, bx = max(lox, x0 - margin), min(b.width, x1 + margin)
        ay, by = max(loy, y0 - margin), min(b.height, y1 + margin)
        ex_x = [v for v in ex_x + [x0, x1] if lox <= v <= b.width]
        ex_y = [v for v in ex_y + [y0, y1] if loy <= v <= b.height]
        if quarter:
            ax, ay = lox, loy
        self.xl = _lines(lox, b.width, ax, bx, fine, growth_xy, ex_x)
        self.yl = _lines(loy, b.height, ay, by, fine, growth_xy, ex_y)
        # Through the thickness, top down: copper of layer 0, gap, copper of layer 1, ...
        L = b.layers
        dz, kind = [], []                                 # kind: copper layer index, or -1 for laminate
        gaps = [b.thickness - b.t_cu] if L == 1 else [(b.thickness - L * b.t_cu) / (L - 1)] * (L - 1)
        for i in range(L):
            if i == 0 and top_first is not None:
                w, cu = [], top_first
                while sum(w) + cu < b.t_cu:
                    w.append(cu)
                    cu *= growth_z
                w = np.array(w) * (b.t_cu / sum(w))
                dz += list(w)
                kind += [i] * len(w)
            else:
                dz += [b.t_cu / n_cu] * n_cu
                kind += [i] * n_cu
            if i < len(gaps):
                g = _graded_gap(gaps[i], first, growth_z)
                if L == 1:                                 # One layer: the laminate is graded from the copper only (the bottom face is bare)
                    g = _graded_gap(2 * gaps[i], first, growth_z)[:len(g) // 2]
                    g *= gaps[i] / g.sum()
                dz += list(g)
                kind += [-1] * len(g)
        self.dz, self.kind = np.array(dz), np.array(kind)
        self.board, self.case, self.quarter = b, c, quarter
        self._assemble()

    def _assemble(self):
        """!
        @brief Assemble K (W/K), the capacities C (J/K) and the source vector q (share of 1 W per cell).
        @return None.
        """
        b, c = self.board, self.case
        dx, dy, dz = np.diff(self.xl), np.diff(self.yl), self.dz
        xc, yc = 0.5 * (self.xl[1:] + self.xl[:-1]), 0.5 * (self.yl[1:] + self.yl[:-1])
        nx, ny, nz = len(dx), len(dy), len(dz)
        self.shape = (nz, ny, nx)
        X, Y = np.meshgrid(xc, yc)                        # (ny, nx)
        kx = np.empty(self.shape)
        kzz = np.empty(self.shape)
        rc = np.empty(self.shape)
        for k in range(nz):
            lay = self.kind[k]
            is_cu = np.full((ny, nx), lay >= 0 and b.copper)
            if lay >= 0:
                for (l2, (a0, b0, a1, b1)) in c.no_copper:
                    if l2 == lay:
                        is_cu &= ~((X > a0) & (X < a1) & (Y > b0) & (Y < b1))
            kx[k] = np.where(is_cu, b.k_cu, b.kr)
            kzz[k] = np.where(is_cu, b.k_cu, b.kz)
            rc[k] = np.where(is_cu, b.rc_cu, b.rc_lam)
        # Vias: the barrel copper area in the cell that holds the via centre (its edges are grid lines), added in z through the whole thickness
        r = 0.5 * c.via_drill
        a_cu = np.pi * (r ** 2 - max(r - c.via_plating, 0.0) ** 2)
        for (vx, vy) in c.vias:
            i, j = np.searchsorted(self.xl, vx) - 1, np.searchsorted(self.yl, vy) - 1
            if not (0 <= i < nx and 0 <= j < ny):
                continue
            f = a_cu / (dx[i] * dy[j])
            kzz[:, j, i] = (1 - f) * kzz[:, j, i] + f * b.k_cu
            rc[:, j, i] = (1 - f) * rc[:, j, i] + f * b.rc_cu
        idx = np.arange(nz * ny * nx).reshape(self.shape)
        rows, cols, vals = [], [], []
        diag = np.zeros(nz * ny * nx)

        def link(ia, ib, g):
            rows.extend([ia.ravel(), ib.ravel()])
            cols.extend([ib.ravel(), ia.ravel()])
            vals.extend([-g.ravel(), -g.ravel()])
            np.add.at(diag, ia.ravel(), g.ravel())
            np.add.at(diag, ib.ravel(), g.ravel())

        DX, DY, DZ = dx[None, None, :], dy[None, :, None], dz[:, None, None]
        # x faces
        ra = 0.5 * DX[:, :, :-1] / kx[:, :, :-1] + 0.5 * DX[:, :, 1:] / kx[:, :, 1:]
        link(idx[:, :, :-1], idx[:, :, 1:], (DY * DZ) / ra)
        # y faces
        ra = 0.5 * DY[:, :-1, :] / kx[:, :-1, :] + 0.5 * DY[:, 1:, :] / kx[:, 1:, :]
        link(idx[:, :-1, :], idx[:, 1:, :], (DX * DZ) / ra)
        # z faces
        ra = 0.5 * DZ[:-1] / kzz[:-1] + 0.5 * DZ[1:] / kzz[1:]
        link(idx[:-1], idx[1:], (DX * DY) / ra)
        # Convection of the two faces through the half cell
        A = dx[None, :] * dy[:, None]
        gt = A / (1.0 / b.h_top + 0.5 * dz[0] / kzz[0]) if b.h_top > 0 else np.zeros_like(A)
        hb = np.full_like(A, b.h_bottom)
        for (a0, b0, a1, b1), he in c.bottom_extra:
            hb += np.where((X > a0) & (X < a1) & (Y > b0) & (Y < b1), he, 0.0)
        gb = np.where(hb > 0, A / (1.0 / np.maximum(hb, 1e-300) + 0.5 * dz[-1] / kzz[-1]), 0.0)
        np.add.at(diag, idx[0].ravel(), gt.ravel())
        np.add.at(diag, idx[-1].ravel(), gb.ravel())
        self.g_top, self.g_bot = gt, gb
        n = nz * ny * nx
        self.K = (sp.csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)) + sp.diags(diag)).tocsc()
        self.C = (rc * DZ * DY * DX).ravel()
        # Source: the part's footprint on the heater layer; top layer: the top copper cell (flux on the face), inner: the copper cells of the layer (volumetric)
        x0, y0, x1, y1 = c.part
        foot = (X > x0) & (X < x1) & (Y > y0) & (Y < y1)
        if not foot.any():
            raise ValueError("the part covers no cell")
        zs = np.where(self.kind == c.layer)[0]
        if c.layer == 0:
            src_z = zs[:1]
        elif c.layer == b.layers - 1:
            src_z = zs[-1:]
        else:
            src_z = zs
        q = np.zeros(self.shape)
        w = np.where(foot, A, 0.0)
        for k in src_z:
            q[k] = w * dz[k]
        # In the quarter model 1/4 W in the quarter is 1 W on the whole board
        self.q = (q / q.sum() * (0.25 if self.quarter else 1.0)).ravel()
        # Readout: the copper cell of the heater layer next to the part (top layer: the top cell), every footprint cell
        zr = zs[-1] if (c.layer == b.layers - 1 and b.layers > 1) else zs[0]
        self.read = idx[zr][foot]
        self.read_xy = np.stack([X[foot], Y[foot]], axis=1)
        self.n = n

    def steady(self) -> np.ndarray:
        """!
        @brief Steady rise per watt in K of every cell.
        @return Array (n,).
        """
        return spla.spsolve(self.K, self.q)

    def heat_out(self, T: np.ndarray) -> float:
        """!
        @brief Heat leaving through the two faces in W for a field T (energy balance check).
        @param T Field (n,).
        @return Heat in W.
        """
        T3 = T.reshape(self.shape)
        return float((self.g_top * T3[0]).sum() + (self.g_bot * T3[-1]).sum())

    def transfer(self, freqs: np.ndarray) -> np.ndarray:
        """!
        @brief H(f) at the footprint cells (K/W, complex), one sparse LU per frequency.
        @param freqs Frequencies in Hz (f = 0 is the steady state).
        @return Array (len(freqs), len(read)).
        """
        out = np.empty((len(freqs), len(self.read)), dtype=complex)
        Cd = sp.diags(self.C)
        for i, f in enumerate(freqs):
            A = (self.K + 2j * np.pi * f * Cd).tocsc() if f > 0 else self.K.astype(complex)
            x = spla.splu(A, permc_spec="MMD_AT_PLUS_A").solve(self.q.astype(complex))
            out[i] = x[self.read]
        return out


class Response:
    """!
    @brief The interpolated transfer function of a Reference at its footprint cells, and the square-wave swing from it.
    """

    def __init__(self, ref: Reference, f_lo: float = 1e-3, f_hi: float = 3e5, per_decade: int = 8):
        """!
        @brief Solve the transfer function on the log grid.
        @param ref Reference.
        @param f_lo Lowest frequency (Hz).
        @param f_hi Highest frequency (Hz).
        @param per_decade Frequencies per decade.
        """
        n = int(round(per_decade * np.log10(f_hi / f_lo))) + 1
        self.f = np.geomspace(f_lo, f_hi, n)
        H = ref.transfer(np.concatenate([[0.0], self.f]))
        self.h0 = H[0].real
        Hf = H[1:]
        lf = np.log(self.f)
        self.spl_mag = CubicSpline(lf, np.log(np.abs(Hf)), axis=0)
        self.spl_ph = CubicSpline(lf, np.unwrap(np.angle(Hf), axis=0), axis=0)
        self.slope = (np.log(np.abs(Hf[-1])) - np.log(np.abs(Hf[-2]))) / (lf[-1] - lf[-2])
        self.ph_end = np.unwrap(np.angle(Hf), axis=0)[-1]
        self.lf_end, self.mag_end = lf[-1], np.log(np.abs(Hf[-1]))
        self.read_xy = ref.read_xy

    def H(self, f: np.ndarray) -> np.ndarray:
        """!
        @brief Interpolated H at frequencies f (Hz, > f_lo), (len(f), cells).
        @param f Frequencies.
        @return Complex array.
        """
        lf = np.log(np.asarray(f, dtype=float))
        inside = lf <= self.lf_end
        out = np.empty((len(lf), len(self.h0)), dtype=complex)
        li = lf[inside]
        out[inside] = np.exp(self.spl_mag(li) + 1j * self.spl_ph(li))
        lo = lf[~inside]
        if len(lo):
            mag = self.mag_end[None, :] + self.slope[None, :] * (lo[:, None] - self.lf_end)
            out[~inside] = np.exp(mag + 1j * self.ph_end[None, :])
        return out

    def wave(self, period: float, duty: float, n_samples: int = 16384) -> np.ndarray:
        """!
        @brief Periodic steady state of a unit square wave at every footprint cell, (n_samples, cells), K per watt of on-power.
        @param period Period (s).
        @param duty On fraction.
        @param n_samples Samples per period.
        @return Real array.
        """
        k = np.arange(1, n_samples // 2)
        Hk = self.H(k / period)
        ck = (1.0 - np.exp(-2j * np.pi * k * duty)) / (2j * np.pi * k)
        spec = np.zeros((n_samples, Hk.shape[1]), dtype=complex)
        spec[1:n_samples // 2] = Hk * ck[:, None]
        spec[-(n_samples // 2 - 1):] = np.conj((Hk * ck[:, None])[::-1])
        return np.fft.ifft(spec, axis=0).real * n_samples + duty * self.h0[None, :]

    def swing(self, period: float, duty: float, n_samples: int = 16384) -> float:
        """!
        @brief Peak-to-peak of the hottest footprint cell at every instant (the program's step-response quantity), K/W.
        @param period Period (s).
        @param duty On fraction.
        @param n_samples Samples per period.
        @return Swing in K/W.
        """
        t = self.wave(period, duty, n_samples).max(axis=1)
        return float(t.max() - t.min())


def time_domain_swing(ref: Reference, period: float, duty: float, steps_per_period: int = 4000, cycles: int = 12) -> float:
    """!
    @brief The same swing by implicit-Euler steps on the same matrices (independent check of the harmonic sum), from the steady state of the average power.
    @param ref Reference.
    @param period Period (s).
    @param duty On fraction (the on-time must be a whole number of steps).
    @param steps_per_period Steps per period.
    @param cycles Cycles simulated (the last one is read).
    @return Swing in K/W of the hottest footprint cell.
    """
    dt = period / steps_per_period
    n_on = int(round(duty * steps_per_period))
    Cd = sp.diags(ref.C / dt)
    lu = spla.splu((Cd + ref.K).tocsc(), permc_spec="MMD_AT_PLUS_A")
    x = duty * spla.spsolve(ref.K, ref.q)
    trace = []
    for cyc in range(cycles):
        for s in range(steps_per_period):
            p = 1.0 if s < n_on else 0.0
            x = lu.solve(ref.C / dt * x + p * ref.q)
            if cyc == cycles - 1:
                trace.append(x[ref.read].max())
    return float(max(trace) - min(trace))
