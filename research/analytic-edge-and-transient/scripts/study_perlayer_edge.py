#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_perlayer_edge.py
@brief Question A: the per-layer Robin edge of the Analytic steady model against the common parameter of the program.

@details Part 1 (--part 1): the idealised model solved by two independent methods. The sheets of analytic._effective_sheet with the TRUE per-layer Robin edge
         (h_side s_l) in the 2D finite-difference solver `sheet_fd` of research/analytic-edge-spatial (0.5 and 0.25 mm, Richardson), against the program (common beta),
         the per-layer iteration of lib/robin_perlayer.py, and the cheap rule "beta of the heated layer". Shows that the iteration converges to the exact solution of
         the idealised model (any deviation left is the idealisation, not the edge treatment), the GMRES iterations and the time.
         Part 2 (--part 2): the 54 boards outside the first study (9 stacks x h_side 10, 50, 200 x part at the centre and the corner, as part 3 of
         study_review_checks.py) against the FVM at 0.5 mm: error of the hottest rise of the program, the per-layer iteration and the heated-layer beta.
         Run from the repository root: .venv/bin/python research/analytic-edge-and-transient/scripts/study_perlayer_edge.py [--part 1|2]
"""

import argparse
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(ROOT))
sys.path.insert(0, os.path.join(ROOT, "lib"))
sys.path.insert(0, os.path.join(REPO, "research", "analytic-edge-spatial", "scripts"))
sys.path.insert(0, os.path.join(REPO, "research", "analytic-edge-spatial", "lib"))
sys.path.insert(0, REPO)

import robin_perlayer as RP            # noqa: E402
import study_review_checks as R        # noqa: E402
import cases                           # noqa: E402
from pcbthermal import analytic        # noqa: E402

OUT = os.path.join(ROOT, "out")

SETS = (("advanced 4 L", 4, True, (1, 1, 1, 1)), ("advanced 6 L", 6, True, (1,) * 6), ("advanced 8 L", 8, True, (1,) * 8),
        ("advanced 4 L partial", 4, True, (0.4, 1, 1, 0.4)), ("advanced 4 L 0.2", 4, True, (0.2, 0.2, 1, 1)),
        ("2 L top full, bottom 0.2", 2, False, (1, 0.2)), ("2 L top full, bottom 0.5", 2, False, (1, 0.5)), ("2 L top 0.2, bottom full", 2, False, (0.2, 1)),
        ("1 L", 1, False, (1,)))


def part_1():
    """!
    @brief The iteration against the independent finite-difference solution of the same sheets.
    @return None.
    """
    print("1. per-layer Robin against the 2D finite differences of the same sheets (true per-layer edge; Richardson from 0.5 and 0.25 mm)")
    for label, layers, adv, fills in SETS[:1] + SETS[5:8] + (("2 L equal 1/1", 2, False, (1, 1)),):
        for hs in (50.0, 200.0):
            p = R.board(layers, adv, hs, "corner", fills)
            t0 = time.perf_counter()
            prog = analytic.solve_steady(p, 1.0).t_max - cases.T0
            t_prog = time.perf_counter() - t0
            t0 = time.perf_counter()
            r = RP.solve(p, 1.0)
            t_pl = time.perf_counter() - t0
            h = RP.solve(p, 1.0, per_layer=False, beta_rule="heated")["t_max"] - cases.T0
            sh = r["sh"]
            rect = analytic._equivalent_rectangle(p.heaters[0].polygon, sh["W"], sh["H"])
            a, b = (R.sheet_fd(sh, p.board, rect, p.total_power(), d) for d in (0.5e-3, 0.25e-3))
            ext = b + (b - a) / 3.0
            x = r["t_max"] - cases.T0
            print(f"  {label:26s} h_side {hs:3.0f}: FD {ext:8.3f} K | program {prog:8.3f} ({100 * (prog / ext - 1):+6.2f} %) | per-layer {x:8.3f} ({100 * (x / ext - 1):+6.2f} %, "
                  f"{r['iterations']} matvecs, balance {r['balance']:.5f}) | heated-layer beta {h:8.3f} ({100 * (h / ext - 1):+6.2f} %) | time {t_prog:.2f} s -> {t_pl:.2f} s", flush=True)
    print()


def part_2():
    """!
    @brief The 54 boards against the FVM at 0.5 mm.
    @return None.
    """
    print("2. 54 boards: error of the hottest rise against the FVM at 0.5 mm (percent); program = common beta of the program")
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for label, layers, adv, fills in SETS:
        for hs in (10.0, 50.0, 200.0):
            for pos in ("centre", "corner"):
                p = R.board(layers, adv, hs, pos, fills)
                f = cases.rise(p, "fvm", 0.5)
                sh = analytic._effective_sheet(p, 1.0)
                rat = sh["slab"] / sh["S"]
                share = float(sh["h_edge"].sum() / sh["h_tot"])
                prog = analytic.solve_steady(p, 1.0).t_max - cases.T0
                t0 = time.perf_counter()
                pl = RP.solve(p, 1.0)
                dt = time.perf_counter() - t0
                he = RP.solve(p, 1.0, per_layer=False, beta_rule="heated")["t_max"] - cases.T0
                e = [100 * (v / f - 1) for v in (prog, pl["t_max"] - cases.T0, he)]
                print(f"  {label:26s} h_side {hs:3.0f} {pos:6s} FVM {f:7.2f} | slab/S spread {rat.max() / rat.min():5.2f} edge share {share:.2f} | program {e[0]:+6.2f} "
                      f"per-layer {e[1]:+6.2f} (it {pl['iterations']:2d}, {dt:.1f} s) heated-beta {e[2]:+6.2f}", flush=True)
                rows.append((label, hs, pos, rat.max() / rat.min(), share, *e, pl["iterations"]))
    arr = np.array([r[3:] for r in rows], dtype=float)
    np.savetxt(os.path.join(OUT, "perlayer_54.txt"), arr, header="spread share err_program err_perlayer err_heated iterations")
    print(f"  summary ({len(rows)} boards): max |err| program {np.abs(arr[:, 2]).max():.2f} %, per-layer {np.abs(arr[:, 3]).max():.2f} %, heated-beta {np.abs(arr[:, 4]).max():.2f} %; "
          f"mean |err| {np.abs(arr[:, 2]).mean():.2f} / {np.abs(arr[:, 3]).mean():.2f} / {np.abs(arr[:, 4]).mean():.2f} %; matvecs mean {arr[:, 5].mean():.1f}, max {arr[:, 5].max():.0f}")
    print()


def part_3():
    """!
    @brief The per-layer iteration around the complete program solve (vias and a heatsink) against the FVM at 0.5 mm.
    @return None.
    """
    import perlayer_local as PL
    print("3. per-layer edge around the complete solve: corner part with a 4 x 4 via array and a 30 x 30 mm heatsink (h_extra 100 W/m2K) on layer 1, h_side 200")
    for label, layers, adv, fills in (SETS[5], SETS[7], SETS[0], SETS[3]):
        for with_sink in (False, True):
            p = R.board(layers, adv, 200.0, "corner", fills)
            p.add_via_array((1.0, 1.0, 9.0, 9.0), 4, 4, diameter=0.3)
            if with_sink:
                p.add_heatsink(1, 100.0, rect=(0, 0, 30, 30))
            f = cases.rise(p, "fvm", 0.5)
            t0 = time.perf_counter()
            prog = analytic.solve_steady(p, 1.0).t_max - cases.T0
            t1 = time.perf_counter()
            pl = PL.solve(p, 1.0)
            t2 = time.perf_counter()
            x = pl["t_max"] - cases.T0
            print(f"  {label:26s} {'vias+sink' if with_sink else 'vias     '}: FVM {f:7.2f} | program {100 * (prog / f - 1):+6.2f} % ({t1 - t0:.1f} s) | per-layer {100 * (x / f - 1):+6.2f} % "
                  f"({pl['matvecs']} full solves, {t2 - t1:.1f} s)", flush=True)
    print()


def main(argv=None):
    """!
    @brief Run the parts.
    @param argv Arguments.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", type=int, default=0)
    args = ap.parse_args(argv)
    if args.part in (0, 1):
        part_1()
    if args.part in (0, 2):
        part_2()
    if args.part in (0, 3):
        part_3()


if __name__ == "__main__":
    main()
