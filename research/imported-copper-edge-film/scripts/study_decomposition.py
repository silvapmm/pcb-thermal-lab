#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_decomposition.py
@brief Question 1: where does the cool bias of the heater rise of an imported-copper board with an outline come from? Rectangle, aligned and turned squares, drawn and imported, against the 3D truth.
@details 2 layers, copper full inside a 1.2 mm inset (top and bottom), 4 mm heater of 1 W, h_top = h_bottom = 10 W/m2K, h_side given, laminate rule at `n_max` sub-gaps. For every
         shape (rectangle without an outline, square aligned, square at 22.5 and 45 degrees), copper (imported, drawn) and cell, prints the mean rise of the heater and its error against
         the 3D truth (`lib/truth3d.py`, resolved laminate, Richardson-extrapolated by the caller) given on the command line.
         Run: `.venv/bin/python research/imported-copper-edge-film/scripts/study_decomposition.py <h_side> <truth K> <cells> <n_max list>`, for example `200 57.25 1,0.5,0.25,0.125 4,16`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))

import cases                                                                   # noqa: E402
from pcbthermal import laminate                                                # noqa: E402


def main():
    """!
    @brief Print the table.
    @return None.
    """
    hs, truth = float(sys.argv[1]), float(sys.argv[2])
    cells = [float(c) for c in sys.argv[3].split(",")]
    nmaxs = [int(x) for x in sys.argv[4].split(",")]
    print("h_side", hs, "truth", truth, "error % = (program / truth - 1) x 100")
    for nmax in nmaxs:
        for shape, ang in (("rect", 0), ("square", 0), ("square", 22.5), ("square", 45)):
            for kind in ("imported", "drawn"):
                p = cases.build(shape, kind, hs, ang=ang)
                row = []
                for c in cells:
                    with laminate.using(max(0.1e-3, 1.53e-3 / nmax) if nmax > 1 else 0.4e-3, nmax):
                        m = cases.run(p, c)[0]
                    row.append(round(100 * (m / truth - 1), 2))
                print("n_max", nmax, shape, ang, kind, cells, row, flush=True)


if __name__ == "__main__":
    main()
