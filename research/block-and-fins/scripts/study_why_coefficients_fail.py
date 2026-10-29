#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_why_coefficients_fail.py
@brief Why are the equivalent-coefficient approaches too hot? A direct test of the explanation "the block spreads the heat of the centre of the pad to the whole pad,
       which a uniform coefficient cannot do".

@details The explanation names one quantity, the lateral conduction `k t` of the block. Three FVM runs per case measure it without the Lumped or Analytic models:
         1. the FVM with the block (the reference of `block_equivalent_study.py`);
         2. the FVM with the block's lateral conduction removed (`k` of a plain block set to 1e-6 W/mK; in the plate model `k` enters only the sheet conductance `k t`);
         3. the FVM on the equivalent problems of `block_equivalent_study.py` (the earlier isothermal coefficient, and approach A with contact area and annular fin).
         If the explanation is right, run 2 is about as hot as run 3 (old), and the error of the Lumped and Analytic models with an equivalent coefficient is
         mostly the error of the equivalent itself (run 3 against run 1), not of the reduced models.

Usage: .venv/bin/python research/block-and-fins/scripts/study_why_coefficients_fail.py   (about 10 s)
"""

import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pcbthermal import analytic, fvm, lumped                                  # noqa: E402
from block_equivalent_study import equivalent, make_case                      # noqa: E402

CASES = (("pad 30x30 in block 60x60, 1 mm Al", (20, 10, 80, 70), (35, 25, 65, 55), 1.0, 204.0),
         ("pad 30x30 in block 60x60, 3 mm Al", (20, 10, 80, 70), (35, 25, 65, 55), 3.0, 204.0),
         ("pad 30x30 in block 60x60, 6 mm Al", (20, 10, 80, 70), (35, 25, 65, 55), 6.0, 204.0),
         ("pad 30x30 in block 60x60, 3 mm steel", (20, 10, 80, 70), (35, 25, 65, 55), 3.0, 50.0),
         ("pad = block 40x40, 3 mm Al", (30, 20, 70, 60), (30, 20, 70, 60), 3.0, 204.0),
         ("pad 20x20 in block 80x60, 3 mm Al", (10, 10, 90, 70), (40, 30, 60, 50), 3.0, 204.0))


def main(r_c=5e-4, cell=1.0):
    """!
    @brief Print, per case, the FVM without lateral conduction in the block and the FVM on the equivalent problems, against the FVM with the block.
    @param r_c Interface resistance in m2K/W (5 K cm2/W, the typical case of the README).
    @param cell Cell size in mm.
    """
    print(f"Errors of the hottest point in % of the FVM rise with the block (R'' = {r_c * 1e4:g} K cm²/W, {cell:g} mm cells)")
    print("| Case | FVM rise (K) | FVM, block k t = 0 | FVM, old equivalent | Lumped / Analytic, old | FVM, equivalent A | Lumped / Analytic, A |")
    print("| :-- | --: | --: | --: | --: | --: | --: |")
    for name, rect, pad, thick, k in CASES:
        p = make_case(rect, pad, thick, k, r_c)
        ref = fvm.solve_steady(p, cell).t_max
        rise = ref - p.board.ambient
        flat = copy.deepcopy(p)
        flat.heatsinks[0].k = 1e-6                                            # No lateral conduction in the block; contact and exposed face unchanged
        e = lambda t: 100.0 * (t - ref) / rise                                # noqa: E731
        no_lat = e(fvm.solve_steady(flat, cell).t_max)
        old, new = equivalent(p, False), equivalent(p, True)
        f_old, f_new = e(fvm.solve_steady(old, cell).t_max), e(fvm.solve_steady(new, cell).t_max)
        la_old = [e(m.solve_steady(old, cell_mm=cell).t_max) for m in (lumped, analytic)]
        la_new = [e(m.solve_steady(new, cell_mm=cell).t_max) for m in (lumped, analytic)]
        print(f"| {name} | {rise:.1f} | {no_lat:+.1f} | {f_old:+.1f} | {la_old[0]:+.1f} / {la_old[1]:+.1f} | {f_new:+.1f} | {la_new[0]:+.1f} / {la_new[1]:+.1f} |", flush=True)


if __name__ == "__main__":
    main()
