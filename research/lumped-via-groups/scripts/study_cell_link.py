#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_cell_link.py
@brief The cell problem behind the link between the rest of the footprint (A) and the core (C): a sheet, a uniformly heated annulus, an ideal sink in the core and a vertical loss.
@details Axisymmetric problem, solved by finite differences (4000 radial points, no Bessel functions) and compared with the two closed forms of `lib/constriction.py`:
         the lossless `krogh(S, a, r_c)` and the lossy `cell_with_loss(S, g, r_c, a, q)`. Equation on r_c < r < a: S (T'' + T'/r) - g T + q = 0, T(r_c) = 0 (the core, an ideal sink),
         T'(a) = 0 (insulated rim). The link of a two-node network (A, C) that reproduces the area mean of A and the heat taken by the core is R_link = mean(T) / I_core.
         The study prints R_link 2 pi S for a grid of r_c / a and a / lambda (lambda = sqrt(S / g)), and the two closed forms as ratios to it: where the lossless link is good, and
         what the lossy one adds.
Usage: python research/lumped-via-groups/scripts/study_cell_link.py   (from the repository root; a few seconds)
"""

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "lumped-analytic-vias", "lib"))

import constriction as cr                                                   # noqa: E402


def exact_link(S, g, r_c, a, n=4000):
    """!
    @brief Mean temperature of the annulus over the heat taken by the core, by finite differences.
    @param S Sheet conductance in W/K.
    @param g Vertical loss per area in W/m2K (0 = none).
    @param r_c Core radius in m.
    @param a Outer radius in m.
    @param n Radial points.
    @return float R_link in K/W.
    """
    r = np.linspace(r_c, a, n)
    h = r[1] - r[0]
    # unknowns T_1 .. T_{n-1} (T_0 = 0); node i: S [ (r_{i+1/2} (T_{i+1} - T_i) - r_{i-1/2} (T_i - T_{i-1})) / (r_i h^2) ] - g T_i + q = 0
    m = n - 1
    main = np.zeros(m)
    lo = np.zeros(m - 1)
    up = np.zeros(m - 1)
    rhs = -np.ones(m)                                   # q = 1 W/m2
    for k in range(m):
        i = k + 1
        rp = r[i] + h / 2
        rm = r[i] - h / 2
        cp = S * rp / (r[i] * h * h)
        cm = S * rm / (r[i] * h * h)
        if i == n - 1:                                   # insulated rim: ghost node, T_{n} = T_{n-2} with the flux term at r + h/2 removed
            main[k] = -cm - g
            if k > 0:
                lo[k - 1] = cm
        else:
            main[k] = -cp - cm - g
            up[k] = cp
            if k > 0:
                lo[k - 1] = cm
    from scipy.linalg import solve_banded
    ab = np.zeros((3, m))
    ab[0, 1:] = up
    ab[1] = main
    ab[2, :-1] = lo
    t = np.concatenate([[0.0], solve_banded((1, 1), ab, rhs)])
    area = math.pi * (a * a - r_c * r_c)
    mean = float(np.trapezoid(t * 2 * math.pi * r, r) / area)
    # heat into the core: total source minus the vertical loss
    q_tot = area
    loss = float(np.trapezoid(g * t * 2 * math.pi * r, r))
    return mean / (q_tot - loss)


def main():
    """!
    @brief Print the table.
    @return None.
    """
    S = 0.0136
    print("## R_link 2 pi S of the cell problem (finite differences), and the closed forms as ratios to it\n")
    print("| r_c / a | a / lambda | R_link 2 pi S | lossless Krogh / R_link | lossy closed form / R_link |")
    print("| --: | --: | --: | --: | --: |")
    for rho in (0.15, 0.3, 0.45, 0.6, 0.8):
        for x in (0.05, 0.5, 1.0, 1.5, 2.0, 3.0):
            a = 5.6e-3
            lam = a / x
            g = S / lam ** 2
            r_c = rho * a
            ex = exact_link(S, g, r_c, a)
            kr = cr.krogh(S, a, r_c)
            lo = cr.cell_with_loss(S, g, r_c, a, 1.0)["R_c"]
            print(f"| {rho:.2f} | {x:.2f} | {ex * 2 * math.pi * S:.4f} | {kr / ex:.3f} | {lo / ex:.3f} |")


if __name__ == "__main__":
    main()
