#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_real_windows.py
@brief How much does the star coupling of the via move the maximum temperature of windows of a real board with its plated holes as vias?
@details The windows are those of research/memory-guard (the CO60 board cut to 40 and 80 mm, plated holes as vias, copper full or in stripes; needs `PCBT_REAL_BOARDS`, the folder of
         the downloaded boards). The FVM runs at 1 and 0.5 mm on the program tree given with `--tree` (a checkout of the commit before the star coupling for "before"); the
         maximum rise and the number of positive off-diagonal entries of K are printed, so that two runs can be compared by eye.
         Run from the repository root: `.venv/bin/python research/via-star-coupling/scripts/study_real_windows.py --tree .`.
"""

import argparse
import logging
import os
import sys


def main():
    """!
    @brief Print the maximum temperature of the windows.
    @return None.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("@details")[0])
    ap.add_argument("--tree", default=os.getcwd(), help="root of the program tree")
    a = ap.parse_args()
    tree = os.path.abspath(a.tree)
    for p in (os.path.join(tree, "research", "memory-guard", "lib"), tree):
        sys.path.insert(0, p)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    logging.disable(logging.WARNING)
    import numpy as np
    import cases
    from pcbthermal import fvm
    print("tree", tree)
    for size in (40.0, 80.0):
        for pattern in ("", "stripes"):
            for cell in (1.0, 0.5):
                spec = dict(family="co60", layers=2, size_mm=size, cell_mm=cell, model="fvm", pattern=pattern, order="layer")
                p = cases.build(spec)
                b = p.board
                net = fvm.Network(p, max(int(round(b.width * 1000.0 / cell)), 2), max(int(round(b.height * 1000.0 / cell)), 2))
                theta, _ = net.solve_steady()
                coo = net.K.tocoo()
                pos = int(((coo.row != coo.col) & (coo.data > 1e-12 * np.abs(net.K.diagonal()).max())).sum())
                print(f"co60 {size:4.0f} mm {pattern or 'full':8s} cell {cell:4.2f} vias {len(p.vias):4d}: max rise {float(theta.max()):8.3f} K, positive entries of K {pos}", flush=True)


if __name__ == "__main__":
    main()
