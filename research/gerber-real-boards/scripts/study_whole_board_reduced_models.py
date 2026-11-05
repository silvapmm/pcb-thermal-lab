#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_whole_board_reduced_models.py
@brief The Lumped and Analytic models against the FVM on a whole imported board (RP2040), 1 W in one part at a time.
@details Question: how far below the FVM do the two reduced models read on the whole imported RP2040 board (52 x 51 mm), which the 24 mm window study
         (`study_lumped_analytic_rule.py`, 1 to 16 %) did not cover? Each heat source gets 1 W in turn (typical stack-up, default convection, the exposed pad of the QFN as proposed),
         the FVM runs at the given cell on the imported copper (faces mapping) and the Lumped and Analytic models run as the program runs them. The rise is the hottest copper node
         minus the ambient; the percentages are (model rise / FVM rise - 1). Not verified: other boards, several parts at once, a physical board.
         Run (from the repository root, the library of boards as PCBT_REAL_BOARDS or the path of the folder with the RP2040 Gerber files as the second argument):
         .venv/bin/python research/gerber-real-boards/scripts/study_whole_board_reduced_models.py 0.25 [path] [U1,U3]   (cell in mm, then optionally the board folder and the designators)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from pcbthermal import api  # noqa: E402
from pcbthermal.gui.import_session import ImportSession  # noqa: E402


def session(path, cell_mm):
    """!
    @brief Open the board in an import session.
    @param path Folder with the Gerber, drill and placement files.
    @param cell_mm Cell of the run in mm.
    @return ImportSession.
    """
    sx = ImportSession()
    sx.set_files(Path(path))
    sx.load()
    sx.cell_mm = cell_mm
    return sx


def main(argv):
    """!
    @brief Print the rise of the three models and the percentages for each heat source.
    @param argv Command-line arguments: cell in mm, optional board folder, optional comma-separated designators.
    @return int Exit code.
    """
    cell = float(argv[1]) if len(argv) > 1 else 0.25
    path = argv[2] if len(argv) > 2 else Path(__import__("os").environ.get("PCBT_REAL_BOARDS", ".")) / "rp2040"
    only = argv[3].split(",") if len(argv) > 3 else None
    names = [p.designator for p in session(path, cell).parts()]
    print("cell %.3g mm, %d parts; 1 W in one part at a time" % (cell, len(names)))
    for d in names:
        if only and d not in only:
            continue
        sx = session(path, cell)
        sx.set_part(d, power=1.0)
        prob = sx.build_problem()
        if not prob.heaters:
            continue                                          # Not a heat source (connectors listed only)
        sim = api.simulate(prob, api.SolverOptions(models=("fvm", "lumped", "analytic"), cell_mm=cell))
        rise = {m: r.t_max - prob.board.ambient for m, r in sim.results.items()}
        print("%-5s fvm %.2f K  lumped %+.1f %%  analytic %+.1f %%" % (d, rise["fvm"], 100 * (rise["lumped"] / rise["fvm"] - 1), 100 * (rise["analytic"] / rise["fvm"] - 1)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
