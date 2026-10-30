#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_real_board.py
@brief The same variants on the program's example board (100 x 80 mm, four layers, 9 vias under U1, a heatsink), after the simple boards.
@details Question: do the conclusions of `study_variants.py` (lagged and block SOR reach the direct solution; the program's rule does not; SSOR-CG is the fast iterative one) hold on a real
         board with a computed layout, partial copper and several heaters? Cells of 1 mm and 0.5 mm; the sweep cap is 60000 (0.5 mm: 20000) so the run stays short.
         Run from the repository root: `.venv/bin/python research/sor-with-via-couplings/scripts/study_real_board.py`.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))

import boards as bd                                                         # noqa: E402
import sorvia as sv                                                         # noqa: E402
from pcbthermal.examples import example_board                               # noqa: E402


def main():
    """!
    @brief Run the variants on the example board and print the table.
    @return None.
    """
    bd.pc.load_libraries()
    print("| cell (mm) | N | direct T_max (K above ambient) | variant | sweeps / iterations | converged | T_max - direct (K) | max field difference (K) | seconds |")
    print("| --: | --: | --: | :-- | --: | :-- | --: | --: | --: |")
    for cell, cap in ((1.0, 60000), (0.5, 20000)):
        prob = example_board()
        net = bd.net_for(prob, cell)
        th, _ = net.solve_steady("direct")
        head = f"| {cell} | {net.K.shape[0]} | {th.max():.3f} |"
        for v in ("program", "lagged", "block"):
            r = sv.solve_variant(net, v, max_iter=cap)
            print(f"{head} {v} | {r['iterations']} | {r['converged']} | {r['theta'].max() - th.max():+.2e} | {np.abs(r['theta'] - th).max():.1e} | {r['seconds']:.1f} |", flush=True)
        r = sv.ssor_cg(net, 1.0, 1e-9, order="natural")
        print(f"{head} SSOR-CG natural | {r['iterations']} | {r['converged']} | {r['theta'].max() - th.max():+.2e} | {np.abs(r['theta'] - th).max():.1e} | {r['seconds']:.1f} |", flush=True)


if __name__ == "__main__":
    main()
