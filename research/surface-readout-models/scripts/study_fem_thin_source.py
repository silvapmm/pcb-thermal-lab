#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_fem_thin_source.py
@brief Why the FEM's through-thickness term on 35 um copper is smaller than the FVM's: the FEM against the exact one-dimensional term and against the physical range on a small part.
@details Added by the review. On a one-dimensional board (a part over the whole top face of an insulated 20 x 20 mm two-layer board, 35 um copper) every watt crosses the top copper, so
         the exact surface minus column mean is q t / (2 k). On a 4 x 4 mm, 1 W part on the same board the heat enters through the face and partly spreads sideways in the copper:
         with the in-plane divergence uniform through 35 um, the term lies between q t / (3 k) (all heat sideways) and q t / (2 k) (all heat down), 0.67 to 1.00 of the bound.
         The FEM (pcbthermal.fem) puts the power of a part on a copper layer of one slab (up to 105 um) as a VOLUMETRIC source in that slab (femmesh.build), and a single linear
         element carries half of that load at its bottom node; the FVM reads the face flux. Printed: the term of each model in mK and in units of q t / (2 k), at 2, 1 and 0.5 mm.
         Usage: .venv/bin/python research/surface-readout-models/scripts/study_fem_thin_source.py (about 20 s, under 1 GB).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from pcbthermal import Problem, SolverOptions, analysis, simulate  # noqa: E402


def board(full):
    """!
    @brief The test board: 20 x 20 mm, two layers of 35 um copper on 1.6 mm, insulated top and sides, a film of 10 W/m2K below.
    @param full True: a 4 W part over the whole top face (one-dimensional); False: a 1 W part of 4 x 4 mm at the centre.
    @return tuple (Problem, footprint area in m2).
    """
    p = Problem.new(20.0, 20.0, layers=2, thickness_mm=1.6, copper_um=35, ambient=25.0, h_top=1e-6, h_bottom=10.0, h_side=None)
    p.add_full_copper(layers=None)
    if full:
        p.add_heater(1, 4.0, rect=(0.0, 0.0, 20.0, 20.0), name="S")
        return p, 400e-6
    p.add_heater(1, 1.0, rect=(8.0, 8.0, 12.0, 12.0), name="S")
    return p, 16e-6


def main():
    """!
    @brief Print the term (surface maximum minus column maximum under the part) of the FVM and the FEM against q t / (2 k).
    """
    for full in (True, False):
        for cell in (2.0, 1.0, 0.5):
            p, area = board(full)
            bound = p.heaters[0].power / area * 35e-6 / (2.0 * p.board.materials.k_copper)
            parts = []
            for m in ("fvm", "fem"):
                r = simulate(p, SolverOptions(models=(m,), cell_mm=cell)).results[m]
                col = analysis.heater_stats(r, p)[0]["t_max"]
                surf = analysis.surface_stats(r, p.heaters[0].polygon, 0, p.board.outline)[0]
                parts.append(f"{m} {1e3 * (surf - col):.3f} mK ({(surf - col) / bound:.2f})")
            kind = "part over the whole face (1D, exact = 1.00)" if full else "4 x 4 mm part (physical range 0.67 to 1.00)"
            print(f"{kind}, cell {cell} mm: q t / 2k = {1e3 * bound:.3f} mK; " + "; ".join(parts), flush=True)


if __name__ == "__main__":
    main()
