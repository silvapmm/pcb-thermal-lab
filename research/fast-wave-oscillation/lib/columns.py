#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file columns.py
@brief One-dimensional columns under the footprint of a part: the exact stack (copper and laminate resolved through the thickness) and the program's lumped column (one node per copper layer), and their difference as a step response.

@details This is the prototype of the correction of research/fast-wave-oscillation (README 5): the difference dZ(t) = Z_exact(t) - Z_lumped(t) of the two columns, both per watt
of the same footprint area, is added to the step response of the program. Imports nothing from pcbthermal; the program's rule for the lumped column (the copper node holds the
copper and the laminate of its slab, the link is k_z A / d with d the thickness of the whole gap) is copied from fvm.Network (simple stack-up) and checked in tests.
"""

from typing import Dict, Tuple

import numpy as np

import axisym_stack as A


class Modal:
    """!
    @brief A symmetric linear thermal system C dT/dt = -K T + q P(t) in modal form, with the same response methods as axisym_stack.Reference.
    """

    def __init__(self, C: np.ndarray, K: np.ndarray, q: np.ndarray, readouts: Dict[str, np.ndarray]):
        """!
        @brief Diagonalise.
        @param C Heat capacities (J/K), shape (n,).
        @param K Conductance matrix (W/K), symmetric positive definite.
        @param q Share of the unit power on every node.
        @param readouts Mapping name to weight vector of a temperature readout.
        """
        s = 1.0 / np.sqrt(C)
        self.lam, V = np.linalg.eigh(K * s[:, None] * s[None, :])
        self.b = V.T @ (s * q)
        self.R = {k: V.T @ (s * v) for k, v in readouts.items()}
        self.rth = {k: float(np.sum(self.R[k] * self.b / self.lam)) for k in self.R}

    step = A.Reference.step
    square_wave = A.Reference.square_wave


def _chain(dz: np.ndarray, kz: np.ndarray, rcp: np.ndarray, area: float, h_top: float, h_bottom: float) -> Tuple[np.ndarray, np.ndarray]:
    """!
    @brief C and K of a chain of cells in z.
    @param dz Cell thicknesses (m).
    @param kz Conductivities (W/mK).
    @param rcp Volumetric heat capacities (J/m3K).
    @param area Column area (m2).
    @param h_top Top-face coefficient (W/m2K).
    @param h_bottom Bottom-face coefficient (W/m2K).
    @return Tuple (C, K).
    """
    n = len(dz)
    C = rcp * dz * area
    K = np.zeros((n, n))
    for k in range(n - 1):
        g = area / (0.5 * dz[k] / kz[k] + 0.5 * dz[k + 1] / kz[k + 1])
        K[k, k] += g; K[k + 1, k + 1] += g; K[k, k + 1] -= g; K[k + 1, k] -= g
    K[0, 0] += h_top * area
    K[-1, -1] += h_bottom * area
    return C, K


def exact_column(stack: A.Stack, area: float, h_top: float, h_bottom: float, n_cu: int = 4, n_gap: int = 16, first: float = 1.5e-6) -> Modal:
    """!
    @brief The stack resolved through the thickness, one-dimensional.
    @param stack Stack.
    @param area Footprint area in m2.
    @param h_top Top coefficient.
    @param h_bottom Bottom coefficient.
    @param n_cu Cells per copper layer.
    @param n_gap Cells per side of every gap.
    @param first First laminate cell in m.
    @return Modal system with the readout "top" (top copper cell).
    """
    dz, cu, _ = A.build_z(stack, n_cu, n_gap, first)
    cm = cu & stack.copper
    C, K = _chain(dz, np.where(cm, stack.k_cu, stack.kz), np.where(cm, stack.rho_cp_cu, stack.rho_cp_lam), area, h_top, h_bottom)
    q = np.zeros(len(dz)); q[:n_cu] = C[:n_cu] / C[:n_cu].sum()
    r = np.zeros(len(dz)); r[0] = 1.0
    return Modal(C, K, q, {"top": r})


def lumped_column(stack: A.Stack, area: float, h_top: float, h_bottom: float) -> Modal:
    """!
    @brief The program's column: one node per copper layer holding the copper and the laminate of its slab, links k_z A / d across the whole gap.
    @param stack Stack (simple stack-up: slab = thickness / layers).
    @param area Footprint area in m2.
    @param h_top Top coefficient.
    @param h_bottom Bottom coefficient.
    @return Modal system with the readout "top" (node of layer 1).
    """
    L = stack.layers
    if L == 1:
        # One-layer board: the copper node plus two laminate nodes (laminate.nodes: gap = (thickness - t_cu) / 2, the last holds half a gap)
        g = (stack.thickness - stack.t_cu) / 2.0
        slabs = np.array([stack.t_cu + 0.5 * g, g, 0.5 * g])
        cmat = np.array([stack.rho_cp_cu * stack.t_cu + stack.rho_cp_lam * 0.5 * g, stack.rho_cp_lam * g, stack.rho_cp_lam * 0.5 * g])
        C = cmat * area
        K = np.zeros((3, 3))
        for k in range(2):
            gk = stack.kz * area / g
            K[k, k] += gk; K[k + 1, k + 1] += gk; K[k, k + 1] -= gk; K[k + 1, k] -= gk
        K[0, 0] += h_top * area; K[-1, -1] += h_bottom * area
        q = np.array([1.0, 0, 0]); r = q.copy()
        return Modal(C, K, q, {"top": r})
    slab = stack.thickness / L
    d = (stack.thickness - L * stack.t_cu) / (L - 1)
    c_node = (stack.rho_cp_cu * stack.t_cu + stack.rho_cp_lam * (slab - stack.t_cu)) * area
    C = np.full(L, c_node)
    K = np.zeros((L, L))
    for k in range(L - 1):
        gk = stack.kz * area / d
        K[k, k] += gk; K[k + 1, k + 1] += gk; K[k, k + 1] -= gk; K[k + 1, k] -= gk
    K[0, 0] += h_top * area; K[-1, -1] += h_bottom * area
    q = np.zeros(L); q[0] = 1.0
    return Modal(C, K, q, {"top": q.copy()})
