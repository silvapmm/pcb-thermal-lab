#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file axisym_stack.py
@brief Independent transient reference: axisymmetric (r, z) conduction through the copper and laminate stack of a board under a disc source, exact in time by modal decomposition.

@details Imports nothing from pcbthermal. The board is a disc of the same area as the real rectangle. The stack is resolved through its thickness: every copper layer in
cells of a few micrometres, every laminate gap in cells that grow from 1.5 um at each copper face (the penetration depth of a 10 kHz wave in FR-4 is 4 um), so the
temperature gradient inside the 35 um copper and the laminate that the program's single node per layer cannot hold is represented. Cell-centred finite volumes,
anisotropic laminate (k_z, k_r), convection on the two faces, insulated edge. The semi-discrete system C dT/dt = -K T + q P(t) is symmetric positive definite, so
K~ = C^(-1/2) K C^(-1/2) = V diag(lambda) V^T and every response is a sum of exponentials; the periodic steady state of a square wave is then a closed form per mode
(no time stepping, no cycle count). The module checks itself against the semi-infinite solid (erfc closed form) in tests/test_axisym_stack.py.
"""

import dataclasses
from typing import Tuple

import numpy as np


@dataclasses.dataclass
class Stack:
    """!
    @brief Material stack, top down, of a board (SI units).
    """
    t_cu: float = 35e-6                 # Copper thickness of every layer (m)
    layers: int = 2                     # Number of copper layers
    thickness: float = 1.6e-3           # Total board thickness (m)
    k_cu: float = 385.0                 # Copper conductivity (W/mK)
    rho_cp_cu: float = 8960.0 * 385.0   # Copper volumetric heat capacity (J/m3K)
    kz: float = 0.3                     # Laminate conductivity through the thickness (W/mK)
    kr: float = 0.9                     # Laminate conductivity along the plane (W/mK)
    rho_cp_lam: float = 1850.0 * 900.0  # Laminate volumetric heat capacity (J/m3K)
    copper: bool = True                 # False: no copper anywhere (the copper cells hold laminate; a bare board)


def _graded(length: float, n: int, first: float, both_ends: bool) -> np.ndarray:
    """!
    @brief Cell widths of a gap, growing geometrically from the copper face(s).
    @param length Gap thickness in m.
    @param n Cells (per side when both_ends, else the whole gap).
    @param first Width of the cell at the copper face in m.
    @param both_ends True: graded from both faces and meeting in the middle (a gap between two copper layers).
    @return Array of widths summing to length.
    """
    def one_side(total, m):
        # Ratio r such that first * (r^m - 1) / (r - 1) = total
        lo, hi = 1.0 + 1e-9, 3.0
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            s = first * (mid ** m - 1.0) / (mid - 1.0)
            lo, hi = (mid, hi) if s < total else (lo, mid)
        r = 0.5 * (lo + hi)
        w = first * r ** np.arange(m)
        return w * (total / w.sum())

    if both_ends:
        half = one_side(0.5 * length, n)
        return np.concatenate([half, half[::-1]])
    return one_side(length, n)


def build_z(stack: Stack, n_cu: int = 4, n_gap: int = 16, first: float = 1.5e-6) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """!
    @brief The z cells of the stack, top down.
    @param stack Stack.
    @param n_cu Cells per copper layer.
    @param n_gap Cells per side of every gap (the bottom laminate of a one-layer board uses n_gap cells graded from the copper only).
    @param first Width of the first laminate cell at a copper face in m.
    @return Tuple (dz, is_copper, layer_index) arrays; layer_index is the copper layer a copper cell belongs to, -1 for laminate.
    """
    L = stack.layers
    dz, cu, idx = [], [], []
    if L == 1:
        gaps = [stack.thickness - stack.t_cu]
    else:
        g = (stack.thickness - L * stack.t_cu) / (L - 1)        # Equal gaps between the copper layers (outer copper on the faces)
        gaps = [g] * (L - 1)
    for i in range(L):
        dz += [stack.t_cu / n_cu] * n_cu
        cu += [True] * n_cu
        idx += [i] * n_cu
        if i < len(gaps):
            w = _graded(gaps[i], n_gap, first, both_ends=(L > 1))
            dz += list(w)
            cu += [False] * len(w)
            idx += [-1] * len(w)
    return np.array(dz), np.array(cu), np.array(idx)


def build_r(a: float, r_board: float, n_in: int = 10, n_out: int = 24) -> np.ndarray:
    """!
    @brief The radial cell edges: n_in equal cells under the disc of radius a, then cells that grow to the board radius.
    @param a Source radius in m.
    @param r_board Board radius in m.
    @param n_in Cells under the source.
    @param n_out Cells outside it.
    @return Edges, increasing, starting at 0, with an edge exactly at a.
    """
    inner = np.linspace(0.0, a, n_in + 1)
    w0 = a / n_in
    lo, hi = 1.0 + 1e-9, 3.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        s = w0 * (mid ** n_out - mid) / (mid - 1.0)
        lo, hi = (mid, hi) if s < (r_board - a) else (lo, mid)
    r = 0.5 * (lo + hi)
    w = w0 * r ** np.arange(1, n_out + 1)
    w *= (r_board - a) / w.sum()
    return np.concatenate([inner, a + np.cumsum(w)])


class Reference:
    """!
    @brief Modal solution of the axisymmetric stack under a disc source.
    """

    def __init__(self, stack: Stack, a: float, r_board: float, h_top: float, h_bottom: float, n_cu: int = 4, n_gap: int = 16, n_in: int = 10, n_out: int = 24):
        """!
        @brief Assemble and diagonalise the system.
        @param stack Stack.
        @param a Source (part) radius in m.
        @param r_board Board radius in m (the disc of the same area as the rectangle).
        @param h_top Convection coefficient of the top face in W/m2K.
        @param h_bottom Convection coefficient of the bottom face in W/m2K.
        @param n_cu Cells per copper layer.
        @param n_gap Cells per side of every gap.
        @param n_in Radial cells under the source.
        @param n_out Radial cells outside the source.
        """
        dz, cu, idx = build_z(stack, n_cu, n_gap)
        re = build_r(a, r_board, n_in, n_out)
        nz, nr = len(dz), len(re) - 1
        self.nz, self.nr, self.dz, self.re, self.cu, self.idx = nz, nr, dz, re, cu, idx
        rc = 0.5 * (re[1:] + re[:-1])
        ring = np.pi * (re[1:] ** 2 - re[:-1] ** 2)                      # Face area of a ring (m2)
        cu_m = cu & stack.copper                                         # Cells that really hold copper
        kz = np.where(cu_m, stack.k_cu, stack.kz)
        kr = np.where(cu_m, stack.k_cu, stack.kr)
        rcp = np.where(cu_m, stack.rho_cp_cu, stack.rho_cp_lam)
        n = nz * nr
        node = lambda k, i: k * nr + i                                   # noqa: E731
        C = (rcp[:, None] * dz[:, None] * ring[None, :]).ravel()
        K = np.zeros((n, n))
        for k in range(nz):
            for i in range(nr):
                p = node(k, i)
                if k + 1 < nz:                                           # Vertical link to the cell below
                    g = ring[i] / (0.5 * dz[k] / kz[k] + 0.5 * dz[k + 1] / kz[k + 1])
                    q = node(k + 1, i)
                    K[p, p] += g; K[q, q] += g; K[p, q] -= g; K[q, p] -= g
                if i + 1 < nr:                                           # Radial link to the next ring
                    rf = re[i + 1]
                    g = 2.0 * np.pi * dz[k] / (np.log(rf / rc[i]) / kr[k] + np.log(rc[i + 1] / rf) / kr[k])
                    q = node(k, i + 1)
                    K[p, p] += g; K[q, q] += g; K[p, q] -= g; K[q, p] -= g
        for i in range(nr):                                              # Convection on the two faces
            K[node(0, i), node(0, i)] += h_top * ring[i]
            K[node(nz - 1, i), node(nz - 1, i)] += h_bottom * ring[i]
        s = 1.0 / np.sqrt(C)
        lam, V = np.linalg.eigh(K * s[:, None] * s[None, :])
        self.lam, self.V, self.s, self.C = lam, V, s, C
        # Unit power on the top copper cells under the source (area-weighted)
        n_src = n_in
        q = np.zeros(n)
        w = ring[:n_src] / ring[:n_src].sum()
        q[node(0, 0):node(0, 0) + n_src] = w
        self.b = V.T @ (s * q)                                           # Modal input
        # Readouts as rows of weights over the nodes
        r_center = np.zeros(n); r_center[node(0, 0)] = 1.0               # Centre cell of the top copper (the program's hottest cell)
        self.readouts = {"center": r_center, "mean": q.copy()}
        self.R = {k: V.T @ (s * v) for k, v in self.readouts.items()}    # Modal output weights (T = sum_k R_k y_k)
        self.rth = {k: float(np.sum(self.R[k] * self.b / lam)) for k in self.R}

    def step(self, t: np.ndarray, readout: str = "center") -> np.ndarray:
        """!
        @brief Unit step response in K/W.
        @param t Times in s.
        @param readout "center" or "mean".
        @return Array like t.
        """
        t = np.asarray(t, dtype=float)
        c = self.R[readout] * self.b / self.lam
        return (c[None, :] * (-np.expm1(-np.outer(t, self.lam)))).sum(axis=1)

    def square_wave(self, period: float, duty: float, readout: str = "center", points: int = 40) -> Tuple[float, float]:
        """!
        @brief Periodic steady state of a unit square wave (1 W on for duty * period, 0 W off): maximum and minimum of the readout over the cycle.
        @param period Period in s.
        @param duty On fraction (0 to 1).
        @param readout "center" or "mean".
        @param points Samples per phase, geometric from each switching instant (the extreme of a non-monotone readout is searched there; for centre = input it is at the edges).
        @return Tuple (maximum, minimum) in K above ambient per watt of on-power.
        """
        lam = self.lam
        tp, to = duty * period, (1.0 - duty) * period
        y_on = self.b / lam
        e_off, e_p, e_T = np.exp(-lam * to), np.exp(-lam * tp), np.exp(-lam * period)
        # y0 (1 - e^{-lam T}) = y_on (e^{-lam to} - e^{-lam T}) (the off-power is zero)
        y0 = y_on * (e_off - e_T) / (-np.expm1(-lam * period))
        y1 = y_on + (y0 - y_on) * e_p
        Rr = self.R[readout]
        phase_on = np.geomspace(tp * 1e-6, tp, points)
        phase_off = np.geomspace(max(to, period * 1e-9) * 1e-6, max(to, period * 1e-9), points)
        y_on_t = y_on[None, :] + (y0[None, :] - y_on[None, :]) * np.exp(-np.outer(phase_on, lam))
        y_off_t = y1[None, :] * np.exp(-np.outer(phase_off, lam))
        vals = np.concatenate([y_on_t @ Rr, y_off_t @ Rr, [y0 @ Rr, y1 @ Rr]])
        return float(vals.max()), float(vals.min())


def rectangle_radius(width_m: float, height_m: float) -> float:
    """!
    @brief Radius of the disc with the area of a rectangle.
    @param width_m Width in m.
    @param height_m Height in m.
    @return Radius in m.
    """
    return float(np.sqrt(width_m * height_m / np.pi))


def part_radius(side_m: float) -> float:
    """!
    @brief Radius of the disc with the area of a square part.
    @param side_m Side in m.
    @return Radius in m.
    """
    return float(side_m / np.sqrt(np.pi))
