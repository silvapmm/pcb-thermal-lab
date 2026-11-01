#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_candidate.py
@brief The candidate for the Analytic model on partial copper (lib/defect.py: a stack of nodes and the copper as a Green-function defect on a bare base) against the resolved 3D solver and the program's models.
@details Questions: (A) how close does the candidate come on the pad boards of study_baseline.py with 1, 2, 4 and 8 nodes through the laminate, and does it follow the FVM with the same nodes?
         (B) does it converge with the tile size, and does the opposite construction (a copper base with negative defects) converge? (C) does it hold out of sample (board size, part size, thickness,
         films, copper weight, laminate conductivity)? (D) pads off the centre, a part off the pad, two pads; (E) the limit: a copper-free window in full copper (the bare spot, A12).
         The references are those of lib/pads.py (quadrant, 0.25 mm) and lib/general.py (whole board, 0.5 mm). Writes data/candidate_*.csv and caches in out/.
         Usage: .venv/bin/python research/analytic-partial-copper/scripts/study_candidate.py   (from the repository root; run study_baseline.py first; about 15 minutes).
"""

import csv
from dataclasses import replace

import _bootstrap as BS
import defect as D
import general as G
import pads as P
from pcbthermal import SolverOptions, laminate, simulate
from study_baseline import board

NS = (1, 2, 4, 8)


def pct(a, b):
    """!
    @brief Relative difference in percent.
    @param a Value.
    @param b Reference.
    @return 100 (a / b - 1).
    """
    return 100.0 * (a / b - 1.0)


def fvm_with_nodes(bd, p, n):
    """!
    @brief The program's FVM of a one-layer board with n laminate nodes (set in memory).
    @param bd A Pad.
    @param p The Problem.
    @param n Laminate nodes.
    @return Rise in K.
    """
    # Since 2.4.5 the program's FVM applies the laminate rule by itself and ignores LAMINATE_NODES on a one-layer board, so "n nodes" would
    # silently be the rule; the rule is switched off here so that n means n nodes again (found by the review of the reproduction pass)
    keep, keep_rule = laminate.LAMINATE_NODES, laminate.uses_rule
    laminate.uses_rule = lambda problem: False
    try:
        laminate.LAMINATE_NODES = n
        return P.program_rise(bd, "fvm", 0.5, p)
    finally:
        laminate.LAMINATE_NODES, laminate.uses_rule = keep, keep_rule


def sweep_pads():
    """!
    @brief (A) the candidate on the baseline boards for n = 1, 2, 4, 8 nodes through the laminate.
    @return list of dict rows.
    """
    base = BS.cached("baseline", lambda: (_ for _ in ()).throw(RuntimeError("run study_baseline.py first")))
    rows = []
    for r in base:
        bd = board(r["layers"], r["second"], r["pad_mm"] or None)
        p = P.problem(bd)
        row = {"kind": r["kind"], "pad_mm": r["pad_mm"], "ref_K": r["ref_K"], "analytic_K": r["analytic_K"], "fvm_K": r["fvm_K"]}
        for n in NS:
            row[f"cand{n}_K"] = D.solve(p, n_sub=n, tile_mm=1.0)["max"]
            if bd.layers == 1:
                row[f"fvm{n}_K"] = fvm_with_nodes(bd, p, n)
        print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
        rows.append(row)
    return rows


def sweep_tiles():
    """!
    @brief (B) tile-size convergence of the construction (bare base, copper added) and of the opposite one (copper base, bare subtracted) on the one-layer 10 and 20 mm pads.
    @return list of dict rows.
    """
    base = {(r["layers"], r["second"], r["pad_mm"]): r["ref_K"] for r in BS.cached("baseline", lambda: None)}
    rows = []
    for pad in (10.0, 20.0):
        bd = board(1, "full", pad)
        p = P.problem(bd)
        ref = base[(1, "full", pad)]
        for tile in (2.0, 1.0, 0.5):
            row = {"pad_mm": pad, "tile_mm": tile, "ref_K": ref}
            for n in (1, 4):
                row[f"min_n{n}_K"] = D.solve(p, n_sub=n, tile_mm=tile, base="min")["max"]
            row["max_n1_K"] = D.solve(p, n_sub=1, tile_mm=tile, base="max")["max"] if tile >= 1.0 else float("nan")
            print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
            rows.append(row)
    return rows


def sweep_tiles_all():
    """!
    @brief (B2) the tile size on the one-layer pads 6, 10, 14 and 20 mm for 1, 2, 4 and 8 laminate nodes: tiles of 1 and 0.5 mm.
    @return list of dict rows.
    """
    base = {(r["layers"], r["second"], r["pad_mm"]): r["ref_K"] for r in BS.cached("baseline", lambda: None)}
    rows = []
    for pad in (6.0, 10.0, 14.0, 20.0):
        bd = board(1, "full", pad)
        p = P.problem(bd)
        row = {"pad_mm": pad, "ref_K": base[(1, "full", pad)]}
        for tile in (1.0, 0.5, 0.25):
            if tile == 0.25 and pad > 10.0:
                continue                                        # 0.25 mm tiles only on the two small pads (the tile system grows with the square of the pad)
            for n in NS:
                row[f"t{tile}_n{n}_K"] = D.solve(p, n_sub=n, tile_mm=tile, n_terms=400)["max"]
        print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
        rows.append(row)
    return rows


OOS = (("size 40", dict(size=40.0)), ("size 80", dict(size=80.0)), ("source 3", dict(source=3.0)), ("source 10", dict(source=10.0)), ("thickness 0.8", dict(thickness=0.8)),
       ("thickness 3.2", dict(thickness=3.2)), ("films 5 and 5", dict(h_top=5.0, h_bottom=5.0)), ("films 50 and 50", dict(h_top=50.0, h_bottom=50.0)), ("copper 17.5", dict(copper=17.5)),
       ("copper 70", dict(copper=70.0)), ("laminate in-plane 0.3", dict(k_inplane=0.3)), ("power 5 W", dict(power=5.0)))


def sweep_out_of_sample():
    """!
    @brief (C) out of sample: a one-layer 14 mm pad with one parameter changed at a time, the candidate (n = 4) and the program's Analytic against the reference.
    @return list of dict rows.
    """
    rows = []
    for label, kw in (("base", {}),) + OOS:
        bd = replace(board(1, "full", 14.0), **kw)
        p = P.problem(bd)
        ref = P.reference(bd, 0.5, 0.25, p=p)["peak"]
        row = {"case": label, "ref_K": ref, "analytic_K": P.program_rise(bd, "analytic", 0.5, p), "fvm_K": P.program_rise(bd, "fvm", 0.5, p),
               "tile_mm": D.tile_for(p), "cand4_K": D.solve(p, n_sub=4, tile_mm=D.tile_for(p))["max"]}
        print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
        rows.append(row)
    return rows


def earlier_board():
    """!
    @brief The board of research/effective-conductivity 4.11 (one layer, 20 mm pad, laminate 0.3 W/mK in every direction): the -28.8 % of the Analytic quoted there, and the candidate.
    @return list with one dict row.
    """
    bd = replace(board(1, "full", 20.0), k_inplane=0.3)
    p = P.problem(bd)
    ref = P.reference(bd, 0.5, 0.25, p=p)["peak"]
    row = {"case": "1 layer, 20 mm pad, laminate 0.3 / 0.3", "ref_K": ref, "analytic_K": P.program_rise(bd, "analytic", 0.5, p), "fvm_K": P.program_rise(bd, "fvm", 0.5, p)}
    for n in (1, 2, 4):
        row[f"cand{n}_K"] = D.solve(p, n_sub=n, tile_mm=1.0)["max"]
    print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
    return [row]


def sweep_layouts():
    """!
    @brief (D) pads off the centre, a part off the pad, two pads; (E) a window in full copper. Whole-board references at 0.5 mm.
    @return list of dict rows.
    """
    one = board(1, "full", None)
    two = replace(board(2, "full", None), size=30.0)
    cases = [
        ("1 layer, pad 14 off the centre, part on it", one, [(31, 25, 45, 39)], (35, 29, 41, 35), "full"),
        ("1 layer, pad 14, part off its centre", one, [(23, 23, 37, 37)], (30, 24, 36, 30), "full"),
        ("1 layer, two pads 14 and 10 (4 mm apart), part on the first", one, [(14, 23, 28, 37), (32, 25, 42, 35)], (18, 27, 24, 33), "full"),
        ("2 layers, pad 10, part on it", two, [(10, 10, 20, 20)], (12, 12, 18, 18), "full"),
        ("2 layers, window 6 in full copper, part over it", two, [(0, 0, 12, 30), (18, 0, 30, 30), (12, 0, 18, 12), (12, 18, 18, 30)], (12, 12, 18, 18), "full"),
        ("2 layers, window 6 in full copper, part off the window", two, [(0, 0, 12, 30), (18, 0, 30, 30), (12, 0, 18, 12), (12, 18, 18, 30)], (6, 12, 12, 18), "full"),
    ]
    rows = []
    for label, bd, rects, src, bottom in cases:
        p = G.problem(bd, rects, src, bottom)
        ref = G.reference(bd, rects, src, bottom, 0.5, p=p)["peak"]
        row = {"case": label, "ref_K": ref, "analytic_K": P.program_rise(bd, "analytic", 0.5, p), "fvm_K": P.program_rise(bd, "fvm", 0.5, p)}
        for n in (1, 4):
            row[f"cand{n}_K"] = D.solve(p, n_sub=n, tile_mm=1.0)["max"]
        print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
        rows.append(row)
    return rows


def write(name, rows):
    """!
    @brief Write a list of dict rows to data/<name>.csv.
    @param name File stem.
    @param rows Rows.
    @return None.
    """
    with open(BS.DATA / f"{name}.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    """!
    @brief Run the four sweeps and print the errors.
    @return None.
    """
    pads = BS.cached("cand_pads", sweep_pads)
    tiles = BS.cached("cand_tiles", sweep_tiles)
    tiles2 = BS.cached("cand_tiles2", sweep_tiles_all)
    oos = BS.cached("cand_oos", sweep_out_of_sample)
    lay = BS.cached("cand_layouts", sweep_layouts)
    earlier = BS.cached("cand_earlier", earlier_board)
    write("candidate_earlier_board", earlier)
    print("\nboard of effective-conductivity 4.11:", {k: (round(100 * (v / earlier[0]["ref_K"] - 1), 1) if k.endswith("_K") and k != "ref_K" else v) for k, v in earlier[0].items()})
    for name, rows in (("candidate_pads", pads), ("candidate_tiles", tiles), ("candidate_tiles_nodes", tiles2), ("candidate_out_of_sample", oos), ("candidate_layouts", lay)):
        write(name, rows)
    print("\n(A) error against the reference (%): program Analytic | candidate n=1,2,4,8 | FVM n=1,2,4,8 (one layer)")
    for r in pads:
        print(f"{r['kind']:24s} pad {r['pad_mm']:4.0f}  {pct(r['analytic_K'], r['ref_K']):+6.1f} | " + " ".join(f"{pct(r[f'cand{n}_K'], r['ref_K']):+6.1f}" for n in NS) +
              (" | " + " ".join(f"{pct(r[f'fvm{n}_K'], r['ref_K']):+6.1f}" for n in NS) if "fvm1_K" in r else ""))
    print("\n(B) tiles")
    for r in tiles:
        print({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}, "errors:", {k[:-2]: round(pct(v, r['ref_K']), 1) for k, v in r.items() if k.endswith("_K") and k != "ref_K"})
    print("\n(B2) tile 1 / 0.5 mm, n = 1, 2, 4, 8 (error %)")
    for r in tiles2:
        print(f"pad {r['pad_mm']:4.0f} ref {r['ref_K']:7.2f}  " + " | ".join(" ".join(f"{pct(r[f't{t}_n{n}_K'], r['ref_K']):+6.1f}" for n in NS) for t in (1.0, 0.5, 0.25) if f"t{t}_n1_K" in r))
    print("\n(C) out of sample: Analytic | FVM | candidate n=4 (tile = source / 6, at most 1 mm)")
    for r in oos:
        print(f"{r['case']:24s} ref {r['ref_K']:7.2f}  {pct(r['analytic_K'], r['ref_K']):+6.1f} | {pct(r['fvm_K'], r['ref_K']):+6.1f} | {pct(r['cand4_K'], r['ref_K']):+6.1f}  tile {r['tile_mm']:.2f}")
    print("\n(D, E) layouts: Analytic | FVM | candidate n=1 | n=4")
    for r in lay:
        print(f"{r['case']:58s} ref {r['ref_K']:7.2f}  {pct(r['analytic_K'], r['ref_K']):+6.1f} | {pct(r['fvm_K'], r['ref_K']):+6.1f} | {pct(r['cand1_K'], r['ref_K']):+6.1f} | {pct(r['cand4_K'], r['ref_K']):+6.1f}")


if __name__ == "__main__":
    main()
