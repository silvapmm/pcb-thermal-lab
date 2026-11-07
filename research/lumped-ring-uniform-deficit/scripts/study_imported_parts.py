#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_imported_parts.py
@brief The parts of the imported boards of reduced-models-imported-passives on the uniform sheet and on the imported copper: Lumped as the program runs it against the proposed first ring.
@details Same parts as research/reduced-models-imported-passives (one part at a time, 1 W, cell 0.5 mm, the board's stack-up and films). Variants built with that folder's
         lib/variants.py: "uniform" (one zone per layer at the layer-average fill; the vias and the outline are kept, as there) and "imported" (the masks, FVM faces mapping). For each part:
         FVM on the variant (the reference), Analytic, Lumped as the program runs it and Lumped with the candidate runner.PROPOSAL (default: the capped first ring; LRU_PROPOSAL="first 1.5 cells" for the alternative). The rise is that of the hottest node.
         CO60 is not run on the imported copper (3.9 GB peak in the earlier study); its uniform sheet is run only when the memory estimate of the program is below 2.5 GB.
         Output: a table and out/imported_parts_<board>.json (git-ignored). Usage, from the repository root (one process, peak below 1 GB for rp2040 and oswlight):
         eval "$(pcb-library/scripts/link_env.sh)"; QT_QPA_PLATFORM=offscreen .venv/bin/python research/lumped-ring-uniform-deficit/scripts/study_imported_parts.py rp2040 [imported]
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lib"))
sys.path.insert(0, str(HERE.parents[1] / "reduced-models-imported-passives" / "lib"))

import runner as R  # noqa: E402
import variants as V  # noqa: E402
from pcbthermal import SolverOptions, simulate  # noqa: E402


def rise(p, model, cell):
    """!
    @brief Rise of the hottest node.
    @param p Problem.
    @param model Model key.
    @param cell Cell in mm.
    @return float K.
    """
    return simulate(p, SolverOptions(models=(model,), cell_mm=cell)).results[model].t_max - p.board.ambient


def main(argv):
    """!
    @brief Run one board.
    @param argv board folder name, optional "imported" to run the imported copper too, optional comma-separated designators.
    @return int Exit code.
    """
    board = argv[1]
    with_imported = len(argv) > 2 and argv[2] == "imported"
    only = argv[3].split(",") if len(argv) > 3 else None
    cell = 0.5
    sx, prob = V.open_board(board, cell)
    rows = []
    for h in prob.heaters:
        if only is not None and h.name not in only:
            continue
        q = V.only_heater(prob, h.name)
        row = {"board": board, "part": h.name}
        variants = {"uniform": V.variant(q, "uniform")}
        if with_imported:
            variants["imported"] = q
        for vname, pp in variants.items():
            ref = rise(pp, "fvm", cell)
            row[vname] = {"fvm": ref, "analytic": rise(pp, "analytic", cell)}
            for c in ("program", R.PROPOSAL):
                R.LL.configure(*R.CANDIDATES[c])
                row[vname][c] = rise(pp, "lumped", cell)
        rows.append(row)
        msg = " | ".join(f"{vn}: FVM {r['fvm']:.1f} A {100 * (r['analytic'] / r['fvm'] - 1):+.0f}% L {100 * (r['program'] / r['fvm'] - 1):+.0f}% -> {100 * (r[R.PROPOSAL] / r['fvm'] - 1):+.0f}%"
                         for vn, r in ((vn, row[vn]) for vn in variants))
        print(f"{h.name:6s} {msg}", flush=True)
    R.OUT.mkdir(exist_ok=True)
    (R.OUT / f"imported_parts_{board}_{R.PROPOSAL.replace(' ', '-')}.json").write_text(json.dumps(rows, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
