#  Copyright (c) 2026 Pedro Silva (PMS Labs). All rights reserved.
#  This code is licensed under the MIT License. Inclusion of this notice is required in any redistribution.
"""!
@file study_via_formulas_checks.py
@brief Do the program's via formulas (barrel conductance, Krogh cell, point-sink radius) reproduce a published case and an independent evaluation?

Question (README 9.4, plan study S0):
(1) TI application note AN-2020 (page 4) prints 261 C/W for one via, length 0.165 cm, plating 0.00175 cm, drill radius 6 mil = 0.01524 cm, copper 4 W/cmK:
    `Via.thermal_area` (plating inside the drill radius) against the printed value, and the variant with the plating outside the drill.
(2) `viaconstriction.krogh` (mean-to-wall resistance of a circular cell with a uniform source and an insulated rim) against a direct numerical integration of
    T(r) - T(a) = int_a^r Q(rho) / (2 pi S rho) d rho, Q = (R^2 - rho^2) / (R^2 - a^2) (the share of the heat generated outside rho), averaged over the annulus (R/a = 3, 10, 50).
(3) `viawell.POINT_SINK_RADIUS` (0.1985 cells, exp(-pi kappa / 2)) against the exact diagonal values of the potential kernel of the five-point lattice,
    a(n, n) = (4/pi) sum_{k=1..n} 1/(2k-1) (Spitzer; a(1,0) = 1), whose asymptote is (2/pi) ln(sqrt(2) n) + kappa; and against Peaceman's continuum value
    exp(-pi/2) = 0.2079 (Ibraguimov and others 2022, Theorem 1, p 11 to 12).

Run (from the repository root):  .venv/bin/python research/theory-sources/scripts/study_via_formulas_checks.py   (about 1 s)
"""
import math
import os
import sys

from scipy.integrate import quad

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)

from pcbthermal import viaconstriction, viawell  # noqa: E402
from pcbthermal.model import Via  # noqa: E402

TI_PRINTED = 261.0                                          # C/W, TI AN-2020 page 4
TI_LENGTH = 1.65e-3                                         # m
TI_PLATING = 17.5e-6                                        # m
TI_DRILL_DIAMETER = 2 * 0.01524e-2                          # m (drill radius 0.01524 cm)
TI_K = 400.0                                                # W/mK (4 W/cmK)


def ti_via():
    """!
    @brief Thermal resistance of the TI AN-2020 via from the program's copper area, and with the plating outside the drill.
    @return dict: r_prog (plating inside the drill, K/W), r_outside (plating outside the drill, K/W), printed, d_prog (r_prog / printed - 1).
    """
    area = Via(0.0, 0.0, TI_DRILL_DIAMETER).thermal_area(TI_PLATING, TI_K)
    r_prog = TI_LENGTH / (TI_K * area)
    r_out = TI_DRILL_DIAMETER / 2
    area_out = math.pi * ((r_out + TI_PLATING) ** 2 - r_out ** 2)
    return dict(r_prog=r_prog, r_outside=TI_LENGTH / (TI_K * area_out), printed=TI_PRINTED, d_prog=r_prog / TI_PRINTED - 1.0)


def krogh_numeric(s_sheet, r_cell, a):
    """!
    @brief Mean-to-wall resistance of the Krogh cell by numerical integration (independent of the closed form).
    @param s_sheet Sheet conductance in W/K.
    @param r_cell  Cell radius in m.
    @param a       Sink disc radius in m.
    @return float K/W.
    """
    area = r_cell ** 2 - a ** 2

    def rise(r):
        """!
        @brief Temperature of radius r above the wall per watt taken by the via.
        @param r Radius in m.
        @return float K/W.
        """
        # The heat that still has to pass inward through radius rho is the share generated outside it, (R^2 - rho^2) / (R^2 - a^2)
        return quad(lambda rho: (r_cell ** 2 - rho * rho) / area / (2 * math.pi * s_sheet * rho), a, r, epsabs=0, epsrel=1e-13, limit=200)[0]

    mean = quad(lambda r: rise(r) * 2 * math.pi * r, a, r_cell, epsabs=0, epsrel=1e-13, limit=200)[0] / (math.pi * area)
    return mean


def krogh_check(ratios=(3.0, 10.0, 50.0), s_sheet=1.7, a=0.15e-3):
    """!
    @brief Closed form of the program against the numerical integration.
    @param ratios  Values of R/a.
    @param s_sheet Sheet conductance in W/K (any value: the result scales as 1/S).
    @param a       Sink radius in m.
    @return list of dict: ratio, closed, numeric, rel (relative difference).
    """
    out = []
    for q in ratios:
        c, n = viaconstriction.krogh(s_sheet, q * a, a), krogh_numeric(s_sheet, q * a, a)
        out.append(dict(ratio=q, closed=c, numeric=n, rel=abs(c / n - 1.0)))
    return out


def lattice_radius(n=1_000_000):
    """!
    @brief Point-sink radius of the five-point lattice from exact diagonal kernel values, against the program's constant and Peaceman's.
    @param n  Diagonal index at which a(n, n) is evaluated (the asymptote error is O(1/n^2)).
    @return dict: r_prog, r_lattice (from a(n, n)), rel (their relative difference), r_peaceman (exp(-pi/2)).
    """
    a_nn = 4.0 / math.pi * math.fsum(1.0 / (2 * k - 1) for k in range(1, n + 1))
    kappa = a_nn - 2.0 / math.pi * math.log(math.sqrt(2.0) * n)             # a(r) ~ (2/pi) ln r + kappa, r = sqrt(2) n
    r_lat = math.exp(-math.pi * kappa / 2.0)
    return dict(r_prog=viawell.POINT_SINK_RADIUS, r_lattice=r_lat, rel=abs(viawell.POINT_SINK_RADIUS / r_lat - 1.0), r_peaceman=math.exp(-math.pi / 2.0))


def main():
    """!
    @brief Print the three checks.
    @return None.
    """
    t = ti_via()
    print(f"1. TI AN-2020 via: program {t['r_prog']:.2f} C/W vs printed {t['printed']:.0f} ({100 * t['d_prog']:+.2f} %); plating outside the drill {t['r_outside']:.1f} C/W")
    print("2. Krogh cell, closed form vs numerical integration")
    for r in krogh_check():
        print(f"  R/a {r['ratio']:g}: closed {r['closed']:.10f} numeric {r['numeric']:.10f} relative difference {r['rel']:.1e}")
    lr = lattice_radius()
    print(f"3. point-sink radius: program {lr['r_prog']:.6f} cells, lattice kernel {lr['r_lattice']:.6f} (relative {lr['rel']:.1e}), Peaceman exp(-pi/2) {lr['r_peaceman']:.4f}")


if __name__ == "__main__":
    main()
