#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review.py
@brief The checks of the review of analytic-partial-copper: a second independent reference, the tile rule on more boards, copper edges inside a tile, the trigger of the Analytic warning, and the size of the candidate's tile system on larger boards.
@details Questions: (a) does a second independent 3D solver (tests/helpers/layered3d.py, isotropic cells, so the laminate is taken as 0.3 W/mK in every direction) give the reference of
         lib/pads.py? (b) is a tile of a sixth of the part enough on other boards and part sizes (candidate against the program's FVM with the same laminate nodes at 0.25 mm)?
         (c) what does a copper edge in the middle of a tile do to the candidate, and to the program's FVM at its own cell? (d) does the program's warning (spread of the
         K0-weighted fill above 0.25) fire on the 52 pad rows of research/gap-subdivision as it does on the 18 pad boards, and does a second spread, computed with the fin length of a
         full-copper sheet, close the gap without warning on the uniform rows and on the example boards? (e) how many unknowns has the dense tile system on boards larger than the
         designed ones? Writes data/review_*.csv and caches in out/.
         Usage: .venv/bin/python research/analytic-partial-copper/scripts/study_review.py   (from the repository root; run study_baseline.py first; long).
"""

import csv
import glob
import json
import re

import numpy as np
from scipy.special import k0

import _bootstrap as BS
import boards as B
import defect as D
import pads as P
from study_baseline import board
from study_rows import pad_board, read, uniform_board
from pcbthermal import Problem, SolverOptions, analytic, laminate, project, simulate
from pcbthermal.geometry import polygon_area, polygon_centroid, zone_fill

import sys
sys.path.insert(0, str(BS.REPO / "tests" / "helpers"))
import layered3d as L3                                                        # noqa: E402  (second independent solver, imports nothing from the program)


def fvm_nodes(p, n, cell_mm):
    """!
    @brief Peak rise of the program's FVM with n laminate nodes (set in memory, one-layer boards).
    @param p Problem.
    @param n Laminate nodes.
    @param cell_mm Cell size in mm.
    @return Rise in K.
    """
    # Since 2.4.5 the program's FVM applies the laminate rule by itself and ignores LAMINATE_NODES on a one-layer board, so "n nodes" would
    # silently be the rule; the rule is switched off here so that n means n nodes again (found by the review of the reproduction pass)
    keep, keep_rule = laminate.LAMINATE_NODES, laminate.uses_rule
    laminate.uses_rule = lambda problem: False
    try:
        laminate.LAMINATE_NODES = n
        return float(simulate(p, SolverOptions(models=("fvm",), cell_mm=cell_mm)).results["fvm"].t_max - p.board.ambient)
    finally:
        laminate.LAMINATE_NODES, laminate.uses_rule = keep, keep_rule


def second_reference(bd, dx_mm=0.25, nsub=8, cell_mm=0.5):
    """!
    @brief Peak rise of a centred pad board in layered3d (quadrant, isotropic cells, film also under the source as in the program), read as lib/pads.py reads its reference.
    @param bd A pads.Pad with k_inplane equal to k_through.
    @param dx_mm Cell size in mm.
    @param nsub Sub-slabs through the laminate.
    @param cell_mm Block over which the peak is averaged, in mm.
    @return dict with peak (K) and balance (heat out over power).
    """
    p = P.problem(bd)
    b = p.board
    kcu, tc = float(b.materials.k_copper), [float(x) for x in b.copper_thickness]
    n = int(round(bd.size / 2 / dx_mm))
    xs = (np.arange(n) + 0.5) * dx_mm
    inside = np.ones(n, dtype=bool) if bd.pad is None else xs < bd.pad / 2
    k1 = np.where(inside[None, :] & inside[:, None], kcu, bd.k_through)
    slabs = [(tc[0], k1, 1)]
    if bd.layers == 1:
        slabs.append((bd.thickness * 1e-3 - tc[0], bd.k_through, nsub))
    else:
        slabs.append((bd.thickness * 1e-3 - sum(tc), bd.k_through, nsub))
        slabs.append((tc[1], kcu if bd.second == "full" else bd.k_through, 1))
    res = L3.solve(dx_mm * 1e-3, n, n, slabs, (0.0, 0.0, bd.source / 2 * 1e-3, bd.source / 2 * 1e-3), bd.power / 4.0, b.h_top, b.h_bottom, film_under_source=True)
    s, r, nb = res["surface_top"], int(round(cell_mm / dx_mm)), int(round(bd.source / 2 / cell_mm))
    peak = max(float(s[i * r:(i + 1) * r, j * r:(j + 1) * r].mean()) for i in range(nb) for j in range(nb))
    return {"peak": peak, "balance": res["heat_out"] / (bd.power / 4.0)}


def part_a():
    """!
    @brief (a) the two independent solvers on five boards (laminate 0.3 W/mK in every direction), with the errors of the program's Analytic, the FVM and the candidate (n = 4, 0.5 mm tile).
    @return list of dict rows.
    """
    rows = []
    for layers, second, pad in ((1, "full", 10.0), (1, "full", 20.0), (2, "empty", 10.0), (2, "full", 20.0), (2, "full", 6.0)):
        bd = P.Pad(layers=layers, second=second, pad=pad, k_inplane=0.3)
        p = P.problem(bd)
        a = second_reference(bd)
        r = P.reference(bd, 0.5, 0.25, p=p)
        row = {"layers": layers, "second": second, "pad_mm": pad, "layered3d_K": a["peak"], "layered3d_balance": a["balance"], "resolved3d_K": r["peak"],
               "analytic_K": P.program_rise(bd, "analytic", 0.5, p), "fvm_K": P.program_rise(bd, "fvm", 0.5, p), "cand4_K": D.solve(p, n_sub=4, tile_mm=0.5)["max"]}
        print(row, flush=True)
        rows.append(row)
    return rows


def part_b():
    """!
    @brief (b) the tile as a fraction of the part (k tiles across, k = 2 to 12) on five boards, candidate with 2 and 4 nodes against the FVM with the same nodes at 0.25 mm.
    @return list of dict rows.
    """
    rows = []
    for size, pad, src in ((40.0, 10.0, 2.0), (40.0, 10.0, 4.0), (60.0, 20.0, 4.0), (60.0, 20.0, 10.0), (40.0, 16.0, 3.0)):
        bd = P.Pad(size=size, pad=pad, source=src)
        p = P.problem(bd)
        for n in (2, 4):
            ref = fvm_nodes(p, n, 0.25)
            row = {"size_mm": size, "pad_mm": pad, "part_mm": src, "n": n, "fvm_K": ref}
            for k in (2, 3, 4, 6, 8, 12):
                tile = src / k
                row[f"k{k}_K"] = D.solve(p, n_sub=n, tile_mm=tile, cell_mm=0.25)["max"]
                # the tile grid is aligned with the pad edges only when (size - pad) / 2 is a multiple of the tile
                row[f"k{k}_edge_offset"] = round(((size - pad) / 2 / tile) % 1.0, 3)
            print(row, flush=True)
            rows.append(row)
    return rows


def part_c():
    """!
    @brief (c) a pad edge inside a tile: candidate (n = 2) against the FVM with two nodes at a cell where the edge is on a cell edge, and the program's FVM itself at 1, 0.5, 0.25 and 0.125 mm.
    @return list of dict rows.
    """
    rows = []
    for size, src, tile, pads in ((60.0, 6.0, 1.0, (10.0, 10.5, 11.0, 11.5, 12.0, 20.0, 20.5, 21.0, 21.5)), (40.0, 4.0, 0.5, (10.0, 10.5, 11.0))):
        for pad in pads:
            p = P.problem(P.Pad(size=size, pad=pad, source=src))
            ref = fvm_nodes(p, 2, 0.25)
            row = {"size_mm": size, "part_mm": src, "tile_mm": tile, "pad_mm": pad, "edge_offset": round(((size - pad) / 2 / tile) % 1.0, 3), "fvm2_025_K": ref,
                   "cand2_K": D.solve(p, n_sub=2, tile_mm=tile, cell_mm=0.25)["max"]}
            if size == 60.0 and pad in (10.0, 10.5, 11.0):
                for c in (1.0, 0.5, 0.25, 0.125):
                    row[f"fvm_program_{c}_K"] = fvm_nodes(p, laminate.LAMINATE_NODES, c)
            print(row, flush=True)
            rows.append(row)
    return rows


def spreads(problem, cell_mm):
    """!
    @brief The spread of the fill of the heater layers under the K0 weights, with the program's fin length (`program`) and with the fin length of the same layer as full copper (`copper`).
    @details Copies the weights of `analytic._effective_sheet` (read only): lambda = sqrt(S / (h_surface + g_adjacent)), K0(r / lambda) around every heater, distance floored at the heater's
             equivalent radius; only `S` changes between the two spreads.
    @param problem A Problem.
    @param cell_mm Sampling cell in mm.
    @return dict with program and copper (largest spread over the heaters).
    """
    prob = laminate.series_bottom_problem(problem)
    sh = analytic._effective_sheet(prob, cell_mm)
    b, m, L, xs, ys = sh["b"], sh["m"], sh["L"], sh["xs"], sh["ys"]
    tc, slab, k_lam, g = sh["tc"], sh["slab"], sh["k_lam"], sh["g_diel"]
    fm = zone_fill(prob.zones, L, sh["nx"], sh["ny"], sh["dx"], sh["dy"], 4)
    out = {}
    for key in ("program", "copper"):
        best = 0.0
        for h in prob.heaters:
            l = h.layer
            g_adj = sum(g[i] for i in (l - 1, l) if 0 <= i < L - 1)
            hs = (b.h_top if l == 0 else 0.0) + (b.h_bottom if l == L - 1 else 0.0)
            f = fm[l].mean() if key == "program" else 1.0
            S = f * m.k_copper * tc[l] + k_lam[l] * (slab[l] - f * tc[l])
            lam = np.sqrt(S / max(hs + g_adj, 1e-9))
            cx, cy = polygon_centroid(h.polygon)
            r0 = np.sqrt(polygon_area(h.polygon) / np.pi)
            w = k0(np.maximum(np.hypot(xs[None, :] - cx, ys[:, None] - cy), max(r0, 0.5 * sh["dx"])) / lam)
            fbar = (fm[l] * w).sum() / w.sum()
            best = max(best, float(np.sqrt(((fm[l] - fbar) ** 2 * w).sum() / w.sum())))
        out[key] = best
    return out


def part_d():
    """!
    @brief (d) the warning: the program's flag and both spreads on the 18 pad and 2 full boards of the baseline, the 52 pad and 44 uniform rows of gap-subdivision, and the example boards
           (these against the program's FVM, having no 3D reference here).
    @return list of dict rows.
    """
    rows = []

    def add(group, tag, p, cell, ref):
        """!
        @brief Run the program's Analytic on one board and store its error, its warning flag and the two spreads.
        @param group Name of the set of boards.
        @param tag Board name.
        @param p Problem.
        @param cell Cell in mm.
        @param ref Reference rise in K (None: the program's FVM at the same cell).
        @return None.
        """
        res = simulate(p, SolverOptions(models=("analytic", "fvm") if ref is None else ("analytic",), cell_mm=cell)).results
        an = float(res["analytic"].t_max - p.board.ambient)
        ref = float(res["fvm"].t_max - p.board.ambient) if ref is None else ref
        warned = any(re.search(r"spread ([0-9.]+)", w) for w in res["analytic"].warnings)
        rows.append({"group": group, "tag": tag, "err_pct": 100.0 * (an / ref - 1.0), "warned": warned, **spreads(p, cell)})

    for r in BS.cached("baseline", lambda: (_ for _ in ()).throw(RuntimeError("run study_baseline.py first"))):
        add("60 mm boards", f"L{r['layers']}-{r['second']}-pad{r['pad_mm']:g}", P.problem(board(r["layers"], r["second"], r["pad_mm"] or None)), 0.5, r["ref_K"])
    for r in read("pads.csv"):
        add("pad rows", r["tag"], B.problem(pad_board(r)), float(r["cell_mm"]), float(r["ref_K"]))
    for r in read("uniform.csv"):
        add("uniform rows", r["sweep"], B.problem(uniform_board(r)), float(r["cell_mm"]), float(r["ref_K"]))
    for f in sorted(glob.glob(str(BS.REPO / "examples" / "*.pcbt.json"))):
        add("example boards (vs FVM)", f.split("/")[-1], project.load_project(f).problem, 0.5, None)
    return rows


def part_e():
    """!
    @brief (e) unknowns of the dense tile system (tiles with a defect times the nodes that carry one) on larger boards, counted through the refusal of `defect.solve`.
    @return list of dict rows.
    """
    def count(p, tile, n=2):
        """!
        @brief Unknowns of the tile system of a Problem.
        @param p Problem.
        @param tile Tile in mm.
        @param n Nodes through every gap.
        @return Number of unknowns (0 when the board has no defect).
        """
        try:
            D.solve(p, n_sub=n, tile_mm=tile, n_terms=40, max_unknowns=1)
            return 0
        except ValueError as e:
            return int(re.search(r"= (\d+) unknowns", str(e)).group(1))

    def make(W, H, L, top, bottom_full, src):
        """!
        @brief A board with a top copper rectangle, full inner layers and a full or framed bottom layer.
        @param W Width in mm.
        @param H Height in mm.
        @param L Layers.
        @param top Rectangle of the top copper in mm.
        @param bottom_full True: full bottom copper; False: a frame 10 mm in from the edge.
        @param src Part side in mm (centred).
        @return Problem.
        """
        p = Problem.new(W, H, L, 1.6, 35.0, h_top=10.0, h_bottom=10.0, h_side=None)
        if L > 1:
            p.board.make_advanced()
        p.add_zone(1, rect=top)
        for l in range(2, L):
            p.add_zone(l, rect=(0, 0, W, H))
        if L > 1:
            p.add_zone(L, rect=(0, 0, W, H) if bottom_full else (10, 10, W - 10, H - 10))
        p.add_heater(1, 1.0, rect=(W / 2 - src / 2, H / 2 - src / 2, W / 2 + src / 2, H / 2 + src / 2))
        return p

    cases = (("60 x 60, 1 layer, 40 mm pad, 6 mm part", make(60, 60, 1, (10, 10, 50, 50), True, 6.0), 1.0),
             ("100 x 80, 2 layers, 60 x 40 top pour, full bottom, 6 mm part", make(100, 80, 2, (20, 20, 80, 60), True, 6.0), 1.0),
             ("100 x 80, 2 layers, 60 x 40 top pour, full bottom, 3 mm part", make(100, 80, 2, (20, 20, 80, 60), True, 3.0), 0.5),
             ("100 x 80, 4 layers, 60 x 40 top pour, 80 x 60 bottom pour, 6 mm part", make(100, 80, 4, (20, 20, 80, 60), False, 6.0), 1.0))
    rows = [{"case": c, "tile_mm": t, "unknowns_n2": count(p, t)} for c, p, t in cases]
    for f in sorted(glob.glob(str(BS.REPO / "examples" / "*.pcbt.json"))):
        p = project.load_project(f).problem
        note = f" ({len(p.vias)} vias, {len(p.heatsinks)} heatsinks: refused by defect.solve, counted without them)" if (p.vias or p.heatsinks) else " (no via, no heatsink)"
        rows.append({"case": f.split("/")[-1] + note, "tile_mm": D.tile_for(p),
                     "unknowns_n2": count(_strip(p), D.tile_for(p))})
    for r in rows:
        print(r, flush=True)
    return rows


def _strip(p):
    """!
    @brief A copy of a Problem without vias and heatsinks (to count the tile system of the copper only).
    @param p Problem.
    @return Problem.
    """
    import copy
    q = copy.deepcopy(p)
    q.vias, q.heatsinks = [], []
    return q


def write(name, rows):
    """!
    @brief Write rows to data/<name>.csv.
    @param name File stem.
    @param rows List of dict rows.
    @return None.
    """
    with open(BS.DATA / f"{name}.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    """!
    @brief Run the five checks and print the summaries quoted in the README chapter Review.
    @return None.
    """
    a = BS.cached("review_a", part_a)
    b = BS.cached("review_b", part_b)
    c = BS.cached("review_c", part_c)
    d = BS.cached("review_d", part_d)
    e = BS.cached("review_e", part_e)
    for name, rows in (("review_second_reference", a), ("review_tiles", b), ("review_edges", c), ("review_warning", d), ("review_cost", e)):
        write(name, rows)
    print("\n(a) layered3d against resolved3d, and errors against layered3d (%): Analytic | FVM | candidate n=4")
    for r in a:
        ref = r["layered3d_K"]
        print(f"L{r['layers']} {r['second']:5s} pad {r['pad_mm']:4.0f}: {ref:8.3f} vs {r['resolved3d_K']:8.3f} ({abs(ref / r['resolved3d_K'] - 1):.1e}), balance {r['layered3d_balance']:.9f} | "
              f"{100 * (r['analytic_K'] / ref - 1):+6.1f} {100 * (r['fvm_K'] / ref - 1):+6.1f} {100 * (r['cand4_K'] / ref - 1):+6.1f}")
    print("\n(b) candidate against the FVM with the same nodes (%), k tiles across the part (edge offset in tiles)")
    for r in b:
        print(f"board {r['size_mm']:3.0f} pad {r['pad_mm']:4.0f} part {r['part_mm']:4.1f} n={r['n']}: " +
              "  ".join(f"k{k} {100 * (r[f'k{k}_K'] / r['fvm_K'] - 1):+5.1f} ({r[f'k{k}_edge_offset']:.2f})" for k in (2, 3, 4, 6, 8, 12)))
    print("\n(c) pad edge inside a tile: candidate n=2 against the FVM n=2 at 0.25 mm (%); the program's FVM at 1 / 0.5 / 0.25 / 0.125 mm (K)")
    for r in c:
        extra = "  program FVM: " + " / ".join(f"{r[f'fvm_program_{x}_K']:.2f}" for x in (1.0, 0.5, 0.25, 0.125)) if "fvm_program_1.0_K" in r else ""
        print(f"board {r['size_mm']:3.0f} tile {r['tile_mm']:.2f} pad {r['pad_mm']:5.2f} offset {r['edge_offset']:.2f}: {100 * (r['cand2_K'] / r['fvm2_025_K'] - 1):+5.1f}{extra}")
    print("\n(d) warning triggers (rows quiet with |error| > 5 %, worst quiet row, warned rows within 2 %)")
    for label, key in (("program flag", None), ("program spread > 0.25", "program"), ("copper spread > 0.25", "copper"), ("either spread > 0.25", "both")):
        def on(r):
            """!
            @brief Whether the trigger fires on a row.
            @param r Row.
            @return bool.
            """
            if key is None:
                return r["warned"]
            return (max(r["program"], r["copper"]) if key == "both" else r[key]) > 0.25
        quiet = [r for r in d if not on(r)]
        loud = [r for r in d if on(r)]
        worst = max(quiet, key=lambda r: abs(r["err_pct"]))
        print(f"{label:24s}: warned {len(loud):3d}, quiet {len(quiet):3d}, quiet beyond 5 %: {sum(abs(r['err_pct']) > 5 for r in quiet)}, worst quiet {worst['tag']} {worst['err_pct']:+.1f} %,"
              f" warned within 2 %: {sum(abs(r['err_pct']) < 2 for r in loud)}")
    for r in d:
        if not r["warned"] and abs(r["err_pct"]) > 3:
            print(f"   unwarned by the program: {r['group']:14s} {r['tag']:22s} {r['err_pct']:+6.1f} %  spreads {r['program']:.2f} / {r['copper']:.2f}")
    for r in d:
        if r["group"].startswith("example"):
            print(f"   {r['tag']}: Analytic against FVM {r['err_pct']:+.1f} %, spreads {r['program']:.2f} / {r['copper']:.2f}")
    print("\n(e) unknowns of the tile system with two nodes per gap")
    for r in e:
        print(f"{r['case']}: tile {r['tile_mm']:.2f} mm, {r['unknowns_n2']} unknowns")


if __name__ == "__main__":
    main()
