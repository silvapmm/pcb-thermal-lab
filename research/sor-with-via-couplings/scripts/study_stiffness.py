#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_stiffness.py
@brief Where does the lagged variant (a) stop converging, and why does the block variant (c) not? The critical stiffness of the via part on simple boards, and the real vias against it.
@details Parts:
         1. the critical factor s_c (bisection on 4000 sweeps: the residual must fall) of K = A + s K_via for the lone via, the row of three and the 3 x 3 array at the program's omega
            and at omega 1.5, for the lagged (a) and the block (c) variants;
         2. the same factor for the real vias: a copper-filled barrel against an open barrel (plating only), a 0.3 mm and a 0.8 mm drill, and the ratio of the via conductance to the
            stencil conductance of one cell (`g_v / g_cell`), the quantity that decides it;
         3. the spectral radius of the lagged sweep against s on the small unit cell (dense, N = 392);
         4. the block variant on hard layouts: a 0.8 mm copper-filled via and rows of vias whose footprints touch or overlap.
         Run from the repository root: `.venv/bin/python research/sor-with-via-couplings/scripts/study_stiffness.py` (a few minutes).
"""

import json
import os
import sys

import numpy as np
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import boards as bd                                                         # noqa: E402
import sorvia as sv                                                         # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")


def converges(net, variant, omega, sweeps=4000):
    """!
    @brief Does the residual of the true K keep falling over the second half of `sweeps` sweeps (and stay finite)?
    @param net The network (or a scaled copy).
    @param variant lagged or block.
    @param omega Relaxation factor (None: the program's).
    @param sweeps Number of sweeps tried.
    @return bool.
    """
    r = sv.solve_variant(net, variant, omega=omega, tol=1e-300, max_iter=sweeps)
    h = r["history"]
    # Convergence means a falling residual over the second half of the run (a slow but stable iteration, such as omega 1.5 on a fine grid, counts as convergent)
    return bool(np.isfinite(r["residual"]) and h[-1][1] < 0.95 * h[len(h) // 2][1])


def critical(net0, variant, omega):
    """!
    @brief Largest tested factor s of K_via for which the variant still converges (bisection on a logarithmic scale between 1 and 1e4; 0 when s = 1 already fails).
    @param net0 The network with s = 1.
    @param variant lagged or block.
    @param omega Relaxation factor.
    @return float s_c (np.inf when the variant converges at 1e4).
    """
    if not converges(bd.scaled(net0, 1.0), variant, omega):
        return 0.0
    if converges(bd.scaled(net0, 1e4), variant, omega):
        return float("inf")
    lo, hi = 1.0, 1e4
    for _ in range(14):
        mid = np.sqrt(lo * hi)
        if converges(bd.scaled(net0, mid), variant, omega):
            lo = mid
        else:
            hi = mid
    return float(lo)


def part1(save):
    """!
    @brief Critical factors on the simple boards.
    @param save dict for the numbers.
    @return None.
    """
    print("\n1. Critical stiffness s_c of K = A + s K_via (copper-filled vias; s = 1 is the real via)")
    print("| board | cell (mm) | omega | lagged (a) s_c | block (c) s_c |")
    print("| :-- | --: | --: | --: | --: |")
    P = bd.pc
    for name, prob, cell in (("lone via, 2 layers", P.lone_via_board(10.0, 0.3, 385.0), 0.5), ("lone via, 2 layers", P.lone_via_board(10.0, 0.3, 385.0), 0.25),
                             ("row of 3 vias", P.row_board(n=3, fill_k=385.0), 0.5), ("3 x 3 array", P.array_board(385.0), 0.5), ("3 x 3 array", P.array_board(385.0), 0.25)):
        net = bd.net_for(prob, cell)
        for om in (None, 1.5):
            sl = critical(net, "lagged", om)
            sb = critical(net, "block", om)
            label = "program's" if om is None else om
            print(f"| {name} | {cell} | {label} | {sl:.2f} | {sb:.3g} |", flush=True)
            save[f"{name} {cell} {label}"] = [sl, sb]


def part2(save):
    """!
    @brief Real vias against the critical factor: g_via / g_cell and s_c for open and filled barrels and two drills on the 3 x 3 board (0.5 mm cell).
    @param save dict for the numbers.
    @return None.
    """
    print("\n2. Real vias: the via conductance against the stencil, and the lagged variant on each (3 x 3 array, 0.5 mm, program's omega)")
    print("| via | barrel conductance G_v per gap (W/K) | G_v / copper-plane stencil conductance g_x | lagged converges | s_c (lagged) |")
    print("| :-- | --: | --: | :-- | --: |")
    P = bd.pc
    for label, fill, dia in (("0.3 mm open (plating 25 um)", 0.0, 0.3), ("0.3 mm copper-filled", 385.0, 0.3), ("0.8 mm open", 0.0, 0.8), ("0.8 mm copper-filled", 385.0, 0.8)):
        prob = P.array_board(fill, diameter_mm=dia)
        net = bd.net_for(prob, 0.5)
        _, B, Gm = sv.via_operator(net)
        gv = float(Gm.diagonal().max())                                    # largest diagonal of the Laplacian blocks: the strongest barrel coupling
        gx = float(sv.stencil_parts(net)["g"][1].max())                    # largest in-plane stencil conductance of one cell
        ok = converges(bd.scaled(net, 1.0), "lagged", None)
        sc = critical(net, "lagged", None)
        print(f"| {label} | {gv:.3e} | {gv / gx:.3f} | {ok} | {sc:.2f} |", flush=True)
        save[label] = [gv, gx, ok, sc]


def part3(save):
    """!
    @brief Spectral radius of the lagged and block sweeps against s on the unit cell (dense).
    @param save dict for the numbers.
    @return None.
    """
    print("\n3. Spectral radius of one sweep against s, unit cell with two layers, 0.25 mm (N = 392), program's omega")
    print("| s | lagged (a) | block (c) | program rule (s only changes the diagonal it keeps) |")
    print("| --: | --: | --: | --: |")
    net0 = bd.net_for(bd.pc.unit_cell_board(3.5, 0.3, 385.0, layers=2), 0.25)
    n = net0.K.shape[0]
    rows = {}
    for s in (0.1, 1.0, 3.0, 10.0, 100.0):
        net = bd.scaled(net0, s)
        out = []
        for kw in ({"Kv": sv.via_matrix(net)}, {"blocks": sv.via_blocks(net)}, {}):
            rb = sv.RB(net, **kw)
            G = np.zeros((n, n))
            z = np.zeros(rb.shape)
            for i in range(n):
                e = np.zeros(n)
                e[i] = 1.0
                G[:, i] = rb.sweep(e.reshape(rb.shape), z).ravel()
            out.append(float(np.abs(np.linalg.eigvals(G)).max()))
        rows[s] = out
        print(f"| {s:g} | {out[0]:.5f} | {out[1]:.5f} | {out[2]:.5f} |", flush=True)
    save["rho"] = {str(k): v for k, v in rows.items()}


def part4(save):
    """!
    @brief The block variant where the lagged one fails and where footprints touch or overlap (blocks merge or sit side by side).
    @param save dict for the numbers.
    @return None.
    """
    print("\n4. Block variant (c) on hard layouts: sweeps to 1e-9 against the board without vias, and the field difference from the direct solver")
    print("| layout | cell (mm) | N | via blocks (cells each) | no-via sweeps | lagged | block | block - direct (K) |")
    print("| :-- | --: | --: | :-- | --: | :-- | --: | --: |")
    P = bd.pc
    layouts = [("3 x 3, 0.8 mm copper-filled", P.array_board(385.0, diameter_mm=0.8), 0.5),
               ("row of 5, pitch 0.5 mm", P.row_board(n=5, pitch_mm=0.5, fill_k=385.0), 0.25),
               ("row of 5, pitch 0.4 mm (footprints overlap)", P.row_board(n=5, pitch_mm=0.4, fill_k=385.0), 0.5)]
    for name, prob, cell in layouts:
        net = bd.net_for(prob, cell)
        th, _ = net.solve_steady("direct")
        base_net = bd.net_for(bd.without_vias(prob), cell, "point")
        base = sv.RB(base_net).solve(base_net.Q, 1e-9, 200000)
        sizes = [len(b) for b in sv.via_blocks(net)]
        rl = sv.solve_variant(net, "lagged", max_iter=30000)
        rb = sv.solve_variant(net, "block", max_iter=200000)
        lag = f"{rl['iterations']}" if rl["converged"] else "no conv."
        print(f"| {name} | {cell} | {net.K.shape[0]} | {len(sizes)} blocks of {min(sizes)}-{max(sizes)} | {base['iterations']} | {lag} | {rb['iterations']}{'' if rb['converged'] else ' (no conv.)'} | {np.abs(rb['theta'] - th).max():.1e} |", flush=True)
        save[name] = [base["iterations"], rl["iterations"] if rl["converged"] else None, rb["iterations"], float(np.abs(rb["theta"] - th).max())]


def main():
    """!
    @brief Run the three parts and save out/study_stiffness.json.
    @return None.
    """
    bd.pc.load_libraries()
    save = {}
    for f in (part1, part2, part3, part4):
        f(save)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "study_stiffness.json"), "w") as fh:
        json.dump(save, fh)


if __name__ == "__main__":
    main()
