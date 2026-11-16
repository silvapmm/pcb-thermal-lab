#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_final_1b_checks.py
@brief Final review of 2.8.0, part 1b: the light numerical checks of docs/theory.md 5 to 8 that no other script of the repository prints.
@details Prints (1) the Lumped closed forms at one point each (Bessel factors, the self distance 0.447 against Maxwell's closed form, the annulus link and its
         disc limit), (2) the ring-1 potential of the first link with the 900 kept source cells against the sum over every cell, (3) the Lumped against the FVM
         on the 'reference board, heater in the corner' row of docs/validation.md 2 (1 mm, both models), (4) the radiation coefficient at 10 and 80 K and the
         computed face coefficients of three board sizes (the numbers of theory 8). Light: under 1 GB and a few seconds.
         Run from the repository root: .venv/bin/python releases/2.8.0/final-review/scripts/study_final_1b_checks.py (releases/2.8.0/final-review/PART_1B.md).
"""
import math
import os
import sys

import numpy as np
from scipy import ndimage

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "research", "models-comparison", "scripts"))

from pcbthermal import convection, fvm, lumped                       # noqa: E402
from pcbthermal import viaconstriction as vc                         # noqa: E402
from pcbthermal.model import Problem                                 # noqa: E402
from pcbthermal.project import problem_from_dict, problem_to_dict    # noqa: E402


def closed_forms():
    """!
    @brief Print the Lumped closed forms at one point each (theory 5 and 5.2).
    @return None.
    """
    for x in (0.3, 1.0, 4.0):
        f_r, f_p = lumped._interior_factors(x)
        print(f"Bessel factors x = {x}: f_R {float(f_r):.5f}  f_P {float(f_p):.5f}")
    # Geometric mean distance of a square to itself (Maxwell): exp(ln 2 / 3 + pi / 3 - 25 / 12)
    print(f"self distance of a square: closed form {math.exp(math.log(2) / 3 + math.pi / 3 - 25 / 12):.6f}, coded 0.447")
    s = 0.0135
    print(f"annulus link 0.2 / 2 mm {vc.annulus_out_resistance(s, 0.2e-3, 2e-3):.6f} K/W; r_c -> 0 {vc.annulus_out_resistance(s, 1e-9, 2e-3):.6f}, "
          f"1 / (8 pi S) {1 / (8 * math.pi * s):.6f}")


def ring1_subsample():
    """!
    @brief Print the link term U1 - phi_b of the first Lumped link with the kept source cells against the sum over every footprint cell (theory 5).
    @return None.
    """
    dx = 0.5e-3
    for side, row in ((20, 0), (30, 0), (40, 0), (59, 5)):
        cov = np.zeros((160, 200))
        cov[row:row + side, 80:80 + side] = 1.0
        foot = cov > 0
        dist = ndimage.distance_transform_edt(~foot, sampling=(dx, dx))
        edges = lumped.ring_edges(dist.max(), dx, dx, 10, a_eq=lumped._equivalent_radius(foot, dx, dx))
        ring1 = (~foot) & (dist <= edges[1])
        phi_b = lumped._footprint_potentials_images(cov, dx, dx)[1]
        kept = lumped.RING1_SOURCES
        try:
            u_kept = lumped._ring1_potential(cov, dx, dx, 160, 200, ring1)
            lumped.RING1_SOURCES = 10 ** 9                            # every source cell
            u_all = lumped._ring1_potential(cov, dx, dx, 160, 200, ring1)
        finally:
            lumped.RING1_SOURCES = kept
        print(f"ring 1, {side * side} footprint cells at a side: U1 - phi_b kept {u_kept - phi_b:.5f}, all {u_all - phi_b:.5f}, "
              f"difference {100 * (u_kept - u_all) / (u_all - phi_b):+.3f} %")


def corner_row():
    """!
    @brief Print the Lumped and the FVM at 1 mm on the 'reference board, heater in the corner' and the centred reference board of docs/validation.md 2.
    @return None.
    """
    import accuracy_study
    d = problem_to_dict(accuracy_study.reference_problem())
    d["heaters"][0]["polygon_mm"] = [[10, 10], [30, 10], [30, 30], [10, 30]]
    for name, p in (("heater in the corner", problem_from_dict(d)), ("centred", accuracy_study.reference_problem())):
        t_f = fvm.solve_steady(p, 1.0).t_max
        t_l = lumped.solve_steady(p, cell_mm=1.0).t_max
        amb = p.board.ambient
        print(f"reference board, {name}: FVM {t_f:.2f} degC, Lumped {t_l:.2f} degC ({100 * (t_l - t_f) / (t_f - amb):+.1f} % of the rise)")


def coefficients():
    """!
    @brief Print the radiation coefficient and the computed face coefficients quoted in theory 8.
    @return None.
    """
    for rise in (10.0, 70.0, 80.0):
        print(f"h_r at a {rise:.0f} K rise over 25 degC, emissivity 0.9: {convection.h_radiation(25.0 + rise, 25.0, 0.9):.2f} W/m2K")
    for w, h in ((60, 40), (100, 80), (160, 100)):
        b = Problem.new(w, h, layers=2).board
        b.ambient = 25.0
        vals = [convection.board_h(b, 25.0 + r, 25.0 + r)[:2] for r in (10.0, 20.0, 40.0)]
        print(f"{w} x {h} mm, top / bottom at 10 / 20 / 40 K: " + ", ".join(f"{t:.1f} / {u:.1f}" for t, u in vals))


def main():
    """!
    @brief Run the four checks.
    @return None.
    """
    closed_forms()
    ring1_subsample()
    corner_row()
    coefficients()


if __name__ == "__main__":
    main()
