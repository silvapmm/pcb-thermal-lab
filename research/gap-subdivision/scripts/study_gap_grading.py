#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_gap_grading.py
@brief Does the way the gap is cut matter more than the number of nodes? Equal, symmetric geometric and one-sided (thin at the top copper) sub-gaps of ratio 1.5 to 4, against the 3D solver on the same cell.
@details Question: the error of the through-thickness discretisation falls only like 1 / n with equal sub-gaps (study_gap_nodes.py, part B), because the edge of the pad is singular in the laminate. Can a graded cut
         reach the same accuracy with fewer nodes (fewer unknowns)? The probe boards are pad10-full, pad20-empty and gap3.2-full of the baseline at the 0.5 mm cell; the error is read against the 3D
         solver on the same in-plane cell with 32 sub-slabs per gap (through-thickness error alone, lib/boards.samecell_peak) and against the converged graded solver (what the user sees).
         Output: the table on the screen and baseline/gap_grading.csv.
         Usage: .venv/bin/python research/gap-subdivision/scripts/study_gap_grading.py   (from the repository root; a minute or two).
"""

import csv
import json

import _bootstrap as BS
import boards as B
import gapnodes as G
import study_baseline_pads as SP

CELL = 0.5
NS = (2, 3, 4, 6, 8)


def main():
    """!
    @brief Run the grading variants and write the table.
    @return None.
    """
    refs = json.loads((BS.OUT / "refs_pads.json").read_text())
    rows_by_tag = {t: bd for _, t, bd, _, _ in SP.rows()}
    out = []
    for tag in ("pad10-full", "pad20-empty", "gap3.2-full"):
        bd = rows_by_tag[tag]
        p = B.problem(bd)
        rc = refs[f"{tag}|{CELL}"]["peak"]
        rz = B.samecell_peak(bd, CELL, 32, p)
        print(f"\n{tag}: converged {rc:.3f} K, same-cell 3D {rz:.3f} K; error (z | total) in percent, n = {' '.join(str(n) for n in NS)}")
        for grading, ratio in (("equal", 1.0), ("graded", 1.5), ("graded", 2.0), ("graded", 3.0), ("graded", 4.0), ("top", 1.5), ("top", 2.0), ("top", 3.0), ("top", 4.0)):
            vals = [G.run(p, CELL, n, "all", grading, ratio=ratio)["peak"] for n in NS]
            z = [100 * (v / rz - 1) for v in vals]
            t = [100 * (v / rc - 1) for v in vals]
            print(f"  {grading:7s} ratio {ratio:3.1f}  " + " ".join(f"{x:+6.2f}" for x in z) + "  |  " + " ".join(f"{x:+6.2f}" for x in t))
            for n, a, b in zip(NS, z, t):
                out.append({"board": tag, "grading": grading, "ratio": ratio, "n": n, "err_z_pct": round(a, 4), "err_total_pct": round(b, 4)})
    with open(BS.BASELINE / "gap_grading.csv", "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        wr.writeheader()
        wr.writerows(out)


if __name__ == "__main__":
    main()
