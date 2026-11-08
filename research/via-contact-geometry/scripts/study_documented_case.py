#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_documented_case.py
@brief The cold-spot board of docs/theory.md 2.2 under the candidate couplings: cold spot and via effect of the FVM and FDM, 1 to 0.125 mm.
@details Same board and measures as research/via-partial-copper/scripts/study_documented_case.py (`copper_edge_board` of tests/test_maximum_principle.py), variants `current`,
         `sheet`, `contact_geo`, `contact` of lib/contact.py. The 3D solid of that study had not converged (0.70 / 2.86 / 7.20 / 10.74 K at 1 to 0.125 mm), so no reference column here.
         Run from the repository root: `.venv/bin/python research/via-contact-geometry/scripts/study_documented_case.py`.
"""

import logging
import sys

import _bootstrap

sys.path.insert(0, str(_bootstrap.REPO / "tests"))
import contact as CT  # noqa: E402
from test_maximum_principle import cold_spot, copper_edge_board, network, positive_entries

logging.disable(logging.WARNING)


def layered(problem, model, cell):
    """!
    @brief Maximum copper rise, the cold spot of the test and the positive entries of one layered solve.
    @param problem Problem.
    @param model "fvm" or "fdm".
    @param cell Cell in mm.
    @return Tuple (max rise, cold spot, positive entries).
    """
    net = network(problem, model, cell)
    theta, _ = net.solve_steady()
    spot = cold_spot(problem, net, theta) if problem.vias else 0.0
    return float(theta[:problem.board.layers].max()), spot, positive_entries(net)[0]


def main():
    """!
    @brief Print the table.
    @return None.
    """
    print(f"{'model':5s} {'variant':12s} {'cell':>6s} {'effect K':>9s} {'cold spot K':>12s} {'pos':>6s}")
    for model in ("fvm", "fdm"):
        for cell in (1.0, 0.5, 0.25, 0.125):
            b = copper_edge_board()
            b.vias = []
            base = layered(b, model, cell)[0]
            for variant in ("current", "sheet", "contact_geo", "contact"):
                with CT.patched(variant):
                    t, spot, pos = layered(copper_edge_board(), model, cell)
                print(f"{model:5s} {variant:12s} {cell:6.3f} {base - t:9.2f} {spot:12.2f} {pos:6d}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
