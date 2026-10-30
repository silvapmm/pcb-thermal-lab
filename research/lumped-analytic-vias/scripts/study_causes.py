#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_causes.py
@brief Which cause explains the overstated via effect of the Lumped and Analytic models? Four causes separated on boards that have only that cause.
@details Part 1 (a, the constriction): the unit cell of a via lattice solved as a ONE-cell network written here (no program): sheets joined by the dielectric and by the barrels, with and
         without the Krogh constriction in every sheet. Without it the answer is the lumped model without a constriction; the Lumped model of the program must reproduce it, and the
         difference to the fine-grid reference is the whole error. With it the closed form predicts the reference; no model is involved.
         Part 2 (b, the radius of the barrel and the 3D floor): the target radius eta = r_t / r_v of the equivalent sink (1.0, 0.78, 0.6) in the closed form of part 1 against the fine-grid
         layered reference and against the 3D solver with the barrel drawn (the floor of the layered idealisation).
         Part 3 (c, neighbours and clusters): a n x n cluster (n = 1, 2, 3) of 0.3 mm vias at 1 mm pitch in the middle of an 8 mm cell heated everywhere: the micro cell of a via is the
         Wigner-Seitz cell of its neighbours, the cluster as a whole is a second, larger constriction; the Lumped without, with the micro cell and with the cluster, and the Analytic.
Usage: python research/lumped-analytic-vias/scripts/study_causes.py   (from the repository root; about 2 minutes)
"""

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import constriction as cr                                                    # noqa: E402
import harness as hz                                                         # noqa: E402
import program_cases as pc                                                   # noqa: E402
import cases                                                                 # noqa: E402


def one_cell(par, pitch, eta, constriction, no_via=False):
    """!
    @brief The unit cell as one node per sheet: the closed-form model with or without the constriction of the vias.
    @param par layer_parameters of the unit-cell board (one via).
    @param pitch Cell side in m.
    @param eta r_t / r_v.
    @param constriction True: a Krogh well in every sheet; False: the sheets meet the barrel directly.
    @param no_via True: the board without the via.
    @return float Rise of the top node in K (the source is the whole top).
    """
    L = len(par["S"])
    area = pitch * pitch
    g_adj = np.asarray(par["gz_area"]) * area
    K = np.zeros((L, L))

    def link(a, b, g):
        K[a, a] += g
        K[b, b] += g
        K[a, b] -= g
        K[b, a] -= g
    for l in range(L - 1):
        link(l, l + 1, g_adj[l])
    if not no_via:
        g_gap = np.asarray(par["gv"][0])
        if constriction:
            r_cell = pitch / math.sqrt(math.pi)
            a = eta * par["r_via"][0]
            g_well = np.array([1.0 / cr.krogh(par["S"][l], r_cell, a) for l in range(L)])
            G = cr.kron_barrel(g_gap, g_well)
            for l in range(L):
                for m in range(l + 1, L):
                    if G[l, m] != 0:
                        link(l, m, G[l, m])
        else:
            for l in range(L - 1):
                link(l, l + 1, g_gap[l])
    K[0, 0] += par["h_top"] * area
    K[L - 1, L - 1] += par["h_bottom"] * area
    q = np.zeros(L)
    q[0] = 1.0
    return float(np.linalg.solve(K, q)[0])


def part1():
    """!
    @brief Part 1: the closed forms against the fine-grid reference and the Lumped model of the program.
    @return None.
    """
    print("## 1. The constriction (unit cell): one-cell closed form against the reference and the program\n")
    print("| layers | drill | pitch | fill | E_ref K | E no constriction K | Lumped program K | E with Krogh K | error no constr % | error program % | error Krogh % |")
    print("| --: | --: | --: | :-- | --: | --: | --: | --: | --: | --: | --: |")
    pc.load_libraries()
    for layers in (2, 4):
        for dia in (0.3, 0.6):
            for pitch in (2, 4, 8):
                for fill in (0.0, 385.0):
                    prob = cases.unit_cell(pitch, dia, fill, layers=layers)
                    e_ref, _, _ = hz.reference_uniform(prob, 1.0 / 16)
                    par = pc.layer_parameters(prob)
                    t0 = one_cell(par, pitch * 1e-3, 1.0, False, no_via=True)
                    e_nc = t0 - one_cell(par, pitch * 1e-3, 1.0, False)
                    e_kr = t0 - one_cell(par, pitch * 1e-3, cr.ETA, True)
                    e_lp = hz.effect(prob, "lumped", hz.VARIANTS["L_prog"][1], 0.5)
                    print(f"| {layers} | {dia} | {pitch} | {'Cu' if fill else 'open'} | {e_ref:.2f} | {e_nc:.2f} | {e_lp:.2f} | {e_kr:.2f} | {100 * (e_nc / e_ref - 1):+.1f} | "
                          f"{100 * (e_lp / e_ref - 1):+.1f} | {100 * (e_kr / e_ref - 1):+.1f} |")


def part2():
    """!
    @brief Part 2: the radius of the sink and the floor of the layered idealisation (3D solver with the barrel drawn).
    @return None.
    """
    print("\n## 2. The radius of the barrel and the 3D floor (unit cell, closed form with the Krogh constriction)\n")
    print("| layers | drill | pitch | fill | E_ref 2D K | E_3D K | 3D vs 2D % | eta 1.0 % | eta 0.78 % | eta 0.6 % |")
    print("| --: | --: | --: | :-- | --: | --: | --: | --: | --: | --: |")
    for layers in (2, 4):
        for dia in (0.3, 0.6):
            for pitch in (4, 8):
                for fill in (0.0, 385.0):
                    prob = cases.unit_cell(pitch, dia, fill, layers=layers)
                    e_ref, _, _ = hz.reference_uniform(prob, 1.0 / 16)
                    e3 = hz.reference_3d_uniform(prob, 1.0 / 16)
                    par = pc.layer_parameters(prob)
                    t0 = one_cell(par, pitch * 1e-3, 1.0, False, no_via=True)
                    errs = [100 * ((t0 - one_cell(par, pitch * 1e-3, eta, True)) / e_ref - 1) for eta in (1.0, cr.ETA, 0.6)]
                    print(f"| {layers} | {dia} | {pitch} | {'Cu' if fill else 'open'} | {e_ref:.2f} | {e3:.2f} | {100 * (e3 / e_ref - 1):+.1f} | " + " | ".join(f"{e:+.1f}" for e in errs) + " |")


def cluster_board(n, pitch=1.0, side=8.0, dia=0.3, fill=385.0, layers=2):
    """!
    @brief An n x n cluster of vias in the middle of a square cell heated everywhere on the top.
    @param n Vias per side.
    @param pitch Cluster pitch in mm.
    @param side Cell side in mm.
    @param dia Drill in mm.
    @param fill Fill conductivity.
    @param layers Layers.
    @return Problem.
    """
    prob = cases.unit_cell(side, dia, fill, layers=layers)
    prob.vias = []
    c = side / 2
    h = (n - 1) / 2
    for i in range(n):
        for j in range(n):
            prob.add_via(c + (i - h) * pitch, c + (j - h) * pitch, dia, fill_k=fill)
    return prob


def part3():
    """!
    @brief Part 3: neighbours and clusters.
    @return None.
    """
    print("\n## 3. Neighbours: a n x n cluster at 1 mm pitch in an 8 mm cell (error of the via effect, percent)\n")
    print("| layers | fill | n | E_ref K | L_prog | L_ring (cell of the ring) | L_nn (micro cell only) | L_grp0 (micro + cluster) | L_grp (+ cap 0.75 fin length) | A_prog | A_on | A_bil | A_fin |")
    print("| --: | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |")
    names = ["L_prog", "L_ring", "L_nn", "L_grp0", "L_grp", "A_prog", "A_on", "A_bil", "A_fin"]
    for layers in (2, 4):
        for fill in (0.0, 385.0):
            for n in (1, 2, 3, 4):
                prob = cluster_board(n, fill=fill, layers=layers)
                e_ref, _, _ = hz.reference_uniform(prob, 1.0 / 16)
                errs = hz.errors(prob, e_ref, 0.5, names)
                print(f"| {layers} | {'Cu' if fill else 'open'} | {n * n} | {e_ref:.2f} | " + " | ".join(f"{errs[k]:+.1f}" for k in names) + " |")


def main():
    """!
    @brief Run the three parts.
    @return None.
    """
    part1()
    part2()
    part3()


if __name__ == "__main__":
    main()
