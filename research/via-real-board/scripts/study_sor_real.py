#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_sor_real.py
@brief S2: the block SOR (c') of sor-with-via-couplings on boards with 100 or more vias: sweeps against the direct solution, against the same board without vias, and the structure of the blocks.
@details Boards: own via fields (100 and 900 vias), the Stormduino (109 holes, 2 layers) and the Allegro board (283 holes, 4 layers) at the cells of --cells. For each: the direct
         solution (sparse LU), the block SOR (variant `block_over`: relaxed, coloured blocks) with the residual stop 1e-9, the sweeps, the largest difference of the field from the direct
         solution (K), the sweeps of the same board without vias (the stencil alone), the program's SOR rule on the same matrix (capped at --cap sweeps: it is expected not to converge,
         S2 repeats the failure on a real layout) and the block structure: number of blocks, largest block (unknowns, after merging overlapping footprints), the dense inverse
         memory (sum of size^2 x 8 bytes) and the greedy colours. Where footprints merge into a few huge blocks the dense inverse is the limit (printed as the memory it would need).
         A configuration is skipped when the dense inverses would need more than --max-inverse-gb. Sweep counts and memory are results; wall times are not recorded.
         Run from the repository root: `.venv/bin/python research/via-real-board/scripts/study_sor_real.py [--cells 1 0.5] [--cap 20000]`.
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import argparse
import logging

import numpy as np
import scipy.sparse.linalg as spla

import matrix_stats as ms
import real_board as rbd
import sorvia as sv
from pcbthermal import fvm


def direct(net):
    """!
    @brief The direct solution of K theta = Q.
    @param net An assembled fvm.Network.
    @return numpy.ndarray (L, ny, nx).
    """
    return spla.spsolve(net.K.tocsc(), net.Q.ravel(), permc_spec=fvm.ORDERING).reshape(net.nl, net.ny, net.nx)


def main(argv=None):
    """!
    @brief Print the SOR table.
    @param argv Command line.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", type=float, nargs="+", default=[1.0, 0.5])
    ap.add_argument("--cap", type=int, default=20000)
    ap.add_argument("--only", nargs="*", default=None, help="run only the boards with these names (alleg, storm, own 100, own 900)")
    ap.add_argument("--max-inverse-gb", type=float, default=2.0)
    a = ap.parse_args(argv)
    logging.disable(logging.WARNING)
    import program_cases as pc
    pc.load_libraries()
    sets = []
    for name, spec in rbd.BOARDS.items():
        try:
            sets.append((name,) + rbd.holes_of(name) + (spec["layers"],))
        except FileNotFoundError as e:
            print("skipped:", e)
    sets += [(f"own {n * n}",) + rbd.own_via_field(n) + (4,) for n in (10, 30)]
    print("| board | cell (mm) | unknowns | blocks (largest, colours) | inverse memory (MB) | block SOR sweeps | max diff to direct (K) | sweeps without vias | program's rule: converged / diff to direct (K) |")
    print("| :-- | --: | --: | :-- | --: | --: | --: | --: | :-- |")
    for name, holes, w, h, layers in sets:
        if a.only and name not in a.only:
            continue
        p = rbd.problem_from_holes(holes, w, h, layers=layers)
        for c in a.cells:
            net = ms.build(p, c, "mw", board_only=True, image=False)
            bs = ms.block_structure(net)
            if bs["inverse_bytes"] / 1e9 > a.max_inverse_gb:
                print(f"| {name} | {c:g} | {net.K.shape[0]:,} | {bs['blocks']} ({bs['largest_block']}, {bs['colours']}) | {bs['inverse_bytes'] / 1e6:.0f} | skipped (> {a.max_inverse_gb:g} GB) | | | | |", flush=True)
                continue
            ref = direct(net)
            blk = sv.solve_variant(net, "block_over", max_iter=a.cap)
            prog = sv.solve_variant(net, "program", max_iter=a.cap)
            net0 = ms.build(rbd.problem_from_holes([], w, h, layers=layers, center=(rbd.densest_window(holes, 8.0, w, h)[:2])), c, "program")
            base = sv.solve_variant(net0, "program", max_iter=a.cap * 4)
            print(f"| {name} | {c:g} | {net.K.shape[0]:,} | {bs['blocks']} ({bs['largest_block']}, {bs['colours']}) | {bs['inverse_bytes'] / 1e6:.0f} | "
                  f"{blk['iterations']}{'' if blk['converged'] else ' (not converged)'} | {np.abs(blk['theta'] - ref).max():.1e} | {base['iterations']}{'' if base['converged'] else ' (not converged)'} | "
                  f"{prog['converged']} / {np.abs(prog['theta'] - ref).max():.1f} |", flush=True)


if __name__ == "__main__":
    main()
