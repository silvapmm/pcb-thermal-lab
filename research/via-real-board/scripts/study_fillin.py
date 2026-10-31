#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fillin.py
@brief S2: the size and fill-in of the matrix with the via couplings against the number of vias and the cell; where it breaks (thousands of vias).
@details Part 1 (scaling): the own via field (n x n thermal vias under a 7 x 7 mm pad on a 60 x 50 mm four-layer board) for n = 5, 10, 20, 30, 50, 70 (25 to 4900 vias) at the cells
         of --cells; for each, the program's matrix ("program": the vias are in the stencil) and the recommended treatment ("mw"): unknowns, non-zeros of K, via blocks, dense
         coupling entries, the footprint size, the non-zeros of the sparse LU factors with the program's ordering and the memory estimated from them (12 bytes per non-zero).
         A configuration is skipped, not built, when the estimated dense coupling entries exceed --max-dense (default 30 million) and its factorisation is skipped when K has more than
         --max-nnz entries (default 40 million); every skip is printed.
         Part 2 (real boards): the same counts on the Allegro board and the Stormduino at 1, 0.5 and 0.25 mm.
         Part 3 (spy data): the coarse sparsity pattern of K for n = 3 and n = 9 on a small board is saved to out/spy_*.npz for make_figures.py (the exact pattern of a large matrix
         cannot be drawn). Timings are NOT recorded; if --time is given, one factorisation time per configuration is printed as scaling on a quiet machine, never as a result.
         Run from the repository root: `.venv/bin/python research/via-real-board/scripts/study_fillin.py [--cells 1 0.5 0.25] [--time]`.
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import argparse
import logging

import numpy as np

import matrix_stats as ms
import paths
import real_board as rbd


def row(label, net, args):
    """!
    @brief One table row of counts for an assembled network.
    @param label Name of the configuration.
    @param net fvm.Network.
    @param args Parsed arguments (max_nnz, time).
    @return str Markdown row.
    """
    c = ms.matrix_counts(net)
    f = ms.lu_fill(net, args.max_nnz)
    lu = "skipped" if f is None else f"{f['nnz_LU']:,} ({f['fill_ratio']:.1f}x), {f['bytes_est'] / 1e9:.2f} GB"
    t = f" {ms.time_factor(net):.1f} s" if args.time and f is not None else ""
    return (f"| {label} | {c['unknowns']:,} | {c['nnz_K']:,} ({c['nnz_per_row']:.1f}/row) | {c['vias']} | {c['largest_footprint']} | {c['dense_entries']:,} | {lu}{t} |")


def main(argv=None):
    """!
    @brief Print the scaling tables and save the spy data.
    @param argv Command line.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", type=float, nargs="+", default=[1.0, 0.5, 0.25])
    ap.add_argument("--sides", type=int, nargs="+", default=[5, 10, 20, 30, 50, 70])
    ap.add_argument("--pitch", type=float, default=1.5, help="pitch of the growing array in mm")
    ap.add_argument("--pitch-sides", type=int, nargs="+", default=[10, 20, 30, 40, 50, 60, 70])
    ap.add_argument("--max-nnz", type=int, default=40_000_000)
    ap.add_argument("--max-dense", type=int, default=30_000_000, help="refuse to build a treatment whose estimated dense coupling entries exceed this")
    ap.add_argument("--time", action="store_true")
    args = ap.parse_args(argv)
    logging.disable(logging.WARNING)
    import program_cases as pc
    pc.load_libraries()
    head = "| configuration | unknowns | nnz(K) | via blocks | largest footprint (cells) | dense coupling entries | LU factor nnz (x K), memory estimate |\n| :-- | --: | --: | --: | --: | --: | :-- |"
    for cell in args.cells:
        print(f"\n## own via field, cell {cell:g} mm\n")
        print(head)
        for n in args.sides:
            holes, w, h = rbd.own_via_field(n)
            p = rbd.problem_from_holes(holes, w, h, layers=4, center=(w / 2, h / 2))
            est = ms.estimate_dense_entries(len(holes), 0.3, cell, 4)
            for tr in ("program", "mw"):
                if tr == "mw" and est > args.max_dense:
                    print(f"| {len(holes)} vias, mw | skipped: estimated {est:,.0f} dense coupling entries (> {args.max_dense:,}) | | | | | |", flush=True)
                    continue
                print(row(f"{len(holes)} vias, {tr}", ms.build(p, cell, tr), args), flush=True)
    for cell in args.cells:                                                  # the fixed pad above saturates (the same cells hold more vias); a fixed pitch makes the touched cells grow
        print(f"\n## own via field (fixed pitch {args.pitch:g} mm, board grows), cell {cell:g} mm\n")
        print(head)
        for n in args.pitch_sides:
            holes, w, h = rbd.via_array_pitch(n, args.pitch)
            p = rbd.problem_from_holes(holes, w, h, layers=4, center=(w / 2, h / 2))
            for tr in ("program", "mw"):
                print(row(f"{len(holes)} vias, {tr}", ms.build(p, cell, tr), args), flush=True)
    print("\n## real boards\n")
    print(head)
    for name in rbd.BOARDS:
        try:
            holes, w, h = rbd.holes_of(name)
        except FileNotFoundError as e:
            print("skipped:", e)
            continue
        p = rbd.problem_from_holes(holes, w, h, layers=rbd.BOARDS[name]["layers"])
        for cell in (1.0, 0.5, 0.25):
            for tr in ("program", "mw"):
                print(row(f"{name} ({len(holes)} holes) {cell:g} mm, {tr}", ms.build(p, cell, tr), args), flush=True)
    paths.OUT.mkdir(parents=True, exist_ok=True)
    for n in (3, 9):                                                         # small boards for the spy plots of the figure
        holes, w, h = rbd.own_via_field(n, pad_mm=3.0 * n / 3.0, ring_vias=0, board_mm=(12.0, 12.0))
        p = rbd.problem_from_holes(holes, w, h, layers=2, source_mm=4.0, center=(6.0, 6.0))
        for tr in ("program", "mw"):
            net = ms.build(p, 0.5, tr)
            np.savez_compressed(paths.OUT / f"spy_{n}x{n}_{tr}.npz", pattern=ms.spy_pattern(net.K, 300), unknowns=net.K.shape[0], nnz=net.K.nnz, vias=n * n)


if __name__ == "__main__":
    main()
