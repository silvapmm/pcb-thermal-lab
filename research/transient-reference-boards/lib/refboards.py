#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file refboards.py
@brief The five synthetic boards of the transient comparison, each as a finite-element model (`independent-fem-edge` and `independent-fem-extensions`, imported and not
       edited) and as the program's `Problem`, plus the readouts and the step-response and wave helpers shared by the study scripts.
@details Boards (all SI inside the FEM, mm in the `Problem`; 1 W of the part, h 10 W/m2K on the faces and the walls unless stated):
         `simple4`  100 x 80 mm, four layers (simple stack-up, 35 um copper, equal gaps), full copper, 6 x 6 mm part, h_side 10 (the case of the 16 % shift of the simple
                    stack-up: a small part on the outer nodes of a four-layer board, whose response is first the local one and then the board's);
         `vias`     a 20 x 20 mm four-layer board with a 4 x 4 cluster of resin-filled hollow vias (0.3 mm drill, 0.8 mm pitch) under the part;
         `plate`    `vias` with a 1 mm aluminium plate under the board through a 0.1 mm interface (FVM and FDM only: the Lumped and Analytic refuse a block in the transient);
         `two2`     60 x 40 mm, two layers, full copper, 10 mm part, insulated edges (the plate of `research/fast-wave-oscillation`);
         `disc`     disc of radius 10 mm with a 4 mm square part, two layers, h_side 10 (an outline board: FVM and FDM only).
         The FEM reads the footprint mean and the hottest top node of the footprint (found in the steady field); the program's FVM and FDM read the hottest cell or node of the board.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
EXT = os.path.join(HERE, "..", "..", "independent-fem-extensions", "lib")
EDGE = os.path.join(HERE, "..", "..", "independent-fem-edge", "lib")
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for p in (EXT, EDGE):
    if p not in sys.path:
        sys.path.insert(0, p)

MM = 1e-3
RC_CU, RC_FR4 = 8960 * 385.0, 1850 * 900.0
BOARDS = ("simple4", "vias", "plate", "two2", "disc")
# Boards that the Lumped and the Analytic can take in a transient (no block, no outline)
REDUCED_OK = ("simple4", "vias", "two2")
# Time horizon (s) of the step response of every board (about ten board time constants, so that the response has reached its plateau: a response cut short makes the
# periodic superposition of a wave see a jump to the steady value) and the first step
T_END = {"simple4": 1500.0, "vias": 1500.0, "plate": 2500.0, "two2": 1500.0, "disc": 1000.0}
DT0 = {"simple4": 1e-3, "vias": 2e-3, "plate": 0.05, "two2": 0.01, "disc": 2e-3}


def t_at(t, z, target):
    """!
    @brief Time at which a rising curve crosses a value (linear in log time between samples).
    @param t Times (the first may be 0).
    @param z Curve.
    @param target Value.
    @return float or None when never reached.
    """
    t, z = np.asarray(t, float), np.asarray(z, float)
    ix = np.nonzero(z >= target)[0]
    if ix.size == 0:
        return None
    k = ix[0]
    if k == 0:
        return float(t[0])
    f = (target - z[k - 1]) / (z[k] - z[k - 1])
    if t[k - 1] <= 0:
        return float(t[k - 1] + f * (t[k] - t[k - 1]))
    return float(np.exp(np.log(t[k - 1]) + f * (np.log(t[k]) - np.log(t[k - 1]))))


def board_rho_c(m):
    """!
    @brief Heat capacity per element of a `board.Board` model: copper where the through-thickness conductivity is that of copper, laminate elsewhere.
    @param m fem.Model.
    @return numpy.ndarray (E,).
    """
    return np.where(m.k[:, 2] > 100.0, RC_CU, RC_FR4)


def fem_board(name, level):
    """!
    @brief Build the finite-element model of a board at a mesh level.
    @param name One of BOARDS.
    @param level Fine plan size in mm for `simple4`, `vias`, `plate` and `two2`; the number of intervals across the part for `disc`.
    @return Tuple (model, rho_c per element, footprint faces (F, 4) node array of the top face, wall weight note str).
    """
    if name == "simple4":
        import board
        import cases
        import mesh2d
        xn = cases.axis(50.0, [3.0], [(0, 3.3)], level, 1.3, 2.0)
        yn = cases.axis(40.0, [3.0], [(0, 3.3)], level, 1.3, 2.0)
        plan = mesh2d.tensor(xn, yn)
        b = board.Board(plan, 4, board_t=1.6e-3, k_xy=0.9, k_z=0.3, n_gap=4, gap_ratio=1.3, h_top=10.0, h_bottom=10.0, h_side=10.0, symmetry=[("x", 0.0), ("y", 0.0)],
                        heaters=[(cases.rect(-1, -1, 3, 3), 0.25)])
        m, info = b.build()
        return m, board_rho_c(m), np.vstack(info["heater_faces"])
    if name in ("vias", "plate"):
        import cluster
        st, hd = cluster.build("A", 6.0, level, plate=(name == "plate"))
        m, info = st.build()
        qs = np.nonzero(hd["inside"](info["c"]))[0]
        return m, info["rho_c"], st.level_nodes(info, 0, qs)
    if name == "two2":
        import board
        import cases
        import mesh2d
        xn = cases.axis(30.0, [5.0], [(0, 5.3)], level, 1.3, 1.0)
        yn = cases.axis(20.0, [5.0], [(0, 5.3)], level, 1.3, 1.0)
        plan = mesh2d.tensor(xn, yn)
        b = board.Board(plan, 2, board_t=1.6e-3, k_xy=0.9, k_z=0.3, n_gap=12, gap_ratio=1.3, h_top=10.0, h_bottom=10.0, symmetry=[("x", 0.0), ("y", 0.0)],
                        heaters=[(cases.rect(-1, -1, 5, 5), 0.25)])
        m, info = b.build()
        return m, board_rho_c(m), np.vstack(info["heater_faces"])
    if name == "disc":
        import cases
        b = cases.disc_board(10.0, n_side=int(level), n_gap=8, layers=2)
        m, info = b.build()
        return m, board_rho_c(m), np.vstack(info["heater_faces"])
    raise ValueError(name)


def program_problem(name):
    """!
    @brief The program's `Problem` of a board (variant of the finite-element board: a 1 W part, h 10 on the faces and 10 on the walls).
    @param name One of BOARDS.
    @return pcbthermal.Problem.
    """
    sys.path.insert(0, ROOT)
    from pcbthermal import Problem
    if name == "simple4":
        p = Problem.new(100, 80, 4, 1.6, 35.0, h_top=10.0, h_bottom=10.0, h_side=10.0)
        for lay in range(1, 5):
            p.add_zone(lay, rect=(0, 0, 100, 80))
        p.add_heater(1, 1.0, rect=(47, 37, 53, 43), role="source")
        return p
    if name in ("vias", "plate"):
        p = Problem.new(20, 20, 4, 1.6, 35.0, h_top=10.0, h_bottom=10.0, h_side=10.0)
        for lay in range(1, 5):
            p.add_zone(lay, rect=(0, 0, 20, 20))
        p.add_heater(1, 1.0, rect=(7, 7, 13, 13), role="source")
        for x in (8.8, 9.6, 10.4, 11.2):
            for y in (8.8, 9.6, 10.4, 11.2):
                p.add_via(x, y, 0.3, fill_k=0.3)
        if name == "plate":
            p.add_heatsink(4, 0.0, rect=(0, 0, 20, 20), thickness_mm=1.0, k=204.0, rho_cp=2.44e6, pad_thickness_mm=0.1, pad_k=3.0)
        return p
    if name == "two2":
        p = Problem.new(60, 40, 2, 1.6, 35.0, h_top=10.0, h_bottom=10.0, h_side=None)
        p.add_zone(1, rect=(0, 0, 60, 40))
        p.add_zone(2, rect=(0, 0, 60, 40))
        p.add_heater(1, 1.0, rect=(25, 15, 35, 25), role="source")
        return p
    if name == "disc":
        p = Problem.new(20, 20, 2, 1.6, 35.0, h_top=10.0, h_bottom=10.0, h_side=10.0)
        ang = np.linspace(0, 2 * np.pi, 361)[:-1]
        p.set_outline(np.column_stack([10 + 10 * np.cos(ang), 10 + 10 * np.sin(ang)]))
        p.add_zone(1, rect=(0, 0, 20, 20))
        p.add_zone(2, rect=(0, 0, 20, 20))
        p.add_heater(1, 1.0, rect=(8, 8, 12, 12), role="source")
        return p
    raise ValueError(name)


def periodise(times, z, rth, period, duty, p_on=1.0, p_off=0.0):
    """!
    @brief Peak and valley of the periodic state of a square wave by the program's own superposition on a step response (`profiles.wave_response`), so that the program's
           models and the finite-element response are post-processed by the same code.
    @param times Response times (s, increasing, without 0).
    @param z Response in K/W.
    @param rth Steady value K/W.
    @param period Period s.
    @param duty On fraction.
    @param p_on Power of the on stretch, W.
    @param p_off Power of the off stretch, W.
    @return Tuple (peak, valley) in K.
    """
    sys.path.insert(0, ROOT)
    from pcbthermal import profiles
    from pcbthermal.model import SquareWave
    resp = profiles.StepResponse("ref", np.asarray(times, float), np.atleast_2d(np.asarray(z, float)), np.array([float(rth)]))
    pk, vl = profiles.wave_response(resp, 0, SquareWave(p_on=p_on, period=period, duty=duty, p_off=p_off))
    return float(pk), float(vl)
