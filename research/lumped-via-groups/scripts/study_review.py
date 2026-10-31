#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review.py
@brief The independent checks of the review: is the via effect of the zone model a via effect, how far is the absolute maximum from the reference, does a second
       layered solver give the same reference, and is the decimation of the potential integrals sound (in the zone model and in the program)?
@details Part 1: vias that conduct nothing (plating 1e-12 m, open barrel) have no effect, so the via effect E of a model on such a board measures what the model changes by
         itself; it is run on the 36 boards of the family for the researcher's zone model (`L_zone_r`) and the zone model after the review (`L_zone`).
         Part 2: the maximum rise with vias of each variant against the fine-grid reference (`refs.reference`, cached), in K and percent of the rise, and the program's
         error without vias, on the same 36 boards: E is a difference of two maxima and an error of E can hide two errors that cancel.
         Part 3: the via effect of four boards from the corrected FVM of `research/point-via-convergence` (`FVM_fix`, 0.25 mm) against the fine-grid layered solver.
         Part 4: the peak integral of the zone model (`lumped_zones.potential_excess`) on concentric discs against the closed form of the annulus, with the strided and the
         block decimation; and the program's own potentials (`pcbthermal.lumped._footprint_potentials`, at most 900 cells, the same strided decimation) on squares and
         discs of 400 to 3600 cells against every cell (read only; the program is not changed).
Usage: python research/lumped-via-groups/scripts/study_review.py [--procs N]   (from the repository root, after `study_family.py`, which writes out/family.json)
"""

import argparse
import json
import math
import multiprocessing as mp
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(FOLDER, "lib"))

import refs                                                                  # noqa: E402
import harness as hz                                                         # noqa: E402
import lumped_zones as lz                                                    # noqa: E402
import program_cases as pc                                                   # noqa: E402

NAMES = ("L_prog", "L_nn", "L_grp0", "L_zone_r", "L_zone")


def label(spec):
    """!
    @brief Short name of a family board.
    @param spec dict.
    @return str.
    """
    s = {**refs.DEFAULT, **spec}
    return f"{s['src']:.0f} mm, {s['layers']} layers, {s['n']}x{s['n']} @ {s['pitch']}, {'Cu' if s['fill'] else 'open'}"


def one(spec):
    """!
    @brief Parts 1 and 2 for one board.
    @param spec dict.
    @return dict with the reference maxima, the model maxima with vias, the program's maximum without vias and the null-via effects.
    """
    pc.load_libraries()
    p = refs.make_problem(spec)
    ref = refs.reference(spec)
    out = {"spec": spec, "t_with": ref["t_with"], "t_without": ref["t_without"], "E": ref["E"], "prog_nv": pc.max_rise(hz.no_vias(p), "lumped", 0.5), "t": {}, "null": {}}
    for n in NAMES:
        with refs.VARIANTS[n]():
            out["t"][n] = pc.max_rise(p, "lumped", 0.5)
    # the same board with vias that conduct nothing: no copper in the barrel, no fill
    pn = refs.make_problem(spec)
    pn.board.via_plating = 1e-12
    for v in pn.vias:
        v.fill_k = 0.0
    for n in ("L_zone_r", "L_zone"):
        out["null"][n] = hz.effect(pn, "lumped", refs.VARIANTS[n], 0.5, hz.no_vias(pn))
    return out


def fvm_check(spec):
    """!
    @brief Part 3 for one board: the via effect of the corrected FVM at 0.25 mm.
    @param spec dict.
    @return tuple (spec, E of the fine-grid reference, E of FVM_fix).
    """
    pc.load_libraries()
    p = refs.make_problem(spec)
    return spec, refs.reference(spec)["E"], hz.effect(p, "fvm", hz.VARIANTS["FVM_fix"][1], 0.25, hz.no_vias(p))


def part4():
    """!
    @brief Part 4: the decimation of the potential integrals, printed.
    @return None.
    """
    from pcbthermal import lumped
    print("\n## 4. Decimation of the potential integrals\n")
    print("Zone model, peak of A (generation 1 W, 0.3 W to the core) on concentric discs, 0.2 mm cells, outer radius 5.6 mm; ratio to the closed form of the annulus:\n")
    print("| core radius mm | cells of A | strided, 700 kept | block, 700 kept | every cell |\n| --: | --: | --: | --: | --: |")
    dx = 0.2e-3
    n = int(24e-3 / dx)
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot((x + 0.5) * dx - 12e-3, (y + 0.5) * dx - 12e-3)
    S = 0.0136
    for rc in (1.5e-3, 3.4e-3, 4.5e-3):
        wc = (r < rc).astype(float)
        wa = ((r >= rc) & (r < 5.6e-3)).astype(float)
        a_eq = math.sqrt((wa.sum() + wc.sum()) * dx * dx / math.pi)
        rc_eq = math.sqrt(wc.sum() * dx * dx / math.pi)
        ex = lz.annulus_excess(S, rc_eq, a_eq, 0.3, 0.7)
        vals = [lz.potential_excess(wa, wc, 0.3, 0.7, S, dx, dx, decimation=d) / ex for d in ("stride", "block")]
        vals.append(lz.potential_excess(wa, wc, 0.3, 0.7, S, dx, dx, max_cells=10 ** 5) / ex)
        print(f"| {rc * 1e3:.1f} | {int(wa.sum())} | " + " | ".join(f"{v:.3f}" for v in vals) + " |")
    print("\nProgram (`lumped._footprint_potentials`, at most 900 cells kept), 0.5 mm cells: the peak term phi_mean - phi_min and the link term phi_bnd - phi_mean with the "
          "decimation of the program and with every cell (a disc: 0.25 for both in the continuum):\n")
    print("| footprint | cells | peak, program | peak, every cell | link, program | link, every cell | link ratio |\n| :-- | --: | --: | --: | --: | --: | --: |")
    for side in (20, 30, 40, 60):
        m = side + 10
        sq = np.zeros((m, m))
        sq[5:5 + side, 5:5 + side] = 1.0
        yy, xx = np.mgrid[0:m, 0:m]
        disc = (np.hypot(xx + 0.5 - m / 2, yy + 0.5 - m / 2) < side / 2).astype(float)
        for name, cov in ((f"square {side * 0.5:.0f} mm", sq), (f"disc {side * 0.5:.0f} mm", disc)):
            old = lumped._MAX_POTENTIAL_CELLS
            try:
                pm, pb, pn = lumped._footprint_potentials(cov, 0.5e-3, 0.5e-3)
                lumped._MAX_POTENTIAL_CELLS = 10 ** 7
                fm, fb, fn = lumped._footprint_potentials(cov, 0.5e-3, 0.5e-3)
            finally:
                lumped._MAX_POTENTIAL_CELLS = old
            print(f"| {name} | {int(cov.sum())} | {pm - pn:.4f} | {fm - fn:.4f} | {pb - pm:.4f} | {fb - fm:.4f} | {(pb - pm) / (fb - fm):.3f} |")


def main():
    """!
    @brief Run the four parts and print the tables.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--procs", type=int, default=4)
    args = ap.parse_args()
    fam = json.load(open(os.path.join(FOLDER, "out", "family.json")))
    with mp.Pool(args.procs) as pool:
        rows = pool.map(one, [r["spec"] for r in fam], chunksize=1)
    print("## 1. Vias that conduct nothing: the via effect the zone model reports (K; the true effect is 0)\n")
    print("| board | E_ref of the real vias K | L_zone_r K | L_zone K |\n| :-- | --: | --: | --: |")
    for r in rows:
        print(f"| {label(r['spec'])} | {r['E']:.2f} | {r['null']['L_zone_r']:+.2f} | {r['null']['L_zone']:+.2f} |")
    for n in ("L_zone_r", "L_zone"):
        v = [r["null"][n] for r in rows]
        w = [100.0 * r["null"][n] / r["E"] for r in rows]
        print(f"\n{n}: {min(v):+.2f} to {max(v):+.2f} K, {min(w):+.1f} to {max(w):+.1f} % of the effect of the real vias")
    print("\n## 2. Maximum rise with vias against the reference (model minus reference, K; positive: the model is hotter, safe)\n")
    print("| board | reference without vias K | program without vias | reference with vias K | " + " | ".join(NAMES) + " |\n| :-- | --: | --: | --: |" + " --: |" * len(NAMES))
    for r in rows:
        print(f"| {label(r['spec'])} | {r['t_without']:.2f} | {r['prog_nv'] - r['t_without']:+.2f} | {r['t_with']:.2f} | "
              + " | ".join(f"{r['t'][n] - r['t_with']:+.2f}" for n in NAMES) + " |")
    print("\n| variant | mean abs. % of the rise | max abs. % | model cooler (unsafe) |\n| :-- | --: | --: | --: |")
    v0 = [100.0 * (r["prog_nv"] - r["t_without"]) / r["t_without"] for r in rows]
    print(f"| program without vias | {np.mean(np.abs(v0)):.1f} | {np.max(np.abs(v0)):.1f} | {sum(x < 0 for x in v0)} of {len(v0)} |")
    for n in NAMES:
        v = [100.0 * (r["t"][n] - r["t_with"]) / r["t_with"] for r in rows]
        print(f"| {n} | {np.mean(np.abs(v)):.1f} | {np.max(np.abs(v)):.1f} | {sum(x < 0 for x in v)} of {len(v)} |")
    specs = [dict(n=5, pitch=1.2, src=10.0, fill=385.0), dict(n=3, pitch=3.5, src=14.0, fill=0.0), dict(n=5, pitch=0.8, src=14.0, fill=385.0), dict(n=3, pitch=3.0, src=12.0, fill=0.0)]
    with mp.Pool(min(args.procs, 2)) as pool:
        chk = pool.map(fvm_check, specs, chunksize=1)
    print("\n## 3. A second layered reference: the corrected FVM at 0.25 mm against the fine-grid solver (via effect E, K)\n")
    print("| board | fine grid | FVM_fix | difference % |\n| :-- | --: | --: | --: |")
    for spec, e_ref, e_fvm in chk:
        print(f"| {label(spec)} | {e_ref:.3f} | {e_fvm:.3f} | {100.0 * (e_fvm / e_ref - 1.0):+.1f} |")
    part4()


if __name__ == "__main__":
    main()
