#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_well.py
@brief How much of the series resistance between a plane and the barrel is carried by the Peaceman well in the program? (It is almost none: the footprint is enlarged until the well is infinite.)
@details For a lone 0.3 mm via on full copper and on the quarter-copper board of scripts/study_reference_set.py, the layer-to-layer conductance of the Kron-reduced block
         (G[0, 1]) of the program, as a share of the barrel conductance of the gap (gv): 1.0 means the two well conductances are infinite (the means are the barrel potential).
         Run from the repository root: `.venv/bin/python research/via-contact-geometry/scripts/study_well.py`.
"""

import logging
import sys

import _bootstrap  # noqa: F401

import study_reference_set as RS

logging.disable(logging.WARNING)


def main():
    """!
    @brief Print the shares.
    @return None.
    """
    Problem, fvm, fdm, solid3d, load_project = RS.setup(str(_bootstrap.REPO))
    cases = RS.make_cases(Problem)
    for name in ("full d0.3", "quarter", "track 0.25"):
        p = cases[name](True)
        d = p.board.gap_thicknesses()
        for cell in (1.0, 0.5, 0.25, 0.125):
            net = fvm.Network(p, max(int(round(10.0 / cell)), 2), max(int(round(10.0 / cell)), 2))
            gv = p.board.materials.k_copper * p.vias[0].thermal_area(p.board.via_plating, p.board.materials.k_copper) / d[0]
            g01 = float(net.via_blocks[0][3][0, 1])
            print(f"{name:12s} cell {cell:5.3f}  G[0,1] / gv = {g01 / gv:6.3f}   footprint cells {len(net.via_blocks[0][0])}")


if __name__ == "__main__":
    sys.exit(main())
