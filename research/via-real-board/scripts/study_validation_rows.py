#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_validation_rows.py
@brief Which numbers of docs/validation.md move with the via change, and by how much: sections 2 and 2.1 (scenarios and mesh table of the example board), 18 (what fills a via barrel), the via rows of the Lumped and Analytic models, section 5 (the solvers).
@details Re-runs the generators of the program's validation documents twice, on develop as it is and inside the patch (recommended treatment, footprint on the board, no image; the 3D
         solid with the single footprint rule), parses every number of the two markdown tables and prints the rows whose value changes by more than --threshold (default 0.05 K or 0.05 %).
         * section 2 / 2.1: `models-comparison/scripts/validation_study.scenario_table` and `mesh_table`;
         * section 18: the example board with the four fills (open, resin 0.3, paste 8, copper 385 W/mK) at 0.5 mm in the five models, copper-fill gain per model;
         * Lumped and Analytic columns are expected unchanged (the Lumped through `gz_via`); the script prints their difference as proof;
         * section 5: the direct/CG/SOR table is recomputed by `models-comparison/scripts/solver_equivalence.py` on the example board only if --solvers is given (the block SOR
           replaces the program's SOR rule on boards with vias; the other boards are bit-identical).
         The program documents themselves are not edited: this output is the list of changes to make on the adoption branch.
         Run from the repository root: `.venv/bin/python research/via-real-board/scripts/study_validation_rows.py [--threshold 0.05] [--solvers]` (several minutes: the 3D solid columns).
"""

import _bootstrap  # noqa: F401  (puts the import paths of this investigation in order)

import argparse
import logging
import re
import sys
from pathlib import Path

import edge_patch as ep
import program_cases as pc
import runs
import solid_patch as sp
from pcbthermal import solid3d
from pcbthermal.examples import example_board

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "research" / "models-comparison" / "scripts"))

NUM = re.compile(r"-?\d+\.?\d*")


def numbers(table):
    """!
    @brief Parse a markdown table into rows of (label, [numbers]).
    @param table Markdown text of a table (header lines are skipped).
    @return list of (label, list of floats found in the cells after the first; a "(+1.2 %)" counts as a separate number).
    """
    rows = []
    for line in table.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set(":-"):
            continue
        nums = [[float(x.replace("−", "-")) for x in NUM.findall(c.replace("−", "-"))] for c in cells[1:]]
        rows.append((cells[0], nums))
    return rows


def compare(title, before, after, threshold):
    """!
    @brief Print the cells of two tables whose numbers differ by more than the threshold.
    @param title Name of the table.
    @param before Markdown table from develop.
    @param after Markdown table from the patched run.
    @param threshold Smallest difference reported (same unit as the table).
    @return None.
    """
    print(f"\n## {title}\n")
    head = [c.strip() for c in before.splitlines()[0].strip().strip("|").split("|")]
    moved = 0
    for (la, na), (lb, nb) in zip(numbers(before), numbers(after)):
        for col, (xa, xb) in enumerate(zip(na, nb)):
            if xa and xb and abs(xa[0] - xb[0]) > threshold:
                moved += 1
                print(f"* {la} | {head[col + 1] if col + 1 < len(head) else col}: {xa[0]:.2f} -> {xb[0]:.2f} ({xb[0] - xa[0]:+.2f})")
    print(f"({moved} cells moved by more than {threshold:g})")


def fills_table(cell_mm=0.5):
    """!
    @brief Section 18 of validation.md: the example board with each fill in the five models.
    @param cell_mm Cell in mm.
    @return str Markdown table of the maximum temperature (ambient plus rise) per model and fill.
    """
    lines = ["| fill | fvm | fdm | solid3d | lumped | analytic |", "| :-- | --: | --: | --: | --: | --: |"]
    for name, k in (("open", 0.0), ("resin 0.3", 0.3), ("paste 8", 8.0), ("copper 385", 385.0)):
        p = example_board()
        for v in p.vias:
            v.fill_k = k
        # No patch of its own: the caller has installed (or not) the treatment, and the copies of the program cannot be nested
        row = [runs.rise(p, m, cell_mm, runs.PROGRAM) for m in ("fvm", "fdm", "solid3d", "lumped", "analytic")]
        lines.append(f"| {name} | " + " | ".join(f"{x + p.board.ambient:.2f}" for x in row) + " |")
    return "\n".join(lines)


def run_tables(patched):
    """!
    @brief The generators of the validation tables, on develop or patched.
    @param patched True: inside the recommended treatment (and the single 3D footprint rule); the Lumped model sees gz_via.
    @return dict name -> markdown text.
    """
    import validation_study as vs
    out = {}
    with solid3d.size_limit(2_000_000):
        if patched:
            with ep.patched_edge(**runs.MW_BOARD), sp.patched("disc_eta"), ep.lumped_sees_gz_via():
                out["2"] = vs.scenario_table(1.0)
                out["2.1"] = vs.mesh_table()
                out["18"] = fills_table()
        else:
            out["2"] = vs.scenario_table(1.0)
            out["2.1"] = vs.mesh_table()
            out["18"] = fills_table()
    return out


def main(argv=None):
    """!
    @brief Run both sets of tables and print what moves.
    @param argv Command line.
    @return None.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.05)
    ap.add_argument("--solvers", action="store_true")
    a = ap.parse_args(argv)
    logging.disable(logging.WARNING)
    pc.load_libraries()
    before = run_tables(False)
    after = run_tables(True)
    for key, title in (("2", "validation.md section 2 (scenarios, 1 mm; values are degC, then error against the FVM in %)"), ("2.1", "validation.md section 2.1 (example board against the cell)"),
                       ("18", "validation.md section 18 (fills of the example board at 0.5 mm, degC)")):
        compare(title, before[key], after[key], a.threshold)
    if a.solvers:
        import solver_equivalence as se
        print("\n## validation.md section 5: run `solver_equivalence.py` on the adoption branch; its example-board rows use the block SOR there (see INTEGRATION.md)\n")
        print(se.__doc__)


if __name__ == "__main__":
    main()
