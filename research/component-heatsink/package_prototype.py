"""!
@file package_prototype.py
@brief Prototype (not part of the program): a power MOSFET on a copper pad as a simple heater and as a junction node, to see what the extra model changes.

The part is the Texas Instruments CSD17308Q3 (SON 3.3 x 3.3 mm). Datasheet numbers used: RthJC 4.5 K/W (junction to case, the drain pad), RthJA typical 46 and
maximum 58 K/W on 1 in2 of 2 oz copper on a 1.5 x 1.5 in, 1.52 mm FR-4 board, 165 K/W maximum on the minimum pad, Tj max 150 degC. The datasheet gives no
junction-to-top-of-case resistance; the top path is explored with assumed values.

Usage: python research/component-heatsink/package_prototype.py
"""

import os
import sys

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pcbthermal import Problem, convection, fvm          # noqa: E402

TJ_MAX = 150.0
PKG = 3.3                                   # Package body, mm
RTH_JC = 4.5                                # Junction to case (drain pad), K/W


def board(pad_mm):
    """!
    @brief The datasheet test board: 38.1 x 38.1 mm, 1.52 mm FR-4, 71 um copper on a square pad on the top, nothing below.
    @param pad_mm Side of the copper pad in mm (25.4 mm is 1 in2).
    @return Problem with a heater (3.3 mm) at the centre whose power is only used to build the footprint weights.
    """
    p = Problem.new(38.1, 38.1, 2)
    p.board.thickness = 1.52e-3
    p.board.copper_thickness = [71e-6, 71e-6]
    p.board.h_side = None                                     # Small board in still air: keep the faces only
    c = 38.1 / 2
    p.add_zone(1, rect=(c - pad_mm / 2, c - pad_mm / 2, c + pad_mm / 2, c + pad_mm / 2))
    p.add_heater(1, 1.0, rect=(c - PKG / 2, c - PKG / 2, c + PKG / 2, c + PKG / 2), name="Q1")
    return p


def solve(problem, power, theta_pad, model, top=None, cell_mm=0.5):
    """!
    @brief Steady temperatures of the board with the part modelled in one of two ways, with the heat transfer coefficients computed by iteration.
    @param problem Problem from board().
    @param power Dissipated power in W.
    @param theta_pad Junction-to-pad resistance in K/W.
    @param model "offset": the heat enters the board under the footprint and Tj = Tmax under the footprint + P theta;
                 "node": a junction node joined to the footprint by a uniform conductance 1/theta (the block-and-plate of JESD15-3).
    @param top Resistance in K/W from the junction to ambient through the top (model "node" only), None for no top path.
    @param cell_mm Cell size in mm.
    @return Dict with Tj, the board maximum, the footprint mean, the heat share through the top and the heat transfer coefficients.
    """
    b = problem.board
    nx, ny = int(round(b.width * 1000 / cell_mm)), int(round(b.height * 1000 / cell_mm))
    net = fvm.Network(problem, nx, ny)
    w = net.Qw[0].ravel()
    n = net.K.shape[0]
    ht, hb = b.h_top, b.h_bottom
    for _ in range(12):
        net.g_top[0] = ht * net.dx * net.dy
        net.g_bottom[-1] = hb * net.dx * net.dy
        net.g_amb = net.g_top + net.g_bottom + net.g_side + net.g_heatsink
        K = net._assemble().tolil()
        if model == "node":
            # Extra unknown (index n): the junction, joined to every footprint cell with w_i / theta
            K.resize((n + 1, n + 1))
            g = w / theta_pad
            rows = np.flatnonzero(w)
            for i in rows:
                K[i, i] += g[i]
                K[n, n] += g[i]
                K[i, n] -= g[i]
                K[n, i] -= g[i]
            if top is not None:
                K[n, n] += 1.0 / top
            rhs = np.zeros(n + 1)
            rhs[n] = power
        else:
            rhs = power * w
        x = spla.spsolve(K.tocsc(), rhs, permc_spec="MMD_AT_PLUS_A")
        theta = x[:n].reshape(net.nl, net.ny, net.nx)
        t = theta + b.ambient
        nt, nb, _ = convection.board_h(b, float(t[0].mean()), float(t[-1].mean()))
        done = abs(nt - ht) < 0.02 and abs(nb - hb) < 0.02
        ht, hb = nt, nb
        if done:
            break
    foot = w > 0
    t_foot_max = float(t.reshape(-1)[foot].max())
    if model == "node":
        tj = float(x[n] + b.ambient)
        top_share = float((x[n] / top) / power) if top else 0.0
    else:
        tj = t_foot_max + power * theta_pad
        top_share = 0.0
    return {"tj": tj, "foot_max": t_foot_max, "foot_mean": float((t.reshape(-1)[foot] * w[foot]).sum()), "board_max": float(t.max()),
            "top_share": top_share, "h": (ht, hb)}


def main():
    """!
    @brief Print the comparison tables.
    """
    amb = 25.0
    print("A. The datasheet's own test: RthJA on the test board (1 W)")
    print("   datasheet: typical 46, maximum 58 K/W on 1 in2; maximum 165 K/W on the minimum pad\n")
    print(f"   {'board':28s} {'model':8s} {'Tj':>6s} {'RthJA':>7s} {'Tfoot':>7s}")
    for name, pad in (("1 in2 pad (25.4 mm)", 25.4), ("5 mm pad (minimum, assumed)", 5.0)):
        p = board(pad)
        for model in ("offset", "node"):
            r = solve(p, 1.0, RTH_JC, model)
            print(f"   {name:28s} {model:8s} {r['tj']:6.1f} {(r['tj'] - amb):7.1f} {r['foot_max']:7.1f}")
    print("\nB. A real use: 2 W in the FET on the 1 in2 pad, without and with a heat heatsink on the package top")
    p = board(25.4)
    print(f"   {'case':44s} {'model':8s} {'Tj':>6s} {'Tj<=150?':>9s} {'top share':>10s}")
    # The datasheet gives no junction-to-top resistance: it is assumed (5, 20 and 40 K/W), plus 1 K/W of paste and a 12 K/W clip-on heat heatsink
    cases = [("no top path", None),
             ("bare mould: 30 K/W + 15 W/m2K on 3.3 mm (assumed)", 30.0 + 1.0 / (15 * (PKG * 1e-3) ** 2))]
    for jc_top in (40.0, 20.0, 5.0):
        cases.append((f"heat heatsink 12 K/W, theta_JC(top) = {jc_top:g} (assumed)", jc_top + 1.0 + 12.0))
    cases.append(("good heat heatsink 4 K/W, theta_JC(top) = 20 (assumed)", 20.0 + 1.0 + 4.0))
    for label, rt in cases:
        for model in ("offset", "node"):
            if model == "offset" and rt is not None:
                continue
            r = solve(p, 2.0, RTH_JC, model, top=rt)
            print(f"   {label:44s} {model:8s} {r['tj']:6.1f} {'yes' if r['tj'] <= TJ_MAX else 'NO':>9s} {100 * r['top_share']:9.1f} %")
    print("\nC. Sensitivity to the junction-to-pad resistance (2 W, 1 in2 pad, no top path)")
    for th in (1.1, 4.5, 8.0):
        r = solve(p, 2.0, th, "node")
        print(f"   theta = {th:4.1f} K/W   Tj = {r['tj']:6.1f} degC   footprint {r['foot_max']:6.1f}")


if __name__ == "__main__":
    main()
