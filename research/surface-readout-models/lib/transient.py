#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file transient.py
@brief The surface read-out of a transient frame of the program's FVM network (rule T), and the matching stacks for the independent column solver.
@details The program's transient keeps only the node temperatures of the board layers in its frames, and its laminate sub-nodes are dropped. Here the network of the program (fvm.Network: K, C, Q, the films) is
         integrated with BDF2 at a constant step, every node is kept, and for one cell the face fluxes of layer 1 are read exactly as pcbthermal/thickness.attach reads them in steady state (the source,
         the film of the outer face, the couplings K to every node of another layer), then the parabola of thickness.offsets gives the face. The board is one-dimensional (a part covers the whole face of an
         insulated board), so every cell is the same and the independent column solver (lib/column1d.py) is the exact reference. tests/test_transient.py holds the flux reading against thickness.attach.
"""

import os
import sys

import numpy as np
import scipy.sparse.linalg as spla

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
HERE = os.path.dirname(os.path.abspath(__file__))
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
from pcbthermal import Problem, fvm, thickness  # noqa: E402
from pcbthermal.model import Dielectric, Materials  # noqa: E402
import column1d  # noqa: E402

AMB = 25.0
W_MM = 20.0
RHO_C_CU = 8960.0 * 385.0
RHO_C_FR4 = 1850.0 * 900.0
T_BOT_UM = 35.0

# name, kind, thick layer mm, its k, its rho c, bottom film
CASES = [
    ("10 mm Cu, k 385", "one", 10.0, 385.0, RHO_C_CU, 400.0),
    ("10 mm Al, k 200", "one", 10.0, 200.0, 2700.0 * 900.0, 1000.0),
    ("2 mm Cu + 1 mm FR-4 + 35 um", "two", 2.0, 385.0, RHO_C_CU, 50.0),
    ("35 um Cu + 1.53 mm FR-4 + 35 um", "thin", 0.035, 385.0, RHO_C_CU, 15.0),
]


def problem(case):
    """!
    @brief The one-dimensional board of a case: a part over the whole face, insulated sides and top.
    @param case Entry of CASES.
    @return Problem (the heater has 1 W; the study scales it).
    """
    name, kind, t, k, rc, h = case
    mat = Materials(k_copper=k, rho_copper=rc / 385.0, cp_copper=385.0)           # rho c of the metal as given (cp 385)
    if kind == "one":
        p = Problem.new(W_MM, W_MM, layers=1, thickness_mm=1.0001 * t, copper_um=t * 1e3, ambient=AMB, h_top=1e-6, h_bottom=h, h_side=None, materials=mat)
    else:
        t_lam = 1.0 if kind == "two" else 1.53
        mat = Materials(k_copper=k, rho_copper=rc / 385.0, cp_copper=385.0, k_fr4_through=0.3, k_fr4_inplane=0.3)
        p = Problem.new(W_MM, W_MM, layers=2, thickness_mm=t + t_lam + 0.035, copper_um=35.0, ambient=AMB, h_top=1e-6, h_bottom=h, h_side=None, materials=mat)
        p.board.copper_thickness = [t * 1e-3, T_BOT_UM * 1e-6]
        p.board.dielectrics = [Dielectric(thickness=t_lam * 1e-3, name="FR-4", k_through=0.3, k_inplane=0.3, rho=1850.0, cp=900.0)]
    p.add_full_copper(layers=None)
    p.add_heater(1, 1.0, rect=(0.0, 0.0, W_MM, W_MM), name="S")
    return p


def column_stack(case):
    """!
    @brief The stack of the independent column solver that matches the problem.
    @param case Entry of CASES.
    @return List of (thickness m, k, rho c, cells) from the top.
    """
    name, kind, t, k, rc, h = case
    if kind == "one":
        return [(t * 1e-3, k, rc, 80), (1e-4 * t * 1e-3, 0.3, RHO_C_FR4, 2)]
    t_lam = 1.0 if kind == "two" else 1.53
    return [(t * 1e-3, k, rc, 80 if t > 0.5 else 6), (t_lam * 1e-3, 0.3, RHO_C_FR4, 20), (T_BOT_UM * 1e-6, k, rc, 2)]


class Frames:
    """!
    @brief The network of the program at one cell, integrated with BDF2, with the face fluxes of layer 1 read at every step.
    """

    def __init__(self, prob, cell_mm=10.0):
        """!
        @param prob Problem of a one-dimensional board (problem()).
        @param cell_mm Cell size in mm (coarse: the board is one-dimensional).
        """
        b = prob.board
        self.prob = prob
        nx = ny = max(int(round(b.width * 1000.0 / cell_mm)), 2)
        self.net = fvm.Network(prob, nx, ny)
        net = self.net
        self.n = nx * ny
        self.cell = (ny // 2) * nx + nx // 2
        self.area = net.dx * net.dy
        r = self.cell                                           # layer 0
        row = net.K.tocsr()[r].tocoo()
        off = (row.col // self.n) != 0
        self.cols, self.g = row.col[off], -row.data[off]
        self.q0 = float(net.Q[0].ravel()[self.cell])            # W in the cell for the 1 W part
        self.film = float(net.g_top[0].ravel()[self.cell] + net.g_heatsink[0].ravel()[self.cell])
        self.t = float(b.copper_thickness[0])
        self.k = b.materials.k_copper

    def run(self, scale, dt, steps):
        """!
        @brief Integrate and read the column and the surface of layer 1 at the middle cell.
        @param scale Function of time returning the multiplier of the part's power (1 W per unit area of the board).
        @param dt Constant step in s.
        @param steps Number of steps.
        @return dict with t, col (rise of the node), surf (rise of the surface by the parabola), q_top, q_bot (W/m2), power (W/m2 entering, for the multiplier 1 is 1/area W/m2 per W).
        """
        net = self.net
        N = net.nl * self.n
        C = net.C.ravel()
        import scipy.sparse as sp
        lu1 = spla.splu((sp.diags(C / dt) + net.K).tocsc())
        lu2 = spla.splu((sp.diags(1.5 * C / dt) + net.K).tocsc())
        q = net.Q.ravel()
        x = np.zeros(N)
        x_old = np.zeros(N)
        t = np.arange(steps + 1) * dt
        col, qt, qb = np.zeros(steps + 1), np.zeros(steps + 1), np.zeros(steps + 1)
        for s in range(steps):
            qs = q * scale(t[s + 1])
            x_new = lu1.solve(C * x / dt + qs) if s == 0 else lu2.solve(C * (4.0 * x - x_old) / (2.0 * dt) + qs)
            x_old, x = x, x_new
            th = x[self.cell]
            col[s + 1] = th
            inner = float((self.g * (th - x[self.cols])).sum())
            qt[s + 1] = (self.q0 * scale(t[s + 1]) - self.film * th) / self.area
            qb[s + 1] = -(inner + float(net.g_bottom[0].ravel()[self.cell]) * th) / self.area
        d_top, _ = thickness.offsets(self.t, self.k, qt, qb)
        return {"t": t, "col": col, "surf": col + d_top, "d": d_top, "q_top": qt, "q_bot": qb, "bound": np.abs(qt) * self.t / (2.0 * self.k)}


def reference(case, scale, dt, steps, power_w=1.0):
    """!
    @brief The exact one-dimensional history of the same board and the same drive.
    @param case Entry of CASES.
    @param scale Function of time (multiplier of the power).
    @param dt Step in s.
    @param steps Number of steps.
    @param power_w Power of the part in W (it covers the whole face).
    @return dict from column1d.solve (surf, mean[0], ...).
    """
    q = power_w / (W_MM * 1e-3) ** 2
    return column1d.solve(column_stack(case), case[5], lambda s: q * scale(s), steps * dt, dt)
