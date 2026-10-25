"""!
@file study_thick_plate_criterion.py
@brief The thick-plate criterion of the program (`checks.check_thick_plates`) over the 74 cases of `block_equivalent_study.py`: how large is q'' t / (2 k) against the rise?

@details For every case the FVM is run and the bound q'' t / (2 k) of the block is divided by the FVM rise, with q'' taken two ways: the largest flux that really enters
         the block under the footprint (`checks._block_flux_under`, what the program uses since the effective-conductivity adoption) and the power of the part over
         its footprint (the first version). The program's `docs/validation.md` section 22 quotes median 0.07 % and maximum 0.34 % (flux into the block, 2 mm cells)
         and 0.50 / 1.78 % (footprint flux); this script reprints them. The warning fires above 5 %.

Usage: .venv/bin/python research/block-and-fins/scripts/study_thick_plate_criterion.py [cell_mm]   (default 2 mm; about 10 s)
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pcbthermal import checks, fvm                                            # noqa: E402
from pcbthermal.geometry import polygon_area                                   # noqa: E402
from block_equivalent_study import cases                                      # noqa: E402


def main(cell=2.0):
    """!
    @brief Print the median and the maximum of the criterion over the 74 cases, and the ratio of the two fluxes.
    @param cell Cell size in mm.
    """
    real, foot, ratio = [], [], []
    for _, p in cases():
        r = fvm.solve_steady(p, cell)
        rise = r.t_max - p.board.ambient
        h, s = p.heaters[0], p.heatsinks[0]
        q_block = checks._block_flux_under(r, h, 1)                           # The blocks of these cases are on the bottom face
        q_foot = h.power / polygon_area(h.polygon)
        real.append(100.0 * checks.thick_plate_bound(q_block, 1.0, s.thickness, s.k) / rise)
        foot.append(100.0 * checks.thick_plate_bound(q_foot, 1.0, s.thickness, s.k) / rise)
        ratio.append(q_block / q_foot)
    real, foot, ratio = map(np.array, (real, foot, ratio))
    print(f"{len(real)} cases, {cell:g} mm cells, bound q'' t / (2 k) in % of the FVM rise")
    print("| flux | median | maximum | above 5 % |")
    print("| :-- | --: | --: | --: |")
    print(f"| into the block (program) | {np.median(real):.2f} % | {real.max():.2f} % | {(real > 5).sum()} |")
    print(f"| power over the footprint | {np.median(foot):.2f} % | {foot.max():.2f} % | {(foot > 5).sum()} |")
    print(f"flux into the block / footprint flux: {100 * ratio.min():.0f} to {100 * ratio.max():.0f} %")


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 2.0)
