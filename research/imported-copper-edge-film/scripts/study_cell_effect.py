#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cell_effect.py
@brief Question 1.2: the cell error of the heater rise at a fixed laminate resolution, for the film on the node and for the film in series, against the same program at the finest cell.
@details Imported copper, full copper inside a 1.2 mm inset, 2 layers; shapes: rectangle without an outline, square aligned (grid lines on the outline at the cells of 1, 0.5, 0.25
         mm), squares at 22.5 and 45 degrees; film switch of `lib/variants.py`. Prints the mean heater rise at every cell and the error against the cell given as reference (the same
         variant), which isolates the cell effect from the laminate resolution and from the idealisation.
         Run: `.venv/bin/python research/imported-copper-edge-film/scripts/study_cell_effect.py <h_side> <cells, coarse to fine; the last is the reference> <n_max> [inset mm, default 1.2]`.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))

import cases                                                                   # noqa: E402
import variants                                                                # noqa: E402
from pcbthermal import laminate                                                # noqa: E402


def main():
    """!
    @brief Print the table.
    @return None.
    """
    hs = float(sys.argv[1])
    cells = [float(c) for c in sys.argv[2].split(",")]
    nmax = int(sys.argv[3])
    cases.set_inset(float(sys.argv[4]) if len(sys.argv) > 4 else 1.2)
    for film in ("node", "series"):
        for shape, ang in (("rect", 0), ("square", 0), ("square", 22.5), ("square", 45)):
            p = cases.build(shape, "imported", hs, ang=ang)
            vals = []
            for c in cells:
                with variants.use(film=film), laminate.using(max(0.1e-3, 1.53e-3 / nmax), nmax):
                    vals.append(cases.run(p, c)[0])
            ref = vals[-1]
            print(film, shape, ang, "values", [round(v, 3) for v in vals], "error vs finest %", [round(100 * (v / ref - 1), 2) for v in vals], flush=True)


if __name__ == "__main__":
    main()
