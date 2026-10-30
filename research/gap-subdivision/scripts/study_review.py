#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_review.py
@brief Checks of the review of gap-subdivision: does the layered copy reach the same-cell 3D solver when n grows, and what is the 3D solid's excess over the converged answer made of?
@details Question 1 (README 2.4 and the review): the decomposition e_total = e_z + e_xy needs the layered model with n -> infinity sub-gaps to approach the 3D solver run on the
         same in-plane cell (lib/boards.samecell_peak). On pad10-full at 0.5 mm the copy is run with n = 1 to 64 (equal) and 1 to 16 (graded 2:1), the same-cell solver with 32,
         64 and 128 sub-slabs per gap; the limit of n is estimated from the last three equal values (v = v0 + C n^-p).
         Question 2 (README 3.2): the program's 3D solid reads 0.4 to 5 % above the converged graded reference on pad boards. The program's solid3d cuts every gap into 4 equal
         slabs on the plan grid of the cell; the same-cell solver with 4 sub-slabs should reproduce it, and with 32 sub-slabs it gives the in-plane error of the cell alone, so the
         excess splits into the in-plane error and the 4-slab error.
         Question 3 (README 2.2, doubt 1): the graded reference of the pad boards rests on a fitted power law; a second solver (resolved3d, uniform plane grid) is refined in the
         plane on two pad boards and extrapolated the same way.
         Usage: .venv/bin/python research/gap-subdivision/scripts/study_review.py [1] [2] [3]   (from the repository root; about 10 minutes for 1, 2 minutes for 2, 10 minutes for 3). Output: out/review.txt.
"""

import json
import math
import sys
from dataclasses import replace

import _bootstrap as BS
import boards as B
import gapnodes as GN

BASE = B.Board("pad", layers=2, gap=1.6, copper=35.0, size=30.0, source=3.0, pad=10.0, pad_layers=(0,))


def say(fh, text):
    """!
    @brief Print a line and write it to the output file.
    @param fh Open output file.
    @param text Line of text.
    @return None.
    """
    print(text, flush=True)
    fh.write(text + "\n")


def limit_of_n(fh):
    """!
    @brief Question 1: the layered copy against the same-cell 3D solver as n grows (pad10-full, 0.5 mm).
    @param fh Open output file.
    @return None.
    """
    p = B.problem(BASE)
    sc = {ns: B.samecell_peak(BASE, 0.5, ns, p) for ns in (32, 64, 128)}
    say(fh, "1. same-cell 3D solver, pad10-full, 0.5 mm: " + ", ".join(f"{ns} sub-slabs {v:.4f} K" for ns, v in sc.items()))
    ref = sc[128]
    eq = {}
    for grading, ns in (("equal", (1, 2, 4, 8, 16, 32, 64)), ("graded", (1, 2, 4, 8, 16))):
        vals = []
        for n in ns:
            v = GN.run(p, 0.5, n, "all", grading)["peak"]
            vals.append(f"n={n} {100 * (v / ref - 1):+.3f}")
            if grading == "equal":
                eq[n] = v
        say(fh, f"   copy, {grading:6s} sub-gaps, error against 128 sub-slabs (%): " + "  ".join(vals))
    # Limit of n from the last three equal values, v = v0 + C n^-p with n doubling: ratio of the differences = 2^p
    v1, v2, v3 = eq[16], eq[32], eq[64]
    r = (v2 - v1) / (v3 - v2)
    v0 = v3 + (v3 - v2) / (r - 1.0)
    say(fh, f"   fitted limit of the copy (n = 16, 32, 64): {v0:.4f} K, {100 * (v0 / ref - 1):+.3f} % from the same-cell solver; order p = {math.log2(r):.2f}")


def solid_excess(fh):
    """!
    @brief Question 2: the program's 3D solid against the same-cell solver with 4 and 32 sub-slabs, on six pad boards (0.5 mm).
    @param fh Open output file.
    @return None.
    """
    refs = json.loads((BS.OUT / "refs_pads.json").read_text())
    say(fh, "2. error against the converged graded reference (%), 0.5 mm cell: program 3D solid | same-cell solver, 4 sub-slabs | same-cell, 32 sub-slabs (in-plane error) | 4-slab part | program FVM")
    boards = [("pad6-full", replace(BASE, pad=6.0)), ("pad10-full", BASE), ("pad20-full", replace(BASE, pad=20.0)), ("gap0.1-full", replace(BASE, gap=0.1)),
              ("gap3.2-full", replace(BASE, gap=3.2)), ("pad10-empty", replace(BASE, empty_layers=(1,)))]
    for tag, bd in boards:
        p = B.problem(bd)
        ref = refs[f"{tag}|0.5"]["peak"]
        s3 = B.program_peak(bd, "solid3d", 0.5, p)
        fv = B.program_peak(bd, "fvm", 0.5, p)
        s4, s32 = B.samecell_peak(bd, 0.5, 4, p), B.samecell_peak(bd, 0.5, 32, p)
        e = lambda v: 100 * (v / ref - 1)                                     # noqa: E731
        say(fh, f"   {tag:12s} ref {ref:8.3f} K   solid3d {e(s3):+6.2f}   same-cell 4 {e(s4):+6.2f}   same-cell 32 {e(s32):+6.2f}   4-slab {100 * (s4 / s32 - 1):+6.2f}"
                f"   FVM {e(fv):+6.2f} (gap alone {100 * (fv / s32 - 1):+6.2f})")


def second_solver(fh):
    """!
    @brief Question 3: the converged graded reference of two pad boards against the uniform-grid solver of bare-spot-under-source refined in the plane (0.5, 0.25, 0.125 mm, 16 sub-slabs).
    @param fh Open output file.
    @return None.
    """
    refs = json.loads((BS.OUT / "refs_pads.json").read_text())
    say(fh, "3. graded reference against a second solver (resolved3d, uniform plane grid, 16 sub-slabs per gap, read on the 0.5 mm cell), limit fitted on the three grids")
    for tag, bd in (("pad6-full", replace(BASE, pad=6.0)), ("pad10-full", BASE)):
        p = B.problem(bd)
        vals = [B.resolved_peak(bd, 0.5, dx, 16, p)["peak"] for dx in (0.5, 0.25, 0.125)]
        r = (vals[0] - vals[1]) / (vals[1] - vals[2])
        v0 = vals[2] - (vals[1] - vals[2]) / (r - 1.0)
        ref = refs[f"{tag}|0.5"]["peak"]
        say(fh, f"   {tag:12s} resolved3d " + " / ".join(f"{v:.3f}" for v in vals) + f" K, limit {v0:.3f} K (order {math.log2(r):.2f}); graded reference {ref:.3f} K;"
                f" difference {100 * (v0 / ref - 1):+.2f} %")


def main(argv):
    """!
    @brief Run the review checks.
    @param argv Question numbers ("1", "2", "3"; none: all).
    @return None.
    """
    parts = argv or ["1", "2", "3"]
    with open(BS.OUT / "review.txt", "w") as fh:
        if "1" in parts:
            limit_of_n(fh)
        if "2" in parts:
            solid_excess(fh)
        if "3" in parts:
            second_solver(fh)


if __name__ == "__main__":
    main(sys.argv[1:])
