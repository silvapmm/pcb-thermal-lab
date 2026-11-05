#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file s3boards.py
@brief Boards and runners of the study S3 (Young's relaxation factor): plates of the program from the simplest to the example board, the program's own SOR with a given omega, and the
       block SOR (c') of research/sor-with-via-couplings for the mean-potential via couplings.
@details The boards are built with the program's `Problem` API and its own `fvm.Network` (the program is imported, never edited). `net_program` gives the network of the program as
         it is (point treatment of the vias: the matrix is a pure stencil, so the program's `solve_sor` iterates the true matrix), `net_meanpot` the network with the
         mean-potential via treatment installed on in-memory copies (`sor-with-via-couplings/lib/boards.py`). `sweeps_program` runs `Network.solve_sor(omega)` of the program,
         `sweeps_block` the variant (c') with the colours and the via blocks relaxed by the same omega.
"""

import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RESEARCH = os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.dirname(RESEARCH)
for p in (ROOT, HERE, os.path.join(RESEARCH, "sor-with-via-couplings", "lib"), os.path.join(RESEARCH, "point-via-convergence", "lib")):
    if p not in sys.path:
        sys.path.insert(0, p)

from pcbthermal import fvm                                                  # noqa: E402
from pcbthermal.model import Materials, Problem                            # noqa: E402
from pcbthermal.project import load_project                                 # noqa: E402


def load_libraries():
    """!
    @brief Load the program's shipped libraries (as the application does).
    @return None.
    """
    import program_cases as pc
    pc.load_libraries()


def plate(layers=2, side_mm=40.0, h_top=10.0, h_bottom=10.0, h_side=None, fill=1.0, power=1.0, source_mm=8.0, vias=0, via_pitch_mm=2.0, fill_k=0.0):
    """!
    @brief A square board with copper zones on every layer, a square source in the middle and an optional square array of vias under it.
    @param layers Copper layers.
    @param side_mm Board side in mm.
    @param h_top Top film coefficient in W/m2K.
    @param h_bottom Bottom film coefficient in W/m2K.
    @param h_side Edge coefficient in W/m2K (None: the program's default).
    @param fill Copper fill fraction of every zone.
    @param power Source power in W.
    @param source_mm Side of the source in mm.
    @param vias Vias per side of the array (0: none).
    @param via_pitch_mm Pitch of the array in mm.
    @param fill_k Via fill conductivity in W/mK.
    @return Problem.
    """
    p = Problem.new(side_mm, side_mm, layers, 1.6, 35.0, h_top=h_top, h_bottom=h_bottom, h_side=h_side, materials=Materials(k_fr4_inplane=0.3))
    for layer in range(1, layers + 1):
        p.add_zone(layer, rect=(0, 0, side_mm, side_mm), fill=fill)
    c = side_mm / 2
    p.add_heater(1, power, rect=(c - source_mm / 2, c - source_mm / 2, c + source_mm / 2, c + source_mm / 2))
    h = (vias - 1) / 2
    for i in range(vias):
        for j in range(vias):
            p.add_via(c + (i - h) * via_pitch_mm, c + (j - h) * via_pitch_mm, 0.3, fill_k=fill_k)
    return p


def partial_copper(layers=4, side_mm=40.0):
    """!
    @brief A board whose inner layers have copper only on the left half and a ragged fill (0.5 on the right quarter): a strongly non-uniform stencil.
    @param layers Copper layers (at least 3).
    @param side_mm Board side in mm.
    @return Problem.
    """
    p = Problem.new(side_mm, side_mm, layers, 1.6, 35.0, h_top=10.0, h_bottom=10.0, h_side=None, materials=Materials(k_fr4_inplane=0.3))
    p.add_zone(1, rect=(0, 0, side_mm, side_mm))
    p.add_zone(layers, rect=(0, 0, side_mm, side_mm), fill=0.7)
    for layer in range(2, layers):
        p.add_zone(layer, rect=(0, 0, side_mm / 2, side_mm))
        p.add_zone(layer, rect=(side_mm / 2, 0, 3 * side_mm / 4, side_mm), fill=0.5)
    c = side_mm / 2
    p.add_heater(1, 1.0, rect=(c - 4, c - 4, c + 4, c + 4))
    return p


def round_board(layers=2, diameter_mm=40.0, n=72):
    """!
    @brief A round board (a polygon outline) with full copper and a source in the middle: cells off the board are pinned to the ambient.
    @param layers Copper layers.
    @param diameter_mm Diameter in mm.
    @param n Vertices of the outline.
    @return Problem.
    """
    p = plate(layers, diameter_mm)
    c, r = diameter_mm / 2, diameter_mm / 2
    p.set_outline([[c + r * math.cos(2 * math.pi * i / n), c + r * math.sin(2 * math.pi * i / n)] for i in range(n)])
    return p


def example_board():
    """!
    @brief The example board of the program (100 x 80 mm, parts, a heatsink without thickness, nine vias).
    @return Problem.
    """
    prob = load_project(os.path.join(ROOT, "examples", "example_board.pcbt.json")).problem
    for s in prob.heatsinks:
        if s.is_block():
            raise ValueError("the example board has a metal block: SOR does not support blocks")
    return prob


def net_program(problem, cell_mm):
    """!
    @brief The program's own network (point treatment of the vias).
    @param problem A Problem.
    @param cell_mm Target cell in mm.
    @return fvm.Network.
    """
    nx = max(int(round(problem.board.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(problem.board.height * 1000.0 / cell_mm)), 2)
    # ladder=False: the network of the versions before the laminate nodes, whose vertical links join consecutive layers (the stencil of sorvia.py assumes it)
    return fvm.Network(problem, nx, ny, ladder=False)


def net_meanpot(problem, cell_mm):
    """!
    @brief The network with the mean-potential via treatment (in-memory copies; see research/sor-with-via-couplings).
    @param problem A Problem.
    @param cell_mm Target cell in mm.
    @return fvm.Network with the via part in K.
    """
    import boards as bd
    return bd.net_for(problem, cell_mm)


def direct_seconds(net):
    """!
    @brief Wall time of the direct solve of a network (the cost the SOR has to beat) and its solution.
    @param net fvm.Network.
    @return Tuple (seconds, theta).
    """
    t0 = time.perf_counter()
    theta, _ = net.solve_steady("direct")
    return time.perf_counter() - t0, theta


def sweeps_program(net, omega, tol=1e-9, max_iter=60000):
    """!
    @brief Sweeps of the program's `Network.solve_sor` at a given omega (a pure-stencil matrix only).
    @param net fvm.Network built with the program's point treatment.
    @param omega Relaxation factor (None: the program's formula).
    @param tol Residual tolerance.
    @param max_iter Sweep limit.
    @return dict(iterations, converged, residual, seconds, theta).
    """
    t0 = time.perf_counter()
    theta, res, info = net.solve_sor(omega=omega, tol=tol, max_iter=max_iter)
    return {"iterations": int(info["iterations"]), "converged": bool(info["converged"]), "residual": float(res), "seconds": time.perf_counter() - t0, "theta": theta}


def sweeps_block(net, omega, tol=1e-9, max_iter=60000):
    """!
    @brief Sweeps of the block SOR (c') on a mean-potential network: colours and via blocks relaxed by omega, blocks coloured.
    @param net fvm.Network with the mean-potential treatment.
    @param omega Relaxation factor.
    @param tol Residual tolerance.
    @param max_iter Sweep limit.
    @return dict as `sorvia.RB.solve`.
    """
    import sorvia as sv
    return sv.RB(net, omega=omega, blocks=sv.via_blocks(net), block_omega=None, colour_blocks=True).solve(net.Q, tol, max_iter)


def adaptive_run(net, omega0=None, window=40, stages=3, tol=1e-9, max_iter=60000, blocks=False):
    """!
    @brief Red-black SOR whose omega is re-estimated from the decay of its own corrections (no extra product with K).
    @details After each of `stages` windows of sweeps the geometric mean decay of the last half window gives lambda, Young's relation gives mu and omega = 2 / (1 + sqrt(1 - mu^2))
             (`young.adaptive_omega`). Sweeps spent in the windows count: they reduce the error too. Omega is only ever raised (below the optimum the decay is a valid probe).
    @param net An assembled network.
    @param omega0 First relaxation factor (None: the program's formula).
    @param window Sweeps per window.
    @param stages Number of re-estimates.
    @param tol Residual tolerance.
    @param max_iter Sweep limit.
    @param blocks True: the via blocks of the mean-potential network are used (variant c').
    @return dict(iterations, converged, omegas (list), residual).
    """
    import sorvia as sv
    import young as yg
    om = yg.omega_program(net.nx, net.ny) if omega0 is None else omega0
    rb = sv.RB(net, omega=om, blocks=sv.via_blocks(net) if blocks else None, block_omega=None, colour_blocks=True)
    q = np.asarray(net.Q, float).reshape(rb.shape)
    qn = max(np.linalg.norm(q), 1e-300)
    theta = np.zeros(rb.shape)
    steps, omegas, done = [], [om], 0
    for it in range(1, max_iter + 1):
        new = rb.sweep(theta, q)
        steps.append(float(np.linalg.norm(new - theta)))
        theta = new
        if done < stages and it % window == 0:
            w_new, _mu, _lam = yg.adaptive_omega(steps[-window // 2:], rb.omega)
            if w_new > rb.omega:
                rb.omega = rb.block_omega = w_new
                omegas.append(w_new)
            done += 1
        if it % 10 == 0:
            res = float(np.linalg.norm(net.K @ theta.ravel() - q.ravel()) / qn)
            if res < tol:
                return {"iterations": it, "converged": True, "omegas": omegas, "residual": res}
    return {"iterations": max_iter, "converged": False, "omegas": omegas, "residual": float("nan")}


def best_omega(run, lo, hi, n_coarse=9, n_fine=7, max_iter=60000):
    """!
    @brief The measured best omega in [lo, hi] by a coarse grid and a refinement around the best point (sweeps to the tolerance, not-converged counted as max_iter).
    @param run Function omega -> iterations.
    @param lo Lower end.
    @param hi Upper end (< 2).
    @param n_coarse Points of the first grid.
    @param n_fine Points of the second grid.
    @param max_iter Value used for a run that did not converge (the callable should return it).
    @return Tuple (omega_best, iterations_best, table) with table the list of (omega, iterations).
    """
    table = []
    for w in np.linspace(lo, hi, n_coarse):
        table.append((float(w), int(run(float(w)))))
    w0 = min(table, key=lambda t: t[1])[0]
    step = (hi - lo) / (n_coarse - 1)
    for w in np.linspace(max(w0 - step, lo), min(w0 + step, hi), n_fine):
        table.append((float(w), int(run(float(w)))))
    table.sort()
    wb = min(table, key=lambda t: t[1])
    return wb[0], wb[1], table
