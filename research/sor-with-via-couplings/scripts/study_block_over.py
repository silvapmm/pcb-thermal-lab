#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_block_over.py
@brief Review: does the block SOR keep the speed of the board without vias when the vias are many and their footprints touch, and what relaxation factor should the SOR use?
@details Compares, on the program's networks with the treatment `mw_disc@eta` (built on in-memory copies by `boards.net_for`):
         `block` (c, the prototype of the study: all blocks at once, block step not relaxed) and `block_over` (c', the review: blocks coloured so that no two blocks of a group
         are coupled, groups in turn, each block step relaxed by the same omega as the colours), against the program's SOR on the same board without vias.
         Part 1: boards from sparse to dense vias (the 3 x 3 array of the study; dense 9 x 9 arrays whose footprints touch in x and y; the example board).
         Part 2: the relaxation factor on the 3 x 3 array: the program's formula, the optimum of Young's theory for the stencil
         `2 / (1 + sqrt(1 - rho_J^2))` with rho_J the spectral radius of the Jacobi iteration of the board without vias (computed with eigsh), and a sweep of omega.
         Part 3: `block_over` at 1e4 times the via stiffness.
         The tables are saved to out/study_block_over.json for `make_figures.py` (figure 08).
         Run from the repository root: `.venv/bin/python research/sor-with-via-couplings/scripts/study_block_over.py` (about five minutes).
"""

import json
import os
import sys
import warnings

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import boards as bd                                                         # noqa: E402
import sorvia as sv                                                         # noqa: E402
from pcbthermal import fvm                                                  # noqa: E402
from pcbthermal.examples import example_board                               # noqa: E402

warnings.filterwarnings("ignore", category=FutureWarning)                   # scipy's spmatrix notice in sp.block_diag


def rho_jacobi(K):
    """!
    @brief Spectral radius of the point Jacobi iteration of a symmetric matrix with positive diagonal: 1 - lambda_min(D^-1/2 K D^-1/2).
    @param K Sparse symmetric matrix.
    @return float.
    """
    d = 1.0 / np.sqrt(K.diagonal())
    Ks = sp.diags(d) @ K @ sp.diags(d)
    lam_min = spla.eigsh(Ks.tocsc(), k=1, sigma=0.0, which="LM", return_eigenvectors=False)[0]
    lam_max = spla.eigsh(Ks.tocsc(), k=1, which="LA", return_eigenvectors=False)[0]
    return float(max(1.0 - lam_min, lam_max - 1.0))


def young_omega(K):
    """!
    @brief Optimal SOR factor of Young's theory for a consistently ordered matrix (the stencil in red-black order): 2 / (1 + sqrt(1 - rho_J^2)).
    @param K Sparse symmetric matrix of the stencil.
    @return Tuple (rho_J, omega).
    """
    r = rho_jacobi(K)
    return r, 2.0 / (1.0 + np.sqrt(1.0 - r * r))


def novia_net(problem, cell_mm):
    """!
    @brief The program's own network of the problem without vias (no patch: the program's code).
    @param problem A Problem.
    @param cell_mm Cell size in mm.
    @return fvm.Network.
    """
    p = bd.without_vias(problem)
    nx = max(int(round(p.board.width * 1000.0 / cell_mm)), 2)
    ny = max(int(round(p.board.height * 1000.0 / cell_mm)), 2)
    return fvm.Network(p, nx, ny)


def part1(save):
    """!
    @brief Sparse to dense vias: sweeps of the board without vias, of `block` and of `block_over`, with the program's omega.
    @param save Dict that receives the rows (key part1).
    @return None.
    """
    P = bd.pc
    cases = [("3 x 3 array, 0.3 mm filled, pitch 3.5 mm", P.array_board(385.0), 0.5),
             ("3 x 3 array, 0.3 mm filled, pitch 3.5 mm", P.array_board(385.0), 0.25),
             ("9 x 9 array, 0.3 mm filled, pitch 0.5 mm (footprints touch)", P.array_board(385.0, pitch_mm=0.5, n=9), 0.25),
             ("9 x 9 array, 0.3 mm filled, pitch 0.75 mm", P.array_board(385.0, pitch_mm=0.75, n=9), 0.25),
             ("9 x 9 array, 0.3 mm filled, pitch 1.0 mm", P.array_board(385.0, pitch_mm=1.0, n=9), 0.5),
             ("example board", example_board(), 1.0)]
    print("1. Sweeps to a residual of 1e-9 with the program's omega; field difference from the direct solver")
    print("| board | cell (mm) | N | blocks (groups) | via cells | no-via | block (c) | block_over (c') | (c') - direct (K) |")
    print("| :-- | --: | --: | --: | --: | --: | --: | --: | --: |")
    for name, prob, cell in cases:
        net = bd.net_for(prob, cell)
        th = net.solve_steady("direct")[0]
        nv = novia_net(prob, cell).solve_sor()[2]["iterations"]
        blocks = sv.via_blocks(net)
        rb = sv.RB(net, blocks=blocks, block_omega=None, colour_blocks=True)
        c = sv.solve_variant(net, "block", max_iter=60000)
        co = rb.solve(net.Q, 1e-9, 60000)
        ncell = sum(len(b) for b in blocks)
        save.setdefault("part1", []).append({"name": name, "cell": cell, "novia": nv, "block": c["iterations"] if c["converged"] else None,
                                             "block_over": co["iterations"] if co["converged"] else None})
        print(f"| {name} | {cell} | {net.K.shape[0]} | {len(blocks)} ({len(rb.groups)}) | {ncell} | {nv} | {c['iterations']}{'' if c['converged'] else ' (no conv.)'} | "
              f"{co['iterations']}{'' if co['converged'] else ' (no conv.)'} | {np.abs(co['theta'] - th).max():.1e} |", flush=True)


def part2(save):
    """!
    @brief The relaxation factor on the 3 x 3 array at 0.5 mm: formula, Young's optimum of the stencil, measured sweeps.
    @param save Dict that receives the rows (keys part2, omega_program, omega_young).
    @return None.
    """
    prob = bd.pc.array_board(385.0)
    net = bd.net_for(prob, 0.5)
    nvn = novia_net(prob, 0.5)
    w_prog = 2.0 / (1.0 + np.sin(np.pi / max(net.nx, net.ny)))
    rJ, w_y = young_omega(nvn.K)
    print()
    print(f"2. Relaxation factor, 3 x 3 array, 0.5 mm: program's formula {w_prog:.4f}; rho_J of the board without vias {rJ:.6f}, Young's optimum {w_y:.4f}")
    save["omega_program"], save["omega_young"] = float(w_prog), float(w_y)
    print("| omega | no-via | block (c) | block_over (c') |")
    print("| --: | --: | --: | --: |")
    for w in (w_prog, 1.9, 1.95, 1.97, w_y, 1.98, 1.99):
        nv = nvn.solve_sor(omega=w, max_iter=20000)[2]
        c = sv.solve_variant(net, "block", omega=w, max_iter=20000)
        co = sv.solve_variant(net, "block_over", omega=w, max_iter=20000)
        f = lambda r, it, ok: str(it) if ok else "-"                       # noqa: E731
        save.setdefault("part2", []).append({"omega": float(w), "novia": nv["iterations"] if nv["converged"] else None,
                                             "block": c["iterations"] if c["converged"] else None, "block_over": co["iterations"] if co["converged"] else None})
        print(f"| {w:.4f} | {f(None, nv['iterations'], nv['converged'])} | {f(None, c['iterations'], c['converged'])} | {f(None, co['iterations'], co['converged'])} |",
              flush=True)
    for name, prob, cell in (("example board", example_board(), 1.0), ("3 x 3 array", bd.pc.array_board(385.0), 0.25)):
        nvn = novia_net(prob, cell)
        rJ, w_y = young_omega(nvn.K)
        a = nvn.solve_sor()[2]
        b = nvn.solve_sor(omega=w_y)[2]
        print(f"   {name}, {cell} mm, no vias: formula omega {a['omega']:.4f} -> {a['iterations']} sweeps; Young's omega {w_y:.4f} (rho_J {rJ:.6f}) -> {b['iterations']} sweeps",
              flush=True)


def part3():
    """!
    @brief `block_over` with the via part multiplied by 1e4 (3 x 3 array, 0.5 mm).
    @return None.
    """
    net = bd.net_for(bd.pc.array_board(385.0), 0.5)
    print()
    for s in (1.0, 1e4):
        sn = bd.scaled(net, s)
        th = spla.spsolve(sn.K.tocsc(), sn.Q.ravel()).reshape(sn.nl, sn.ny, sn.nx)
        r = sv.solve_variant(sn, "block_over", max_iter=60000)
        print(f"3. block_over, via stiffness x {s:g}: {r['iterations']} sweeps, converged {r['converged']}, max |field - direct| {np.abs(r['theta'] - th).max():.1e} K", flush=True)


def main():
    """!
    @brief Run the three parts and save out/study_block_over.json.
    @return None.
    """
    bd.pc.load_libraries()
    save = {}
    part1(save)
    part2(save)
    part3()
    out = os.path.join(os.path.dirname(HERE), "out")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "study_block_over.json"), "w") as fh:
        json.dump(save, fh)


if __name__ == "__main__":
    main()
