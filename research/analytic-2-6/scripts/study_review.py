#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review.py
@brief The reviewer's checks of the analytic-2-6 claims: is the error left by the per-layer edge the laminate rule of the FVM, is the FVM reference of the transient
       converged, what makes the local transient slow on the 4-layer board, and does the factor on the vias alone fix it.

@details Part 1: the per-layer edge against the FVM at 0.5 mm with the shipped laminate rule (at most 4 sub-gaps) and with a single laminate link (laminate_n_max 1,
         the layered idealisation that the Analytic shares), on the six worst boards of README 2.3 and 2.4 (corner part, h_side 200).
         Part 2: the FVM time to 63 % of the 4-layer board with vias and a 300 W/m2K heatsink at 1, 0.5 and 0.25 mm (and the FDM at 1 and 0.5 mm).
         Part 3: which element makes the local transient slow: the 4-layer board alone, with vias, with a heatsink and with both, early-time response and time to 63 %
         against the FVM at 0.5 mm (local system K 24, one factor on the whole tile matrix as in the first proposal).
         Part 4: one factor on the whole tile matrix (calibrate_on "all") against a factor on the via couplings only ("vias"), K 16, every board of
         study_transient_both.py plus two with a 300 and a 100 W/m2K heatsink, against the FVM at 0.5 mm.
         Part 5: the frozen example_board (9 vias and a heatsink, first part alone): the FVM at 2, 1 and 0.5 mm, the program and the two calibrations.
         Run from the repository root: .venv/bin/python research/analytic-2-6/scripts/study_review.py [--part N]   (about 3 minutes in all, peak about 1.1 GB)
"""

import argparse
import copy
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(ROOT))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "lib"))
sys.path.insert(0, os.path.join(REPO, "research", "analytic-edge-spatial", "scripts"))
sys.path.insert(0, os.path.join(REPO, "research", "analytic-edge-spatial", "lib"))
sys.path.insert(0, os.path.join(REPO, "tests", "regression"))
sys.path.insert(0, REPO)

import boards26 as B                   # noqa: E402
import local_modal as LM               # noqa: E402
from pcbthermal import SolverOptions, analytic, fdm, fvm, simulate   # noqa: E402


def _zi(t, z, x):
    """!
    @brief Step response at time x by log-time interpolation.
    @param t Times in s.
    @param z Response in K/W.
    @param x Time in s.
    @return float K/W.
    """
    return float(np.interp(np.log(x), np.log(t), z))


def part_1():
    """!
    @brief The per-layer edge against the FVM with and without the laminate sub-gaps.
    @return None.
    """
    import cases                        # noqa: E402  (research/analytic-edge-spatial/lib)
    import perlayer_local as PL         # noqa: E402
    import robin_perlayer as RP         # noqa: E402
    import study_review_checks as R     # noqa: E402
    print("1. hottest-rise error (percent) against the FVM at 0.5 mm with the laminate rule (n_max 4) / with one laminate link (n_max 1); corner part, h_side 200")
    for fills, label in (((1, 0.2), "2 L top full, bottom 0.2"), ((0.2, 1), "2 L top 0.2, bottom full"), ((1, 0.5), "2 L top full, bottom 0.5")):
        for vias in (False, True):
            p = R.board(2, False, 200.0, "corner", fills)
            if vias:
                p.add_via_array((1.0, 1.0, 9.0, 9.0), 4, 4, diameter=0.3)
            f = {n: simulate(p, SolverOptions(cell_mm=0.5, models=("fvm",), laminate_n_max=n)).results["fvm"].t_max - cases.T0 for n in (4, 1)}
            prog = analytic.solve_steady(p, 1.0).t_max - cases.T0
            pl = (PL.solve(p, 1.0) if vias else RP.solve(p, 1.0))["t_max"] - cases.T0
            e = lambda v, n: 100.0 * (v / f[n] - 1.0)   # noqa: E731
            print(f"  {label:26s} {'vias' if vias else '    '}: FVM {f[4]:7.2f} / {f[1]:7.2f} K | program {e(prog, 4):+6.2f} / {e(prog, 1):+6.2f} | "
                  f"per-layer {e(pl, 4):+6.2f} / {e(pl, 1):+6.2f}", flush=True)
    print()


def part_2():
    """!
    @brief Grid convergence of the FVM reference on the 4-layer board.
    @return None.
    """
    import study_transient_both as S     # noqa: E402
    p = dict(S.boards())["4L vias+sink under"]
    print("2. 4 L, vias and a 300 W/m2K heatsink under the part: the reference against the cell")
    for c in (1.0, 0.5, 0.25):
        t0 = time.perf_counter()
        t, z, r = fvm.step_responses(p, cell_mm=c)
        print(f"  FVM {c:4.2f} mm: R {r[0]:.3f} K/W, t63 {B.t63(t, z[:1], r[:1])[0]:6.2f} s, z(1 s) {_zi(t, z[0], 1.0):.3f} K/W ({time.perf_counter() - t0:.1f} s)", flush=True)
    for c in (1.0, 0.5):
        t, z, r = fdm.step_responses(p, cell_mm=c)
        print(f"  FDM {c:4.2f} mm: R {r[0]:.3f} K/W, t63 {B.t63(t, z[:1], r[:1])[0]:6.2f} s", flush=True)
    print()


def part_3():
    """!
    @brief Which local element makes the local transient slow.
    @return None.
    """
    pl, wv, ws = B.plain, B.with_vias, B.with_sink
    print("3. local system K 24 (one factor on the whole tile matrix) against the FVM at 0.5 mm; z(t) / R at 0.1 s and 1 s")
    for name, p in (("plain 4 L", pl(4)), ("4 L vias", wv(pl(4))), ("4 L sink 300", ws(pl(4), 300.0)), ("4 L vias + sink 100", ws(wv(pl(4)), 100.0)),
                    ("4 L vias + sink 300", ws(wv(pl(4)), 300.0)), ("2 L sink 300", ws(pl(), 300.0)), ("2 L vias + sink 300", ws(wv(pl()), 300.0))):
        t, z, r = fvm.step_responses(p, cell_mm=0.5)
        f = B.t63(t, z[:1], r[:1])[0]
        tl, zl, rl, s = LM.step_local(p, 1.0, 300, 24)
        lo = B.t63(tl, zl, rl)[0]
        print(f"  {name:22s} t63 FVM {f:7.2f} local {lo:7.2f} s ({100 * (lo / f - 1):+5.1f} %, s {s:.3f}) | z/R at 0.1 s {_zi(t, z[0], 0.1) / r[0]:.3f} / "
              f"{_zi(tl, zl[0], 0.1) / rl[0]:.3f}, at 1 s {_zi(t, z[0], 1.0) / r[0]:.3f} / {_zi(tl, zl[0], 1.0) / rl[0]:.3f}", flush=True)
    print()


def part_4():
    """!
    @brief One factor on the whole tile matrix against a factor on the vias only.
    @return None.
    """
    import study_transient_both as S     # noqa: E402
    pl, wv, ws = B.plain, B.with_vias, B.with_sink
    extra = [("2L vias+sink 300", ws(wv(pl()), 300.0)), ("4L vias+sink 100", ws(wv(pl(4)), 100.0))]
    print("4. time to 63 % against the FVM at 0.5 mm, local K 16: factor on the whole tile matrix (all) / on the via couplings only (vias)")
    for name, p in S.boards() + extra:
        t, z, r = fvm.step_responses(p, cell_mm=0.5)
        f = B.t63(t, z[:1], r[:1])[0]
        ta, za, ra = analytic.step_responses(p, 1.0)
        a = B.t63(ta, za[:1], ra[:1])[0]
        out = []
        for how in ("all", "vias"):
            tl, zl, rl, s = LM.step_local(p, 1.0, 300, 16, calibrate_on=how)
            lo = B.t63(tl, zl, rl)[0]
            out.append(f"{lo:7.2f} s ({100 * (lo / f - 1):+5.1f} %, s {s:.3f}, R {rl[0]:.3f})")
        print(f"  {name:24s} FVM {f:7.2f} s (R {r[0]:.3f}) | program {100 * (a / f - 1):+6.1f} % | all {out[0]} | vias {out[1]}", flush=True)
    print()


def part_5():
    """!
    @brief The frozen example board, first part alone.
    @return None.
    """
    import regress_boards as RB          # noqa: E402
    p = RB.build("example_board", os.path.join(REPO, "examples"))
    solo = copy.deepcopy(p)
    for k, h in enumerate(solo.heaters):
        h.power = 1.0 if k == 0 else 0.0
        h.profile = None
    print("5. example_board, first part alone: time to 63 % (s)")
    ref = {}
    for c in (2.0, 1.0, 0.5):
        t0 = time.perf_counter()
        t, z, r = fvm.step_responses(solo, cell_mm=c)
        ref[c] = B.t63(t, z[:1], r[:1])[0]
        print(f"  FVM {c:3.1f} mm: {ref[c]:6.2f} s, R {r[0]:.3f} K/W ({time.perf_counter() - t0:.1f} s)", flush=True)
    ta, za, ra = analytic.step_responses(solo, 1.0)
    rows = [("program", B.t63(ta, za[:1], ra[:1])[0])]
    for how in ("all", "vias"):
        tl, zl, rl, s = LM.step_local(solo, 1.0, 300, 16, calibrate_on=how)
        rows.append((f"local K16 {how} (s {s:.3f})", B.t63(tl, zl, rl)[0]))
    for label, v in rows:
        print(f"  {label:26s} {v:6.2f} s: {100 * (v / ref[2.0] - 1):+6.1f} % of the FVM at 2 mm, {100 * (v / ref[0.5] - 1):+6.1f} % of the FVM at 0.5 mm", flush=True)
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
    for k, fn in enumerate((part_1, part_2, part_3, part_4, part_5), start=1):
        if args.part in (0, k):
            fn()


if __name__ == "__main__":
    main()
