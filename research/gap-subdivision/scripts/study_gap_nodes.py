#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_gap_nodes.py
@brief Does cutting the dielectric gap into more than one node through its thickness remove the error of the layered model against a resolved 3D answer? Single-effect experiments.
@details Everything is measured on an in-memory copy of the program's layered FVM (lib/gapnodes.py -> research/bare-spot-under-source/lib/layered.py, which reproduces the program's
         peak with one sub-gap) and compared with the exact series (uniform boards) or the converged graded 3D solver (boards with pads), at the model cell of 0.5 mm.
         Parts (the number is the section of the README):
         A  uniform boards: n = 1 to 8 nodes, equal and graded, layers x gap: what the subdivision does when there is nothing to fix.
         B  pad boards: n sweep x where (all cells, bare cells plus a margin) x grading, on the representative boards of the baseline.
         C  single-effect probes on two pad boards: (1) only the gap under the pad, (2) only the bare cells (margin 0), (3) the margin around the bare cells, (4) the half-layer correction of
            the copper node (the reading of the surface), (5) the in-plane conductivity of the laminate turned down to 0.01 W/mK (the mechanism: lateral conduction in the gap),
            (6) the cell size, (7) the through conductivity.
         D  cost: unknowns of a local implementation and the time of the copy.
         Usage: .venv/bin/python research/gap-subdivision/scripts/study_gap_nodes.py [A|B|C|D ...]   (from the repository root; references are cached in out/, the first run takes several minutes).
"""

import json
import sys
import time
from dataclasses import replace
from multiprocessing import Pool

import _bootstrap as BS
import boards as B
import gapnodes as G
import study_baseline_pads as SP

NS = (1, 2, 3, 4, 6, 8)
RECORDS = []                                                                 # rows of baseline/gap_nodes.csv: part, board, probe, n, total error %, through-thickness error %
CELL = 0.5
CACHE = BS.OUT / "refs_extra.json"


def _ref(args):
    """!
    @brief Worker: converged reference of a board.
    @param args (key, Board, cell).
    @return (key, dict).
    """
    key, bd, cell = args
    return key, B.graded_peak(bd, cell)


def references(items, nproc=4):
    """!
    @brief Converged references for a list of (key, Board, cell), cached in out/refs_extra.json and in the baseline cache of study_baseline_pads.
    @param items List of (key, Board, cell).
    @param nproc Number of processes.
    @return dict key -> reference dict.
    """
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    base_path = BS.OUT / "refs_pads.json"
    base = json.loads(base_path.read_text()) if base_path.exists() else {}
    out, todo = {}, []
    for key, bd, cell in items:
        k = f"{key}|{cell}"
        if k in base:
            out[key] = base[k]
        elif k in cache:
            out[key] = cache[k]
        else:
            todo.append((key, bd, cell))
    if todo:
        print(f"  computing {len(todo)} references ...", flush=True)
        with Pool(nproc) as pool:
            for key, r in pool.imap_unordered(_ref, todo):
                cell = [c for k2, _, c in todo if k2 == key][0]
                cache[f"{key}|{cell}"] = r
                CACHE.write_text(json.dumps(cache))
                out[key] = r
    return out


def err(v, ref):
    """!
    @brief Error in percent of the rise.
    @param v Value.
    @param ref Reference.
    @return float.
    """
    return 100.0 * (v / ref - 1.0)


def part_a():
    """!
    @brief Part A: the subdivision on uniform boards (nothing to fix).
    @return None.
    """
    print("\nA. Uniform boards, error against the exact series (percent), all cells refined, n = 1 2 3 4 6 8 (equal | graded 2:1)")
    for l in (2, 4, 8):
        for g in (0.1, 0.4, 1.6):
            for src, h in ((6.0, 10.0), (2.0, 100.0)):
                bd = B.Board("u", layers=l, gap=g, source=src, h_top=h, h_bottom=h)
                p = B.problem(bd)
                ref = B.exact_peak(bd, CELL, p)
                eq = [err(G.run(p, CELL, n, "all", "equal")["peak"], ref) for n in NS]
                gr = [err(G.run(p, CELL, n, "all", "graded")["peak"], ref) for n in NS]
                print(f"  L{l} gap {g:4.1f} src {src:3.0f} h {h:4.0f}  " + " ".join(f"{x:+6.2f}" for x in eq) + "  |  " + " ".join(f"{x:+6.2f}" for x in gr[1:]))


def pad_boards():
    """!
    @brief The representative pad boards of parts B to D.
    @return List of (tag, Board).
    """
    rows = {t: bd for _, t, bd, _, _ in SP.rows()}
    keep = ["pad10-empty", "pad10-full", "pad10-pad", "pad20-empty", "pad20-full", "pad20-pad", "gap0.4-full", "gap0.1-full", "gap3.2-full", "L4-gap1.6-top-pad", "L4-gap0.2-top-pad",
            "L6-gap0.4-all-pads", "src6", "h100"]
    return [(t, rows[t]) for t in keep]


def both(p, cell, ref_conv, ref_cell, n, **kw):
    """!
    @brief Error of the copy with n sub-gaps against the converged solver (total) and against the 3D solver on the same in-plane grid (through-thickness part only).
    @param p The Problem.
    @param cell Cell size in mm.
    @param ref_conv Converged peak in K.
    @param ref_cell Peak of the 3D solver on the same in-plane cell, many sub-slabs, in K.
    @param n Sub-gaps per gap.
    @param kw Arguments of gapnodes.run (where, grading, half_layer, margin).
    @return Tuple (total error %, through-thickness error %).
    """
    v = G.run(p, cell, n, **kw)["peak"]
    return err(v, ref_conv), err(v, ref_cell)


def part_b(nproc):
    """!
    @brief Part B: the n sweep on the pad boards, every cell refined or only the bare cells plus a margin, equal and graded.
    @param nproc Number of processes for the references.
    @return None.
    """
    boards = pad_boards()
    refs = references([(t, bd, CELL) for t, bd in boards], nproc)
    print("\nB. Pad boards, n = 1 2 3 4 6 8: error against the converged 3D solver (tot) and against the 3D solver on the same 0.5 mm in-plane grid (z), percent")
    print(f"  {'board':22s} {'where':>6s} {'grading':>7s} {'':3s} " + " ".join(f"{n:>6d}" for n in NS))
    for t, bd in boards:
        p = B.problem(bd)
        rc = refs[t]["peak"]
        rz = B.samecell_peak(bd, CELL, 32, p)
        print(f"  {t:22s} converged {rc:.3f} K, same-cell 3D {rz:.3f} K, in-plane error of the cell {err(rz, rc):+.2f} %")
        for where, grading in (("all", "equal"), ("all", "graded"), ("bare", "equal"), ("bare", "graded")):
            vals = [both(p, CELL, rc, rz, n, where=where, grading=grading) for n in NS]
            RECORDS.extend(("B", t, f"{where}-{grading}", n, round(v[0], 4), round(v[1], 4)) for n, v in zip(NS, vals))
            print(f"  {'':22s} {where:>6s} {grading:>7s} tot " + " ".join(f"{v[0]:+6.2f}" for v in vals))
            print(f"  {'':22s} {'':>6s} {'':>7s} z   " + " ".join(f"{v[1]:+6.2f}" for v in vals))


def part_c(nproc):
    """!
    @brief Part C: single-effect probes on two pad boards.
    @param nproc Number of processes for the references.
    @return None.
    """
    rows = {t: bd for _, t, bd, _, _ in SP.rows()}
    for tag in ("pad10-full", "pad20-empty"):
        bd = rows[tag]
        p = B.problem(bd)
        rc = references([(tag, bd, CELL)], nproc)[tag]["peak"]
        rz = B.samecell_peak(bd, CELL, 32, p)
        print(f"\nC. Probes on {tag}: converged {rc:.3f} K, same-cell 3D {rz:.3f} K; error in percent (tot | z), n = 1 2 3 4 6 8")

        def line(label, vals):
            """!
            @brief Print one probe line (total errors, then through-thickness errors).
            @param label Name of the probe.
            @param vals List of (tot, z) pairs.
            @return None.
            """
            print(f"  {label:42s} " + " ".join(f"{v[0]:+6.2f}" for v in vals) + "  |  " + " ".join(f"{v[1]:+6.2f}" for v in vals))
            RECORDS.extend(("C", tag, label, NS[i] if len(vals) == len(NS) else 1, round(v[0], 4), round(v[1], 4)) for i, v in enumerate(vals))

        line("(0) every cell, equal", [both(p, CELL, rc, rz, n, where="all") for n in NS])
        line("(0') every cell, graded", [both(p, CELL, rc, rz, n, where="all", grading="graded") for n in NS])
        line("(1) only the gap under the pad", [both(p, CELL, rc, rz, n, where="under") for n in NS])
        for m in (0, 1, 2, 4, 8, 16):
            line(f"(2/3) bare cells + margin of {m} cells", [both(p, CELL, rc, rz, n, where="bare", margin=m) for n in NS])
        line("(4) every cell + half-layer correction", [both(p, CELL, rc, rz, n, where="all", half_layer=True) for n in NS])
        line("(4') one node + half-layer correction only", [both(p, CELL, rc, rz, 1, where="none", half_layer=True)])
        # (5) the in-plane conductivity of the laminate turned down: the lateral conduction in the gap is the mechanism if the error disappears
        for kxy in (0.01, 0.3, 0.9, 3.0):
            b2 = replace(bd, k_inplane=kxy)
            p2 = B.problem(b2)
            r2 = references([(f"{tag}-kxy{kxy:g}", b2, CELL)], nproc)[f"{tag}-kxy{kxy:g}"]["peak"]
            z2 = B.samecell_peak(b2, CELL, 32, p2)
            line(f"(5) k_inplane {kxy:g} W/mK", [both(p2, CELL, r2, z2, n, where="all") for n in NS])
        for kz in (0.1, 0.3, 1.0):
            b2 = replace(bd, k_through=kz)
            p2 = B.problem(b2)
            r2 = references([(f"{tag}-kz{kz:g}", b2, CELL)], nproc)[f"{tag}-kz{kz:g}"]["peak"]
            z2 = B.samecell_peak(b2, CELL, 32, p2)
            line(f"(7) k_through {kz:g} W/mK", [both(p2, CELL, r2, z2, n, where="all") for n in NS])
        for c in (1.0, 0.25):
            r2 = references([(f"{tag}-cellprobe{c:g}", bd, c)], nproc)[f"{tag}-cellprobe{c:g}"]["peak"]
            z2 = B.samecell_peak(bd, c, 32, p)
            line(f"(6) cell {c:g} mm", [both(p, c, r2, z2, n, where="all") for n in NS])


def part_d():
    """!
    @brief Part D: cost of the subdivision (unknowns of a local implementation, seconds of the copy) on pad10-full.
    @return None.
    """
    rows = {t: bd for _, t, bd, _, _ in SP.rows()}
    bd = rows["pad10-full"]
    p = B.problem(bd)
    print("\nD. Cost on pad10-full at 0.5 mm (unknowns of a local implementation, seconds of the in-memory copy)")
    for where, margin in (("none", None), ("bare", None), ("bare", 0), ("all", None)):
        for n in (1, 2, 4, 8):
            t = time.time()
            r = G.run(p, CELL, n, where, margin=margin)
            print(f"  where {where:5s} margin {str(margin):4s} n {n}: unknowns {r['unknowns']:7d} ({r['unknowns'] / 7200:.2f} x the program)  {time.time() - t:.2f} s")


def main(argv):
    """!
    @brief Run the parts named on the command line (all by default).
    @param argv Part letters.
    @return None.
    """
    parts = [a.upper() for a in argv] or ["A", "B", "C", "D"]
    if "A" in parts:
        part_a()
    if "B" in parts:
        part_b(4)
    if "C" in parts:
        part_c(4)
    if "D" in parts:
        part_d()
    if RECORDS:
        import csv
        with open(BS.BASELINE / "gap_nodes.csv", "w", newline="") as fh:
            wr = csv.writer(fh)
            wr.writerow(["part", "board", "probe", "n", "err_total_pct", "err_z_pct"])
            wr.writerows(RECORDS)


if __name__ == "__main__":
    main(sys.argv[1:])
