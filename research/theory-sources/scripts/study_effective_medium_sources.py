#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_effective_medium_sources.py
@brief F4: the 2D effective-medium formulas of the copper-mapping research (Bruggeman, Hashin-Shtrikman, Keller-Dykhne) against Milton's book and an independent solver.
@details The formulas of `research/gerber-models/lib/conduction.py` were written from memory; here they are compared with the forms printed in Milton, The Theory of
Composites (2002), equations 7.9, 7.10, 3.9, 3.11, 10.31 and 10.32, and with a periodic finite-volume solution of the field equation (lib/cond2d.py, which imports nothing
of the program): (1) the bounds of equation 7.10 for d = 2 against the repository forms; (2) the Bruggeman root for d = 3 against the closed form of equation 10.32 and for
d = 2 against the repository function; (3) the solver against the bounds on a square array of disks and a random cell medium; (4) the Keller phase-interchange product and
the checkerboard value sqrt(s1 s2) approached by grid refinement.
Run from the repository root: .venv/bin/python research/theory-sources/scripts/study_effective_medium_sources.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, os.path.join(ROOT, "research", "gerber-models", "lib"))

import cond2d as c2  # noqa: E402
import conduction as cd  # noqa: E402


def part1():
    """!
    @brief Bounds of Milton equation 7.10 for d = 2 against the repository Hashin-Shtrikman forms, and Milton's 3D Bruggeman closed form (10.32).
    @return Dict with the maximum relative differences and the 13/7 and 28/13 values.
    """
    f = np.linspace(0.02, 0.98, 49)
    a, b = 10.0, 1.0                               # copper-like phase 1 (better) and laminate-like phase 2
    low = np.array([c2.hs_bounds(x, a, b, 2)[0] for x in f])
    up = np.array([c2.hs_bounds(x, a, b, 2)[1] for x in f])
    rl = cd.map_hashin_shtrikman(f, "lower", a, b)
    ru = cd.map_hashin_shtrikman(f, "upper", a, b)
    # Closed form 10.32: s = (gamma + sqrt(gamma^2 + 8 s1 s2)) / 4, gamma = (3 f1 - 1) s1 + (3 f2 - 1) s2
    worst3 = 0.0
    for x in f:
        gam = (3 * x - 1) * a + (3 * (1 - x) - 1) * b
        closed = 0.25 * (gam + np.sqrt(gam * gam + 8 * a * b))
        worst3 = max(worst3, abs(c2.bruggeman(x, a, b, 3) / closed - 1))
    return {"low": float(np.abs(low / rl - 1).max()), "up": float(np.abs(up / ru - 1).max()), "bruggeman3d_vs_10_32": worst3,
            "13/7": c2.hs_bounds(0.5, 4.0, 1.0, 2)[0], "28/13": c2.hs_bounds(0.5, 4.0, 1.0, 2)[1]}


def part2():
    """!
    @brief Bruggeman d = 2 (the form derived from Milton 7.9) against the repository function.
    @return Maximum relative difference over fractions and ratios.
    """
    worst = 0.0
    for a, b in ((10.0, 1.0), (400.0, 0.3), (1000.0, 1.0)):
        for f in np.linspace(0.05, 0.95, 19):
            repo = float(cd.map_bruggeman(np.array([f]), a, b)[0])
            worst = max(worst, abs(c2.bruggeman(f, a, b, 2) / repo - 1))
    return worst


def part3():
    """!
    @brief The solver on a square array of disks (phase 1 conductivity 10 in a matrix of 1, area fraction 0.3) and on a random medium of cells, with the bounds and Bruggeman.
    @return Dict with the numbers.
    """
    out = {}
    vals = []
    for n in (48, 96, 192):
        vals.append(c2.effective_conductivity(c2.disk_array(n, 0.3, 10.0, 1.0)))
    out["disks"] = vals
    out["bounds_d2"] = c2.hs_bounds(0.3, 10.0, 1.0, 2)
    # Random medium of 8 x 8 pixel blocks with phase 1 probability 0.3 (a "cell material" of Milton section 3.2), 8 realisations
    rng = np.random.default_rng(7)
    ks = []
    for _ in range(8):
        blocks = rng.random((16, 16)) < 0.3
        ks.append(c2.effective_conductivity(np.where(np.kron(blocks, np.ones((8, 8))) > 0, 10.0, 1.0)))
    out["random_mean"], out["random_std"] = float(np.mean(ks)), float(np.std(ks))
    out["bruggeman2d"] = c2.bruggeman(0.3, 10.0, 1.0, 2)
    return out


def part4():
    """!
    @brief Keller phase interchange (Milton 3.9: s*(s1,s2) s*(s2,s1) = s1 s2 for an isotropic cell) on the disk array, and the checkerboard sqrt(s1 s2) (3.11) under refinement.
    @return Dict with the numbers.
    """
    prod = []
    for n in (48, 96, 192):
        a = c2.effective_conductivity(c2.disk_array(n, 0.3, 10.0, 1.0))
        b = c2.effective_conductivity(c2.disk_array(n, 0.3, 1.0, 10.0))
        prod.append(a * b / 10.0)
    cb = [c2.effective_conductivity(c2.checkerboard(n, 10.0, 1.0)) for n in (8, 16, 32, 64)]
    # Richardson from the last three values with the observed ratio of differences
    d1, d2 = cb[2] - cb[1], cb[3] - cb[2]
    ratio = d2 / d1
    extrap = cb[3] + d2 * ratio / (1.0 - ratio)
    return {"product": prod, "checker": cb, "sqrt": float(np.sqrt(10.0)), "extrapolated": float(extrap), "ratio": float(ratio)}


def main():
    """!
    @brief Print the results of the four parts.
    @return None.
    """
    p1 = part1()
    print("1. Milton 7.10 (d = 2) against the repository forms: lower %.2e, upper %.2e (relative); 13/7 = %.6f, 28/13 = %.6f; Bruggeman d=3 against 10.32: %.2e"
          % (p1["low"], p1["up"], p1["13/7"], p1["28/13"], p1["bruggeman3d_vs_10_32"]))
    print("2. Bruggeman d = 2 (derived from 7.9) against the repository function: max relative difference %.2e" % part2())
    p3 = part3()
    print("3. Square array of disks f 0.3, ratio 10, grids 48/96/192: %s ; HS bounds (lower = coated cylinders 7.9) %.4f %.4f"
          % (", ".join("%.4f" % v for v in p3["disks"]), *p3["bounds_d2"]))
    print("   random 8 x 8 blocks, p1 0.3: mean %.4f std %.4f ; Bruggeman 2D %.4f" % (p3["random_mean"], p3["random_std"], p3["bruggeman2d"]))
    p4 = part4()
    print("4. Keller product s*(10,1) s*(1,10) / 10 on the disk array at 48/96/192: %s" % ", ".join("%.4f" % v for v in p4["product"]))
    print("   checkerboard at 8/16/32/64 cells per square: %s ; sqrt(10) %.4f ; extrapolated %.4f (difference ratio %.3f)"
          % (", ".join("%.4f" % v for v in p4["checker"]), p4["sqrt"], p4["extrapolated"], p4["ratio"]))


if __name__ == "__main__":
    main()
