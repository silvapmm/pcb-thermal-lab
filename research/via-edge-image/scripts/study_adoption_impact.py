#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_adoption_impact.py
@brief What the mirror image would move in the frozen-number boards, plus the matrix properties, the heat balance and the cost per via of the edge term.
@details (1) For every board of the regression harness that has vias: the number of vias with a straight wall within 6 cells, and the change of the FVM and FDM maximum temperature with the image (FVM only is changed)
         at 2, 1 and 0.5 mm. (2) On the edge test board: the FVM matrix of the program and with the image: symmetry, row sums (the via part has zero row sum), smallest diagonal, positive off-diagonal count,
         and the heat balance reported by `simulate`. (3) Time of `edge_term` per via.
         Run from the repository root: `.venv/bin/python research/via-edge-image/scripts/study_adoption_impact.py`.
"""

import logging
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lib"))
import paths  # noqa: E402,F401
import edge_hook as eh  # noqa: E402
import edge_reference as er  # noqa: E402
import program_cases as pc  # noqa: E402

sys.path.insert(0, os.path.join(paths.REPO, "tests", "regression"))
import regress_boards as rbd  # noqa: E402

from pcbthermal import SolverOptions, simulate  # noqa: E402
from pcbthermal import fvm  # noqa: E402


def board_impact():
    """!
    @brief Table of the frozen boards with vias: vias near a wall and the change of T_max with the image.
    @return None.
    """
    # Since feature/via-edge-image the program has the image: the baseline is the program with its reach set to zero ("none"), the change is that of the
    # program's image ("program") and, for the record, of this folder's prototype ("mirror", which also images a side beyond its end)
    print("| board | vias | vias with a wall within 6 cells, prototype rule (2 / 1 / 0.5 mm) | change of FVM T_max, program's image (2 / 1 / 0.5 mm) | the same, prototype |")
    print("| :-- | --: | :-- | :-- | :-- |")
    for name in rbd.board_names():
        p = rbd.build(name)
        if not p.vias:
            continue
        near, dts, dps = [], [], []
        for c in (2.0, 1.0, 0.5):
            near.append(sum(1 for v in p.vias if eh.walls_for(p, v, 6 * c * 1e-3)))
            with eh.patched("none"):
                a = simulate(p, SolverOptions(models=("fvm",), cell_mm=c)).results["fvm"].T.max()
            b = simulate(p, SolverOptions(models=("fvm",), cell_mm=c)).results["fvm"].T.max()
            with eh.patched("mirror"):
                m = simulate(p, SolverOptions(models=("fvm",), cell_mm=c)).results["fvm"].T.max()
            dts.append(f"{b - a:+.4f} K")
            dps.append(f"{m - a:+.4f} K")
        print(f"| {name} | {len(p.vias)} | {' / '.join(map(str, near))} | {' / '.join(dts)} | {' / '.join(dps)} |", flush=True)


def matrix_checks():
    """!
    @brief Symmetry, row sums, positive off-diagonals and heat balance of the FVM with and without the image on the edge board (the via 0.16 mm from the edge, 1 mm cell).
    @return None.
    """
    p = er.edge_board(0.16, True, None, 10.0)
    for mode in ("none", "program"):
        with eh.patched(mode):
            r = simulate(p, SolverOptions(models=("fvm",), cell_mm=1.0)).results["fvm"]
            net = fvm.Network(p, 10, 10)
        K = net.K.tocsr()
        asym = abs(K - K.T).max()
        off = K - __import__("scipy.sparse", fromlist=["diags"]).diags(K.diagonal())
        # The via part alone has zero row sum: compare the row sums with and without vias (the ambient conductance is the only other term)
        q = er.deepcopy_without_via(p)
        with eh.patched("none"):
            K0 = fvm.Network(q, 10, 10).K.tocsr()
        rowdiff = abs(np.asarray((K - K0).sum(axis=1)).ravel()).max()
        print(f"{mode}: T_max {r.T.max():.4f} degC, max |K - K^T| {asym:.1e}, max |row sum(K) - row sum(K without vias)| {rowdiff:.1e} W/K, "
              f"positive off-diagonals {int((off.data > 0).sum())}, heat balance error {r.balance_error:+.2e}")


def cost():
    """!
    @brief Time of the edge term per via at several cells.
    @return None.
    """
    from pcbthermal import viawell
    for c in (1.0, 0.5, 0.25, 0.125):
        dx = c * 1e-3
        cover = np.ones((int(10 / c), int(10 / c)))
        w, r_eff, r_t = viawell.footprint(9.84e-3, 5e-3, 0.15e-3, dx, 0.0, cover)
        t = time.perf_counter()
        for _ in range(50):
            eh.edge_term(w, dx, (9.84e-3, 5e-3), 0.15e-3, [("x", 10e-3)], [float("inf")], "mirror")
        print(f"cell {c:g} mm: footprint {len(w)} cells, edge term {1e3 * (time.perf_counter() - t) / 50:.3f} ms")


if __name__ == "__main__":
    logging.disable(logging.WARNING)
    pc.load_libraries()
    board_impact()
    print()
    matrix_checks()
    print()
    cost()
