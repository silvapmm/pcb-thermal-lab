#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_documented_case.py
@brief The board of docs/theory.md 2.2 (30 x 30 mm, two layers, h = 10 W/m2K, the top copper ending at the centre of a 0.3 mm via, a 2 W part beside the edge): the cold spot and the via effect, program against the candidate treatments and the 3D solid.
@details The board is `copper_edge_board` of tests/test_maximum_principle.py. For FVM and FDM at 1, 0.5, 0.25 and 0.125 mm and every variant: the maximum rise on the copper
         with the via, the via effect (rise without the via minus rise with it), the cold spot of the test (window of the via centres plus 1 mm, window minimum minus the minimum on the rim), the
         positive off-diagonal entries. The 3D solid at 1, 0.5, 0.25 and 0.125 mm shows whether the reference has converged (it has not: the effect keeps growing, see the README).
         Run from the repository root: `.venv/bin/python research/via-partial-copper/scripts/study_documented_case.py`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np                                                            # noqa: E402

from pcbthermal import solid3d                                                # noqa: E402

import viavariants as vv                                                      # noqa: E402
from test_maximum_principle import cold_spot, copper_edge_board, network, positive_entries   # noqa: E402


def layered(problem, model, cell):
    """!
    @brief Maximum copper rise, the cold spot of the test and the positive entries for one layered solve.
    @param problem Problem.
    @param model "fvm" or "fdm".
    @param cell Cell in mm.
    @return Tuple (max rise, cold spot, positive entries, minimum rise).
    """
    net = network(problem, model, cell)
    theta, _ = net.solve_steady()
    keep = np.ones(theta.shape, dtype=bool) if net.drop is None else ~net.drop
    spot = cold_spot(problem, net, theta) if problem.vias else 0.0
    return float(theta[:problem.board.layers].max()), spot, positive_entries(net)[0], float(theta[keep].min())


def main():
    """!
    @brief Print the table.
    @return None.
    """
    print("3D solid (reference, not converged)")
    for cell in (1.0, 0.5, 0.25, 0.125):
        a, b = copper_edge_board(), copper_edge_board()
        b.vias = []
        ta = solid3d.solve_steady(a, cell).t_max
        tb = solid3d.solve_steady(b, cell).t_max
        print(f"  cell {cell:5.3f}  via effect {tb - ta:7.2f} K")
    print(f"{'model':5s} {'variant':8s} {'cell':>6s} {'max rise':>9s} {'effect':>8s} {'cold spot':>10s} {'pos':>6s} {'min rise':>9s}")
    for model in ("fvm", "fdm"):
        for cell in (1.0, 0.5, 0.25, 0.125):
            b = copper_edge_board()
            b.vias = []
            base = layered(b, model, cell)[0]
            for variant in ("current", "sheet", "plane", "star"):
                with vv.patched(variant):
                    t, spot, pos, tmin = layered(copper_edge_board(), model, cell)
                print(f"{model:5s} {variant:8s} {cell:6.3f} {t:9.2f} {base - t:8.2f} {spot:10.2f} {pos:6d} {tmin:9.2f}", flush=True)


if __name__ == "__main__":
    main()
